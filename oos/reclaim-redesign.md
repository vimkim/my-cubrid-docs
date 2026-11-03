# OOS 삭제를 확정 뒤 회수로 바꾸는 설계 개정안

## 질문, 독자, 결론

이 문서는 세 질문에 답한다.

1. 최근 OOS 결함 가운데 동시성과 복구가 겹치는 결함들은 같은 설계 가정에서 나오는가.
2. 그 가정을 없애는 설계는 무엇이고, 성능은 어떻게 바뀌는가.
3. 그 설계를 구현 전에 TLA+로 어떻게 검증하는가.

독자는 OOS 설계 담당자와 보고를 받는 팀장이다. 담당자는 이 문서로 사양 개정과 구현 순서를 정한다. 팀장은 이 절과 [보고 요약](#보고-요약)만 읽어도 결함, 수정 방향, 검증 계획, 일정 영향을 파악할 수 있다.

핵심 결과는 다음과 같다.

- **확인된 결함.** CBRD-27858, CBRD-27781, CBRD-27237은 소스에서 경로를 확인했다. CBRD-27237은 `dcbf09e4f`에서 실행으로 재현된 기록이 있다. CBRD-27858과 CBRD-27781은 기존 TLA+ 모델의 반례이고, CBRD-27781은 `224104a36` debug 테스트로 재현된 기록이 있다.
- **U1 결과(모델 검사).** 설계 모델 `OosReclaim.tla`가 현재 설계에서 네 결함을 모두 반례로 재현했다. CBRD-27858과 CBRD-27781은 "비운 공간은 되돌려지지 않는다"는 가정 하나에만 걸리고, CBRD-27237은 "확정되지 않은 정보로 삭제를 정해도 된다"는 가정 하나에만 걸린다. CBRD-26950은 두 가정과 무관한 세 번째 가정, "OOS OID는 계속 같은 값을 가리킨다"에 걸린다. 그래서 처음 세운 "가정 두 개" 가설은 세 결함에 대해서만 맞다. 결과는 [U1 결과](#u1-결과) 절에 있다.
- **제안.** OOS chain 삭제를 "결정이 확정된 뒤에 실행하는 redo-only, 멱등 회수"로 바꾼다. 이 문서는 이 설계를 D3라고 부른다. D3에서는 OOS에서 삭제를 undo하는 경로가 없어진다.
- **성능.** 지금 vacuum은 chunk를 지울 때 chunk 레코드 전체를 undo 데이터로 로그에 쓴다(소스). D3는 slot 번호만 쓴다. 회수 로그 양이 OOS 값 크기에 비례하지 않게 된다(추론, 측정 전).
- **열린 것.** D3 자체의 정확성(특히 회수 도중 crash 뒤 재시도), postpone 실행 실패 정책, 실제 성능 수치가 아직 열려 있다.

## 보고 요약

- OOS에는 commit된 데이터를 잃거나 page를 손상시킬 수 있는 결함 세 개가 열려 있다. vacuum 실패나 재시작 undo가 다른 트랜잭션이 쓴 slot을 덮어쓰는 결함(CBRD-27858, CBRD-27781)과, rollback한 UPDATE의 원래 값을 vacuum이 지우는 결함(CBRD-27237)이다.
- 세 결함은 따로 생긴 것이 아니다. OOS는 비운 slot을 즉시 재사용하게 하면서, 그 삭제를 나중에 undo할 수 있게 만들었다. 또 commit 여부를 확인하지 않은 정보로 삭제를 결정한다. TLA+ 모델에서 이 두 가정을 하나씩 되돌리면 각 결함의 반례가 사라지고, 하나씩 다시 넣으면 해당 결함만 다시 나타난다. heap과 file manager는 같은 문제를 "commit 뒤에 해제"하는 postpone으로 이미 피하고 있다.
- 수정 방향은 OOS도 같은 원칙을 따르게 하는 것이다. 삭제 결정은 postpone으로 남기고, 실제 삭제는 확정 뒤에 되돌리지 않는 방식으로 실행한다. 결함마다 하나씩 붙은 장치(latch 연장, in-memory 보호 map, LSA reclaim gate)가 필요 없어지거나 줄어든다.
- 기대 효과는 정확성과 성능이다. vacuum이 OOS 값을 회수할 때 값 전체를 로그에 쓰던 비용이 없어진다. 이 효과는 측정으로 확인한 뒤 채택한다.
- 검증 순서는 모델, 사양, 구현이다. 첫 단계(U1)는 끝났다. TLA+ 모델이 현재 설계에서 알려진 결함 네 개를 모두 재현했다. 다음 단계(U2)는 새 설계가 같은 검사를 통과하는지 확인하는 것이다. 통과하면 사양을 개정하고 구현한다.
- 일정 영향이 있다. PR #7990 병합 전에 하면 형식 변경 비용이 없다. 병합 뒤에 하면 OOS page와 로그 형식의 호환성 문제가 생긴다.

## 기준과 근거 범위

| 항목 | 값 |
| --- | --- |
| 저장소와 브랜치 | CUBRID/cubrid `feature/oos-merge` |
| 근거 commit | `dcbf09e4f7fd02ff9c8fc6493ec8887fc2919d67` |
| 작성 시점의 원격 head | `f67f2f692`. 다시 확인하지 않았다. 별도 문서(아래)는 `dcbf09e4f`에서 `beb3faccc`까지 삭제 함수의 변경이 bestspace 인자 제거뿐이라고 기록한다. |
| 사양 | `/home/vimkim/gh/cubrid-oos-context/OOS-CONTEXT.md`, SHA-256 `6300aa1fa6ffb54033b9c7f7ea959466e9d88f0530e1ab0d7178b4459d4fcf63` |
| 작성일 | 2026-11-03 (Asia/Seoul) |
| 관련 이슈 | CBRD-27858, CBRD-27781, CBRD-27237, CBRD-26950, CBRD-26786, CBRD-27230, CBRD-27860, CBRD-27881 |
| 관련 PR | [#7990](https://github.com/CUBRID/cubrid/pull/7990), [#8348](https://github.com/CUBRID/cubrid/pull/8348), [#8350](https://github.com/CUBRID/cubrid/pull/8350) |

방법은 정적 읽기다. 읽기 전용 조사 agent 두 개가 slot 재사용과 chain 삭제 소유권을 나누어 읽었다. 작성자가 아래 링크의 줄을 `dcbf09e4f`에서 직접 다시 확인했다. 이 작업에서는 엔진을 빌드하거나 실행하지 않았다. 실행 근거는 모두 기존 기록에서 가져왔고, 해당 위치에 출처를 적었다.

담당자가 2026-11-03에 정한 조건은 다음과 같다.

- PR #7990 병합 전에는 OOS page 형식, chunk header, recovery index를 storage-format revision을 올리지 않고 바꿀 수 있다. ADR-0006은 "미출시 변경이 기존 DB를 읽을 수 없게 하면 revision을 올린다"고 적는다. 사양을 개정할 때 이 결정을 ADR-0006에도 남긴다.
- 사양 개정은 담당자가 하고 팀장에게 보고한다.
- 채택 조건은 성능 개선이다.

## 결함들이 공유하는 가정

### 가정 1. 비운 공간은 되돌려지지 않는다

이 가정은 코드 주석에 적혀 있다. `spage_save_space`는 vacuum worker를 건너뛰며 "Vacuum workers do not rollback their heap changes"라고 쓴다([slotted_page.c L506-L510](https://github.com/CUBRID/cubrid/blob/dcbf09e4f7fd02ff9c8fc6493ec8887fc2919d67/src/storage/slotted_page.c#L506-L510)).

OOS가 들어온 뒤로 이 가정은 맞지 않는다. `vacuum_heap_record`는 OOS가 있는 레코드를 sysop 안에서 지운다. OOS 삭제가 실패하면 `log_sysop_abort`가 그 sysop을 되돌린다. sysop이 끝나기 전에 서버가 죽으면 재시작 복구가 되돌린다.

되돌리는 undo는 물리적이다. 같은 slot 번호에 `spage_insert_for_recovery`로 옛 레코드를 다시 쓴다. 이 함수는 slot이 비어 있다고 assert한다([slotted_page.c L1964-L1972](https://github.com/CUBRID/cubrid/blob/dcbf09e4f7fd02ff9c8fc6493ec8887fc2919d67/src/storage/slotted_page.c#L1964-L1972)). release 빌드에는 이 assert가 없어서, 다른 트랜잭션의 레코드를 덮어쓴다(조사 agent의 소스 추론, 실행하지 않음).

그런데 OOS의 slot은 비우는 순간 재사용할 수 있다.

- OOS page는 `ANCHORED`로 초기화된다([oos_file.cpp L3174](https://github.com/CUBRID/cubrid/blob/dcbf09e4f7fd02ff9c8fc6493ec8887fc2919d67/src/storage/oos_file.cpp#L3174)). 그래서 `spage_delete`가 slot을 바로 `REC_DELETED_WILL_REUSE`로 만든다.
- `spage_find_free_slot`은 `REC_DELETED_WILL_REUSE` slot을 새 레코드에 준다([slotted_page.c L1281-L1291](https://github.com/CUBRID/cubrid/blob/dcbf09e4f7fd02ff9c8fc6493ec8887fc2919d67/src/storage/slotted_page.c#L1281-L1291)).
- vacuum은 forward slot을 `reusable=true`로 비우고, page를 bestspace에 알린 뒤, sysop이 끝나기 전에 latch를 놓는다([vacuum.c L2546-L2558](https://github.com/CUBRID/cubrid/blob/dcbf09e4f7fd02ff9c8fc6493ec8887fc2919d67/src/query/vacuum.c#L2546-L2558)).
- `oos_delete_chain`은 chunk 하나를 지울 때마다 그 page의 latch를 놓는다.

slot을 보호하는 것은 page write latch 하나뿐이다. latch를 놓은 뒤 sysop이 끝나기 전까지, 다른 트랜잭션은 그 slot을 가져갈 수 있다.

### 가정 2. 확정되지 않은 정보로 삭제를 정해도 된다

vacuum의 forward-walk는 `RVHF_UPDATE_NOTIFY_VACUUM` 레코드의 undo image를 읽어 옛 chain을 지운다([vacuum.c L3619](https://github.com/CUBRID/cubrid/blob/dcbf09e4f7fd02ff9c8fc6493ec8887fc2919d67/src/query/vacuum.c#L3619), [L3764](https://github.com/CUBRID/cubrid/blob/dcbf09e4f7fd02ff9c8fc6493ec8887fc2919d67/src/query/vacuum.c#L3764)). block이 vacuum 대상이 되는 조건은 그 block의 트랜잭션이 모두 끝났다는 것뿐이다([vacuum.c L3287](https://github.com/CUBRID/cubrid/blob/dcbf09e4f7fd02ff9c8fc6493ec8887fc2919d67/src/query/vacuum.c#L3287)). commit했는지는 확인하지 않는다. rollback한 UPDATE의 undo image는 rollback으로 다시 살아난 원래 chain을 가리킨다. vacuum은 그 chain을 지운다.

identity stamp로는 이 결함을 막을 수 없다. undo image의 stub과 되살아난 stub은 stamp가 같다(사양 §3 step 4). 사양 §3은 commit 조건부 알림 `RVOOS_NOTIFY_VACUUM`을 요구한다. 그러나 `dcbf09e4f`에는 이 알림을 남기는 코드가 없다([recovery.h L206-L209](https://github.com/CUBRID/cubrid/blob/dcbf09e4f7fd02ff9c8fc6493ec8887fc2919d67/src/transaction/recovery.h#L206-L209)).

### 가정 3. OOS OID는 계속 같은 값을 가리킨다

OOS OID는 물리 주소다. slot을 다른 chain이 다시 쓰면, 같은 OID가 다른 값을 가리킨다. vacuum block을 다시 실행하면 바뀌지 않는 undo image에서 옛 OID를 다시 읽는다. CBRD-26950 이전 코드는 그 slot에 레코드가 있는지만 확인하고 지웠으므로, 다른 chain의 값을 지웠다. 지금은 head의 identity stamp를 비교해 이 경우를 no-op으로 처리한다.

U1 모델은 이 결함이 가정 1, 2와 무관하다는 것을 보여 준다. 재사용을 확정 뒤로 미루고 commit된 정보로만 삭제해도, 확정된 삭제 뒤에 slot이 재사용되면 재시도가 그 slot을 지운다. D3도 회수기를 재시도하므로 identity stamp를 유지한다.

### 결함과 가정의 대응

| 결함 | 증상 | 가정 | 현재 대응 | 상태 |
| --- | --- | --- | --- | --- |
| CBRD-27858 | 다른 INSERT가 가져간 forward slot에 abort나 재시작 undo가 옛 레코드를 씀 | 1 | forward page latch를 sysop 끝까지 유지 | #8348 draft |
| CBRD-27781 | 다른 INSERT가 가져간 OOS chunk slot에 undo가 씀 | 1 | 후보 비교 중 | 미해결. 2026-10-27 리뷰에서 병합 차단 지적 |
| CBRD-26786 | 빈 page가 아직 undo 대상일 수 있음 | 1 (page 단위) | LSA reclaim gate | 구현됨 |
| CBRD-26950 | vacuum 재시도가 재사용된 slot의 다른 값을 지움 | 3 | page-LSA identity stamp | 구현됨 |
| CBRD-27237 | rollback한 UPDATE의 원래 chain을 vacuum이 지움 | 2 | 사양 §3 알림. emitter 없음 | 미해결. `dcbf09e4f`에서 재현 |
| CBRD-27860 | vacuum과 heap page 할당이 서로의 latch를 기다림 | 별개 (latch 순서) | 조건부 조회 뒤 재시작 | #8350 draft |

가정 1 하나를 latch 연장과 LSA gate가 각각 다른 자리에서 막는다. CBRD-27781 후보에는 in-memory 보호 map이 하나 더 있다. 같은 가정을 slot과 page에서 장치를 따로 두어 막는다는 뜻이다(추론). identity stamp는 가정 3을 막는 장치이고 D3에서도 남는다.

CBRD-27860은 이 표에서 원인이 다르다. vacuum이 heap page를 쥔 채 heap header에서 OOS VFID를 찾는 latch 순서 문제다. TLA+로 교착을 검사할 수는 있지만, 이 문서의 설계 변경으로 해결되지는 않는다.

## heap과 file manager는 이미 확정 뒤에 해제한다

CUBRID에는 "지금 비우고, 확정되면 재사용을 허용한다"는 장치가 이미 있다.

- heap page는 `ANCHORED_DONT_REUSE_SLOTS`다([heap_file.c L1139-L1143](https://github.com/CUBRID/cubrid/blob/dcbf09e4f7fd02ff9c8fc6493ec8887fc2919d67/src/storage/heap_file.c#L1139-L1143)). 일반 삭제는 slot을 `REC_MARKDELETED`로 만들고, `spage_find_free_slot`은 이 slot을 건너뛴다.
- 재사용 OID heap의 삭제는 `RVHF_MARK_REUSABLE_SLOT`을 postpone으로 남긴다([heap_file.c L23879-L23882](https://github.com/CUBRID/cubrid/blob/dcbf09e4f7fd02ff9c8fc6493ec8887fc2919d67/src/storage/heap_file.c#L23879-L23882)). slot은 commit할 때 재사용 가능해진다. abort하면 postpone이 버려진다.
- `file_dealloc`은 영구 파일의 page 해제를 commit 뒤로 미룬다. 주석은 "we don't want anyone to reuse it until we are really sure the page is no longer used"라고 쓴다([file_manager.c L6131-L6174](https://github.com/CUBRID/cubrid/blob/dcbf09e4f7fd02ff9c8fc6493ec8887fc2919d67/src/storage/file_manager.c#L6131-L6174)).
- `log_sysop_commit`은 그 sysop의 postpone을 실행한다([log_manager.c L3985](https://github.com/CUBRID/cubrid/blob/dcbf09e4f7fd02ff9c8fc6493ec8887fc2919d67/src/transaction/log_manager.c#L3985)). 재시작 복구는 남은 postpone을 마저 실행한다([log_recovery.c L4082](https://github.com/CUBRID/cubrid/blob/dcbf09e4f7fd02ff9c8fc6493ec8887fc2919d67/src/transaction/log_recovery.c#L4082)).

OOS는 이 장치를 쓰지 않는다. OOS page는 `ANCHORED`라서 삭제 즉시 재사용할 수 있고, chunk 삭제에 postpone이 없다.

PostgreSQL TOAST와 InnoDB 외부 BLOB도 공간을 해제하는 동작 자체는 undo하지 않는다(배경 지식, 저장소 근거가 아님). 해제는 마지막 단계이고 redo만 남긴다.

## 수정 후보 비교

| 후보 | 내용 | 막는 결함 | 한계 |
| --- | --- | --- | --- |
| D1. 확정까지 latch 유지 | #8348 방식을 모든 page로 넓힌다 | CBRD-27858 | CBRD-27781을 막으려면 chain의 page를 모두 함께 쥐어야 한다. page latch에는 교착 탐지가 없다(CBRD-27860 분석). eager 경로는 user 트랜잭션이 끝날 때까지 latch를 쥘 수 없다. |
| D2. 확정까지 예약 | MARKDELETED와 postpone으로 slot을 예약하거나, in-memory map으로 page를 삽입 후보에서 뺀다 | CBRD-27858, CBRD-27781 | MARKDELETED는 slot 번호만 막는다. undo에는 바이트 공간도 필요한데 `spage_save_space`는 vacuum worker를 건너뛴다. map 방식은 둘 다 막지만 삭제자가 끝날 때까지 그 page의 빈 공간을 아무도 못 쓰고, 모든 삽입 결정에 map 조회가 붙는다. |
| D3. 확정 뒤에만 회수 | 삭제 결정을 postpone으로 남기고, 확정 뒤에 redo-only로 지운다 | CBRD-27781, CBRD-27237, eager 경로 | 새 recovery index, chunk header 변경, 사양 개정이 필요하다. 회수 도중 crash 뒤 재시도라는 새 문제가 생긴다. |

같은 날 작성된 CBRD-27781 수정 후보 보고서가 있다(`docs/CBRD-27781-fix-options` 브랜치, commit `5acf70d`, `cbrd-27781/fix-options.md`, 아직 `main`에 병합 전). 그 보고서의 후보는 이 문서와 다음처럼 대응한다.

| 그 보고서 | 이 문서 |
| --- | --- |
| A 임시 페이지 제외 | D2 (map 방식) |
| B1 슬롯과 바이트 예약, B2 본문 보존 tombstone | D2의 변형 |
| C 영속적인 지연 삭제 | D3 |
| D 모든 청크 latch 유지 | D1 |

그 보고서는 A를 다음 실험 후보로 추천했다. 이유는 기존 물리 undo와 형식을 유지한 채 검증하기 좋다는 것이다. 이 문서는 D3를 추천한다. 판단이 갈리는 이유는 세 가지다.

- 담당자 결정으로 형식 유지라는 제약이 없어졌다. A의 주된 장점이 이 제약에서 나왔다.
- A는 CBRD-27781만 다룬다. D3는 CBRD-27237의 권장 수정과 같은 장치를 쓴다. [CBRD-27237 수정 후보 심층 분석](../cbrd-27237/CBRD-27237-fix-options-deep-dive_dcbf09e_claude.md)은 commit 조건부 알림을 postpone에 실어 보내는 A'를 추천한다.
- 성능이 채택 조건이다. A는 모든 삽입 결정에 map 조회를 더하고 page 공간을 묶는다. D3는 vacuum 로그 양을 줄인다(아래 성능 절).

그 보고서가 C에 대해 적은 증명 의무는 D3에도 그대로 적용된다. 아래 D3 설계에서 그 의무를 다룬다.

## D3 설계: 회수 의도와 redo-only 회수기

### 원칙

OOS chunk 삭제는 되돌리지 않는다. 삭제를 결정하는 단위(트랜잭션 또는 sysop)는 회수 의도만 postpone으로 남긴다. 그 단위가 commit하면 회수기가 chain을 지운다. abort하면 postpone이 버려지고 chain은 그대로 남는다.

### 데이터 구조

- **회수 의도.** `(OOS VFID, head OOS OID, head identity stamp)`다. postpone 레코드나 vacuum 알림 레코드에 싣는다.
- **chunk header의 next 링크.** `(next-chunk OID, next-chunk identity stamp)`로 바꾼다. 지금은 OID만 있다. 삽입은 꼬리 chunk부터 하므로(사양 §2), 앞 chunk를 쓸 때 다음 chunk의 stamp를 이미 알고 있다. chunk header는 24B에서 32B가 된다.

### 회수 의도를 남기는 곳

| 삭제 결정 | 지금 | D3 |
| --- | --- | --- |
| vacuum REMOVE | sysop 안에서 chunk를 바로 지우고 undo를 남긴다 | sysop 안에서 회수 의도를 postpone으로 남긴다. `log_sysop_commit`이 회수기를 실행한다. |
| commit된 UPDATE가 버린 chain | forward-walk가 undo image를 보고 지운다 | UPDATE가 회수 의도를 postpone으로 남긴다. commit 때 postpone이 vacuum 알림을 남기고, vacuum이 MVCC상 안전한 시점에 회수기를 실행한다(A'). |
| 비-MVCC eager 정리 | user 트랜잭션 안에서 바로 지우고 undo를 남긴다 | 트랜잭션 commit 때 실행되는 postpone으로 회수 의도를 남긴다. |
| INSERT rollback | `RVOOS_INSERT` undo가 chunk를 지운다 | 바꾸지 않는다. 레코드를 지울 뿐 공간을 새로 쓰지 않는다. |
| forward-walk | undo image로 chain을 지운다 | 없앤다. 사양 §3이 이미 제거를 요구한다. |

### 회수기의 동작

1. head page를 write latch로 고정한다. page가 없거나, slot이 비었거나, stamp가 다르면 이미 회수된 chain이다. 아무것도 하지 않고 끝낸다.
2. next 링크를 따라 chain을 읽는다. 각 chunk의 stamp를 앞 chunk의 링크 stamp와 비교한다. slot이 비었거나 stamp가 다르면 그 앞 chunk까지를 남은 chain으로 본다.
3. 꼬리 chunk부터 지우고 head를 마지막에 지운다. 각 삭제는 slot 번호만 담은 redo-only 로그를 남긴다.
4. 비워진 page를 page 회수에 넘긴다.

head를 마지막에 지우는 이유가 있다. head가 남아 있는 동안은 재시도가 남은 chain을 찾을 수 있다. head를 먼저 지우고 crash하면 재시도는 head가 없으니 회수가 끝났다고 판단하고, 나머지 chunk는 고아로 남는다. CBRD-27781 수정 후보 보고서가 C의 반증 조건으로 든 경우다.

링크에 stamp를 넣는 이유도 있다. 이미 지운 chunk의 slot을 다른 chain이 가져갔을 수 있다. OID만 따라가는 재시도는 그 다른 chain의 chunk를 지운다. 지금 `oos_delete_chain`은 head에서만 stamp를 비교하고([oos_file.cpp L3346-L3352](https://github.com/CUBRID/cubrid/blob/dcbf09e4f7fd02ff9c8fc6493ec8887fc2919d67/src/storage/oos_file.cpp#L3346-L3352)), continuation chunk는 stamp 확인 없이 `pgbuf_fix`로 고정한다([oos_file.cpp L3305](https://github.com/CUBRID/cubrid/blob/dcbf09e4f7fd02ff9c8fc6493ec8887fc2919d67/src/storage/oos_file.cpp#L3305)). 지금은 chain 삭제 전체가 sysop 하나라서 이 문제가 드러나지 않는다. D3는 원자성을 버리고 재시도로 끝을 보장하므로 이 확인이 필요하다.

다른 방법으로 head에서 chunk를 하나씩 떼어 내는 방식이 있다. head의 next를 바꾸는 것과 chunk 삭제가 서로 다른 page를 바꾸므로, 둘을 crash에 대해 원자적으로 묶으려면 sysop과 undo가 다시 필요하다(추론). 그래서 이 문서는 채택하지 않는다.

### 실패 정책

- CBRD-27781 수정 후보 보고서에 따르면 postpone 실행의 recovery callback 오류 반환을 버리는 경로가 있다(`beb3faccc`의 `log_manager.c` L8636-L8644). 회수기가 실패한 채 넘어가면 chain이 조용히 새어 나간다. 데이터 손실은 아니지만 §4의 빈 page 회수 불변식을 깬다. 실패하면 서버를 멈추고 복구가 다시 실행하게 하는 방식과, 회수 의도를 다시 쌓는 방식 중에서 고른다.
- 회수기는 commit이 결정된 뒤에 돈다. 이 시점의 `ER_INTERRUPTED`는 회수를 멈출 이유가 되지 않는다. 회수기는 인터럽트를 무시하거나, 회수 의도를 다시 쌓은 뒤 멈춰야 한다.
- 복구 중 postpone을 다시 실행할 때 A'의 알림이 MVCCID assert에 걸릴 수 있다. CBRD-27237 심층 분석은 이때 알림 없이 chain을 바로 지우는 선택지를 적는다.

### 없어지는 것

- `RVOOS_DELETE`의 undo. 지금은 chunk 레코드 전체를 undo 데이터로 쓴다.
- forward-walk 삭제와 그 sysop wrapper `vacuum_forward_walk_oos_delete_atomic`.
- LSA reclaim gate일 가능성이 있다. 이 gate는 "끝나지 않은 삭제자가 chunk 삭제를 그 page에 되돌릴 수 있다"는 이유로 있다. D3에서는 chunk 삭제를 되돌리지 않는다. INSERT rollback의 undo는 레코드를 지울 뿐 공간을 쓰지 않는다. 그래서 gate가 필요 없을 수 있다(추론, 모델의 U2에서 확인한다).
- CBRD-27781 후보 A의 in-memory 보호 map. 만들 필요가 없다.

### 남는 것

- identity stamp. 회수기 재시도의 멱등성과 읽기의 stale 참조 거부에 계속 쓴다.
- CBRD-27858의 forward page latch 유지(#8348). heap slot의 undo는 vacuum sysop에 그대로 남는다. forward page 하나만 쥐므로 교착 위험이 작다(추론). heap forward slot에 MARKDELETED와 postpone을 쓰는 방법도 있지만 이 문서의 범위 밖이다.

## 성능 영향

| 항목 | 지금 | D3 | 근거 |
| --- | --- | --- | --- |
| chunk 삭제 로그 | chunk 레코드 전체를 undo로 쓴다(`log_append_undoredo_recdes (..., RVOOS_DELETE, ..., recdes_p, NULL)`, [oos_file.cpp L3221](https://github.com/CUBRID/cubrid/blob/dcbf09e4f7fd02ff9c8fc6493ec8887fc2919d67/src/storage/oos_file.cpp#L3221)) | slot 번호만 담은 redo-only 레코드 | 지금은 소스, D3는 제안 |
| 값 크기와 회수 로그 양 | 1MB 값을 회수하면 약 1MB를 로그에 쓴다 | chunk 수에 비례하는 작은 레코드 | 추론, 측정 전 |
| 빈 page 회수 | LSA gate가 일부 page를 미룬다 | gate를 없애면 바로 회수한다 | 추론 |
| 삽입 경로 | 변화 없음 | 변화 없음. 후보 A는 map 조회가 붙는다. | 제안 |
| latch 보유 시간 | chunk마다 짧다 | 같다. D1은 길어진다. | 제안 |
| 추가 비용 | 없음 | chain마다 postpone 레코드 1개, chunk header 8B, continuation page를 읽기와 삭제에 두 번 고정 | 추론 |

채택 전에 다음을 측정한다. 같은 release 빌드, 같은 데이터, 같은 설정으로 전후를 비교한다. 측정할 때는 benchmark checklist에 따라 수치가 무엇에 막혀 있는지 함께 기록한다.

1. 값 크기별(4KB, 64KB, 1MB) UPDATE 뒤 vacuum이 쓴 로그 바이트.
2. OOS UPDATE가 많은 부하에서 vacuum이 log block 하나를 처리하는 시간.
3. UPDATE와 DELETE를 반복한 뒤 OOS 파일의 page 수.
4. INSERT와 UPDATE의 지연. 나빠지지 않아야 한다.

## 사양 개정안

"사양 §3, §4 개정"은 `OOS-CONTEXT.md`에서 D3와 맞지 않는 정규 문장을 바꾸는 일이다. 지금 사양은 "chunk 삭제는 sysop 안에서 하고, 실패하면 rollback한다"를 요구한다. D3는 "chunk 삭제는 확정 뒤에 하고, rollback하지 않는다"로 바꾼다. chunk header가 바뀌므로 §2도 함께 바뀐다.

| 위치 | 지금 문장의 요지 | 개정 제안 |
| --- | --- | --- |
| §2 L141-L143 chunk 레코드 형식 | header는 `total_data_length`, `chunk_index`, next-chunk OID, `identity_stamp`의 24B | next 링크에 다음 chunk의 identity stamp를 더해 32B로 한다. |
| §2 L148 stamp 복원 | "Insert redo/delete undo restore the stored stamp from the logged image." | insert redo만 stamp를 복원한다. chunk 삭제에는 undo가 없다. |
| §2 L150 identity 검사 | head stamp를 삭제와 같은 write latch 아래 비교한다 | 회수기는 continuation chunk마다 링크의 stamp와 비교한다. head는 마지막에 지운다. |
| §2 L154 eager 정리 | eager 정리는 DML을 끝내고 건너뛴 정리를 진단으로 남긴다 | eager 정리는 트랜잭션 commit 때 실행되는 회수 의도를 남긴다. |
| §3 L216 step 3 | `logtb_complete_mvcc` 전에 commit hook에서 `RVOOS_NOTIFY_VACUUM`을 남긴다 | UPDATE가 버린 chain 목록을 postpone으로 남긴다. commit의 postpone 실행이 알림을 남긴다(A'). |
| §3 L217 step 4 | vacuum 재시도의 멱등성은 CBRD-26950 identity 검사로 얻는다 | 회수기의 멱등성은 head stamp, 링크 stamp, head를 마지막에 지우는 순서로 얻는다. |
| §3 L220 REMOVE와 eager의 역할 | "DELETE's REMOVE path and the SA/non-MVCC eager path keep their roles." | 두 경로 모두 chain을 직접 지우지 않고 회수 의도를 남긴다. |
| §4 L234-L239 복구 불변식 | 불변식 1-6 | 7번을 더한다. "OOS chunk 삭제는 redo-only이며, 삭제를 결정한 트랜잭션이나 sysop이 commit한 뒤에만 실행된다." |
| §4 L247 Vacuum + OOS | "REMOVE deletes within the caller's sysop ... Chunk deletes are logged so a mid-delete failure/recovery rolls back or replays the appropriate atomic operation." | REMOVE는 자기 sysop의 postpone으로 회수 의도를 남긴다. 알림 처리도 같은 회수기를 쓴다. 회수 도중 crash하면 head부터 이어서 지우고, 되돌리지 않는다. |
| §4 L258 LSA reclaim gate | 빈 page가 undo 대상일 수 있으면 회수를 미룬다 | U2 결과에 따라 지우거나 남긴다. 남기면 이유를 새로 적는다. |

사양은 U2가 통과한 뒤에 개정한다. 사양은 정규 문서라서, 검증 전에 바꾸면 현재 코드가 검증되지 않은 설계에 대해 부적합 상태가 된다.

## TLA+ 검증 계획

### 모델을 두 층으로 나눈다

- **설계 모델([reclaim-model/OosReclaim.tla](reclaim-model/OosReclaim.tla)).** 코드 줄이 아니라 프로토콜을 모델링한다. 행위자는 user 트랜잭션(INSERT, UPDATE, DELETE, commit, abort, savepoint rollback), vacuum worker(REMOVE, 알림 소비, block 재시도), 다른 INSERT, crash와 재시작 복구다. 상태는 slot 상태, row 버전과 stub, undo 로그, postpone 로그, snapshot이다.
- **적합성 모델(이미 있다).** `cubrid-verify-vacuum-slot-undo` 스킬은 코드에서 latch 해제 지점을 읽어 TLA+ 모델에 넣고, 코드가 성질을 지키는지 검사한다. D3를 구현하는 PR마다 같은 방식으로 이 층을 갱신한다.

### 검사할 성질

| 성질 | 내용 | 관련 결함 |
| --- | --- | --- |
| `UndoFindsEmptySlot` | undo는 다른 트랜잭션이 쓴 slot에 쓰지 않는다 | CBRD-27858, CBRD-27781 |
| `NoLiveChainDeleted` | live record나 활성 snapshot이 볼 수 있는 버전이 참조하는 chain은 지워지지 않는다 | CBRD-27237, CBRD-26950 |
| `NoForeignDelete` | 회수기는 자기 chain이 아닌 chunk를 지우지 않는다 | D3의 재시도 |
| `NoForeignRead` | 읽기는 다른 chain의 바이트를 돌려주지 않는다 | CBRD-26950 |
| `EventuallyReclaimed` | 참조가 끊긴 chain과 빈 page는 결국 회수된다. fairness 가정이 필요한 liveness 성질이다. | CBRD-26786, 고아 chain |

U1은 현재 설계의 결함을 결함별로 구분하려고 이 성질들을 더 잘게 나누어 검사했다. 이름과 대응은 [U1 결과](#u1-결과)에 있다. U2에서 D3를 검사할 때 `NoForeignDelete`와 `EventuallyReclaimed`를 더한다.

### 작업 단위와 확인 기준

1. **U1. 현재 설계 재현(완료, [U1 결과](#u1-결과)).** 설계 모델에 현재 설계를 넣는다. TLC가 CBRD-27858, CBRD-27781, CBRD-27237, stamp 이전의 CBRD-26950을 모두 반례로 찾아야 한다. "공간 재사용 시점" 설정 하나와 "삭제 결정 근거" 설정 하나로 이 반례들이 모두 설명되면 가정 두 개가 맞은 것이다. 설명되지 않으면 이 문서의 가설이 틀린 것이고, 설계를 다시 본다.
2. **U2. 후보 비교.** D1, D2, D3를 같은 모델의 대안 설정으로 넣고 같은 성질을 검사한다. crash는 모든 지점에서 허용한다. D3에서는 회수기 두 개가 같은 chain을 겹쳐 처리하는 경우와, 회수 도중 crash가 반복되는 경우를 포함한다. LSA gate를 뺀 D3도 함께 검사한다.
3. **U3. 사양 개정.** U2를 통과한 설계로 `OOS-CONTEXT.md`의 §2, §3, §4를 개정하고 ADR을 쓴다.
4. **U4. 구현.** PR을 나누어 구현한다. PR마다 적합성 모델을 갱신하고, 오류 주입 ctest로 반례의 실행 순서를 실제 코드에서 재현한다.

규모는 기존 모델과 비슷하게 잡는다. vacuum worker 하나, 트랜잭션 둘, row 하나, chunk 둘, crash 한 번이다. 기존 모델은 이 정도 규모에서 한 번 실행에 약 5초가 걸린다(스킬 기록). snapshot을 넣으면 상태 수가 늘겠지만 감당할 만할 것으로 본다(추측). TLC 1.7.4와 Java 8이 작업 서버에 있다.

모델이 통과해도 그것은 이 규모 안에서 설계가 맞다는 뜻이다. 코드가 설계를 따르는지는 적합성 모델과 오류 주입 테스트가 확인한다.

## U1 결과

2026-11-03에 실행했다. 모델은 [OosReclaim.tla](reclaim-model/OosReclaim.tla), 실행 도구는 [run.py](reclaim-model/run.py)다.

### 모델이 다루는 것

모델은 코드 줄이 아니라 `dcbf09e4f`의 프로토콜을 따른다. 설정 세 개가 현재 설계의 가정 세 개를 나타낸다. 각 설정의 첫 값이 현재 코드다.

| 설정 | 값 | 뜻 |
| --- | --- | --- |
| `ReuseAt` | `immediate`, `final` | 되돌릴 수 있는 삭제가 비운 slot을 다른 트랜잭션이 언제 가져갈 수 있는가 |
| `DecideFrom` | `ended`, `committed` | forward-walk가 undo image를 쓰기 전에 UPDATE에 대해 무엇을 확인하는가 |
| `HeadIdentity` | `stamp`, `none` | 삭제가 head chunk에서 무엇을 비교하는가. `none`은 CBRD-26950 이전 코드 |

작업 부하는 두 가지다. `del`에서는 T1이 relocated row를 지우고, vacuum REMOVE가 sysop 하나로 forward slot과 chunk 두 개짜리 chain A를 지운다. `upd`에서는 T1이 row를 새 chain B로 UPDATE한 뒤 commit하거나 rollback하고, vacuum forward-walk가 chain A를 자기 sysop에서 지운다. 다른 트랜잭션 T2는 빈 slot 하나를 가져갈 수 있다. 실행 중 방해는 많아야 한 번 일어난다. 삭제 단계 실패, block 중단, crash 중 하나다.

| 모델 동작 | 코드 |
| --- | --- |
| `RemoveStart`, `RemoveForwardSlot` | `vacuum_heap_record`의 `log_sysop_start`, `spage_vacuum_slot (forward_page, ..., true)`, 로그, forward page latch 해제 |
| `WalkStart` | `vacuum_process_log_block`에서 `vacuum_forward_walk_reclaim_oos`, `vacuum_forward_walk_oos_delete_atomic`의 `log_sysop_start` |
| `HeadAbsent`, `HeadStale`, `DeleteChunk` | `oos_delete_chain`의 head 확인, `RVOOS_DELETE` 로그, `spage_delete`, chunk마다 latch 해제 |
| `SysopCommit`, `BlockDone` | `log_sysop_commit`, block의 `set_vacuumed` |
| `FailStep` | 삭제 단계 실패와 `log_sysop_abort`. REMOVE는 block을 다시 실행하고, forward-walk는 오류를 지우고 block을 끝내거나 `ER_INTERRUPTED`면 다시 실행한다 |
| `Interrupt` | sysop commit 뒤, block 완료 전 중단. block을 `start_lsa`부터 다시 실행한다 |
| `Crash` | 재시작 복구가 열린 sysop과 T1을 undo하고 block을 다시 실행한다 |
| `T2Insert` | 다른 트랜잭션의 INSERT가 `spage_find_free_slot`으로 빈 slot을 받아 쓰고 commit한다 |

검사한 성질은 다섯 개다.

| 성질 | 내용 | 결함 |
| --- | --- | --- |
| `ForwardUndoFindsEmptySlot` | undo가 forward record를 다른 레코드 위에 쓰지 않는다 | CBRD-27858 |
| `ChunkUndoFindsEmptySlot` | undo가 OOS chunk를 다른 레코드 위에 쓰지 않는다 | CBRD-27781 |
| `RowChainIntact` | row가 아직 참조하는 chain은 지워지지 않는다 | CBRD-27237 |
| `OtherRecordIntact` | T2가 commit한 레코드는 사라지지 않는다 | CBRD-26950, 그리고 CBRD-27858과 CBRD-27781의 결과 |
| `ReclaimedWhenDone` | block이 끝나면 죽은 chain과 forward record가 해제되어 있다 | 회수 누락 |

### 실행 명령과 결과

```sh
python3 oos/reclaim-model/run.py --out <새 디렉터리>
```

설정 8개, 작업 부하 2개, 성질 5개를 곱한 80회를 실행했다. 실행마다 distinct state는 15-124개이고, 8개를 병렬로 돌린 전체 실행은 약 12초 걸렸다. 80회 모두 `run.py`의 `expected`와 같았고 종료 코드는 0이었다. 실행한 spec의 SHA-256은 `1f9eeda8b269efc107415f56eb3171ee787e1ea410f58f8cf5910b81a231a22d`다. TLC는 `~/.cache/tlaplus/tla2tools-1.7.4.jar`(SHA-256 `936a262061c914694dfd669a543be24573c45d5aa0ff20a8b96b23d01e050e88`, TLC 2.19)이고 Java는 Temurin 1.8.0_462다.

현재 코드의 설정에서 네 결함을 모두 재현했다.

| 결함 | 작업 부하 | 설정 | 성질 | 결과 |
| --- | --- | --- | --- | --- |
| CBRD-27858 | `del` | 현재 코드 | `ForwardUndoFindsEmptySlot` | 반례 |
| CBRD-27781 | `del` | 현재 코드 | `ChunkUndoFindsEmptySlot` | 반례 |
| CBRD-27237 | `upd` | 현재 코드 | `RowChainIntact` | 반례 |
| CBRD-26950 | `upd` | `ReuseAt=final`, `DecideFrom=committed`, `HeadIdentity=none` | `OtherRecordIntact` | 반례 |

CBRD-26950은 다른 두 가정을 막은 설정에서 확인했다. 현재 코드의 재사용 설정에서는 undo 덮어쓰기가 같은 성질을 먼저 깨므로, 재시도 경로만 분리해 보기 위해서다.

가설은 다음 표로 검사했다. 세 가정을 모두 막은 설정(`final`, `committed`, `stamp`)에서 시작해, 가정 하나만 현재 코드로 되돌렸을 때 무엇이 깨지는지 본다.

| 작업 부하 | 성질 | 시작 설정 | 깨뜨리는 설정 하나 |
| --- | --- | --- | --- |
| `del` | `ForwardUndoFindsEmptySlot` | 통과 | `ReuseAt=immediate` |
| `del` | `ChunkUndoFindsEmptySlot` | 통과 | `ReuseAt=immediate` |
| `del` | `OtherRecordIntact` | 통과 | `ReuseAt=immediate` |
| `upd` | `ChunkUndoFindsEmptySlot` | 통과 | `ReuseAt=immediate` |
| `upd` | `RowChainIntact` | 통과 | `DecideFrom=ended` |
| `upd` | `OtherRecordIntact` | 통과 | `ReuseAt=immediate`, 또는 `HeadIdentity=none` |
| `upd` | `ReclaimedWhenDone` | 반례 | 설정과 무관 |

표에서 읽을 수 있는 것은 다음과 같다.

- 각 가정은 자기 결함만 일으킨다. 가정 하나를 넣으면 그 가정에 걸린 결함만 나타나고, 다른 결함은 나타나지 않는다. 그래서 수정도 가정 단위로 할 수 있다. D3는 가정 1과 2를 없애고, 가정 3은 identity stamp로 계속 막는다.
- forward-walk에도 CBRD-27781과 같은 반례가 있다(`upd`의 `ChunkUndoFindsEmptySlot`). CBRD-27237 심층 분석이 `vacuum_forward_walk_oos_delete_atomic`에 대해 추론한 위험을 모델에서 확인한 것이다. 기존 적합성 모델은 이 wrapper를 다루지 않는다.
- forward-walk는 어느 설정에서도 회수를 빠뜨릴 수 있다(`upd`의 `ReclaimedWhenDone`). 삭제 단계가 실패하면 오류를 지우고 block을 끝내기 때문이다. 코드가 "leaving OOS unreclaimed (bounded leak)"라고 기록하는 의도된 동작이다([vacuum_oos.cpp L346-L355](https://github.com/CUBRID/cubrid/blob/dcbf09e4f7fd02ff9c8fc6493ec8887fc2919d67/src/query/vacuum_oos.cpp#L346-L355)). D3의 실패 정책 절이 다루는 문제다.

CBRD-27237의 반례는 다음과 같다. 다른 반례는 실행 출력의 `summary.md`에 같은 형식으로 남는다.

1. T1: heap_update가 새 chain B로 새 버전을 쓴다. undo image에는 chain A의 stub이 남는다.
2. T1이 rollback한다. chain A의 stub을 가진 옛 레코드가 복원되고 chain B의 insert는 undo된다.
3. vacuum: forward-walk가 UPDATE undo image에서 chain A의 stub을 읽고(block은 T1이 끝났는지만 확인한다) `log_sysop_start`를 부른다.
4. vacuum: `oos_delete_chain`이 `RVOOS_DELETE`를 기록하고 `spage_delete`로 slot a1을 비운다. row는 아직 chain A를 참조한다.

### 모델의 한계

- 이 결과는 위 규모 안에서만 성립한다. row 하나, T1 연산 하나, T2 INSERT 하나, 방해 한 번이다.
- slot 하나가 page 하나의 관심 slot을 나타낸다. 바이트 공간은 모델링하지 않는다. 그래서 `ReuseAt=final`은 "slot 번호와 공간을 모두 확정까지 막는다"는 추상적인 설정이다. D2의 MARKDELETED 방식은 slot 번호만 막으므로 이 설정과 같지 않다.
- T2의 INSERT는 slot 획득부터 commit까지를 한 단계로 본다. commit이 로그를 flush하므로, T2의 commit보다 앞선 vacuum 로그도 durable하다고 가정한다.
- MVCC snapshot 독자, savepoint rollback, eager 정리, UPDATE의 chain 재사용(CBRD-27230), HA는 모델에 없다. U2에서 D3를 검사할 때 eager 정리와 savepoint rollback을 넣는다.
- 설계 모델이다. 코드가 모델대로 동작하는지는 확인하지 않는다. 그 일은 `cubrid-verify-vacuum-slot-undo` 같은 적합성 모델과 오류 주입 테스트가 맡는다.

## 다른 검증 방법과 비교

| 방법 | 잘 찾는 것 | 못 찾는 것 | 판단 |
| --- | --- | --- | --- |
| TLA+와 TLC | 실행 순서, crash 지점, 복구 순서의 모든 조합 | 모델과 코드가 어긋난 부분 | 설계 검증에 쓴다. 도구와 선례가 이미 있다. |
| Quint | TLA+와 같다. 문법에 타입이 있다. | TLA+와 같다 | 설치되어 있지 않고 얻는 것이 적다. |
| P 언어 | 구현에 가까운 상태 기계 테스트 | C 엔진 코드와 연결되지 않는다 | 쓰지 않는다. |
| ctest 오류 주입 | 실제 코드에서 특정 실행 순서 | 누구도 떠올리지 못한 순서 | 구현 검증에 함께 쓴다. |
| 설계 리뷰만 | 빠르다 | crash가 끼는 순서 | 부족하다. 기존 모델은 forward page를 OOS 삭제 뒤에 놓는 변형이 crash와 재시작 undo를 거쳐야만 깨진다는 것을 찾았다. |

## 열린 질문과 위험

- vacuum worker의 `vacuum_heap_record` sysop 안에서 `log_append_postpone`을 쓸 수 있는지 확인하지 않았다. OOS page 회수의 `file_dealloc`이 sysop 안에서 postpone을 쓰므로 가능성은 높다(추론).
- savepoint rollback과 statement rollback이 그 범위의 postpone을 버리는지 확인해야 한다. CBRD-27237 심층 분석은 버린다고 추론하고, 구현 뒤 실행 확인을 요구한다.
- HA replica, prepared 2PC 트랜잭션에서 회수 의도가 어떻게 처리되는지 확인하지 않았다.
- 성능은 측정하지 않았다. 성능 절의 표는 소스와 추론이다.
- 근거 commit 이후 `feature/oos-merge`가 `f67f2f692`로 움직였다. 구현 전에 관련 함수를 다시 확인한다.

## 근거 문서

- 사양 `/home/vimkim/gh/cubrid-oos-context/OOS-CONTEXT.md` §2, §3, §4와 `docs/reference/implementation-observations.md`의 CBRD-27237, CBRD-26950, CBRD-26786 항목.
- [CBRD-27237 수정 후보 심층 분석](../cbrd-27237/CBRD-27237-fix-options-deep-dive_dcbf09e_claude.md). A' 추천과 postpone 실행 순서 근거.
- [CBRD-27881 OOS 리팩토링 후보 조사](../cbrd-27881/CBRD-27881-oos-refactoring-candidates_dcbf09e_claude.md). DF-01..DF-31 결함 후보 목록.
- CBRD-27781 수정 후보 보고서. `docs/CBRD-27781-fix-options` 브랜치 commit `5acf70d`의 `cbrd-27781/fix-options.md`. 작성 시점에 `main`에 병합되지 않았다.
- CBRD-27781 이슈 초안. `/home/vimkim/gh/my-cubrid-jira/issues/CBRD-27781-oos-slot-reuse-rollback-undo_dcbf09e_claude.md`의 재현 절차와 후보 비교.
- 기존 TLA+ 모델. `/home/vimkim/.claude/skills/cubrid-verify-vacuum-slot-undo/`의 `SKILL.md`와 `model/VacuumSlotUndo.tla`.
- [CBRD-27860 latch 순환 분석](../cbrd-26357/PR-7990-R2-vacuum-heap-header-deadlock_dcbf09e_codex.md).
