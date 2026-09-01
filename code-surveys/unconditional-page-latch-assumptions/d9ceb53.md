# CUBRID unconditional page-latch 실패 가정 패턴

## Verdict

CUBRID `d9ceb5317c4d5bf15d2bcd2e89c08c2db9de3530`에는 `PGBUF_UNCONDITIONAL_LATCH`로 page를 요청한 뒤 실패를 정상 경합으로 처리하지 않는 호출부가 여러 storage/recovery 경로에 존재한다. 일부는 곧바로 `assert_release(false)`를 실행하고, 일부는 허용된 오류를 `ER_INTERRUPTED` 등으로 제한한 뒤 다른 오류에 assert한다. `pgbuf_fix_internal()`이 transaction의 zero-wait 상태를 보고 unconditional 요청을 conditional로 바꾸면 `ER_LK_PAGE_TIMEOUT`이 이 불변식 경로에 들어갈 수 있다.

B-tree는 구분해야 한다. `src/storage/btree.c`에는 unconditional latch 요청이 59곳 있지만, 확인한 직접 획득 실패 경로는 대부분 NULL/error를 상위로 전달한다. B-tree의 중요한 사례는 assert 가정이 아니라 그 반대다. `btree_set_error()`는 B-tree page latch를 보유한 상태에서 class name을 읽다가 dead latch가 생기지 않도록 `LK_FORCE_ZERO_WAIT`를 설정하고, 획득 실패 시 class name만 생략한다.

## Shared Scenario

호출자가 다음 계약으로 page를 요청한다고 가정한다.

```
pgbuf_fix(..., PGBUF_UNCONDITIONAL_LATCH)
  -> busy이면 기다린 뒤 page 반환
  -> interrupt/I/O/복구 불가능 오류만 실패
```

현재 page buffer는 transaction의 `LOG_TDES::wait_msecs`가 `LK_ZERO_WAIT` 또는 `LK_FORCE_ZERO_WAIT`이면 이 요청을 `PGBUF_CONDITIONAL_LATCH`로 바꾼다. busy page는 기다리지 않고 실패하므로 caller가 생각한 오류 집합이 달라진다.

## CUBRID Trace

### 사용자 작업에서 도달 가능한 대표 경로

| 함수 | 위치 | 실패 가정 |
|------|------|-----------|
| `file_temp_alloc()` | `src/storage/file_manager.c:8667`, fix `:8711`, `:8842` | temp file table page를 unconditional로 잡는다. NULL이면 `ER_INTERRUPTED`만 허용하고 다른 오류는 `assert_release(false)`다. `ER_LK_PAGE_TIMEOUT`은 assert 대상이다. |
| `file_destroy()` | `src/storage/file_manager.c:4136`, fix `:4176` | temp file은 interrupt를 막았으므로 header fix 실패를 허용하지 않는다. temp 경로의 NULL은 `assert_release(!is_temp)`를 실패시킨다. |
| `disk_reserve_sectors()` | `src/storage/disk_manager.c:4300`, assert `:4434` | 하위 volume-header/sector-table latch 오류가 올라오면 I/O와 interrupt 등 일부만 허용한다. `ER_LK_PAGE_TIMEOUT`은 예상 목록 밖이라 assert한다. CBRD-27198의 직접 경로다. |
| `disk_volume_expand()` | `src/storage/disk_manager.c:1904`, header fix `:1933` | `disk_get_volheader()` 실패를 즉시 `assert_release(false)`와 fatal error로 처리한다. |
| `file_temp_reset_user_pages()` | `src/storage/file_manager.c:8966`, fix `:9099` | temp file table chain의 다음 page fix 실패를 `assert_release(false)`로 처리한다. |

### recovery·정리 불변식 경로

다음 함수도 unconditional fix 실패를 복구 불가능한 내부 오류로 취급한다.

| 함수 | 위치 | 코드의 판단 |
|------|------|-------------|
| `log_rv_redo_fix_page()` | `src/transaction/log_recovery.c:6563-6585` | NULL이면 recovery가 불가능하다는 주석과 함께 assert |
| `pgbuf_rv_dealloc_undo()` | `src/storage/page_buffer.c:15173-15194` | deallocated page 복원 fix가 NULL이면 assert |
| `disk_rv_undo_format()` | `src/storage/disk_manager.c:1235-1273` | volume header fix 오류를 알 수 없는 오류로 보고 assert |
| `disk_rv_reserve_sectors()` / `disk_rv_unreserve_sectors()` | `src/storage/disk_manager.c:3909-4035` | disk-check critical section 재진입 뒤 refix는 “should not fail” |
| `file_rv_dealloc_internal()` | `src/storage/file_manager.c:6631-6667` | recovery 중 file header fix는 “should not be interrupted” |
| `file_rv_user_page_unmark_delete_logical()` | `src/storage/file_manager.c:8423-8464` | recovery 중 file header fix 실패를 assert |

이는 “모든 unconditional 호출이 assert한다”는 뜻은 아니다. 소스에는 `PGBUF_UNCONDITIONAL_LATCH`가 252회 등장하며 많은 호출부는 오류를 정상적으로 반환한다. 위 표는 latch 획득 실패 자체를 assert하거나 허용 오류를 좁혀 `ER_LK_PAGE_TIMEOUT`을 불변식 위반으로 만드는 고신뢰 사례다.

### 반대 계약: busy를 정상 결과로 쓰는 곳

| 함수 | 위치 | 의도 |
|------|------|------|
| `bestspace::shard::L1_fix()` | `src/storage/bestspace.cpp:669-700` | `LK_FORCE_ZERO_WAIT` 뒤 `pgbuf_ordered_fix()`를 호출하고 page가 바쁘면 `status::CONTENDED`로 건너뛴다. |
| `btree_set_error()` | `src/storage/btree.c:19724-19783` | B-tree page latch를 보유한 채 `heap_get_class_name()`을 호출하므로 dead latch를 피하려고 force-zero를 사용한다. 실패하면 진단 문자열에서 class name만 생략한다. |
| `pgbuf_ordered_fix()` | `src/storage/page_buffer.c:12332-12344` | `LK_FORCE_ZERO_WAIT`일 때 오류를 추가로 설정하지 않고 page scan이 계속될 수 있도록 한다. |

한 transaction 필드가 “반드시 기다려야 한다”와 “절대 기다리면 안 된다”라는 반대 계약을 동시에 전달하는 것이 근본 문제다. 따라서 CBRD-27356에서는 호출자가 wait/try/ordered-retry를 명시하도록 page-buffer 경계를 바꾸고, B-tree/best-space의 nonblocking 의미를 보존해야 한다.

## PostgreSQL and MySQL

| 시스템 | transaction lock timeout과 내부 latch 관계 | 이 패턴과의 대응 |
|--------|--------------------------------------------|------------------|
| PostgreSQL | `lock_timeout`은 heavyweight lock에 적용되고 LWLock/buffer content lock은 별도 blocking/conditional API를 사용 | transaction timeout 때문에 unconditional 내부 latch가 try-lock으로 바뀌는 대응 패턴 없음 |
| MySQL/InnoDB | `innodb_lock_wait_timeout`은 record/table lock에 적용되고 page rw-lock/mutex는 별도 wait/nowait API를 사용 | transaction timeout이 internal latch caller의 실패 집합을 바꾸는 대응 패턴 없음 |

세 DBMS의 상세 근거는 기존 [lock-vs-latch timeout 보고서](../../cbrd-27198/research/lock-vs-latch-timeout-survey_d9ceb53_codex.md)에 정리되어 있다.

## Runtime Probe

새 probe는 실행하지 않았다. CBRD-27198의 기존 재현에서 `file_temp_alloc()` → `disk_reserve_sectors()` 경로로 `ER_LK_PAGE_TIMEOUT`이 assert에 도달하는 현상이 이미 확인됐고, 이번 질문은 같은 정적 호출 패턴의 범위를 찾는 것이므로 추가 instrumentation이 결론을 바꾸지 않는다. CUBRID, PostgreSQL, MySQL 소스는 수정하지 않았다.

## Unknowns

- recovery/cleanup 표의 각 경로가 실제로 zero-wait `LOG_TDES`를 상속할 수 있는지는 별도 runtime fault injection이 필요하다.
- wrapper를 여러 단계 거쳐 오류를 최종 assert하는 경로는 더 있을 수 있다. 위 목록은 직접 fix 실패와 CBRD-27198의 확인된 전파 경로를 중심으로 한 고신뢰 목록이며 전체 252개 호출부의 완전한 의미 분류는 아니다.
- B-tree의 59개 unconditional 호출은 직접 획득 실패를 대체로 반환하지만, 상위 호출자가 그 오류를 다시 불변식 위반으로 바꾸는지는 별도 call-graph audit 대상이다.

## Source Revisions

- CUBRID: `/home/vimkim/gh/cb/review-CBRD-27198-no-wait-demote`, `d9ceb5317c4d5bf15d2bcd2e89c08c2db9de3530`, tracked files clean
- PostgreSQL: `/home/vimkim/gh/pg/postgres`, `fd2b89854d93d70fe8c9a69d5b8fafd5b9302cfc`, tracked files clean; pre-existing `.omc/`
- MySQL: `/home/vimkim/gh/mysql/mysql-server`, `06a5c1c99c377fc41b2eba1ea244e8b220bdc3c8`, tracked files clean
