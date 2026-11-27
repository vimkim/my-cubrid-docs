https://jira.cubrid.org/browse/CBRD-28436

## Purpose

- OOS 단위 테스트 `test_oos_real_vacuum_latch_timeout_retry`가 바로 앞의 `test_oos_real_vacuum_latch_timeout` 다음에 실행되면 ctest 제한 시간(60초)까지 멈춥니다. 엔진 결함이 아니라 테스트 코드 결함입니다.
- AS-IS: 테스트가 `log_Gl.prior_info.prior_lsa`까지 로그 flush를 요청합니다. 이 위치는 다음 로그 레코드가 들어갈 자리여서, 다른 스레드가 새 로그를 쓰기 전에는 `logpb_flush_pages()`가 끝나지 않습니다. 앞 테스트가 vacuum 작업을 모두 끝낸 뒤에는 로그를 쓰는 스레드가 없어서 계속 기다립니다.
- TO-BE: 테스트가 마지막으로 쓴 레코드의 시작 위치(`prev_lsa`)까지 flush를 요청합니다. 엔진의 `logpb_flush_pages()` 호출자와 같은 방식이어서, 다른 로그 쓰기가 없어도 flush가 끝납니다.

## Implementation

- `unit_tests/oos/test_oos_real_vacuum_server.cpp`에 `flush_log_through_last_record()` 헬퍼를 추가했습니다. 이 헬퍼는 `log_Gl.prior_info.prev_lsa`까지 flush합니다.
- `prior_lsa`까지 flush하던 두 곳이 이 헬퍼를 씁니다.
  - `OosRealVacuumHeaderHeld::flush_log()`: `FailingHeapCostsOneLookupPerRun` 등이 로그 블록을 닫을 때 호출합니다.
  - `VacuumWaitsForHeapHeaderWithoutHoldingLastPage`
- 엔진 코드는 바꾸지 않았습니다.

## Remarks

- 원인: 모든 로그가 flush되면 `nxio_lsa`(디스크에 기록된 끝 위치)가 `prior_lsa`와 같아집니다. `logpb_need_wal()`은 `nxio_lsa <= lsa`일 때 참이므로, `prior_lsa`까지 요청한 flush는 다른 레코드가 쓰여야 끝납니다. 멈춘 프로세스의 스택은 `FailingHeapCostsOneLookupPerRun` → `flush_log()` → `logpb_flush_pages()`의 `pthread_cond_timedwait`이었고, vacuum과 log flush 스레드는 모두 대기 중이었습니다.
- 검증 (GCC `RelWithDebInfo`, `-DUNIT_TEST_OOS=ON`):
  - 수정 전: `oos_setup_db` → `test_oos_real_vacuum_latch_timeout` → `test_oos_real_vacuum_latch_timeout_retry` 순서로 10회 실행해 10회 모두 timeout이 났습니다.
  - 수정 후: 같은 순서에 `test_oos_real_vacuum_latch_timeout_shutdown`까지 붙여 3회 실행해 모두 통과했습니다. `test_oos_real_vacuum_latch_timeout_retry`는 11.0-11.5초에 끝납니다.
  - `test_oos_real_vacuum_server`를 쓰는 ctest 항목 5개(`ctest -R '^(oos_setup_db|test_oos_real_vacuum.*)$'`)가 모두 통과했습니다.
- assert가 켜진 Debug 빌드에서는 실행하지 않았습니다.
- gha-ci는 단위 테스트를 빌드하거나 ctest를 실행하지 않으므로, 이 PR의 CI 결과는 이 테스트를 검증하지 않습니다.
