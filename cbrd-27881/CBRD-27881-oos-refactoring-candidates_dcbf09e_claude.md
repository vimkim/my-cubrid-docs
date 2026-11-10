# CBRD-27881 OOS 리팩토링 후보 조사 결과 (feature/oos-merge dcbf09e)

## Question, readers, and principal findings

이 문서는 두 질문에 답한다.

1. `feature/oos-merge`의 OOS 코드에서 동작을 바꾸지 않고 구조를 정리할 수 있는 곳은 어디인가.
2. 그중 지금 작은 PR로 낼 수 있는 것은 무엇이고, 나머지는 왜 미루거나 기록만 남기는가.

독자는 OOS 유지보수자와 OOS PR 리뷰어다. 유지보수자는 이 문서로 draft PR 7개의 처리 순서와 사람이 정해야 할 항목을 고른다. 리뷰어는 각 PR이 동작 보존을 어떤 근거로 주장하는지 확인한다.

조사 범위는 OOS 엔진 코드와 OOS 단위 테스트다. 다섯 구역으로 나누어 읽었다.

| 구역 | 대상 |
| --- | --- |
| A | `oos_file.cpp` 1-2090행. bestspace cache, OOS 파일 생성과 삭제, 빈 페이지 회수 |
| B | `oos_file.cpp` 2038행 이후, `oos_file.hpp`, `oos_log.hpp`, `oos_util.*`. insert, read, delete, redo, 테스트 hook |
| C | heap 쪽 OOS 연동. `heap_file.c`, `heap_oos.cpp`, `heap_oos_value_ref.*`, `locator_sr.c` |
| D | vacuum, 로그, 복제와 CDC, 복구, file manager, schema 변경, 진단 |
| E | `unit_tests/oos/`의 테스트, ctest 등록, 운영 코드 안의 테스트 seam |

핵심 결과는 다음과 같다.

- 원시 후보 70개를 중복 제거해 67개 항목(R-01..R-66, R-70)으로 정리했다. 리팩토링이 아니라 결함일 수 있는 것은 30개(DF-01..DF-30)로 따로 분리했다.
- 8개 항목을 draft PR 7개로 만들었다. PR마다 CBRD-27881의 sub-task가 하나씩 있다(CBRD-27882..CBRD-27888). 모두 `feature/oos-merge` 대상 draft이고, 계획대로 병합하지 않았다.
- 실행 코드를 바꾼 PR 6개는 로컬 OOS ctest 44개를 통과했다. GitHub CI(gha-ci)는 `unit_tests/oos`를 빌드하지도 실행하지도 않는다. 그래서 단위 테스트 수준의 확인은 이 로컬 결과뿐이다. 주석만 바꾼 PR7은 주석을 뺀 token 비교로 실행 코드 차이가 빈 `if` 하나뿐임을 확인했다.
- 시험 삼아 만든 PR 2개(R-15, R-11)는 코드가 읽기 쉬워지지 않아 게시하지 않았다.
- DF-03은 CBRD-27237과 같은 결함이며, dcbf09e4f에서 재현했다. UPDATE를 ROLLBACK한 행의 원래 OOS 값을 vacuum이 지운다. 그 뒤 행을 읽으면 `ER_HEAP_OOS_CORRUPTED_RECORD`(-1389)가 난다.
- DF-01(tier-3 bestspace sync가 운영 경로에서 실행되지 않음), DF-02(demotion 기준이 사양과 다름), DF-04(`oos_find_best_page`가 에러를 버림)는 소스로 확인했다. DF-01은 gdb 관찰 하나가 소스 판정을 뒷받침한다. 2026-11-03 12:40에 JIRA를 다시 검색했다. DF-01은 CBRD-27213이, DF-02는 #8299(CBRD-27785)가 이미 다룬다. DF-04를 다루는 이슈는 없다.

| 확인된 것 | 열려 있는 것 |
| --- | --- |
| PR 7개의 동작 보존 근거. 로컬 ctest(PR7은 token 비교), 독립 리뷰, 독립 재빌드와 재실행 | PR 7개의 최종 CI 결과(아래 표의 CI 칸) |
| DF-03 재현. 단위 테스트, gdb 호출 경로, SQL 대조 실험 | DF-03의 kill -9 뒤 복구, savepoint rollback, release 빌드 동작 |
| DF-01, DF-02, DF-04의 소스 근거 | DF-01 때문에 OOS 파일이 실제로 더 커지는지(측정하지 않음) |
| NEEDS-DECISION 7개 항목의 결정 지점 | 그 결정. 유지보수자가 내린다. |

## Source revision, method, and limits

| 항목 | 값 |
| --- | --- |
| 저장소와 브랜치 | CUBRID/cubrid `feature/oos-merge` |
| 기준 commit | `dcbf09e4f7fd02ff9c8fc6493ec8887fc2919d67`. 조사하는 동안 바뀌지 않았다. |
| 작성일 | 2026-11-03 (Asia/Seoul) |
| 로컬 빌드 | `debug_gcc` preset, `UNIT_TEST_OOS=ON` |
| 단위 테스트 기준 | `ctest -R 'oos\|test_byte_span_writer'`, 44개 |
| 같은 코드를 고치는 진행 중 PR | #8128 (CBRD-26659), #8299 (CBRD-27785), #8330 (CBRD-27827), #8347 (CBRD-27841), #8348 (CBRD-27858), #8350 (CBRD-27860) |

방법은 네 단계다.

1. 구역 조사. 읽기 전용 agent 다섯 개가 구역 A-E를 하나씩 읽고 원시 후보 70개를 냈다. 이 단계에서는 빌드나 실행을 하지 않았다.
2. ledger 정리. 별도 판정 agent가 중복을 합치고 항목마다 위험, 작업량, 효과, 안전망, 진행 중 PR과의 겹침, 상태를 매겼다. coordinator가 PR 대기열 항목의 핵심 주장을 dcbf09e4f에서 다시 확인했다.
3. 30분 재검토. 30분마다 base commit과 진행 중 PR 목록이 바뀌었는지 확인했다. 그리고 다음 PR 후보의 근거를 코드에서 다시 읽었다. 이 과정에서 R-05를 NEEDS-DECISION으로, R-29를 #8347 쪽으로 옮겼다. DF-29와 DF-30도 이때 추가했다.
4. PR 단위 작업. 후보마다 별도 worktree에서 owner agent가 구현하고 ctest로 확인했다. 그다음 owner와 독립인 review lane(opus)과 gate lane(sonnet)이 같은 head SHA에서 각각 판정했다. review lane은 동작 보존, WAL과 래치 영향, 진행 중 PR과의 merge를 확인했다. gate lane은 다시 빌드하고 ctest를 다시 돌렸다. 두 번째 PR부터는 ccache를 끄고 빌드했다. 주석만 바꾼 PR7은 gate lane 대신 review lane이 token diff를 다시 확인했다. PR은 한 시간에 하나만 열었고, 연 뒤에는 tc base 확인을 거쳐 `/run all`을 한 번 보냈다.

한계는 다음과 같다.

- 후보 조사 자체는 정적 읽기다. 실행 근거는 PR 검증, DF-03 재현, 그리고 PR 검증 중에 얻은 DF-01과 DF-30 관찰뿐이다.
- 다음 영역은 읽지 않았거나 훑기만 했다. `log_recovery.c`, CBRD-26357의 storage format 코드, unloaddb와 compactdb의 raw fetch, `transform_cl.c`, `object_printer.cpp`, `unload_schema.c`, `locator_cl.c` 대부분, `server_support.c`, CDC와 flashback, TDE.
- #8299가 다시 쓰는 heap read 경로(`heap_file.c` 약 10950-12100행)와 demotion planner는 일부러 건너뛰었다. #8299 병합 뒤 다시 조사해야 한다.
- 진행 중 PR과의 겹침은 hunk 범위로 판정했다. 의미 수준의 겹침은 PR로 만든 후보에 대해서만 3-way merge와 컴파일로 확인했다.
- HA, 복제, sql.log 경로는 단위 테스트와 `/run all` 어디에도 없다. 이 영역의 항목은 실행으로 확인하지 않았다.
- 미사용 판정은 `src/`와 `unit_tests/` 검색에 기댄다. `contrib/`와 `util/`까지 검색한 것은 R-05뿐이다.
- 성능은 측정하지 않았다.

## Candidates turned into draft PRs

| Sub-task | PR | 항목 | 바뀐 것 | 검증 근거 | CI |
| --- | --- | --- | --- | --- | --- |
| [CBRD-27882](https://jira.cubrid.org/browse/CBRD-27882) | [#8367](https://github.com/CUBRID/cubrid/pull/8367) | R-01 | 쓰이지 않는 `OOS_STATS_PREV_BEST_INDEX`와 `bridge_oos_vpid_init_new`, `oos_stats_update`의 항상 0인 `prev_freespace` 인자, 중복 NULL 대입을 지운다. 3 files, +3/-14 | ctest 44/44, review PASS, gate PASS | 5/5 SUCCESS |
| [CBRD-27883](https://jira.cubrid.org/browse/CBRD-27883) | [#8368](https://github.com/CUBRID/cubrid/pull/8368) | R-06, R-07 | 호출 없는 SQL 테스트 helper 2개를 지운다. 두 header에 복사된 `test_oos_utils` helper 9개를 `test_oos_utils.hpp`로 옮긴다. 4 files, +165/-272 | ctest 44/44 전후, 테스트 TU 28개 재컴파일, #8128과 #8299 적용 상태에서도 컴파일 | 5/5 SUCCESS |
| [CBRD-27884](https://jira.cubrid.org/browse/CBRD-27884) | [#8369](https://github.com/CUBRID/cubrid/pull/8369) | R-08 | 두 heap 속성 writer에 복사된 LOB 복사 코드(약 40줄)를 `heap_attrvalue_copy_lob`으로 합친다. +64/-75 | ctest 44/44 전후, token 비교, gdb로 두 호출부 모두 helper 통과 | 5/5 SUCCESS (test_shell flaky 1건, rerun 후 통과) |
| [CBRD-27885](https://jira.cubrid.org/browse/CBRD-27885) | [#8370](https://github.com/CUBRID/cubrid/pull/8370) | R-10 | 네 번 반복된 "로그 없이 header 페이지 dirty" 6줄을 `oos_hdr_page_set_dirty_unlogged`로 합친다. +16/-27 | ctest 44/44, gdb로 세 곳은 기존 테스트가 실행, 나머지 한 곳은 조건을 강제해 실행 | 5/5 SUCCESS |
| [CBRD-27886](https://jira.cubrid.org/browse/CBRD-27886) | [#8371](https://github.com/CUBRID/cubrid/pull/8371) | R-14 | `xheap_destroy`와 `xheap_destroy_newly_created`에 복사된 OOS 파일 정리 18줄을 `heap_oos_remove_file`로 합친다. +41/-38 | ctest 44/44 전후, `DONT_REUSE_OID` 테이블 DROP을 gdb와 `cubrid diagdb -d 1`로 확인 | 5/5 SUCCESS |
| [CBRD-27887](https://jira.cubrid.org/browse/CBRD-27887) | [#8372](https://github.com/CUBRID/cubrid/pull/8372) | R-09 | `build_attr_change_map`의 INVISIBLE, PREFER_INLINE, FORCE_OUTLINE 판정 블록 3개를 `build_attr_flag_change_property`로 합친다. +53/-79 | 입력 768가지 전수 비교, 의도적 오류 8개 모두 검출, csql ALTER 35단계, ctest 44/44 | 5/5 SUCCESS |
| [CBRD-27888](https://jira.cubrid.org/browse/CBRD-27888) | [#8373](https://github.com/CUBRID/cubrid/pull/8373) | R-12 | 코드와 다른 사실을 말하는 OOS 주석을 고치고, 주석만 담은 빈 `if` 하나를 없앤다. 7 files, +38/-44 | 주석을 뺀 token diff는 빈 `if` 하나뿐, review가 새 주석을 코드와 하나씩 대조 | 5/5 SUCCESS |

#8369의 첫 `/run all`은 `test_shell`의 `check_option.sh` 44단계에서 실패했다. 이 단계는 unloaddb client 12개를 동시에 띄워 `max_clients=10` 한도에 걸리기를 기대한다. 이번에는 12개가 모두 성공해 기대와 달랐다. 최근 실행 51회 중 이 PR과 무관한 PR에서도 같은 실패가 3회 있었다. `/run rerun` 한 번으로 gha-ci 다섯 항목이 모두 통과했다.

각 후보를 PR로 만든 이유는 다음과 같다.

- **#8367.** 쓰이지 않는 매크로와 항상 0인 인자는 독자가 있지도 않은 의미를 찾게 만든다. 삭제는 컴파일러가 확인하므로 위험이 가장 낮았다. PR 절차 전체를 처음 시험하기에도 알맞았다.
- **#8368.** 두 helper 복사본은 이미 함수 순서, 중괄호, 주석이 서로 달라져 있었다. 한쪽만 고치는 실수를 막는다. 엔진 코드는 바뀌지 않는다.
- **#8369.** 대기열에서 가장 큰 운영 코드 중복이다. 두 번째 복사본은 OOS 병합 준비 작업(CBRD-26835, #7803)에서 생겼다. 앞으로 LOB 복사 규칙을 바꿀 때 한 곳만 고치면 된다.
- **#8370.** "힌트는 WAL이 필요 없다"는 이유가 네 곳에서 반복되었다. 이유를 한 곳에 적어 두면 WAL 규칙을 바꿀 때 빠뜨리는 곳이 없다. 이 PR을 검증하다가 네 곳 중 sync-scan 직전 한 곳에 어떤 테스트도 닿지 않는다는 것을 알았다. 이 관찰이 DF-01의 실행 근거가 되었다.
- **#8371.** heap을 지우는 두 경로가 OOS 파일을 같은 방식으로 지워야 한다는 규칙이 코드에 한 번만 남는다. 동작 차이가 하나 있고 PR 본문에 밝혔다. heap header 페이지가 손상되어 `heap_oos_find_vfid`가 에러 없이 실패하는 경우다. 이전 코드는 heap 파일과 OOS 파일을 모두 남겼고, 새 코드는 OOS 파일만 남긴다. 독립 리뷰는 이 경로가 손상된 header에서만 열리며 새 동작이 덜 남긴다고 판정했다.
- **PR6 (CBRD-27887).** OOS는 STORAGE 옵션을 추가하면서 INVISIBLE 판정 블록을 두 번 복사했다. enum 값을 bool로 바꾸는 부분이 위험 지점이라, 가능한 입력 전체를 비교하는 표로 확인했다. INVISIBLE 블록은 develop에 원래 있던 코드이므로 리뷰어가 이 부분을 따로 봐야 한다.
- **PR7 (CBRD-27888).** 없는 검사나 없어진 구현을 근거로 드는 주석은 잘못된 수정을 부른다. 예를 들어 heap 삭제와 갱신 경로의 주석은 OOS 즉시 삭제 조건을 "SA_MODE"라고 적지만, 실제 조건은 `!is_mvcc_op`이다. 실행 코드에서는 빈 `if` 하나만 사라진다.

## Candidates left out of PRs

67개 항목의 최종 상태는 다음과 같다.

| 상태 | 개수 | 뜻 |
| --- | --- | --- |
| PR | 8 | 위 표 |
| DEFERRED | 18 | 진행 중 PR과 같은 코드를 고친다. 그 PR이 병합된 뒤 다시 본다. |
| NEEDS-DECISION | 7 | 기술적으로는 할 수 있지만 유지보수자의 결정이 먼저다. |
| REPORT-ONLY | 29 | 효과가 작거나 위험이 효과보다 크다. 기록만 남긴다. |
| REJECTED | 5 | 취향 문제이거나 의도된 코드다. |

### DEFERRED

| 막고 있는 PR | 항목 | 내용 | 풀리는 조건 |
| --- | --- | --- | --- |
| #8330 | R-18, R-21, R-22, R-28 | bestspace entry 해제 helper와 mutex guard(R-18), `oos_stats_find_page_in_bestspace` 분해(R-21), `oos_find_best_page`의 header 소유와 fallback 정리(R-22), `oos_file.cpp`를 bestspace와 reclaim으로 분리(R-28) | #8330 병합. R-22는 DF-04를 고친 뒤에 한다. fallback을 하나로 합치면 버려지는 에러가 그대로 굳기 때문이다. R-28은 R-13, R-42, R-43 뒤에 한다. |
| #8299 | R-20, R-23, R-25, R-27, R-32 | 일회성 fault hook 7개를 한 타입으로(R-20), `oos_read`와 `oos_read_many`의 chain 끝 helper와 RAII page fix(R-23), 24 B inline stub codec 하나로(R-25), 순수 demotion planner(R-27), 큰 테스트 파일 분리(R-32) | #8299 병합. R-27은 DF-02와 함께 정한다. |
| #8128 | R-24, R-30 | OOS 복제 로그 emitter 하나로(R-24), 테스트 등록 CMake helper(R-30) | #8128 병합 |
| #8128, #8299 | R-19, R-31 | `bridge_*` seam 선언을 한 곳에(R-19), SQL 테스트 fixture 기반 클래스(R-31) | 두 PR 병합 뒤 한 번에 옮긴다. |
| #8299, #8330 | R-33 | tdes의 OOS 복제 LSA 상태 타입과 중첩 suppression guard | 두 PR 병합. WAL 경로이므로 따로 리뷰한다. |
| #8299, #8350 | R-26 | RECDES 수준 OOS helper를 `heap_file.c` 밖으로 | 두 PR 병합 |
| #8347 | R-29 | 기록하는 곳이 없는 `RVREPL_OOS_DELETE`를 지우고, 복구 주석과 rv handler 이름을 정리한다. | 새 PR이 아니라 #8347(CBRD-27841)에 합치기를 제안한다. #8347은 같은 종류의 미사용 인덱스 `RVOOS_NOTIFY_VACUUM`을 지우고 번호를 다시 매긴다. 같이 하면 번호를 두 번 바꾸지 않는다. |
| #8367 | R-13 | bestspace와 header 힌트 내부 정의를 내부 header로 옮기고 layout을 `static_assert`로 고정한다. | #8367 병합. 같은 `oos_file.hpp` 영역을 고친다. |
| #8368 | R-16 | 테스트 파일마다 있는 page와 chunk helper 복사본을 공용 header로 옮긴다. | #8368 병합. 새 header 위에 쌓인다. |

### NEEDS-DECISION

| 항목 | 현재 상태 | 유지보수자가 정할 것 |
| --- | --- | --- |
| R-34 | tier-3 sync 추정치, `second_best` ring, `idx_badspace`, sync 상수가 운영 경로에서 쓰이지 않는다(DF-01). | tier-3 bestspace sync를 사양 §2대로 고칠 것인가, 지울 것인가. 고치면 R-34는 DF-01 수정이 된다. 지우면 사양 §2도 바꾼다. 기존 이슈 CBRD-27213은 지우고 heap bestspace 재설계 기반으로 바꾸는 방향을 정했다. |
| R-05 | `oos_chunk_exists`, `oos_get_identity_stamp`, `oos_get_length`를 부르는 운영 코드가 없다. header 주석은 "tests and diagnostics"용이라고 적는다. | 진단 API로 남길 것인가, `CUBRID_UNIT_TEST_ENABLED` 빌드에서만 컴파일할 것인가. |
| R-35 | `LC_IS_FLUSH_INSERT`는 일반 insert와 `LC_FLUSH_INSERT_OOS`를 함께 참으로 본다. 오래된 TODO는 PR7에서 설명으로 바꿨다. | 매크로를 일반용과 OOS용으로 나눌 것인가, 지금 매크로를 유지할 것인가. |
| R-36 | 손상 검출 exit 16곳이 같은 에러 설정 순서를 반복한다. | `OOS_RETURN_ERROR` 같은 에러 매크로를 CUBRID 관례로 받아들일 것인가. |
| R-37 | `test_oos_mock_vacuum_server.cpp`와 `test_oos.cpp`에 다른 테스트가 이미 덮거나 아무것도 확인하지 않는 케이스가 있다. 읽기로만 판정했다. | CBRD-26659의 테스트 유지 정책상 이 케이스들을 지워도 되는가. |
| R-38 | 테스트 로그 계층(`test_oos_log.hpp`, 호출 45곳)은 기본값에서 아무것도 출력하지 않는다. | 계층을 지울 것인가, `test_oos_debug`만 남길 것인가. |
| R-39 | `file_type_to_string (FILE_OOS)`가 "OUT_OF_LINE_OVERFLOW_STORAGE"를 반환한다. 기능 이름은 Out-of-row Overflow Storage다. | 사용자에게 보이는 진단 문자열을 바꿀 것인가. 바꾸면 diagdb 출력을 비교하는 테스트 답안도 바뀔 것이다(추론). |

### REPORT-ONLY

| 항목 | 내용 | 기록만 남기는 이유 |
| --- | --- | --- |
| R-11 | `oos_file.cpp`의 `#if` 테스트 seam을 이름 있는 helper로 | 시험 PR을 버렸다. 아래 참고 |
| R-15 | `heap_oos.cpp`의 class repr 해제와 last-error helper | 시험 PR을 버렸다. 아래 참고 |
| R-17 | prefetch 조건에 이름 붙이기, midxkey OOS pre-scan 공유 | 효과가 작다. |
| R-40 | 셸 DB 수명 helper, 일회성 도구 이동 | CBRD-26659 스크립트 작업, #8347과 겹친다. |
| R-41 | `FILE_FTAB_COLLECTOR` RAII와 bitmap 순회 helper | lambda와 stop flag가 sweep 루프에 상태를 더한다. |
| R-42 | `oos_try_reclaim_page_internal` 단계 분리 | 래치, WAL, LSA gate 순서를 건드린다. |
| R-43 | reclaim sweep 단계 분리, side map registry 클래스 | single-flight와 condvar 동작을 건드린다. |
| R-44 | cache API 계약 정리 | redo 경로를 건드린다. |
| R-45 | sysop RAII guard | 소멸 순서 오류는 복구 버그가 된다. |
| R-46 | chunk header peek helper | 운영 코드 복사본이 2개뿐이고 에러 매핑이 서로 다르다. |
| R-47 | insert API 배관 정리 | 작은 단계만 떼면 효과가 작다. |
| R-48 | `oos_insert_across_pages`의 복제 guard 타입 | HA 쪽 확인 수단이 거의 없다. |
| R-49 | `oos_delete_chain`에서 head 검증 분리 | CBRD-26950 안전장치를 건드린다. |
| R-50 | `const_cast` 없는 physical log helper | `heap_file.c`가 쓰는 `LOG_DATA_ADDR` 관용구와 달라진다. |
| R-51 | 작은 코드 nit 모음 | 효과가 작다. |
| R-53 | VOT entry decoder가 공용 accessor를 쓰게 하기 | INT와 부호 처리에서 동작이 바뀐다. DF-07로 보냈다. |
| R-54 | 소유권을 가진 OOS payload 타입 | 여러 파일과 allocator를 바꾼다. |
| R-55 | eager cleanup gate helper | 줄어드는 양이 적다. 주석 부분은 PR7에 들어갔다. |
| R-56 | `la_rebuild_oos_recdes` 정리 | HA 경로라 단위 테스트와 `/run all`로 확인할 수 없다. |
| R-57 | `la_get_current`를 구조체 배열로 | 빌드 외에 확인 수단이 없다. |
| R-58 | sql.log OOS cache를 별도 TU 클래스로 | 300줄이 넘는 변경이다. |
| R-59 | `file_header_get_class_oid` helper | OOS 이전부터 있던 중복이다. |
| R-60 | `SM_ATTFLAG_OOS_STORAGE_MASK` | 재빌드 범위가 넓고 효과가 작다. |
| R-61 | `la_apply_*` prologue helper | flush 묶음 처리를 건드리고 단위 테스트가 없다. |
| R-62 | `ovf_list` 해제 helper, `oos_record_header.hpp` 분리 | 효과가 작다. |
| R-63 | SA와 SERVER 대칭 테스트 본문을 `.inc`로 공유 | macro로 펼쳐지는 TEST 본문은 읽기 어렵다. |
| R-64 | `OosFileTest` fixture, `insert_string` helper | 범위가 크다. R-07, R-16 뒤에 본다. |
| R-65 | `OOS_TEST_MAIN`, `gtest_main` 연결 | 효과가 작다. |
| R-66 | `xoos_get_stats_by_class_oid`를 `heap_oos.cpp`로 | 이미 테스트 빌드 전용이다. |
| R-71 | 여러 sector에 걸친 OOS 파일의 통계 테스트. `oos_get_stats_by_vfid()`(`SHOW HEAP OOS` 경로)가 sector bitmap을 펼쳐 세는 `num_recs`와 `recs_sumlen`을 sector 하나보다 큰 파일에서 확인하는 테스트가 없다. 지금 확인은 작은 파일뿐이고, `SweepCursorWrapsAcrossSectorBoundary`는 회수 sweep의 cursor와 페이지 수만 본다. 2026-11-03에 닫힌 PR #7614(CBRD-26831)와 비교해 추가했다. | 동작 결함은 찾지 못했고 테스트 보강만 남는다. #7614의 `BestspaceSectorBitmapSyncAcrossSectors`는 `oos_delete`가 `oos_chain_ref`를 받고 성장 게이트 sweep이 빈 페이지를 회수하도록 바뀌어 그대로 옮길 수 없다. sync 쪽 확인은 CBRD-27213이 sync를 지우면 필요 없다. |

REJECTED 5개는 다음과 같다. R-02(전방 선언 9개 삭제)는 CUBRID가 static 함수 prototype 블록을 빠짐없이 두는 관례와 맞지 않는다. R-03(`case FILE_OOS` fallthrough)은 문서화된 의도적 fallthrough다. R-04(`oos_info`와 FATAL 삭제)는 대칭인 로그 함수군의 일부다. R-52(`oos_vpid_init_new` 반환값)는 `FILE_INIT_PAGE_FUNC` callback이라 signature를 바꿀 수 없다. R-70은 모양만 바꾸는 변경 모음이라 리뷰어에게 잡음이 된다.

### Dropped trials

**R-15.** `heap_oos.cpp`에서 class representation 획득과 해제를 기존 `make_scope_exit`로 묶었다. `er_errid () == NO_ERROR ? ER_FAILED : er_errid ()` 관용구는 helper 하나로 바꿨다. owner는 ctest 44/44와 gdb trace 동일을 확인했다. 그러나 획득과 해제 사이에 이른 반환이 없어서 scope_exit가 보호할 경로가 없었다. 세 쌍 중 두 쌍만 바꿀 수 있었고 들여쓰기가 한 단계 늘었다. helper는 관용구 사용 10곳 중 5곳만 덮었다. 읽기 부담이 줄지 않아 04:08에 버렸다.

**R-11.** `oos_file.cpp`에서 운영 제어 흐름 사이에 있는 `#if` 테스트 seam 4곳을 이름 있는 no-op helper로 바꾸려 했다. 부분 diff는 seam 함수 10개를 더해 +71/-25였다. 운영 코드 독자가 얻는 것보다 코드가 더 늘었다. owner가 04:44 이후 진척이 없어 05:40에 멈추고 버렸다. 발견 하나는 남긴다. `oos_insert_many`의 `publication_count`는 두 publish 경로 모두에서 `pos`와 함께 늘어나므로 항상 `pos`와 같다(소스 확인). 다음에 이 함수를 고칠 때 지역 변수 하나를 줄일 수 있다.

## Defect candidates

근거 종류는 다음 네 가지로 표시한다. **실행**은 이번 조사에서 실행으로 관찰한 것이다. **소스(재확인)**는 coordinator가 dcbf09e4f에서 코드를 다시 읽어 확인한 것이다. **소스(조사)**는 구역 조사 agent의 판정이며 다시 확인하지 않은 것이다. **추론**은 코드에서 유도한 영향이며 관찰하지 않은 것이다.

### Priority defects

| 순위 | ID | 결함 후보 | 근거 종류 | 처리 |
| --- | --- | --- | --- | --- |
| 1 | DF-03 | ROLLBACK한 UPDATE의 원래 OOS chain을 vacuum이 지운다. | 실행, 소스(재확인) | CBRD-27237에 재현 근거 댓글을 남겼다. |
| 2 | DF-01 | tier-3 bestspace sync가 운영 경로에서 실행되지 않는다. | 소스(재확인), 실행(gdb 0회 관찰), 영향은 추론 | [CBRD-27213](https://jira.cubrid.org/browse/CBRD-27213)(Open)이 이미 다룬다. 그 이슈는 legacy sync를 고치지 않고, heap bestspace 재설계 기반으로 바꾸면서 지운다. |
| 3 | DF-02 | demotion 기준이 사양의 4,060 B가 아니라 `DB_PAGESIZE / 4`다. | 소스(재확인) | [#8299](https://github.com/CUBRID/cubrid/pull/8299)(CBRD-27785)의 commit `4c3c8d791`이 고친다. |
| 4 | DF-04 | `oos_find_best_page`의 이른 fallback이 에러를 버리고 새 페이지를 할당한다. | 소스(재확인), 영향은 추론 | 다루는 이슈가 없다(2026-11-03 12:40 JQL 검색). 새 버그 후보. R-22보다 먼저 고친다. |

**DF-03 (CBRD-27237).** vacuum은 `RVHF_UPDATE_NOTIFY_VACUUM`과 `RVHF_DELETE_NEWHOME_NOTIFY_VACUUM` 로그의 undo image를 따라가 옛 OOS chain을 지운다. 이 경로에는 commit과 abort를 구분하는 조건이 없다(소스 재확인). ROLLBACK한 UPDATE의 undo image는 아직 살아 있는 원래 값을 가리킨다. 사양 §3은 commit hook에서 `RVOOS_NOTIFY_VACUUM`을 남기고 이 forward-walk 삭제 경로를 없애라고 정한다. dcbf09e4f에는 이 인덱스를 기록하는 곳이 없고, #8347은 이 인덱스를 지운다. CBRD-27841 설명은 이 삭제가 CBRD-27230의 요구를 끝내거나 취소하지 않으며, 알림을 구현할 때 실제 복구 인덱스를 다시 정의해야 한다고 적는다. 그래서 #8347은 해결 방식과 무관하게 병합할 수 있다.

2026-11-03 02:09에 dcbf09e4f의 `debug_gcc` 빌드에서 다음을 관찰했다.

- 단위 테스트. 479cd960e에 비활성으로 남아 있던 `OosRealVacuum.RolledBackUpdateKeepsCommittedOosAfterVacuum`을 dcbf09e4f로 옮겨 두 번 실행했다. 두 번 모두 실패했다. rollback 직후에는 원래 OOS 값을 읽었지만, vacuum 뒤에는 `oos_read_with_alloc`이 -2를 반환했다.
- gdb. vacuum worker가 `vacuum_process_log_block`(vacuum.c:3619)에서 `vacuum_forward_walk_reclaim_oos`를 거쳐 `oos_delete_chain`을 불러, 커밋된 원래 chain을 지웠다.
- SQL. CBRD-27237의 재현 절차대로 UPDATE 뒤 ROLLBACK한 행은 vacuum 뒤 조회에서 -1389로 실패했다. UPDATE 뒤 COMMIT한 대조 행은 vacuum 뒤에도 정상으로 읽혔다.
- 확인하지 않은 범위. kill -9 뒤 복구, savepoint rollback, release 빌드.

**DF-01.** `oos_find_best_page`는 `estimates.num_other_high_best / estimates.num_pages`가 0.1 이상일 때만 sync를 부른다. `estimates.num_pages`를 쓰는 곳은 sync 안뿐이다. OOS 파일을 만들 때 header 통계는 0으로 채워진다. 그리고 유일한 sync 호출은 이 조건 안에 있으며, 실제 header가 아니라 0으로 채운 임시 `tmp_hdr`를 넘긴다. 그래서 실제 header의 `num_pages`는 0으로 남고 조건은 참이 되지 않는다(소스 재확인). #8370 검증 중 OOS 테스트 바이너리 36개를 gdb로 실행했을 때 sync-scan 지점에는 한 번도 닿지 않았다(실행). 영향은 추론이다. in-memory cache와 `best[]`에 없는 반쯤 빈 페이지를 다시 찾지 못해, OOS 파일이 공간을 재사용하지 않고 커질 수 있다. 사양 §2는 cache miss 때 `oos_stats_sync_bestspace()`를 부른다고 적는다. 같은 결함은 CBRD-27213의 설명에 이미 기록되어 있다. CBRD-27213은 legacy 해시, `best[]`, sync를 지우고 heap bestspace 재설계 기반으로 바꾸는 것을 해결 방향으로 정했다.

**DF-02.** demotion 판정과 중단 조건은 `DB_PAGESIZE / 4`(16 KB 페이지에서 4,086 B)를 쓴다. 사양 §1은 `heap_oos_inline_target_size()`(16 KB 페이지에서 4,060 B)를 요구하고 raw `DB_PAGESIZE/4`를 명시적으로 거부한다. 이 함수는 dcbf09e4f 소스에 없다. CBRD-27057은 JIRA에서 Resolved/Fixed지만, 그 구현인 draft #7462는 병합되지 않고 닫혔다. 2026-11-03 01:54에 CBRD-27057에 남은 댓글에 따르면, 같은 수정이 #8299(CBRD-27785)의 commit `4c3c8d791`로 옮겨졌다. 12:40에 이 commit이 #8299에 있는 것을 확인했다. 따라서 DF-02는 #8299가 병합되면 풀린다.

**DF-04.** `file_get_sticky_first_page`가 실패해도 에러를 스택에 둔 채 새 페이지를 할당한다. header `pgbuf_fix`가 실패해도, `ER_INTERRUPTED`인 경우까지 포함해 할당으로 넘어간다. 반면 sync 뒤 header를 다시 fix하는 곳은 `ER_INTERRUPTED`를 확인하고 멈춘다. 이른 fallback 경로는 새 페이지를 cache에 등록하는 단계도 건너뛴다(소스 재확인). 인터럽트된 요청이 멈추지 않고 페이지를 하나 더 할당하며, 남은 에러가 뒤의 판단을 흐릴 수 있다(추론). 2026-11-03 12:40 JQL 검색에서 이 문제를 다루는 이슈는 없었다.

### Other defect candidates

| ID | 결함 후보 | 근거 종류 | 확신 | 처리 |
| --- | --- | --- | --- | --- |
| DF-29 | `heap_attrinfo_transform_variable_to_disk`에서 BLOB/CLOB 값의 ELO가 NULL이면 가변 속성 루프 중간에 함수 전체가 `S_SUCCESS`로 끝나, 뒤의 가변 속성을 쓰지 않는다. develop에 원래 있던 코드다(git blame, CBRD-26361). #8369는 이 동작을 그대로 보존했다. | 소스(재확인), 도달 가능성 미확인 | 코드 중, 도달성 낮음 | LOB 담당자 확인 |
| DF-30 | ctest timeout이 테스트 도중 서버를 죽인 뒤, 공용 unittestdb 재시작 복구가 `log_rv_analysis_sysop_end`(log_recovery.c:1750)의 assert에 걸려 이후 서버 테스트가 모두 중단되었다. 한 번 관찰했고 재실행은 통과했다. | 실행(1회) | 중하 | kill 뒤 복구 재현으로 확인 |
| DF-05 | MVCC 재평가가 레코드를 eager OOS 경로로 다시 만든다. 동시 UPDATE 재평가에서 `ER_GENERIC_ERROR`와 고아 chunk가 생길 수 있다. | 소스(조사) | 낮음 | 동시 UPDATE 재현 뒤 등록 |
| DF-06 | `oos_delete_chain`에서 continuation chunk가 없으면 에러 설정 없이 `ASSERT_ERROR_AND_SET`에 닿는다. read 경로는 같은 경우를 `ER_HEAP_OOS_CORRUPTED_RECORD`로 바꾼다. | 소스(재확인) | 높음 | 새 버그 후보(낮은 우선순위) |
| DF-24 | #8128이 `test_oos_boundaries`를 `RESOURCE_LOCK OOS_SHARED_UNITTESTDB` 없이 등록한다. `ctest -j`에서 다른 테스트와 DB를 두고 경쟁할 수 있다. | 소스(재확인) | 중상 | #8128에 전달 |
| DF-20 | 정상적인 운영 실패(`ER_INTERRUPTED`, 디스크 부족)에 `assert (false)`가 걸려 debug QA 실행을 중단시킨다. | 소스(조사) | 중 | 기록 |
| DF-12 | HAS_OOS인데 OOS 파일이 없으면 forward-walk가 `assert_release` 뒤 계속한다. release에서는 조용한 누수다. | 소스(조사) | 중 | 기록 |
| DF-09 | 복제 적용 경로 다섯 곳이 `oos_oids`만 비우고 `tdes->oos_insert_lsa_queue`는 비우지 않는다. | 소스(조사) | 중하 | 큐가 비어 있지 않을 수 있는지 확인 |
| DF-10 | `la_get_oos_chunk_oid`가 읽기 실패를 `NO_ERROR`와 null OID로 바꾸고, 호출부는 결과를 무시한다(sql.log 전용). | 소스(조사) | 중 | 기록 |
| DF-11 | `la_rebuild_oos_recdes`가 전체 길이만 확인하고 chunk 순서는 확인하지 않는다. | 소스(조사) | 중 | 기록 |
| DF-07 | 복제 fixup이 VOT offset BYTE와 SHORT만 처리하고, INT에서는 에러 설정 없이 `ER_FAILED`를 반환한다. | 소스(조사), 도달성은 추론 | 코드 높음, 도달성 낮음 | 기록 |
| DF-08 | bounds 확인 전에 VOT를 읽는 곳이 세 군데 있다. 손상된 레코드에서만 문제가 된다. | 소스(조사) | 중 | 기록 |
| DF-14 | `oos_create_file_internal`이 `NO_ERROR`와 NULL 페이지 조합에서 `er_set` 없이 `ER_FAILED`를 반환한다. | 소스(조사) | 중 | 기록 |
| DF-19 | 잘못된 인자 처리가 함수마다 다르고, `oos_read`는 head NULL 확인이 없다. | 소스(조사) | 중 | 기록 |
| DF-13 | cache 힌트는 `spage_get_free_space_without_saving` 값을 저장하고, 조회는 `spage_max_space_for_new_record`와 비교한다. page fix 때 바로잡힌다. | 소스(조사) | 중 | 기록 |
| DF-15 | sync가 `ER_INTERRUPTED`를 지운다. DF-01이 남아 있는 동안은 실행되지 않는다. | 소스(조사) | 중 | DF-01과 함께 |
| DF-31 | `oos_get_stats_by_vfid()`가 page fix 실패를 모두 `er_clear ()`하고 넘어가(`oos_file.cpp:3880-3886`) `ER_INTERRUPTED`를 지운다. `pgbuf_fix`는 인터럽트를 감지하면 표시를 지우고 이 에러만 남기므로, `SHOW HEAP OOS` 중의 ^C와 KILL이 사라진다. 같은 파일의 `oos_reclaim_fix_candidate()`는 `ER_INTERRUPTED`를 돌려준다. DF-15와 달리 운영 경로에서 실행된다. 2026-11-03에 닫힌 PR #7614와 비교해 추가했다. | 소스(재확인), 실행 안 함 | 중 | 기록. 고칠 때는 `ER_INTERRUPTED`만 돌려주고 busy와 deallocated page는 계속 건너뛴다. #7614처럼 모든 오류를 돌려주면 `lock_timeout=0`에서 busy page도 실패가 된다(추론). |
| DF-27 | `oos_insert_within_page`는 정렬하지 않은 크기를, `oos_insert_many`는 정렬한 크기를 `oos_find_best_page`에 넘긴다. | 소스(조사), 영향 미증명 | 낮음 | 기록 |
| DF-28 | 오류 경로 7곳이 `heap_oos_begin_insert_publication`의 `S_ERROR`를 무시한다. | 소스(조사) | 낮음 | 기록 |
| DF-16 | sweep 대기자가 인터럽트 확인 없이 `pthread_cond_wait`에서 기다린다. 의도된 절충일 가능성이 크다. | 소스(조사) | 낮음 | 기록 |
| DF-17 | `oos_bestspace_initialize`가 실패 시 부분 상태를 남기고 static mutex를 다시 초기화한다. | 소스(조사) | 낮음 | 기록 |
| DF-18 | `oos_remove_file`의 임계 구역이 둘로 나뉘어 있다. 힌트를 검증하므로 해는 없다. | 소스(조사) | 낮음 | 기록 |
| DF-21 | `STORAGE FORCE_OUTLINE`은 끝까지 구현되어 있지만 사양에는 없다. | 소스(조사) | 높음 | 사양 갱신 |
| DF-22 | `log_append_*_crumbs` 두 함수가 `RVHF_INSERT_NEWHOME`에서 다르게 동작한다. develop에 원래 있던 것으로 OOS와 무관하다. | 소스(조사) | 높음 | 범위 밖 |
| DF-23 | `ER_OUT_OF_VIRTUAL_MEMORY` 인자 크기가 틀린 곳이 있고, `la_apply_oos_insert_log`는 "apply_insert"로 로그를 남긴다. | 소스(조사) | 높음 | 표기 수정 |
| DF-25 | 테스트의 `ServerEnv`가 boot 결과를 `assert`로만 확인해, Release 빌드에서 `db_restart` 실패를 무시한다. | 소스(조사) | 높음 | 테스트 기반 수정 |
| DF-26 | 테스트 fault hook 두 개는 해제 함수가 없어, 실패한 케이스가 다음 케이스에 hook을 남길 수 있다. | 소스(조사) | 중 | 테스트 기반 수정 |

## Next steps

1. CBRD-27237(DF-03)을 먼저 고친다. 데이터 손실이며 fix-before-release 항목이다. 수정 방식 후보는 세 개다. 사양 §3의 commit 조건부 알림(A), COMMIT 여부 확인(B), 삭제 전 현재 행 확인(C)이다. 비교와 읽을 자료는 [담당자가 정할 것](CBRD-27881-owner-decisions_dcbf09e_claude.md) 1절에 있다. 어느 방식을 골라도 #8347은 병합할 수 있다. A를 고르면 알림을 구현할 때 복구 인덱스를 다시 정의한다. 회귀 테스트는 479cd960e의 비활성 테스트를 다시 켜면 된다. 2026-11-03에 담당자는 수정 방식이 정해질 때까지 #8347을 보류하기로 했다.
2. PR 7개는 모두 CI 5/5를 통과했고 draft로 둔다. ready 전환과 리뷰 요청은 담당자가 직접 한다. 서로 독립이므로 어떤 순서로도 병합할 수 있다. 실행 코드 변화가 적은 순서로 #8367, #8368, #8373, #8370, #8369, #8371, #8372를 제안한다.
3. NEEDS-DECISION 7개를 정한다. R-34(DF-01의 tier-3 sync를 고칠지 지울지)는 CBRD-27213의 방향(지우고 재설계)을 따르면 된다. R-05와 R-39는 짧게 정할 수 있다.
4. DF-04를 JIRA에 등록할지 정한다. DF-01은 CBRD-27213이, DF-02는 #8299가 이미 다룬다. 2026-11-10: DF-04는 [CBRD-28017](https://jira.cubrid.org/browse/CBRD-28017)(CBRD-26978 Sub-task)로 등록했다. R-22는 그 수정 뒤에 한다.

정할 항목을 쉬운 말로 다시 쓴 문서가 두 개 있다. [담당자가 정할 것](CBRD-27881-owner-decisions_dcbf09e_claude.md)은 CBRD-27237 수정 방식, PR 리뷰 요청, #8371 동작 차이, DF-04를 다룬다. [결정 필요 리팩토링 항목](CBRD-27881-needs-decision-items_dcbf09e_claude.md)은 NEEDS-DECISION 7개를 다룬다.
5. R-29를 #8347(CBRD-27841) 작성자에게, DF-24를 #8128(CBRD-26659) 작성자에게 전달한다.
6. 진행 중 PR이 병합될 때마다 DEFERRED 항목을 다시 본다. #8330은 R-18, R-21, R-22, R-28을 연다. #8128은 R-24, R-30을, #8299는 R-20, R-23, R-25, R-27, R-32를 연다. #8367은 R-13을, #8368은 R-16을 연다.
7. DF-30을 kill 뒤 복구 재현으로 확인해, 실제 복구 결함인지 테스트 DB 문제인지 가른다.
8. #8299 병합 뒤 heap read 경로와 demotion planner를 다시 조사한다.

## Evidence

조사 ledger, 결정 기록, 구역별 조사 원문, 실행 로그는 공개 위치가 없다. 필요한 내용은 이 문서에 요약했다. PR별 본문과 검증 기록은 이 디렉터리의 `*-pr-body_*`, `*-pr-context_*` 파일이며 [README](README.md)에 목록이 있다.

### Pull requests and CI

- 이 조사에서 만든 draft PR. [#8367](https://github.com/CUBRID/cubrid/pull/8367), [#8368](https://github.com/CUBRID/cubrid/pull/8368), [#8369](https://github.com/CUBRID/cubrid/pull/8369), [#8370](https://github.com/CUBRID/cubrid/pull/8370), [#8371](https://github.com/CUBRID/cubrid/pull/8371), [#8372](https://github.com/CUBRID/cubrid/pull/8372), [#8373](https://github.com/CUBRID/cubrid/pull/8373).
- #8369의 첫 `/run all`([실행 41495947206](https://github.com/CUBRID/cubrid/actions/runs/41495947206), `test_shell` 실패)과 rerun([실행 41507656612](https://github.com/CUBRID/cubrid/actions/runs/41507656612), 통과).
- 겹침을 확인한 진행 중 PR. [#8128](https://github.com/CUBRID/cubrid/pull/8128), [#8299](https://github.com/CUBRID/cubrid/pull/8299), [#8330](https://github.com/CUBRID/cubrid/pull/8330), [#8347](https://github.com/CUBRID/cubrid/pull/8347), [#8348](https://github.com/CUBRID/cubrid/pull/8348), [#8350](https://github.com/CUBRID/cubrid/pull/8350).
- DF-02 관련으로 병합되지 않고 닫힌 draft. [#7462](https://github.com/CUBRID/cubrid/pull/7462).

### JIRA

- 상위 작업 [CBRD-27881](https://jira.cubrid.org/browse/CBRD-27881). sub-task는 위 PR 표에 링크했다.
- [CBRD-27237](https://jira.cubrid.org/browse/CBRD-27237). DF-03 재현 근거를 댓글 4777509로 남겼다.
- [CBRD-27057](https://jira.cubrid.org/browse/CBRD-27057)(DF-02), [CBRD-27841](https://jira.cubrid.org/browse/CBRD-27841)(R-29 전달 대상).
- [CBRD-27213](https://jira.cubrid.org/browse/CBRD-27213)(DF-01과 R-34를 다루는 기존 이슈), [CBRD-27785](https://jira.cubrid.org/browse/CBRD-27785)(DF-02 수정을 담은 #8299의 이슈).

### Source at dcbf09e4f

| 근거 | 위치 |
| --- | --- |
| DF-01 sync 조건과 임시 header로 부르는 sync | [oos_file.cpp L3080-L3105](https://github.com/CUBRID/cubrid/blob/dcbf09e4f7fd02ff9c8fc6493ec8887fc2919d67/src/storage/oos_file.cpp#L3080-L3105) |
| DF-01 `estimates.num_pages`를 쓰는 유일한 곳 | [oos_file.cpp L980-L1002](https://github.com/CUBRID/cubrid/blob/dcbf09e4f7fd02ff9c8fc6493ec8887fc2919d67/src/storage/oos_file.cpp#L980-L1002) |
| DF-01 파일 생성 시 header 통계 0 초기화 | [oos_file.cpp L1163-L1165](https://github.com/CUBRID/cubrid/blob/dcbf09e4f7fd02ff9c8fc6493ec8887fc2919d67/src/storage/oos_file.cpp#L1163-L1165) |
| DF-02 demotion 판정과 중단 조건 | [heap_file.c L13177](https://github.com/CUBRID/cubrid/blob/dcbf09e4f7fd02ff9c8fc6493ec8887fc2919d67/src/storage/heap_file.c#L13177), [heap_file.c L13210](https://github.com/CUBRID/cubrid/blob/dcbf09e4f7fd02ff9c8fc6493ec8887fc2919d67/src/storage/heap_file.c#L13210), [heap_oos.cpp L129](https://github.com/CUBRID/cubrid/blob/dcbf09e4f7fd02ff9c8fc6493ec8887fc2919d67/src/storage/heap_oos.cpp#L129) |
| DF-03 vacuum의 forward-walk 호출 두 곳 | [vacuum.c L3616-L3621](https://github.com/CUBRID/cubrid/blob/dcbf09e4f7fd02ff9c8fc6493ec8887fc2919d67/src/query/vacuum.c#L3616-L3621), [vacuum.c L3757-L3765](https://github.com/CUBRID/cubrid/blob/dcbf09e4f7fd02ff9c8fc6493ec8887fc2919d67/src/query/vacuum.c#L3757-L3765) |
| DF-03 forward-walk 본체 | [vacuum_oos.cpp L248-L369](https://github.com/CUBRID/cubrid/blob/dcbf09e4f7fd02ff9c8fc6493ec8887fc2919d67/src/query/vacuum_oos.cpp#L248-L369) |
| DF-04 이른 fallback, sync 뒤 확인, cache 등록 | [oos_file.cpp L3024-L3036](https://github.com/CUBRID/cubrid/blob/dcbf09e4f7fd02ff9c8fc6493ec8887fc2919d67/src/storage/oos_file.cpp#L3024-L3036), [L3108-L3116](https://github.com/CUBRID/cubrid/blob/dcbf09e4f7fd02ff9c8fc6493ec8887fc2919d67/src/storage/oos_file.cpp#L3108-L3116), [L3155-L3160](https://github.com/CUBRID/cubrid/blob/dcbf09e4f7fd02ff9c8fc6493ec8887fc2919d67/src/storage/oos_file.cpp#L3155-L3160) |
| DF-29 루프 중간 반환 | [heap_file.c L13994-L13998](https://github.com/CUBRID/cubrid/blob/dcbf09e4f7fd02ff9c8fc6493ec8887fc2919d67/src/storage/heap_file.c#L13994-L13998) |
| DF-30 복구 assert | [log_recovery.c L1750](https://github.com/CUBRID/cubrid/blob/dcbf09e4f7fd02ff9c8fc6493ec8887fc2919d67/src/transaction/log_recovery.c#L1750) |
| R-05 테스트용 probe 선언과 주석 | [oos_file.hpp L209-L219](https://github.com/CUBRID/cubrid/blob/dcbf09e4f7fd02ff9c8fc6493ec8887fc2919d67/src/storage/oos_file.hpp#L209-L219) |
| R-11 `publication_count`와 `pos` | [oos_file.cpp L2243-L2299](https://github.com/CUBRID/cubrid/blob/dcbf09e4f7fd02ff9c8fc6493ec8887fc2919d67/src/storage/oos_file.cpp#L2243-L2299) |
| R-29 기록하는 곳이 없는 `RVREPL_OOS_DELETE` | [recovery.h L205](https://github.com/CUBRID/cubrid/blob/dcbf09e4f7fd02ff9c8fc6493ec8887fc2919d67/src/transaction/recovery.h#L205), [recovery.c L899-L900](https://github.com/CUBRID/cubrid/blob/dcbf09e4f7fd02ff9c8fc6493ec8887fc2919d67/src/transaction/recovery.c#L899-L900), [tde.h L142](https://github.com/CUBRID/cubrid/blob/dcbf09e4f7fd02ff9c8fc6493ec8887fc2919d67/src/storage/tde.h#L142) |
| R-35 `LC_IS_FLUSH_INSERT` | [locator.h L126-L132](https://github.com/CUBRID/cubrid/blob/dcbf09e4f7fd02ff9c8fc6493ec8887fc2919d67/src/transaction/locator.h#L126-L132) |
| R-39 FILE_OOS 진단 문자열 | [file_manager.c L3038-L3039](https://github.com/CUBRID/cubrid/blob/dcbf09e4f7fd02ff9c8fc6493ec8887fc2919d67/src/storage/file_manager.c#L3038-L3039) |

### OOS specification at 3462a7f

- §1 demotion 기준(4,060 B, raw `DB_PAGESIZE/4` 거부). [OOS-CONTEXT.md L60-L87](https://github.com/vimkim/cubrid-oos-context/blob/3462a7f69a7ec0de8a0b97ad8da32b463ecf0e8c/OOS-CONTEXT.md?plain=1#L60-L87)
- §2 cache miss 때 sync. [OOS-CONTEXT.md L165](https://github.com/vimkim/cubrid-oos-context/blob/3462a7f69a7ec0de8a0b97ad8da32b463ecf0e8c/OOS-CONTEXT.md?plain=1#L165)
- §3 commit hook의 `RVOOS_NOTIFY_VACUUM`과 forward-walk 삭제 경로 제거. [OOS-CONTEXT.md L216](https://github.com/vimkim/cubrid-oos-context/blob/3462a7f69a7ec0de8a0b97ad8da32b463ecf0e8c/OOS-CONTEXT.md?plain=1#L216)
- §4 UPDATE 뒤 고아 chain 금지. [OOS-CONTEXT.md L236](https://github.com/vimkim/cubrid-oos-context/blob/3462a7f69a7ec0de8a0b97ad8da32b463ecf0e8c/OOS-CONTEXT.md?plain=1#L236)

### DF-03 regression test

- 비활성 회귀 테스트를 남긴 commit. [vimkim/cubrid 479cd960e](https://github.com/vimkim/cubrid/commit/479cd960ec04196c92bf9789b1fc340af9046c2c). 재현에서는 이 테스트를 dcbf09e4f로 옮겨 `DISABLED_`만 뗐다.
