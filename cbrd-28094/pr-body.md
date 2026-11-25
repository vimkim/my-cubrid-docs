https://jira.cubrid.org/browse/CBRD-28094

## Purpose

- 디버그 로그 호출 16곳에서 printf 형식의 포맷 문자열과 실제 인자의 개수나 종류가 맞지 않습니다. 로그를 켜면 틀린 값이나 쓰레기 값이 출력되고, 일부 호출은 C 표준상 정의되지 않은 동작입니다.
- AS-IS: 서버 모드의 vacuum, file, btree, disk 디버그 로그는 `trid=` 자리에 트랜잭션 ID 대신 `LOG_TDES` 포인터의 일부를 출력합니다. 다른 15곳은 인자가 모자라거나 남거나 다른 종류의 값을 넘깁니다.
- TO-BE: 16곳 모두 변환 지정자와 인자가 일치하고, `trid=` 는 현재 트랜잭션 ID를 출력합니다.

## Implementation

- `src/transaction/log_impl.h`: `LOG_THREAD_TRAN_ARGS` 가 `logtb_find_current_tranid ()` 를 넘깁니다. 이 함수는 tdes가 NULL이면 `NULL_TRANID` 를 반환합니다.
- `src/storage/double_write_buffer.cpp`: 한 `dwb_log` 에는 빠진 block 번호를 넘기고, 다른 하나에서는 인자가 없는 `%d` 를 지웁니다.
- `src/thread/critical_section.c` (4곳): `%d.06d` 오타를 `%lld.%06ld` 로 고치고, `time_t` 와 `suseconds_t` 값을 캐스트해서 넘깁니다.
- `src/query/vacuum.c`, `src/transaction/log_applier.c` (2곳), `src/transaction/log_manager.c` (`cdc_log`): 이미 넘기던 인자에 맞는 지정자를 메시지에 추가합니다.
- `src/storage/file_manager.c`: `%|%d` 를 `%d|%d` 로 고칩니다.
- `src/api/cubrid_log.c`: `LOG_LSA` 구조체를 `%lld` 에 넘기지 않고 `LSA_AS_ARGS` 로 `pageid|offset` 을 출력합니다.
- `src/broker/shard_proxy_io.c` (3곳): `char *` 에 쓰던 `%S`(wide 문자열)를 `%s` 로 고칩니다.
- 로그 메시지만 바뀌고 다른 동작은 바뀌지 않습니다.

## Remarks

- 확인 방법: `_er_log_debug`, `proxy_log_write`, `cubrid_log_tracelog` 선언에 `__attribute__ ((format (printf, ...)))` 를 임시로 붙이고 GCC 11.5 debug 빌드(`cmake --build <build-dir> -- -k 0`)에서 `-Wformat` 경고를 비교했습니다. 임시 속성은 커밋에 넣지 않았습니다.
  - 변경 전 (`develop`): 16곳 모두 인자 개수나 종류 경고가 나옵니다. `LOG_THREAD_TRAN_ARGS` 를 쓰는 호출 171곳에서 `LOG_TDES*` 경고가 나옵니다.
  - 변경 후: 이 종류의 경고가 0건입니다. 남은 경고는 `%d` 에 64비트 값을 넘기는 폭 차이뿐이며 이 PR의 범위가 아닙니다.
- 속성 없는 debug 빌드는 성공하고, 수정한 파일에서 새 경고가 없습니다. `ctest` 는 70개 중 69개가 통과했습니다. `test_oos_real_vacuum_latch_timeout_retry` 가 서버 부하가 높을 때 시간 초과로 실패했지만, 단독으로 5번 다시 실행하면 모두 통과했습니다.
- 포맷 검사 속성 추가와 나머지 폭 차이 정리는 [CBRD-28100](https://jira.cubrid.org/browse/CBRD-28100)에서 다룹니다.
