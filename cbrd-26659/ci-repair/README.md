# PR8128 testcase 수리 범위와 상태

범위 결정: 2026-10-12, work item 331. 마지막 갱신: 2026-10-13, Asia/Seoul. 실행 work item 332.
관련 PR: [Engine #8128](https://github.com/CUBRID/cubrid/pull/8128), [public TC #3688](https://github.com/CUBRID/cubrid-testcases/pull/3688), [private TC #4365](https://github.com/CUBRID/cubrid-testcases-private-ex/pull/4365).

이 문서는 실패 TC의 수리 대상 여부와 검증 상태를 추적한다. 사용자는 SQL와 shell의 실패 전체를 검토하고 아래 제외 규칙을 적용한 뒤 남는 SQL 14개를 모두 정상화하는 범위에 동의했다. **대상 14개는 수리·검증 완료**다. 최종 Engine `1ef86a7`의 fresh DB 독립 검증 14/14, 원래 72-case 순서 72/72와 [단일 CI run38271660063](https://github.com/CUBRID/cubrid/actions/runs/38271660063)의 대상 14개 JUnit PASS를 확인했다. 전체 CI는 shell 7 fail로 FAILURE다. 합의된 shell 제외 5개와 추가 관측 2개를 아래에 별도로 남기며, terminal 보고 뒤 추가 수리를 수행하지 않는다.

공유 이해는 2026-10-12에 최종 확인했다. 실행 절차와 완료 기준은 [합의된 수리 계획](plan.md)에 정리한다.

## 합의된 제외 규칙

1. `feature/oos-merge`의 기존 TC 구성에서 이미 관측된 동일 증상 실패는 이번 수리 대상에서 제외한다. 새 TC가 동일 Engine 소스에서도 실패한다는 이유만으로 자동 제외하지 않는다.
2. 이전 delivery에서 올바른 성공 기대를 유지한 채 알려진 결함의 재현기로 남긴 예상 실패 TC는 이번 수리 대상에서 제외한다.

이 규칙은 이번 수리 작업의 범위를 정한다. 제외된 결함은 미해결로 기록하고, 실행 생략이나 정답 변경은 별도 결정으로 다룬다. 정상적인 오류를 검증하는 SQL 문장은 passing testcase의 검증 조건이므로 제외 대상이 아니다.

원인 검증용 가설 패치를 허용한다. 최종 게시에는 올바른 정답과 assertion을 보존하고, 원인을 설명하는 경로 증거와 패치 전후 대조 실행을 확보한다. 모든 큐 연산의 추적을 의무화하지 않는다.

예상 실패인 partition 결함이 대상 SQL 14개의 연쇄 실패 원인으로 입증되면, 14개 정상화에 필요한 공통 원인 수리를 허용한다. Partition 자체의 모든 기존 결함을 해결할 의무로 범위를 넓히지 않으며, 다른 제외 항목의 수리는 기존 범위를 유지한다.

## 범위 합의에 사용한 역사적 실행과 리비전

- 합의 당시 최신 결과: [run38245729674, attempt 1](https://github.com/CUBRID/cubrid/actions/runs/38245729674). SQL 72개 중 57 pass / 15 fail, shell replay 8개 중 3 pass / 5 fail. Medium은 이전 통과 결과를 유지했고 이 run에서 재실행하지 않았다.
- Engine: `a5da823b2a84e95b4b22d48abe4a3f9fd601c176`.
- Public TC: `1a556a0752073aaad573bf87d53f3eb75f398138`. Private TC: `a2054f965a20241b87dc9577585ccc8a8cb6ab97`.
- 기존 기준 실행: [run36570256001, attempt 1](https://github.com/CUBRID/cubrid/actions/runs/36570256001), Engine `fb567a629cdb390fff920542173fa36f454c74a0`. 새 OOS TC는 이 실행의 기존 corpus에 없었다.
- 범위 합의 당시 `feature/oos-merge`와 PR8128의 `a5da823` Engine source tree는 동일했다. 이번 `1ef86a7`은 그 위에 입증된 replication guard 수리를 추가한다. Testcase 구성, 빌드 및 실행 조건의 동등성을 tree identity만으로 주장하지 않는다.

## 현재 terminal 검증

[Run38271660063, attempt 1](https://github.com/CUBRID/cubrid/actions/runs/38271660063)은 2026-10-13 02:32:56 KST에 FAILURE로 종료했다. Engine `1ef86a7efa34002e971b1b30bcf5d451e9db441b`, public TC `d7bec2fdeb6a19573300e1a624e03e0b87eb9e96`, private TC `a2054f965a20241b87dc9577585ccc8a8cb6ab97`이다. Release/Debug build는 SUCCESS이고 모든 suite shard의 build provenance는 같은 run/attempt의 Debug다.

| Suite | Planned | Run | Pass | Fail / error | Skip | Unrun |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| SQL | 17488 | 17488 | 17488 | 0 / 0 | 0 | 0 |
| Shell | 3307 | 3277 | 3270 | 7 / 0 | 30 | 0 |
| Medium | 975 | 975 | 975 | 0 / 0 | 0 | 0 |

대상 14개와 excluded full partition을 포함한 72개 identity는 CI shard09의 complete XML에 각각 정확히 한 번 있고 모두 PASS다. XML은 retained bundle의 `providers/github-actions/runs/38271660063/attempts/1/test_sql/raw/shards/09/linux_sql_64bit.xml`이다. Bundle root는 `/home/vimkim/.local/share/cubrid-ci-data/github-actions/CUBRID-cubrid/pr-8128/1ef86a7efa34002e971b1b30bcf5d451e9db441b`이다. Schema·identity·raw hash·counts 검증과 모든 per-case positive record는 `/home/vimkim/tmp/oos-sql-repair-332/validated-terminal.json`에 보존한다. Local/native와 CI runtime의 차이 및 원래 72개 실제 실행 순서 증거는 [수리 검증 기록](repair-results.md)에 둔다.

Public TC #3688와 private TC #4365는 OPEN draft다. **개인 정책의 TC Merge Gate는 미해제**이며 인간의 merge/close가 필요하다. Live checks에 해당 이름의 context는 없고 `--required`도 configured required checks를 보고하지 않았다. 이를 merge 허용으로 해석하지 않는다.

## 범위 합의 당시 SQL 실패 15개

모든 경로는 public repository의 `sql/_36_guava/cbrd_26659/cases/` 아래이다. 순서는 최신 72-case shard의 실제 실행 위치이다. 최신 관측 열은 역사적 run38245729674의 실패를 보존한다. 현재 검증의 identity·명령·결과는 [수리 검증 기록](repair-results.md)에 둔다. 아래 Fresh `F01`–`F14`는 `/home/vimkim/tmp/s332-final-01`–`14`이며 모두 Engine `1ef86a7efa34002e971b1b30bcf5d451e9db441b`, public TC `1dec9d147547d8d404b6705b742e6e6fa0a58b98`, native Debug/HA/JDBC와 동일 runner SHA를 사용한다. 각 `verify.log`, XML, copied `.result`와 `cleanup.exit`가 실제 근거다.

| 순서 | TC basename | 수리 판정 | 역사적 관측(run38245729674) | 현재 수리·검증 결과 |
| --- | --- | --- | --- | --- |
| 43 | `cbrd_26659_oos_partition.sql` | 제외: 기존 예상 실패 | Partition UPDATE `-21019`, `repl_log_insert`, `replication.c:468` assertion | 제외 유지; source DELETE의 OOS 큐 재소비 원인 입증 및 guard 수리. Local original partition 포함 4/4 pass; 최종 순서 43번 logical PASS(72/72); CI38271660063 shard09 JUnit PASS |
| 44 | `cbrd_26659_oos_partition_routing.sql` | 대상 | 초기 DROP `-581`; JDBC reconnect 실패 | Fresh F01: golden·artifact PASS(1/1), cleanup 0; 원래 72-case 위치 44–57: golden·artifact PASS(72/72), cleanup 0; CI38271660063 shard09 JUnit PASS |
| 45 | `cbrd_26659_oos_representation.sql` | 대상 | 초기 DROP `-581` | Fresh F02: golden·artifact PASS(1/1), cleanup 0; 원래 72-case 위치 44–57: golden·artifact PASS(72/72), cleanup 0; CI38271660063 shard09 JUnit PASS |
| 46 | `cbrd_26659_oos_schema.sql` | 대상 | 초기 DROP `-581` | Fresh F03: golden·artifact PASS(1/1), cleanup 0; 원래 72-case 위치 44–57: golden·artifact PASS(72/72), cleanup 0; CI38271660063 shard09 JUnit PASS |
| 47 | `cbrd_26659_oos_sql01_insert_select.sql` | 대상 | 초기 DROP `-581` | Fresh F04: golden·artifact PASS(1/1), cleanup 0; 원래 72-case 위치 44–57: golden·artifact PASS(72/72), cleanup 0; CI38271660063 shard09 JUnit PASS |
| 48 | `cbrd_26659_oos_sql04_delete.sql` | 대상 | 초기 DROP `-581` | Fresh F05: golden·artifact PASS(1/1), cleanup 0; 원래 72-case 위치 44–57: golden·artifact PASS(72/72), cleanup 0; CI38271660063 shard09 JUnit PASS |
| 49 | `cbrd_26659_oos_sql04_update.sql` | 대상 | 초기 DROP `-581` | Fresh F06: golden·artifact PASS(1/1), cleanup 0; 원래 72-case 위치 44–57: golden·artifact PASS(72/72), cleanup 0; CI38271660063 shard09 JUnit PASS |
| 50 | `cbrd_26659_oos_sql05_bigone.sql` | 대상 | 초기 DROP `-581` | Fresh F07: golden·artifact PASS(1/1), cleanup 0; 원래 72-case 위치 44–57: golden·artifact PASS(72/72), cleanup 0; CI38271660063 shard09 JUnit PASS |
| 51 | `cbrd_26659_oos_sql05_constraints.sql` | 대상 | 초기 DROP VIEW `-581` | Fresh F08: golden·artifact PASS(1/1), cleanup 0; 원래 72-case 위치 44–57: golden·artifact PASS(72/72), cleanup 0; CI38271660063 shard09 JUnit PASS |
| 52 | `cbrd_26659_oos_sql05_transactions.sql` | 대상 | `autocommit off` 후 초기 DROP `-581` | Fresh F09: golden·artifact PASS(1/1), cleanup 0; 원래 72-case 위치 44–57: golden·artifact PASS(72/72), cleanup 0; CI38271660063 shard09 JUnit PASS |
| 53 | `cbrd_26659_oos_sql06_triggers.sql` | 대상 | 초기 DROP `-581` | Fresh F10: golden·artifact PASS(1/1), cleanup 0; 원래 72-case 위치 44–57: golden·artifact PASS(72/72), cleanup 0; CI38271660063 shard09 JUnit PASS |
| 54 | `cbrd_26659_oos_sql07_read_paths.sql` | 대상 | 초기 DROP VIEW `-581` | Fresh F11: golden·artifact PASS(1/1), cleanup 0; 원래 72-case 위치 44–57: golden·artifact PASS(72/72), cleanup 0; CI38271660063 shard09 JUnit PASS |
| 55 | `cbrd_26659_oos_sql09_lob_copy.sql` | 대상 | 초기 DROP `-581` | Fresh F12: golden·artifact PASS(1/1), cleanup 0; 원래 72-case 위치 44–57: golden·artifact PASS(72/72), cleanup 0; CI38271660063 shard09 JUnit PASS |
| 56 | `cbrd_26659_oos_sql09_lob_maxcols.sql` | 대상 | 초기 DROP `-581` | Fresh F13: golden·artifact PASS(1/1), cleanup 0; 원래 72-case 위치 44–57: golden·artifact PASS(72/72), cleanup 0; CI38271660063 shard09 JUnit PASS |
| 57 | `cbrd_26659_oos_storage_policy.sql` | 대상 | 초기 DROP `-581` | Fresh F14: golden·artifact PASS(1/1), cleanup 0; 원래 72-case 위치 44–57: golden·artifact PASS(72/72), cleanup 0; CI38271660063 shard09 JUnit PASS |

15개는 43–57번에 연속한다. 42번 chunk-boundaries와 58번 VOT-many-attributes는 통과했다. 뒤 14개는 초기 DDL부터 실패했으므로 연쇄 실패가 의심되지만, 이를 각 TC의 확정 원인으로 기록하지 않는다. 재실행 범위는 `sql/_36_guava` 전체 72개이며, 세 기존 실패 파일만의 실행이 아니다.

## 합의된 Shell 제외 5개

모든 경로는 private repository 기준이다. 현재 다섯 항목은 모두 제외 규칙에 해당하므로 이번에 반드시 수리할 shell 잔여 항목은 없다.

| TC path | 수리 판정 | 역사적 근거와 미해결 상태 | 이번 run38271660063의 실제 관측 |
| --- | --- | --- | --- |
| `shell/_37_elderberry/cbrd_23842_cdc/bug/cbrd_27064/cases/cbrd_27064.sh` | 제외: 기존 기준 실패 | 기존 TC 구성에서도 delete/update extractor `rc=-10` 관측; 부분 건수는 실행마다 다름 | FAIL; delete 0/700, update 0/2400, extractor `rc=-10` |
| `shell/_40_guava/cbrd_26659_partition_owner/cases/cbrd_26659_partition_owner.sh` | 제외: 기존 예상 실패 | Destination child ownership/descriptor 검증 실패 재현기 | FAIL; destination ownership mismatch, retained CBRD-27089 |
| `shell/_40_guava/cbrd_26659_snapshots_reclaim/cases/cbrd_26659_snapshots_reclaim.sh` | 제외: 기존 예상 실패 | Chunk drain 뒤 positive page return 미달; downstream churn 검증 미완료 | FAIL; snapshot/reclaim controller exit 1; underlying 원인은 재진단하지 않음 |
| `shell/_40_guava/cbrd_26659_utility_sa_physical/cases/cbrd_26659_utility_sa_physical.sh` | 제외: 기존 예상 실패 | SA logical load와 별개로 destination OOS physical placement 미달 | FAIL; utility controller status 1; underlying 원인은 재진단하지 않음 |
| `shell/_40_guava/cbrd_27237_rollback_vacuum/cases/cbrd_27237_rollback_vacuum.sh` | 제외: 기존 예상 실패 | Vacuum 뒤 rollback pre-image read에서 OOS metadata corruption 관측 | FAIL; rollback-after-vacuum pre-image controller exit 1; underlying 원인은 재진단하지 않음 |

## Full CI에서 추가 관측한 shell 실패 2개

두 항목은 최신 failure replay의 5개 목록에 없었으며 이번 `/run all`에서 관측됐다. 기존 두 제외 규칙과 역사적 signature를 확인해 기록하되, 이번 SQL14 수리 범위를 넓히거나 정답·discovery를 변경하지 않는다.

| TC path | 이번 실제 관측 | 제외 규칙과 잔여 상태 |
| --- | --- | --- |
| `shell/_37_elderberry/cbrd_23842_cdc/bug/cbrd_27075/cases/cbrd_27075.sh` | Subcheck 1 NOK; 4K/8K `EXTRACT_ERR=1`, 16K 0, total corruption 0 | 기존 CDC 실패도 추가 관측됨. Base run36570256001의 subcheck 1 / extraction errors와 같은 종류이고 ADR-0005가 deferred gap으로 유지한다. 규칙 1의 기존 실패로 SQL14 필수 수리에서 제외하며 실행과 올바른 기대를 보존 |
| `shell/_06_issues/_17_1h/cbrd_20759/hide_cubrid_replay/cases/hide_cubrid_replay.sh` | Subcheck 6 NOK, `qa8.answer` mismatch | 추가 잔여 실패, 원인 미확정. Base run36570256001의 subcheck 7 / `qa9.answer`, 이전 full run38223008491의 `qa9`·`qa10`과 다르므로 동일 baseline 원인으로 제외하지 않음. Terminal 이후 다음 인간 지시까지 수리하지 않음 |

이전 base artifact와 현재 artifact의 비교는 `/home/vimkim/tmp/oos-sql-repair-332/additional-failure-comparison.json`에 보존한다. Base Engine은 `fb567a629cdb390fff920542173fa36f454c74a0`이고 현재 Engine은 `1ef86a7`이다. 개별 count 차이를 같은 값으로 표현하거나 서로 다른 signature를 확정 공통 원인으로 묶지 않는다. CDC의 실행 유지 정책은 [ADR-0005](/home/vimkim/gh/cubrid-oos-context/docs/adr/0005-defer-oos-history-from-the-11-5-merge.md:17)를 따른다.

## 합의된 완료 기준과 갱신 방법

SQL 14개 모두 새 DB의 독립 실행에서 정답과 비교해 통과하고, partition을 포함한 최신 CI의 원래 72-case 순서에서도 대상 14개가 통과해야 한다. 각 결과의 실제 로그, 정답 비교와 artifact verdict를 남긴다. 제외 항목의 실패는 별도로 기록하며, 대상 14개의 검증을 대체하지 않는다.

최종 CI는 개인 CUBRID PR 정책과 출발 핸드오프의 운영 경계를 따른다. Scoped 변경과 필요한 TC 변경을 게시한 뒤 CI를 한 번 실행하고, terminal 결과와 제외/잔여 실패를 보고한 뒤 다음 인간 지시를 기다린다. Engine 변경 시 `/run all`, Engine이 그대로인 TC 변경 시 유효성을 확인한 failure replay를 선택한다. CI에서 대상 실패가 남으면 수리 완료로 기록하지 않는다.

새 검증을 수행하면 해당 행의 상태를 갱신하면서 Engine/TC revision, 실행 조건, attempt/run 식별자, 실제 artifact verdict와 근거 위치를 함께 남긴다. 기존 관측은 run 식별자를 유지한다. 독립 실행 통과만으로 순서 실행의 실패를 해결했다고 기록하지 않으며, 제외 항목을 자동으로 해결 완료로 바꾸지 않는다. 새 실패는 먼저 두 제외 규칙의 근거를 확인한 뒤 표에 추가한다.

## 근거 문서와 retained artifacts

- [기존 예상 실패 5개와 passing selection](../ci-replan/delivery/14-complete-local-validation.md), 특히 `Five correct tracked candidates` 및 SQL selection 표.
- [Shell conversion의 retained candidate 상태](../ci-replan/shell-conversion-results-20261012.md).
- [Representation의 passing TC와 별도 target 재현기](../ci-replan/delivery/03-representation-chunks.md).
- [기존 CDC 증상 비교](../ci_analysis_report_a5da823_codex.md), `Existing CDC` 및 exact-base 비교. 최신 run과 역사적 비교를 혼동하지 않는다.
- 최신 receipt: `/home/vimkim/tmp/oos-ci-8128-controller-repair-20261012.8P6hTT/terminal-receipt.json`.
- 순서/assertion/reconnect: 같은 디렉터리의 `shard-sql-00.log`, 1015–1109행. Replay selection: `plan.log`, 740–743행 및 1036–1045행.
- Per-case artifacts: `/home/vimkim/.local/share/cubrid-ci-data/github-actions/CUBRID-cubrid/pr-8128/a5da823b2a84e95b4b22d48abe4a3f9fd601c176/providers/github-actions/runs/38245729674/attempts/1/`.

최종 수리의 path evidence, retained attempts, 14개 independent/ordered 결과와 CI receipt는 [수리 검증 기록](repair-results.md)에 보존한다.

TC 옆 요약은 public checkout의 `sql/_36_guava/cbrd_26659/README.md`에 둔다. 이 문서가 전체 실패 목록과 근거를 관리하고, TC README는 합의된 범위와 탐색 위치를 안내한다.
