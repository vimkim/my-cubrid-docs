# PR #7630 `LK_FORCE_ZERO_WAIT` Preservation Recommendation

**PR:** [CUBRID/CUBRID#7630](https://github.com/CUBRID/cubrid/pull/7630)
**HEAD SHA:** `d9ceb5317c4d5bf15d2bcd2e89c08c2db9de3530`
**작성 일시:** 2026-08-26

> **TL;DR:** `force_latch_wait`는 사용자 설정에서 유래한 `LK_ZERO_WAIT`만 `LK_INFINITE_WAIT`으로 승격하고, 엔진 내부의 dead-latch 회피 정책인 `LK_FORCE_ZERO_WAIT`은 보존하는 것을 권장한다. Production에서는 force-zero가 즉시 포기 의미를 유지하고, debug에서는 두 정책이 충돌하는 순간을 `assert`로 탐지한다.

## Problem

현재 [`pgbuf_find_current_wait_msecs()`](https://github.com/CUBRID/cubrid/blob/d9ceb5317c4d5bf15d2bcd2e89c08c2db9de3530/src/storage/page_buffer.c#L16880-L16910)은 `force_latch_wait`가 설정되면 다음 두 값을 모두 `LK_INFINITE_WAIT`으로 승격한다.

```c
if (wait_msecs == LK_ZERO_WAIT || wait_msecs == LK_FORCE_ZERO_WAIT)
```

두 값은 같은 no-wait 계열이지만 interface 의미가 다르다.

| Value | Owner | Meaning |
|---|---|---|
| `LK_ZERO_WAIT` | 사용자 transaction 정책 | `lock_timeout=0`에서 유래한 fail-fast 정책 |
| `LK_FORCE_ZERO_WAIT` | 엔진 내부 progress 정책 | busy page를 건너뛰거나 이미 latch를 보유한 경로의 dead-latch를 회피 |

실제 사용처도 이 차이를 보여 준다.

- [`bestspace.cpp:680`](https://github.com/CUBRID/cubrid/blob/d9ceb5317c4d5bf15d2bcd2e89c08c2db9de3530/src/storage/bestspace.cpp#L672-L688)은 contended page를 기다리지 않고 `CONTENDED` 결과로 처리한다.
- [`btree.c:19764`](https://github.com/CUBRID/cubrid/blob/d9ceb5317c4d5bf15d2bcd2e89c08c2db9de3530/src/storage/btree.c#L19760-L19778)은 B-tree page latch를 보유한 상태의 추가 fix가 `dead latch`를 만들 수 있어 `LK_FORCE_ZERO_WAIT`을 사용한다고 명시한다.

따라서 향후 다음 호출 경로가 생기면 엔진의 dead-latch 회피 정책이 무력화될 수 있다.

```text
caller sets LK_FORCE_ZERO_WAIT
  -> caller holds another page latch
  -> disk_get_volheader() or disk_stab_cursor_fix()
  -> force_latch_wait maps FORCE_ZERO to INFINITE
  -> thread waits for a disk metadata latch
```

현재 HEAD에서 이 위험을 실제 cycle로 만드는 구체적인 호출 경로는 확인되지 않았다. 이 제안은 확정된 regression 수정이 아니라 두 정책의 의미를 분리해 미래의 잘못된 조합을 방지하는 hardening이다.

## Recommendation

정책 결합 seam인 `pgbuf_find_current_wait_msecs()`에서 사용자 `LK_ZERO_WAIT`만 승격하고, `LK_FORCE_ZERO_WAIT`은 보존한다.

```c
#if defined (SERVER_MODE)
  THREAD_ENTRY *flag_owner_p = (thread_p != NULL) ? thread_p : thread_get_thread_entry_info ();

  if (flag_owner_p != NULL && flag_owner_p->force_latch_wait)
    {
      if (wait_msecs == LK_ZERO_WAIT)
	{
	  return LK_INFINITE_WAIT;
	}

      /* LK_FORCE_ZERO_WAIT is an engine-internal progress policy used to avoid dead latches or
       * skip contended pages. */
      assert (wait_msecs != LK_FORCE_ZERO_WAIT);
    }
#endif /* SERVER_MODE */

  return wait_msecs;
```

이 구현은 다음 두 동작을 동시에 제공한다.

- Production: `assert`가 제거되어도 최종 `return wait_msecs`가 `LK_FORCE_ZERO_WAIT`을 그대로 반환하므로 latch wait로 승격되지 않는다.
- Debug: `force_latch_wait`와 `LK_FORCE_ZERO_WAIT`이 동시에 활성화되는 순간에 assert하여 위험한 호출 조합을 조기에 발견한다.

`assert_release()`는 release 서버까지 종료시킬 수 있으므로 사용하지 않는 것을 권장한다. Assertion을 두 disk helper에 중복 배치하는 대신 `pgbuf_find_current_wait_msecs()`에 두면 정책 결합 지점 한 곳에서 현재와 미래의 모든 caller를 검증할 수 있어 locality가 높다.

## Existing Indirect Path

`bestspace -> pgbuf_ordered_fix() -> debug page validation -> disk helper`의 간접 진입은 존재하지만 이 assertion의 오탐이 아니다. [`disk_is_page_sector_reserved_with_debug_crash()`](https://github.com/CUBRID/cubrid/blob/d9ceb5317c4d5bf15d2bcd2e89c08c2db9de3530/src/storage/disk_manager.c#L4194-L4245)이 helper 진입 전에 transaction wait를 `LK_INFINITE_WAIT`으로 바꾸고, 종료할 때 기존 `LK_FORCE_ZERO_WAIT`을 복원하기 때문이다.

```text
bestspace sets FORCE_ZERO
  -> validator saves FORCE_ZERO
  -> validator sets INFINITE
  -> disk helper sees INFINITE: assertion does not fire
  -> validator restores FORCE_ZERO
  -> ordered fix continues with FORCE_ZERO
```

## Verification Matrix

| Original wait | `force_latch_wait` | Effective wait | Expected debug result |
|---|---:|---|---|
| `LK_ZERO_WAIT` | `true` | `LK_INFINITE_WAIT` | continue |
| `LK_FORCE_ZERO_WAIT` | `true` | `LK_FORCE_ZERO_WAIT` | assert |
| positive finite | `true` | original value | continue |
| `LK_INFINITE_WAIT` | `true` | `LK_INFINITE_WAIT` | continue |
| any value | `false` | original value | continue |

## Optional Naming Improvement

현재 이름 `force_latch_wait`는 모든 no-wait 정책을 덮어쓴다는 인상을 준다. 변경 범위를 넓힐 수 있다면 `override_user_zero_wait`처럼 사용자 `LK_ZERO_WAIT`만 대상으로 한다는 이름이 interface를 더 정확하게 표현한다. 현재 PR을 작게 유지하려면 조건 수정과 debug assertion만으로 충분하다.
