# PR #8299 적대적 코드 리뷰와 후속 조치

- 작성일: 2026-11-02, Asia/Seoul. 작성: Claude Code (claude-opus-5-5) 세션과 그 하위 에이전트.
- 관련: [CBRD-27785](https://jira.cubrid.org/browse/CBRD-27785), [PR #8299](https://github.com/CUBRID/cubrid/pull/8299), OOS 후속 후보 [CBRD-27873](https://jira.cubrid.org/browse/CBRD-27873).
- 독자: PR 작성자와 리뷰어, OOS 후속 작업을 고르는 사람.

## 질문과 결론

질문은 PR #8299가 `feature/oos-merge`의 동작을 바꾸지 않으면서 일반 행 읽기와 UPDATE의 CPU 비용만 줄이는지였다. PR은 MVCC, recovery, ownership, identity 검사와 COPY 의미를 유지한다고 주장한다.

결론은 다음과 같다.

- 실행으로 증명된 엔진 동작 결함은 없다. 같은 입력에서 head와 base의 읽기 값과 기록 레코드 바이트가 같고, ASan에서 use-after-free, 누수, 이중 해제가 나오지 않았다.
- 증명된 결함은 모두 minor다. PR 테스트가 PR이 주장한 동작을 고정하지 못한 곳, 벤치마크 스크립트의 종료 코드, 이전 head를 가리키는 PR 본문이다.
- 리뷰 후 PR head `5837393ff`에 테스트 보강, 벤치마크 수정, stack 배열 경계 수정이 들어갔다. PR 본문 갱신과 현재 head의 CI 결과는 이 문서 작성 시점에 남아 있다.
- 리뷰 중 발견한 기존 문제는 OOS 코드에 속한 것과 `develop`에도 있는 것으로 나눴다. OOS 쪽은 CBRD-27873 후보로 넘기고, 나머지는 [OOS와 무관한 기존 문제](#non-oos-existing)에 기록한다.

## 대상 revision

| 역할 | 저장소 | commit |
|---|---|---|
| 리뷰 base (`origin/feature/oos-merge`) | CUBRID/cubrid | `dcbf09e4f7fd02ff9c8fc6493ec8887fc2919d67` |
| 리뷰한 head | CUBRID/cubrid PR #8299 | `f8114e432d3e97cc7a11149ab8ac852de4a1b935` |
| 재검증한 head | 같은 PR | `eec338aaa8cf79c33902b00112ab1c923fbfbe49` |
| 후속 반영 후 PR head | 같은 PR | `5837393ffb9d69bccb93271d63b0e38b884e0ed4` |
| OOS 여부 판정 기준 | CUBRID/cubrid `develop` | `d5674fe94f08d084c6832ba4e3f6521d66cbee0e` |

빌드는 `debug_gcc`와 `UNIT_TEST_OOS=ON`, 벤치마크는 `release_gcc`(`-O2 -finline-functions`)를 썼다. 각 실행은 전용 worktree, 전용 설치본, 전용 DB 디렉터리에서 했다.

## 방법

공격 영역을 다섯으로 나눠 adversary 다섯 명을 병렬로 실행했다. 모델은 opus 2, sonnet 3이다.

| # | 영역 | 증명 방식 |
|---|---|---|
| 1 | 가변 offset 경계와 손상 레코드 | 실제 레코드를 메모리에서 손상해 head와 base에 같은 바이트로 입력, fork한 자식에서 결과 분류 |
| 2 | OOS 읽기 버퍼 소유권과 수명 | ASan 빌드, 해제 후 poisoning, 실패 주입 |
| 3 | 읽기 결과 동등성 | SQL, 직접 heap 읽기, 다중 컬럼 index key를 정규화해 dump, head와 base dump 비교 |
| 4 | 레코드 writer와 UPDATE owner | INSERT, UPDATE, 직접 생성한 레코드 바이트를 마스킹해 dump, 비교. gdb로 owner 경로 추적 |
| 5 | PR 테스트와 벤치마크의 가치 | mutation testing |

결함은 실행으로 증명된 것만 인정했다. adversary가 보고한 결함과 PASS 판정은 조정자가 같은 명령을 다시 실행해 확인했다. 실행으로 증명하지 못한 주장은 별도 절에 의심점으로 둔다.

## 증명된 결함과 처리 상태

위치는 리뷰한 head `f8114e432` 기준이다.

| # | 내용 | 위치 | 처리 |
|---|---|---|---|
| 1 | PR 본문이 이전 head `067aae4e4`의 CI와 CTest를 근거로 든다 | PR 본문 | 남음 |
| 2 | `bench.py compare`에 `rounds = 10**9`인 증거를 주면 `MemoryError`로 exit 1. README는 exit 1을 regression, 잘못된 증거를 exit 2로 정의 | [`bench.py:261`](https://github.com/CUBRID/cubrid/blob/f8114e432d3e97cc7a11149ab8ac852de4a1b935/contrib/benchmarks/oos-performance/bench.py#L261), [`:425`](https://github.com/CUBRID/cubrid/blob/f8114e432d3e97cc7a11149ab8ac852de4a1b935/contrib/benchmarks/oos-performance/bench.py#L425) | `eabea7c54`에서 수정 |
| 3 | grouped payload 해제를 지운 mutant가 PR 테스트를 모두 통과. killer 테스트는 1,500행 스캔에서 peak RSS 37,120 KiB 증가 | [`heap_file.c:11707`](https://github.com/CUBRID/cubrid/blob/f8114e432d3e97cc7a11149ab8ac852de4a1b935/src/storage/heap_file.c#L11707) | `a4cdd6191` |
| 4 | `oos_read_many()`의 `done` 배열을 4칸으로 줄인 mutant가 통과. killer는 읽은 값 합 321(기대 560). PR 테스트는 요청 4개 이상을 만들지 않음 | [`oos_file.cpp:2880`](https://github.com/CUBRID/cubrid/blob/f8114e432d3e97cc7a11149ab8ac852de4a1b935/src/storage/oos_file.cpp#L2880) | `a4cdd6191` |
| 5 | `num_values < 2`를 `< 3`으로 바꾼 mutant가 통과 | [`heap_oos.cpp:747`](https://github.com/CUBRID/cubrid/blob/f8114e432d3e97cc7a11149ab8ac852de4a1b935/src/storage/heap_oos.cpp#L747) | `a4cdd6191` |
| 6 | NULL 슬롯이 이전 행 값을 유지하는 mutant가 통과. `FixedValuesAcrossNullsAndRepresentations`는 주석이 말하는 슬롯 재사용을 거치지 않음 | [`test_oos_sql_crud.cpp:369`](https://github.com/CUBRID/cubrid/blob/f8114e432d3e97cc7a11149ab8ac852de4a1b935/unit_tests/oos/sql/test_oos_sql_crud.cpp#L369) | `a4cdd6191` |
| 7 | `PendingReferencesResolveAndFinalizeInPlace`는 stack scratch와 heap 버퍼 두 경우의 COPY를 고정한다고 적었지만 scratch COPY 제거를 잡지 못함. 반환 직후 읽어 죽은 프레임의 바이트가 아직 맞기 때문 | [`test_oos_sql_deferred_write.cpp:1011`](https://github.com/CUBRID/cubrid/blob/f8114e432d3e97cc7a11149ab8ac852de4a1b935/unit_tests/oos/sql/test_oos_sql_deferred_write.cpp#L1011) | `a4cdd6191` |

adversary가 증명하고 조정자가 다시 실행하지 않은 테스트 공백도 `a4cdd6191`과 `5837393ff`가 다룬다.

- `heap_oos_attr_has_inline_ref()`의 "offsets differ" 조건 제거(M4b). adversary 1과 5가 독립적으로 찾았다.
- 단일 엔트리 경계 `- 1`을 `- 0`으로 바꾼 mutant(M1c).
- `heap_attrinfo_determine_disk_layout()`의 8칸 stack 배열과 임계값 리터럴이 따로 있어, 어긋나도 테스트가 조용히 통과(M5b, M5c). `5837393ff`는 임계값을 배열 길이에서 유도해 이 종류의 불일치를 없앤다.
- `test_bench.py` mutant 15개 중 9개 생존. 설치본 검사, hash 동등성, `complete` 검사, sample별 서버 identity, regression과 inconclusive 판정이 고정되지 않았다. 이후 `adbf26e81`, `b01204f51`, `eabea7c54`가 테스트를 추가했지만 생존 mutant를 다시 세지는 않았다.

### 테스트 보강 검증

`a4cdd6191`은 조정자가 `f32e182f2`로 넘긴 커밋을 그대로 cherry-pick한 것이다. diff가 같음을 확인했다. 변경은 `unit_tests/oos/sql/test_oos_sql_crud.cpp` +295줄, `test_oos_sql_deferred_write.cpp` +12줄이고 `src/`는 바꾸지 않는다.

`f32e182f2`(parent `b01204f51`)에서 실행한 결과다.

- `ctest --test-dir build_preset_debug_gcc -R '^test_oos_sql_'`에서 19/19 통과.
- 새로 넣거나 바꾼 case 7개를 두 번 더 실행해 모두 통과.
- 하위 에이전트가 `eec338aaa`에서 mutant 10개(M8a, M8b, M8c, M3a, M4a, M4b, M1c, M12, S1, S2)를 모두 잡았다. 조정자가 S1, M3a, M8b를 다시 실행해 의도한 case가 잡는 것을 확인했다.
- 누수 검사는 1회 스캔의 peak RSS 증가로 판정한다. 정상 소스는 0 KiB, 누수 mutant는 11~12 MiB 늘었고 한계는 4,096 KiB다. 독립 서버 호출이 끝날 때 private heap을 해제하므로 할당 카운터로는 이 경우를 볼 수 없다.

## 코드 근거만 있는 의심점

- `heap_attrvalue_read()`가 `ALWAYS_INLINE`이 되면서 16 KB OOS scratch가 release 빌드에서 record loop 프레임으로 옮겨졌다. 이 의심점은 `5c5f2a170`이 해소했다. 아래 재검증 절에 수치가 있다.
- `heap_midxkey_get_value()`의 COPY 플래그를 false로 바꾼 mutant가 모든 테스트에서 살아남는다. 호출자가 스택 재사용 전에 값을 쓰므로 관찰하지 못했다. 심각도 낮음.
- `locator_update_force()`의 호출처 네 곳은 항상 `from_copyarea == from_workspace`다. 둘 중 하나만 보는 mutant는 지금 동등하다. 두 값이 다른 호출자가 생기면 검증되지 않은 경로가 된다. 심각도 낮음.
- 손상 레코드에서 OOS 필드의 끝 엔트리가 잘리면 에러 코드가 `ER_HEAP_OOS_BAD_INLINE_HEADER`(-1387)에서 `ER_GENERIC_ERROR`로 바뀐다. 손상 레코드에 한정된 변화이며 PR이 밝힌 경계 검사 의도에서 나온 결과다.

## 재검증: 로컬 head `eec338aaa`

리뷰 뒤 다른 세션이 `f8114e432` 위에 커밋 세 개를 올렸다(`5c5f2a170`, `12fe25a2c`, `eec338aaa`). 리뷰한 산출물과 머지할 산출물이 달라졌으므로 같은 harness로 다시 확인했다. `b01204f51`과 `5837393ff`의 `src/`와 `unit_tests/` 중 엔진 동작에 관계된 부분은 `eec338aaa`와 같거나, 위의 한 줄 임계값 변경만 다르다.

| 검사 | 결과 |
|---|---|
| 읽기 dump (1,494,527줄) | base와 180줄 차이, 모두 BLOB/CLOB locator의 무작위 파일 이름 |
| 쓰기 dump (102,742줄) | padding hash 줄을 빼면 차이 0줄, `endcheck=BAD` 0, OOS 플래그 불일치 0 |
| 수명 테스트 | 통과 |
| OOS SQL 전체 | 19/19 통과 |

`-fstack-usage`(`-O2 -DNDEBUG -finline-functions`, SERVER_MODE)로 잰 프레임 크기다.

| 함수 | `f8114e432` | `eec338aaa` |
|---|---|---|
| `heap_attrinfo_read_dbvalues` | 16,768 B | 336 B |
| `heap_attrinfo_read_dbvalues_without_oid` | 16,736 B | 304 B |
| `heap_attrinfo_read_dbvalues_lazy` | 16,608 B | 144 B |
| `heap_attrinfo_delete_lob` | 16,672 B | 224 B |
| `heap_attrvalue_peek_lazy` | 16,576 B | 128 B |
| `heap_attrvalue_read_oos` (noinline) | 없음 | 16,576 B |

### release 벤치마크

판단 기준을 먼저 정했다. `5c5f2a170`이 일반 테이블 스캔의 서버 명령어 수를 PR 기준 2%보다 많이 늘리면 재작업 대상으로 표시하고, 그렇지 않으면 재검증을 닫는다.

- 도구: PR의 `contrib/benchmarks/oos-performance/bench.py` scan 비교. 200,000행, narrow(`SUM(a)`)와 wide(두 정수와 `LENGTH(s)`), 실행마다 20회 스캔, round 2개에 run 5개, 각 round 첫 run 버림.
- 설정: `data_buffer_size=4G`, `max_query_cache_entries=0`, `query_cache_size_in_pages=0`. 두 설치본 모두 같은 설정이며 한 번에 서버 하나만 띄웠다.
- 순서: `f8114e432`, `eec338aaa`를 번갈아 세 쌍. 쌍마다 서버를 새로 시작하고 끝나면 정지했다.
- 판정: 공유 호스트이므로 경과 시간이 아니라 서버 프로세스의 user 명령어 수로 판정했다.

| case | 명령어 수 변화 (`eec338aaa` 대 `f8114e432`) | 같은 쪽 안 spread | `compare --max-overhead-percent 2` |
|---|---|---|---|
| narrow | -1.33%, 세 쌍 모두 같음 | 0.009% 이하 | 세 번 모두 `within_budget`, exit 0 |
| wide | -1.78%, 세 쌍 모두 같음 | 0.005% 이하 | 세 번 모두 `within_budget`, exit 0 |

판정은 회귀 없음이다. 원인은 분리하지 못했다. `-fstack-clash-protection`이 꺼져 있어 stack probe 때문은 아니다(prologue가 `sub $0x4138,%rsp`에서 `sub $0x108,%rsp`로 바뀔 뿐이다). 1회 `perf record` 비교는 변화가 바뀌지 않은 함수에 흩어져 있고 전체 차이(-8.4%)가 벤치마크(-1.3%)보다 훨씬 커서 대표성이 없다. 따라서 이 결과를 "이 커밋으로 1.3% 빨라졌다"로 쓰지 말고 "회귀 없음"으로 써야 한다. 단건 OOS 읽기 경로와 UPDATE는 측정하지 않았다.

<a id="oos-existing"></a>
## OOS 코드의 기존 문제 (CBRD-27873 후보)

`develop`에는 없는 OOS 코드다. PR이 만든 문제는 아니지만 PR이 비슷한 검사를 넣은 곳 옆에 남아 있다.

- PR은 `heap_oos_attr_has_inline_ref()`에서 검사 없는 `OR_VAR_IS_NULL`을 경계 검사가 있는 pair reader로 바꿨다. 같은 패턴이 두 곳에 남아 있다.
  - [`heap_midxkey_get_oos_extra_size()`, `heap_file.c:11828`](https://github.com/CUBRID/cubrid/blob/f8114e432d3e97cc7a11149ab8ac852de4a1b935/src/storage/heap_file.c#L11828)
  - [`locator_fixup_oos_oids_in_recdes()`, `locator_sr.c:14471`](https://github.com/CUBRID/cubrid/blob/f8114e432d3e97cc7a11149ab8ac852de4a1b935/src/transaction/locator_sr.c#L14471)
- `OR_VAR_IS_NULL`은 `location`과 `location + 1` 엔트리를 레코드 길이 확인 없이 읽는다. 잘린 레코드가 다중 컬럼 index key 생성이나 OOS OID fixup 경로로 들어오면 VOT를 범위 밖에서 읽을 수 있다. 이 경로의 harness는 만들지 않았으므로 실행으로 증명하지 않았다.

<a id="non-oos-existing"></a>
## OOS와 무관한 기존 문제

모두 `develop` `d5674fe94`에 같은 코드가 있어 OOS 통합이나 이 PR에서 생긴 문제가 아니다.

1. 손상 레코드에 대한 가변 필드 읽기 방어가 부족하다.
   - `develop`의 [`heap_attrvalue_point_variable()`](https://github.com/CUBRID/cubrid/blob/d5674fe94f08d084c6832ba4e3f6521d66cbee0e/src/storage/heap_file.c#L11262)은 현재 엔트리와 다음 엔트리를 [검사 없이 읽는다(11272)](https://github.com/CUBRID/cubrid/blob/d5674fe94f08d084c6832ba4e3f6521d66cbee0e/src/storage/heap_file.c#L11272). 필드 범위 `[this_off, next_off)`가 레코드 안인지도 확인하지 않는다.
   - SET, MULTISET, SEQUENCE, BLOB, CLOB은 다음 offset을 찾으려 [VOT 전체를 검사 없이 순회한다(11299)](https://github.com/CUBRID/cubrid/blob/d5674fe94f08d084c6832ba4e3f6521d66cbee0e/src/storage/heap_file.c#L11299).
   - 재사용한 `attr_info`로 header보다 짧은 레코드를 읽으면 [`heap_rec_layout_init()`의 assert(11098)](https://github.com/CUBRID/cubrid/blob/d5674fe94f08d084c6832ba4e3f6521d66cbee0e/src/storage/heap_file.c#L11098)에서 멈춘다. `heap_attrinfo_recache(NULL_REPRID)`가 `read_classrepr`을 지우면서 `values[i].read_attrepr`은 남기기 때문이다. base와 head에서 같게 재현했다.
   - PR #8299는 엔트리 쌍 읽기에만 경계 검사를 넣었다. 잘린 레코드 sweep의 8,214건은 base와 head 모두 crash한다.
2. record writer가 초기화하지 않은 padding 바이트를 디스크에 쓴다. VOT 정렬 padding, 어느 fixed 속성에도 속하지 않는 fixed 영역 바이트, 고정 속성 수 이상의 bound bit가 해당한다. `develop`의 writer도 [`resize_buffer()`(13683)](https://github.com/CUBRID/cubrid/blob/d5674fe94f08d084c6832ba4e3f6521d66cbee0e/src/storage/heap_file.c#L13683)와 `or_init()` 뒤 버퍼를 0으로 채우지 않는다. 같은 build의 두 실행에서도 이 바이트가 달라진다. 이전 heap 내용이 데이터 파일과 백업에 남을 수 있다는 점은 추정이며 확인하지 않았다.
3. ASan이 기존 문제를 보고했다.
   - `do_prepare_update()`와 `do_prepare_delete()`는 안쪽 block에 `XASL_NODE_HEADER xasl_header`를 선언하고 `stream.xasl_header = &xasl_header`를 넣는다. block 밖의 두 번째 `prepare_query (contextp, &stream)`가 이 포인터로 쓴다. ASan은 `qmgr_prepare_query()`의 `memset`에서 stack-use-after-scope를 보고했다. `develop`의 같은 위치는 [`execute_statement.c:10035-10038`과 `10125`](https://github.com/CUBRID/cubrid/blob/d5674fe94f08d084c6832ba4e3f6521d66cbee0e/src/query/execute_statement.c#L10035), [`11430-11433`과 `11508`](https://github.com/CUBRID/cubrid/blob/d5674fe94f08d084c6832ba4e3f6521d66cbee0e/src/query/execute_statement.c#L11430)이다.
   - `db_shutdown()` 중 [`db_ws_free()`의 header 검사(quick_fit.c:256 부근)](https://github.com/CUBRID/cubrid/blob/d5674fe94f08d084c6832ba4e3f6521d66cbee0e/src/object/quick_fit.c#L256)에서 global-buffer-overflow가 났다. `quick_fit.c`는 `develop`과 feature에서 같다. 해제 대상 포인터가 무엇인지는 추적하지 않았다.
   - 클라이언트 쪽 `pr_do_db_value_string_compression`과 authorization cache에서 누수가 보고됐다.

## 기각한 주장

- 손상 레코드 fuzz에서 head만 crash한 경우. base 3회와 head 2회 실행에서 8건이 head에서만 crash했지만 두 head 실행 모두에서 crash한 건은 없다. base도 재실행마다 새 crash를 1~7건 만들고, base에서만 crash한 건은 216건이다. 임의 offset 읽기의 비결정성으로 판단했다.
- OOM 시 동작 차이. head는 예외 대신 `ER_OUT_OF_VIRTUAL_MEMORY`를 돌려준다. 개선이다.
- 읽기 dump의 BLOB/CLOB 차이. locator 파일 이름이 실행마다 다르다.
- `test_oos_server` timeout. 호스트 부하 중 1회였고 단독 실행에서 31초에 통과했다.

## 검증 범위의 한계

- SA 모드 테스트에서 저장된 행은 모두 8바이트 header다. live MVCC header는 직접 만든 레코드로만 확인했다.
- 4바이트 offset 폭은 SQL로 만들 수 없어(-1388) 직접 만든 레코드로만 확인했다.
- 동시성과 HA 복제 로그는 다루지 않았다.
- CI의 shell, SQL, medium은 이 리뷰에서 실행하지 않았다. 문서 작성 시점에 `5837393ff`의 gha-ci는 대기 중이다.

## 재현 자료

리뷰 harness는 로컬 브랜치 `CBRD-27785-review-harness`(`7472ed577`, parent `f8114e432`)에 보관했다. 이 브랜치는 원격에 올리지 않았다. 각 harness는 같은 파일을 head와 base worktree에서 실행해 결과를 비교한다.

- `test_oos_sql_zz_readdiff`: `$OOS_READDIFF_OUT`에 읽기 결과를 dump한다. BLOB/CLOB locator 줄은 실행마다 다르다.
- `test_oos_sql_zz_writediff`: `$WRITEDIFF_OUT`에 레코드를 dump한다. `padding_bytes=` 줄을 빼고 비교한다.
- `test_oos_sql_a1_var_offsets`: 손상 레코드 sweep과 fuzz. `A1_PIN`으로 레코드 바이트를 고정하고, base에서는 `a1_flavor.hpp`의 `A1_HAS_PAIR`를 0으로 둔다.
- `test_oos_sql_lifetime`: grouped, scalar, pending 경로의 값이 버퍼, 다음 행, 스캔보다 오래 살아남는지 확인한다.

OOS 테스트 fixture는 configure 시점의 `CUBRID_DATABASES`를 `CTestTestfile.cmake`에 고정한다. 새 worktree에서는 `cub-workenv init` 뒤에 CMake를 다시 실행해야 한다.
