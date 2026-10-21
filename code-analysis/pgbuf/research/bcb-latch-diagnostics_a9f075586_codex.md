# BCB 래치 대기자의 소유자 추적과 무한 대기 진단 가능성

조사일: 2026-10-07 (Asia/Seoul). 대상: `/home/vimkim/gh/cb/develop`, `develop`, 소스 커밋 `a9f07558634bd84250452149029e85d5fb170e37`. 입력 브리핑: `/tmp/cub_ctv.md` — `cub_ctv`의 critical-section 관측 도구 설명이다. Work Tracker: #300.

이 문서는 현재 소스에서 확인한 사실과 후속 설계 제안을 구분한다. 실제 hang을 재현하거나 특정 장애의 원인을 판정한 결과는 아니다. 엔진과 모니터링 도구의 구현은 변경하지 않았다.

## 판단

**아이디어는 타당하다.** 스레드가 보유한 페이지와 페이지별 대기자를 연결할 자료구조는 이미 있다. BCB에 holder 역참조가 없어도 전체 thread의 holder를 한 번 순회하면 페이지별 소유자 집합을 역산할 수 있다. 다만 다음 두 가지가 필요하다.

1. 현재 자료구조를 다른 thread에서 안전하게 읽는 방법. 단순한 타 thread holder 순회는 현재 엔진의 동시성 규약으로 보호되지 않는다.
2. 소유자가 래치를 놓지 못하는 이유를 보여주는 정보. 보유 페이지 목록만으로는 다른 페이지 대기, CS/transaction lock 대기, I/O, CPU spin, 누락된 wakeup을 구분할 수 없다.

따라서 최초 기능은 **대기 thread → 대상 페이지 → 소유 thread 집합 → 소유 thread의 현재 대기/실행 위치**를 보여주는 진단 기능으로 잡는 것이 좋다. BCB→holder 역참조를 hot path에 먼저 추가해야 하는 것은 아니다.

## 1. 이미 있는 연결과 없는 연결

### thread에서 보유 페이지로

```text
THREAD_ENTRY.m_holder_anchor
  → PGBUF_HOLDER_ANCHOR.thrd_hold_list
  → PGBUF_HOLDER.thrd_link (다음 active holder)
  → PGBUF_HOLDER.bufptr
  → PGBUF_BCB.vpid / atomic_latch
```

`pgbuf_Pool.thrd_holder_info[thread.index]`에서도 동일한 anchor를 찾을 수 있다. `next_holder`는 free 목록용 연결이며 보유 목록은 `thrd_link`로 순회해야 한다. `holder.fix_count`는 해당 thread의 중복 fix 수다. `anchor.num_hold_cnt`는 holder entry 수이므로 BCB의 총 fix count와 같은 의미가 아니다. 근거: [holder/anchor 정의](https://github.com/CUBRID/cubrid/blob/a9f07558634bd84250452149029e85d5fb170e37/src/storage/page_buffer.c#L439-L469), [thread의 anchor](https://github.com/CUBRID/cubrid/blob/a9f07558634bd84250452149029e85d5fb170e37/src/thread/thread_entry.hpp#L334), [holder 탐색](https://github.com/CUBRID/cubrid/blob/a9f07558634bd84250452149029e85d5fb170e37/src/storage/page_buffer.c#L6029-L6057).

WRITE 래치는 한 thread에 귀속되고 READ 래치는 여러 thread가 보유할 수 있으므로 결과는 `owners[]`가 적합하다. 일관된 상태에서 해당 BCB를 가리키는 holder들을 모아 `sum(holder.fix_count)`를 총 `fcnt`와 비교할 수 있으나, 아래 설명하는 전이 중에는 불일치가 정상일 수 있다. 근거: [래치 허용과 중복 fix 판정](https://github.com/CUBRID/cubrid/blob/a9f07558634bd84250452149029e85d5fb170e37/src/storage/page_buffer.c#L6308-L6370).

### 페이지에서 대기 thread로

```text
PGBUF_BCB.next_wait_thrd
  → THREAD_ENTRY.next_wait_thrd
  → request_latch_mode / request_fix_count / wait_for_latch_promote
```

BCB에는 대기 큐의 첫 thread가 있고, 큐는 thread의 `next_wait_thrd`로 연결된다. `pgbuf_block_bcb()`가 READ/WRITE/FLUSH 요청을 기록하고 promoter는 큐 앞, 일반 요청은 뒤에 연결한다. 근거: [BCB 정의](https://github.com/CUBRID/cubrid/blob/a9f07558634bd84250452149029e85d5fb170e37/src/storage/page_buffer.c#L490-L504), [대기 등록](https://github.com/CUBRID/cubrid/blob/a9f07558634bd84250452149029e85d5fb170e37/src/storage/page_buffer.c#L6981-L7028).

**현재 `THREAD_ENTRY`에는 대기 중인 BCB를 직접 가리키는 필드가 없다.** 따라서 engine 변경 없이 찾으려면 BCB들의 대기 큐를 훑어 `thread → waiting BCB` 매핑을 만들어야 한다. `request_latch_mode`만으로 현재 대기 여부를 판정할 수도 없다. 정상 wakeup 함수는 resume 상태를 바꾸지만 해당 필드를 NO_LATCH로 초기화하지 않는다. 큐 소속·resume 상태·thread 상태를 함께 확인해야 한다. 근거: [thread의 래치 대기 필드](https://github.com/CUBRID/cubrid/blob/a9f07558634bd84250452149029e85d5fb170e37/src/thread/thread_entry.hpp#L259-L277), [wakeup](https://github.com/CUBRID/cubrid/blob/a9f07558634bd84250452149029e85d5fb170e37/src/storage/page_buffer.c#L11515-L11540).

이 역산의 자료구조상 비용은 `O(thread 수 + 전체 held holder 수)` 및 `O(BCB 수 + 전체 queued waiter 수)`다. 실제 성능은 `/proc` 읽기 방식과 버퍼 규모에 따라 측정해야 한다. 18개 정적 CS를 고빈도로 읽는 브리핑의 측정치를 전체 BCB 순회에 적용할 수 없다. BCB 배열은 [풀 정의](https://github.com/CUBRID/cubrid/blob/a9f07558634bd84250452149029e85d5fb170e37/src/storage/page_buffer.c#L735-L768)로 확인했다.

## 2. 현재 소유자로 사용하면 안 되는 필드

| 필드 | 실제 의미와 한계 |
| --- | --- |
| `BCB.latch_last_thread` | 최근 일부 래치 획득 경로에서 기록한 thread. 전체 reader 집합도, 검증된 현재 owner도 아니다. |
| `BCB.owner_mutex` | BCB 관리 정보를 보호하는 `pthread_mutex_t`의 모니터링용 소유자. 페이지 READ/WRITE 래치 소유자와 다르다. |
| `BCB.atomic_latch.fcnt` | 총 fix 수. 소유 thread 수가 아니며 중복 fix를 포함한다. |
| `holder.perf_stat.hold_has_*_latch` | 해당 hold 기간에 있었던 모드의 성능 통계. 현재 모드를 그대로 표현하는 단일 필드가 아니다. |

`latch_last_thread`는 실제 guard가 SERVER_MODE만이므로 Release 서버에도 있다. 닫는 주석의 `&& !NDEBUG`를 실제 조건으로 읽으면 안 된다. lock-free READ 획득은 `fcnt`와 holder를 갱신하면서 이 필드는 갱신하지 않는다. 마지막 unfix 때 현재 owner로서 초기화하는 규약도 없다. FLUSH 대기에서 복귀한 thread까지 `pgbuf_block_bcb()` 끝에서 이 필드를 기록한다. 근거: [정의](https://github.com/CUBRID/cubrid/blob/a9f07558634bd84250452149029e85d5fb170e37/src/storage/page_buffer.c#L502-L504), [lock-free READ](https://github.com/CUBRID/cubrid/blob/a9f07558634bd84250452149029e85d5fb170e37/src/storage/page_buffer.c#L7657-L7718), [대기 복귀 후 기록](https://github.com/CUBRID/cubrid/blob/a9f07558634bd84250452149029e85d5fb170e37/src/storage/page_buffer.c#L7098).

`owner_mutex` 갱신은 선택적 `pgbuf_bcbmon_*()` 경로에 있다. `pgbuf_monitor_locks`의 기본값은 false이며 NDEBUG 서버는 설정을 따르고 Debug 서버는 모니터링을 활성화한다. 따라서 Release 기본 설정에서 이 필드로 내부 mutex 소유자도 보장할 수 없다. 근거: [BCB lock 매크로](https://github.com/CUBRID/cubrid/blob/a9f07558634bd84250452149029e85d5fb170e37/src/storage/page_buffer.c#L927-L934), [모니터링 lock](https://github.com/CUBRID/cubrid/blob/a9f07558634bd84250452149029e85d5fb170e37/src/storage/page_buffer.c#L16591-L16622), [초기화 정책](https://github.com/CUBRID/cubrid/blob/a9f07558634bd84250452149029e85d5fb170e37/src/storage/page_buffer.c#L1648-L1654), [설정 기본값](https://github.com/CUBRID/cubrid/blob/a9f07558634bd84250452149029e85d5fb170e37/src/base/system_parameter.c#L4220-L4230), [holder 통계 정의](https://github.com/CUBRID/cubrid/blob/a9f07558634bd84250452149029e85d5fb170e37/src/storage/page_buffer.c#L420-L426).

## 3. API 구현의 핵심 문제는 일관성과 수명이다

holder/anchor의 연결과 데이터는 일반 non-atomic 필드다. 목록은 해당 thread가 관리하며 `th_entry_lock`으로 모든 fix/unfix를 보호하는 규약도 없다. BCB mutex를 잡았다는 사실로 다른 thread의 holder 목록을 안전하게 읽을 수는 없다.

- **추가 중의 창:** allocator가 holder를 active 목록에 먼저 연결하고 caller가 `bufptr`와 `fix_count`를 나중에 채운다. [allocator](https://github.com/CUBRID/cubrid/blob/a9f07558634bd84250452149029e85d5fb170e37/src/storage/page_buffer.c#L5942-L6020), [호출 후 초기화](https://github.com/CUBRID/cubrid/blob/a9f07558634bd84250452149029e85d5fb170e37/src/storage/page_buffer.c#L6391-L6408).
- **grant와 holder 사이의 창:** wakeup 측이 `fcnt`와 모드를 먼저 올리고 대기 큐에서 제거한 뒤 깨운다. holder는 깨어난 thread가 만든다. 따라서 `fcnt > 0`인데 owner holder가 아직 없을 수 있다. [grant와 wakeup](https://github.com/CUBRID/cubrid/blob/a9f07558634bd84250452149029e85d5fb170e37/src/storage/page_buffer.c#L7471-L7514), [복귀 후 holder 생성](https://github.com/CUBRID/cubrid/blob/a9f07558634bd84250452149029e85d5fb170e37/src/storage/page_buffer.c#L6533-L6564).
- **해제 중의 창:** unfix는 thread holder를 감소/제거한 다음 BCB의 `fcnt`를 줄인다. holder가 free 목록으로 넘어가는 과정도 별도의 전이이다. [unfix 순서](https://github.com/CUBRID/cubrid/blob/a9f07558634bd84250452149029e85d5fb170e37/src/storage/page_buffer.c#L3065-L3098), [holder 제거](https://github.com/CUBRID/cubrid/blob/a9f07558634bd84250452149029e85d5fb170e37/src/storage/page_buffer.c#L6130-L6188), [lock-free unfix](https://github.com/CUBRID/cubrid/blob/a9f07558634bd84250452149029e85d5fb170e37/src/storage/page_buffer.c#L7721-L7760).
- **promotion 중의 창:** 여러 reader가 있는 READ→WRITE promotion은 자기 READ fix 수를 빼고 holder를 제거한 뒤 WRITE 대기자로 등록한다. 과거 holder 상태를 현재 wait와 섞으면 잘못된 자기 교착을 표시할 수 있다. [promotion](https://github.com/CUBRID/cubrid/blob/a9f07558634bd84250452149029e85d5fb170e37/src/storage/page_buffer.c#L2853-L2915).
- **BCB 재사용:** 같은 주소의 BCB가 다른 VPID로 바뀔 수 있다. 실제 검색 코드도 mutex 획득 뒤 VPID를 재확인한다. [검색 시 검증](https://github.com/CUBRID/cubrid/blob/a9f07558634bd84250452149029e85d5fb170e37/src/storage/page_buffer.c#L7544-L7577).

결론적으로 다음을 구분해야 한다.

| 관측 방식 | 결과 해석 |
| --- | --- |
| 실행 중인 서버를 외부에서 `/proc/<pid>/mem`으로 읽기 | 서버에 읽기 코드를 실행시키지 않고 후보를 찾을 수 있다. 여러 읽기를 하나의 시점으로 보장하지 않으며 반복 확인으로도 완전한 snapshot은 되지 않는다. 불일치는 unknown/partial로 표시해야 한다. |
| 엔진 내부 API에서 다른 thread의 raw holder 목록 순회 | 지금 있는 락을 임의로 잡는 것으로 안전해지지 않는다. 동시 변경에 대한 C++ data race와 목록 재사용 문제를 해결해야 한다. |
| 적절히 수집한 process/core snapshot | 동시 변경이 멈춘 자료와 모든 thread의 stack을 연결하기 좋다. 다만 fix/grant/unfix 전이 중에 정지한 상태도 고려해야 한다. |
| 새로 동기화하여 공개한 진단용 레코드 | 안정적인 API로 만들 수 있다. 원시 포인터 대신 페이지·thread 식별자와 전이 상태를 공개하고 유효성·수명을 정해야 한다. 이는 후속 설계다. |

진단용 publication을 sequence counter로 설계하더라도 reader가 동시에 수정되는 일반 C++ 필드를 무조건 읽도록 해서는 안 된다. atomic payload, 보호된 복사 또는 수명이 보장된 immutable record 등 실제 데이터 접근 규약을 함께 설계해야 한다. 모든 fix마다 전역 mutex를 잡는 방법은 성능과 새 교착 위험을 평가해야 한다.

## 4. 무한 대기라고 부르는 현상을 구분해야 한다

### 일반 READ/WRITE 대기

`pgbuf_block_bcb()`는 페이지 래치 사이에 교착이 없음을 보장하지 않는다고 설명하고, READ/WRITE가 즉시 허용되지 않으면 timed sleep을 사용한다. `pgbuf_timed_sleep()`은 트랜잭션의 no-wait 정책이면 0, 그 외에는 `pgbuf_latch_timeout_msecs`를 사용한다. 이 값은 숨김 서버 설정 `page_latch_timeout_in_msecs`에서 초기화하며 기본 300,000 ms이다. 트랜잭션 lock의 infinite-wait 정책이 페이지 대기에 무한 sleep을 그대로 적용한다는 뜻은 아니다. 근거: [timed sleep 선택 이유](https://github.com/CUBRID/cubrid/blob/a9f07558634bd84250452149029e85d5fb170e37/src/storage/page_buffer.c#L7078-L7088), [대기 시간 선택](https://github.com/CUBRID/cubrid/blob/a9f07558634bd84250452149029e85d5fb170e37/src/storage/page_buffer.c#L7233-L7260), [timeout 설정](https://github.com/CUBRID/cubrid/blob/a9f07558634bd84250452149029e85d5fb170e37/src/base/system_parameter.c#L5405-L5415).

하지만 timeout 때 `logtb_is_current_active()`가 false이면 `goto try_again`으로 다시 기다린다. rollback/postpone 등의 상황에서는 반복 대기가 가능하다. active 요청은 queue 정리 후 timeout/abort 오류를 만드는 경로이며, 해당 정리가 BCB mutex를 blocking 획득하기 때문에 내부 mutex가 고장 난 경우 watchdog 만료가 즉시 반환을 보장하지도 않는다. 근거: [timeout 재대기 및 정리](https://github.com/CUBRID/cubrid/blob/a9f07558634bd84250452149029e85d5fb170e37/src/storage/page_buffer.c#L7289-L7316), [정리의 mutex 획득](https://github.com/CUBRID/cubrid/blob/a9f07558634bd84250452149029e85d5fb170e37/src/storage/page_buffer.c#L7131-L7144), [active 판정](https://github.com/CUBRID/cubrid/blob/a9f07558634bd84250452149029e85d5fb170e37/src/transaction/log_tran_table.c#L3202-L3217).

### FLUSH 대기

FLUSH는 페이지를 fix하는 래치 모드가 아니라 flush 완료를 기다리는 요청이다. 이 경로는 `thread_suspend_wakeup_and_unlock_entry()`를 호출하며 내부는 timeout 없는 `pthread_cond_wait()`이다. interrupt/shutdown 등의 wakeup은 가능하지만 기본 watchdog은 이 경로에 적용되지 않는다. 근거: [FLUSH 모드 정의](https://github.com/CUBRID/cubrid/blob/a9f07558634bd84250452149029e85d5fb170e37/src/storage/page_buffer.h#L189-L196), [FLUSH suspend](https://github.com/CUBRID/cubrid/blob/a9f07558634bd84250452149029e85d5fb170e37/src/storage/page_buffer.c#L7031-L7069), [untimed wait](https://github.com/CUBRID/cubrid/blob/a9f07558634bd84250452149029e85d5fb170e37/src/thread/thread_entry.cpp#L536-L553).

flush 기다림은 WRITE 소유자의 unfix 후 flush를 기다리는 경우와, 이미 진행 중인 flush 완료를 기다리는 경우를 포함한다. 후자의 수행 thread는 페이지 holder 목록에 반드시 나타나지 않는다. BCB에는 flushing/async-flush flag가 있지만 flush 실행자의 현재 identity 필드는 없다. 따라서 flush 소유자·시작 시각·현재 단계(WAL/DWB/write/post-flush 등)는 별도의 관측 설계가 필요하다. 근거: [safe flush의 두 경우](https://github.com/CUBRID/cubrid/blob/a9f07558634bd84250452149029e85d5fb170e37/src/storage/page_buffer.c#L8760-L8813), [flush 실행과 완료 규약](https://github.com/CUBRID/cubrid/blob/a9f07558634bd84250452149029e85d5fb170e37/src/storage/page_buffer.c#L10648-L10714), [완료 후 wakeup](https://github.com/CUBRID/cubrid/blob/a9f07558634bd84250452149029e85d5fb170e37/src/storage/page_buffer.c#L10853-L10860).

### BCB mutex 대기와 CPU spin

BCB 내부 mutex를 기다리는 thread는 페이지 대기 큐에 아직 들어가지 않았을 수 있다. CAS spin은 잠들지 않으므로 큐나 THREAD_PGBUF_SUSPENDED만 보면 놓칠 수 있다. 현재 소스에는 idle BCB에 잘못 남은 `waiter_exists` 때문에 BCB mutex를 보유한 채 무한 spin할 수 있었다는 설명과 보정 코드가 있다. 이는 **현재 버전의 미수정 결함을 주장하는 것이 아니라**, 페이지 holder/waiter 그래프만으로 관측할 수 없는 hang 종류를 보여주는 소스 근거다. [idle 상태 보정](https://github.com/CUBRID/cubrid/blob/a9f07558634bd84250452149029e85d5fb170e37/src/storage/page_buffer.c#L6255-L6267), [flush waiter 정리의 설명](https://github.com/CUBRID/cubrid/blob/a9f07558634bd84250452149029e85d5fb170e37/src/storage/page_buffer.c#L10917-L10925).

페이지 래치 이외에도 새 BCB/victim 할당 대기는 별도 큐와 THREAD_ALLOC_BCB 상태를 사용한다. 이를 특정 VPID의 래치 owner 대기로 표시하면 안 된다. [할당 대기의 설명과 등록](https://github.com/CUBRID/cubrid/blob/a9f07558634bd84250452149029e85d5fb170e37/src/storage/page_buffer.c#L8140-L8189), [할당 wakeup 판정](https://github.com/CUBRID/cubrid/blob/a9f07558634bd84250452149029e85d5fb170e37/src/storage/page_buffer.c#L8242-L8246).

## 5. “무슨 작업하다 멈췄나”까지 연결할 수 있는가

일부 작업 식별 정보는 이미 있다. `THREAD_ENTRY`의 `type`, `tran_index`, `net_request_index`, `rid`, `query_entry`와 resume 상태를 이용할 수 있다. `rid`는 연결의 request ID이며 작업 종류를 표현하는 것은 `net_request_index`이다. `SHOW THREADS`도 type/status/resume/Net_request/Wait_for_latch_promote를 출력한다. 근거: [thread identity](https://github.com/CUBRID/cubrid/blob/a9f07558634bd84250452149029e85d5fb170e37/src/thread/thread_entry.hpp#L227-L260), [net_request_index](https://github.com/CUBRID/cubrid/blob/a9f07558634bd84250452149029e85d5fb170e37/src/thread/thread_entry.hpp#L272-L288), [SHOW THREADS 변환](https://github.com/CUBRID/cubrid/blob/a9f07558634bd84250452149029e85d5fb170e37/src/query/show_scan.c#L543-L581), [SHOW의 컬럼](https://github.com/CUBRID/cubrid/blob/a9f07558634bd84250452149029e85d5fb170e37/src/parser/show_meta.c#L655-L682).

`tran_index`에서 client user/program/host/PID로 연결하는 코드도 있다. 실행 SQL은 `LOG_TDES.xasl_id`에서 XASL cache의 SQL text를 찾는 기존 tranlist용 흐름이 있지만, 이 코드는 transaction-table CS와 cache 조회를 사용하므로 hang용 별도 endpoint에서 그대로 호출하면 다시 막힐 수 있다. daemon/system thread나 cache에서 사라진 SQL은 문자열이 없는 것이 정상이다. 또한 기존 tranlist의 blocker 조회는 transaction lock manager의 흐름이며 페이지 래치 owner를 제공하는 것으로 해석하면 안 된다. 근거: [client identity 조회](https://github.com/CUBRID/cubrid/blob/a9f07558634bd84250452149029e85d5fb170e37/src/transaction/log_tran_table.c#L2168-L2189), [transaction-table CS](https://github.com/CUBRID/cubrid/blob/a9f07558634bd84250452149029e85d5fb170e37/src/transaction/log_tran_table.c#L2263-L2268), [기존 blocker/SQL 조회](https://github.com/CUBRID/cubrid/blob/a9f07558634bd84250452149029e85d5fb170e37/src/transaction/log_tran_table.c#L2315-L2358).

더 구체적인 실행 위치에는 별도 근거가 필요하다.

| 정보 | 현재 제공 여부와 의미 |
| --- | --- |
| holder의 `fixed_at` | !NDEBUG에서 fix 호출 파일·라인 모음. 현재 실행 stack이나 마지막으로 멈춘 위치가 아니다. Release에는 없다. |
| 현재 페이지 대기 시작 시각 | universal한 공개 thread 필드가 없다. slow-query trace는 suspend 함수의 지역 `start_time`으로 측정하고 조건부로 사용한다. |
| 현재 native stack | holder에서 얻을 수 없다. 기존 `er_dump_call_stack()`는 호출하는 thread 자신의 stack을 얻는다. 타 thread의 현재 stack은 별도 수집 수단이 필요하다. |
| OS native TID | `m_id`는 std::thread::id이며 기존 변환은 pthread_self와 일치시킨다. `/proc/<pid>/task/<tid>`의 Linux TID라고 가정하면 안 된다. |

근거: [Debug holder 필드](https://github.com/CUBRID/cubrid/blob/a9f07558634bd84250452149029e85d5fb170e37/src/storage/page_buffer.c#L440-L450), [fixed_at 기록](https://github.com/CUBRID/cubrid/blob/a9f07558634bd84250452149029e85d5fb170e37/src/storage/page_buffer.c#L11461-L11503), [조건부 지역 시간 측정](https://github.com/CUBRID/cubrid/blob/a9f07558634bd84250452149029e85d5fb170e37/src/thread/thread_entry.cpp#L609-L660), [현재 thread의 backtrace](https://github.com/CUBRID/cubrid/blob/a9f07558634bd84250452149029e85d5fb170e37/src/base/stack_dump.c#L379-L388), [pthread ID 변환/등록](https://github.com/CUBRID/cubrid/blob/a9f07558634bd84250452149029e85d5fb170e37/src/thread/thread_entry.cpp#L330-L358).

기존 `pgbuf_dump_if_any_fixed()`/`pgbuf_dump()`는 CUBRID_DEBUG 영역의 디버깅 함수이며 내부 mutex를 blocking 획득하고 consistency 검사도 한다. 주석부터 동시 사용자가 있으면 좋은 결과를 주지 않는다고 명시한다. 그대로 안정적인 live API로 노출할 함수가 아니다. [dump의 용도와 잠금](https://github.com/CUBRID/cubrid/blob/a9f07558634bd84250452149029e85d5fb170e37/src/storage/page_buffer.c#L11219-L11254), [CUBRID_DEBUG 영역 끝](https://github.com/CUBRID/cubrid/blob/a9f07558634bd84250452149029e85d5fb170e37/src/storage/page_buffer.c#L11459).

## 6. 원인 판정을 돕는 출력

아래는 설명용 가상 예이며 실제 관측 결과가 아니다.

```text
T1: holds page A WRITE; waits page B WRITE for 120 s
T2: holds page B WRITE; waits page A READ for 119 s

T1 → B → T2 → A → T1
```

이런 자료는 교착 후보를 분명하게 보여준다. 하지만 cycle 판정에는 같은 관측 구간의 유효한 ownership과 wait 관계, 요청 모드의 충돌을 확인해야 한다. READ 대기자는 현재 reader와 충돌하지 않아도 앞에 queued writer가 있으면 새 READ 획득이 거절될 수 있으므로 큐 순서도 필요하다. stale/partial 자료로 단정한 cycle은 오탐이 될 수 있다. 근거: [reader도 waiter가 있으면 대기하는 판정](https://github.com/CUBRID/cubrid/blob/a9f07558634bd84250452149029e85d5fb170e37/src/storage/page_buffer.c#L6310-L6332), [wakeup 정책](https://github.com/CUBRID/cubrid/blob/a9f07558634bd84250452149029e85d5fb170e37/src/storage/page_buffer.c#L7406-L7413).

| 관측한 상황 | 추가로 확인할 증거 |
| --- | --- |
| 소유자가 다른 페이지를 기다림 | 해당 페이지의 owners와 전체 wait chain. 교착 후보는 지속성과 snapshot 일관성 확인. |
| 소유자가 CS/transaction lock을 기다림 | 해당 자원의 owner/queue로 이어지는 다른 종류의 wait edge. |
| 소유자가 I/O/WAL/DWB/flush 중 | native stack 또는 공개한 작업 단계, OS 상태와 경과 시간. |
| 페이지는 idle인데 waiter가 남아 있고 변화 없음 | queue/grant 전이, wakeup predicate·signal 기록과 여러 시점의 상태. |
| fcnt가 있지만 holder가 없음 | 먼저 grant/unfix 전이와 partial 관측을 배제한 뒤 누락된 holder/누수 가설 검토. |
| CPU를 쓰는데 큐에는 대기자가 없음 | native stack과 반복 샘플로 CAS spin/livelock 경로 확인. |

**소유자와 페이지를 알면 원인 조사 범위를 크게 줄일 수 있다. 그것만으로 “왜 unfix/wakeup이 일어나지 않았는가”를 자동 확정할 수는 없다.** wakeup 누락이나 잘못된 전이를 입증하려면 bounded event history 또는 실제 stack과 소스 경로가 필요하다.

## 7. 작은 단계로 구현하는 제안

아래 항목은 구현 완료된 기능이 아니라 이 조사에서 도출한 순서다.

### A. 엔진 변경 없이 관측의 유용성 확인

`/proc/<pid>/mem` 도구에서 BCB의 VPID/atomic latch/flags/wait queue와 thread holder 목록을 읽어 후보를 연결할 수 있다. 브리핑의 layout 검증·정보 강등 원칙을 유지하되, BCB/holder의 빌드별 layout 및 live 동시 변경에 대한 검증을 새로 마련해야 한다. 긴 대기의 지속 여부와 부분 결과를 먼저 보여준다. `/proc`가 래치 의미를 직접 제공하는 것은 아니며, 이 방식은 엔진 메모리를 외부에서 해석하는 것이다. 입력 브리핑은 현재 BCB와 lock_manager를 범위 밖으로 명시하므로 `cub_ctv`/`cub_top`에 이 기능이 이미 구현되어 있다고 이번 조사로 주장할 수 없다.

### B. 대기 진단에 필요한 정보만 공개

thread가 실제 block에 들어가고 나오는 경계에서 다음을 일관되게 공개하는 기능부터 설계한다.

| 자료 | 현재 소스와 추가 작업 |
| --- | --- |
| thread index/type, transaction identity, network request | 기존 자료 활용. slot 재사용과 transaction identity 변화를 검증. |
| 대기 대상 BCB slot + VPID, request mode, promote 여부 | mode/promote는 기존에 있다. target의 직접 연결과 일관된 공개는 추가. |
| monotonic 대기 시작 시각, wait epoch, 단계 | 현재의 정확한 지속 시간과 같은 대기의 재관측을 위해 추가. |
| block 시점에 보유한 페이지와 fix 수 | 자기 thread가 안전하게 복사한 bounded record를 공개하는 방안. 결과에는 block 시점 자료임을 표시. |
| caller 위치 또는 bounded stack PCs | Debug fixed_at과 별개로 선택적 진단 계측. 심볼 해석/문자열 출력은 hot path 밖에서 수행. |
| Linux native TID | OS의 CPU/I/O/wchan과 연결할 필요가 있으면 thread 등록 시 기록. |

block 시점의 자기 holder snapshot은 raw 타 thread 순회를 피하는 작은 시작점이다. 하지만 running/spinning owner의 현재 보유 상태까지 제공하지는 않으므로 그런 owner는 unknown으로 남겨야 한다. 모든 fix마다 live ownership을 공개하는 확장은 계측 비용과 grant/promote/unfix의 전이 규약을 별도로 검증해야 한다.

### C. 소유자의 정체 지점과 hang 때의 접근성을 확장

필요성이 확인되면 현재 owner 목록의 안전한 publication, flush 실행자/시작 시각/단계, 짧은 acquire/release/enqueue/grant/wakeup 이력을 추가한다. dump/API는 정상 worker pool과 SQL 실행 경로가 막혀도 진단 자료를 읽을 수 있도록 별도 경로를 검토한다. endpoint가 별도 thread라는 이유만으로 hang에 강해지는 것은 아니다. 자료 수집도 문제의 latch/CS/mutex에 무기한 대기하지 않아야 하며, busy·partial·stale·truncated를 표현하고 serializing/logging 전에 내부 lock을 놓는 규약이 필요하다.

이 순서라면 초기 요구를 “모든 래치의 완전한 deadlock 탐지 API”로 키우지 않고, **긴 페이지 대기에서 대상 페이지와 thread의 보유 페이지를 보여주는 기능**으로 시작할 수 있다. 이후 실제 사례에서 부족한 ownership·현재 stack·flush stage를 수집해 확장 근거를 만들 수 있다.

## 8. 조사 및 검증 기록

- 필수 personal CUBRID 정책과 source/docs의 적용 지침, `/tmp/cub_ctv.md`를 읽었다. 기존 knowledge base의 page-buffer/inspector 조사도 검색하고 현재 소스로 다시 확인했다.
- `gh-pr-info`는 현재 `develop`에 여러 과거 PR이 매칭되어 exit 2였다. 이 조사에 해당하는 단일 PR identity/head repository/headRefName/baseRefName을 선택하지 않았다. “PR 없음”과 다른 lookup 결과이다.
- `rg`, `nl -ba`, 함수 주변 source 읽기로 구조체·grant·wait·wakeup·unfix·promotion·timeout·Debug guard를 확인했다. research background agent가 ownership와 snapshot 전이를 별도로 검토했다.
- 통합 보고서의 58개 source 링크(9개 파일)는 고정 commit과 유효한 줄 범위를 확인했고, code fence 및 staged diff 공백 검사를 통과했다. background agent가 통합 문서의 snapshot·현재 stack·MVP 한계도 재검토하여 수정이 필요한 source overclaim을 찾지 못했다.
- 분석한 주요 파일에는 HEAD 대비 working-tree diff가 없었다. `page_buffer.c`의 working file, `git show HEAD:src/storage/page_buffer.c`, 해당 commit의 GitHub raw 파일 모두 SHA-256 `34b1b4392bba2e8c6d17b99f315d88df5469fac6a1e2c39a55d4e5a53ca18ebd`로 일치했다. 줄 수 17,485.
- 소스 변경·빌드·부하 측정·hang 재현은 수행하지 않았다. 따라서 제안의 성능, 실제 장애 원인, 기존 외부 도구의 구현 품질은 이번 정적 조사로 검증하지 않았다.
- `develop`의 기존 CCI/JDBC 및 untracked 사용자 파일은 보존했다. 결과 문서는 별도 `my-cubrid-docs` topic worktree에서만 작성했다.
