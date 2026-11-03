# PR #8299 리뷰 수정 후 최종 head의 검증과 측정

- 작성일: 2026-11-02, Asia/Seoul. 작성: Claude Code 세션.
- 관련: [CBRD-27785](https://jira.cubrid.org/browse/CBRD-27785), [PR #8299](https://github.com/CUBRID/cubrid/pull/8299).
- 독자: PR #8299 리뷰어와 PR 작성자.
- 수정일: 2026-11-04, Asia/Seoul.
- 수정 이력. 2026-11-04: 성능 변화의 부호를 좋아지면 +로 바꿨다.

### 수치를 읽는 법

- **성능 변화의 부호.** 이 문서의 성능 변화 % 값은 모두 (기준 값 − 비교 대상 값) ÷ 기준 값이다. 비교 대상이 좋아지면 +, 나빠지면 −다. 예를 들어 narrow scan의 명령어 수 +1.33%는 `eec338aaa`가 `f8114e432`보다 명령어를 1.33% 덜 썼다는 뜻이다.
- **지표 두 가지.** 수치마다 어떤 지표인지 적었다.
  - **명령어 수**는 DB 서버 프로세스가 그 SQL을 처리하는 동안 실행한 user-space CPU 명령어 수(`instructions:u`)다. 이 문서의 판정 지표다. 호스트 부하에 거의 흔들리지 않는다.
  - **cycles**는 CPU가 그 일에 쓴 clock 수(`cycles:u`)다. 명령어 수가 같아도 cache miss나 분기 예측 실패가 늘면 커진다. 실제 CPU 시간에 가깝다. 이 측정에서는 서버 재시작마다 크게 흔들려 참고로만 적었다.
- **기준.** 모든 성능 비교의 기준은 이전 PR head `f8114e432`다. develop이나 PR base 대비 값이 아니다.
- **목표.** `f8114e432` 대비 명령어 수가 2% 넘게 나빠지면 회귀로 본다.
- **크기.** stack frame과 코드 크기는 성능 변화가 아니다. bytes 값을 그대로 적었다.
- **주의.** 아래 재현 자료 절의 도구 출력은 반대 부호를 쓴다. 그 출력에서는 늘면 +다.

## Purpose

이 문서는 PR #8299 본문이 인용하는 최종 head `5837393ff`의 근거를 모은다.
질문은 리뷰 수정 뒤의 최종 head가 이전 head보다 느려지지 않았는지, 그리고 리뷰가 지적한 stack 사용 문제가 사라졌는지다.

- AS-IS: 이전 head `f8114e432`에서는 `heap_attrvalue_read`가 항상 inline되면서 16KB OOS 임시 버퍼를 가졌다. 그래서 이 함수를 inline하는 레코드 읽기 함수마다 stack frame이 약 16.6KB였다.
- TO-BE: 최종 head `5837393ff`에서는 OOS Resolve(행 밖에 저장한 값을 읽어 오는 단계)만 noinline 함수가 맡는다. 레코드 읽기 함수의 frame은 128~336 bytes다.

결론은 다음과 같다.

- stack 문제는 해소됐다. 16KB 버퍼는 noinline 함수 `heap_attrvalue_read_oos` 한 곳에만 남는다.
- 서버 명령어 수는 측정한 5개 경우 모두 `f8114e432`보다 0.47~1.82% 적다. 판정은 회귀 없음이다. 속도 개선으로 쓰지 않는다.
- cycles는 서버 재시작마다 크게 흔들려 판정 기준으로 쓰지 않았다. 한 경우의 중앙값 차이는 설명하지 못했다. [cycles](#cycles) 절에 기록한다.
- 측정한 revision은 `eec338aaa`다. 최종 head의 `heap_file.o` 기계어가 이와 같음을 확인했다.

리뷰 결과와 mutation testing은 [PR #8299 적대적 리뷰](CBRD-27785-pr8299-adversarial-review_f8114e432_claude.md)에 있다.
base 대비 성능 수락은 이 문서의 범위가 아니다. [과거 측정 보고서](CBRD-27785-common-reader_067aae4_codex.md)와 [성능 수락 기준](CBRD-27785-pr7990-performance-acceptance_dcbf09e_codex.md)을 본다.

## Implementation

### 대상 revision

| 역할 | commit |
|---|---|
| PR base (`feature/oos-merge`) | `dcbf09e4f7fd02ff9c8fc6493ec8887fc2919d67` |
| 이전 PR 본문의 head | `067aae4e4e91fec8c71c914a4c7fc3c4b13dcd65` |
| 리뷰한 head, 성능 비교 기준 | `f8114e432d3e97cc7a11149ab8ac852de4a1b935` |
| 성능을 측정한 revision | `eec338aaa8cf79c33902b00112ab1c923fbfbe49` |
| 최종 head | `5837393ffb9d69bccb93271d63b0e38b884e0ed4` |

### `067aae4e4` 이후의 commit

| commit | 내용 | 바뀐 곳 |
|---|---|---|
| `9962b4490` | 가변 offset을 검사된 공통 decoder로 읽음 | `heap_file.c`, `heap_file.h`, `heap_oos.cpp`, 테스트 |
| `f8114e432` | 비교할 수 없는 벤치마크 증거를 거부 | `contrib/benchmarks/oos-performance/` |
| `5c5f2a170` | OOS Resolve 임시 버퍼를 noinline 함수로 분리 | `heap_file.c` |
| `12fe25a2c` | disk layout 계획의 할당 실패를 한곳에서 처리 | `heap_file.c` |
| `eec338aaa` | offset entry reader의 오류 주석 수정 | `heap_file.c` 주석 |
| `adbf26e81`, `b01204f51` | fixture 내용을 양 끝에서 검증 | `contrib/benchmarks/oos-performance/` |
| `eabea7c54` | 너무 큰 sample grid를 invalid 증거로 거부 | `bench.py`, `test_bench.py` |
| `a4cdd6191` | grouped OOS 읽기와 scalar COPY를 SQL 테스트로 고정 | `unit_tests/oos/sql/` |
| `5837393ff` | stack 배열 기준값을 배열 길이에서 계산 | `heap_file.c` 한 줄 |

### OOS Resolve 분리

[`heap_attrvalue_read`](https://github.com/CUBRID/cubrid/blob/5837393ffb9d69bccb93271d63b0e38b884e0ed4/src/storage/heap_file.c#L11587)는 계속 `ALWAYS_INLINE`이다.
값이 OOS 참조이면 [`heap_attrvalue_read_oos`](https://github.com/CUBRID/cubrid/blob/5837393ffb9d69bccb93271d63b0e38b884e0ed4/src/storage/heap_file.c#L11548)를 호출한다.
이 함수는 [`__attribute__ ((noinline))`](https://github.com/CUBRID/cubrid/blob/5837393ffb9d69bccb93271d63b0e38b884e0ed4/src/storage/heap_file.c#L770)으로 선언했다.
임시 버퍼, Resolve, `DB_VALUE` 변환, heap 버퍼 해제를 모두 이 함수가 맡는다.
변환은 COPY로 한다. 그래서 함수가 반환한 뒤에는 `DB_VALUE`가 임시 버퍼를 가리키지 않는다.
grouped 읽기로 미리 가져온 값과 오류 경로의 처리는 바꾸지 않았다.

### disk layout 계획

[`heap_attrinfo_determine_disk_layout`](https://github.com/CUBRID/cubrid/blob/5837393ffb9d69bccb93271d63b0e38b884e0ed4/src/storage/heap_file.c#L13147)은 함수 전체를 try 블록으로 감싼다.
[`std::bad_alloc`](https://github.com/CUBRID/cubrid/blob/5837393ffb9d69bccb93271d63b0e38b884e0ed4/src/storage/heap_file.c#L13263)을 받으면 `ER_OUT_OF_VIRTUAL_MEMORY`를 돌려준다.
이전에는 세 할당 중 하나만 이 함수에서 처리했고, 나머지 둘은 호출자가 다른 버퍼의 크기로 보고했다.
컬럼 크기 배열은 8칸 stack 배열을 쓰고 더 많으면 vector를 쓴다. 기준값은 이제 [배열 길이](https://github.com/CUBRID/cubrid/blob/5837393ffb9d69bccb93271d63b0e38b884e0ed4/src/storage/heap_file.c#L13154)에서 계산한다. 두 리터럴 중 하나만 바뀌어 stack을 넘치는 일을 막는다.

### 테스트와 벤치마크 도구

`a4cdd6191`은 테스트만 바꾼다. 적대적 리뷰에서 살아남은 mutant를 잡는 case를 더했다.

- [`GroupedReadReleasesItsPayloadBuffers`](https://github.com/CUBRID/cubrid/blob/5837393ffb9d69bccb93271d63b0e38b884e0ed4/unit_tests/oos/sql/test_oos_sql_crud.cpp#L683)는 1회 스캔의 peak RSS 증가가 4,096 KiB 이하인지 본다. grouped payload 해제를 빼면 실패한다.
- [`GroupedReadOfManyOosColumnsKeepsEveryValue`](https://github.com/CUBRID/cubrid/blob/5837393ffb9d69bccb93271d63b0e38b884e0ed4/unit_tests/oos/sql/test_oos_sql_crud.cpp#L616)는 OOS 컬럼 2, 8, 9개를 grouped로 읽는다.
- [`VarOffsetEntryReaderStopsAtTheEndOfTheOffsetTable`](https://github.com/CUBRID/cubrid/blob/5837393ffb9d69bccb93271d63b0e38b884e0ed4/unit_tests/oos/sql/test_oos_sql_crud.cpp#L537), [`OosFlagOnEmptyVariableFieldReadsAsNull`](https://github.com/CUBRID/cubrid/blob/5837393ffb9d69bccb93271d63b0e38b884e0ed4/unit_tests/oos/sql/test_oos_sql_crud.cpp#L562), [`NullFixedValueReplacesBoundValueInReusedSlot`](https://github.com/CUBRID/cubrid/blob/5837393ffb9d69bccb93271d63b0e38b884e0ed4/unit_tests/oos/sql/test_oos_sql_crud.cpp#L719)는 경계 조건을 고정한다.
- [`PendingReferencesResolveAndFinalizeInPlace`](https://github.com/CUBRID/cubrid/blob/5837393ffb9d69bccb93271d63b0e38b884e0ed4/unit_tests/oos/sql/test_oos_sql_deferred_write.cpp#L873)는 값을 확인하기 전에 죽은 stack frame을 덮어쓴다. 임시 버퍼 COPY를 빼면 실패한다.

[`bench.py compare`](https://github.com/CUBRID/cubrid/blob/5837393ffb9d69bccb93271d63b0e38b884e0ed4/contrib/benchmarks/oos-performance/bench.py#L294)는 기대 sample 집합을 만들기 전에 sample 수를 `rounds * queries * runs`와 비교한다.
이전에는 `rounds = 10**9`인 manifest가 메모리를 다 쓰고 exit 1(regression)로 끝났다. 이제 exit 2(invalid 증거)로 끝난다.
`test_bench.py`는 1 GiB 주소 공간 제한 아래에서 이 경우를 검사한다.

## Remarks

### Test Plan

| 검사 | revision | 결과 |
|---|---|---|
| 엄격한 GCC 8.5 컴파일(경고를 오류로), SA_MODE·SERVER_MODE | `5837393ff` | 통과 |
| debug 빌드, `UNIT_TEST_OOS=ON`, OOS CTest 전체 | `5837393ff` | 44/44 통과, 359초 |
| `contrib/benchmarks/oos-performance/test_bench.py` | `eabea7c54` 이후 | 16개 통과 |
| `eabea7c54`의 수정을 되돌린 mutant | `eabea7c54` | 새 두 case가 MemoryError로 실패, 약 9초 |
| GitHub Actions 전체 CI | `5837393ff` | 아래 CI 절 |

엄격한 GCC 8.5 컴파일은 `cubridci/cubridci:build_rl8.10` 이미지에서 `-Wno-error*` 옵션을 모두 뺀 명령으로 했다.

### CI

[run 41435647083](https://github.com/CUBRID/cubrid/actions/runs/41435647083)은 `/run all`로 `5837393ff`를 시험했다.

- release·debug 빌드, SQL, medium은 성공했다.
- shell은 `shell/_06_issues/_25_2h/cbrd_26280` 1건이 실패했다. `collect` job은 shard 실패를 모으는 검사라서 함께 실패했다.
- 실패한 단계는 loaddb test 7.2다. 기대 출력의 `line 3: syntax error at "NNUL"` 줄이 없고, 실패 개수가 2가 아니라 1이었다.
- 같은 testcase가 [develop PR #8235의 run 39701778475](https://github.com/CUBRID/cubrid/actions/runs/39701778475)에서도 같은 두 줄 때문에 실패했다. 그 PR에는 OOS 코드가 없다. 그때는 요약 줄이 syntax error 줄보다 먼저 출력됐다.
- 이 PR이 바꾼 engine 파일은 `heap_file.c`, `heap_file.h`, `heap_oos.cpp`, `heap_oos.hpp`, `oos_file.cpp`, `locator_sr.c`다. loader와 parser 파일은 없다.
- 이 PR의 이전 head `f8114e432`의 run 41399957211에서는 같은 testcase가 통과했다.
- 판정은 이 PR과 무관한 출력 순서 문제다. 이것은 추론이며 로컬에서 재현하지 않았다.

실패한 case만 다시 돌린 [run 41459706876](https://github.com/CUBRID/cubrid/actions/runs/41459706876)은 `/run rerun 41435647083`으로 시작했다. `cbrd_26280`은 7.3초 만에 통과했고 run은 성공으로 끝났다.
`5837393ff`의 gha-ci status 5개(release·debug 빌드, shell, SQL, medium)는 모두 이 run을 가리키며 성공이다.

### stack frame과 코드 크기

GCC 11.5, release SERVER_MODE의 컴파일 명령에 `-fstack-usage`만 더해 `heap_file.c`를 컴파일했다. 경고는 0건이다.

| 함수 | `f8114e432` frame | `5837393ff` frame |
|---|---:|---:|
| `heap_attrinfo_read_dbvalues` | 16,768 B | 336 B |
| `heap_attrinfo_read_dbvalues_without_oid` | 16,736 B | 304 B |
| `heap_attrinfo_read_dbvalues_lazy` | 16,608 B | 144 B |
| `heap_attrinfo_delete_lob` | 16,672 B | 224 B |
| `heap_attrvalue_peek_lazy` | 16,576 B | 128 B |
| `heap_attrinfo_set_uninitialized` | 16,736 B | 심볼 없음 |
| `heap_attrvalue_read_oos` (noinline) | 없음 | 16,576 B |

- `heap_file.o`의 `.text*` 합계는 275,641 bytes에서 272,569 bytes로 3,072 bytes 줄었다.
- `heap_attrinfo_read_dbvalues`의 코드는 5,031 bytes에서 4,340 bytes가 됐다.
- 4,096 bytes 이상의 frame을 가진 함수는 21개에서 16개가 됐다. 위 표의 레코드 읽기 함수 6개가 빠지고 helper 1개가 더해졌다.
- `heap_midxkey_get_value`의 16,592 bytes는 base부터 있었고 이 PR의 범위가 아니다.
- `eec338aaa`와 `5837393ff`의 `heap_file.o`를 같은 명령으로 컴파일해 `objdump -d` 결과를 비교했다. 기계어가 같다. 두 revision 사이의 다른 `src/` 변경은 없다.

### release 벤치마크

판정 기준은 측정 전에 정했다. 서버 user 명령어 수가 `f8114e432`보다 2%를 넘게 늘면 회귀로 본다.

- 비교: `f8114e432`와 `eec338aaa`. 두 설치본은 같은 컴파일 명령과 CMake cache로 만들었다. `UNIT_TEST_*`는 모두 OFF, GCC 11.5, `-O2 -DNDEBUG`다.
- 고정: 서버는 CPU 16~19, client는 CPU 12에 묶었다.
- 순서: 8 round, 각 round 안에서 두 revision을 ABBA 순서로 번갈아 실행했다. round마다 서버를 새로 시작했다.
- scan 경우: PR의 `bench.py`로 200,000행 표를 읽었다. narrow는 `SUM(v)`, wide는 `SUM(id)`, `SUM(v)`, `SUM(LENGTH(payload))`다. 각 run의 첫 실행은 버렸고 쪽마다 sample 64개다.
- 일반 경우: PR의 `ordinary.py`로 200,000행 표를 썼다. 일반 scan은 `COUNT(*), SUM(a)`, 조건 scan은 `SUBSTR(s,30,1)='a'` 조건, UPDATE는 `SET a=a+1`이다. UPDATE는 sample마다 새 복제본에서 시작했다. 각 run의 첫 실행은 버렸고 쪽마다 sample 32개다.

| 경우 | 성능 변화 (명령어 수, `f8114e432` 대비 `eec338aaa`) |
|---|---:|
| narrow scan | +1.33% |
| wide scan | +1.78% |
| 일반 scan | +1.82% |
| 조건 scan | +0.82% |
| UPDATE | +0.47% |

- 명령어 수는 같은 revision 안에서 거의 변하지 않는다. 5개 경우 모두 모든 sample 쌍에서 `eec338aaa`가 적었다.
- `bench.py compare --max-overhead-percent 2`는 round 0과 1에서 모두 `within_budget`, exit 0이었다.
- 판정은 회귀 없음이다. 원인은 분리하지 못했으므로 속도 개선으로 쓰지 않는다.

<a id="cycles"></a>
### cycles

cycles는 공유 호스트와 서버 재시작의 영향을 크게 받는다.
일반 scan을 서버 시작마다 100회 `perf stat`으로 쟀을 때 `f8114e432`는 8.80~9.12e9, `eec338aaa`는 8.80~9.29e9 cycles였다. `eec338aaa`의 두 서버 시작은 서로 약 3% 달랐다.

| 경우 | 성능 변화 (cycles 하위 10%, `f8114e432` 대비) | 성능 변화 (cycles 중앙값, `f8114e432` 대비) |
|---|---:|---:|
| narrow scan | +0.05% | −12.86% |
| wide scan | +1.73% | −3.64% |
| 일반 scan | −2.79% | −1.60% |
| 조건 scan | +1.88% | +10.46% |
| UPDATE | +2.66% | +2.20% |

- narrow scan의 중앙값은 12.86% 높지만 하위 10%와 최솟값은 거의 같다. 분포로 보면 두 revision 모두 느린 sample이 섞였고 그 비율이 달랐다. 원인은 확인하지 못했다.
- 일반 scan의 하위 10% cycles −2.79%는 위의 재시작 간 차이 안에 있다.
- 일반 scan의 `perf record`에서 `heap_attrinfo_read_dbvalues`는 가장 큰 심볼이다. cycles 비율은 16.8%에서 14.5%로, 절대 sample은 10~13% 줄었다. 바꾸지 않은 호출자 몇 개는 5~10% 늘었다. 코드 배치가 바뀐 영향으로 추정하지만 증명하지 않았다.

### 한계

- 성능은 `eec338aaa`에서 쟀다. 최종 head에 적용하는 근거는 위의 기계어 동일성 비교다.
- 단건 OOS 읽기 경로는 측정하지 않았다.
- base `dcbf09e4f` 대비 성능은 다시 재지 않았다. 과거 측정과 수락 판단은 [과거 측정 보고서](CBRD-27785-common-reader_067aae4_codex.md)에 있다.
- `test_bench.py`의 mutant 생존 수는 리뷰 이후 다시 세지 않았다.

### 재현 자료

[pr8299-final-20261102/](pr8299-final-20261102/)에 비교 결과를 보존한다.

- `analysis-all.txt`는 8 round 전체의 명령어 수와 cycles 중앙값 비교다. 파일의 `head`는 `f8114e432`, `fix`는 `eec338aaa`다.
- `analysis-min.txt`는 cycles의 최솟값과 하위 백분위 비교다.
- `compare-r0.txt`, `compare-r1.txt`는 round 0과 1의 `bench.py compare` 출력이다.

세 파일은 도구 출력 그대로다. 도구는 옛 부호로 출력한다. 그래서 명령어 수나 cycles가 늘면 +다.
