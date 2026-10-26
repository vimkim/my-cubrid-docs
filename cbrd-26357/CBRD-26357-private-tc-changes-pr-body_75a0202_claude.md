https://jira.cubrid.org/browse/CBRD-26357

## Purpose

- 엔진 PR [CUBRID/cubrid#7990](https://github.com/CUBRID/cubrid/pull/7990)(`feature/oos-merge` → `develop`)과 함께 머지해야 하는 shell 테스트 변경입니다.
- OOS(Out-of-row Overflow Storage)는 큰 가변 길이 값을 행 밖의 OOS 파일에 저장하고, 행에는 값의 위치 정보(stub)만 남기는 기능입니다. 그래서 큰 행이 overflow 파일 대신 OOS 파일을 쓰고, 힙 페이지 수, 로그 종류, 진단 출력이 달라집니다.
- AS-IS: develop의 기대값으로는 OOS 엔진에서 아래 테스트가 실패합니다.
- TO-BE: OOS 엔진에서 정해진 동작을 기대값에 반영하고, 각 테스트의 원래 검증 의도는 유지합니다.

## Implementation

변경된 테스트는 17개(파일 26개)입니다. 경로의 `shell/` 접두어와 `cases/`는 생략했습니다.

| 테스트 | 수정 내용 | 수정 이유 |
|---|---|---|
| `_06_issues/_12_2h/bug_bts_9836` (`log2.answer`, `log3.answer`), `_06_issues/_14_2h/bug_bts_14120` (`bug_bts_14120_1.answer`) | `call_stack_dump_activation_list` 기본값 출력에서 `-50` 뒤에 `-1387,-1389,-1390`을 추가합니다. | OOS 엔진은 OOS 레코드 손상 오류 3개(`ER_HEAP_OOS_BAD_INLINE_HEADER`, `ER_HEAP_OOS_CORRUPTED_RECORD`, `ER_HEAP_OOS_INVALID_ARGUMENT`)를 call stack을 남기는 기본 오류 목록에 넣습니다. |
| `_06_issues/_14_2h/bug_bts_15529` (`test.answer`, `testdebug.answer`) | 기본값을 읽는 두 줄에 같은 번호 3개를 추가합니다. | 위와 같습니다. develop이 2026-10-16에 이 테스트를 `_25_unstable`에서 다시 꺼내면서 이번 PR에 들어왔습니다. |
| `_06_issues/_26_1h/cbrd_26527` (`cbrd_26527.sh`) | Case 4에서 DROP 후 없어져야 하는 보조 파일을 overflow 파일(`MULTIPAGE_OBJECT_HEAP`) 대신 OOS 파일(`OUT_OF_LINE_OVERFLOW_STORAGE ... OOS for HFID`)에서 찾습니다. 주석과 메시지도 고칩니다. | OOS에서는 `char(2048)` 값이 overflow 파일 대신 테이블의 OOS 파일에 저장됩니다. "DROP하면 보조 파일도 정리된다"는 검증 내용은 그대로입니다. |
| `_35_cherry/issue_21654_server_side_loaddb/bigPageSize` (`bigPageSize.sh`) | 비교 쿼리의 정렬을 `order by 1 desc, id`로 바꿉니다. | 256개 행의 정렬 값이 모두 같아서 `limit 1`이 아무 행이나 고를 수 있었습니다. OOS에서 행의 물리 순서가 바뀌자 두 DB가 다른 행을 골랐습니다. `id`를 추가해 결과를 하나로 고정합니다. 엔진과 무관하게 결정적입니다. |
| `_35_cherry/issue_21654_server_side_loaddb/partition_tbls` (`partition_tbls.sh`, `bug_bts_11093.answer`, `bug_bts_11093.answer_WIN`) | test2에 검사를 추가합니다: 범위 밖 값(`100`)이 있는 loaddb가 실패하는지, 실패한 묶음이 rollback되는지, 올바른 파일을 다시 넣으면 1행만 들어가는지. answer에서는 test2의 "2행 입력 성공" 블록을 지웁니다. | 기존 answer는 `loaddb -C`가 파티션 범위를 검사하지 않는 버그를 정상으로 기록하고 있었습니다. OOS 브랜치의 #7927(CBRD-27089) 이후 엔진은 이 행을 `ER_PARTITION_NOT_EXIST`로 거부합니다. develop 쪽 같은 버그 수정은 엔진 PR #8275(CBRD-27441)입니다. |
| `_36_damson/cbrd_23608_tde/file_enc_01` (`file_enc_01.sh`, `result.answer`) | 기대 힙 페이지 수를 9에서 5로 바꿉니다(grep 기준 줄과 answer). | 4K 페이지 DB에서 `char(2000)` 값은 OOS 파일로 가므로 힙이 처음 5페이지에서 늘어나지 않습니다. |
| `_36_damson/cbrd_23608_tde/file_enc_02` (`result.answer`) | AES 페이지 할당 줄 1쌍을 추가합니다. | OOS 파일 페이지를 할당할 때도 TDE(투명 데이터 암호화) AES가 설정됩니다. |
| `_36_damson/cbrd_23608_tde/file_enc_03` (`result.answer`) | OOS 페이지의 AES 설정 줄과 해제 줄을 1줄씩 추가합니다. | 값이 OOS 페이지에 기록되고, DROP할 때 OOS 파일 페이지도 해제됩니다. |
| `_36_damson/cbrd_23608_tde/file_enc_04` (`result.answer`) | AES 적용 3줄을 추가하고, 마지막 NONE 블록을 9줄에서 5줄로 줄입니다. | 첫 큰 값을 넣을 때 OOS 파일이 AES로 만들어지고, 힙 페이지는 늘어나지 않습니다. |
| `_36_damson/cbrd_23608_tde/file_enc_05` (`result.answer`) | OOS 페이지 해제(AES) 2줄과 NONE 설정 2줄을 추가합니다. | DROP과 재시작 복구 때 OOS 파일 페이지도 해제됩니다. "해제 수 = NONE 수"라는 검증 내용은 그대로입니다. |
| `_36_damson/cbrd_23608_tde/file_enc_07` (`result.answer`) | AES 설정 2줄을 지웁니다. | 힙 페이지가 늘어나지 않아서 일반 처리와 복구가 각각 3페이지만 설정합니다. |
| `_36_damson/cbrd_23608_tde/log_enc_04` (`log_enc_04.sh`, `rcvindex.data`) | 고정 길이 `bit(160000)` 테이블을 추가해 overflow 로그를 계속 만들고, 기대 로그 목록에 `RVOOS_INSERT`, `RVOOS_DELETE`를 추가합니다. 빠진 로그 종류를 모두 보고하도록 검사를 고칩니다. | OOS에서는 큰 가변 길이 값이 행 밖으로 가서 기존 쿼리가 overflow·relocation 로그를 만들지 않습니다. 고정 길이 BIT 값은 행 밖으로 가지 않으므로 overflow 경로를 계속 검증할 수 있습니다. OOS 페이지도 암호화되므로 OOS 로그를 확인합니다. |
| `_36_damson/cbrd_23608_tde/tbl_enc_08`, `_36_damson/cbrd_23608_tde/tbl_enc_14` (`result.answer`) | diagdb의 파일 종류를 `MULTIPAGE_OBJECT_HEAP`(overflow)에서 `OUT_OF_LINE_OVERFLOW_STORAGE`(OOS)로 바꿉니다. | 약 20KB 행이 overflow 파일 대신 OOS 파일을 만듭니다. OOS 파일도 AES로 암호화됩니다. |
| `_37_elderberry/cbrd_23842_cdc/bug/cbrd_27064`, `_37_elderberry/cbrd_23842_cdc/bug/cbrd_27075` → `_25_unstable/` 아래 같은 경로, `_25_unstable/readme.txt` | 파일 내용은 그대로 두고 `_25_unstable`로 옮깁니다. readme에 측정한 실패와 되돌리는 조건을 적습니다. | 두 CDC 테스트는 OOS 엔진에서 실패합니다. CDC·flashback의 OOS 이력 지원(CBRD-26939)은 이번 엔진 PR 범위에서 뺐습니다. 2026-10-26 결정에 따라 gha-ci에서만 제외하고 daily VM 회귀에서는 계속 실행합니다. CDC 수정 후 5회 연속 통과하면 원래 경로로 되돌립니다. |

## Remarks

- 검증: 엔진 `5a70787fe`와 이 TC head `75a02020e`로 실행한 [gha-ci run 40349442612](https://github.com/CUBRID/cubrid/actions/runs/40349442612)에서 `test_shell`이 3,460 PASS / 0 FAIL / 30 SKIP으로 통과했습니다.
- **머지 순서:** `Check TC PRs` 검사 때문에 이 PR은 엔진 PR보다 먼저 TC develop에 들어가야 합니다. 그 사이에는 develop 엔진에 OOS가 없으므로, `bigPageSize`와 CDC 이동을 뺀 대부분의 테스트가 develop CI와 daily 회귀에서 실패할 것으로 예상합니다. 엔진 PR을 머지하기 직전에 머지해 주세요.
- **CDC 격리의 영향:** 이 PR이 머지되면 `cbrd_27064`, `cbrd_27075`는 모든 엔진 PR의 gha-ci에서 빠집니다. 두 테스트는 develop 엔진에서는 통과합니다. 되돌릴 때까지는 daily VM 회귀에서만 실행됩니다.
- **오류 번호:** `-1387,-1389,-1390`은 `error_code.h`의 순서로 정해집니다. develop에 오류 코드가 추가되면 answer 파일 5개(8줄)를 다시 맞춰야 합니다. 지금까지 develop 동기화 때마다 6번 갱신했습니다.
- 기존 승인 뒤에 `partition_tbls`(`7bc77c666`)와 CDC 격리(`dd12b36a2`)가 추가되었습니다. 이 두 변경은 다시 봐 주세요.
- 짝 PR: [CUBRID/cubrid-testcases#3551](https://github.com/CUBRID/cubrid-testcases/pull/3551)(SQL·medium). `feat/oos` 시절의 이전 PR #3782에서 16개 파일을 그대로 가져왔습니다.
- 커밋별 이력과 근거: [CBRD-26357-tc-pr-changes_5a70787_claude.md](https://github.com/vimkim/my-cubrid-docs/blob/main/cbrd-26357/CBRD-26357-tc-pr-changes_5a70787_claude.md)
