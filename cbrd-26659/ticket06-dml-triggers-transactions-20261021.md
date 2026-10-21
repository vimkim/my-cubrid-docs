# Work456/06: DML·트리거·트랜잭션과 실제 레코드 상태

기준일: 2026-10-21, Asia/Seoul. 독자: Work456 조정자와 PR 8128 검토자. 질문: 일반 DML과 트리거 쓰기가 독립적인 전체 값 모델, 실제 HAS_OOS 전환, 실패·rollback의 소유권 보존을 만족하는가?

일반 DML, 입력 형식, 제약 거부, 즉시 rollback/savepoint와 트리거 거부의 원자성을 제품 인터페이스로 검증했다. 트리거의 INSERT/UPDATE/DELETE 관련 쓰기는 **전체 값은 정확하지만 요구된 HAS_OOS set을 만들지 못하는 엔진 FAIL**이다. 이 보고서는 보완 테스트 전달과 passing coverage를 구분하며 엔진 수정을 포함하지 않는다. Vacuum 이후 rollback은 티켓 13의 별도 실제 CS 실행을 연결하며, 여기의 즉시 rollback으로 대체하지 않는다.

## 기준과 실행 경계

| 항목 | 정확한 식별자와 범위 |
| --- | --- |
| 엔진 실행 | `d13aebf6428a68c2852d16df143d1da203d86dea`, own `task/work456-06-source`, Linux·16 KiB·optdebug, provider의 UNIT_TEST_OOS ON 설치. `1ef86a7` 위의 티켓 14 C++ 테스트 두 개만 추가된 리비전이며 production 수정은 없다. |
| 설치 | 불변 provider `/home/vimkim/.cub/install/work456-ticket14/optdebug`를 own `work456-ticket06/optdebug`로 복사했다. Provider의 289개 파일 해시가 own 복사와 모두 일치했다. 각 native preflight에서 installed `d13aebf`, `commit_match=yes`, mismatch 예외 없음. |
| 공개 TC | 시작 `410ba5d2ce3151054b11f8443d2da9966a5eafff`; 구현 `a3e640fbe`와 form C/S 보완 `74e6c84a7`, 새 SQL/answer 1쌍. 기존 6개 case bytes는 변경하지 않았다. |
| 비공개 TC | 시작 `f934b56621c352df84fc7b5a7965148adb07d5ea`; 구현 `d997311c3`, cleanup receipt `92f9811fd`, form C/S 완결 `1f867526e`; native shell 8개와 공통 controller/observer 2개. |
| 별도 C++ 실행 | 티켓 14의 frozen source `1ef86a7efa34002e971b1b30bcf5d451e9db441b`, UNIT_TEST_OOS ON, 29개의 별도 fixture-aware native CTest invocation. 그중 06 관련 57개를 독립 대조했다. `d13aebf` 제품 실행과 합쳐 단일 receipt로 표현하지 않는다. |
| Runner | `cubrid-testkit dev`; SHA-256 `31be3b1e542b05d1ac7581d47f785319ce61421f4b5d94681a9c558d71445f5a`, Go revision `5f641188b4ca5d9404a43bcc00ed65fa6ebc60b0`, modified=true. |
| CTP·JDK | CTP `9c62858b10005d721546cc007be260844033b9e9`의 기존 다섯 tracked 수정은 보존했다. CTP는 asset만 제공하고 native runner가 실행했다. Temurin 8.0.462+8; 복사 JDBC jar SHA-256 `17e2e0ee4c0756b4b0a7cd679f1fea4630124f5704bc69db0c2107235190ff98`. |
| 계약·매뉴얼 | OOS-CONTEXT 전체를 읽고 앞뒤 SHA-256 `b38059a3a8e9495a88c16cfe14daec89d72586e3d0ef2c86755b64305ebccb65` 동일함을 확인했다. Trigger correlation/error oracle은 manual `3b6ae97bfbdc664b010ffa933ded5a05b291ae03`, `en/sql/trigger.rst:262–305`와 기존 canonical SQL/answer를 사용했다. |

PR은 [engine 8128](https://github.com/CUBRID/cubrid/pull/8128), [public TC 3688](https://github.com/CUBRID/cubrid-testcases/pull/3688), [private TC 4365](https://github.com/CUBRID/cubrid-testcases-private-ex/pull/4365)이다. Source integration head repository는 `vimkim/cubrid`, head는 `CBRD-26659-oos-testcases-handover`, base는 `feature/oos-merge`다. 게시·push·destination merge·CI·TC PR 조작은 하지 않았다.

조정자가 native D를 승인했다. `cub-workenv init --no-db`로 own config/registry/숫자 자원을 할당하고, 매 실행에 설치·CTP·HOME·TMP·빈 registry를 따로 복사했다. `TESTKIT_NATIVE=sql|shell`, `TESTKIT_CONTAIN=1`, suite slot 1개를 사용하고 실행은 직렬이었다. Shell은 read-only corpus와 `scenario_disk=on`, SQL은 복사한 cases/answers를 사용했다. Native suite slot의 network/PID/IPC/mount 격리는 pinned testkit의 실제 경로를 사용한다. 기존 CCI dirt, CTP 수정, 다른 사용자의 서비스는 건드리지 않았다. Owned DB·등록·디렉터리와 subreaper process groups를 검사해 정리했다.

자체 source build/compile database는 생성하지 않았다. OOS validator는 해당 두 개발 도구의 부재를 보고했다. 이 티켓은 source 수정이나 LSP에 의존하지 않으며, 일치하는 검증된 제품 설치와 텍스트 source/제품 관측을 사용했다. 새 빌드 통과 주장은 하지 않는다.

## 독립 값 모델과 현재 슬롯 매핑

기본 값은 `X'19ab23cd45ef'`, `X'29bc34de56fa'`, 5,107 byte의 `a1×1701 + b2×1703 + c3×1703`, 5,407 byte의 `d4×1801 + e5×1803 + f6×1803`, 21,011 byte의 `17×7001 + 28×7003 + 39×7007`이다. 각 행의 id/note와 **전체 payload equality**를 검사한다. NULL과 empty VARBIT은 별도 모델이다. 길이·개수·SHOW 합계는 이 equality를 대체하지 않는다.

`oos_dml/dml_check.py`는 WHERE 없는 `SELECT_RECORD_INFO`의 전체 physical set을 읽는다. 정상 SELECT 또는 writer ACK SELECT로 보인 전체 모델과 연결하고, 현재 행은 정확히 하나의 `REC_HOME=2`, delete ID 없음, 올바른 flag, 기존 home 슬롯으로 검증한다. 정수 플래그의 `0x08`만 HAS_OOS로 해석한다. Slot relocation·partition·임의 version-chain mapping은 허용하지 않는다. Physical id/page/slot 숫자는 관찰값이며 golden constant가 아니다.

삭제·rollback INSERT의 슬롯은 이전에 관측한 정확한 slot identity와 트랜잭션 순서로 별도 기록한다. 실패한 다중 INSERT가 새 `REC_DELETED_WILL_REUSE=7` 슬롯을 남기는 경우에는 다음 조건을 모두 요구한다.

- 이 fresh owned heap의 유일한 writer가 실행한 정확한 INSERT와 기대 오류, nonzero CSQL 종료를 먼저 보존한다.
- 실패 전후 **전체** physical set의 새 슬롯 차이만 사용하며, 개수는 시도한 INSERT 행 수 이하여야 한다.
- 새 슬롯은 type 6/7, logical id/note·flags·insert/delete ID가 모두 NULL이고 value_ok=0이어야 한다.
- SQL 본문·SHA-256·오류·종료 상태·이전 rows/slots·새 정확한 slot identity를 ledger에 남긴다. 이후 관측은 저장한 동일 슬롯만 허용한다.

일반 unknown/live/duplicate 슬롯은 실패다. Trigger 거부로 rollback된 side-effect INSERT에도 같은 qualification을 적용한다. 이 슬롯에는 HAS_OOS credit을 주지 않는다. 현재 행의 전체 값·home·flag와 class/heap/OOS VFID, 청크 수·총 직렬화 byte 보존은 별도로 검사한다. SHOW의 배타적 관측이 writer와 충돌하는 구간은 동일 writer의 ACK된 SHOW로 읽는다.

## 전달·실행한 제품 사례

비공개 경로 prefix는 `shell/_40_guava/`, 각 case는 `<name>/cases/<name>.sh`다. 제품 SQL은 `sql/_36_guava/cbrd_26659/`의 cases/answers pair를 사용한다.

| Shell case | 필수 사례와 실제 검증 | 최종 판정 |
| --- | --- | --- |
| `cbrd_26659_dml_forms` | single/multi VALUES, INSERT SET, literal defaults, expression, scalar subquery 각각의 C/S, INSERT SELECT/self-copy; 같은 heap의 실제 C/S와 distinct 전체 값 | PASS |
| `cbrd_26659_dml_states` | assigned C→C/C→S/S→C/S→S, unassigned, assigned-equal, NULL/empty, subquery/join UPDATE, PK/payload/all DELETE, reinsertion, TRUNCATE/reinsert | PASS |
| `cbrd_26659_dml_transactions` | writer I/U/D와 C↔S, rollback의 원래 membership·값·flags·ownership 복구, savepoint 전후 I/U/D와 partial rollback, commit, committed DELETE absence | PASS |
| `cbrd_26659_dml_atomicity` | narrow PK/UNIQUE/NOT NULL, 다중 INSERT/UPDATE 실패, supported view WITH CHECK OPTION의 INSERT/UPDATE 거부, 정확한 이전 값·flags·소유 파일/청크 보존, 이후 valid DML | PASS |
| `cbrd_26659_dml_triggers_reject` | BEFORE 거부의 다중 UPDATE atomicity, AFTER/BEFORE side effects 없음, 원래 S/C 행·파일/청크 보존, reject 제거 후 쓰기 | PASS |
| `cbrd_26659_dml_triggers_insert` | BEFORE INSERT의 new, AFTER INSERT의 obj, actual target와 두 mirror의 전체 모델/flags | FAIL: 3개 S 의무가 C로 남음 |
| `cbrd_26659_dml_triggers_update` | BEFORE UPDATE의 obj old model, AFTER UPDATE obj new model, actual updated target flags | FAIL: 3개 S 의무가 C로 남음 |
| `cbrd_26659_dml_triggers_delete` | BEFORE DELETE obj old model, AFTER STATEMENT DELETE의 독립 literal write, 실제 대상 행 부재 | FAIL: 2개 S 의무가 C로 남음 |

`new/old/obj`의 적용성은 매뉴얼 계약을 따른다. AFTER DELETE에는 row correlation이 없으므로 BEFORE에서 old rows를 복사하고 AFTER STATEMENT에서 알려진 별도 행을 쓴다. 일반 FK와 큰 key의 주 검증은 티켓 10, MERGE/REPLACE/ODKU는 티켓 07이다. Table-schema CHECK는 baseline에서 enforcement를 제공하지 않으므로 기존 canonical supported view WITH CHECK OPTION oracle을 유지했다.

공개 JDBC native 실행은 새 `cbrd_26659_oos_dml_forms.sql`과 기존 `sql01_insert_select`, `sql04_update`, `sql04_delete`, `sql05_constraints`, `sql05_transactions`, `sql06_triggers` 6개, 총 7개를 모두 실행해 PASS했다. 새 case는 literal 전체 모델로 SET/default/expression/scalar subquery의 C/S 모델과 joined UPDATE를 검사한다. JDBC receipt는 논리 결과의 증거이며 shell fixture의 flags를 해당 JDBC invocation의 관측으로 빌려 쓰지 않는다.

## Trigger placement failure

세 독립 trigger case는 모든 예정된 논리·물리 target 단계를 끝냈다. 실제 엔진 오류를 이유로 다음 family를 skip하지 않았다. 5,107/5,407 byte 값의 정상 일반 INSERT/UPDATE는 같은 설치에서 S가 되지만 다음 trigger 경로의 현재 `REC_HOME=2`에는 `HAS_OOS=0`이다.

| 실제 대상 | 관찰 |
| --- | --- |
| triggered INSERT target, BEFORE INSERT mirror, AFTER INSERT mirror | 각각 large id 2의 flags=1, clear |
| triggered UPDATE target, AFTER UPDATE mirror | 각각 new large id 1의 flags=5/1, clear |
| BEFORE UPDATE mirror, BEFORE DELETE mirror | 각각 old large id 2의 flags=1, clear |
| AFTER STATEMENT DELETE literal target | id 9, note909, 5,407 byte 전체 값 정확, flags=1, clear |

각 fixture는 eligible variable payload가 하나뿐이고 다른 데이터는 int다. Accepted demotion gate에서 충분히 벗어나므로 payload 크기만 보고 HAS_OOS를 추정한 결과가 아니다. 실제 slot flags가 기대와 다르다. Correct expected set은 바꾸지 않았다. 각 final case는 native NOK이며 8개 물리 의무에 PASS credit이 없다.

Source `d13aebf`의 `src/query/execute_statement.c:9596`/`:9627`은 trigger가 있는 UPDATE를 client로 선택하고, `:12308`/`:12446`은 INSERT trigger 또는 `do_Trigger_involved`에서 server INSERT를 허용하지 않는다. `src/object/transform_cl.c:781`의 `tf_mem_to_disk`가 관련 client serialization 경계다. 이는 관련 source 경로에 대한 정적 근거이며 완결된 root-cause/fix proof는 아니다. [별도 엔진 수정 handoff](engine-followup-client-trigger-oos-placement-20261021.md)에 재현 방법과 repair acceptance를 남겼다. [CBRD-27424](https://jira.cubrid.org/browse/CBRD-27424)는 관련 SA/client serialization 배경이며 이 trigger 결함을 자동으로 그 수정에 귀속시키지 않는다. 별도 수정 연결의 owner는 조정자이며 attribution은 under triage다.

## Native receipt와 negative control

Raw evidence root: `/home/vimkim/temp/work456-implementation/ticket06/`. 각 attempt에는 preflight, copied config/environment, exact expected list, 입력 SHA-256, command, stdout/stderr, runner status, native summary/XML/feedback와 cleanup 증거가 있다. SQL은 명시된 `Result Root Dir`, shell은 `<attempt>/CTP/result/shell/current_runtime_logs`를 verifier로 검사했다. Runner exit 0만으로 PASS를 판단하지 않는다.

`red-forms01`은 observer 미구현으로 정확히 1 NOK였다. `green-forms01`은 1/1 PASS였다. `green-states01/02`의 인용·empty-model 오류, `green-other01`의 mapper NameError/17-character DB-name 위반과 중단, `green-models02`의 unknown aborted-slot 감지, `green-models03`의 observer session blocking과 rejected-trigger slot qualification gap은 test implementation 시도다. 엔진 FAIL이나 passing coverage에 합산하지 않았다. 모든 원본 로그를 보존하고 수정 후 fresh attempt로 다시 실행했다. DB 이름 제한은 manual `en/admin/admin_utils.rst:86`에 근거한다.

| 최종/검증 attempt | Required = executed | PASS / FAIL / SKIP | 의미 |
| --- | ---: | --- | --- |
| `final-shell03` | 8 | 5 / 3 / 0 | 위 8개 committed shell case; 3개 correct engine FAIL |
| `final-sql02` | 7 | 7 / 0 / 0 | 새 forms와 retained logical population; 입력을 commit bytes와 대조 |
| `negative-flag02` | 1 | 0 / 1 / 0 | INSERT 입력은 보존하고 independent expected large flag만 clear로 바꾼 disposable copy |
| `negative-tail02` | 1 | 0 / 1 / 0 | INSERT 입력은 보존하고 expected 작은 값의 마지막 byte ef→ee만 바꾼 disposable copy |

최종 shell의 required/executed 56개 phase와 8개 physical FAIL 의무를 별도로 대조했다. Native 최종 receipt·negative-control 결과와 commit input 비교는 handoff의 `independent-artifact-audit.json`에 연결한다. SQL answer의 trailing spaces는 기존 native formatting convention으로 유지했으며 그 외 Bash syntax, warning-level ShellCheck, task diff checks를 통과했다.

## 관련 C++ 57개의 assertion disposition

`cpp-reconciliation.json`은 공통 frozen receipt의 SHA-256 `d55d4243db537e6c8c5338ffd15d8f41429e76391f04d18990b367cbbb585b9e`를 확인하고 아래 57개 각각을 required/discovered/started/native GTest XML PASS, CTest rc0, per-binary owned process 없음에 대조한다. Registry와 config 보존도 공통 receipt에 남아 있다. Native SQL과 동일 결과라는 이유로 C++를 삭제하지 않았다.

| Retained group | 수 | 유지하는 실제 assertion과 모드 |
| --- | ---: | --- |
| `OosSqlBigone` | 4 | SA API의 OOS+bigone 거부/기존행 보존과 일반 bigone·잔여 record 허용. 경계 population의 주 owner는 12. |
| `OosSqlCrud` | 8 | SA module/API CRUD, 다중 OOS 속성, single/multi chunk 값과 read dispatch batching/Expand 회피. 제품 equality만으로 dispatch 계약을 대체할 수 없다. |
| `OosSqlDelete` | 8 | SA eager DELETE/update/reinsert, selective survivor와 multi-column/multi-chunk 경로. |
| `OosEagerCleanup` | 12 | SA synchronous old-chain/current chunk/page accounting과 반복 UPDATE/DELETE. CS MVCC의 지연된 cleanup과 구별한다. |
| `OosSqlTxn` | 8 | SA API commit/abort와 membership/길이/값 복구. CS writer/snapshot/vacuum 증거와 합치지 않는다. |
| `OosSqlUpdateDelete` | 7 | SA 값 변경·unassigned attribute·repeated/chunk transition·DELETE/TRUNCATE API 동작. |
| `OosEagerDiagnostics` | 10 | Direct native stale/missing/reused/malformed identity, retained reference, relocated record, interrupted cleanup과 diagnostic/error 보존. 정상 제품 SQL로 도달하지 않는 fault 계약이다. |

정확한 case IDs는 다음과 같다.

- `OosEagerDiagnostics.DeleteCompletesAndDiagnosesAStampMismatch`: retain; native PASS.
- `OosEagerDiagnostics.UpdateCompletesAndDiagnosesAStampMismatch`: retain; native PASS.
- `OosEagerDiagnostics.DeleteDiagnosesAHeadSlotAlreadyEmpty`: retain; native PASS.
- `OosEagerDiagnostics.DeleteDiagnosesADeallocatedAndAReusedHeadPage`: retain; native PASS.
- `OosEagerDiagnostics.LiveReferenceIsReclaimedWithoutADiagnostic`: retain; native PASS.
- `OosEagerDiagnostics.UpdateKeepsAChainTheNewImageStillReferencesAndDiagnosesOnlyTheDropped`: retain; native PASS.
- `OosEagerDiagnostics.RelocatedUpdateAndDeleteDiagnoseTheForwardRecordsStaleStub`: retain; native PASS.
- `OosEagerDiagnostics.ThreeStaleChainsInOneRecordAreOneNotification`: retain; native PASS.
- `OosEagerDiagnostics.MatchingNonHeadReferenceFailsTheDelete`: retain; native PASS.
- `OosEagerDiagnostics.InterruptedCleanupIsAnErrorNotASkip`: retain; native PASS.
- `OosSqlBigone.OosColumnWithBigoneRejected`: retain; native PASS.
- `OosSqlBigone.BigoneWithoutOosColumnSucceeds`: retain; native PASS.
- `OosSqlBigone.OosColumnInlineBetween4kAnd16kSucceeds`: retain; native PASS.
- `OosSqlBigone.UpdateIntoOosBigoneRejected`: retain; native PASS.
- `OosSqlCrud.BasicInsertSelect`: retain; native PASS.
- `OosSqlCrud.SmallRecordNoOos`: retain; native PASS.
- `OosSqlCrud.MultipleOosColumns`: retain; native PASS.
- `OosSqlCrud.Cbrd27006MultiOosColumnSelectsAndUpdate`: retain; native PASS.
- `OosSqlCrud.Cbrd27006MixedSingleChunkAndMultiChunkRow`: retain; native PASS.
- `OosSqlCrud.Cbrd27006ReadDispatchBatchesOnlyMultiOosProjections`: retain; native PASS.
- `OosSqlCrud.MultiChunkOos`: retain; native PASS.
- `OosSqlCrud.MixedChunkSizes`: retain; native PASS.
- `OosSqlDelete.DeleteSingleChunk`: retain; native PASS.
- `OosSqlDelete.DeleteMultiChunk`: retain; native PASS.
- `OosSqlDelete.DeleteLarge160KB`: retain; native PASS.
- `OosSqlDelete.DeleteSelectiveRowsIntact`: retain; native PASS.
- `OosSqlDelete.DeleteAndReinsert`: retain; native PASS.
- `OosSqlDelete.DeleteMixedColumns`: retain; native PASS.
- `OosSqlDelete.UpdateOosColumn`: retain; native PASS.
- `OosSqlDelete.DeleteAndReinsertMultiChunk`: retain; native PASS.
- `OosEagerCleanup.SingleUpdateCleansOldOos`: retain; native PASS.
- `OosEagerCleanup.MultipleUpdatesPagesBounded`: retain; native PASS.
- `OosEagerCleanup.MultiOosColumnUpdateCleanup`: retain; native PASS.
- `OosEagerCleanup.UpdateChurnStress`: retain; native PASS.
- `OosEagerCleanup.StepByStepLifecycleWithPageCounts`: retain; native PASS.
- `OosEagerCleanup.UpdateVaryingOosSizes`: retain; native PASS.
- `OosEagerCleanup.MixedColumnsUpdateOnlyOos`: retain; native PASS.
- `OosEagerCleanup.SingleDeleteCleansOos`: retain; native PASS.
- `OosEagerCleanup.InsertDeleteChurnPagesBounded`: retain; native PASS.
- `OosEagerCleanup.MultiChunkDeleteCleansAllChunks`: retain; native PASS.
- `OosEagerCleanup.MultiOosColumnDeleteCleanup`: retain; native PASS.
- `OosEagerCleanup.MixedFillerDeleteChurnPagesBounded`: retain; native PASS.
- `OosSqlTxn.RollbackInsert`: retain; native PASS.
- `OosSqlTxn.RollbackUpdate`: retain; native PASS.
- `OosSqlTxn.CommittedDataPersists`: retain; native PASS.
- `OosSqlTxn.RollbackMultiChunk`: retain; native PASS.
- `OosSqlTxn.ComboThenCommit`: retain; native PASS.
- `OosSqlTxn.RollbackDelete`: retain; native PASS.
- `OosSqlTxn.DeleteCommit`: retain; native PASS.
- `OosSqlTxn.DeleteRollback`: retain; native PASS.
- `OosSqlUpdateDelete.UpdateOosValue`: retain; native PASS.
- `OosSqlUpdateDelete.UpdateNonOosColumn`: retain; native PASS.
- `OosSqlUpdateDelete.RepeatedUpdates`: retain; native PASS.
- `OosSqlUpdateDelete.SizeChangeChunkTransition`: retain; native PASS.
- `OosSqlUpdateDelete.DeleteOosRows`: retain; native PASS.
- `OosSqlUpdateDelete.TruncateAndReinsert`: retain; native PASS.
- `OosSqlUpdateDelete.UpdateMultiChunk`: retain; native PASS.

## 다른 티켓과 남은 경계

Unassigned UPDATE의 현재 값과 flag는 이 실제 제품 invocation에서 확인했다. Entire 24-byte stub/OID/stamp 동일성과 newest-version owner, commit-conditional notification은 [CBRD-27230](https://jira.cubrid.org/browse/CBRD-27230)의 계약이며 티켓 15의 실제 reachable seam 사례가 추가로 맡는다. 이 보고서의 SHOW class/file/chunk 관측이 전체 stub 또는 notification을 증명한다고 주장하지 않는다. SA eager CPP와 CS 제품 의미를 유지하고 assertion 삭제는 없다.

티켓 13의 final01은 실제 CS `cbrd_26659_snapshot_visibility` PASS와 `cbrd_27237_rollback_vacuum` FAIL을 별도로 실행했다. 후자는 writer rollback 및 vacuum ACK 뒤 metadata inconsistency/corruption을 관찰했다. [CBRD-27237](https://jira.cubrid.org/browse/CBRD-27237)의 해당 receipt를 유지하며 이 즉시 rollback PASS로 대체하지 않는다. Raw pointers는 `ticket13/handoff.json`과 `ticket13/final01/independent-audit.json`이다. Source `1ef86a7`의 별도 invocation이며 여기의 d13 flags와 단일 receipt로 합산하지 않는다. Actual CS page-LSA/system-horizon qualification은 13/15의 별도 남은 범위다.

티켓 06의 required 제품 family와 관련 retained C++ population은 전달·실행되었다. Trigger placement의 3 FAIL은 올바른 intended oracle 아래 남으며 수정 attribution은 under triage다. 성능·HA qualification, production repair, 다른 티켓의 미완료 boundary와 source/TC publication/CI는 이 전달의 완료 주장에 포함하지 않는다.
