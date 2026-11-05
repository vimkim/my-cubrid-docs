# ADR-0008 이후 CBRD-27925 조사 범위

2026-11-05, Asia/Seoul. Work816. 독자는 OOS 구현 담당자와 재현 승인 범위를 정할 담당자다.

## 권고는 조사 축소와 구현 후 검증이다

질문은 LSA reclaim gate가 없어지는 ADR-0008 이후에도 CBRD-27925 후속 조사가 필요한가이다. **게이트 원인 추적은 새 설계의 필수 작업에서 제외하고, 빈 페이지 반환·재시도·성장 전 재사용 검증은 유지한다.** 현행 게이트를 고치기 위한 별도 DB 재현을 지금 요청할 필요는 없다. 승인된 Work742 구현 뒤, 남는 경로만 묶어 Work790의 별도 승인을 받아 검증하는 편이 낫다.

이유는 다음과 같다. LSA gate는 chunk 삭제 undo가 쓸 페이지를 보호한다. 확정 뒤 redo-only 회수는 그 복원 필요를 없앤다. 그러나 INSERT undo가 빈 페이지를 만드는 경로, READ 래치 경합, 검사 결과 분류와 `pending_deletes` 정산은 별개다. 또 chain의 모든 chunk를 지웠다는 사실은 빈 페이지를 파일 관리자에 반환했다는 뜻이 아니다.

원래 다섯 FAIL을 보존하고, abort 잔여 두 페이지의 최종 판정은 미확정으로 남긴다. 이번 조사는 이슈 해결이나 PASS 판정이 아니다. 엔진 소스 수정·빌드·서버 실행·DB 재현·JIRA 게시·상태 변경·merge·push는 수행하지 않았다.

## 비교 기준과 승인된 목표

| 기준 | revision과 해석 |
| --- | --- |
| 현재 엔진 | `CUBRID/CUBRID`, `CBRD-27925-adr0008-scope`, `d52b1889e907abcf84190ec504dde3bc93de260d`. 새 checkout의 소스를 읽었으며 변경하지 않았다. 핸드오프의 통합 대상은 `feature/oos-merge`다. |
| 기존 실제 DB 관측 | Engine `e3589ae42d42b04eb020e1ae43e165b01d31b12a`, TC `01df2600ac75180812451462b5c044cfa56b732a`. [기존 진단](../cbrd-26659/reclaim-compact-diagnosis.md)을 재실행하지 않았다. |
| 기존 READ 경합 모델·추출 실행 | `f67f2f692a7ad9f9efada2178759ca713e596b9d`. 이번에는 핵심 함수 비교와 별도의 순수 모델만 실행했다. 이전 추출 실행 전체를 현재 엔진의 실행 증거로 승격하지 않는다. |
| 정규 명세 | `vimkim/cubrid-oos-context`의 `281a940eafb5db507bce8e75a51de0ea94b4bfde`, `OOS-CONTEXT.md` 전체. SHA-256 `6300aa1fa6ffb54033b9c7f7ea959466e9d88f0530e1ab0d7178b4459d4fcf63`. 2026-10-27 문안은 LSA gate를 포함한다. |
| ADR | 같은 저장소의 `d5e81a77df40a952428acf918d699c4c930a2cb9`, `docs/adr/0008-reclaim-oos-chains-after-the-delete-is-final.md`, 결정 1–5. 파일의 `proposed`와 A'/B3 미정 문구는 11월 5일 승인 기록보다 오래된 문안이다. 정합화는 Work747이다. |
| 승인 근거 | 사용자 핸드오프와 `vimkim/my-cubrid-jira` `5660dbfe4549b53e8e4e1679d162d0900d14288f`의 `reviews/oos-postpone-20261105/REVIEW.md`, `PUBLICATION.md`, `issues/CBRD-27925-deferred-empty-page-reclaim.md`. [게시된 결정 댓글](https://jira.cubrid.org/browse/CBRD-27925?focusedCommentId=4777969#comment-4777969)은 A'와 확정 뒤 redo-only 회수, 별도 DB 승인 조건을 기록한다. 이번에 live workflow 상태를 다시 조회하거나 변경하지 않았다. |
| 문서 저장소 | `vimkim/my-cubrid-docs` main `9599d88`에서 별도 branch `docs/CBRD-27925-adr0008-scope`를 만들었다. |

이 분석의 target은 승인된 **A'**다. UPDATE postpone은 commit 확정 뒤 vacuum 알림을 만들고, vacuum은 오래된 snapshot이 끝난 뒤 chain을 회수한다. REMOVE는 heap 제거와 회수 의도를 같은 sysop에 기록한다. Eager cleanup은 트랜잭션 commit 뒤 회수한다. 회수기는 tail부터 head 순서로 redo-only 삭제하고 링크 stamp를 검사하며 오류·crash 뒤 재실행한다. LSA gate를 제거하되 vacuum fast path와 growth-gate sweep은 유지한다.

물리 페이지의 LSA horizon 제거와 **MVCC snapshot horizon 유지**를 구분해야 한다. A'의 MVCCID 전달·복구 중 알림 재발행은 Work742의 구현 의무다. B3 선택을 다시 열지 않는다. PR #7990은 수정·검증 뒤 develop 병합이라는 결정을 유지하며, CBRD-27230의 전체 미할당 컬럼 재사용을 병합 전 범위에 추가하지 않는다.

현재 엔진은 아직 target이 아니다. [삭제 로깅](https://github.com/CUBRID/CUBRID/blob/d52b1889e907abcf84190ec504dde3bc93de260d/src/storage/oos_file.cpp#L3191-L3199)은 전체 chunk를 undo로 남긴다. [복구 함수 표](https://github.com/CUBRID/CUBRID/blob/d52b1889e907abcf84190ec504dde3bc93de260d/src/transaction/recovery.c#L881-L911)는 `RVOOS_DELETE` undo를 재삽입에 연결하며 `RVOOS_NOTIFY_VACUUM`은 no-op stub이다. [현재 chunk header](https://github.com/CUBRID/CUBRID/blob/d52b1889e907abcf84190ec504dde3bc93de260d/src/storage/oos_file.hpp#L32-L47)에는 next-chunk stamp도 없다. 이 상태에서 gate만 제거하는 변경은 안전하지 않다.

## 어떤 작업을 남길 것인가

| 범위 | 현재 소스·관측 | 승인된 target 이후의 판정 |
| --- | --- | --- |
| LSA horizon 공급자·append clamp 추적 | `oos_reclaim_sample_horizon`의 regular/system head 최소값과 clamp가 페이지 회수를 유예한다. | **필수 조사에서 제외.** gate 삭제가 완료되면 이 원인은 없다. 과거 원인 확정이 별도로 필요할 때만 과거 기준 재현으로 남긴다. |
| Gate 때문에 유예된 페이지의 재방문 | Horizon 전진 자체에는 재호출 장치가 없다. | **게이트 전용 수리는 대체.** target에서 LSA 유예가 사라지는지 검증한다. 그 밖의 오류·경합 재시도는 계속 필요하다. |
| INSERT rollback의 마지막 chunk 삭제 | `RVOOS_INSERT` undo가 `oos_rv_redo_delete`를 호출하고 회수 힌트를 알린다. | **유지.** [기존 설계 보고서](../oos/reclaim-redesign.md#회수-의도를-남기는-곳)도 이 경로를 그대로 둔다. 새 chain reclaimer의 성공만으로 이 경로를 검증할 수 없다. |
| 1차 READ 경합·힌트 소실 | READ 실패가 LSA 비교 전 `SKIPPED`로 반환된다. 완료한 lap은 `DEFERRED`만 다시 더한다. | **유지.** 게이트를 없애도 같은 반례가 남는다. 최종 구현이 이 경로를 바꾸면 새 경로의 재시도 보장으로 검증을 옮긴다. |
| 2차 WRITE 실패 | READ 통과 뒤 WRITE fix 실패는 `DEFERRED`다. | **유지할 대조군.** LSA 유예와 함께 삭제하면 안 된다. READ 실패 가설을 과거 WRITE 실패 수리와 혼동하지 않는다. |
| `pending_deletes`·boot rule·cursor | 파일별 메모리 힌트로 sweep 실행 여부와 재방문 위치를 정한다. | **유지.** redo-only 전환이 힌트 정산을 대체하지 않는다. 재시작과 힌트 유실도 검증한다. |
| 확정된 intent·chunk 삭제 오류 재시도 | Target은 아직 미구현이다. 기존 삭제는 undo로 되돌린다. | **Work742 구현 후 검증.** intent를 잃지 않고 모든 남은 chunk까지 수렴해야 한다. 빈 페이지 반환과는 별도 완료 조건이다. |
| 추가 쓰기 없는 eventual return | 현행 fast path는 일회성 후보 목록이고 sweep은 해당 파일의 할당 시점에 실행된다. | **유지.** gate 제거로 fast path 성공률이 좋아져도 READ 경합·오류·후보 유실·INSERT undo 뒤의 재방문은 보장되지 않는다. |
| 성장 전 빈 페이지 재사용 | 기존 140 INSERT 대조는 빈 VPID 20개를 새 sector의 live page보다 먼저 재사용했다. | **구현 후 검증.** 부분 여유 공간 재사용·page 반환·새 sector 예약을 따로 관측한다. CBRD-27945의 메타데이터 재귀 예약은 별도 문제로 유지한다. |
| Abort 잔여 `1|1312`, `1|1313` | Undo·sweep 진입은 관측했으나 동일 호출의 emptiness·래치·최종 enum은 없다. | **과거 미확정 근거 보존.** 정확한 과거 두 VPID의 원인 확정을 target 검증의 선행 조건으로 두지 않는다. 새 기준에서 같은 경로를 검증한다. |

따라서 “조사 전체 유지”는 없어질 gate 원인에 시간을 쓰게 하고, “조사 불필요”는 남는 반환 의무를 놓친다. 선택은 **특정 범위 유지와 구현 후 검증으로 대체**다.

## Gate가 없어도 남는 반례

근거 경로는 [INSERT undo callback](https://github.com/CUBRID/CUBRID/blob/d52b1889e907abcf84190ec504dde3bc93de260d/src/storage/oos_file.cpp#L3649-L3673), [힌트 알림](https://github.com/CUBRID/CUBRID/blob/d52b1889e907abcf84190ec504dde3bc93de260d/src/storage/oos_file.cpp#L423-L435), [1차 READ 실패](https://github.com/CUBRID/CUBRID/blob/d52b1889e907abcf84190ec504dde3bc93de260d/src/storage/oos_file.cpp#L1572-L1604), [lap 정산](https://github.com/CUBRID/CUBRID/blob/d52b1889e907abcf84190ec504dde3bc93de260d/src/storage/oos_file.cpp#L1783-L1796), [다음 sweep 진입 조건](https://github.com/CUBRID/CUBRID/blob/d52b1889e907abcf84190ec504dde3bc93de260d/src/storage/oos_file.cpp#L1861-L1887)이다. Runtime rollback은 [WRITE latch 획득](https://github.com/CUBRID/CUBRID/blob/d52b1889e907abcf84190ec504dde3bc93de260d/src/transaction/log_manager.c#L7481) 뒤 callback을 실행하고 [마지막에 해제](https://github.com/CUBRID/CUBRID/blob/d52b1889e907abcf84190ec504dde3bc93de260d/src/transaction/log_manager.c#L7692-L7695)한다.

다음 순서는 gate가 없는 경우에도 가능하다는 소스 기반 가설이다. 다른 삭제 알림·유예·앞선 회수 성공이 없는 한 바퀴를 가정한다.

1. INSERT undo가 마지막 chunk를 삭제하고 WRITE latch를 잡은 채 `pending_deletes=1`을 알린다.
2. Sweep이 `pending_at_start=1`을 저장하고 해당 페이지를 검사한다. 조건부 READ가 실패하여 `SKIPPED`로 끝난다. LSA 비교에는 도달하지 않는다.
3. Undo가 WRITE latch를 해제한다. 페이지는 비어 있고 회수 가능하지만 sweep은 이미 지나갔다.
4. 한 바퀴가 회수 없이 끝난다. `n_deferred=0`이므로 `pending_deletes = 1 - 1 + 0 = 0`, `swept_this_boot=true`가 된다.
5. 다음 growth 호출은 sweep을 생략할 수 있다. 페이지는 디스크에 존재하지만 다시 검사할 메모리 힌트가 없다.

첫 READ가 성공했다면 gate 제거는 실제 차이를 만든다. LSA만 막던 빈 페이지는 회수할 수 있다. 반대로 첫 READ가 실패하면 비교식을 없애도 검사 결과가 바뀌지 않는다. 이 구분이 조사 축소의 근거다.

### 이번 독립 검사의 결과와 한계

[check_gate_scope.py](check_gate_scope.py)는 소스 SHA-256을 고정하고 `oos_reclaim_fix_candidate`, `oos_try_reclaim_page_internal`, `oos_reclaim_settle_lap`, `oos_reclaim_sweep_step`, `oos_rv_redo_delete`의 함수 본문이 기존 `f67f2f6`과 현재 `d52b188`에서 같은지 확인한다. 다섯 함수 모두 일치했다. 이어 한 lap의 결과 분류와 정산을 순수 모델로 실행한다.

```sh
python3 -B cbrd-27925/check_gate_scope.py <d52b188의-CUBRID-checkout>
```

| 조건 | 모델 결과 |
| --- | --- |
| READ busy, gate 있음 | `SKIPPED`, LSA 비교 미도달, 정산 뒤 pending 0 |
| READ busy, gate 없음 | 같은 결과. 다음 sweep 비활성화 반례 유지 |
| READ 성공, LSA만 거부 | gate가 있으면 `DEFERRED`; gate가 없고 WRITE도 가능하면 `RECLAIMED` |
| READ 성공, gate 없음, WRITE busy | `DEFERRED`, pending 1 유지 |
| Lap 시작 뒤 다른 삭제 알림 | 시작 건수만 차감하므로 새 힌트는 남는다. |
| Restart 뒤 boot rule | `swept_this_boot=false`이면 pending 0이어도 다음 성장 검사는 활성화된다. |

실행은 exit 0이었다. 여섯 조건 조합과 mid-lap 알림·boot 대조를 확인했다. 이는 **소스와 연결한 순수 모델**이며 추출 C++ 실행, 엔진 실행, 동시성 전체 탐색, 실제 sector 증가 측정이 아니다. Gate 없음은 target 전체 구현이 아니라 비교식만 생략한 가정이다. Latch 해제와 lap 정산 사이의 위 순서를 입력으로 준다.

이 모델은 `oos_find_best_page`와 file manager를 실행하지 않는다. Bestspace 표본이 빈 페이지를 재발견하거나 file manager에 이미 가용 페이지가 있으면 실제 sector 증가는 피할 수 있다. 따라서 증명한 것은 “gate 제거만으로 재검사 힌트 소실을 막지 못한다”이다. SQL 도달 가능성·발생 빈도·새 sector 예약까지의 연결은 미확정이다. 핵심 함수 일치도 주변 코드 전체 실행의 동등성을 뜻하지 않는다.

## Chunk 회수와 page 반환은 완료 조건이 다르다

Redo-only reclaimer는 확정된 intent를 받아 죽은 chain을 지운다. 오류·crash 뒤에도 intent가 남아 있어야 하고, head를 마지막에 지우며 링크 stamp로 다른 chain을 보호해야 한다. 이 보장은 **아직 존재하는 chunk**에 대한 것이다. 기존 [설계 결정 검증](../oos/reclaim-decisions.md#결정-3-d3-회수기가-재시도에서-수렴하는-방법)은 이 범위를 다룬다.

Page reclaimer는 **이미 chunk가 없는 페이지**를 반환한다. 현재 [page 반환](https://github.com/CUBRID/CUBRID/blob/d52b1889e907abcf84190ec504dde3bc93de260d/src/storage/oos_file.cpp#L1650-L1668)은 `file_dealloc`의 postpone과 별도 sysop commit을 사용한다. [Growth sweep](https://github.com/CUBRID/CUBRID/blob/d52b1889e907abcf84190ec504dde3bc93de260d/src/storage/oos_file.cpp#L1961-L1992)은 빈 페이지를 하나 반환하면 즉시 멈추고, 반환 없이 한 바퀴를 마쳐야 정산한다. [할당 wrapper](https://github.com/CUBRID/CUBRID/blob/d52b1889e907abcf84190ec504dde3bc93de260d/src/storage/oos_file.cpp#L2012-L2026)는 interrupt 외 sweep 오류를 경고 후 흡수하고 할당을 진행한다. 오류 시 힌트를 보존하는 것과 현재 성장 방지를 성공하는 것도 다르다.

Chain의 마지막 chunk와 head가 사라져 intent가 완료되어도, page fast path가 READ 경합이나 오류로 실패하면 빈 페이지는 남을 수 있다. 이미 head가 없는 intent를 다시 실행하는 것만으로 그 페이지를 재발견한다고 가정할 수 없다. 반대로 sweep은 빈 페이지를 찾을 뿐, chunk가 남은 실패한 chain을 끝까지 지워 주지 않는다. 따라서 두 메커니즘은 서로 대체하지 않는다.

현재 [vacuum wrapper](https://github.com/CUBRID/CUBRID/blob/d52b1889e907abcf84190ec504dde3bc93de260d/src/query/vacuum_oos.cpp#L225-L246)는 후보 목록을 지우고, [vacuum 호출](https://github.com/CUBRID/CUBRID/blob/d52b1889e907abcf84190ec504dde3bc93de260d/src/query/vacuum.c#L1978-L1987)은 home page unfix 뒤 한 번 실행한다. 후속 sweep은 해당 파일의 새 페이지 할당에서 시작한다. 추가 쓰기가 없으면 그 호출도 없다. Gate 제거 뒤 fast path가 모두 성공한다는 전제는 READ 경합·오류·후보 유실·INSERT undo에 적용할 수 없다.

구현은 chunk intent를 끝내는 시점과 page 반환 재시도를 넘기는 시점을 명시해야 한다. 재시도 큐·재방문 작업 같은 구체적 수단은 Work742·761에서 정하되, 메모리 힌트가 사라져도 빈 페이지가 발견되고 추가 쓰기 없이 결국 반환된다는 근거가 필요하다. 기존 코드의 “idle files are never shrunk” 주석은 정규 명세의 eventual-return 요구를 없애지 않는다. 명세에 없는 20초 보장을 만들거나 timeout만 늘려 PASS로 바꾸지도 않는다.

## Gate 제거 전 확인할 undo 목적지

| 경로 | 현재 동작 | Target에서 필요한 안전 근거 |
| --- | --- | --- |
| `RVOOS_DELETE` undo | `oos_rv_redo_insert`가 `spage_insert_for_recovery`로 chunk를 원래 slot에 복원한다. | REMOVE·UPDATE cleanup·eager 전체에서 삭제 undo를 없앤다. 일부 호출만 redo-only로 바꿔서는 안 된다. 현재 gate를 제거할 수 없는 직접 근거다. |
| `RVOOS_INSERT` undo | `oos_rv_redo_delete`로 chunk를 지우고 CLR을 남긴다. | 재삽입 목적지를 만들지는 않는다. 그러나 빈 페이지 생성·힌트·callback의 WRITE latch가 남으므로 회수 검증은 필요하다. 이미 끝낸 undo의 CLR redo를 사용자 undo와 혼동하지 않는다. |
| 새 OOS page 초기화·할당 | 초기화의 `RVPGBUF_NEW_PAGE` undo는 page type을 바꾼다. | [할당 sysop](https://github.com/CUBRID/CUBRID/blob/d52b1889e907abcf84190ec504dde3bc93de260d/src/storage/oos_file.cpp#L2984-L3002)은 commit 뒤에도 WRITE latch를 유지해 INSERT에 넘긴다. 할당 중 아직 빈 페이지가 회수되거나 초기화 undo와 겹치지 않도록 이 경계를 유지한다. |
| Heap 물리 undo·stub 복원 | Heap 레코드와 forward slot undo는 남는다. | REMOVE의 heap 제거와 intent가 같은 sysop이어야 한다. Abort하면 intent를 버려 복원된 stub의 chain이 살아 있어야 한다. Forward slot 보호는 CBRD-27858의 별도 의무다. |
| UPDATE·savepoint·statement rollback | 현재 forward-walk가 undo image를 삭제 근거로 삼는다. | A' postpone 취소와 forward-walk 제거로 살아 있는 chain을 보존한다. UPDATE INSERT undo가 지우는 새 chain과 이전 chain을 구분한다. |
| 재시작·오래된 snapshot | Redo와 undo, reader 수명이 함께 작용한다. | 물리 LSA gate를 없애도 WAL redo 순서·postpone 재실행·MVCC 안전시점은 유지한다. 모든 recovery fix를 임의의 page 재사용에 안전하다고 일반화하지 않는다. |

현재 OOS의 직접 재삽입 지점은 [oos_rv_redo_insert](https://github.com/CUBRID/CUBRID/blob/d52b1889e907abcf84190ec504dde3bc93de260d/src/storage/oos_file.cpp#L3677-L3704)이며, 복구 표는 이 함수를 INSERT redo와 DELETE undo에 함께 쓴다. 새 페이지 undo의 [실제 구현](https://github.com/CUBRID/CUBRID/blob/d52b1889e907abcf84190ec504dde3bc93de260d/src/storage/page_buffer.c#L15272-L15276)도 확인했다. Heap undo가 OOS page에 직접 chunk를 복원하는 것은 아니지만, 복원한 heap stub이 살아 있는 chain을 요구하므로 finality 조건에서 제외할 수 없다.

Gate 없이도 INSERT page 선택과 회수의 경합을 막는 header latch·두 단계 emptiness 재검사·WRITE fix·sticky header 제외·deallocation commit 순서가 남아야 한다. [기존 gate 모델](../oos/reclaim-decisions.md#결정-4-d3에서-lsa-reclaim-gate가-필요한가)은 chunk 삭제 undo가 없을 때의 안전성을 보였을 뿐, 이 동기화나 bestspace 경합까지 증명하지 않았다. [엔진 사실 보고서](../oos/reclaim-engine-facts.md)는 더 오래된 `dcbf09e4f`의 소스 분석이며 이번 실행 증거가 아니다.

## 별도 승인 뒤 실행할 최소 DB 범위

지금은 Work742의 target 구현과 Work747의 사양 정합화를 우선한다. 이후 revision·matching 설치본·설정을 고정하고 아래 범위를 한 승인 요청에 묶는 것을 권한다. 기존 Work790의 팀장 승인 전에는 서버 시작·DB 생성·SQL·통합 복구 테스트를 실행하지 않는다. 이 보고서는 승인 요청을 다른 사람에게 발송하지 않는다.

| 검증 묶음 | 필요한 관측과 판정 |
| --- | --- |
| INSERT abort·READ 경합 | 같은 VFID·VPID·sweep ID로 마지막 chunk 삭제, hint 알림, 시작 건수 snapshot, 1차 READ 결과, WRITE 해제, lap 정산과 다음 호출을 연결한다. 경합이 끝난 뒤 검사·반환 의무가 살아 있어야 한다. WRITE 실패·경합 없는 rollback·mid-lap 삭제·boot rule을 대조한다. |
| 확정·rollback·snapshot·복구 | REMOVE sysop abort, eager transaction abort, UPDATE statement·savepoint rollback과 commit, 오래된 snapshot 종료, postpone 중 오류·crash를 검사한다. 각 chunk 삭제 단계 뒤 동시 INSERT·page 재사용에도 생존 값이 보존되고 intent가 남은 chunk를 끝까지 지워야 한다. Work742 검증과 중복 실행하지 않는다. |
| Page 반환과 쓰기 없는 대기 | Chain 삭제 완료와 file-manager 반환을 따로 기록한다. 후보 처리 실패·힌트 유실·재시작 후에도 추가 OOS 할당 없이 반환되는 경로를 입증한다. Timeout은 시험 한도이며 요구사항 수치가 아니다. |
| 성장 압력 | Bestspace 재발견을 허용한 정상 경로와 해당 재발견이 없는 조건을 비교한다. 데이터 page 할당, 빈 VPID 반환·재할당, 실제 `disk_reserve_sectors`, user page·sector 수, 생존 값 전체를 연결한다. 검사 생략만 보고 불필요한 sector 증가를 확정하지 않는다. 메타데이터 재귀 예약은 CBRD-27945의 별도 조건으로 다룬다. |
| 기존 회귀 비교 | `churn_abort_retry`, `churn_insert_delete`, `churn_insert_update_delete`, `churn_restart`, `snapshots_reclaim`의 원래 FAIL을 보존하고 새 기준의 결과와 나란히 기록한다. 과거 `1|1312`, `1|1313`의 관측에 최종 enum을 소급해 채워 넣지 않는다. |

순수 모델·추출 함수 검사는 승인 전에도 가능하지만 위 DB 관측을 대신하지 않는다. ADR-0008의 성능 채택 조건인 로그량·vacuum 비용·churn 크기와 INSERT·UPDATE 지연도 Work742에 남는다. 이번에는 성능을 측정하거나 개선을 주장하지 않았다.

## Work816의 완료 범위

Work816은 조사 필요성과 범위 판정까지 완료한다. Work761에는 이 결론과 보고서를 연결하며, 기존 FAIL과 실제 DB 승인 조건을 유지한다. Work742는 구현·동기화·오류 재시도·성능 검증, Work747은 승인 문안 정합화, Work790은 별도 native 재현 승인 추적을 계속 맡는다. 이번 결론만으로 이 항목이나 CBRD-27925를 완료 처리하지 않는다.

이번 checkout에는 `PRESET_MODE`, build 디렉터리와 `compile_commands.json`이 준비되지 않았다. 빌드·LSP를 사용하는 구현 검증은 하지 않았으며, 직접 소스·고정 revision·함수 본문 비교·순수 모델을 근거로 판단했다. 이전 native 원본·모델·추출 실행 자료는 변경하지 않았다.

문서 두 파일의 Markdown 소스 검사, 상대 링크 7개와 대상 heading, README 색인 항목을 확인했다. 순수 모델과 `git diff --check`도 통과했다. `check_gate_scope.py`는 이 판정의 재검증에 필요한 지원 파일로 보존한다. 원시 로그나 생성한 소스 사본은 커밋하지 않는다.
