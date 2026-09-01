# PR #7617 전체 범위 코드 리뷰 보고서

**PR:** [CUBRID/cubrid#7617](https://github.com/CUBRID/cubrid/pull/7617)

**제목:** [CBRD-26786] Reclaim empty OOS pages in vacuum via file_dealloc

**리뷰 범위:** `140fc5ef6...bd0766dbb` (PR 13 commits, 14 files)

**원격 PR HEAD:** `bd0766dbb8e7e1d5f1f6f87824aa8819233991e9`

**리뷰 일시:** 2026-09-01

> **TL;DR:** 전체 diff를 hunk 단위로 다시 검토해 실제 문제 3건을 찾았고 모두 로컬 worktree에 수정했습니다. 성장 sweep은 전체 page vector 대신 sector bitmap을 직접 순회하도록 바꿨고 multi-sector cursor-wrap 회귀 테스트를 추가했습니다. 다만 이 수정은 아직 PR 원격 HEAD에 commit/push되지 않았습니다. observability counter와 현재 SQL baseline 수정은 사용자 결정으로 건너뛰었으며, legacy numerable OOS 호환 guard는 미출시 feature-branch 정책상 범위 밖입니다.

## Review Outcome

| 구분 | 결과 |
|---|---|
| 원격 PR HEAD | **CHANGES REQUESTED** — 아래 3개 수정이 아직 원격에 없음 |
| 로컬 수정 상태 | 3 findings fixed, 회귀 테스트 추가, OOS unit tests 27/27 통과 |
| Standards | 구체적 수정 1건 적용; AI-generated라는 포괄적 판단 근거는 없음 |
| Spec | interrupt 전달 및 growth-sweep 비용/순서 문제 수정 |
| CI | medium 통과, SQL 14 failures, shell 미실행/미제공; 별도 [CI 보고서](./ci_analysis_report_bd0766d_codex.md) 참고 |

## Applied Findings

### 1. Test-only header mutation lacked logging/dirty bookkeeping

**위치:** `unit_tests/oos/test_oos_growth_sweep.cpp`, `simulate_hint_loss`

테스트 helper가 fixed OOS header page를 직접 변경하면서 log-skip과 dirty 표시를 하지 않았습니다. buffer가 flush되거나 재사용되는 조건에서 테스트 상태가 보존된다는 보장이 없고, 테스트가 실제 엔진 page mutation convention과 달랐습니다.

**로컬 수정:** `LOG_DATA_ADDR`를 구성해 `log_skip_logging`을 호출하고 `pgbuf_set_dirty(..., DONT_FREE)`로 변경 내용을 등록했습니다.

### 2. Shutdown interruption was swallowed after forward-walk reclaim

**위치:** `src/query/vacuum_oos.cpp`, `src/query/vacuum_oos.hpp`, `src/query/vacuum.c`

`vacuum_forward_walk_oos_delete_atomic`은 reclaim가 `ER_INTERRUPTED`를 반환해도 오류를 지웠고, 상위 forward walk helper는 `void`라 vacuum의 표준 shutdown 경로로 전달할 수 없었습니다. 일반 reclaim 실패를 best-effort로 처리하는 정책과 shutdown 요청을 삼키는 것은 별개입니다.

**로컬 수정:** 일반 cleanup 오류는 기존처럼 log + clear하여 vacuum block을 계속 처리하되, `ER_INTERRUPTED`만 `vacuum_process_log_block`까지 반환합니다. 두 call site는 `vacuum_check_shutdown_interruption`을 거쳐 기존 `end` 경로로 종료합니다. post-commit reclaim이므로 이미 commit된 OOS delete는 유지되고, 비워진 page는 다음 growth sweep에서 회수됩니다.

### 3. Growth sweep expanded every allocated page into a vector and sorted it

**위치:** `src/storage/oos_file.cpp`, `oos_reclaim_sweep_step`

기존 hunk는 file-manager sector bitmap을 모든 `VPID`로 확장한 뒤 `std::vector<VPID>`를 정렬했습니다. OOS 파일이 커질수록 growth gate에서 `O(P)` 추가 메모리와 `O(P log P)` 정렬 비용을 지불하며, page 수 자체가 allocation-failure 표면이 됐습니다.

**로컬 수정:** `FILE_FTAB_COLLECTOR`의 sector snapshot을 직접 사용합니다. sector descriptor만 `disk_compare_vsids`로 정렬하고 각 `page_bitmap`의 set bit를 두 구간으로 순회합니다.

1. cursor보다 큰 VPID
2. wrap 후 cursor 이하 VPID

따라서 기존 sorted-vector의 원형 순서를 그대로 유지하면서 비용을 `O(S)` 메모리와 `O(S log S)` 정렬로 줄였습니다. 여기서 한 sector는 64 page bit를 보유하므로 일반적으로 `S ≈ P/64`입니다. 같은 직접 bitmap 순회 관례는 file manager의 sector page mapping/deallocation 경로에서도 사용됩니다.

**회귀 테스트:** `SweepCursorWrapsAcrossSectorBoundary`는 66개의 page-filling record로 두 sector를 만들고, high-page reclaim으로 cursor를 끝쪽에 둔 다음 다른 sector의 low page만 비웁니다. 다음 insert가 sector 끝에서 wrap하여 low page를 재사용하고 파일 page 수가 증가하지 않는지 검증합니다.

## Hunk-by-Hunk Coverage

| 파일/변경 묶음 | 검토 결과 |
|---|---|
| `src/query/vacuum.c` — touched-page batch, forward-walk call sites | interrupt propagation 수정 적용; 나머지 batch/latch 경계는 스펙과 일치 |
| `src/query/vacuum_oos.cpp/.hpp` — atomic delete/reclaim API | 일반 오류 best-effort와 shutdown interrupt를 분리 |
| `src/storage/file_manager.c/.h` — data-sector snapshot API | OOS가 file table internals를 복제하지 않고 narrow interface를 사용; 문제 없음 |
| `src/storage/heap_oos.cpp` — reclaim 금지 설명 | user transaction abort/undo 계약과 일치; 실행 변경 없음 |
| `src/storage/oos_file.cpp` — state, two-phase reclaim, growth gate, stale hints | page-vector 성능 문제 수정; latch/ownership/reclaim-debt 경로 재검증 |
| `unit_tests/oos/CMakeLists.txt` | 기존 GTest OOS harness 등록 방식과 일치 |
| `test_oos_bestspace.cpp` | stale bestspace coverage 적절 |
| `test_oos_growth_sweep.cpp` | helper bookkeeping 수정, multi-sector wrap test 추가 |
| `test_oos_remove_file*.cpp` | SA/server fixture 중복은 존재하지만 harness lifecycle이 달라 blocking 아님 |
| `test_oos_vacuum_server.cpp` | vacuum reclaim/LSA gate 시나리오가 구현 계약과 일치 |

## Explicitly Skipped

### Observability counter — SKIPPED BY REQUEST

ADR의 “deallocated page를 만나 sync가 건너뛴 횟수” 관측 항목과 달리 현재 구현은 local `skipped_deallocated` 값과 debug trace만 사용하며 release build에서는 지속 counter가 없습니다. correctness나 reclaim 진행성 문제는 아니고 운영 진단 범위입니다.

사용자 결정에 따라 counter 추가를 **명시적으로 건너뛰었습니다**. 미해결 correctness defect로 세지 않으며, 코드에서 실수로 빠진 것으로도 기록하지 않습니다.

### Exact-head SQL baseline fix — SKIPPED BY REQUEST

정확한 HEAD CI에서 SQL 14건이 실패했습니다. 2건은 다수 LOB locator를 포함한 18,036-byte row가 OOS demotion 후에도 최대 16,236 bytes를 넘는 feature-branch 호환 문제이고, 나머지 12건은 error code, numeric rendering, query-plan trace baseline 차이입니다.

이 PR은 oversized-row demotion, arithmetic, aggregate typing/rendering, optimizer/parallel execution을 변경하지 않습니다. 사용자 결정에 따라 이 PR에서 source/answer fix를 하지 않고 feature-branch baseline 후속 작업으로 기록합니다. 이는 실패를 정상으로 승인한다는 뜻이 아니며 SQL CI는 여전히 red입니다.

## Out of Scope

### Legacy numerable OOS files

호환 guard는 추가하지 않았습니다. 현재 OOS 생성 경로는 항상 non-numerable이고 OOS는 아직 출시되지 않은 feature-branch 기능입니다. 이 patch 이전에 실험용 바이너리로 만든 DB는 재생성한다는 프로젝트 정책을 사용자와 확인했습니다. 따라서 legacy file-format 분기는 오히려 도달 불가능한 정책을 숨기고 유지보수 표면만 넓힙니다.

## Withdrawn or Suppressed Concerns

- **`std::vector`와 C-style error model은 양립 불가능하다:** 철회. `.c` 파일도 C++17로 컴파일되고, engine 경계에서 `std::bad_alloc`을 CUBRID error code로 번역하는 기존 패턴이 있습니다. 실제 문제는 예외 사용 자체가 아니라 page 수에 비례한 vector materialization 비용이었습니다.
- **`vacuum.c`의 method call은 무조건 INDENT guard가 필요하다:** 철회. 해당 member-call 형태만으로 GNU indent 규칙 위반을 입증할 수 없습니다.
- **GTest 사용이 convention 위반이다:** 철회. OOS unit-test module의 기존 framework가 GTest입니다.
- **Latch-order deadlock / unbounded condition wait:** 도달 가능한 교착 경로를 입증하지 못했습니다. single-flight scope-exit broadcast와 conditional page latch 경로를 확인해 finding으로 유지하지 않습니다.
- **SA/server test duplication:** 유지보수상 중복이지만 fixture lifecycle이 달라 현재 PR의 correctness/standards blocker로 보지 않습니다.

## Verification

- `git diff --check`: 통과
- local debug build 및 unit-test build: 통과
- configured OOS unit tests: **27/27 passed**, 0 failures, 103.72 seconds
- `OosGrowthSweepTest.SweepCursorWrapsAcrossSectorBoundary`: 통과
- exact remote-head CI:
  - release/debug/download builds: 통과
  - `test_medium`: 975/975 통과
  - `test_sql`: 17,443/17,457 통과, 14 failures
  - `test_shell`: exact-head result 없음

## Decision and Next Boundary

원격 PR HEAD `bd0766dbb` 자체에는 이번 리뷰 수정이 없으므로 현재 판정은 **CHANGES REQUESTED**입니다. 로컬 수정은 build와 OOS unit tests를 통과했으며, 다음 source-side 단계는 이 5개 파일을 검토해 commit/push한 뒤 exact-head CI를 다시 수집하는 것입니다.

이번 요청의 publication 범위에서는 source branch를 commit/push하지 않습니다. 이 문서와 CI 분석 보고서만 `my-cubrid-docs`에 게시하고 PR에는 상태를 오해하지 않도록 “local fixes not yet landed”를 명시합니다.
