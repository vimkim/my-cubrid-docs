# CBRD-28379 검증 보고서: 거절된 조건부 latch 요청이 남기는 `waiter_exists`

- 이슈: [CBRD-28379](https://jira.cubrid.org/browse/CBRD-28379) (관련: CBRD-28378, CBRD-28163, CBRD-26425)
- 작성일: 2026-11-25 (Asia/Seoul)
- 기준 코드: `CUBRID/cubrid` `develop` `ca39c2c6a4` ([page_buffer.c](https://github.com/CUBRID/cubrid/blob/ca39c2c6a48df0bbc689c4d8b8d640113bb87d3e/src/storage/page_buffer.c))
- 수정 커밋: 브랜치 `CBRD-28379` 의 `5c213aaac66549e92f805d2ed643c8fbdbc57939` (아직 push하지 않음)
- 빌드: CMake preset `debug_gcc` (assert 활성), Linux, 80코어 공유 장비
- 독자: 이 PR의 리뷰어와, 나중에 page buffer latch 동작을 다시 볼 개발자

## 질문과 결론

질문: 조건부 latch 요청(`PGBUF_CONDITIONAL_LATCH`)이 거절되면 버퍼 프레임(BCB)이 어느 LRU 목록에도 속하지 않게 되는가? 그렇다면 어떻게 고치는가?

결론:

- 그렇다. 수정 전 `develop` 에서 재현했다. 단위 테스트 4개가 모두 실패했다. 동시 OOS INSERT 재현에서는 라운드마다 1024개 BCB 중 57–167개가 VOID 영역에 버려졌다.
- 수정 후에는 단위 테스트 4개가 모두 통과한다. 같은 재현 10라운드에서 버려진 BCB는 0개였다.
- 독립 리뷰는 차단 문제를 찾지 않았다.

남은 질문:

- release 빌드에서 버퍼가 고갈되어 멈추는 현상(이슈의 938/1024)은 이번에 다시 재현하지 않았다. debug 빌드에서는 버려지는 BCB는 매번 생겼지만, 멈출 만큼 쌓이지는 않았다.
- 새 fallback 경로(아래 수정 2)에 닿는 테스트는 없다.

## 원인 (기준 코드 `ca39c2c6a4`)

1. `pgbuf_latch_bcb_upon_fix ()` ([L6972](https://github.com/CUBRID/cubrid/blob/ca39c2c6a48df0bbc689c4d8b8d640113bb87d3e/src/storage/page_buffer.c#L6972))는 latch를 바로 줄 수 없을 때 CAS로 `waiter_exists = true` 를 기록한다. 조건부 요청도 같다.
   - Case 3: 비보유자의 요청 ([L7117-L7120](https://github.com/CUBRID/cubrid/blob/ca39c2c6a48df0bbc689c4d8b8d640113bb87d3e/src/storage/page_buffer.c#L7117-L7120)).
   - Sub-case 2-2: 다른 reader가 있을 때 READ 보유자가 WRITE로 승격을 요청한 경우 ([L7099-L7104](https://github.com/CUBRID/cubrid/blob/ca39c2c6a48df0bbc689c4d8b8d640113bb87d3e/src/storage/page_buffer.c#L7099-L7104)).
   - 조건부 요청은 이어서 대기열에 들어가지 않고 `ER_FAILED` 로 돌아간다. 이때 표시를 지우지 않는다.
2. `pgbuf_unlatch_bcb_upon_unfix ()` 는 `blocked_reader_writer = waiter_exists` 로 읽는다 ([L7357](https://github.com/CUBRID/cubrid/blob/ca39c2c6a48df0bbc689c4d8b8d640113bb87d3e/src/storage/page_buffer.c#L7357)). 마지막 unfix에서 이 값이 참이면 영역별 처리를 통째로 건너뛰고, 깨우기(`pgbuf_wakeup_reader_writer ()`)만 한다. 영역별 처리에는 VOID 영역 BCB를 LRU에 넣는 `pgbuf_unlatch_void_zone_bcb ()` 가 포함된다. 깨우기는 대기자가 없음을 확인하고 표시만 지운다.
3. 결과: 막 할당하거나 디스크에서 읽어 아직 VOID 영역에 있던 BCB가 latch 없이(fcnt 0), LRU 연결도 없이 남는다. flush daemon의 victim 후보 수집에도, 재사용 탐색에도 보이지 않는다.
4. 같은 표시는 READ로 잡힌 페이지에 대한 비보유자의 READ 요청도 막는다(Case 1). lock-free READ 경로(`pgbuf_lockfree_fix_ro`)도 꺼진다. CBRD-28163이 설명한 READ 차단과 같은 현상이다.
5. CBRD-26425 이전에는 unfix가 대기열을 직접 훑었다(`pgbuf_is_exist_blocked_reader_writer ()`). 대기열에 들어가지 않는 조건부 요청은 배치를 막지 않았다.

## 수정 내용

### 수정 1: 조건부 요청은 `waiter_exists` 를 세우지 않는다

`pgbuf_latch_bcb_upon_fix ()` 의 Case 3에서는 `condition == PGBUF_UNCONDITIONAL_LATCH` 일 때만 표시를 세운다. Sub-case 2-2의 조건부 분기에서는 표시를 세우는 줄을 지웠다.

이 변경이 맞는 이유:

- 대기열에 들어가는 요청은 무조건 요청뿐이다. `pgbuf_block_bcb ()` 의 assert(READ/WRITE 대기자는 들어가기 전에 표시를 세움)는 두 무조건 경로에서 그대로 성립한다.
- 거절된 조건부 요청에서는 `new_impl == old_impl` 이다. 따라서 CAS는 아무것도 쓰지 않는다. 동시에 일어난 lock-free `fcnt` 변경으로 CAS가 실패하면 루프가 다시 계산할 뿐이다.
- `waiter_exists` 의 모든 변경은 여전히 BCB mutex 아래에서 일어난다. lock-free 경로는 표시를 읽기만 한다. 이번 변경으로 lock-free READ가 허용되는 경우가 늘어나지만, 모두 실제 대기자가 없는 경우다.
- 조건부 READ가 실제 대기자 뒤에서 거절되는 경우(Case 1)는 원래 표시를 바꾸지 않았다.

### 수정 2: 대기자가 모두 포기했으면 VOID BCB를 배치한다

`pgbuf_unlatch_bcb_upon_unfix ()` 에서 영역 처리를 대기자 때문에 건너뛰었는데 깨우기 뒤에도 latch가 `PGBUF_NO_LATCH` 이면 BCB를 배치한다. 이것은 아무 대기자도 latch를 받지 못한 경우다. 이때 BCB가 VOID 영역이면, 대기자 없는 unfix와 같은 방식으로 `pgbuf_unlatch_void_zone_bcb ()` 를 호출한다.

이 경로가 생기는 경우:

- 대기자가 latch 시간 초과나 interrupt로 포기할 때가 있다. 대기자는 `pgbuf_timed_sleep ()` 에서 thread entry lock만 잡고 `request_latch_mode = PGBUF_NO_LATCH` 를 쓴다. 그다음 BCB mutex를 기다린다.
- 그 사이에 보유자가 unfix하면 보유자는 표시를 참으로 읽는다. 깨우기는 그 대기자를 대기열에서 빼지만, latch는 누구에게도 넘어가지 않는다.
- 대기 시간이 0인 스레드(트랜잭션 descriptor가 없는 스레드 포함)는 곧바로 시간 초과되므로 이 창이 더 자주 열린다.
- CBRD-26425 이전의 대기열 검사에도 같은 창이 있었다.

이 처리가 안전한 이유:

- BCB 상태가 대기자 없는 경로와 같다. mutex를 쥐고 있고, fcnt는 0이고, latch는 `NO_LATCH` 이다.
- 두 번 배치하지 않는다. 영역 처리를 건너뛴 경우에만 실행된다. `MOVE_TO_LRU_BOTTOM` 경로를 탔으면 BCB는 이미 VOID 영역을 벗어났다.
- 이미 LRU에 있는 BCB는 예전처럼 boost만 빠진다.

## 검증

### 단위 테스트 `unit_tests/oos/test_pgbuf_conditional_latch_server.cpp`

- 서버를 프로세스 안에서 부팅한다. OOS 서버 테스트의 `ServerModeEnv` 와 `OOS_DB` fixture를 재사용한다.
- "다른 스레드"의 요청은 worker 1개짜리 pool의 task로 실행한다.

| 케이스 | 확인 내용 | 기준(수정 전) | 수정 후 |
| --- | --- | --- | --- |
| `RefusedWriteRequestLetsNewPageEnterLru` | 새 페이지 8개를 WRITE로 쥔 채 다른 스레드의 조건부 WRITE가 거절된 뒤 unfix → LRU 수가 8 이상 늘어남 | 실패 (52 → 52) | 통과 |
| `RefusedReadRequestLetsNewPageEnterLru` | 같은 조건에서 조건부 READ가 거절됨 | 실패 (54 → 54) | 통과 |
| `RefusedWriteRequestDoesNotBlockReaders` | READ 보유 중 조건부 WRITE가 거절된 뒤, 세 번째 스레드의 조건부 READ가 허용됨 | 실패 (`read_granted` false) | 통과 |
| `RefusedPromotionDoesNotBlockReaders` | 두 reader 중 하나의 조건부 승격이 거절된 뒤, 세 번째 스레드의 READ가 허용됨 | 실패 | 통과 |

- 수정 후 3회 연속 통과했다. 실행 명령: `ctest -R '^test_pgbuf_conditional_latch_server$'`.
- 검증 함정: 작업 환경의 `LD_LIBRARY_PATH` 가 설치 경로의 `libcubrid` 를 RUNPATH보다 먼저 찾는다. 그래서 기준 소스로 다시 빌드한 라이브러리를 시험할 때는 빌드 트리의 `cubrid/` 를 `LD_LIBRARY_PATH` 맨 앞에 두었다. 첫 기준 실행 때는 설치본 자체가 기준 빌드였으므로 이 문제가 없었다.

### 동시 OOS INSERT 재현 (CBRD-28378의 작은 재현)

- 설정: `data_buffer_size=16m`, `enable_string_compression=n`. 세션 10개가 `repeat('y', 204800)` 값을 40건씩 INSERT한다(총 400행).
- 각 라운드 뒤 gdb로 `pgbuf_Pool.BCB_table` 을 훑어 VOID 영역 BCB를 셌다. 셀 때 fcnt 0과 `prev_BCB`/`next_BCB` NULL 조건을 함께 보았다.

| 빌드 | 라운드 | 행 | 시간(초) | 버려진 VOID BCB (1024 중) |
| --- | --- | --- | --- | --- |
| 기준 `ca39c2c6a4` | 5 | 각 400 | 1.77–2.01 | 167, 103, 93, 146, 57 |
| 수정(첫 빌드) | 5 | 각 400 | 2.33–5.02 | 0, 0, 0, 0, 0 |
| 수정 `5c213aaac6` | 5 | 각 400 | 0.87–2.28 | 0, 0, 0, 0, 0 |

- 시간 차이는 장비 부하 때문이다. 수정 첫 빌드 측정 때 load average는 약 229(80코어)였고, 최종 측정 때는 약 13이었다.
- 모든 수정 라운드에서 `lru=1024` 였다. 서버 오류 로그에 ERROR, FATAL, assert는 없었다.

### 회귀 테스트와 정적 검사

- 설정된 ctest 전체: 75개 중 74개가 통과했다.
  - `test_oos_real_vacuum_latch_timeout_retry` 1개가 60초 시간 초과로 실패했다. load average 약 229일 때였다.
  - 부하가 낮아진 뒤 3회 재실행했고 모두 통과했다(16–17초).
  - 이 테스트는 2초 latch timeout과 fault injection으로 시간에 민감하다. 부하로 인한 flake로 판단하지만, 기준 빌드에서 같은 부하로 비교하지는 않았다.
- `cubrid-static-check ca39c2c6a4..`: cppcheck, clang-tidy, 중복 코드 모두 새 항목 0개였다. 복잡도는 `pgbuf_latch_bcb_upon_fix` CCN +1, `pgbuf_unlatch_bcb_upon_unfix` CCN +4로 경고 기준 아래였다.
- GNU indent 2.2.11 `-l120 -lc120`: `page_buffer.c` 는 바이트 단위로 같았다. 테스트 파일은 CI의 astyle 옵션에서 같았다. `git diff --check` 도 깨끗했다.

## 독립 리뷰 반영

리뷰 원문: [review-findings.md](review-findings.md) (커밋 `11b40319ee` 기준). 결론은 "차단 문제 없음"이었다.

| 항목 | 처리 |
| --- | --- |
| F1 LRU 수를 정확히 비교하면 배경 스레드 때문에 불안정할 수 있음 | 페이지 8개를 묶어 `>= before + 8` 로 비교하고, 실패하면 수치를 출력한다. 버그가 있으면 증가량은 0이다 |
| F2 fallback에 닿는 테스트 없음 | 대기자를 `pgbuf_timed_sleep ()` 안에서 멈출 hook이 없다. 테스트 머리 주석과 커밋 설명에 이 한계를 적었다 |
| F3 fallback에서 `pgbuf_pg_unfix_cnt` 를 세지 않음 | 그대로 둔다. 통계만 다르고, 예전의 대기자 경로와 같다 |
| F4 worker callback이 예외로 끝나면 대기가 걸림 | `scope_exit` 로 `tran_index` 복구와 promise 완료를 항상 수행한다 |
| F5 page buffer 테스트가 OOS 디렉터리에 있음 | 그대로 둔다. 서버 부팅과 fixture를 재사용하기 위해서이고, CMake 주석에 이유를 적었다 |
| F6 주석 문장 | 고쳤다 |
| F7 `pgbuf_discard_page` 가 flush 대기 전에 `set_waiter_exists (true)` 호출 ([L3654](https://github.com/CUBRID/cubrid/blob/ca39c2c6a48df0bbc689c4d8b8d640113bb87d3e/src/storage/page_buffer.c#L3654)) | 이번 변경과 관계없는 기존 코드다. 별도 이슈로 다룬다 |

## 한계와 후속 작업

- release 빌드의 버퍼 고갈과 멈춤은 다시 재현하지 않았다. 원인인 VOID BCB 누수는 debug 빌드에서 재현했고, 수정으로 사라졌다.
- 수정 2(fallback)는 코드 읽기와 리뷰로만 검증했다.
- OOS 쪽에서 채우기 전의 새 페이지를 bestspace에 알리는 동작은 CBRD-28378이 따로 다룬다. 이번 변경은 `src/storage/oos_file.cpp` 를 바꾸지 않는다.
- 이미 버려진 BCB를 statdump로 보이게 하는 일(이슈의 ANALYSIS 확인 사항 3)은 이번 범위에 넣지 않았다.
