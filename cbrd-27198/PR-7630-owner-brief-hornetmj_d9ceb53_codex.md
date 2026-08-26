# PR #7630 Module Owner Brief for `@hornetmj`

**수신:** 민준 팀장님 (`@hornetmj`)  
**PR:** [CUBRID/CUBRID#7630](https://github.com/CUBRID/cubrid/pull/7630)  
**검토 HEAD:** `d9ceb5317c4d5bf15d2bcd2e89c08c2db9de3530`  
**상세 분석:** [PR #7630 `LK_FORCE_ZERO_WAIT` Preservation Recommendation](https://github.com/vimkim/my-cubrid-docs/blob/main/cbrd-27198/PR-7630-preserve-lk-force-zero-wait_d9ceb53_codex.md)

## Conclusion

PR의 정책과 원래 CBRD-27198 수정은 수용 가능하다. 다만 [`pgbuf_find_current_wait_msecs()`](https://github.com/CUBRID/cubrid/blob/d9ceb5317c4d5bf15d2bcd2e89c08c2db9de3530/src/storage/page_buffer.c#L16880-L16910)이 `LK_ZERO_WAIT`뿐 아니라 엔진 내부의 `LK_FORCE_ZERO_WAIT`까지 `LK_INFINITE_WAIT`으로 바꾸는 조건은 좁힐 것을 권장한다.

## Evidence

- **원래 결함은 계속 해결된다.** 사용자 `lock_timeout=0`은 [`tdes->wait_msecs = 0`](https://github.com/CUBRID/cubrid/blob/d9ceb5317c4d5bf15d2bcd2e89c08c2db9de3530/src/transaction/log_tran_table.c#L2553-L2569), 즉 `LK_ZERO_WAIT`이다. disk helper가 `force_latch_wait=true`인 동안 이 값만 `LK_INFINITE_WAIT`으로 승격해도 [`PGBUF_UNCONDITIONAL_LATCH`의 conditional 강등](https://github.com/CUBRID/cubrid/blob/d9ceb5317c4d5bf15d2bcd2e89c08c2db9de3530/src/storage/page_buffer.c#L2227-L2236)은 방지된다.
- **`LK_FORCE_ZERO_WAIT`은 사용자 설정 값이 아니다.** `lock_timeout`의 [`lower_limit`은 `-1`](https://github.com/CUBRID/cubrid/blob/d9ceb5317c4d5bf15d2bcd2e89c08c2db9de3530/src/base/system_parameter.c#L1345-L1357)이고 range checker가 그보다 작은 값을 거절한다. 반면 [`LK_FORCE_ZERO_WAIT`은 `-2`](https://github.com/CUBRID/cubrid/blob/d9ceb5317c4d5bf15d2bcd2e89c08c2db9de3530/src/transaction/lock_manager.h#L55-L62)다.
- **실제 writer는 엔진 progress 경로다.** [`bestspace`](https://github.com/CUBRID/cubrid/blob/d9ceb5317c4d5bf15d2bcd2e89c08c2db9de3530/src/storage/bestspace.cpp#L675-L688)는 busy page를 건너뛰기 위해, [`btree`](https://github.com/CUBRID/cubrid/blob/d9ceb5317c4d5bf15d2bcd2e89c08c2db9de3530/src/storage/btree.c#L19760-L19778)는 이미 latch를 보유한 경로의 dead-latch를 피하기 위해 이 값을 설치한다.

현재 HEAD에서 `LK_FORCE_ZERO_WAIT -> disk helper`가 실제 latch cycle을 만드는 확정 경로는 확인하지 못했다. 따라서 확인된 regression이 아니라 사용자 wait 정책과 엔진 progress 정책의 경계를 보존하는 예방적 hardening이다.

## Recommended Change

`force_latch_wait`가 설정되어도 사용자 `LK_ZERO_WAIT`만 `LK_INFINITE_WAIT`으로 승격하고, `LK_FORCE_ZERO_WAIT`은 production에서 보존한다. Debug에서는 두 정책이 동시에 관측되면 정책 결합 지점에서 assert하여 새로운 위험 경로를 조기에 발견한다.

```c
if (flag_owner_p != NULL && flag_owner_p->force_latch_wait)
  {
    if (wait_msecs == LK_ZERO_WAIT)
      {
	return LK_INFINITE_WAIT;
      }

    assert (wait_msecs != LK_FORCE_ZERO_WAIT);
  }

return wait_msecs;
```

이 변경은 CBRD-27198의 사용자 no-wait 재현을 그대로 해결하면서, 엔진 내부 dead-latch 회피 값을 무한 대기로 바꾸는 부작용을 막는다. 300초 `page_latch_timeout_in_msecs` watchdog은 장시간 대기의 안전망이지 latch deadlock이 불가능하다는 증거는 아니다.

