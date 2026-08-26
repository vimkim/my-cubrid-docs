# PR #7630 Blocking Refutation and Better Designs

**PR:** [CUBRID/cubrid#7630](https://github.com/CUBRID/cubrid/pull/7630)

**Title:** `[CBRD-27198] Do not turn an unconditional latch on a structural page into a conditional one`

**Reviewed HEAD:** `1185f16d7e5f540ffdad4509cbd061ef0535f4df`

**Decision:** **BLOCK / REJECT**

**Scope:** PR의 전제, observable behavior, timeout classification, progress risk, 검증 공백, 대안 설계

**Non-goal:** 작성자 개인에 대한 평가. 이 문서는 코드와 주장만 공격한다.

## Executive Summary

이 PR은 원래 crash를 없애지만, 제출된 형태로는 merge할 수 없다.

1. **확정된 regression:** `force_latch_wait`가 원래 transaction wait policy를 읽기 전에 무조건 `LK_INFINITE_WAIT`를 반환한다. 그 결과 positive finite policy도 infinite classification으로 바뀌며, page-latch watchdog 만료 시 expected `ER_LK_PAGE_TIMEOUT` 대신 debug assert와 `ER_LK_UNILATERALLY_ABORTED` 경로를 탄다.
2. **미입증 전제:** “`lock_timeout`은 사용자가 lock에만 적용하려 한 값”이라는 해석은 이름과 주 용례에 근거한 추론이다. exact code의 effective contract는 같은 값을 page-latch admission과 timeout classification에 오랫동안 사용해 왔다. engine도 `LK_FORCE_ZERO_WAIT`를 page-latch 회피에 의도적으로 사용한다.
3. **정의되지 않은 정책 범주:** `structural page`는 기존 CUBRID page category가 아니다. Merge-base에는 용례가 없고 exact HEAD의 다섯 용례는 모두 이 PR이 추가했다. Type, predicate, membership rule 없이 새 umbrella term이 no-wait override의 근거가 됐다.
4. **새 progress 의미:** zero-wait structural-page miss가 즉시 실패하던 동작에서, 독립 page-latch watchdog까지 기다리는 동작으로 바뀐다. 기본 상한은 300초이며, 만료 시 infinite classification의 강한 실패 경로를 선택한다.
5. **검증 부재:** PR diff는 production source 6개, 62 insertions이고 test 변경이 없다. latch-order cycle이 없다는 audit, forced-contention test, watchdog-expiry test, four-policy matrix가 모두 없다.
6. **원래 repro의 한계:** `cbrd_27198_repro.sh`는 `lock_timeout=0 → immediate -76 → disk_reserve_sectors assert`를 재현할 뿐, PR의 wait policy가 옳거나 deadlock-safe하다는 것을 검증하지 않는다.

가장 작은 merge 가능 수정은 PR의 scoped-wait 정책을 유지하되 **zero-wait 두 sentinel만 override하고 positive 및 already-infinite 값을 보존**하는 것이다. 그러나 zero-wait을 page latch에도 적용해야 한다는 제품 계약을 선택한다면, 이 PR의 thread-local override 자체를 버리고 typed `WOULD_BLOCK` interface와 all-or-nothing reservation cleanup을 설계해야 한다.

## Standard of Proof

이 보고서는 다음 primary source만 사용한다.

- exact reviewed worktree: `/home/vimkim/gh/cb/review-CBRD-27198-unconditional`
- exact reviewed commit: `1185f16d7e5f540ffdad4509cbd061ef0535f4df`
- [CBRD-27198](http://jira.cubrid.org/browse/CBRD-27198) 및 [재현 attachment](http://jira.cubrid.org/secure/attachment/1020031/cbrd_27198_repro.sh)
- [작성자의 architecture response](https://github.com/CUBRID/cubrid/pull/7630#issuecomment-5365130299)
- 기존 [published review report](./PR-7630-report_1185f16_codex.md)

확정된 code path와 미검증 risk를 구분한다. 이 보고서는 실제 latch-order cycle을 발견했다고 주장하지 않는다. 대신 PR이 그 부재를 증명하지 않았고, zero-wait transaction을 그 wait path에 새로 진입시키면서 필요한 검증을 추가하지 않았다고 주장한다.

## What the PR Changes

PR은 volume header와 sector table fix를 다음 save/set/fix/restore sequence로 감싼다.

```c
save_force_latch_wait = pgbuf_set_force_latch_wait (thread_p, true);
page = pgbuf_fix (..., PGBUF_UNCONDITIONAL_LATCH);
(void) pgbuf_set_force_latch_wait (thread_p, save_force_latch_wait);
```

적용 위치:

- [volume header scope: `disk_manager.c:3233-3236`](https://github.com/CUBRID/cubrid/blob/1185f16d7e5f540ffdad4509cbd061ef0535f4df/src/storage/disk_manager.c#L3233-L3236)
- [sector table scope: `disk_manager.c:3510-3513`](https://github.com/CUBRID/cubrid/blob/1185f16d7e5f540ffdad4509cbd061ef0535f4df/src/storage/disk_manager.c#L3510-L3513)

실제 정책 변경은 helper가 아니라 transaction wait lookup 깊숙한 곳에 있다.

```c
if (flag_owner_p != NULL && flag_owner_p->force_latch_wait)
  {
    return LK_INFINITE_WAIT;
  }
```

Source: [`page_buffer.c:16922-16949`](https://github.com/CUBRID/cubrid/blob/1185f16d7e5f540ffdad4509cbd061ef0535f4df/src/storage/page_buffer.c#L16922-L16949)

이 early return은 원래 `tdes->wait_msecs`가 무엇이었는지 확인하지 않는다.

## Attack 1: “Structural Page” Is a New, Undefined Category

`structural page`는 기존 CUBRID domain term이나 page-buffer contract가 아니다.

- Exact merge-base `169cef5434ace12ca3597d6abf278b3ccf09e3b2`에서 case-insensitive exact phrase 검색 결과는 0건이다.
- Exact reviewed HEAD의 다섯 용례—`thread_entry.hpp` 1건, `page_buffer.c` 2건, `disk_manager.c` 2건—는 모두 이 PR의 diff addition이다.
- `STRUCTURAL_PAGE` enum, flag, predicate, membership table은 없다.
- 기존 concrete page classification은 [`PAGE_TYPE`](https://github.com/CUBRID/cubrid/blob/1185f16d7e5f540ffdad4509cbd061ef0535f4df/src/storage/storage_common.h#L148-L166)의 `PAGE_VOLHEADER`, `PAGE_VOLBITMAP` 등이다. 이 enum 자체도 source 주석상 validation/debugging 용도이며 `structural`이라는 상위 범주를 정의하지 않는다.

PR이 실제로 override를 적용하는 곳은 다음 두 call site뿐이다.

| Exact page | Existing CUBRID name/type | PR의 새 표현 |
|---|---|---|
| volume header page | `PAGE_VOLHEADER` | structural page |
| sector allocation-table/bitmap page | `PAGE_VOLBITMAP` | structural page |

가장 가까운 기존 표현은 volume의 `system page` 영역이다. `DISK_VOLUME_HEADER::sys_lastpage`는 last system page를 나타내지만, source 어디에도 `system page == structural page`라는 equivalence나 wait-policy contract는 없다.

따라서 다음 문장은 기존 invariant를 인용하는 것이 아니라 PR이 새 정책을 선언하는 것이다.

```c
/* A structural page must not inherit the transaction's no-wait setting. */
```

Source: [`page_buffer.c:16922-16931`](https://github.com/CUBRID/cubrid/blob/1185f16d7e5f540ffdad4509cbd061ef0535f4df/src/storage/page_buffer.c#L16922-L16931)

정의가 없으므로 interface boundary가 불명확하다.

- volume header와 sector table만 포함하는가?
- file header, heap header, B-tree root도 구조를 대표하므로 포함되는가?
- page가 hot하거나 내부 metadata라는 사실이 no-wait override의 충분조건인가?
- 이 범주에 속하면 latch가 항상 microseconds 안에 해제된다는 보장은 무엇인가?
- 새 caller가 이 helper를 사용해도 되는지는 어떤 rule로 판정하는가?

현재 형태는 deep policy를 page-buffer interface에 올린 것이 아니라, 두 call site에 대한 예외를 generic-sounding label로 포장한 것이다. Scope가 정말 두 page뿐이라면 comment와 API contract는 `volume header and sector allocation table`을 정확히 명시해야 한다. 더 넓은 architecture category라면 membership, wait invariant, allowed callers를 type 또는 predicate로 정의하고 그 전체 범위를 audit/test해야 한다.

## Attack 2: “Lock-only Intent” Is Not the Existing Contract

작성자는 답변에서 다음을 인정한다.

- intended meaning은 lock 한정이라고 판단한다.
- 별도 parameter description은 없다.
- 판단 근거는 `lock_timeout`이라는 이름과 주된 용례다.
- 실제 동작은 latch까지 포함한다.

이는 target architecture에 대한 의견으로는 타당할 수 있다. 하지만 backward-compatible existing contract의 증거는 아니다.

### Evidence for lock-oriented intent

- [`db_set_lock_timeout`](https://github.com/CUBRID/cubrid/blob/1185f16d7e5f540ffdad4509cbd061ef0535f4df/src/compat/db_admin.c#L1563-L1597)은 object lock 획득 대기라고 설명한다.
- [`LOG_TDES::wait_msecs`](https://github.com/CUBRID/cubrid/blob/1185f16d7e5f540ffdad4509cbd061ef0535f4df/src/transaction/log_impl.h#L475-L487) 주석은 “for locks”라고 쓴다.
- [`xlogtb_reset_wait_msecs`](https://github.com/CUBRID/cubrid/blob/1185f16d7e5f540ffdad4509cbd061ef0535f4df/src/transaction/log_tran_table.c#L2537-L2570) 주석도 lock 획득을 설명한다.

### Evidence for latch-inclusive effective behavior

- [`pgbuf_fix`](https://github.com/CUBRID/cubrid/blob/1185f16d7e5f540ffdad4509cbd061ef0535f4df/src/storage/page_buffer.c#L2273-L2283)는 같은 transaction wait 값을 읽어 unconditional latch를 conditional로 바꾼다.
- [`pgbuf_timed_sleep`](https://github.com/CUBRID/cubrid/blob/1185f16d7e5f540ffdad4509cbd061ef0535f4df/src/storage/page_buffer.c#L7284-L7296)는 같은 값을 latch admission과 timeout classification에 사용한다.
- [`bestspace.cpp`](https://github.com/CUBRID/cubrid/blob/1185f16d7e5f540ffdad4509cbd061ef0535f4df/src/storage/bestspace.cpp#L672-L689)는 busy page를 건너뛰기 위해 `LK_FORCE_ZERO_WAIT`를 transaction field에 의도적으로 저장한다.
- [`btree.c`](https://github.com/CUBRID/cubrid/blob/1185f16d7e5f540ffdad4509cbd061ef0535f4df/src/storage/btree.c#L19757-L19777)는 이미 B-tree page latch를 보유한 상태에서 “dead latch”를 피하기 위해 같은 sentinel을 의도적으로 사용한다.
- [Git blame](https://github.com/CUBRID/cubrid/blame/1185f16d7e5f540ffdad4509cbd061ef0535f4df/src/storage/page_buffer.c#L2273-L2283)은 unconditional-to-conditional behavior가 적어도 2014년부터 source에 존재했음을 보여 준다.

따라서 “no-wait가 latch에 전파되는 것은 단순 accidental leak이며 사용자는 의도하지 않았다”는 전제는 code로 입증되지 않는다. 반대로 current interface는 서로 다른 두 의미를 같은 state에 합쳐 놓은 오래된 coupling이다.

이 coupling을 제거하는 장기 방향과, 현재 사용자가 관측하는 behavior를 두 페이지 종류에서만 바꾸는 단기 PR은 별개의 결정이다. 후자는 explicit spec, compatibility analysis, test evidence가 필요하다.

## Attack 3: “No-wait Gains Nothing” Is Refuted by the Codebase

PR의 새 주석은 structural-page latch가 microseconds 동안만 유지되므로 no-wait을 존중해도 얻는 것이 없다고 주장한다. 이 주장은 너무 강하다.

1. 정상 hold time이 짧다는 사실은 deadlock cycle이나 latch leak이 불가능하다는 증명이 아니다. cycle은 평균 hold time과 무관하게 영구 대기가 될 수 있다.
2. B-tree code는 다른 latch를 이미 보유한 상태에서 추가 page fix가 “dead latch”가 될 수 있음을 명시하고, 이를 피하기 위해 `LK_FORCE_ZERO_WAIT`를 사용한다.
3. `bestspace`는 busy page를 정상 contention 결과로 취급하고 물러난다. no-wait은 실제 engine progress policy다.
4. PR은 volume-header→sector-table ordering을 변경하지 않지만, zero-wait transaction을 기존 queue/watchdog path에 새로 진입시킨다. 기존 order라고 해서 새 population에 대한 progress 검증이 불필요해지는 것은 아니다.

실제 reverse-order cycle은 아직 제시되지 않았다. 따라서 “deadlock bug가 확정됐다”고 말해서는 안 된다. 정확한 blocking objection은 다음이다.

> PR은 zero-wait을 최대 300초 wait 및 fatal watchdog classification으로 바꾸면서, 이 두 structural-page path에 cycle이 없다는 audit나 deterministic contention/watchdog test를 제공하지 않는다.

## Attack 4: “Unconditional Cannot Fail” Is Also Too Strong

`disk_get_volheader_internal`은 `pgbuf_fix`가 `NULL`을 반환할 수 있음을 직접 처리한다.

Source: [`disk_manager.c:3233-3246`](https://github.com/CUBRID/cubrid/blob/1185f16d7e5f540ffdad4509cbd061ef0535f4df/src/storage/disk_manager.c#L3233-L3246)

`disk_reserve_sectors`도 interrupt와 I/O error를 expected failure로 열거한다.

Source: [`disk_manager.c:4421-4455`](https://github.com/CUBRID/cubrid/blob/1185f16d7e5f540ffdad4509cbd061ef0535f4df/src/storage/disk_manager.c#L4421-L4455)

즉 정확한 문제는 “unconditional fix는 실패할 수 없다”가 아니다. **Latch contention에 의한 `ER_LK_PAGE_TIMEOUT`이 이 caller의 expected-error contract에 포함되지 않았다**는 것이다.

이 구분은 중요하다. 전자를 받아들이면 wait policy를 무조건 덮어쓰는 방향으로 가고, 후자를 받아들이면 `WOULD_BLOCK`을 명시적 outcome으로 만들거나 caller가 cleanup 후 반환하도록 만들 수 있다.

## Blocking Finding 1: Positive Finite Policy Is Reclassified as Infinite

### Before the PR

Positive transaction value는 `pgbuf_find_current_wait_msecs`에서 그대로 반환된다. 실제 latch sleep duration은 별도 `pgbuf_latch_timeout_msecs`를 사용하지만, expiry classification은 원래 positive value를 보존한다.

```c
old_wait_msecs = wait_msecs = pgbuf_find_current_wait_msecs (thread_p);

if (wait_msecs == LK_ZERO_WAIT || wait_msecs == LK_FORCE_ZERO_WAIT)
  wait_msecs = 0;
else
  wait_msecs = pgbuf_latch_timeout_msecs;
```

Source: [`page_buffer.c:7284-7296`](https://github.com/CUBRID/cubrid/blob/1185f16d7e5f540ffdad4509cbd061ef0535f4df/src/storage/page_buffer.c#L7284-L7296)

Watchdog가 만료되면 positive original value는 expected page-timeout branch를 탄다.

```c
else if (old_wait_msecs > 0)
  {
    ...
    er_set (..., ER_LK_PAGE_TIMEOUT, ...);
  }
```

Source: [`page_buffer.c:7409-7420`](https://github.com/CUBRID/cubrid/blob/1185f16d7e5f540ffdad4509cbd061ef0535f4df/src/storage/page_buffer.c#L7409-L7420)

### After the PR

Structural fix scope에서는 original value를 읽기 전에 `LK_INFINITE_WAIT`가 반환된다. 따라서 positive finite도 infinite branch로 들어간다.

```c
if (old_wait_msecs == LK_INFINITE_WAIT)
  {
    er_set (..., ER_PAGE_LATCH_TIMEDOUT, ...);
    assert (0);
    ...
    er_set (..., ER_LK_UNILATERALLY_ABORTED, ...);
  }
```

Source: [`page_buffer.c:7375-7407`](https://github.com/CUBRID/cubrid/blob/1185f16d7e5f540ffdad4509cbd061ef0535f4df/src/storage/page_buffer.c#L7375-L7407)

### Concrete timeline

```text
T1  volume header WRITE latch 보유
T2  original wait policy = positive finite
T2  structural helper가 force_latch_wait = true
T2  pgbuf_find_current_wait_msecs() → LK_INFINITE_WAIT
T2  page-latch watchdog까지 대기
T2  watchdog 만료
Expected: ER_LK_PAGE_TIMEOUT, caller가 error 처리
Actual:   debug assert + ER_LK_UNILATERALLY_ABORTED classification
```

이것은 가정이나 missing test가 아니라 exact code로 증명되는 blocking regression이다.

## Blocking Finding 2: Zero-wait Becomes a Long, Strongly Classified Wait

PR 전 zero-wait structural miss는 unconditional request가 conditional로 바뀌어 즉시 reject된다.

Source: [`page_buffer.c:2273-2283`](https://github.com/CUBRID/cubrid/blob/1185f16d7e5f540ffdad4509cbd061ef0535f4df/src/storage/page_buffer.c#L2273-L2283), [`page_buffer.c:6543-6577`](https://github.com/CUBRID/cubrid/blob/1185f16d7e5f540ffdad4509cbd061ef0535f4df/src/storage/page_buffer.c#L6543-L6577)

PR 후 같은 request는 `LK_INFINITE_WAIT`로 보이며 waiter queue에 들어간다. 실제 wait는 literal infinite가 아니라 independent page-latch watchdog으로 제한된다. 기본값은 300초다.

Source: [`system_parameter.c:5308-5319`](https://github.com/CUBRID/cubrid/blob/1185f16d7e5f540ffdad4509cbd061ef0535f4df/src/base/system_parameter.c#L5308-L5319)

따라서 observable change는 단순히 “crash가 사라진다”가 아니다.

```text
Before: busy now → immediate ER_LK_PAGE_TIMEOUT
After:  busy now → queue → release되면 성공
                         → watchdog까지 지속되면 assert/unilateral-abort classification
```

이 behavior가 제품적으로 옳을 수는 있다. 그러나 다음이 없으면 merge 근거가 없다.

- structural-page exception에 대한 explicit specification
- zero-wait user-visible latency 변화에 대한 승인
- watchdog expiry의 intended error/abort classification
- volume-header/sector-table latch-order audit
- forced-contention 및 watchdog-expiry regression test

## Blocking Finding 3: The PR Adds No Tests for a Concurrency Policy Change

Exact merge-base 대비 diff는 다음 6개 production file만 바꾼다.

```text
src/storage/disk_manager.c
src/storage/page_buffer.c
src/storage/page_buffer.h
src/thread/thread_entry.cpp
src/thread/thread_entry.hpp
src/thread/thread_entry_task.cpp
```

총 62 insertions이며 test file은 없다.

이 PR은 단순 crash guard가 아니다. 다음을 동시에 바꾼다.

- waiter queue admission
- per-thread mutable state lifecycle
- parallel worker와 shared transaction state의 관계
- page-latch watchdog expiry classification
- user zero-wait latency
- positive finite error meaning

테스트가 없다는 사실만으로 항상 reject하는 것은 아니다. 그러나 deterministic하게 검증 가능한 policy matrix를 전혀 추가하지 않은 상태에서 concurrency semantics를 변경하고, 실제로 한 matrix row가 잘못 구현되어 있으므로 merge를 block해야 한다.

## What the Reproducer Proves—and Does Not Prove

[Attachment](http://jira.cubrid.org/secure/attachment/1020031/cbrd_27198_repro.sh)은 다음 load를 만든다.

1. `temp_file_memory_size_in_pages=0` 등으로 temp file을 disk에 강제한다.
2. 100만 행과 여러 대형 sort로 temp file 생성을 유도한다.
3. 8개 session에서 `SET SYSTEM PARAMETERS 'lock_timeout=0'`을 실행한다.
4. query 실행 직후 client를 kill해 temp file 생성과 connection cleanup을 겹친다.
5. `CODE = -76`, server PID 변화, boot count 증가를 관찰한다.

따라서 다음은 검증한다.

- dblink 없이 local query만으로 original failure를 재현할 수 있다.
- no-wait, disk temp-file creation, volume-header contention이 겹치면 `-76` 및 debug assert crash가 발생한다.
- cub_master의 빠른 restart 때문에 단순 process existence가 아니라 PID/boot count를 봐야 한다.

다음은 검증하지 않는다.

- 사용자가 lock만 또는 latch까지 zero-wait하려 했는가
- structural page가 반드시 wait해야 하는가
- PR의 forced wait가 deadlock-safe한가
- zero-wait thread가 watchdog까지 stall하지 않는가
- positive finite와 infinite classification이 보존되는가
- conditional failure 뒤 partial reservation cleanup이 안전한가

PR HEAD에서 이 script가 더 이상 crash하지 않는 것은 original crash path가 사라졌다는 증거일 뿐, 새 behavior의 correctness 증거가 아니다.

## Better Solution A: Smallest Correct Repair to the Submitted Design

PR의 정책—zero-wait structural fix만 기다리게 한다—을 그대로 승인한다고 가정한다. 그러면 override는 original value가 두 no-wait sentinel일 때만 적용해야 한다.

```c
STATIC_INLINE int
pgbuf_find_current_wait_msecs (THREAD_ENTRY *thread_p)
{
  THREAD_ENTRY *flag_owner_p;
  LOG_TDES *tdes;
  int wait_msecs;

  flag_owner_p = thread_p != NULL ? thread_p : thread_get_thread_entry_info ();
  wait_msecs = /* resolve original tdes->wait_msecs */;

  if (flag_owner_p != NULL
      && flag_owner_p->force_latch_wait
      && (wait_msecs == LK_ZERO_WAIT || wait_msecs == LK_FORCE_ZERO_WAIT))
    {
      return LK_INFINITE_WAIT;
    }

  return wait_msecs;
}
```

Required invariants:

- `LK_ZERO_WAIT` → scoped override 허용
- `LK_FORCE_ZERO_WAIT` → scoped override 허용하되 engine skip/dead-latch semantics 영향 평가 필요
- positive finite → original positive value 그대로 반환
- `LK_INFINITE_WAIT` → 그대로 반환
- sibling worker는 shared `LOG_TDES`를 건드리지 않음
- nested save/restore는 outer value를 잃지 않음
- interrupt/error return 뒤 flag가 복구됨

이것이 현재 PR을 가장 작게 고치는 방법이다. 그러나 zero-wait user contract에 대한 architecture objection은 남는다.

## Better Solution B: Preserve Strict Zero-wait with Typed WOULD_BLOCK

제품 결정이 “`lock_timeout=0`이면 page-latch queue에도 들어가지 않는다”라면, thread-local override는 잘못된 방향이다. Page-buffer module의 seam에서 contention을 typed outcome으로 반환해야 한다.

```c
typedef enum
{
  PGBUF_FIX_ACQUIRED,
  PGBUF_FIX_WOULD_BLOCK,
  PGBUF_FIX_INTERRUPTED,
  PGBUF_FIX_ERROR
} PGBUF_FIX_STATUS;

PGBUF_FIX_STATUS
pgbuf_try_fix (THREAD_ENTRY *thread_p,
               const VPID *vpid,
               PAGE_FETCH_MODE fetch_mode,
               PGBUF_LATCH_MODE latch_mode,
               PAGE_PTR *page_out,
               int *error_out);
```

Interface contract:

- `ACQUIRED`: page가 pinned되고 requested latch mode를 보유한다.
- `WOULD_BLOCK`: incompatible latch 때문에 즉시 실패했으며 new pin/latch/waiter/error-manager side effect가 없다.
- `INTERRUPTED`: interrupt cleanup 완료 후 반환한다.
- `ERROR`: I/O, invalid page 등 real error이며 `error_out`이 유효하다.

`disk_reserve_sectors`는 `WOULD_BLOCK`을 expected contention으로 받아들여야 한다.

```c
if (status == PGBUF_FIX_WOULD_BLOCK)
  {
    disk_reservation_attempt_unwind (...);
    return ER_DISK_RESERVE_BUSY; /* or compatibility ER_LK_PAGE_TIMEOUT */
  }
```

### Why removing the assert alone is insufficient

현재 reservation은 여러 sector-table page를 순회하면서 바로 bit를 수정하고 dirty로 만든다.

Source: [`disk_manager.c:3637-3649`](https://github.com/CUBRID/cubrid/blob/1185f16d7e5f540ffdad4509cbd061ef0535f4df/src/storage/disk_manager.c#L3637-L3649)

뒤쪽 page에서 contention이 발생하면 앞쪽 page는 이미 수정되었을 수 있다. Error path는 temp reservation을 명시적으로 unreserve하고 cache state를 복구한 뒤 system operation을 abort한다.

Source: [`disk_manager.c:4379-4422`](https://github.com/CUBRID/cubrid/blob/1185f16d7e5f540ffdad4509cbd061ef0535f4df/src/storage/disk_manager.c#L4379-L4422)

그런데 temp cleanup도 volume header와 sector table을 다시 fix한다.

Source: [`disk_manager.c:4801-4843`](https://github.com/CUBRID/cubrid/blob/1185f16d7e5f540ffdad4509cbd061ef0535f4df/src/storage/disk_manager.c#L4801-L4843)

Rollback까지 strict no-wait이면 cleanup 자체가 다시 `WOULD_BLOCK`할 수 있다. 따라서 다음 중 하나를 명시해야 한다.

1. mutation 전에 필요한 structural page를 stable order로 preflight acquire한다.
2. cleanup/compensation만은 unconditional internal policy를 허용한다.
3. resumable compensation record를 남기고 safe worker가 나중에 복구한다.
4. observed initial volume-header miss만 immediate-return 대상으로 좁히고 late sector-table miss는 별도 설계한다.

Strict no-wait은 가능한 설계지만, 단순 assert 삭제가 아니라 reservation all-or-nothing interface를 다시 세우는 작업이다.

## Better Solution C: Long-term Explicit Page-buffer Wait-policy Seam

현재 interface는 서로 다른 결정을 한 값에 섞는다.

- caller latch condition
- transaction lock wait policy
- actual page-latch watchdog duration
- expiry error classification
- error를 set할지 silent result로 돌려줄지

이를 explicit policy로 분리해야 한다.

```c
typedef enum
{
  PGBUF_WAIT_TRANSACTION_COUPLED,
  PGBUF_WAIT_IMMEDIATE,
  PGBUF_WAIT_UNTIL,
  PGBUF_WAIT_INTERNAL_WATCHDOG
} PGBUF_WAIT_KIND;

typedef struct
{
  PGBUF_WAIT_KIND kind;
  struct timespec absolute_deadline; /* WAIT_UNTIL only */
} PGBUF_WAIT_POLICY;

typedef enum
{
  PGBUF_FIX_ACQUIRED,
  PGBUF_FIX_WOULD_BLOCK,
  PGBUF_FIX_DEADLINE_EXPIRED,
  PGBUF_FIX_WATCHDOG_EXPIRED,
  PGBUF_FIX_INTERRUPTED,
  PGBUF_FIX_ERROR
} PGBUF_FIX_OUTCOME;

PGBUF_FIX_OUTCOME
pgbuf_fix_with_policy (THREAD_ENTRY *thread_p,
                       const VPID *vpid,
                       PAGE_FETCH_MODE fetch_mode,
                       PGBUF_LATCH_MODE latch_mode,
                       PGBUF_WAIT_POLICY policy,
                       PAGE_PTR *page_out);
```

이 module은 내부에서 다음 private plan으로 resolve한다.

```text
enqueue? + absolute deadline/watchdog + reporting mode + expiry consequence
```

Leverage:

- caller가 `LOG_TDES`, `LK_*`, thread-local flag를 알 필요가 없다.
- admission과 error classification이 한 implementation에 모여 locality가 생긴다.
- deterministic test가 page-buffer interface만 통과해 모든 matrix row를 검증할 수 있다.
- `force_latch_wait` mutable state와 save/restore ordering이 사라진다.

Migration cost:

- exact source에서 `PGBUF_UNCONDITIONAL_LATCH` token은 251회, `PGBUF_CONDITIONAL_LATCH`는 30회 나타난다.
- hidden transaction coupling에 의존하는 caller를 audit해야 한다.
- 따라서 이 설계는 현재 ticket의 작은 patch가 아니라 별도 architecture project다.

작성자의 “근본 수정은 caller argument만으로 latch wait 여부를 정하는 것”이라는 방향과도 일치한다. 차이는 이 PR이 그 장기 방향을 증명하지 않은 scoped exception으로 덮는 동안, explicit seam은 정책을 interface에 올려 test 가능하게 만든다는 점이다.

## Required Deterministic Test Matrix

현재 probabilistic repro를 merge gate로 사용해서는 안 된다. Page-buffer contention을 deterministic하게 주입하는 test seam이 필요하다.

| Original policy | Structural flag | Busy latch admission | Required observable result |
|---|---:|---|---|
| `LK_ZERO_WAIT` | false | immediate | `ER_LK_PAGE_TIMEOUT` 또는 typed `WOULD_BLOCK` |
| `LK_FORCE_ZERO_WAIT` | false | immediate | silent/typed contention, no waiter |
| positive finite | false | queue | watchdog expiry → `ER_LK_PAGE_TIMEOUT`, no unilateral abort |
| `LK_INFINITE_WAIT` | false | queue | watchdog expiry → documented internal-stall path |
| `LK_ZERO_WAIT` | true | **spec required** | PR policy라면 queue; strict policy라면 immediate |
| `LK_FORCE_ZERO_WAIT` | true | **spec required** | engine semantics 영향 명시 |
| positive finite | true | queue | **original positive classification preserved** |
| `LK_INFINITE_WAIT` | true | queue | unchanged |

추가 scenario:

1. holder가 watchdog 전에 release하면 waiter가 성공하고 page가 정확히 한 번 unfix된다.
2. interrupt가 wait 중 도착하면 waiter queue와 `waiter_exists` state가 정리된다.
3. parallel sibling worker 중 한 thread의 scoped flag가 다른 sibling의 policy를 바꾸지 않는다.
4. nested save/restore가 outer flag를 보존한다.
5. volume-header contention과 sector-table contention을 각각 주입한다.
6. failure 뒤 disk cache count, sector bitmap, output VSID array, system-operation state가 원상복구된다.
7. page-latch watchdog을 작은 값으로 설정해 expiry error와 transaction/server 생존을 확인한다.
8. original attachment는 end-to-end smoke test로 유지하되 deterministic matrix를 대체하지 않는다.

## Merge Gates

다음이 충족되기 전에는 merge하면 안 된다.

- [ ] positive finite policy가 `LK_INFINITE_WAIT`로 재분류되지 않도록 구현 수정
- [ ] `structural page`의 membership과 wait-policy invariant를 정의하거나, 정확한 두 page 예외로 terminology/API scope 축소
- [ ] zero-wait structural-page exception의 explicit specification
- [ ] `LK_FORCE_ZERO_WAIT` engine use와의 상호작용 분석
- [ ] volume-header→sector-table 및 관련 reverse-order path audit
- [ ] forced contention에서 zero/force-zero/positive/infinite matrix test
- [ ] page-latch watchdog expiry 시 error/abort behavior test
- [ ] parallel worker와 nested flag lifecycle test
- [ ] reservation partial-failure 뒤 cache/bitmap/system-operation consistency test
- [ ] original repro가 crash만 보지 않고 latency와 error classification도 관찰하도록 보완

## Reviewer-ready Blocking Comment

> **BLOCK:** 이 PR은 original zero-wait crash를 피하지만 transaction wait policy를 무조건 `LK_INFINITE_WAIT`로 덮어씁니다. 따라서 positive finite policy까지 infinite timeout classification으로 바뀌어 page-latch watchdog 만료 시 기존 `ER_LK_PAGE_TIMEOUT` 대신 debug assert 및 `ER_LK_UNILATERALLY_ABORTED` 경로를 선택합니다. 최소한 `LK_ZERO_WAIT`와 `LK_FORCE_ZERO_WAIT`만 override하고 positive/already-infinite 값을 보존해야 합니다.
>
> 더 근본적으로, “사용자 의도는 lock-only”라는 주장은 parameter 이름과 주 용례에 근거한 추론이지 existing behavior contract의 증명이 아닙니다. Exact code는 같은 field를 page-latch admission에 오랫동안 사용했고 engine도 busy-page skip/dead-latch avoidance에 `LK_FORCE_ZERO_WAIT`를 의도적으로 사용합니다. Structural-page exception이 제품 정책이라면 이를 명시하고 zero-wait의 최대 300초 wait 변화, latch ordering, watchdog expiry를 deterministic하게 검증해야 합니다.
>
> 또한 `structural page`는 기존 CUBRID source에 정의된 page category가 아니며, merge-base에는 용례가 없습니다. Exact HEAD의 다섯 용례는 모두 이 PR이 추가했고 type/predicate/membership rule도 없습니다. 현재 override 대상이 volume header와 sector allocation table뿐이라면 generic category 대신 두 page를 정확히 명시해야 합니다. 더 넓은 범주라면 어떤 page가 포함되고 왜 그 범주가 transaction no-wait을 무시해야 하는지 contract와 test가 필요합니다.
>
> 첨부 repro는 original `immediate -76 → assert` mechanism만 검증합니다. PR의 forced-wait 정책, deadlock safety, positive timeout preservation은 검증하지 않으며, PR에는 test 변경이 없습니다. 위 matrix와 consistency gate가 추가되기 전에는 merge할 수 없습니다.

## Final Position

이 PR이 해결하려는 production symptom은 실재한다. Per-thread flag를 선택한 이유—parallel workers가 shared `LOG_TDES`를 사용하므로 transaction field save/restore는 race가 된다는 점—도 합리적이다.

그러나 좋은 motive와 일부 올바른 implementation detail은 merge 기준을 대체하지 않는다.

- 현재 코드는 definite positive-timeout regression을 포함한다.
- `structural page`라는 새 정책 범주가 정의·분류·검증되지 않았다.
- zero-wait 의미를 바꾸는 policy 근거가 specification이 아니라 추론이다.
- progress와 watchdog behavior를 검증하지 않았다.
- concurrency policy change에 test가 하나도 없다.

따라서 exact reviewed HEAD `1185f16d7e5f540ffdad4509cbd061ef0535f4df`에 대한 결정은 **BLOCK / REJECT**다.
