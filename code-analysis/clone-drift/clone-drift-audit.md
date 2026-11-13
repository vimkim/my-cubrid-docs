# 중복 코드 drift 감사: 한쪽 복사본에만 들어간 수정 찾기

- 분석일: 2026-11-13 (Asia/Seoul)
- 대상: CUBRID `develop` `e64a04a79a` (`/home/vimkim/gh/cb/develop`), `src/` 전체. 소스는 수정하지 않았다.
- 재현에 쓴 설치본: `11.5.0.2635-30043f4` debug build. `30043f4`는 `e64a04a79a`의 조상이고, 재현한 함수(`consume_tokens`)의 본문은 두 커밋에서 같다(시그니처만 `std::string` → `const std::string &`로 바뀜).
- 도구: PMD CPD 7.29.0, lizard 1.26.0, git. 도구 평가는 개인 문서 저장소 `my-docs`의 `workflow-tools/2026-11-13-static-analysis-tool-trial.md`에 있다.
- 관련 이슈: [CBRD-28080](https://jira.cubrid.org/browse/CBRD-28080) (보정용 기준 결함). 이번 감사에서는 JIRA를 등록하지 않았다.

## 1. 질문과 결론

질문: CUBRID 안에서 복사된 코드 중, 한쪽에만 버그 수정(NULL·오류 검사, 범위 검사, latch 해제, 오류 경로 정리, 타입 폭)이 들어가고 다른 쪽은 그대로 남은 곳이 있는가. CBRD-28080이 이런 경우다. broker `cas_execute.c`의 `convert_db_value_to_string`은 `db_get_char`가 NULL이면 NULL을 돌려주고 호출자가 검사하지만, C++로 옮긴 `method_query_util.cpp`의 같은 함수는 그 검사 없이 `std::string (NULL)`을 만든다.

결론:

- 약 75개 함수 쌍을 비교했다. **재현된 새 결함 1건**, 코드로 확인한 그럴듯한 결함 4건, 실제 drift지만 지금은 호출되지 않는 코드 1묶음(7건)이 나왔다.
- 가장 강한 결과는 D1이다. Java SP의 서버 측 JDBC(PL/CSQL `EXECUTE IMMEDIATE` 포함)가 `?` 개수를 셀 때 `no_backslash_escapes`를 무시한다. 백슬래시로 끝나는 문자열 리터럴이 있으면 정상 SQL이 바인드 오류로 실패한다. broker 쪽은 2012년에 고쳐졌고(CUBRIDSUS-8197, CUBRIDSUS-7481), 2022년 C++ 이식(CBRD-23846) 때 그 조건이 주석 처리되었다.
- 방법에 대한 결론. CPD(토큰 기반 중복 탐지)는 CBRD-28080 쌍을 최소 토큰 60에서도 찾지 못했다. C++ 이식 과정에서 코드가 다시 쓰였기 때문이다. 같은 이름의 함수를 파일 간에 짝짓는 단순한 방법(이하 "이름 쌍")이 CBRD-28080과 D1을 모두 찾았다. CPD는 같은 파일이나 같은 모듈 안의 변형 복사본(D3, D4, D7)을 찾는 데 쓸모가 있었다. 두 방법을 함께 써야 한다.

### 후보 요약

| ID | 판정 | 범주 | 수정된 쪽 | 수정 안 된 쪽 | 찾은 방법 |
| --- | --- | --- | --- | --- | --- |
| D1 | **real, 재현됨** | 문자열 경계 검사 | `broker/cas_common_execute.c:225`, `:243` | `method/method_query_util.cpp:608`, `:626` | 이름 쌍 9위 |
| D2 | plausible | 오류 검사 | `storage/compactdb_sr.c:111` | `executables/compactdb.c:572` | 이름 쌍 |
| D3 | plausible (메모리 부족 시에만) | NULL 검사·오류 경로 정리 | `query/query_hash_scan.c:232-239` | `query/query_aggregate.cpp:2920-2923` | CPD 530위 |
| D4 | plausible (정의되지 않은 동작) | 버퍼 수명 | `storage/heap_file.c:17415` | `storage/heap_file.c:26495`, `:26534` | CPD 358위 |
| D5 | real drift, 현재 도달 불가 | SQL·이름 비교 7건 | `broker/cas_execute.c` | `method/method_schema_info.cpp` | 이름 쌍 2위 등 |
| D6 | plausible-low | 문자열 길이 | `broker/cas_execute.c:3867` | `method/method_query_util.cpp:762` | 이름 쌍 |
| D7 | latent | 오류 코드 검사 | `thread/critical_section.c:1290` | `thread/critical_section.c:602` | CPD 1379위 |
| D8 | real, 사소함 | 메모리 해제 | `executables/compactdb_cl.c:924` | `executables/compactdb.c:130` | 이름 쌍 |
| K | 기존 결함 (보정) | NULL 검사 | `broker/cas_execute.c:10201` | `method/method_query_util.cpp:463` | 이름 쌍 49위 |

## 2. 방법

모든 단계는 [tools/](tools/)의 스크립트로 다시 실행할 수 있다.

```bash
tools/run_all.sh /home/vimkim/gh/cb/develop <outdir> 120
```

1. **CPD 두 번 실행** (`tools/run_cpd.sh`). 기본 모드는 `--dir src`로, 식별자·리터럴 무시 모드는 `src/base/jisx0212.h`, `ksc5601.h`, `CRC.h`를 뺀 `--file-list`로 돌렸다. 최소 토큰은 120이다. 결과는 기본 모드 519그룹, 무시 모드 4,081그룹이고, 합쳐서 63초가 걸렸다(80코어).
2. **함수 매핑과 순위** (`tools/rank_pairs.py`). lizard CSV(함수 25,111개)로 각 구간을 가장 많이 겹치는 함수에 매핑하고, 그룹을 함수 쌍으로 펼쳤다(그룹 크기 7 이상은 표 생성 패턴이라 제외). 쌍마다 양쪽 함수 범위를 `git blame`해서 가장 최근 커밋 날짜를 구했다. 점수는 `토큰/100 × (1 + 2·모듈 간 + 0.5·파일 간) × (1 + 날짜 차이(년, 최대 10))`이다. 2,866쌍이 나왔다.
3. **잡음 제거** (`tools/filter_pairs.py`). 한쪽이 함수 밖(`<global>`)인 쌍, 줄의 60% 이상이 `case`/`return`/열거자인 쌍, `if`/`for`/`while`이 3개 미만인 쌍, 본문이 완전히 같은 쌍을 뺐다. 1,019쌍이 남았다. 무시 모드 상위는 대부분 enum·문자열 표·`switch` 나열이었고, 이 단계에서 걸러졌다.
4. **이름 쌍** (`tools/name_twins.py`). 보정 단계에서 CPD가 CBRD-28080 쌍(`convert_db_value_to_string`)을 최소 토큰 60에서도 찾지 못했다. 그래서 lizard 함수 목록에서 같은 짧은 이름(네임스페이스 제외)을 가진 함수를 서로 다른 파일 사이에서 짝지었다. 크기 6줄 이상, 토큰 유사도 0.45~0.995, 같은 이름 4개 이하로 제한했다. 120쌍이 나왔고 CBRD-28080 쌍은 49위였다.
5. **검토 대상 선정.** 모듈 간 쌍과 git 날짜 차이가 큰 쌍을 우선하고, `xts_save_*`/`stx_build_*`처럼 같은 틀로 찍어 낸 함수 묶음은 하나만 남겼다. 약 75쌍을 6개 묶음(S1~S6)으로 나눴다.
6. **비교와 분류.** 묶음마다 하위 에이전트(Sonnet)가 [tools/review-recipe.md](tools/review-recipe.md)에 따라 두 본문을 diff하고, 차이를 NULL·오류 검사, 범위 검사, latch 해제, 오류 경로 정리, 타입 폭, 의도된 차이, 표면적 차이로 나눴다. 의도되지 않은 차이는 `git log -L`, `git log -S`로 어느 쪽이 언제 바뀌었는지 찾았다.
7. **검증.** 하위 에이전트가 낸 후보는 모두 직접 소스를 다시 읽어 확인했다. D1은 debug 설치본에서 재현했다.

## 3. 검토한 쌍 순위 표

"출처"는 CPD 순위(`rank_pairs.py` 결과의 행 번호) 또는 이름 쌍 순위다. 판정의 "의도"는 두 복사본이 다른 일을 하도록 만든 차이라는 뜻이다.

| 묶음 | 출처 | A | B | 차이 분류 | 판정 |
| --- | --- | --- | --- | --- | --- |
| S2 | CPD 1 | `broker/cas_str_like.c:102` `str_eval_like` | `method/method_query_util.cpp:72` | 없음(본문 동일) | drift 없음 |
| S2 | 이름 9 | `broker/cas_common_execute.c:192` `consume_tokens` | `method/method_query_util.cpp:576` | 경계 검사 조건 주석 처리 | **D1** |
| S2 | 이름 49 | `broker/cas_execute.c:10201` `convert_db_value_to_string` | `method/method_query_util.cpp:463` | NULL 검사 | K (CBRD-28080) |
| S2 | 이름 | `broker/cas_execute.c:10225` `serialize_collection_as_string` | `method/method_query_util.cpp:786` | NULL 검사(K의 호출자) | K에 포함 |
| S2 | 이름 8 | `broker/cas_execute.c:3772` `get_column_default_as_string` | `method/method_query_util.cpp:685` | 문자열 끝 NUL 중복 | D6 |
| S2 | 이름 | `broker/cas_str_like.c:72` `str_like` | `method/method_query_util.cpp:450` | 소문자 변환 함수 | D5 범위(죽은 호출자) |
| S2 | 이름 | `broker/cas_common_execute.c:131` `get_stmt_type` | `method/method_query_util.cpp:478` | C 쪽만 `select`/`merge` 추가 | 의도(C++은 CALL만 판별) |
| S2 | 이름 | `broker/cas_execute.c:10455` `set_host_variables` | `method/method_query_handler.cpp:1095` | 표면적 | drift 없음 |
| S2 | 이름 | `broker/cas_execute.c:3901` `set_column_info` | `method/method_query_handler.cpp:1050` | 의도 | drift 없음 |
| S2 | 이름 | `broker/cas_execute.c:3294` `get_set_domain` | `method/method_query_util.cpp:825` | 반환 타입 공간 다름 | 의도 |
| S2 | CPD 31 | `method/query_method.cpp:446` `method_fixup_set_vobjs` | `query/cursor.c:177` | 표면적 | drift 없음 |
| S2 | 이름 7 | `method/method_callback.cpp:549` `is_supported_dbtype` | `sp/pl_executor.cpp:222` | 없음 | drift 없음 |
| S1 | 이름 2, 6, 11, 13, 14, 16 등 | `broker/cas_execute.c` `sch_*` 15개 함수 | `method/method_schema_info.cpp` | SQL·이름 비교 | **D5** (7건) |
| S1 | CPD | `method/method_schema_info.cpp:1139` `get_schema_*_meta` | `method/method_struct_schema_info.cpp:144` | 공백만 | drift 없음 |
| S3 | CPD 461, 이름 1 | `broker/cas.c:878` `process_request` | `broker/cas_cgw.c:466` | shard·세션 분기 없음 | 의도(CGW에는 CUBRID 엔진이 없음) |
| S3 | CPD 617, 738, 785, 830 | `cas_execute.c`/`cas_function.c` `ux_auto_commit`, `ux_fetch`, `fn_end_tran`, `fn_close_req_handle` | `cas_cgw_execute.c`/`cas_cgw_function.c` | CALL·keep session 분기 없음 | 의도 |
| S3 | CPD 721, 이름 12 | `connection/connection_cl.cpp` `css_*` 7개 | `connection/connection_sr.c` | 서버 쪽 `rmutex`, `stop_talk` | 의도(클라이언트는 연결당 단일 스레드) |
| S3 | CPD 870 | `connection/tcp.c:212` `css_hostname_to_ip` | `executables/master_heartbeat.c:1986` | 오류 코드만 | drift 없음 |
| S3 | CPD 291 | `broker/broker_shm.c:487` `broker_shm_initialize_shm_as` | `broker/shard_shm.c:63` | B는 `#if defined(UNDEFINED)` 안 | 죽은 코드 |
| S4 | CPD 469, 709, 788, 1137, 1398 | `storage/btree_sort.c` `btsort_*` 5개 | `storage/external_sort.c` `sort_*` | `SORT_PUT_STOP` 처리, `orderby_stats` | 의도(2026-09-14 분리, btree put 함수는 STOP을 내지 않음) |
| S4 | CPD 326 | `storage/btree_sort_merge.cpp:222` `btsort_run_merge` | `storage/external_sort.c:1028` | 중복 제거 없음 | 의도(키에 OID가 붙어 동점 없음) |
| S4 | CPD 711 | `external_sort.c:3410` `sort_exphase_merge` | `external_sort.c:2481` `_elim_dup` | 의도 | drift 없음 |
| S4 | CPD 924 | `storage/btree_load.c:6045` `btree_sort_get_next` | `btree_load.c:5688` `_parallel` | 페이지 순회만 | drift 없음 |
| S4 | CPD 85, 142, 352, 463 | `query/query_hash_scan.c` `fhs_*` 4개 | `storage/extendible_hash.c` `ehash_*` | 로그·헤더 페이지 | 의도(fhs는 임시·무로그) |
| S4 | CPD 604, 797 | `query/query_manager.c` `qmgr_free_old_page`, `qmgr_get_old_page` | 각 `_simple_fix`/`_read_only` | latch 모드만 | drift 없음 |
| S4 | CPD 564 | `storage/file_manager.c:3987` `file_sector_map_dealloc` | `:4046` `_temp` | 의도 | drift 없음 |
| S4 | CPD 358 | `storage/heap_file.c:17407` `heap_rv_mvcc_redo_insert` | `:26466` `heap_rv_mvcc_redo_redistribute` | 버퍼 선언 위치 | **D4** |
| S4 | CPD 446 | `storage/es.c:355` `es_copy_file` | `:477` `es_rename_file` | 캐스트 하나 | drift 없음 |
| S4 | CPD 1277 | `storage/page_buffer.c:10818` | `:10732` (aout list 제거) | 의도 | drift 없음 |
| S5 | CPD 116, 이름 3~5 | `bfmt_print` 3개(`compat/cnv.c`, `executables/unload_object_file.c`, `object/object_domain.c`) | 서로 | 표면적 | drift 없음 |
| S5 | 이름 14 | `executables/compactdb.c:535` `process_value` | `storage/compactdb_sr.c:86` | `S_ERROR` 검사 | **D2** |
| S5 | 이름 | `executables/compactdb.c:98` `compactdb` | `executables/compactdb_cl.c:787` | `tables` 해제 | **D8** |
| S5 | 이름 | `loaddb/load_object.c` `put_varinfo`, `put_attributes`, `find_current_attribute` | `object/transform_cl.c` | 데이터 모델 | 의도 |
| S5 | CPD 676, 927, 1016, 1089 | `loaddb/load_sa_loader.cpp:1484` `ldr_find_class_by_query` | `query/execute_statement.c` `do_find_*_by_query` 4개 | `strncpy` 종료 문자, `Au_user_name` | 낮음(아래 기타) |
| S5 | CPD 491 | `query/serial.c:336` | `sp/sp_code.cpp:75` | 오류 경로 동일 | drift 없음 |
| S5 | CPD 1313 | `optimizer/histogram/histogram_cl.cpp:623` | `optimizer/query_graph.c:5324` | 주석만 | drift 없음 |
| S5 | CPD 125 | `base/ddl_log.c:1354` `logddl_get_time_string` | `broker/broker_util.c:421` `ut_time_string` | 캐시 추가 | 의도 |
| S5 | 이름 | `unix_style_path` 3개, `CreateMiniDump` 2개 | 서로 | Windows 전용, 같음 | drift 없음 |
| S6 | CPD 530 | `query/query_aggregate.cpp:2898` `qdata_alloc_agg_hkey` | `query/query_hash_scan.c:208` `qdata_alloc_hscan_key` | NULL 검사 | **D3** |
| S6 | CPD 1379 | `thread/critical_section.c:474` `csect_enter_critical_section` | `:1170` `csect_promote_critical_section` | 시간 초과 오류 코드 | **D7** |
| S6 | CPD 1053 | `critical_section.c:915` `csect_demote_critical_section` | `:696` `_as_reader` | 대기 조건 | 계약상 도달 불가 |
| S6 | CPD 511 | `transaction/log_manager.c` `log_do_postpone` | `transaction/log_recovery.c` `log_recovery_find_first_postpone` | fetch LSA 수정(CBRD-20336) | 해당 없음(단일 스레드 복구 경로) |
| S6 | 이름 | `thread_worker_pool_elastic.hpp` / `_impl.hpp` `get_new_task`, `assign_task` | 서로 | 확장 | 의도 |
| S6 | CPD 1381, 이름 | `connection/connection_worker.cpp` / `coordinator.cpp` `notify`, `run`, `finalize_resources`, `eventfd_*` | 서로 | 의도·동일 | drift 없음 |
| S6 | CPD 1399 | `base/memory_hash.c:2079` `mht_rem` | `:2205` `mht_rem2` | data 비교 추가 | 의도 |
| S6 | CPD 231, 407 | `query/fetch_arith_ops.c` 날짜 함수 2개 | `query/string_opfunc.c` | 연산자 코드 | drift 없음 |
| S6 | CPD 1395 | `query_aggregate.cpp:4272` / `query_analytic.cpp:1078` interpolation | 서로 | 표면적 | drift 없음 |
| S6 | CPD 1159, 1302, 828 | `object/object_primitive.c` char/string 3쌍 | 서로 | 의도 | drift 없음 |
| S6 | CPD 1342 | `query/arithmetic.c:1073` `db_mod_int` | `:922` `db_mod_short` | 오버플로 검사 | 의도(short는 int로 승격) |
| S6 | CPD 704 | `query/string_opfunc.c:15192` `db_to_datetime` | `:14276` `db_to_timestamp` | `H` 형식 | 의도로 보임(2012 b6dfdc5874가 datetime만 대상) |

## 4. 후보 상세

### D1. 서버 측 JDBC의 `?` 개수 계산이 `no_backslash_escapes`를 무시한다 (real, 재현됨)

**책임과 계약.** Java SP와 PL/CSQL이 서버 안에서 SQL을 실행할 때 `cubmethod::query_handler`가 prepare를 처리한다. `query_handler::get_num_markers` (`method/method_query_handler.cpp:119-126`)는 `calculate_num_markers` (`method/method_query_util.cpp:508`)로 SQL 문자열의 `?`를 센다. 이 값은 prepare 응답의 `num_markers` (`method_query_handler.cpp:217`)로 Java에 가고, 실행 때 바인드 값 개수 (`:588`, `:698`)로 쓰인다. 개수를 세는 동안 문자열 리터럴과 주석 안의 `?`는 `consume_tokens`가 건너뛴다.

**차이.** broker 원본은 백슬래시를 escape로 볼지 시스템 파라미터로 정한다.

```c
/* broker/cas_common_execute.c:225 (243도 같은 형태) */
else if (cas_default_no_backslash_escapes == false && *p == '\\')
  {
    p++;
  }
```

C++ 복사본은 그 조건을 주석으로 막았다.

```cpp
/* method/method_query_util.cpp:608 (626도 같은 형태) */
else if (/* cas_default_no_backslash_escapes == false && */ sql[index] == '\\')
  {
    index++;
  }
```

`no_backslash_escapes`의 기본값은 `yes`다(`base/system_parameter.c:2051`). 기본 설정에서 SQL 파서는 `'C:\'`를 완전한 문자열로 읽는다. 그런데 C++ 계산기는 `\'`를 escape된 따옴표로 보고 문자열이 계속된다고 판단한다. 그 결과 뒤따르는 `?`를 놓치거나, 문자열 안의 `?`를 바인드 변수로 센다.

**이력.**

| 커밋 | 날짜 | 내용 |
| --- | --- | --- |
| `9a221564b3` | 2012-07-10 | [CUBRIDSUS-8197] fix the bug get_num_markers() returned unexpected num bind parameter |
| `2bb2031711` | 2012-08-29 | [CUBRIDSUS-7481] Fix host variable counting when cas prepare |
| `d37359b032` | 2022-04-06 | [CBRD-23846] Java SP 서버 측 재설계. C++ 복사본이 조건을 주석 처리한 채 생성됨 |

같은 파일의 `get_backslash_escape_string` (`method_query_util.cpp:44`)은 이미 `PRM_ID_NO_BACKSLASH_ESCAPES`를 읽는다. 조건을 되살릴 수단이 같은 파일에 있었다.

**재현.** 설치본 `11.5.0.2635-30043f4` debug, 새 DB `driftdb`, `csql -u dba`, `;server-output on`.

```sql
CREATE TABLE t (p VARCHAR(20), id INT);
INSERT INTO t VALUES ('C:\', 1);

-- 1) 실제 마커 1개, C++ 계산 0개
CREATE OR REPLACE PROCEDURE p_dyn (x INT) AS n INT; BEGIN
  EXECUTE IMMEDIATE 'SELECT COUNT(*) FROM t WHERE p = ''C:\'' AND id = ?' INTO n USING x;
  DBMS_OUTPUT.put_line ('dyn n=' || n); END;
CALL p_dyn (1);

-- 2) 실제 마커 0개, C++ 계산 1개
CREATE OR REPLACE PROCEDURE p_dyn2 (x INT) AS n INT; BEGIN
  EXECUTE IMMEDIATE 'SELECT COUNT(*) FROM t WHERE p = ''C:\'' OR p = ''?''' INTO n;
  DBMS_OUTPUT.put_line ('dyn2 n=' || n); END;
CALL p_dyn2 (1);
```

관찰한 결과:

| 실행 | 결과 |
| --- | --- |
| `CALL p_dyn (1)` | `ERROR: Stored procedure execute error: (line 1, column 59) Missing or invalid position of the bind variable provided` |
| `CALL p_dyn2 (1)` | `ERROR: Stored procedure execute error: (line 1, column 60) Attempt to execute the query when not all the parameters are binded` |
| 대조: `''C:/''`로 바꾼 같은 두 프로시저 | 둘 다 정상 실행(`dyn_ok n=0`, `dyn2_ok n=0`) |
| 대조: csql에서 직접 `SELECT COUNT(*) FROM t WHERE p = 'C:\' OR p = '?';` | 정상, `1` |
| 정적 SQL(`SELECT ... WHERE p = 'C:\' AND id = x`) | 정상(`n=1`). PL/CSQL 정적 SQL은 이 계산을 거치지 않거나 결과가 맞는 형태다 |

**도달성과 영향.** 기본 설정에서 일반 사용자가 도달한다. Java SP의 `getDefaultConnection()` prepare와 PL/CSQL 동적 SQL이 대상이다. 정상 SQL이 오류로 실패한다. 메모리 손상은 관찰하지 않았다. release 빌드에는 `assert (num_bind == bind_values.size ())` (`method_query_handler.cpp:589`, `:699`)가 없다. 그래서 Java 쪽 검사를 통과하는 조합이 있다면 바인드 개수가 어긋난 채 `set_host_variables`가 실행될 수 있다(추론, 미확인).

**판정.** real. CBRD-28080과 같은 경로(broker → C++ 이식)에서 나온 같은 종류의 drift다.

같은 함수에서 drift는 아니지만 함께 볼 점: `calculate_num_markers`의 `method_query_util.cpp:523`은 `sql[++i] == ':'` 비교에서 `?` 바로 다음 문자를 항상 건너뛴다(하위 에이전트 보고, 코드 확인만 함).

### D2. SA 모드 compactdb가 heap 읽기 오류를 끊어진 참조로 처리한다 (plausible)

- 수정된 쪽: `storage/compactdb_sr.c:111-120`은 `scan_code == S_ERROR`이면 오류를 반환하고 멈춘다. `S_ERROR`가 아닌 실패일 때만 참조를 NULL로 바꾼다.
- 수정 안 된 쪽: `executables/compactdb.c:572`는 `scan_code != S_SUCCESS`이면 `S_ERROR`까지 포함해 `OID_SET_NULL (ref_oid)` 하고 객체를 다시 쓴다.
- 이력: `6a1f5b4a38`(2015-04-09)이 두 복사본 모두에 `S_ERROR` 처리를 넣었다. 다음 날 `4fc3ee1760`(2015-04-10, CUBRIDSUS-16544, "Reverted changes in compactdb.c")이 `compactdb.c`만 되돌렸다. `d0e8ac3839`(2015-08-11)가 `heap_get_visible_version` 호출을 다시 넣을 때 검사는 돌아오지 않았다.
- 도달성: `cubrid compactdb -S`(SA)는 `compactdb.c`로 빌드된다(`sa/CMakeLists.txt:28`). CS 모드는 서버의 `compactdb_sr.c`를 쓴다.
- 영향: I/O 오류, 인터럽트, 메모리 부족 같은 일시적 오류가 나면 살아 있는 객체에 대한 참조가 NULL로 바뀌어 저장된다. 오프라인 관리 도구라 발생 빈도는 낮지만, 결과는 조용한 데이터 손실이다.
- 판정: plausible. 오류 주입 없이 재현하기는 어렵다.

### D3. `qdata_alloc_agg_hkey`가 `pr_make_value` 실패를 검사하지 않는다 (plausible, 메모리 부족 시에만)

- 수정된 쪽 `query/query_hash_scan.c:232-239`:

  ```c
  key->values[i] = pr_make_value ();
  if (key->values[i] == NULL)
    {
      key->free_values = true;
      qdata_free_hscan_key (thread_p, key, i);
      ...
      return NULL;
  ```

- 수정 안 된 쪽 `query/query_aggregate.cpp:2920-2923`은 `key->values[i] = pr_make_value ();`만 있다.
- 이력: 검사는 hash list scan을 추가한 `e9e09485c7`(2020-09-05, CBRD-23665)에서 hscan 복사본과 함께 들어왔다. 집계 복사본은 처음부터 검사가 없었다.
- 도달성: 호출자 `query/query_executor.c:7404`, `:28244`, `:28253`, `:35152`는 `alloc_vals=true`로 부르고 key 자체가 NULL인지만 본다. `values[i]`가 NULL이면 이후 hash GROUP BY 처리에서 역참조된다(하위 에이전트 보고, 예 `:28289`). `pr_make_value`는 malloc 실패에서만 NULL을 돌려준다(`object/object_primitive.c:1824-1831`).
- 같은 파일 `query_aggregate.cpp:3022-3023`(accumulator 값 할당)도 같은 형태로 검사가 없다.
- 판정: plausible. 메모리 부족에서만 발생하고, 결과는 서버 비정상 종료다.

### D4. `heap_rv_mvcc_redo_redistribute`가 블록을 벗어난 버퍼를 쓴다 (plausible, 정의되지 않은 동작)

- 쌍둥이 `heap_rv_mvcc_redo_insert`는 `data_buffer`를 함수 범위에 선언한다(`storage/heap_file.c:17415`).
- `heap_rv_mvcc_redo_redistribute`는 `else` 블록 안에 선언한다(`heap_file.c:26495`). 그 블록 안에서 `recdes.data`를 이 버퍼로 맞추고, 블록이 끝난 뒤 `spage_insert_for_recovery (thread_p, rcv->pgptr, slotid, &recdes)`(`:26534`)가 그 포인터를 읽는다.
- 이력: 두 함수 모두 2016-01-12 줄 폭 변경 커밋 `b9aebe11b9` 이전부터 이 모양이다. 어느 쪽이 먼저 고쳐졌는지는 git으로 판별할 수 없다.
- 영향: 지금 컴파일러는 블록 뒤에 다른 지역 변수를 두지 않아 실제로는 동작할 가능성이 크다. 그래도 C++ 기준으로 수명이 끝난 객체 접근이다. ASan의 `detect_stack_use_after_scope`가 잡을 수 있다. 회복 redo 경로라 잘못되면 페이지 내용이 손상된다.
- 판정: plausible. 수정은 선언을 함수 범위로 올리는 한 줄 이동이다.

### D5. `method_schema_info.cpp`가 broker 수정 7건을 받지 못했다 (real drift, 현재 도달 불가)

`schema_info_handler`는 broker `cas_execute.c`의 `sch_*` 함수를 C++로 옮긴 것이다. 이후 broker 쪽 수정이 C++ 쪽에 들어가지 않았다. 아래 C는 `broker/cas_execute.c`, P는 `method/method_schema_info.cpp`다.

| # | 내용 | P 위치 | C 수정 커밋 |
| --- | --- | --- | --- |
| 1 | `information_schema` 소유 클래스의 이름 한정 `CASE` 누락 | P:213-217, 300-309, 828-842, 915-922 | `8a64a3a10a` 2026-06-02 CBRD-26859 |
| 2 | `sch_attr_info` 정확 일치 분기가 `a.attr_name` 대신 `a.class_name`을 비교 | P:360 | P는 처음부터 잘못됨(`38564b5838`), C:7604는 `a.attr_name` |
| 3 | `sch_queryspec`이 삭제된 열 `db_vclass.unique_name` 조회 | P:406 | `63fa361c7b` 2022-06-03 CBRD-24379 |
| 4 | `sch_trigger`가 `db_get_owner (trigger mop)` 사용, 소유자 제거 이름을 계산하고 쓰지 않음 | P:624, 632, 644 | `496c148d66` 2022-06-05 |
| 5 | `sch_class_priv`가 `class_name_only` 대신 `class_name`으로 패턴 비교 | P:742 | `63fa361c7b` |
| 6 | `sch_attr_priv`가 속성 이름 자리에 클래스 이름 전달 | P:795 | C:8416은 처음부터 `attr_name` |
| 7 | `sch_primary_key` SQL 오타 `AMD`, 모호한 `owner_name` | P:932, 942 | `43b48e20ac` 2022-06-04 |

도달성: 직접 확인했다. `METHOD_CALLBACK_GET_SCHEMA_INFO` 분기는 `// error = get_schema_info (unpacker); assert (false);`다(`method/method_callback.cpp:195-197`). `schema_info_handler`를 만드는 유일한 코드는 주석 블록 안에 있다(`method_callback.cpp:526-541`). Java 쪽(`SUConnection.java`)은 아직 이 요청을 보낼 수 있다고 하위 에이전트가 보고했다. 그러므로 debug 빌드에서는 assert, release에서는 빈 응답이 된다. 이 기능을 다시 켜면 7건이 모두 살아난다.

판정: 코드로는 real drift, 런타임 영향은 지금 없음. 기능을 다시 켜기 전에 고치거나, 쓰지 않을 코드라면 지우는 쪽이 낫다. 같은 이유로 `str_like`의 `::tolower` 차이(`method_query_util.cpp:450` 대 broker `ut_tolower`)도 호출자가 이 죽은 코드뿐이라 영향이 없다.

### D6. 서버 측 JDBC 열 기본값 문자열에 NUL이 하나 더 붙는다 (plausible-low)

- C `broker/cas_execute.c:3861-3867`은 `'` + 값 + `'` 뒤에 종료 문자 하나를 쓴다(C 문자열 종료).
- C++ `method/method_query_util.cpp:762`는 `std::string`에 `push_back ('\0')`을 더한다. 이 NUL은 문자열 길이에 포함되어 `column_info::default_value_string`(`method/method_struct_query.cpp:117`)으로 Java에 간다.
- 영향: 서버 측 JDBC에서 열 메타데이터의 기본값 문자열 끝에 `\u0000`이 붙을 수 있다(추론, Java 쪽 처리 미확인).
- 판정: plausible-low.

### D7. `csect_enter_critical_section`의 시간 제한 대기가 시간 초과를 오류로 본다 (latent)

- `thread/critical_section.c:1290`(promote)은 `ER_CSS_PTHREAD_COND_WAIT`와 `ER_CSS_PTHREAD_COND_TIMEDOUT`을 모두 받는다.
- `critical_section.c:602`(enter)는 `ER_CSS_PTHREAD_COND_WAIT`만 받는다. 시간 초과가 나면 assert 후 `ER_CSS_PTHREAD_COND_WAIT`를 반환한다.
- 이력: 두 형태 모두 2014년 이전 코드다.
- 도달성: 하위 에이전트에 따르면 양수 대기 시간으로 이 함수를 부르는 호출자가 없다. 지금은 영향이 없고, 시간 제한 진입을 쓰기 시작하면 드러난다.

### D8. SA 모드 compactdb가 `tables` 배열을 해제하지 않는다 (real, 사소함)

`executables/compactdb.c:130`에서 `malloc`한 `tables`를 해제하지 않는다. CS 복사본은 `executables/compactdb_cl.c:924`에서 해제한다. 프로세스 종료 직전의 한 번뿐인 누수다.

### K. CBRD-28080 (보정용, 기존 결함)

`method/method_query_util.cpp:463`이 `std::string (val_str)`을 `val_str == NULL`일 수 있는 상태로 만든다. C 원본 `broker/cas_execute.c:10201`은 NULL을 반환하고 호출자 `serialize_collection_as_string`(`:10251`, `:10285`)이 검사한다. C++ 복사본은 생성(`d37359b032`, 2022-04-06) 때부터 검사가 없었다. 이번 방법이 이 결함을 다시 찾는지 확인하려고 넣었다. CPD는 놓쳤고 이름 쌍은 찾았다.

### 기타 관찰 (drift 아님 또는 근거 약함)

- `execute_statement.c`의 `do_find_serial_by_query`, `do_find_trigger_by_query`는 `strncpy (buf, ..., buf_size)` 후 종료 문자를 보장하지 않고, `do_find_stored_procedure_by_query`는 `strcpy`(`:21548`)를 쓴다. 길이 검사는 assert뿐이다. `ldr_find_class_by_query`는 `b2bdbcef70`(2025-07-09)에서 `buf_size - 1`과 종료 문자로 고쳐졌다. 카탈로그 이름 길이 제한 때문에 실제로 넘칠 가능성은 낮다고 보고 후보에서 뺐다.
- `ehash_dump`(`storage/extendible_hash.c:4598`)는 일부 조기 반환(`:4633`, `:4760`, `:4794`)에서 `dir_root_page_p`를 unfix하지 않는다. 호출자가 없다.
- `btsort_read_area`(`storage/btree_sort.c:4708`)는 `sort_read_area`가 `4a9d047564`에서 바꾼 `pgbuf_copy_temp_page_to_area_and_discard`를 받지 않았다. 성능 차이이고 정확성 문제는 아니다.
- 양쪽에 똑같이 있는 약점(drift가 아님): CAS와 CGW 모두 클라이언트가 보낸 본문 크기로 상한 없이 `MALLOC`(`broker/cas.c:1056`, `broker/cas_cgw.c:567`), 클라이언트·서버 모두 `css_make_conn (datagram_fd)`의 NULL 반환을 처리하지 않음(`connection/connection_cl.cpp:1076`, `connection/connection_sr.c:1176`).

## 5. 오탐과 의도된 차이

다음 묶음은 CPD 점수가 높았지만 차이가 의도된 것이었다. 같은 방법을 다시 쓸 때 먼저 걸러도 된다.

- CAS 대 CGW(`cas*.c` 대 `cas_cgw*.c`): CGW에는 CUBRID 엔진·세션·shard가 없다.
- 클라이언트 대 서버 연결(`connection_cl.cpp` 대 `connection_sr.c`): 서버만 다중 스레드라 `rmutex`가 있다.
- `btree_sort.c` 대 `external_sort.c`: 2026-09-14에 분리된 복사본이고, 차이는 B-tree 정렬에 없는 기능(STOP, ORDER BY 통계)이다.
- `fhs_*` 대 `ehash_*`: hash scan은 임시·무로그 자료구조다.
- `xts_save_*`/`stx_build_*`/`pt_print_*` 등 같은 틀 함수: 필드 이름만 다른 직렬화 코드라 drift 판정이 의미가 없다. 무시 모드 CPD의 상위를 많이 차지한다.

## 6. 한계

- 검토한 쌍은 약 75개다. CPD 필터 결과 1,019쌍과 이름 쌍 120쌍 중 순위 상위만 봤다. 같은 파일 안의 쌍은 대부분 보지 않았다.
- 분류는 하위 에이전트가 먼저 했다. 후보로 올라온 것은 모두 직접 다시 확인했지만, "drift 없음"으로 판정된 쌍은 일부만 다시 확인했다(S3의 CGW 분기, S4의 `SORT_PUT_STOP` 근거, S6의 `db_mod_short`).
- 실행으로 확인한 것은 D1뿐이다. D2~D8은 소스와 git 이력만으로 판단했다.
- 이름 쌍은 이름을 바꾼 복사본을 놓친다. CPD는 다시 쓴 복사본을 놓친다. 둘 다 놓치는 복사본이 있을 수 있다.
- `git blame` 날짜는 대량 포맷 변경 커밋(예: 2016-01-12 `b9aebe11b9`, 2026년의 여러 포맷 정리) 때문에 실제 로직 변경보다 늦게 나올 수 있다. 순위에만 썼고 판정에는 `git log -L`/`-S`를 썼다.

## 7. 다음 단계 후보

이슈 등록 여부는 사용자가 정한다.

1. D1: JIRA 등록 후보. 위 재현 SQL을 그대로 쓸 수 있다. 수정은 두 줄의 조건을 `prm_get_bool_value (PRM_ID_NO_BACKSLASH_ESCAPES) == false`로 되살리는 것이다. 같은 함수의 `cas_default_ansi_quotes` 주석 처리(`method_query_util.cpp:563`)도 함께 볼 만하다(하위 에이전트는 영향 없다고 판단).
2. D2, D3, D4: 각각 한두 줄 수정이다. 한 이슈로 묶을 수 있다.
3. D5: `schema_info_handler`를 지울지, 기능을 되살리며 고칠지 결정이 필요하다.
4. 방법: `tools/name_twins.py`를 정기 점검에 추가하고, broker ↔ `method/` 쌍은 broker 쪽 커밋이 들어올 때마다 비교하는 규칙을 둘 수 있다.
