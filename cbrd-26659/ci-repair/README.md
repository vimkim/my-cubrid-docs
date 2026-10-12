# PR8128 testcase 수리 범위와 상태

범위 결정: 2026-10-12, work item 331. 마지막 갱신: 2026-10-13, Asia/Seoul. 실행 work item 332.
관련 PR: [Engine #8128](https://github.com/CUBRID/cubrid/pull/8128), [public TC #3688](https://github.com/CUBRID/cubrid-testcases/pull/3688), [private TC #4365](https://github.com/CUBRID/cubrid-testcases-private-ex/pull/4365).

이 문서는 최신 실패 TC의 수리 대상 여부와 검증 상태를 추적한다. 사용자는 SQL와 shell의 실패 전체를 검토하고 아래 제외 규칙을 적용한 뒤 남는 SQL 14개를 모두 정상화하는 범위에 동의했다. 범위 합의와 실행 완료를 구분한다. 현재 최종 Engine `1ef86a7`의 대상 14개 fresh DB 독립 검증은 모두 통과했고, 원래 72-case 순서와 단일 CI qualification은 진행 중이다.

공유 이해는 2026-10-12에 최종 확인했다. 실행 절차와 완료 기준은 [합의된 수리 계획](/home/vimkim/gh/my-cubrid-docs/cbrd-26659/ci-repair/plan.md)에 정리한다.

## 합의된 제외 규칙

1. `feature/oos-merge`의 기존 TC 구성에서 이미 관측된 동일 증상 실패는 이번 수리 대상에서 제외한다. 새 TC가 동일 Engine 소스에서도 실패한다는 이유만으로 자동 제외하지 않는다.
2. 이전 delivery에서 올바른 성공 기대를 유지한 채 알려진 결함의 재현기로 남긴 예상 실패 TC는 이번 수리 대상에서 제외한다.

이 규칙은 이번 수리 작업의 범위를 정한다. 제외된 결함은 미해결로 기록하고, 실행 생략이나 정답 변경은 별도 결정으로 다룬다. 정상적인 오류를 검증하는 SQL 문장은 passing testcase의 검증 조건이므로 제외 대상이 아니다.

원인 검증용 가설 패치를 허용한다. 최종 게시에는 올바른 정답과 assertion을 보존하고, 원인을 설명하는 경로 증거와 패치 전후 대조 실행을 확보한다. 모든 큐 연산의 추적을 의무화하지 않는다.

예상 실패인 partition 결함이 대상 SQL 14개의 연쇄 실패 원인으로 입증되면, 14개 정상화에 필요한 공통 원인 수리를 허용한다. Partition 자체의 모든 기존 결함을 해결할 의무로 범위를 넓히지 않으며, 다른 제외 항목의 수리는 기존 범위를 유지한다.

## 판정에 사용한 실행과 리비전

- 최신 결과: [run38245729674, attempt 1](https://github.com/CUBRID/cubrid/actions/runs/38245729674). SQL 72개 중 57 pass / 15 fail, shell replay 8개 중 3 pass / 5 fail. Medium은 이전 통과 결과를 유지했고 이 run에서 재실행하지 않았다.
- Engine: `a5da823b2a84e95b4b22d48abe4a3f9fd601c176`.
- Public TC: `1a556a0752073aaad573bf87d53f3eb75f398138`. Private TC: `a2054f965a20241b87dc9577585ccc8a8cb6ab97`.
- 기존 기준 실행: [run36570256001, attempt 1](https://github.com/CUBRID/cubrid/actions/runs/36570256001), Engine `fb567a629cdb390fff920542173fa36f454c74a0`. 새 OOS TC는 이 실행의 기존 corpus에 없었다.
- 현재 `feature/oos-merge`와 PR8128의 Engine source tree는 동일하다. 이 사실만으로 testcase 구성, 빌드 및 실행 조건의 동등성을 주장하지 않는다.

## SQL 실패 15개

모든 경로는 public repository의 `sql/_36_guava/cbrd_26659/cases/` 아래이다. 순서는 최신 72-case shard의 실제 실행 위치이다. 최신 관측 열은 역사적 run38245729674의 실패를 보존한다. 현재 검증의 identity·명령·결과는 [수리 검증 기록](/home/vimkim/gh/my-cubrid-docs/cbrd-26659/ci-repair/repair-results.md)에 둔다. 아래 Fresh `F01`–`F14`는 `/home/vimkim/tmp/s332-final-01`–`14`이며 모두 Engine `1ef86a7efa34002e971b1b30bcf5d451e9db441b`, public TC `1dec9d147547d8d404b6705b742e6e6fa0a58b98`, native Debug/HA/JDBC와 동일 runner SHA를 사용한다. 각 `verify.log`, XML, copied `.result`와 `cleanup.exit`가 실제 근거다.

| 순서 | TC basename | 수리 판정 | 최신 관측 | 상태와 다음 검증 |
| --- | --- | --- | --- | --- |
| 43 | `cbrd_26659_oos_partition.sql` | 제외: 기존 예상 실패 | Partition UPDATE `-21019`, `repl_log_insert`, `replication.c:468` assertion | 제외 유지; source DELETE의 OOS 큐 재소비 원인 입증 및 guard 수리. Local original partition 포함 4/4 pass; 최종 순서·CI 별도 확인 |
| 44 | `cbrd_26659_oos_partition_routing.sql` | 대상 | 초기 DROP `-581`; JDBC reconnect 실패 | Fresh F01: golden·artifact PASS(1/1), cleanup 0; 원래 72-case·CI 진행 중 |
| 45 | `cbrd_26659_oos_representation.sql` | 대상 | 초기 DROP `-581` | Fresh F02: golden·artifact PASS(1/1), cleanup 0; 원래 72-case·CI 진행 중 |
| 46 | `cbrd_26659_oos_schema.sql` | 대상 | 초기 DROP `-581` | Fresh F03: golden·artifact PASS(1/1), cleanup 0; 원래 72-case·CI 진행 중 |
| 47 | `cbrd_26659_oos_sql01_insert_select.sql` | 대상 | 초기 DROP `-581` | Fresh F04: golden·artifact PASS(1/1), cleanup 0; 원래 72-case·CI 진행 중 |
| 48 | `cbrd_26659_oos_sql04_delete.sql` | 대상 | 초기 DROP `-581` | Fresh F05: golden·artifact PASS(1/1), cleanup 0; 원래 72-case·CI 진행 중 |
| 49 | `cbrd_26659_oos_sql04_update.sql` | 대상 | 초기 DROP `-581` | Fresh F06: golden·artifact PASS(1/1), cleanup 0; 원래 72-case·CI 진행 중 |
| 50 | `cbrd_26659_oos_sql05_bigone.sql` | 대상 | 초기 DROP `-581` | Fresh F07: golden·artifact PASS(1/1), cleanup 0; 원래 72-case·CI 진행 중 |
| 51 | `cbrd_26659_oos_sql05_constraints.sql` | 대상 | 초기 DROP VIEW `-581` | Fresh F08: golden·artifact PASS(1/1), cleanup 0; 원래 72-case·CI 진행 중 |
| 52 | `cbrd_26659_oos_sql05_transactions.sql` | 대상 | `autocommit off` 후 초기 DROP `-581` | Fresh F09: golden·artifact PASS(1/1), cleanup 0; 원래 72-case·CI 진행 중 |
| 53 | `cbrd_26659_oos_sql06_triggers.sql` | 대상 | 초기 DROP `-581` | Fresh F10: golden·artifact PASS(1/1), cleanup 0; 원래 72-case·CI 진행 중 |
| 54 | `cbrd_26659_oos_sql07_read_paths.sql` | 대상 | 초기 DROP VIEW `-581` | Fresh F11: golden·artifact PASS(1/1), cleanup 0; 원래 72-case·CI 진행 중 |
| 55 | `cbrd_26659_oos_sql09_lob_copy.sql` | 대상 | 초기 DROP `-581` | Fresh F12: golden·artifact PASS(1/1), cleanup 0; 원래 72-case·CI 진행 중 |
| 56 | `cbrd_26659_oos_sql09_lob_maxcols.sql` | 대상 | 초기 DROP `-581` | Fresh F13: golden·artifact PASS(1/1), cleanup 0; 원래 72-case·CI 진행 중 |
| 57 | `cbrd_26659_oos_storage_policy.sql` | 대상 | 초기 DROP `-581` | Fresh F14: golden·artifact PASS(1/1), cleanup 0; 원래 72-case·CI 진행 중 |

15개는 43–57번에 연속한다. 42번 chunk-boundaries와 58번 VOT-many-attributes는 통과했다. 뒤 14개는 초기 DDL부터 실패했으므로 연쇄 실패가 의심되지만, 이를 각 TC의 확정 원인으로 기록하지 않는다. 재실행 범위는 `sql/_36_guava` 전체 72개이며, 세 기존 실패 파일만의 실행이 아니다.

## Shell 실패 5개

모든 경로는 private repository 기준이다. 현재 다섯 항목은 모두 제외 규칙에 해당하므로 이번에 반드시 수리할 shell 잔여 항목은 없다.

| TC path | 수리 판정 | 근거와 미해결 상태 |
| --- | --- | --- |
| `shell/_37_elderberry/cbrd_23842_cdc/bug/cbrd_27064/cases/cbrd_27064.sh` | 제외: 기존 기준 실패 | 기존 TC 구성에서도 delete/update extractor `rc=-10` 관측; 부분 건수는 실행마다 다름 |
| `shell/_40_guava/cbrd_26659_partition_owner/cases/cbrd_26659_partition_owner.sh` | 제외: 기존 예상 실패 | Destination child ownership/descriptor 검증 실패 재현기 |
| `shell/_40_guava/cbrd_26659_snapshots_reclaim/cases/cbrd_26659_snapshots_reclaim.sh` | 제외: 기존 예상 실패 | Chunk drain 뒤 positive page return 미달; downstream churn 검증 미완료 |
| `shell/_40_guava/cbrd_26659_utility_sa_physical/cases/cbrd_26659_utility_sa_physical.sh` | 제외: 기존 예상 실패 | SA logical load와 별개로 destination OOS physical placement 미달 |
| `shell/_40_guava/cbrd_27237_rollback_vacuum/cases/cbrd_27237_rollback_vacuum.sh` | 제외: 기존 예상 실패 | Vacuum 뒤 rollback pre-image read에서 OOS metadata corruption 관측 |

## 합의된 완료 기준과 갱신 방법

SQL 14개 모두 새 DB의 독립 실행에서 정답과 비교해 통과하고, partition을 포함한 최신 CI의 원래 72-case 순서에서도 대상 14개가 통과해야 한다. 각 결과의 실제 로그, 정답 비교와 artifact verdict를 남긴다. 제외 항목의 실패는 별도로 기록하며, 대상 14개의 검증을 대체하지 않는다.

최종 CI는 개인 CUBRID PR 정책과 출발 핸드오프의 운영 경계를 따른다. Scoped 변경과 필요한 TC 변경을 게시한 뒤 CI를 한 번 실행하고, terminal 결과와 제외/잔여 실패를 보고한 뒤 다음 인간 지시를 기다린다. Engine 변경 시 `/run all`, Engine이 그대로인 TC 변경 시 유효성을 확인한 failure replay를 선택한다. CI에서 대상 실패가 남으면 수리 완료로 기록하지 않는다.

새 검증을 수행하면 해당 행의 상태를 갱신하면서 Engine/TC revision, 실행 조건, attempt/run 식별자, 실제 artifact verdict와 근거 위치를 함께 남긴다. 기존 관측은 run 식별자를 유지한다. 독립 실행 통과만으로 순서 실행의 실패를 해결했다고 기록하지 않으며, 제외 항목을 자동으로 해결 완료로 바꾸지 않는다. 새 실패는 먼저 두 제외 규칙의 근거를 확인한 뒤 표에 추가한다.

## 근거 문서와 retained artifacts

- [기존 예상 실패 5개와 passing selection](/home/vimkim/gh/my-cubrid-docs/cbrd-26659/ci-replan/delivery/14-complete-local-validation.md), 특히 `Five correct tracked candidates` 및 SQL selection 표.
- [Shell conversion의 retained candidate 상태](/home/vimkim/gh/my-cubrid-docs/cbrd-26659/ci-replan/shell-conversion-results-20261012.md).
- [Representation의 passing TC와 별도 target 재현기](/home/vimkim/gh/my-cubrid-docs/cbrd-26659/ci-replan/delivery/03-representation-chunks.md).
- [기존 CDC 증상 비교](/home/vimkim/gh/my-cubrid-docs/cbrd-26659/ci_analysis_report_a5da823_codex.md), `Existing CDC` 및 exact-base 비교. 최신 run과 역사적 비교를 혼동하지 않는다.
- 최신 receipt: `/home/vimkim/tmp/oos-ci-8128-controller-repair-20261012.8P6hTT/terminal-receipt.json`.
- 순서/assertion/reconnect: 같은 디렉터리의 `shard-sql-00.log`, 1015–1109행. Replay selection: `plan.log`, 740–743행 및 1036–1045행.
- Per-case artifacts: `/home/vimkim/.local/share/cubrid-ci-data/github-actions/CUBRID-cubrid/pr-8128/a5da823b2a84e95b4b22d48abe4a3f9fd601c176/providers/github-actions/runs/38245729674/attempts/1/`.

최종 수리의 path evidence, retained attempts, 14개 independent/ordered 결과와 CI receipt는 [수리 검증 기록](/home/vimkim/gh/my-cubrid-docs/cbrd-26659/ci-repair/repair-results.md)에 보존한다.

TC 옆 요약은 public checkout의 `sql/_36_guava/cbrd_26659/README.md`에 둔다. 이 문서가 전체 실패 목록과 근거를 관리하고, TC README는 합의된 범위와 탐색 위치를 안내한다.
