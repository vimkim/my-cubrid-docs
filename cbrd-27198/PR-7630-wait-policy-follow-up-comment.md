추가로 `PGBUF_UNCONDITIONAL_LATCH`와 transaction wait policy의 관계를 확인해 보았습니다.

두 값은 서로 다른 축으로 보입니다.

| 구분 | 의미 |
|---|---|
| `PGBUF_UNCONDITIONAL_LATCH` | Caller가 요청한 page-latch admission condition |
| `tdes->wait_msecs` | Transaction의 wait policy: zero, positive finite 또는 infinite |

PR 적용 전 동작은 다음과 같습니다.

| Latch request | Original transaction policy | PR 적용 전 동작 |
|---|---|---|
| `PGBUF_UNCONDITIONAL_LATCH` | `LK_ZERO_WAIT` 또는 `LK_FORCE_ZERO_WAIT` | Conditional로 강등되어 busy latch에서 즉시 실패 |
| `PGBUF_UNCONDITIONAL_LATCH` | positive finite | Unconditional 유지, waiter queue 진입 |
| `PGBUF_UNCONDITIONAL_LATCH` | `LK_INFINITE_WAIT` | Unconditional 유지, waiter queue 진입 |

즉 `PGBUF_UNCONDITIONAL_LATCH`를 요청했다는 사실이 transaction policy도 반드시 `LK_INFINITE_WAIT`라는 의미는 아닙니다. Positive finite policy를 가진 transaction도 동일한 volume-header 또는 sector-table fix 경로에 들어갈 수 있습니다.

그런데 현재 PR에서는 `force_latch_wait`가 설정되면 original `tdes->wait_msecs`를 확인하기 전에 무조건 `LK_INFINITE_WAIT`를 반환합니다.

```c
if (flag_owner_p != NULL && flag_owner_p->force_latch_wait)
  {
    return LK_INFINITE_WAIT;
  }
```

Source: [`page_buffer.c:16922-16949`](https://github.com/CUBRID/cubrid/blob/1185f16d7e5f540ffdad4509cbd061ef0535f4df/src/storage/page_buffer.c#L16922-L16949)

그 결과 PR 적용 후에는 다음과 같이 변경됩니다.

| Original transaction policy | PR 적용 전 | PR 적용 후 |
|---|---|---|
| `LK_ZERO_WAIT` / `LK_FORCE_ZERO_WAIT` | Conditional로 강등되어 즉시 실패 | `LK_INFINITE_WAIT`로 override되어 waiter queue 진입 |
| positive finite | Waiter queue 진입, original positive classification 보존 | Waiter queue 진입하지만 `LK_INFINITE_WAIT`로 재분류 |
| `LK_INFINITE_WAIT` | Waiter queue 진입, infinite classification | 실질적으로 변경 없음 |

Positive finite와 infinite는 모두 실제 latch wait에 별도 `page_latch_timeout_in_msecs`를 사용하므로, 정상적으로 latch를 획득하면 차이가 드러나지 않습니다. 차이는 watchdog 만료 후 error handling에서 발생합니다.

| `old_wait_msecs` | Watchdog 만료 후 경로 |
|---|---|
| positive finite | `ER_LK_PAGE_TIMEOUT` 반환 |
| `LK_INFINITE_WAIT` | Debug assert 후 `ER_LK_UNILATERALLY_ABORTED` classification |

Source: [`page_buffer.c:7375-7420`](https://github.com/CUBRID/cubrid/blob/1185f16d7e5f540ffdad4509cbd061ef0535f4df/src/storage/page_buffer.c#L7375-L7420)

따라서 이 PR은 original ticket의 zero-wait 동작뿐 아니라 positive finite transaction의 timeout classification도 변경합니다.

이 변경도 의도된 것인지 확인 부탁드립니다. 목적이 zero-wait transaction의 두 structural-page fix만 기다리게 하는 것이라면, 최소한 original policy를 먼저 확인하고 `LK_ZERO_WAIT`와 `LK_FORCE_ZERO_WAIT`만 override하며 positive finite와 already-infinite policy는 보존해야 하지 않을까요?
