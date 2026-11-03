# OOS 회수 설계 결정의 TLA+ 검증

## 질문, 독자, 결론

[OOS 삭제를 확정 뒤 회수로 바꾸는 설계 개정안](reclaim-redesign.md)에는 정해야 할 결정이 네 개 있다. 이 문서는 결정마다 후보를 TLA+ 모델에 넣고, 각 후보가 가능한지, 가능하다면 왜 가능한지를 TLC 검사 결과로 설명한다.

독자는 OOS 설계 담당자와 보고를 받는 팀장이다. 담당자는 이 문서로 후보를 고르고 구현할 조건을 확인한다. 팀장은 이 절의 표만 읽어도 무엇이 가능하고 무엇이 불가능한지 알 수 있다.

| 결정 | 가능한 후보 | 불가능한 후보와 이유 | 고른 후보 |
| --- | --- | --- | --- |
| 1. 지운 chunk의 slot과 바이트를 undo 때까지 지키는 방법 | D2b slot과 바이트 예약, D2c page 제외, D3 undo 없음 | 현재 코드(slot과 바이트를 다른 INSERT가 가져감), D1 latch 유지(두 vacuum worker가 서로의 page latch를 기다림), D2a slot만 예약(바이트를 다른 INSERT가 가져감) | D3 |
| 4. D3에서 LSA reclaim gate가 필요한가 | gate 없이도 안전: D1, D2c, D3 | gate 없으면 깨짐: 현재 코드, D2a, D2b | D3에서 gate를 없앤다 |
| 2. chain이 죽었다는 판단의 근거 | A' postpone 알림 | 현재 코드(rollback한 UPDATE), B commit 확인(statement rollback 뒤 commit), A commit hook 알림(hook과 commit 레코드 사이의 crash) | A' |
| 3. D3 회수기가 재시도에서 수렴하는 방법 | 꼬리부터 지우고 head를 마지막에, next 링크에 stamp, 오류 시 다시 실행 | head부터 지움(나머지 chunk가 고아가 됨), 링크 stamp 없음(재시도가 다른 레코드를 지움), 오류를 버림(회수가 멈춤) | 가능한 후보 그대로 |

"가능하다"는 모델의 모든 도달 가능 상태에서 성질이 성립한다는 뜻이다. "왜 가능한가"는 이유 불변식으로 답한다. 이유 불변식은 후보가 성질을 지키는 메커니즘을 상태 조건으로 쓴 것이다. TLC는 이 조건이 모든 도달 가능 상태에서 성립하는지 확인했다. 그 조건이 성질을 함의한다는 것은 각 절의 설명이 보이는 논증이다.

이 결과는 설계에 대한 것이다. 코드가 설계를 따르는지, 성능이 어떤지, 구현이 얼마나 어려운지는 답하지 않는다.

## 기준과 실행

| 항목 | 값 |
| --- | --- |
| 근거 코드 | CUBRID/cubrid `feature/oos-merge` `dcbf09e4f7fd02ff9c8fc6493ec8887fc2919d67` |
| 작성일 | 2026-11-03 (Asia/Seoul) |
| 모델 | [OosSpaceProtect.tla](reclaim-model/OosSpaceProtect.tla) (결정 1, 4), [OosDropDecision.tla](reclaim-model/OosDropDecision.tla) (결정 2), [OosReclaimRetry.tla](reclaim-model/OosReclaimRetry.tla) (결정 3) |
| 실행 도구 | [check_decisions.py](reclaim-model/check_decisions.py). 검사 96개와 기대값을 담고 있다. |
| TLC | `~/.cache/tlaplus/tla2tools-1.7.4.jar`, SHA-256 `936a262061c914694dfd669a543be24573c45d5aa0ff20a8b96b23d01e050e88`, TLC 2.19, Temurin 1.8.0_462 |
| 결과 | 96개 모두 기대값과 같다. 종료 코드 0, 8개 병렬 실행으로 약 18초. |

모델 파일의 SHA-256은 다음과 같다. `OosSpaceProtect.tla` `b283293cf0744e2581af573600bf78cca7187e8b0f2b1f8d2d3f798686e82f92`, `OosDropDecision.tla` `13029048d9ad3052e45cb1339aa41deab08d4cd71ed8b2e26aed6fa97c62623d`, `OosReclaimRetry.tla` `3ddbae04a3233d9391f0ff62f95e72329874ea106dce27e10f94e748178409a6`.

다시 실행하려면 다음 명령을 쓴다. `--out`은 새 디렉터리여야 한다.

```sh
python3 oos/reclaim-model/check_decisions.py --out <새 디렉터리>
```

출력 디렉터리의 `summary.md`에 전체 결과표와 모든 반례가 남는다. 통과한 검사의 상태 수는 모델 전체의 도달 가능 상태 수다. 결정 1은 138-460개, 결정 2는 20-28개, 결정 3은 32-50개다. 반례의 상태 수는 TLC가 반례를 찾을 때까지 본 수라 더 작다.

## 결정 1. 지운 chunk의 slot과 바이트를 undo 때까지 지키는 방법

### 모델

vacuum worker 두 개가 각자 죽은 chain 하나를 sysop 하나 안에서 지운다. chain A는 page p1에서 p2로, chain C는 p2에서 p1로 이어진다. page 하나에는 1단위 레코드가 둘 있고, 용량은 2단위다. 다른 트랜잭션 T2는 1단위 레코드 하나를 넣을 수 있다. 방해는 많아야 한 번 일어난다. 삭제 단계 실패 뒤의 `log_sysop_abort`이거나, crash 뒤의 재시작 undo다.

| 설정 `Protect` | 후보 | 모델에서 하는 일 |
| --- | --- | --- |
| `none` | 현재 코드 | `ANCHORED` page라서 지운 slot이 바로 `REC_DELETED_WILL_REUSE`가 된다. chunk마다 latch를 놓는다. |
| `latch` | D1 | 지운 page의 latch를 sysop이 끝날 때까지 쥔다. |
| `slot_only` | D2a | `ANCHORED_DONT_REUSE_SLOTS`라서 지운 slot이 `REC_MARKDELETED`가 된다. commit 때 postpone이 재사용 가능하게 바꾼다. 바이트는 바로 돌려준다. |
| `slot_and_bytes` | D2b | D2a에 더해, 지운 레코드의 바이트를 sysop이 끝날 때까지 그 sysop에 예약한다. |
| `page_exclude` | D2c | sysop이 끝날 때까지 그 page를 INSERT와 page 회수에서 뺀다(CBRD-27781 수정 후보 A). |
| `no_undo` | D3 | sysop은 회수 의도만 남긴다. commit 뒤에 chunk를 redo-only로 지운다. |

### 결과

| 성질 | 현재 코드 | D1 | D2a | D2b | D2c | D3 |
| --- | --- | --- | --- | --- | --- | --- |
| `UndoFindsEmptySlot` undo가 다른 레코드 위에 쓰지 않는다 | 반례 | 통과 | 통과 | 통과 | 통과 | 통과 |
| `UndoFindsRoom` undo가 page에서 자리를 찾는다 | 반례 | 통과 | 반례 | 통과 | 통과 | 통과 |
| `OtherRecordIntact` T2의 레코드가 남는다 | 반례 | 통과 | 통과 | 통과 | 통과 | 통과 |
| `ReclaimedWhenDone` 끝나면 죽은 chunk가 모두 지워져 있다 | 통과 | 통과 | 통과 | 통과 | 통과 | 통과 |
| `NoLatchWaitCycle` 두 worker가 서로의 latch를 기다리지 않는다 | 통과 | 반례 | 통과 | 통과 | 통과 | 통과 |

### 현재 코드가 깨지는 이유

두 반례 모두 다음 순서로 깨진다.

1. w1이 sysop을 시작하고, p1의 chunk A1을 `RVOOS_DELETE`(undo 있음)와 `spage_delete`로 지운 뒤 latch를 놓는다.
2. T2의 INSERT가 p1의 slot 1(A1이 있던 slot)에 레코드를 넣고 commit한다.
3. w1의 다음 삭제 단계가 실패해 `log_sysop_abort`가 A1을 slot 1에 되돌려 쓴다. T2의 레코드를 덮어쓴다.

두 번째 반례에서는 2단계의 T2가 slot 1 대신 새 slot 3을 쓴다. 그러면 3단계의 undo가 page에서 자리를 찾지 못한다. 실제 코드에서는 `spage_insert_for_recovery`가 `SP_DOESNT_FIT`를 돌려주고, `oos_rv_redo_insert`가 fatal 오류를 남긴다(`oos_file.cpp:3699-3722`).

이유 불변식으로 보면 두 조건이 모두 깨진다.

```tla
UndoSlotsStayEmpty ==   \* 열린 sysop이 되돌려 쓸 수 있는 slot은 지금 비어 있다
    \A w \in Workers : \A i \in 1..Len(vlog[w]) :
        slot[vlog[w][i].p][vlog[w][i].s].st # "used"
UndoBytesStayFree ==    \* page의 레코드와 열린 sysop이 되돌릴 레코드를 합해도 용량을 넘지 않는다
    \A p \in Pages : Used(p) + PendingOn(p) <= Cap
```

undo가 성공하려면 이 두 조건이 필요하다. 아래 후보는 모두 이 두 조건을 어떤 메커니즘으로 지키는지에 따라 갈린다.

### D1 latch 유지는 안전하지만 교착한다

D1에서는 `LatchCoversUndo`가 모든 상태에서 성립한다. 열린 sysop이 되돌려 쓸 수 있는 page는 모두 그 sysop이 latch를 쥐고 있다는 뜻이다.

```tla
LatchCoversUndo ==
    \A w \in Workers : \A i \in 1..Len(vlog[w]) : vlog[w][i].p \in held[w]
```

다른 트랜잭션은 latch 없이 page를 바꿀 수 없다. 그래서 `UndoSlotsStayEmpty`와 `UndoBytesStayFree`가 함께 성립한다. TLC는 이 셋을 모두 통과시켰다.

그러나 `NoLatchWaitCycle`의 반례가 있다. w1이 p1의 A1을 지우고 latch를 쥔다. w2가 p2의 C1을 지우고 latch를 쥔다. 그러면 w1은 p2를, w2는 p1을 기다린다. page latch에는 교착 탐지가 없으므로(CBRD-27860 분석) 둘은 영원히 기다린다. chain마다 page 순서가 다르므로 page 순서를 고정해서 피할 수도 없다. 순서를 고정하려면 지우기 전에 chain 전체를 읽어 page 목록을 알아야 한다(추론). 그래서 D1은 불가능하다고 판단한다.

### D2a slot만 예약하는 방식은 바이트를 지키지 못한다

D2a에서는 `MarkCoversUndo`가 성립한다. 되돌려 쓸 slot은 모두 `REC_MARKDELETED`이고, `spage_find_free_slot`은 이 slot을 건너뛴다. 그래서 `UndoSlotsStayEmpty`가 성립하고 `UndoFindsEmptySlot`도 통과한다.

그러나 `UndoBytesStayFree`는 깨진다. `spage_delete`는 anchor 타입과 상관없이 바이트를 먼저 돌려준다(`slotted_page.c:2079-2094`). T2는 새 slot 3을 만들어 그 바이트를 쓴다. 반례는 현재 코드의 두 번째 반례와 같다. "OOS page를 `ANCHORED_DONT_REUSE_SLOTS`로 바꾸면 되지 않는가"라는 질문의 답이 이 결과다. slot 번호는 지키지만 바이트는 지키지 못한다.

### D2b slot과 바이트 예약은 가능하다

D2b에서는 두 이유 불변식이 모두 성립한다.

```tla
MarkCoversUndo ==       \* 되돌려 쓸 slot은 모두 REC_MARKDELETED다
    \A w \in Workers : \A i \in 1..Len(vlog[w]) :
        slot[vlog[w][i].p][vlog[w][i].s].st = "marked"
ReserveCoversUndo ==    \* 예약은 되돌릴 레코드 수와 같고, 레코드와 예약의 합은 용량을 넘지 않는다
    /\ \A w \in Workers, p \in Pages :
         res[w][p] = Cardinality({i \in 1..Len(vlog[w]) : vlog[w][i].p = p})
    /\ \A p \in Pages : Used(p) + ResOn(p) <= Cap
```

`MarkCoversUndo`가 `UndoSlotsStayEmpty`를 함의한다. `ReserveCoversUndo`의 두 조건을 합치면 `Used(p) + PendingOn(p) <= Cap`이 되고, 이것이 `UndoBytesStayFree`다. 그래서 undo는 언제나 빈 slot과 자리를 찾는다.

모델은 구현 비용을 보여 주지 않는다. 실제로 D2b를 하려면 다음이 필요하다. `spage_save_space`의 vacuum worker 예외와 그 assert를 바꿔야 하고(`slotted_page.c:506-510`), OOS용 mark-reusable postpone recovery index를 만들어야 한다. 또 예약이 vacuum worker의 system tdes에서 언제 풀리는지 정해야 한다. 모델은 sysop이 끝날 때 예약이 풀린다고 가정한다.

### D2c page 제외도 가능하다

D2c에서는 `ExcludeCoversUndo`가 성립한다. 되돌려 쓸 page는 모두 그 sysop이 INSERT와 회수에서 빼 두었다는 뜻이다. 다른 트랜잭션은 그 page에 아무것도 넣지 못하므로 두 조건이 함께 성립한다. 대가는 sysop이 끝날 때까지 그 page의 빈 공간을 아무도 쓰지 못한다는 것이다. 메모리 map의 수명, 같은 소유자의 재사용, prepared 2PC 같은 증명 의무는 CBRD-27781 수정 후보 보고서에 정리되어 있고, 이 모델 밖이다.

### D3는 되돌릴 것이 없어서 가능하다

D3에서는 `NothingToUndo`가 성립한다. 어떤 상태에서도 열린 sysop의 undo 목록에 chunk 삭제가 없다.

```tla
NothingToUndo == \A w \in Workers : vlog[w] = <<>>
```

되돌려 쓸 slot이 없으므로 `UndoSlotsStayEmpty`와 `UndoBytesStayFree`가 아무 조건 없이 성립한다. 다른 후보는 "되돌릴 때까지 지킨다"로 성질을 지키지만, D3는 "되돌리지 않는다"로 지킨다. 그래서 지울 때 slot과 바이트를 바로 다른 트랜잭션에 넘겨도 된다.

## 결정 4. D3에서 LSA reclaim gate가 필요한가

같은 모델에 `Gate` 설정을 넣었다. `lsa`는 현재 코드다. 열린 sysop이 쓴 page는 회수하지 않는다(LSA horizon을 단순화한 조건). `none`은 레코드가 없는 page를 바로 회수한다. 성질 `UndoFindsPage`는 undo가 회수된 page를 대상으로 삼지 않는다는 것이다.

| `Gate` | 현재 코드 | D1 | D2a | D2b | D2c | D3 |
| --- | --- | --- | --- | --- | --- | --- |
| `lsa` | 통과 | 통과 | 통과 | 통과 | 통과 | 통과 |
| `none` | 반례 | 통과 | 반례 | 반례 | 통과 | 통과 |

gate가 없을 때 D2b의 반례는 일곱 단계다. w1이 A1과 A2를 지우고, w2가 C1을 지우면 p2가 빈다. 이때 page 회수가 p2를 반납한다. 그 뒤 w1이 실패하면 undo가 이미 반납된 p2에 A2를 쓰려 한다. 바이트를 예약해도 page 자체는 지키지 못한다.

D3는 gate 없이도 통과한다. 이유는 결정 1과 같은 `NothingToUndo`다. 삭제를 되돌리지 않으므로 빈 page가 undo의 대상이 될 일이 없다. 사양 §4는 gate의 이유를 "끝나지 않은 삭제자가 chunk 삭제를 그 page에 되돌릴 수 있다"로 적는다. D3에서는 이 이유가 없어지므로 gate를 지울 수 있다. 이 모델은 그 이유 하나만 다룬다. bestspace가 회수 중인 page를 INSERT에 넘기는 경쟁은 다루지 않는다.

D1과 D2c도 gate 없이 통과한다. latch나 제외 map이 page 회수까지 막기 때문이다. 다만 D1은 결정 1에서 교착으로 탈락했다.

## 결정 2. chain이 죽었다는 판단의 근거

### 모델

T1이 row를 chain A(버전 v0)에서 chain B(버전 v1)로 UPDATE한다. T1은 그 UPDATE를 statement rollback이나 savepoint rollback으로 되돌린 뒤에도 commit할 수 있고, 그냥 commit할 수도 있고, rollback할 수도 있다. 로그는 레코드 목록이고, 그 앞부분만 durable하다. WAL flush는 언제든 durable 범위를 끝까지 늘릴 수 있다. crash는 많아야 한 번이고, 복구는 durable한 부분만 남긴다. T1이 끝나면 vacuum이 block을 한 번 처리한다.

| 설정 `Notify` | 후보 | vacuum이 chain A를 지우는 조건 |
| --- | --- | --- |
| `undo_image` | 현재 코드 | block에 T1의 UPDATE undo image가 있다 |
| `commit_filter` | B | 위 조건에 더해 로그에 T1의 commit 레코드가 있다 |
| `commit_hook` | A (사양 §3 step 3) | 로그에 `RVOOS_NOTIFY_VACUUM`이 있다. commit hook이 commit 레코드 앞에 남긴다. 버린 chain 목록은 statement rollback을 따라 줄어든다(A에 가장 유리한 가정). |
| `postpone` | A' | 로그에 알림이 있다. UPDATE가 postpone 레코드를 남기고, `LOG_COMMIT_WITH_POSTPONE`이 durable해진 뒤 postpone 실행이 알림을 남긴다. statement rollback은 그 postpone을 취소한다. |

### 결과

| 성질 | 현재 코드 | B | A | A' |
| --- | --- | --- | --- | --- |
| `RowChainIntact` row가 참조하는 chain은 지워지지 않는다 | 반례 | 반례 | 반례 | 통과 |
| `DroppedChainReclaimed` commit된 UPDATE가 버린 chain은 지워진다 | 통과 | 통과 | 통과 | 통과 |

### 깨지는 후보의 반례

- **현재 코드(세 단계).** T1이 UPDATE하고 rollback한다. vacuum은 block에 undo image가 있다는 이유로 chain A를 지운다. row는 다시 chain A를 참조한다. CBRD-27237이다.
- **B(네 단계).** T1이 UPDATE하고, statement rollback으로 그 UPDATE를 되돌린 뒤 commit한다. commit 레코드가 있으므로 vacuum은 chain A를 지운다. 트랜잭션은 commit했지만 그 UPDATE는 commit되지 않았다.
- **A(다섯 단계).** T1의 commit hook이 알림을 남긴다. WAL flush가 알림을 durable하게 만든다. commit 레코드를 쓰기 전에 crash가 난다. 복구는 T1을 loser로 되돌리지만 알림은 로그에 남는다. vacuum은 그 알림으로 chain A를 지운다. CBRD-27237 심층 분석이 "commit 직전 장애 구간"이라고 부른 경우다.

### A'가 가능한 이유

A'에서는 두 이유 불변식이 모두 성립한다.

```tla
NotifyDurableOnlyWithCommit ==   \* 알림이 durable하면 commit 결정도 durable하다
    (\E i \in 1..durable : log[i] = "notify") =>
        \E i \in 1..durable : log[i] \in {"commit", "commit_pp"}
NotifyOnlyForSurvivingUpdate ==  \* 알림은 되돌려지지 않은 UPDATE에만 있다
    InLog("notify") => ~InLog("clr")
```

첫 조건이 있으면 복구가 T1을 loser로 만들 수 없다. 알림이 남아 있다면 commit 결정도 남아 있기 때문이다. 둘째 조건이 있으면 statement rollback으로 되돌린 UPDATE에는 알림이 없다. 두 조건이 함께 성립하므로 알림은 "commit된 UPDATE가 chain A를 버렸다"는 사실과 같다. 그래서 vacuum은 알림만 보고 지워도 된다.

A에서는 둘째 조건은 성립하고 첫 조건이 깨진다. 반례는 위 A 반례의 앞 세 단계다. A와 A'의 차이는 알림이 commit 결정보다 먼저 durable해질 수 있는지 하나뿐이다.

## 결정 3. D3 회수기가 재시도에서 수렴하는 방법

### 모델

chain A는 a1, a2, a3 순서의 세 chunk다. stub과 heap 레코드는 이미 없으므로 아무도 이 chain을 읽지 않는다. 회수기는 commit 뒤에 돌고, 각 삭제는 redo-only라 지운 slot은 바로 재사용된다. T2는 빈 slot 하나를 가져갈 수 있다. 방해는 많아야 한 번이다. crash가 나면 복구가 postpone을 head부터 다시 실행한다. 삭제 단계에서 오류가 나면 `OnError` 설정에 따라 처리한다.

| 설정 | 값 |
| --- | --- |
| `Order` | `head_first`는 chunk를 지우고 그 next 링크를 따라간다. `tail_first`는 head부터 chain을 읽은 뒤 꼬리부터 지우고 head를 마지막에 지운다. |
| `LinkStamp` | `TRUE`는 next 링크에 다음 chunk의 identity stamp도 두고 매 단계 비교한다. `FALSE`는 stub의 head stamp만 비교한다(현재 코드). |
| `OnError` | `discard`는 postpone 단계의 오류를 버리고 회수를 멈춘다. `rerun`은 head부터 다시 실행한다. |

### 결과

| `Order` | `LinkStamp` | `OnError` | `OtherRecordIntact` | `ReclaimedWhenDone` |
| --- | --- | --- | --- | --- |
| `head_first` | 둘 다 | 둘 다 | 통과 | 반례 |
| `tail_first` | `FALSE` | 둘 다 | 반례 | `rerun`만 통과 |
| `tail_first` | `TRUE` | `discard` | 통과 | 반례 |
| `tail_first` | `TRUE` | `rerun` | 통과 | 통과 |

### 깨지는 후보의 반례

- **`head_first`(네 단계).** 회수기가 a1을 지운다. 다음 단계가 실패하거나 crash가 난다. 다시 실행하면 head가 비어 있으므로 할 일이 없다고 판단한다. a2와 a3는 영원히 남는다.
- **`tail_first`, 링크 stamp 없음(여섯 단계).** 회수기가 a3를 지운다. 다음 단계가 실패한다. T2가 비어 있는 a3 slot을 가져간다. 다시 실행하면 a2의 next 링크가 가리키는 a3에 레코드가 있으므로 chain의 일부로 읽는다. 그리고 T2의 레코드를 지운다.
- **`discard`(두 단계).** 첫 삭제 단계가 실패하고 오류를 버린다. chain 전체가 남는다. CBRD-27781 수정 후보 보고서에 따르면, 지금 postpone 실행에는 recovery callback의 오류 반환을 버리는 경로가 있다(`beb3faccc`의 `log_manager.c` L8636-L8644).

### 꼬리부터, 링크 stamp, 다시 실행이 가능한 이유

이 조합에서는 두 이유 불변식이 성립한다.

```tla
RemainingIsPrefix ==     \* 남은 chunk는 언제나 chain의 앞부분이다
    /\ slot["a2"].own = "A" => slot["a1"].own = "A"
    /\ slot["a3"].own = "A" => slot["a2"].own = "A"
ListStillNamesChain ==   \* 아직 지울 목록의 slot은 모두 chain A의 chunk다
    (Order = "tail_first" /\ rpc = "run") =>
        \A i \in 1..pos : slot[list[i].s].own = "A"
```

`RemainingIsPrefix`가 성립하면 head부터 다시 읽어도 남은 chunk를 모두 찾는다. head를 마지막에 지우기 때문이다. `ListStillNamesChain`이 성립하면 회수기는 chain A의 chunk만 지운다. 링크 stamp 때문에 다른 레코드가 들어온 slot에서 읽기가 멈추기 때문이다. 그리고 `rerun`이 있어야 회수가 끝까지 간다.

다른 조합에서 어떤 조건이 깨지는지가 실패 이유를 보여 준다. `head_first`는 `RemainingIsPrefix`를 깬다. a1을 지운 순간 a2와 a3가 head 없이 남는다. 링크 stamp가 없으면 `ListStillNamesChain`이 깨진다.

## 결정을 합친 설계

모델 결과로 고른 조합은 다음과 같다.

- OOS chunk 삭제는 되돌리지 않는다(D3). 결정을 내린 트랜잭션이나 sysop은 회수 의도를 postpone으로 남긴다.
- UPDATE가 버린 chain은 postpone 실행이 남기는 알림으로만 vacuum에 알린다(A').
- 회수기는 head부터 chain을 읽고 꼬리부터 지우며, head를 마지막에 지운다. next 링크에 다음 chunk의 stamp를 둔다. 실패하면 오류를 버리지 않고 다시 실행한다.
- LSA reclaim gate는 없앤다. heap forward slot(CBRD-27858)은 이 모델 밖이며, #8348처럼 forward page latch를 sysop 끝까지 쥐는 방식으로 둔다.

D2b와 D2c도 결정 1을 통과하므로 대안으로 남는다. 둘 다 chunk 삭제의 undo를 유지하므로, chunk 레코드 전체를 undo로 쓰는 비용이 그대로 남는다. D2b는 gate도 남는다. 결정 2는 어느 후보를 고르든 필요하다. 결정 3은 D3를 고를 때만 필요하다. D2b나 D2c에서는 chain 삭제가 지금처럼 sysop 하나로 원자적이므로 head stamp만으로 재시도가 안전하다(U1의 CBRD-26950 결과).

## 모델의 한계

- 결정마다 따로 만든 작은 모델이다. 결정 사이의 상호작용은 아직 검사하지 않았다. 예를 들어 A'의 알림을 소비하는 vacuum이 D3 회수기를 부르는 전체 경로가 그렇다. 다음 단계에서 하나의 모델로 합친다.
- 규모가 작다. worker 둘, chain 둘, 다른 INSERT 하나, 방해 한 번이다. 결정 2와 3은 트랜잭션 하나와 chain 하나다.
- 결정 1의 바이트는 레코드당 1단위로 단순화했다. D2b의 예약은 sysop이 끝날 때 풀린다고 가정한다. 실제 `spage_save_space`는 트랜잭션 단위로 예약을 관리한다.
- 결정 4의 `lsa` gate는 "열린 sysop이 쓴 page는 회수하지 않는다"로 단순화했다. 실제 gate는 page LSA와 활성 트랜잭션, system tdes의 head LSA를 비교한다.
- 결정 2에는 MVCC snapshot 독자, HA replica, prepared 2PC, 복구 중 postpone 재실행의 MVCCID 문제가 없다. 마지막 문제는 CBRD-27237 심층 분석이 구현 때 정할 일로 남겼다.
- 모두 설계 모델이다. 코드가 이 설계를 따르는지는 `cubrid-verify-vacuum-slot-undo` 같은 적합성 모델과 오류 주입 테스트로 확인해야 한다.
