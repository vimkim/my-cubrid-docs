# PR #8611 리뷰: CBRD-27739 page latch timeout이 주인 없는 fix count를 남기는 문제

- PR: https://github.com/CUBRID/cubrid/pull/8611 (작성자 YeunjunLee, base `develop`)
- 리뷰 대상: head `50d4a9a3c275c6d95700c8f6ac22d074e74351fd`, base(`develop`) 및 merge-base `cf9ef288818d7bb8059606ae78edffa1dcbe942d` 대비 diff (`src/storage/page_buffer.c`만 변경)
- 리뷰 일자: 2026-11-18
- 방식: 코드 정독으로만 검토함 (빌드나 재현은 하지 않음). 줄 번호는 PR head 기준이고, 11.4는 `origin/release/11.4` 기준임.
- 주요 소스 링크 (PR head 고정):
  - [`pgbuf_timed_sleep ()` timeout 분기, page_buffer.c:8011-8041](https://github.com/CUBRID/cubrid/blob/50d4a9a3c275c6d95700c8f6ac22d074e74351fd/src/storage/page_buffer.c#L8011-L8041)
  - [`pgbuf_timed_sleep_error_handling ()` case 3, page_buffer.c:7906-7940](https://github.com/CUBRID/cubrid/blob/50d4a9a3c275c6d95700c8f6ac22d074e74351fd/src/storage/page_buffer.c#L7906-L7940)
  - [F1: `thread_wakeup_internal ()`, thread_entry.cpp:755-769](https://github.com/CUBRID/cubrid/blob/50d4a9a3c275c6d95700c8f6ac22d074e74351fd/src/thread/thread_entry.cpp#L755-L769)
  - [F1: `css_stop_non_log_writer ()`, server_support.c:2262-2270](https://github.com/CUBRID/cubrid/blob/50d4a9a3c275c6d95700c8f6ac22d074e74351fd/src/connection/server_support.c#L2262-L2270)
  - [F2: `LK_FORCE_ZERO_WAIT` 처리, page_buffer.c:7973-7977](https://github.com/CUBRID/cubrid/blob/50d4a9a3c275c6d95700c8f6ac22d074e74351fd/src/storage/page_buffer.c#L7973-L7977)

## 결론

**승인 가능.** PR이 설명한 두 경쟁(race)은 모두 실제로 존재한다. 이 PR은 둘을 모두 닫고, 새로 생기는 결함은 찾지 못했다.
다만 같은 증상(fix count 누수)을 내는 **세 번째 경로가 그대로 남아 있다** (F1, 기존 결함).
또한 PR 본문의 Impact 절은 이 결함이 드물게만 나타난다고 하지만, 실제로는 그보다 자주 발생할 수 있다 (F2).
둘 다 이 PR의 병합을 막을 사유는 아니다. 후속 이슈와 11.4 backport로 처리하기를 권한다.

| # | 심각도 | 구분 | 요약 |
|---|---|---|---|
| F1 | Medium | 기존 결함 (잔여 위험) | 무조건 interrupt wakeup이 `THREAD_PGBUF_RESUMED`를 덮어쓰면 grant가 유실됨 |
| F2 | Low (본문 정확성, 우선순위) | PR 본문 | `LK_FORCE_ZERO_WAIT` 요청은 queue에 들어가 0 ms 뒤 timeout됨. 기본 설정에서도 race 창이 자주 열림 |
| F3 | Low | 테스트 및 CI | TC가 확률적이고 release 빌드 전용임. 회귀 CI(gha-ci)가 아직 실행되지 않음 |
| F4 | Info | 기존 결함 | `pgbuf_allocate_bcb ()`의 timeout 분기가 소유하지 않은 entry lock을 unlock함 (PR이 범위 밖으로 명시함). 실제 영향은 PR 설명보다 큼 |
| F5 | Info | 동작 불변 | case 3은 READ가 아닌 다음 대기자에서 멈추고 건너뛰지 않음. 진행은 보장됨 |
| F6 | Info | 기존 결함 | `pgbuf_wakeup_reader_writer ()`가 CAS 재시도 루프 안에서 entry lock을 잡음. 현재는 재시도가 일어나지 않음 |

---

## 1. 프로토콜과 두 race 검증

### 1.1 latch를 넘겨주는 규칙 (granter와 waiter)

- 잠금 순서는 모든 경로에서 **BCB mutex → thread entry lock**이다.
  - granter인 `pgbuf_wakeup_reader_writer ()`는 BCB mutex를 잡은 상태에서 대기자의 entry lock을 잡는다 (page_buffer.c:8201).
  - waiter는 `pgbuf_timed_sleep ()` 진입 시 BCB mutex를 잡은 상태에서 자기 entry lock을 잡고 BCB를 놓는다 (page_buffer.c:7966-7967).
- granter는 entry lock을 잡은 한 구간 안에서 세 일을 한다. `request_latch_mode != PGBUF_NO_LATCH`를 확인하고, `fcnt += request_fix_count`를 더하고, `pgbuf_wakeup ()`으로 `resume_status = THREAD_PGBUF_RESUMED`를 기록한 뒤 unlock한다 (page_buffer.c:8201-8261, 12459-12484).
- 따라서 waiter도 "grant 받았는지 확인"과 "포기(`request_latch_mode = PGBUF_NO_LATCH`)"를 같은 entry lock 안에서 해야 한다. 그래야 granter의 구간과 겹치지 않는다.

### 1.2 race 1: `pgbuf_timed_sleep ()`의 timeout 분기 (확인됨)

- `thread_suspend_timeout_wakeup_and_unlock_entry ()`는 ETIMEDOUT이면 predicate를 다시 보지 않고 루프를 빠져나온다. 그리고 **entry lock을 놓은 채** 반환한다 (thread_entry.cpp:580-599).
- 기존 timeout 분기는 lock 없이 `resume_status`를 읽고 `request_latch_mode = PGBUF_NO_LATCH`를 썼다.

```
W (waiter)                                G (granter, BCB mutex 보유)
timedwait ETIMEDOUT, entry unlock 후 반환
resume_status == SUSPENDED 로 읽음 (lock 없음)
                                          lock(W); W->request_latch_mode == READ
                                          fcnt += 1; queue에서 W 제거
                                          pgbuf_wakeup: RESUMED, unlock(W)
request_latch_mode = NO_LATCH
thread_unlock_entry(W)   <- 소유하지 않은 lock
error_handling: case 1/2 (W는 이미 queue에 없음)
ER_LK_PAGE_TIMEOUT 반환                   -> +1에 주인이 없음
```

- 덧붙여, 기존 코드는 같은 분기에서 소유하지 않은 mutex를 unlock했고, lock 없이 `goto try_again`해서 `pthread_cond_timedwait`를 호출했다.
  - `th_entry_lock`은 속성 없이 초기화된 기본(normal) mutex다 (thread_entry.cpp:178). glibc의 normal mutex는 소유자를 검사하지 않고 그대로 풀어 버린다.
  - 그래서 G가 W의 entry lock을 잡고 있는 동안 W가 unlock하면 G의 상호배제가 깨진다. PR 본문은 이 결과를 "unlock 오류" 정도로만 적었지만, 실제로는 race를 넓히는 두 번째 원인이다. 소유하지 않은 mutex로 `cond_timedwait`를 부르는 것은 정의되지 않은 동작(UB)이다.

### 1.3 race 2: `pgbuf_timed_sleep_error_handling ()` case 3 (확인됨)

- develop의 기존 case 3은 lock 없이 `request_latch_mode == READ`를 읽었다. 그 값으로 CAS를 성공시켜 fcnt를 먼저 더하고, 그 뒤에 entry lock을 잡아 다시 확인했다. 대기자가 이미 포기한 상태면 fcnt를 되돌리지 않고 `break`했다 (diff의 제거된 부분).
- 11.4는 entry lock을 먼저 잡고, 확인한 뒤 더한다 (11.4 page_buffer.c:6560-6567 영역). 이 race는 원자적 latch를 도입한 CBRD-26425에서 생겼다는 PR 설명과 일치한다.

### 1.4 수정이 두 race를 닫는가: 닫는다

- **timeout 분기** (page_buffer.c:8011-8041): `thread_lock_entry (thread_p)`를 먼저 잡는다. 그 뒤 `RESUMED`이면 latch를 가진 채 `NO_ERROR`를 반환한다. 아니면 lock을 잡은 상태에서 `NO_LATCH`를 기록하고 unlock한다. 이제 G의 구간(확인부터 wakeup까지)과 W의 구간(확인부터 포기까지)이 같은 mutex로 직렬화된다. 결과는 둘 중 하나뿐이다. G가 먼저면 W가 `RESUMED`를 보고 latch를 소유한다. W가 먼저면 G가 `NO_LATCH`를 보고 건너뛴다.
- **case 3** (page_buffer.c:7906-7940): lock, 확인, CAS, queue 제거, `pgbuf_wakeup ()` 순서다. entry lock은 확인부터 `pgbuf_wakeup ()`의 unlock까지 이어진다. CAS 재시도 루프도 lock 안에 있으므로 lock을 두 번 잡지 않는다.
- 결과적으로 두 grant 경로 모두에서 `pgbuf_wakeup ()`의 `"already timedout"` 분기(page_buffer.c:12477)에 도달하지 않는다. PR이 지키려는 불변식은 다음과 같다. **fcnt가 더해졌다면, 같은 entry lock 구간 안에서 대기자가 queue에서 빠지고 `RESUMED`를 받는다.** 이 불변식은 위 두 경로에서 성립한다. 단, F1의 외부 writer는 예외다.

### 1.5 새 결함 탐색 결과: 없음

- **lock을 잡은 채 `goto try_again`** (page_buffer.c:8027 → 7983): 처음 진입할 때와 상태가 같다. 둘 다 entry lock 보유, BCB mutex 미보유다. `thread_prepare_suspension ()`의 `m_status` assert는 `thread_prepare_resumption ()`이 이미 상태를 복원했으므로 통과한다. `logtb_is_current_active ()`는 lock을 잡지 않으므로(log_tran_table.c:3347-3364) lock을 쥔 채 불러도 문제없다.
- **interrupt 분기** (r == NO_ERROR, page_buffer.c:7989-8005): 변경되지 않았고, 원래부터 lock을 다시 잡는다.
- **pthread 오류 분기**: `thread_suspend_timeout_wakeup_and_unlock_entry ()`는 이 경우 lock을 쥔 채 반환한다 (thread_entry.cpp:585). 그래서 기존 `else` 분기의 `thread_unlock_entry ()`가 맞다. 변경 없음.
- **잠금 순서 및 deadlock**: 새 코드는 entry → BCB 순서의 중첩을 만들지 않는다. timeout 분기는 entry lock을 놓은 뒤에야 `pgbuf_timed_sleep_error_handling ()`에서 BCB mutex를 잡는다. case 3은 BCB → entry 순서로, 기존 granter와 같다.
- **latch word의 동시 변경**: lock-free fix/unfix는 `waiter_exists`가 false일 때만 동작한다 (page_buffer.c:8421, 8502). 대기자가 queue에 있는 동안에는 이 플래그가 true이므로, case 3 CAS 도중에 latch word를 바꾸는 쪽은 BCB mutex 보유자뿐이다. `compare_exchange_weak`의 spurious failure도 lock 안에서 재시도하므로 안전하다.
- **`waiter_exists`**: case 3이 queue를 비워도 플래그를 지우지 않는 동작은 기존과 같다. 마지막 unfix가 `pgbuf_wakeup_reader_writer ()`를 거쳐 정리한다. 변경 없음.

### 1.6 11.4와 develop의 차이

| | develop (PR 전) | 11.4 |
|---|---|---|
| timeout 분기 race 1 | 있음 | **있음**. 11.4의 `thread_suspend_timeout_wakeup_and_unlock_entry ()`도 timeout 시 unlock 후 반환함 (11.4 thread_entry.cpp:545-569). timeout 분기 코드도 같음 (11.4 page_buffer.c:6668~) |
| case 3 race 2 | 있음 (원자적 latch에서 순서가 바뀜) | 없음 (확인 후 더함) |
| spurious wakeup | predicate 루프로 흡수함 | 루프가 없음. r == 0이면 interrupt로 처리함 (누수는 없음) |

따라서 11.4에는 **timeout 분기 hunk만 backport**하면 된다. F2를 보면 11.4에서도 자주 발생할 수 있다.

---

## 2. Findings

### F1 [Medium, 기존 결함] 무조건 interrupt wakeup이 `RESUMED`를 덮어써서 grant를 잃는다

- **근거**
  - `thread_wakeup_internal ()`은 현재 `resume_status`를 보지 않고 덮어쓴다 (thread_entry.cpp:755-769, 특히 764).
  - `logtb_wakeup_thread_with_tran_index ()`는 상태 확인 없이 `thread_wakeup ()`을 부른다 (log_tran_table.c:6439-6449). deadlock 희생자 처리 경로가 이를 10 ms마다 반복 호출한다 (lock_manager.c:2516-2529).
  - `css_stop_non_log_writer ()`는 `m_status == TS_WAIT`만 확인하고 `THREAD_RESUME_DUE_TO_INTERRUPT`로 깨운다 (server_support.c:2262-2270). W의 `m_status`는 timedwait 안에서 mutex를 다시 얻고 `thread_prepare_resumption ()`을 실행할 때까지 `TS_WAIT`로 남는다.
  - 대조군: `network_sr.c:1029-1081`은 lock 안에서 `resume_status`가 `*_SUSPENDED`일 때만 깨운다. `THREAD_PGBUF_RESUMED`는 건너뛴다.
- **interleaving**

```
W (BCB X에서 READ 대기)            G (granter)                    I (interrupter)
pthread_cond_timedwait 중
                                   lock(W); fcnt += 1; queue에서 제거
                                   RESUMED, signal, unlock(W)
                                                                  lock(W); m_status == TS_WAIT
                                                                  resume_status = INTERRUPT; unlock
mutex 재획득: INTERRUPT != SUSPENDED 이므로 루프 탈출, r = 0
interrupt 분기: lock; RESUMED 아님
request_latch_mode = NO_LATCH; unlock
error_handling: case 1/2 (queue에 없음)
ER_INTERRUPTED 반환                -> +1에 주인이 없음 (CBRD-27739와 같은 증상)
```

  W가 timeout으로 깨어나는 경우에도 같다. 새 timeout 분기는 `RESUMED`를 확인하지만, I가 먼저 `INTERRUPT`로 덮어쓰면 timeout으로 처리하고 누수가 생긴다.
- **영향**: 증상은 이 PR이 고치는 것과 같다. 해당 페이지가 서버 재시작 전까지 latch된 상태로 남고, 종료 시 `pgbuf_flush_all ()`이 멈출 수 있다. 발생 조건은 같은 트랜잭션의 다른 worker가 deadlock 희생자 처리를 하거나 서버가 worker를 정지시키는 경우로 좁다. PR 본문의 "Either way, the fix count has an owner"는 두 grant 경로에 대해서만 참이다.
- **제안 (후속 이슈)**: 둘 중 하나를 택한다.
  - (a) PGBUF 대기자를 깨우는 외부 경로가 `THREAD_PGBUF_SUSPENDED`일 때만 깨우게 한다. `thread_check_suspend_reason_and_wakeup ()`을 쓰거나 network_sr.c 방식을 따른다.
  - (b) grant 여부를 `resume_status`가 아닌, 외부에서 덮어쓰지 않는 필드로 판정한다. 예를 들어 `pgbuf_wakeup ()`이 entry lock 안에서 표시를 남기게 한다.
  
  (b)가 page buffer 안에서 닫히므로 범위가 작다. 이 PR에 넣을 필요는 없다.

### F2 [Low, PR 본문 정확성] "기다리면 안 되는 요청은 queue에 들어가지 않는다"는 설명은 `LK_FORCE_ZERO_WAIT`에 대해 틀리다

- **근거**
  - `pgbuf_latch_bcb_upon_fix ()`는 `LK_ZERO_WAIT`만 즉시 거절한다 (page_buffer.c:7238-7256).
  - `LK_FORCE_ZERO_WAIT`는 `pgbuf_block_bcb ()`로 queue에 들어간다. `pgbuf_timed_sleep ()`은 이를 `wait_msecs = 0`으로 바꿔 바로 timeout시킨다 (page_buffer.c:7973-7977).
  - 사용처
    - bestspace의 heap page WRITE fix (bestspace.cpp:748, 1765). 경합 시 `ER_LK_PAGE_TIMEOUT`을 정상 경로로 처리한다.
    - btree.c:24374
    - 11.4: heap_file.c:3289 (`heap_stats_find_best_page`)
- **의미**: 기본값(`page_latch_timeout_in_msecs` 300초)에서도 insert가 몰리는 heap page에서 0 ms timeout이 계속 생긴다. race 1의 창이 PR 본문이 말하는 "300초 대기 후"보다 훨씬 자주 열린다. 수정 내용은 맞다. 다만 우선순위와 11.4 backport의 필요성이 본문 설명보다 크다.
- **제안**: 본문의 Impact 절을 고친다. 11.4 backport 이슈를 연결한다.

### F3 [Low, 테스트/CI]

- 새 shell TC `cbrd_27739`는 debug 빌드에서 OK를 쓰고 끝난다. release 빌드에서도 확률적이다. PR 본문 기준으로 develop에서 5/5 실패, PR에서 0/10 실패였다.
- F1 경로는 다루지 않는다.
- PR head의 체크는 lint 계열(code-style, cppcheck, license, pr-style)과 TC Merge Gate(설계상 실패)뿐이다. **회귀 CI(gha-ci)는 아직 실행되지 않았다** (`gh pr checks 8611` 기준).
- 제안: 병합 전에 gha-ci를 실행한다. QA의 release 회귀에 이 TC가 포함되는지 확인한다.

### F4 [Info, 기존 결함, PR이 범위 밖으로 명시] `pgbuf_allocate_bcb ()` timeout 분기

- page_buffer.c:9026-9031은 소유하지 않은 entry lock을 unlock하고, lock 없이 `resume_status = THREAD_ALLOC_BCB_RESUMED`를 기록한다.
- 1.2와 같은 이유로 normal mutex의 상호배제가 깨질 수 있다. 이때 victim을 배정하는 쪽은 W의 entry lock을 쥔 채 `bcb_victims[idx]`를 설정한다 (page_buffer.c:16485-16499).
- 그래서 영향은 "latch를 남기지 않는다"보다 넓다. 배정된 direct victim이 유실될 가능성도 있다. 이 부분은 검증하지 않았고 추정이다.
- 코드에 `assert (r != ER_CSS_PTHREAD_COND_TIMEDOUT)`가 있어 드문 경로다. 후속 이슈로 남기면 충분하다.

### F5 [Info] case 3은 READ가 아닌 다음 대기자에서 `break`한다

- `NO_LATCH` 대기자 뒤에 있는 READ 대기자는 이번 호출에서 깨어나지 않는다. `pgbuf_wakeup_reader_writer ()`는 같은 상황에서 건너뛰고 계속한다.
- 이 동작은 PR 전과 같다. 그리고 포기한 대기자는 반드시 자기 `pgbuf_timed_sleep_error_handling ()`을 실행한다. 맨 앞이면 case 3이 되어 뒤의 READ를 넘겨주고, 중간이면 case 2가 되어 자기만 빠진다. 따라서 대기자가 영영 남는 일은 없다. 조치 불필요.

### F6 [Info, 기존 결함] `pgbuf_wakeup_reader_writer ()`가 CAS 재시도 루프 안에서 `thread_lock_entry ()`를 부른다

- 위치: page_buffer.c:8195-8238. CAS가 실패해 루프를 다시 돌면 같은 non-recursive mutex를 다시 잠그거나, 다른 분기로 나가면서 lock을 놓지 않는다.
- 현재는 `compare_exchange_strong`이고, latch word는 BCB mutex 보유자만 바꾸므로 재시도가 일어나지 않는다.
- 이 PR의 case 3은 같은 패턴을 피했다 (lock을 루프 밖에서 잡음). 참고로만 적는다.

---

## 3. 요약 및 권고

1. 이 PR은 그대로 병합해도 된다. 두 race가 실제로 있고, 수정이 granter/waiter의 entry lock 프로토콜에 맞게 두 race를 닫으며, 새 결함은 찾지 못했다.
2. 병합 전: gha-ci를 실행한다 (F3). 본문의 Impact 절을 고친다 (F2).
3. 후속 이슈:
   - interrupt wakeup이 `RESUMED`를 덮어쓰는 경로 (F1)
   - 11.4에 timeout 분기 hunk backport (1.6, F2)
   - `pgbuf_allocate_bcb ()`의 timeout 분기 (F4)
