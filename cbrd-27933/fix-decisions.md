# CBRD-27933 수리 결정

- 결정일은 2026-11-05 (Asia/Seoul)이다. 작업 추적은 Work 786이다.
- 소스 기준은 `feature/oos-merge` 의 `d52b1889e907abcf84190ec504dde3bc93de260d` 이다. PR #8350은 이 커밋으로 squash 병합되었다.
- 결정의 런타임 근거는 [repro-analysis.md](repro-analysis.md)에 있다. 이 문서는 무엇을 왜 정했는지만 적는다.

## 결정 요약

| 항목 | 결정 | 상태 |
| --- | --- | --- |
| 수리 방향 | 선택지 B. 헤더 조회 실패를 오류로 반환하고, 그 로그 블록을 `interrupted` 로 넘겨 나중에 다시 실행한다 | 결정. [리뷰어 답](https://github.com/CUBRID/cubrid/pull/8350#discussion_r4477032325) 대기 |
| 결정 1. debug 정책 | 헤더 조회 실패를 vacuum assert의 허용 목록에 넣는다. "OOS 플래그는 있는데 OOS 파일이 없는" 논리 결함에는 그 결함이 지나가는 경로에 debug assert를 새로 둔다 | 결정 |
| 결정 2. 회귀 테스트 빌드 | `heap_oos_find_vfid` 조회 앞에 debug 전용 장애 주입점을 두고 debug 테스트를 만든다. release 증거는 기존 latch timeout 테스트로 유지한다 | 결정 |
| 결정 3. 기준 브랜치 | `feature/oos-merge` | PR #8350 병합으로 해소 |

선택지 B를 고른 근거는 [repro-analysis.md의 구현 선택지](repro-analysis.md#구현-선택지)와 [선택지 B prototype 결과](repro-analysis.md#선택지-b-prototype-결과)에 있다. 리뷰어가 제안한 방향은 같은 페이지 재시도였다. 그와 다르게 정한 이유는 PR #8350 스레드의 [답글](https://github.com/CUBRID/cubrid/pull/8350#discussion_r4477032325)로 알렸다.

## 결정 1. debug 빌드에서 헤더 조회 실패를 다루는 방식

### 정한 내용

1. vacuum 워커의 헤더 조회 실패를 debug assert가 허용하는 이유에 넣는다. 그러면 debug에서도 B의 블록 재실행 경로가 실행된다. 다른 예상 밖 오류에서는 지금처럼 바로 멈춘다.
2. "OOS 플래그는 있는데 그 heap에 OOS 파일이 없는" 경우에는 debug assert를 새로 둔다. 위치는 이 경우가 실제로 지나가는 성공 경로다. 이 경우는 debug에서 바로 멈춘다.

### 현재 코드

vacuum 워커가 블록을 끝까지 처리하지 못했을 때, debug assert가 인정하는 이유는 셧다운과 메모리 부족뿐이다.

- [`vacuum_finished_block_vacuum`](https://github.com/CUBRID/cubrid/blob/d52b1889e907abcf84190ec504dde3bc93de260d/src/query/vacuum.c#L4029-L4031) 은 미완료 블록이 셧다운이나 `ER_OUT_OF_VIRTUAL_MEMORY` 때문인지 assert한다.
- [`vacuum_check_shutdown_interruption`](https://github.com/CUBRID/cubrid/blob/d52b1889e907abcf84190ec504dde3bc93de260d/src/query/vacuum.c#L8271-L8278) 은 vacuum 워커의 오류가 셧다운 중의 `ER_INTERRUPTED` 인지 assert한다. 레코드 준비가 실패하면 [`vacuum_heap_page`](https://github.com/CUBRID/cubrid/blob/d52b1889e907abcf84190ec504dde3bc93de260d/src/query/vacuum.c#L1779-L1795) 가 이 함수를 부른다.

B는 헤더 조회 실패를 오류로 올려 보낸다. 이 두 assert를 그대로 두면 debug는 B의 처리 경로에 들어서는 순간 멈춘다.

### 허용 목록에 넣는 이유

assert는 코드가 틀렸을 때만 일어나는 상황, 곧 논리 결함을 잡는 장치다. 빨리 멈추는 것은 논리 결함에서 가치가 있다.

헤더 조회 실패는 논리 결함이 아니다. 원인은 헤더 페이지의 latch timeout과 헤더 페이지 I/O 오류다. 둘 다 코드가 맞아도 부하나 실행 환경 때문에 일어난다. 재현에서는 다른 스레드가 헤더 페이지를 latch timeout보다 오래 잡는 것만으로 이 실패가 났다 ([E2](repro-analysis.md#관측-결과)).

B를 넣으면 이 실패는 설계된 처리 경로를 탄다. 블록은 `interrupted` 로 남고 나중에 다시 실행되며, OOS 값을 잃지 않는다 ([선택지 B prototype 결과](repro-analysis.md#선택지-b-prototype-결과)). 그러니 fatal도 아니다. 처리하도록 만든 경로에 "일어날 수 없다"는 assert를 두면 코드가 스스로 모순된다. 그리고 debug에서는 그 경로가 한 번도 실행되지 않으므로, 결정 2의 debug 테스트도 만들 수 없다.

선례도 있다. [`vacuum_heap`](https://github.com/CUBRID/cubrid/blob/d52b1889e907abcf84190ec504dde3bc93de260d/src/query/vacuum.c#L1593-L1621) 은 `ER_OUT_OF_VIRTUAL_MEMORY` 를 같은 방식으로 다룬다. 이 오류는 페이지를 재시도하지 않고 미완료 블록이 되며, 위 assert가 이를 허용한다.

허용 목록에는 한 가지만 더한다. assert를 지우는 것이 아니다. 다른 예상 밖 오류에서는 debug가 지금처럼 바로 멈춘다.

debug에서 latch timeout만은 이 결정과 상관없이 [`pgbuf_timed_sleep`](https://github.com/CUBRID/cubrid/blob/d52b1889e907abcf84190ec504dde3bc93de260d/src/storage/page_buffer.c#L7321-L7392) 의 `FIXME` assert(`page_buffer.c:7365`)에서 먼저 멈춘다. 이 assert는 vacuum 밖의 모든 infinite wait timeout에 걸리므로 이번 수리에서 건드리지 않는다.

### 논리 결함 assert를 새로 두는 이유

지금 helper [`vacuum_oos_find_vfid_for_heap_record`](https://github.com/CUBRID/cubrid/blob/d52b1889e907abcf84190ec504dde3bc93de260d/src/query/vacuum_oos.cpp#L398-L426) 의 `assert_release (false)` 와 그 진단 로그는 "OOS 플래그는 있는데 OOS 파일이 없는" 불변식 위반을 잡으려고 둔 것이다. 주석은 원인 후보로 잘못 설정된 플래그, drop된 OOS 파일, 꼬인 recovery 순서를 든다. 이 자리의 진단은 실제로 결함을 찾아낸 적이 있다. CBRD-27089에서 이 자리에 둔 abort가 QA에서 파티션 레코드의 OOS 소유 heap 불일치를 드러냈다. 그 원인은 [PR #7927](https://github.com/CUBRID/cubrid/pull/7927)로 고쳐졌고, 2026-10-22에 `feature/oos-merge` 에 병합되었다.

그런데 지금의 [`heap_oos_find_vfid` 계약](https://github.com/CUBRID/cubrid/blob/d52b1889e907abcf84190ec504dde3bc93de260d/src/storage/heap_file.c#L13335-L13369)에서 `false` 는 항상 실제 오류다. OOS 파일이 없으면 `true` 와 NULL VFID를 돌려준다. 그래서 위의 불변식 위반은 더 이상 helper의 오류 분기로 오지 않는다. 대신 다음 경로로 지나간다.

1. [`vacuum_heap_prepare_oos_vfid`](https://github.com/CUBRID/cubrid/blob/d52b1889e907abcf84190ec504dde3bc93de260d/src/query/vacuum.c#L2314-L2324) 의 conditional 조회나 helper의 대기 조회가 `true` 와 NULL VFID를 돌려준다.
2. [`vacuum_heap_record`](https://github.com/CUBRID/cubrid/blob/d52b1889e907abcf84190ec504dde3bc93de260d/src/query/vacuum.c#L2563-L2567) 의 `has_oos` 가 거짓이 된다.
3. vacuum은 assert도 로그도 없이 OOS 정리를 건너뛴다.

이 경로는 소스로 확인했고, 실행으로는 확인하지 않았다.

결국 지금 helper의 debug assert는 잡으려던 논리 결함은 잡지 못한다. 대신 논리 결함이 아닌 실행 중 실패에서만 멈춘다. 이 결정은 두 경우를 제자리로 돌린다.

| 경우 | 성격 | 지금 debug | 결정 뒤 debug | 결정 뒤 release |
| --- | --- | --- | --- | --- |
| 헤더 latch timeout, 헤더 페이지 I/O 오류 | 실행 중 실패 | helper의 assert에서 멈춤 (latch timeout은 그 전에 `page_buffer.c:7365` 에서 멈춤) | 블록을 `interrupted` 로 넘김 (latch timeout은 여전히 `page_buffer.c:7365` 에서 멈춤) | 블록을 `interrupted` 로 넘김 |
| OOS 플래그는 있는데 OOS 파일이 없음 | 논리 결함 | assert도 로그도 없이 정리를 건너뜀 | 새 assert에서 바로 멈춤 | 지금처럼 정리를 건너뜀 |

### 구현할 때 정할 세부

- 새 assert의 위치는 구현 때 정한다. 조건은 "레코드에 OOS가 있는데, 조회가 성공했고 VFID가 NULL"이다. conditional 조회와 대기 조회 두 경로를 모두 덮어야 한다.
- helper가 release에서 남기던 "OOS flag set but no OOS VFID" 진단 로그도 새 assert와 같은 자리로 옮긴다. 그러면 release에서도 이 결함의 진단 기록이 남는다.
- 기존 debug 테스트에서 새 assert가 걸리면, 아직 남은 불변식 위반이 드러난 것이다. 그 경우는 CBRD-27089처럼 별도 이슈로 다룬다. 수리 PR의 debug 테스트와 CI에서 확인한다.

## 결정 2. 회귀 테스트를 돌리는 빌드

### 정한 내용

vacuum helper가 `heap_oos_find_vfid` 를 부르기 직전에 debug 전용 장애 주입점을 둔다. 이 주입점으로 헤더 조회 실패를 만드는 debug 테스트를 추가한다. release 쪽 증거는 기존 latch timeout 재현 테스트로 유지한다.

### 이유

- 기존 재현 테스트는 latch timeout으로 실패를 만든다. debug에서는 그 timeout이 `page_buffer.c:7365` 에서 먼저 서버를 멈춘다 ([E1](repro-analysis.md#관측-결과)). 그래서 이 테스트는 release에서만 판정이 난다.
- `FIXME` assert를 지우는 방법은 vacuum 밖의 모든 infinite wait timeout을 바꾼다. 이번 수리 범위를 넘는다.
- 테스트를 release 전용으로 두면 debug로 도는 테스트에서는 이 결함을 잡지 못한다.
- 장애 주입 기반은 이미 있다. [`fault_injection.h`](https://github.com/CUBRID/cubrid/blob/d52b1889e907abcf84190ec504dde3bc93de260d/src/base/fault_injection.h#L33-L45) 의 `FI_TEST` 는 debug에서만 동작한다. release에서는 `NO_ERROR` 로 컴파일되어 제품 코드에 남지 않는다.
- 주입한 실패는 기다리지 않고 바로 일어난다. 그래서 아직 측정하지 않은 "바로 실패하는 오류에서 같은 블록을 얼마나 자주 다시 실행하는가"를 같은 테스트로 잴 수 있다. vacuum master 주기 `vacuum_master_interval_in_msecs` 의 기본값은 10ms이므로, 같은 블록이 초당 최대 약 100번 다시 배정될 수 있다 (소스 추론, 측정 안 함).

### 결정 1과의 관계

이 테스트는 결정 1이 있어야 쓸 수 있다. 결정 1이 없으면 주입한 오류가 vacuum assert에 걸려 debug 테스트가 멈춘다.

### 구현 전에 확인할 것

- in-process 서버 테스트에서 주입을 켜고 끄는 방법. `fault_injection_ids` 파라미터와 `FI_SET` 가 후보다.
- 기존 핸들러 `fi_handler_random_fail` 은 `ER_FAILED` 를 돌려주고 `ER_FAILED_ASSERTION` 알림을 남긴다. 이 알림이 debug에서 문제를 일으키는지 확인한다. 문제가 되면 실제 실패와 같은 오류 코드를 돌려주는 핸들러를 따로 둔다.

## 남은 일

- 리뷰어의 답을 받는다. B와 다른 방향을 요구하면 이 문서를 고친다.
- 바로 실패하는 오류의 재실행 간격을 결정 2의 테스트로 측정한다. 재실행이 너무 잦으면 B에 재실행 간격을 더한다.
- 실패한 블록을 얼마나 포기할지 구현 때 정한다. prototype은 실패 즉시 블록 전체를 넘긴다. 같은 블록의 나머지 페이지를 계속 처리하고 마지막에 `interrupted` 로 표시하는 방법도 있다.
