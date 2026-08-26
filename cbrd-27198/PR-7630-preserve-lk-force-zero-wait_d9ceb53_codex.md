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

## Why the Original CBRD-27198 Failure Remains Fixed

이 권장 수정은 원래 PR이 해결하려던 `lock_timeout=0` 재현의 동작을 바꾸지 않는다. 원래 재현의 입력은 엔진 내부 값인 `LK_FORCE_ZERO_WAIT`이 아니라 사용자 설정에서 유래한 `LK_ZERO_WAIT`이기 때문이다.

코드상 전달 경로는 다음과 같다.

1. [`db_admin.c:2934-2937`](https://github.com/CUBRID/cubrid/blob/d9ceb5317c4d5bf15d2bcd2e89c08c2db9de3530/src/compat/db_admin.c#L2934-L2937)은 `lock_timeout`이 양수일 때만 1,000을 곱한다. 따라서 사용자가 설정한 `0`은 그대로 `tran_reset_wait_times(0)`에 전달된다.
2. [`tran_reset_wait_times()`](https://github.com/CUBRID/cubrid/blob/d9ceb5317c4d5bf15d2bcd2e89c08c2db9de3530/src/transaction/transaction_cl.c#L170-L175)는 이 값을 서버로 전달하고, [`xlogtb_reset_wait_msecs()`](https://github.com/CUBRID/cubrid/blob/d9ceb5317c4d5bf15d2bcd2e89c08c2db9de3530/src/transaction/log_tran_table.c#L2553-L2569)가 `tdes->wait_msecs = 0`으로 저장한다. enum 정의상 이 값은 [`LK_ZERO_WAIT`](https://github.com/CUBRID/cubrid/blob/d9ceb5317c4d5bf15d2bcd2e89c08c2db9de3530/src/transaction/lock_manager.h#L55-L62)이다.
3. PR은 volume header fix와 sector allocation table fix 직전에 각각 `force_latch_wait=true`를 설정한다: [`disk_get_volheader_internal()`](https://github.com/CUBRID/cubrid/blob/d9ceb5317c4d5bf15d2bcd2e89c08c2db9de3530/src/storage/disk_manager.c#L3227-L3237), [`disk_stab_cursor_fix()`](https://github.com/CUBRID/cubrid/blob/d9ceb5317c4d5bf15d2bcd2e89c08c2db9de3530/src/storage/disk_manager.c#L3501-L3515).
4. 권장 구현의 `pgbuf_find_current_wait_msecs()`는 `force_latch_wait=true`이면서 `wait_msecs == LK_ZERO_WAIT`이면 현재 PR과 동일하게 `LK_INFINITE_WAIT`을 반환한다.
5. 따라서 [`pgbuf_fix_internal()`의 강등 조건](https://github.com/CUBRID/cubrid/blob/d9ceb5317c4d5bf15d2bcd2e89c08c2db9de3530/src/storage/page_buffer.c#L2227-L2236)인 `LK_ZERO_WAIT || LK_FORCE_ZERO_WAIT`에 해당하지 않는다. `PGBUF_UNCONDITIONAL_LATCH` 요청은 conditional request로 강등되지 않고 latch 대기에 진입한다.

```text
SET SYSTEM PARAMETERS 'lock_timeout=0'
  -> tdes->wait_msecs = 0 = LK_ZERO_WAIT
  -> disk helper sets force_latch_wait = true
  -> recommended mapping: LK_ZERO_WAIT -> LK_INFINITE_WAIT
  -> unconditional fix is not demoted to conditional
  -> contention waits instead of returning ER_LK_PAGE_TIMEOUT immediately
```

원래 재현에 대한 현재 PR과 권장 수정의 결과는 동일하다.

| Case | Current PR | Recommended change |
|---|---|---|
| User `lock_timeout=0` (`LK_ZERO_WAIT`) | `LK_INFINITE_WAIT` | `LK_INFINITE_WAIT` |
| Engine `LK_FORCE_ZERO_WAIT` | `LK_INFINITE_WAIT` | preserve force-zero; debug assert |

따라서 원래 결함인 “사용자 no-wait 설정 때문에 disk manager의 unconditional latch가 즉시 conditional로 강등되고 `ER_LK_PAGE_TIMEOUT`을 반환하는 현상”은 계속 해결된다. 달라지는 것은 원래 재현과 별개인 엔진 내부 `LK_FORCE_ZERO_WAIT` 정책뿐이다.

이 결론은 no-wait로 인한 **즉시 거절 경로**가 제거된다는 의미다. 실제 latch wait는 `page_latch_timeout_in_msecs` watchdog, interrupt 또는 다른 오류로 종료될 수 있으므로 모든 disk latch 실패가 불가능해진다는 뜻은 아니다.

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
