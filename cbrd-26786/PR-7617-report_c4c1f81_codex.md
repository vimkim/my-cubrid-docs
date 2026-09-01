# PR #7617 코드 리뷰 보고서

**PR:** [CUBRID/cubrid#7617](https://github.com/CUBRID/cubrid/pull/7617)
**제목:** [CBRD-26786] Reclaim empty OOS pages in vacuum via file_dealloc
**작성자:** vimkim
**HEAD SHA:** `c4c1f816d77a34068cd702b0b2a3f6296c692914`
**리뷰 일시:** 2026-09-01

> **TL;DR** (Blocking): `PAGE_OOS` 타입만 확인하는 stale hint 경로는 다른 OOS 파일로 재할당된 페이지에 쓰기를 허용할 수 있습니다. 또한 조건부 latch 실패로 건너뛴 빈 페이지의 회수 debt를 full lap 정산이 지우며, 최종 커밋은 legacy numerable OOS 파일의 회수 금지 guard도 제거했습니다.

## Summary

- **변경 요약:** vacuum fast path, LSA reclaim gate, single-flight 성장 게이트 sweep을 통해 빈 OOS 데이터 페이지를 `file_dealloc` 로 반환합니다.
- **판정:** 데이터 소유권 및 파일 메타데이터 정합성 위험 2건과 회수 불변식 위반 1건이 남아 있어 `REJECT` 입니다.
- **예외 처리:** 로컬 `try/catch` 가 C++ 예외를 CUBRID 오류 코드로 변환하고 엔진 경계 밖으로 전파하지 않는 경로는 지적에서 제외했습니다.
- **검증:** `debug_gcc` 빌드와 구성된 OOS 테스트 27개가 모두 통과했습니다(0 failures, 111.49초). 아래 race, legacy, 대규모 파일 시나리오는 이 테스트 집합이 검증하지 않습니다.

---

## Findings

### Blocking (must fix)

- `src/storage/oos_file.cpp:681-699` -- 회수된 VPID가 다른 OOS 파일의 데이터 페이지로 재할당되면 page type은 계속 `PAGE_OOS` 이므로 현재 검사를 통과합니다. 비영속 `best[]` 또는 hash hint가 stale인 동안 `oos_find_best_page` 가 그 페이지를 원래 VFID의 후보로 반환해 다른 파일에 OOS chunk record를 삽입할 수 있습니다. 후보 page가 요청한 VFID에 실제로 속하는지, stale을 정상 결과로 처리하는 non-asserting file-membership API로 확인한 뒤에만 사용해야 합니다.

- `src/storage/oos_file.cpp:1452-1471,1755-1768,1901-1929` -- phase 1에서 빈 페이지를 확인한 뒤 phase 2의 조건부 WRITE fix가 일시적인 reader와 경합하면 결과가 `OOS_RECLAIM_SKIPPED` 로 남습니다. full lap은 `DEFERRED` 만 debt로 되돌리고 `pending_deletes` 를 정산하므로, reader가 빠진 뒤에도 다음 무관한 delete 또는 재시작 전까지 그 빈 페이지를 다시 찾지 않습니다. transient busy를 별도 retry/deferred 결과로 분류해 lap 정산 후에도 성장 게이트를 armed 상태로 유지해야 합니다.

- `src/storage/oos_file.cpp:1619`, `src/storage/file_manager.c:185-188,6211-6215` -- 최종 커밋 `c4c1f816d` 가 `file_is_numerable` 과 batch/sweep의 legacy numerable guard를 제거했습니다. `FILE_TYPE_CAN_BE_NUMERABLE` 에 `FILE_OOS` 가 없어서 `file_dealloc(..., FILE_OOS)` 는 numerable user-page table을 갱신하지 않고 sector bitmap만 해제하며, 이후 `file_numerable_find_nth` 가 이미 회수된 VPID를 반환할 수 있습니다. ADR-0001 계약대로 per-file 검사를 복원하고 legacy numerable OOS 파일에서는 모든 page reclaim을 건너뛰어야 합니다.

### Non-blocking (should consider)

- `src/storage/oos_file.cpp:1877-1890` -- cursor가 있어도 매 sweep step마다 전체 allocation bitmap을 `vector` 로 복사하고 전체 정렬한 뒤 한 페이지만 회수합니다. N-page delete burst를 N번 재사용하면 O(N²) 준비 비용과 전체 파일 지연이 INSERT 경로에 반복됩니다. bitmap cursor 또는 bounded chunk iterator로 실제 열거 비용도 resume해야 합니다.

- `src/storage/oos_file.cpp:1815-1831` -- concurrent grower의 `pthread_cond_wait` 는 CUBRID interrupt predicate나 timed wake-up이 없습니다. query cancel 또는 shutdown은 active sweep이 broadcast할 때까지 반응하지 못할 수 있으므로 timed wait loop에서 interrupt를 확인하고 `ER_INTERRUPTED` 를 반환해야 합니다.

- `unit_tests/oos/test_oos_growth_sweep.cpp:60-84` -- `simulate_hint_loss` 가 WRITE-fix한 `OOS_HDR_STATS` 를 변경한 뒤 dirty로 표시하지 않습니다. buffer eviction/flush 타이밍에 따라 변경이 보존되지 않아 테스트 의도가 흔들릴 수 있으므로 `pgbuf_set_dirty` 후 unfix해야 합니다.

- `unit_tests/oos/`, `tests/` -- 다른 OOS 파일로 VPID가 재할당되는 stale hint, phase 2 conditional-latch miss, legacy numerable 파일, 대규모 delete burst, waiter cancel을 재현하는 회귀 테스트가 없습니다. JIRA에 남은 10K churn, concurrent DELETE/vacuum/INSERT, crash-injection CTP 검증도 완료해야 합니다.

- `src/storage/oos_file.cpp:825-989` -- ADR-0001이 요구한 "sync skipped a deallocated page" 관측값은 함수 지역 변수와 trace로만 존재합니다. release 운영에서 누적 경향을 확인할 수 있도록 기존 debug/performance counter 체계에 process-lifetime 누적 counter를 추가해야 합니다.

## Existing Review Reconciliation

- 이전 B1 답변은 재할당된 **non-OOS** 페이지를 `PAGE_OOS` 검사로 막았습니다. 이번 blocking 항목은 재할당 대상도 `PAGE_OOS` 인 cross-file 경우라서 기존 답변이 닫지 못한 별도 소유권 race입니다.
- 이전 concurrent-grower blocker는 기다림으로 해결됐지만, 새 wait 경로의 cancel/shutdown 응답성은 별도 non-blocking 항목입니다.
- 예외 관련 Greptile 지적은 답글 후 bot이 철회했고, 이번 판정에서도 CUBRID 오류로 변환되어 전파되지 않는 로컬 `try/catch` 를 문제로 보지 않았습니다.

## Recommended Fix Order

1. stale candidate의 VFID 소유권 검증과 legacy numerable guard를 먼저 복원해 cross-file 및 file-table 손상 가능성을 차단합니다.
2. reclaim 결과에 transient retry 상태를 추가하고 lap 정산이 그 수만큼 debt를 유지하도록 고칩니다.
3. sector-bitmap 열거를 cursor-resumable하게 만들고 condition wait를 interrupt-aware하게 바꿉니다.
4. dirty 처리, race/legacy/CTP 테스트, skipped-deallocated counter를 추가한 뒤 동일한 27개 OOS 테스트와 신규 테스트를 다시 실행합니다.

## JIRA Context

CBRD-26786의 규범은 모든 완전히 빈 OOS 데이터 페이지가 결국 file manager로 반환되고, 지금 안전하게 회수 가능한 빈 페이지가 없을 때만 새 sector를 예약하는 것입니다. ADR-0001은 신규 OOS 파일을 non-numerable로 만들되 legacy numerable 파일의 reclaim은 건너뛰고, bitmap snapshot staleness를 관측 가능하게 유지하도록 명시합니다. 현재 HEAD는 이 세 계약을 모두 만족하지 못합니다.
