# CBRD-26325 — Page Latch Timeout 원인 규명용 Instrumentation Proposal

## 배경

- 본 crash 위치(`pgbuf_timed_sleep` → `assert(0)`)는 debug 빌드에서 **의도된 abort**임이 확인됨.
- 실제 규명 대상은 *왜 한 스레드가 heap header 페이지의 WRITE latch를 300초 이상 점유했는가* 임.
- 현재 보유한 단일 스레드 core dump만으로는 holder의 정체와 stuck 원인을 단정할 수 없음.
- CUBRID page latch는 설계상 deadlock 미감지 → timeout으로만 해소 (`pgbuf_block_bcb` 주석 참조).
- 단계적으로 instrumentation을 추가하여 holder/대기 큐/holder의 현재 위치를 확정한다.

---

## Phase 1 — `assert(0)` 직전에 BCB 상태 dump (최소 비용, 우선 적용)

**위치**: `src/storage/page_buffer.c`, `pgbuf_timed_sleep`의 `er_set_return:` 라벨 안, `assert(0)` 직전.

```c
#if !defined(NDEBUG)
{
  PGBUF_ATOMIC_LATCH_IMPL impl_dbg = get_impl (&bufptr->atomic_latch);
  THREAD_ENTRY *w;
  int idx = 0;

  er_log_debug (ARG_FILE_LINE,
    "PGBUF_LATCH_TIMEOUT: bcb=%p vpid={%d,%d} mode=%d fcnt=%d flags=0x%llx "
    "last_thread=%p(tran=%d) my_request=%d wait=%ds\n",
    bufptr, bufptr->vpid.volid, bufptr->vpid.pageid,
    impl_dbg.impl.latch_mode, impl_dbg.impl.fcnt,
    (long long) bufptr->flags,
    bufptr->latch_last_thread,
    bufptr->latch_last_thread ? bufptr->latch_last_thread->tran_index : -1,
    save_request_latch_mode, wait_secs);

  for (w = bufptr->next_wait_thrd; w != NULL; w = w->next_wait_thrd, idx++)
    {
      er_log_debug (ARG_FILE_LINE,
        "  waiter[%d] thrd=%p tran=%d mode=%d fcnt=%d resume=%d\n",
        idx, w, w->tran_index, w->request_latch_mode,
        w->request_fix_count, w->resume_status);
    }
}
#endif
```

**확보 가능한 정보**

- WRITE latch 마지막 grantee의 tran_index (보유 중이면 곧 현재 holder)
- 대기 큐 전체 깊이 및 각 waiter의 (mode, fcnt, resume_status)
- 같은 페이지를 어떤 모드로 누가 기다리는지

**한계**

- `latch_last_thread`는 grant 직후 갱신되므로 일부 예외 경로에서 stale 가능 → Phase 2로 보강.

---

## Phase 2 — 명시적 WRITE Holder 추적 (확정성 강화)

**구조체 변경**: `PGBUF_BCB`에 debug 전용 필드 추가.

```c
#if !defined(NDEBUG)
  THREAD_ENTRY   *dbg_owner;
  struct timespec dbg_owner_acquired_at;
  const char     *dbg_owner_caller_file;
  int             dbg_owner_caller_line;
#endif
```

**Set 위치** — WRITE grant가 발생하는 모든 경로:

- `pgbuf_latch_bcb_upon_fix` 즉시 grant 분기 (NO_LATCH→WRITE 전이 시)
- `pgbuf_block_bcb` 대기 후 wakeup 직후 (WRITE 요청 성공)
- `pgbuf_promote_read_latch` 의 promote 성공 분기 (READ→WRITE)
- 기타 latch_mode를 WRITE로 만드는 모든 지점

```c
#if !defined(NDEBUG)
if (new_latch_mode == PGBUF_LATCH_WRITE) {
  bufptr->dbg_owner = thread_p;
  clock_gettime (CLOCK_MONOTONIC, &bufptr->dbg_owner_acquired_at);
  bufptr->dbg_owner_caller_file = caller_file;
  bufptr->dbg_owner_caller_line = caller_line;
}
#endif
```

**Clear 위치** — WRITE 해제/downgrade:

- `pgbuf_unlatch_bcb_upon_unfix` 마지막 unfix에서 WRITE→NO_LATCH
- WRITE→READ downgrade 경로

```c
#if !defined(NDEBUG)
if (was_write && new_latch_mode != PGBUF_LATCH_WRITE)
  bufptr->dbg_owner = NULL;
#endif
```

**Phase 1 dump 확장**

```c
if (bufptr->dbg_owner != NULL) {
  struct timespec now;
  double held_for;
  clock_gettime (CLOCK_MONOTONIC, &now);
  held_for = (now.tv_sec - bufptr->dbg_owner_acquired_at.tv_sec)
           + (now.tv_nsec - bufptr->dbg_owner_acquired_at.tv_nsec) / 1e9;
  er_log_debug (ARG_FILE_LINE,
    "  HOLDER: thrd=%p tran=%d acquired_at=%s:%d held_for=%.1fs\n",
    bufptr->dbg_owner, bufptr->dbg_owner->tran_index,
    bufptr->dbg_owner_caller_file, bufptr->dbg_owner_caller_line,
    held_for);
}
```

**확보 가능한 정보**

- holder thread 및 tran_index
- 어느 caller가 잡았는지 (`heap_file.c:3562` 같은 식별자)
- 보유 시간(초)

---

## Phase 3 — Holder의 "지금 무엇을 기다리는지" (Breadcrumb)

**구조체 변경**: `THREAD_ENTRY` 에 debug 전용 breadcrumb 필드 추가.

```c
#if !defined(NDEBUG)
  char dbg_breadcrumb[160];
  struct timespec dbg_breadcrumb_at;
#endif
```

**매크로**

```c
#if !defined(NDEBUG)
#define DBG_BREADCRUMB(thr_p, fmt, ...) do {                  \
  if ((thr_p) != NULL) {                                      \
    snprintf((thr_p)->dbg_breadcrumb,                         \
             sizeof((thr_p)->dbg_breadcrumb),                 \
             "%s:%d " fmt, __FILE__, __LINE__, ##__VA_ARGS__);\
    clock_gettime (CLOCK_MONOTONIC,                           \
                   &(thr_p)->dbg_breadcrumb_at);              \
  }                                                           \
} while (0)
#else
#define DBG_BREADCRUMB(...) ((void)0)
#endif
```

**삽입 지점** — 장시간 블로킹 가능한 호출 직전:

- `pgbuf_fix_debug` 진입: `DBG_BREADCRUMB(thread_p, "pgbuf_fix v=%d p=%d m=%d", vpid->volid, vpid->pageid, request_mode);`
- `pgbuf_block_bcb` / `pgbuf_timed_sleep` 진입
- `lock_object` 진입 (with oid)
- `heap_stats_sync_bestspace` 진입 + 스캔 루프 매 N회
- `pthread_cond_wait` / `thread_suspend_*` 직전
- `fileio_*` (디스크 I/O) 호출 직전

**Phase 1 dump 확장**

```c
if (bufptr->dbg_owner != NULL) {
  er_log_debug (ARG_FILE_LINE,
    "  HOLDER BREADCRUMB: %s\n", bufptr->dbg_owner->dbg_breadcrumb);
}
```

**확보 가능한 정보**

- holder가 timeout 시점에 어디서 무엇을 기다리는지 한 줄 요약 (예: `lock_manager.c:1234 lock_object oid={...}`, `file_io.c:567 fileio_read vol=3 pg=99999`).

---

## Phase 4 — Holder에게 강제 스택 덤프 (최후 수단, 선택)

**개념**: timeout 시 holder thread에 `SIGUSR2`를 보내 자기 스택을 error log에 출력시키고 abort하지 않음.

**핸들러 등록** (`src/executables/server.c`, debug 빌드):

```c
#if !defined (NDEBUG)
static void dbg_stack_handler (int signo) {
  er_print_crash_callstack (signo);   /* abort 없이 콜스택만 */
}
/* main에서: */
register_signal_handler (SIGUSR2, dbg_stack_handler);
#endif
```

**Phase 1 dump 직후**:

```c
#if !defined(NDEBUG)
if (bufptr->dbg_owner != NULL && bufptr->dbg_owner != thread_p
    && bufptr->dbg_owner->tid != 0) {
  pthread_kill (bufptr->dbg_owner->tid, SIGUSR2);
  usleep (500 * 1000);
}
#endif
```

**확보 가능한 정보**

- holder의 실제 콜스택 전체.

---

## 부속 권장 사항

1. **`pgbuf_latch_timeout` 임시 단축**
   - 재현 사이클 축소용으로 300s → 30~60s로 임시 조정.
   - 단 normal-but-slow wait이 false-positive로 잡힐 수 있으므로 dump 신뢰성 확보 후 원복.

2. **`assert(0)`는 유지**
   - dump는 `assert(0)` *직전*에 `er_log_debug`로 출력 → core 분석 없이도 `cub_server.err`에서 회수 가능.
   - 의도된 debug abort 동작은 그대로 보존.

3. **Release 빌드 대응 (선택)**
   - `er_log_debug` 자체는 release에서도 동작하므로, Phase 1 dump를 `#if !defined(NDEBUG)` 가드 없이도 적용 가능 (CPU 비용은 timeout 발생 시점 한 번뿐).
   - 운영 환경에서 동일 현상 발생 시 분석 자료 확보 가능.

4. **권장 도입 순서**
   - Phase 1 (단독 적용, ~15줄) → 재현해서 holder/큐 정보 확보.
   - 부족하면 Phase 2 추가 → holder 확정 + hold time 확정.
   - stuck 원인 미상이면 Phase 3 추가 → 무엇을 기다리는지 확정.
   - 그래도 부족하면 Phase 4 → 콜스택 회수.
   - 통상 Phase 1+2+3에서 원인 규명 가능.

---

## 기대 산출물

각 단계 적용 후 `cub_server.err`에 다음 형태의 라인이 남게 됨:

```
[timestamp] PGBUF_LATCH_TIMEOUT: bcb=0x... vpid={1,257} mode=2 fcnt=1 ...
  HOLDER: thrd=0x... tran=512 acquired_at=heap_file.c:3562 held_for=301.4s
  HOLDER BREADCRUMB: lock_manager.c:1234 lock_object oid={...}
  waiter[0] thrd=0x... tran=1026 mode=2 fcnt=1 resume=1
  waiter[1] thrd=0x... tran=773  mode=1 fcnt=1 resume=1
  ...
```

이 정보면 다음 중 어느 시나리오인지 단정 가능:

- (a) 단일 holder가 임계영역에서 다른 자원(lock/I/O/page latch)에 stuck → breadcrumb이 가리킴
- (b) page latch 간 deadlock cycle → waiter 중 holder가 들고 있는 다른 페이지를 잡고 있음이 보임
- (c) 단순 hot-table 경합으로 누적 timeout → holder는 짧게 잡고 풀지만 큐가 너무 깊음 (held_for가 짧고 큐 길이가 매우 큼)
