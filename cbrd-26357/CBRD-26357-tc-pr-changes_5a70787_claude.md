# CBRD-26357: PR 7990 testcase PR 변경 내역과 근거

작성일: 2026-10-27 (Asia/Seoul). 작성: `claude`.

## Purpose

- **질문:** 엔진 PR [CUBRID/cubrid#7990](https://github.com/CUBRID/cubrid/pull/7990)(OOS, `feature/oos-merge` → `develop`)과 함께 머지할 testcase PR 두 개는 무엇을 왜 바꾸는가?
- **독자:** 두 testcase PR의 리뷰어와 머지 담당자.
- **범위:** 각 PR의 net diff(`develop...tc/pr-7990`)에 있는 모든 파일. 커밋 이력은 이유를 설명할 때만 사용합니다.
- **결론:** 모든 변경은 OOS 엔진에서 정해진 동작을 기대값에 반영하거나, 원래부터 불안정하던 검사를 고정하거나, 알려진 CDC 실패를 gha-ci에서만 격리합니다. 엔진 동작을 숨기는 변경은 없습니다. 단, 머지 순서와 CDC 격리는 develop 전체에 영향을 주므로 아래 [Remarks](#remarks)를 확인해야 합니다.
- AS-IS: develop의 testcase 기대값으로는 OOS 엔진에서 SQL 2개, medium 1개, shell 15개 테스트가 실패하고, CDC 테스트 2개는 OOS 엔진에서 실패합니다.
- TO-BE: OOS 엔진 + 이 testcase head로 gha-ci의 build, `test_sql`, `test_medium`, `test_shell`이 모두 통과합니다.

### 리비전

| 항목 | 값 |
| --- | --- |
| 엔진 PR head | `5a70787feea9e0488222af7e3a0249cc431562ca` |
| public PR | [CUBRID/cubrid-testcases#3551](https://github.com/CUBRID/cubrid-testcases/pull/3551), `tc/pr-7990` = `70db22a1c99dbbaa27fa1438c8967effdfcad551`, base `develop` = `2c828d25ddf282b9696dde7258ec80c220e09e9b` (merge base와 같음) |
| private PR | [CUBRID/cubrid-testcases-private-ex#4210](https://github.com/CUBRID/cubrid-testcases-private-ex/pull/4210), `tc/pr-7990` = `75a02020e19be4bfc64e47f7c7a3d5c2b02d7676`, base `develop` = `88bec5cd8881fe496a2a10c8754105c0c25ef8b4` (merge base와 같음) |
| net diff | public 5개 파일 +21/-3 (테스트 3개), private 26개 파일 +134/-94 (테스트 17개 + `_25_unstable/readme.txt`) |
| 확인 CI | [gha-ci run 40349442612](https://github.com/CUBRID/cubrid/actions/runs/40349442612). shard 정보에 기록된 testcase 리비전이 위 두 head와 같습니다. |

두 `tc/pr-7990`은 2026-10-27에 당시 develop을 머지했습니다. 그래서 PR diff에는 develop 쪽 변경이 섞이지 않습니다.

## Implementation

OOS(Out-of-row Overflow Storage)는 큰 가변 길이 값을 행 밖의 테이블별 OOS 파일에 저장하고, 행에는 16바이트 위치 정보(stub)만 남깁니다. 이 때문에 testcase에서 다음 차이가 보입니다.

- 큰 행이 overflow 파일(`MULTIPAGE_OBJECT_HEAP`) 대신 OOS 파일(`OUT_OF_LINE_OVERFLOW_STORAGE`)을 씁니다.
- 큰 값이 힙 페이지를 늘리지 않으므로 힙 페이지 수가 줄어듭니다.
- 새 로그 종류(`RVOOS_INSERT`, `RVOOS_DELETE`)와 새 오류 코드(`ER_HEAP_OOS_*`, 엔진 `5a70787fe`의 `src/base/error_code.h` L1791-1801)가 생깁니다.

### 1. public PR #3551 (SQL·medium)

#### 1.1 `sql/_13_issues/_14_1h/bug_bts_10516`, `sql/_15_fbo/_02_qa_test/fbo_ddl02`

- **파일:** 각 테스트의 `cases/*.sql`, `answers/*.answer`.
- **수정 내용:**
  - 테이블 `allcolumn_t4`(BLOB/CLOB 컬럼 1000개)에 모든 컬럼을 채운 행을 넣는 INSERT의 결과로 answer에 `Error:-1388` 블록을 추가합니다.
  - 그 뒤에 `b001`, `c001`만 채운 행을 넣는 INSERT와 설명 주석 2줄을 추가합니다.
  - 파일 끝 줄바꿈을 추가합니다. 동작은 바뀌지 않습니다.
- **이유:** OOS 엔진에서는 값을 행 밖으로 보내도 행에 남는 stub 1000개가 최대 레코드 크기를 넘습니다. develop은 이 행을 overflow 레코드로 저장하지만, OOS 엔진은 `ER_HEAP_OOS_OVERPASS_MAXOBJ_SIZE`(-1388)로 거부합니다. 원래 행이 없으면 뒤의 `insert ... select`, SELECT, UPDATE, DELETE가 빈 테이블에서 실행되므로, 일부 컬럼만 채운 행을 넣어 뒤의 기대값을 그대로 검증합니다.
- **근거:**
  - 이전 PR [cubrid-testcases#3159](https://github.com/CUBRID/cubrid-testcases/pull/3159) 본문 (`feat/oos` 시절, 같은 변경과 이유).
  - `09c39006e` [CBRD-26517] Port OOS testcase baseline to feature/oos-merge: #3159 최종 변경을 이 브랜치로 옮겼습니다.
  - 오류 번호 갱신: `8be3e498c`(-1383), `6add917dd`(-1384), 머지 `c434a1a10`(-1387), `f9da38c7b`(-1388). 처음 값은 -1382였습니다. develop에 오류 코드가 추가될 때마다 번호가 밀렸습니다.

#### 1.2 `medium/_02_xtests/7105`

- **파일:** `cases/7105.sql`. answer는 바뀌지 않습니다.
- **수정 내용:** `db_class`에서 `%eeeoo%` 클래스를 조회하는 SELECT에 `order by class_name`을 추가합니다.
- **이유:** ORDER BY가 없는 조회는 행 순서를 보장하지 않습니다. 기존 answer는 `eeeoo1`, `eeeoo2`, `subeeeoo` 순서를 기대합니다. OOS 엔진 head `2c792b423`의 CI에서 이 테스트가 실패했고, 실패 분류는 "OOS 레코드 형식 변경으로 인한 기대 출력 차이"였습니다. 정렬을 명시하면 같은 answer를 엔진과 무관하게 검증할 수 있습니다.
- **근거:** `8be3e498c` [CBRD-26939] Update OOS merge regression expectations; [cbrd-26939/ci-fix/pr-7990/index.md](../cbrd-26939/ci-fix/pr-7990/index.md)의 실패 목록.
- **한계:** 그 실패의 실제 출력은 보존되어 있지 않습니다. "행 순서가 달라졌다"는 것은 수정 내용과 answer로부터의 추론입니다.

### 2. private PR #4210 (shell)

private 변경 중 16개 파일은 `b5a4d3490` [CBRD-26517]이 이전 PR [cubrid-testcases-private-ex#3782](https://github.com/CUBRID/cubrid-testcases-private-ex/pull/3782)(`feat/oos` 시절, 승인 후 닫힘)의 최종 head `c71941cf8`에서 그대로 가져왔습니다. #3782 본문에 파일별 이유가 있습니다. 나머지는 이 PR 기간에 추가된 변경입니다.

#### 2.1 `_06_issues/_12_2h/bug_bts_9836`, `_06_issues/_14_2h/bug_bts_14120`

- **파일:** `bug_bts_9836/cases/log2.answer`(2줄), `log3.answer`(1줄), `bug_bts_14120/cases/bug_bts_14120_1.answer`(1줄).
- **수정 내용:** `call_stack_dump_activation_list=` 출력에서 `-50` 뒤, `-51` 앞에 `-1387,-1389,-1390`을 넣습니다.
- **이유:** OOS 엔진은 `ER_HEAP_OOS_BAD_INLINE_HEADER`(-1387), `ER_HEAP_OOS_CORRUPTED_RECORD`(-1389), `ER_HEAP_OOS_INVALID_ARGUMENT`(-1390)를 `src/base/system_parameter.c`의 기본 `call_stack_dump_error_codes[]`에서 `ER_HEAP_BAD_RELOCATION_RECORD`(-50) 바로 뒤에 둡니다(엔진 `2c792b423`, [CBRD-26835]). 그래서 `paramdump`의 기본값 출력이 바뀝니다. develop의 `error_code.h`에는 이 오류 코드가 없습니다.
- **번호 이력:** `-1378,-1380,-1381`(`876639d8d`) → `-1380,-1382,-1383`(`212149852`) → `-1381,-1383,-1384`(`06fb3262e`, 여기까지 #3782) → `-1382,-1384,-1385`(`843aa7d88`) → `-1383,-1385,-1386`(`cebbd0884`) → `-1386,-1388,-1389`(머지 `28ffb7365`) → `-1387,-1389,-1390`(`aa1db95f8`).

#### 2.2 `_06_issues/_14_2h/bug_bts_15529`

- **파일:** `cases/test.answer`, `cases/testdebug.answer`. 파일마다 2줄입니다.
- **수정 내용:** `call_stack_dump_activation_list` 기본값을 읽는 두 출력(처음 값, 기본값으로 되돌린 뒤 값)에 같은 번호 3개를 넣습니다. 명시 값 `4207500`을 확인하는 부분은 그대로입니다.
- **이유:** 2.1과 같은 OOS 기본값입니다. develop이 2026-10-16(`7842a35f4`, CUBRIDQA-1136)에 이 테스트를 `_25_unstable`에서 원래 위치로 되돌렸고, 2026-10-21 develop 머지로 이 브랜치에서도 실행되기 시작했습니다. 엔진 `1a8c705`의 CI에서 이 두 줄만 다르게 나왔습니다. 엔진 수정이 필요한 문제가 아니라 의도된 기본값 차이로 판정했습니다.
- **근거:** `73e2b2f44`, `aa1db95f8`; [ci_analysis_report_1a8c705_codex.md](ci_analysis_report_1a8c705_codex.md); [non_cdc_followup_1a8c705_codex.md](non_cdc_followup_1a8c705_codex.md). 2026-10-27 develop 머지(`75a02020e`)는 같은 파일의 다른 부분(develop의 optimizer_reserve_02 출력 삭제)을 자동 병합했습니다. PR diff에는 두 줄만 남습니다.

#### 2.3 `_06_issues/_26_1h/cbrd_26527`

- **파일:** `cases/cbrd_26527.sh` (+19/-15).
- **수정 내용:** Case 4가 DROP 후 diagdb에서 사라져야 하는 보조 파일의 HFID를 `MULTIPAGE_OBJECT_HEAP ... Overflow for HFID` 줄 대신 `OUT_OF_LINE_OVERFLOW_STORAGE ... (dba.tbl), OOS for HFID` 줄에서 가져옵니다. 힙 page id로 찾는 단계는 없어졌습니다. 주석과 OK/NOK 메시지의 "overflow"를 "OOS file"로 바꿉니다.
- **이유:** OOS에서는 `char(2048)` 값 10행이 overflow 파일을 만들지 않고 테이블의 OOS 파일에 저장됩니다. diagdb는 OOS 파일의 소유 클래스를 보여 줍니다(CBRD-27038). "DROP하면 보조 파일과 힙이 모두 postpone 정리된다"는 원래 검증은 그대로입니다. 엔진 `5a70787fe`에서도 OOS 파일은 `file_postpone_destroy`로 정리됩니다(`src/storage/heap_file.c` `xheap_destroy`, `src/storage/oos_file.cpp` `oos_remove_file`).
- **근거:** `c3a318e6f`(#3782), #3782 본문 "그룹 C", [feat-oos/ci-142161-tde-shell-failures-analysis_e20543df8_claude.md](../feat-oos/ci-142161-tde-shell-failures-analysis_e20543df8_claude.md).
- **참고:** develop에서 온 L37-40, L50 주석은 아직 "overflow heap"이라고 씁니다. 동작에는 영향이 없습니다.

#### 2.4 `_35_cherry/issue_21654_server_side_loaddb/bigPageSize`

- **파일:** `cases/bigPageSize.sh` L24.
- **수정 내용:** 비교 SELECT의 `order by 1 desc limit 1`을 `order by 1 desc, id limit 1`로 바꿉니다. `id`는 `AUTO_INCREMENT` 컬럼입니다.
- **이유:** 256개 행이 모두 같은 `col1` 값을 가지므로(시작 행 1개를 8번 복제) `limit 1`이 고르는 행이 정해져 있지 않았습니다. OOS에서 db2(4K 페이지, `loaddb -C`)의 행이 `REC_BIGONE` 대신 OOS 레코드로 저장되면서 물리 순서가 바뀌었고, 두 DB가 서로 다른 행을 골라 CLOB/BLOB locator 두 줄만 달랐습니다. loaddb는 locator를 정확히 보존했으므로 엔진 버그가 아닙니다. 정렬 키를 추가해도 locator 보존 검증은 그대로입니다.
- **근거:** [5b5ff58/failed_tcs/bigpagesize-report.md](5b5ff58/failed_tcs/bigpagesize-report.md), `212149852`, #3782 본문 "그룹 D".

#### 2.5 `_35_cherry/issue_21654_server_side_loaddb/partition_tbls`

- **파일:** `cases/partition_tbls.sh` (+55/-2), `cases/bug_bts_11093.answer` (-19), `cases/bug_bts_11093.answer_WIN` (-19).
- **수정 내용:**
  - test2는 계속 범위 밖 값 `100`(파티션 `p0`은 `i < 10`)을 추가합니다. 이제 올바른 object 파일을 따로 저장하고, 잘못된 입력의 loaddb 출력은 `$res` 대신 별도 파일로 보냅니다.
  - loaddb가 0이 아닌 값으로 끝나고 `Appropriate partition does not exist`를 출력하는지 확인합니다.
  - `t`와 `t__p__p0`가 모두 0행인지(실패한 묶음이 rollback되었는지) 확인합니다.
  - 같은 DB에 올바른 파일을 다시 넣어 성공하고, 각 테이블에 `i = 1`인 행이 정확히 1개인지 확인합니다.
  - answer 두 파일에서는 test2의 "2 instances committed / Total 2 object(s) inserted" 블록만 지웁니다. test1, test3는 그대로입니다.
- **이유:** 기존 answer는 `loaddb -C`가 파티션 범위를 검사하지 않아 `100`이 `p0`에 들어가는 버그를 정상 출력으로 기록하고 있었습니다. OOS 브랜치에 들어간 #7927(CBRD-27089, 엔진 `3252fcffc`)이 loader에 실제 pruning 종류를 넘기면서, 엔진은 이 행을 `ER_PARTITION_NOT_EXIST`로 거부합니다. 엔진 `5a65b28`의 CI(run 39930102206)에서 test2 비교만 실패했습니다. 수정 후 이 테스트만 다시 실행한 run 40283949823에서 통과했습니다.
- **근거:** `7bc77c666`. 같은 스크립트 수정을 develop `ba88e4700`에서 먼저 설계·실행한 기록: [partition-loader/develop-partition-tc-ba88e470_codex.md](../partition-loader/develop-partition-tc-ba88e470_codex.md). develop 쪽 엔진 수정: [cbrd-27441/CBRD-27441-validate-partition-range-server-loaddb_109f16a_claude.md](../cbrd-27441/CBRD-27441-validate-partition-range-server-loaddb_109f16a_claude.md), 엔진 PR [#8275](https://github.com/CUBRID/cubrid/pull/8275)(draft).

#### 2.6 `_36_damson/cbrd_23608_tde/` TDE 테스트 9개

TDE(투명 데이터 암호화) 테스트는 서버 로그의 페이지별 암호화 설정 줄을 셉니다. OOS 파일 페이지가 생기고 힙 페이지가 덜 늘어나므로 줄 수가 바뀝니다. 9개 모두 `e7e87aa43`(#3782)에서 고쳤고, `file_enc_03`, `file_enc_05`는 develop 머지에서 OOS 줄이 빠진 것을 `eb715e21d`, `212149852`에서 되살렸습니다. 근거: #3782 본문 "그룹 A", [feat-oos/ci-142161-tde-shell-failures-analysis_e20543df8_claude.md](../feat-oos/ci-142161-tde-shell-failures-analysis_e20543df8_claude.md).

| 테스트 | 파일 | 수정 내용 | 이유 |
| --- | --- | --- | --- |
| `file_enc_01` | `file_enc_01.sh`, `result.answer` | OOS 설명 주석 6줄 추가. 기준 줄 `pages = 9`를 `pages = 5`로. answer에서 NONE 4줄, AES 4줄 삭제 | 4K 페이지에서 `char(2000)` 값이 OOS 파일로 가서 힙이 처음 5페이지에 머뭅니다. 기준 줄을 그대로 두면 `result.log`가 비게 됩니다. |
| `file_enc_02` | `result.answer` | `file_alloc` AES + `pgbuf_set_tde_algorithm` AES 1쌍 추가 | OOS 파일 페이지 할당도 AES를 설정합니다(CBRD-26830). |
| `file_enc_03` | `result.answer` | AES 설정 1줄, AES 페이지 해제 1줄 추가 | 값이 OOS 페이지에 기록되고, DROP 때 OOS 파일 페이지도 해제됩니다. |
| `file_enc_04` | `result.answer` | AES 적용 1줄 + AES 설정 2줄 추가. 마지막 NONE 블록 9줄 → 5줄 | OOS 파일은 첫 큰 값에서 AES로 생깁니다. 힙이 늘지 않아 마지막 NONE 적용이 5페이지입니다. |
| `file_enc_05` | `result.answer` | AES 페이지 해제 2줄, NONE 설정 2줄 추가 (11 + 11줄) | DROP과 재시작 복구 때 OOS 파일 페이지도 해제됩니다. "해제 수 = NONE 수"는 유지됩니다. |
| `file_enc_07` | `result.answer` | AES 설정 2줄 삭제 (6줄) | 힙 페이지가 늘지 않아 일반 처리와 복구가 각각 3페이지만 설정합니다. |
| `log_enc_04` | `log_enc_04.sh`, `rcvindex.data` | 아래 설명 | 아래 설명 |
| `tbl_enc_08` | `result.answer` L7-8 | `MULTIPAGE_OBJECT_HEAP` / `Overflow for HFID`를 `OUT_OF_LINE_OVERFLOW_STORAGE` / `CLASS_OID: ... (dba.ttt), OOS for HFID`로. `tde_algorithm: AES`는 그대로 | 약 20KB `varchar` 행이 overflow 파일 대신 OOS 파일을 만들고, 그 파일도 AES로 암호화됩니다. diagdb는 OOS 파일의 클래스를 보여 줍니다(CBRD-27038). |
| `tbl_enc_14` | `result.answer` L8-9 | `tbl_enc_08`과 같은 교체. `BTREE_OVERFLOW_KEY` 줄은 그대로 | `tbl_enc_08`과 같습니다. B-tree overflow key 파일은 OOS와 무관합니다. |

`log_enc_04` 상세:

- **수정 내용:**
  1. 암호화 테이블 `t_fix (a bit(160000))`를 추가합니다.
  2. `RVHF_INSERT_NEWHOME`을 만들기 위해 3800바이트 행 4개(a = 7..10)를 넣고 a=5 행을 3800바이트로 키웁니다. 이전에는 10000바이트 UPDATE를 썼습니다.
  3. `t_big` 주석을 `RVOOS_INSERT`/`RVOOS_DELETE`로 고칩니다.
  4. `t_fix`의 INSERT/UPDATE를 SA 모드(`RVOVF_NEWPAGE_INSERT`, `RVOVF_PAGE_UPDATE`)와 CS 모드(`RVHF_MVCC_UPDATE_OVERFLOW`, `t_big`에서 옮김)에 추가합니다.
  5. 확인 루프가 첫 누락에서 멈추지 않고 빠진 로그 종류를 모두 보고합니다.
  6. `rcvindex.data`에 `RVOOS_INSERT`, `RVOOS_DELETE`를 추가합니다.
- **이유:** OOS에서는 DB_PAGESIZE/4보다 큰 레코드의 큰 가변 길이 값이 행 밖으로 갑니다. 그래서 10000바이트 UPDATE가 레코드를 옮기지 않아 `RVHF_INSERT_NEWHOME`이 없고, 20000바이트 `varchar`가 overflow 레코드를 만들지 않아 `RVOVF_*`, `RVHF_MVCC_UPDATE_OVERFLOW`도 없습니다. 고정 길이 BIT 값은 행 밖으로 가지 않으므로 overflow 경로를 계속 만듭니다. OOS 페이지도 TDE로 암호화되는 새 페이지이므로 OOS 로그를 기대 목록에 넣습니다.
- **근거:** `01af62db7`(#3782).

#### 2.7 CDC `cbrd_27064`, `cbrd_27075` 격리

- **파일:** `_37_elderberry/cbrd_23842_cdc/bug/cbrd_27064/cases/{cbrd_27064.sh,cdc_extract.c}`, `.../cbrd_27075/cases/{cbrd_27075.sh,cdc_extract.c}`를 `_25_unstable/` 아래 같은 경로로 옮깁니다(내용 동일, rename 100%). `_25_unstable/readme.txt`에 7줄을 추가합니다.
- **readme 내용:** 격리 날짜(2026-10-26), 측정한 실행(엔진 `5a65b2807`, testcase `fea33d9fe`, CI run 39930102206), 정책(daily VM 회귀에서는 계속 실행, CDC/OOS 호환 수정 후 5회 연속 통과하면 원래 경로로 복원), 측정한 실패(27064: overflow delete/update 중 CDC 추출이 `rc=-10`, delete 81/700, update 0/2400 이벤트 수신. 27075: 8K·16K 페이지에서 추출 오류, `CONFIGS_OK=1/3`, 보고된 손상 0).
- **동작:** `_25_unstable`은 gha-ci `test_shell`에서 제외되고 daily VM 회귀에서는 실행됩니다(`readme.txt` L1-2).
- **이유:** 두 테스트는 overflow 레코드를 CDC로 추출하는 회귀 테스트입니다. OOS 엔진 head에서는 실패하고 merge base에서는 통과합니다. CDC·flashback의 OOS 이력 지원(CBRD-26939)은 [ADR-0005](https://github.com/vimkim/cubrid-oos-context/blob/75f8b58674ac901d478ba60f9b2cc2fff11f66f6/docs/adr/0005-defer-oos-history-from-the-11-5-merge.md)에 따라 이번 엔진 PR에서 뺐습니다. 2026-10-26 결정으로 이 두 테스트만 gha-ci에서 격리했습니다(`dd12b36a2`, CI 대상 3486 → 3484).
- **한계:** 현재 실패(`rc=-10`)의 정확한 원인은 분석하지 않았습니다.

### 3. 이력에는 있지만 net diff에는 없는 변경

| 커밋 | 내용 | 남지 않은 이유 |
| --- | --- | --- |
| `046d0e2f8` | `cbrd_24916_check_index_ovfps` answer 5개(페이지 수) | develop 머지 `fea33d9fe`에서 develop의 새 answer(`c79be6f9c`, CBRD-27247)를 택했고, OOS 엔진에서도 통과했습니다. |
| `843aa7d88`의 `cbrd_25080` 부분 | selectivity 마스크 answer | 결과가 develop의 같은 파일과 같습니다. |
| `fc12d46ca`, `83f7fa821` | sync bot의 develop 변경(CBRD-26459) | 이미 develop에 있습니다. |

## Remarks

### Test Plan

- [gha-ci run 40349442612](https://github.com/CUBRID/cubrid/actions/runs/40349442612), 엔진 `5a70787fe`:
  - build release/debug: SUCCESS.
  - `test_medium` (public `70db22a1c`): 975/975 PASS.
  - `test_shell` (private `75a02020e`, shard 50개 모두 같은 리비전): 3,460 PASS / 0 FAIL / 30 SKIP, 실행 누락 0.
  - `test_sql` (public `70db22a1c`): GitHub 상태 SUCCESS, 실패 목록 0건. 수집 도구가 shard 01의 결과와 JUnit 개수 불일치를 보고해서 SQL 개수는 검증된 요약으로 확정하지 못했습니다. 같은 증상이 merge base run 39979262220에서도 보고되었고, 원인은 아직 확인하지 않았습니다.

### 머지할 때 확인할 것

- **머지 순서:** 엔진 PR의 `Check TC PRs` 검사는 두 testcase PR이 testcase `develop`에 먼저 들어가야 통과합니다. 그 사이 develop 엔진에는 OOS가 없으므로 다음이 develop CI와 daily 회귀에서 실패할 것으로 예상합니다(실행해 확인하지는 않았습니다): `bug_bts_10516`, `fbo_ddl02`, `bug_bts_9836`, `bug_bts_14120`, `bug_bts_15529`, `cbrd_26527` Case 4, TDE 테스트 9개, `partition_tbls`. `7105`, `bigPageSize`, CDC 이동은 엔진과 무관합니다. 엔진 PR 직전에 testcase PR을 머지하는 것이 좋습니다.
- **CDC 격리의 영향:** private PR이 머지되면 `cbrd_27064`, `cbrd_27075`는 모든 엔진 PR의 gha-ci에서 빠집니다. 두 테스트는 develop 엔진에서는 통과합니다. 복원 전까지는 daily VM 회귀에서만 실행됩니다.
- **정책 문서와의 차이:** ADR-0005와 `OOS-CONTEXT.md`는 아직 "두 테스트를 활성화한 채 실패를 보이게 두라"고 씁니다. 2026-10-26 격리 결정 뒤에 갱신되지 않았습니다.
- **오류 번호:** public의 `-1388`과 private의 `-1387,-1389,-1390`은 `error_code.h` 순서로 정해집니다. 엔진 PR 머지 전에 develop에 오류 코드가 추가되면 public answer 2개, private answer 5개(8줄)를 다시 맞춰야 합니다.
- **승인 시점:** private PR의 승인(2026-09-30 `c4b9d482f`, 2026-10-26 06:38Z `fea33d9fe`) 뒤에 `partition_tbls`(`7bc77c666`)와 CDC 격리(`dd12b36a2`)가 추가되었습니다.
- **develop 쪽 중복 수정:** 엔진 PR #8275(CBRD-27441)가 같은 loader 버그를 develop에서 고칩니다. 그 짝 private TC PR #4570에는 현재 파일 변경이 없습니다. 두 엔진 PR 중 먼저 들어가는 쪽이 `partition_tbls` 수정을 필요로 합니다.
- **PR 기록:** 2026-10-26 엔진 PR을 닫았다 다시 열 때 sync bot이 #4210을 닫고 "closed without merge" 댓글을 남겼습니다. 10분 뒤 다시 열었으므로 PR은 정상입니다.

### 한계

- `7105`의 "행 순서 차이"와 머지 순서 기간의 develop 실패는 추론입니다.
- CDC 두 테스트의 현재 실패 원인은 분석하지 않았습니다.
- 커밋 `73e2b2f44`, `aa1db95f8`, `7bc77c666`, `dd12b36a2`, `843aa7d88`, `cebbd0884`은 메시지에 제목만 있습니다. 이 문서가 그 이유를 대신 기록합니다.
