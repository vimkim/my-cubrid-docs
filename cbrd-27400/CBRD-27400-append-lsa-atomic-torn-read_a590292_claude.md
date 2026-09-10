# [CBRD-27400] Fix torn read of append_lsa during log page rollover

/ 로그 append 위치(`append_lsa`)를 락 없이 읽다가 페이지 전환과 겹쳐 찢어진 값을 읽고 assert 로 서버가 죽는 문제 수정

- JIRA: <https://jira.cubrid.org/browse/CBRD-27400> (상위 CBRD-26583 OOS M2 epic 의 sub-task, 태그 `[non-OOS]`)
- 브랜치: `CBRD-27400-append-lsa-atomic` (base `develop`)
- 소스 커밋: `a590292`

## Purpose

### 배경 용어

- `LOG_LSA` (log sequence address): 로그 안의 한 위치를 가리키는 8바이트 값이다. `pageid` (48비트) 와 `offset` (16비트) 두 비트필드를 한 워드에 담은 구조체다 (`src/transaction/log_lsa.hpp`).
- `log_Gl.hdr.append_lsa`: 다음 로그 레코드가 로그 페이지 버퍼에 놓일 위치. 로그를 쓰는 쪽이 계속 전진시킨다.
- MVCC (다중 버전 동시성 제어): 조회가 자기 스냅샷보다 새 버전을 만나면, 레코드에 적힌 이전 버전 주소를 따라 undo 로그에서 옛 버전을 읽어 온다.

### AS-IS / TO-BE

| | 내용 |
|---|---|
| **AS-IS (현재 동작)** | 40개 스레드가 JDBC 로 갱신·조회를 동시에 돌리는 워크로드(`shell/_06_issues/_11_1h/bug_bts_4633`)를 optdebug (release 수준 최적화에 assert 를 살려 둔 빌드) 서버에서 돌리면, 드물게 undo 로그에서 이전 버전을 읽는 경로의 assert 가 터져 `cub_server` 가 core 를 남긴다. |
| **TO-BE (목표 동작)** | 이전 버전을 로그에서 읽는 조회가 append 페이지 전환 도중에 실행돼도 정상 결과를 돌려주고, 서버가 살아 있다. |

### 왜 필요한가

QA 실패다. GHA run 34186373809 shard 31 (PR #6864) 에서 `[NOK] core` 로 실패했다. 이 결함은 OOS/CDC 와 무관하며, optdebug CI 어디서든 재발할 수 있다. release 빌드는 이 assert 가 `-DNDEBUG` (`CMakeLists.txt`) 로 컴파일되지 않아 크래시 대신 찢어진 값이 조용히 다음 판단에 쓰인다.

`[Regression]` 태그에 대해: 원인 코드는 2016년(blame `63378ed15c`, 2016-05-06)부터 있었고 `develop` 과 `feat/oos` 에서 바이트 단위로 같다. 이 실패는 회귀가 아니라 기존 결함이다. 이 PR 에서 JIRA 제목의 `[Regression]` 태그를 떼는 것을 제안한다.

## Implementation

### 근본 원인: 읽기가 두 번, 쓰기가 두 번

읽는 쪽은 락을 잡지 않는다. `log_get_undo_record` (`src/transaction/log_manager.c`) 는 append 위치를 복사해 "이 주소가 아직 로그에 반영되기 전인지" 를 검사한다.

```c
oldest_prior_lsa = *log_get_append_lsa ();
assert (LSA_LT (&process_lsa, &oldest_prior_lsa));
```

최적화 컴파일러(CI 의 GCC 8.5, 로컬 GCC 11.5)는 지역 복사본을 만들지 않고, 비교에 필요한 `pageid` 와 `offset` 을 메모리에서 따로 읽는다. 즉 8바이트 한 값을 두 번에 나눠 읽는다.

쓰는 쪽 `logpb_next_append_page` (`src/transaction/log_page_buffer.c`) 는 페이지가 꽉 차면 다음처럼 두 문장을 두 store 로 낸다.

```c
log_Gl.hdr.append_lsa.pageid++;     /* store 1: (P+1, 예전 offset) */
log_Gl.hdr.append_lsa.offset = 0;   /* store 2: (P+1, 0) */
```

x86 은 store 순서를 지키므로, 읽는 스레드의 첫 load 가 store 1 앞에 오고 둘째 load 가 store 2 뒤에 오면, 조합된 값은 `(옛 페이지 P, 새 페이지의 어린 offset)` 이 된다. 로그가 한 번도 가진 적 없는 주소다. `process_lsa` 가 페이지 P 위에 있으면(직전 갱신된 행의 이전 버전은 거의 항상 현재 append 페이지에 있다) `LSA_LT` 가 거짓이 되어 assert 가 터진다.

```
읽는 스레드 (log_get_undo_record)      쓰는 스레드 (logpb_next_append_page, LOG_CS 보유)
load1  word=(P, 16328)
                                       store1  append_lsa=(P+1, 16328)
                                       store2  append_lsa=(P+1, 0)
                                       ... 새 페이지에 레코드 추가 -> (P+1, 48)
load2  offset=48
비교값 = (P, 48)  vs  process_lsa=(P, 15112)  ->  LSA_LT 거짓  ->  assert
```

### 수정: 8바이트를 원자적으로 발행하고 소비한다

`src/transaction/log_lsa.hpp` 에 헬퍼 두 개를 추가했다. `LOG_LSA` 를 8바이트 한 번의 원자 접근으로 복사한다.

```c
inline void lsa_atomic_load (log_lsa *dest, const log_lsa *src);   // __atomic_load  (ACQUIRE)
inline void lsa_atomic_store (log_lsa *dest, const log_lsa *src);  // __atomic_store (RELEASE)
```

- 리눅스/기타: GCC/clang 공용 내장함수 `__atomic_load` / `__atomic_store` 를 `LOG_LSA` 객체 그대로 쓴다. `LOG_LSA` 는 8바이트이고 `append_lsa` 는 8바이트 정렬돼 있어(`LOG_HEADER` 의 `INT64 fpageid` 뒤, `log_storage.hpp`) 락 없는 8바이트 접근으로 컴파일된다.
- Windows(MSVC, `__atomic` 없음): `_InterlockedExchange64` / `_InterlockedCompareExchange64` 로 같은 8바이트 원자 접근을 한다.
- `std::atomic<LOG_LSA>` 는 쓰지 않았다. `LOG_LSA` 를 품은 `LOG_HEADER` 는 디스크로 그대로 복사되는 온디스크 헤더(`memcpy (…, &log_Gl.hdr, sizeof (log_Gl.hdr))`)라, 필드에 `std::atomic` 을 심을 수 없다.

바꾼 지점:

| 파일 | 함수 | 변경 |
|---|---|---|
| `src/transaction/log_page_buffer.c` | `logpb_next_append_page` | 새 LSA 를 지역 변수 `next_append_lsa` 에 만들고(`pageid++`, `offset=0`), `lsa_atomic_store` 한 번으로 발행. 두 store 가 하나가 됐다. |
| `src/transaction/log_manager.c` | `log_get_undo_record` | append 위치를 `lsa_atomic_load` 로 지역 복사본에 담아 비교. assert 는 그대로 둔다. |
| `src/storage/heap_file.c` | `heap_get_visible_version_from_log` | 락 없이 append 위치를 읽는 두 곳 모두 `lsa_atomic_load`. 기존 `/* TODO: fix atomicity issue on x86 */` 주석 제거. |
| `src/transaction/log_page_buffer.c` | `logpb_fetch_page` | append 위치 복사를 `lsa_atomic_load` 로. (같은 함수의 `prev_lsa` 복사는 범위 밖이라 그대로 둔다.) |

온디스크 포맷·프로토콜·단일 스레드 동작은 바뀌지 않는다. append_lsa 의 값 자체는 그대로이고, 복사만 원자적이 됐다.

## Remarks

### 리뷰어가 볼 곳

- `src/transaction/log_lsa.hpp` 의 헬퍼 두 개: 파일에 이미 있는 `LSA_*` 인라인 패턴(선언은 `inline`, 정의는 키워드 없이)을 그대로 따른다. `.hpp` 는 astyle 대상이라 C++ 문법이 그대로 허용된다.
- `.c` 파일 세 곳에는 C++ 전용 문법이 들어가지 않았다(호출과 지역 변수 선언뿐). 그래서 `/* *INDENT-OFF* */` 래핑이 필요 없다.

### 완결성: 다른 writer 는 왜 괜찮은가

`append_lsa` 를 쓰는 지점은 세 종류다. 이 중 락 없는 reader 에게 위험한 것은 하나뿐이다.

1. **페이지 전환 `logpb_next_append_page`**: `pageid` 와 `offset` 을 반대 방향(pageid 증가, offset 0 으로)으로 함께 바꾼다. 로그가 가진 적 없는 값을 만드는 유일한 writer 이고, 동시에 조회 스레드와 겹치는 유일한 지점이다. 이번에 원자 store 로 고쳤다.
2. **offset 전진 매크로**(`log_page_buffer.c` 의 `offset += length` 등): `offset` 만 바꾸고 `pageid` 는 그대로다. reader 의 8바이트 원자 load 는 같은 페이지의 (P, 옛 offset) 또는 (P, 새 offset) 중 하나를 온전하게 본다. 두 값 모두 단조 증가라 assert 를 깨지 않는다. 게다가 이 경로는 `LOG_CS` (로그 전역 임계구역) 안에서 돈다.
3. **`LOG_RESET_APPEND_LSA` 와 종료 시 sentinel**(`log_append.cpp`, `log_manager.c`): 복구·재시작·초기화·종료 경로다. 동시 조회가 시작되기 전이거나 `LOG_CS` 안이라 락 없는 reader 와 겹치지 않는다.

즉 동시성 상황에서 반대 방향으로 두 필드를 함께 바꾸는 writer 는 페이지 전환 하나뿐이고, 그것을 원자화하면 크래시는 닫힌다.

### 같은 뿌리의 다른 노출

store 1 과 store 2 사이에는 `(P+1, 예전 offset)` 이라는, 실제보다 앞선 위치가 잠깐 보인다. 8바이트를 한 번에 읽던 다른 reader(`heap_get_visible_version_from_log`, `logpb_fetch_page`)가 이 값을 보면 아직 만들어지지 않은 페이지를 다루려 할 수 있었다. 이 reader 들도 이번에 원자 load 로 바꿨고, writer 가 원자 store 하나로 발행하므로 이 전이 상태도 함께 닫혔다.

### 한계 / 후속

- `feat/oos` 브랜치의 `oos_file.cpp` 는 `*log_get_append_lsa ()` 를 같은 식으로 복사한다. `feat/oos` 가 다음 develop 머지를 받을 때 이 헬퍼를 쓰도록 맞추면 된다(이 PR 범위 밖).
- `feat/oos` 는 이 develop PR 을 다음 머지에서 자동으로 받는다. 코드가 양쪽에서 같아 별도 cherry-pick 은 필요 없다.

### Test Plan

ns 단위 창은 ctest 나 JDBC 레벨 테스트로 고정할 수 없다. 그래서 재현 가능한 GDB 프로브로 검증했다. optdebug 빌드(`a590292`, GCC 11.5)에서:

1. **디스어셈블 확인**. 고친 `log_get_undo_record` 는 append 위치를 8바이트 load 하나(`mov (%rax),%rdx`)로 읽는다. 옛 빌드에 있던 둘째 offset load(`movzwl 0x6(%rax)`)가 사라졌다. `logpb_next_append_page` 는 새 값을 8바이트 store 하나(`mov %rax,0x118(%rbx)`)로 발행한다. 옛 빌드의 2바이트 store(`mov %ax,0x11e(%rbx)`)가 사라졌다.
2. **GDB 프로브**. 첫 load 직후에 그 스레드를 멈춰, 다른 스레드가 페이지를 넘길 시간을 준다(진단 때 옛 코드에서 assert 를 강제로 터뜨린 것과 같은 스케줄). scenario 7 를 두 번 돌려, 옛 코드였다면 assert 가 터졌을 "창 안 페이지 전환" 을 합계 55회 잡았다(`would_fail_if_torn=55`). 고친 서버는 assert 분기에 0회 도달했고 core 를 남기지 않았다.
3. **디버거 없는 재현**. scenario 7 를 프로브 없이 10회, 그리고 7개 시나리오 전체를 1회 돌렸다. 14개 실행 전부 core 0, assert 0. 7개 전체 실행의 scenario 7 에서 Java 클라이언트가 `OutOfMemoryError` 를 냈는데, 이는 진단서에 적힌 테스트 하네스 아티팩트(1GB 힙에서 statement 누수)이지 엔진 버그가 아니다. 서버는 그때도 살아 있었다.

진단 상세(프로브 소스, 두 바이너리 디스어셈블, core backtrace)는 `cbrd-27400/2940b1c_claude/` 에 있다.
