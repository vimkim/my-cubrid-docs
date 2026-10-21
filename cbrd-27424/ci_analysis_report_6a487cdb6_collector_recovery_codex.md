# PR7925: recovered CI evidence and shell failure analysis

Date: 2026-10-17, Asia/Seoul. Work Items 397 and 393.
Revalidated and extended: 2026-10-21, Asia/Seoul, under Work Item 393.
PR: [CUBRID/cubrid #7925](https://github.com/CUBRID/cubrid/pull/7925).
Engine: `6a487cdb6cbda36ac94ad9b22009cea6cb58aa2f`.

## 2026-10-21 재분석: 왜 실패했나?

이번 재분석의 독자는 PR 작성자이며, 질문은 현재 공개된 소스의 shell CI 실패 원인과 다음 조사 순서입니다.
새 CI를 실행하지 않고 기존 run `38938588691`, attempt 1의 증거를 다시 수집·검증했습니다.
**실패를 발생시킨 검사 조건은 6건 모두 확인했습니다. 각 조건을 깨뜨린 엔진·실행 환경의 근본 원인은 아직 확정하지 못했습니다.**
이전에 기록한 수집기 오류는 이미 해결됐으며, 현재 실패 목록을 확인하지 못하는 이유가 아닙니다.

SQL은 17,471/17,471, medium은 975/975 통과했습니다.
Shell은 3,253건 통과, 6건 실패, 30건 건너뜀, 미실행 0건입니다.
아래 이름은 뒤의 [전체 경로와 job 링크가 있는 목록](#failure-inventory)에 대응하며, 각 행은 실패한 testcase 파일 하나입니다.

| Testcase | 직접 확인한 실패 조건 | 정확한 merge-base 실행과 비교 | 아직 확인할 원인 |
| --- | --- | --- | --- |
| `bug_bts_13242` | 잠금 수가 기대값에 도달하지 않아 3개 지점에서 각각 60회 대기를 소진하고, 정렬한 잠금 덤프가 answer와 달라짐 | 기준 실행은 통과, head에서 추가 실패 | 기대값을 초과하는 잠금의 소유자와 종류, 세션 종료·덤프 시점 |
| CDC `thread` | 서버를 종료하는 4번 검사에서 `result4.log`에 `API ERROR`가 1회 있음. 종료 성공 문구도 1회 있음 | 기준 실행은 통과, head에서 추가 실패 | 오류를 반환한 API 호출과 서버 종료 시점의 관계 |
| `bug_bts_14305` | 종료 요청은 성공했지만 대상 CSQL 출력에서 기대한 중단 메시지가 0회 검출됨 | 기준 실행은 통과, head에서 추가 실패 | 실제 종료한 트랜잭션과 배경 CSQL의 대응, 출력 내용 |
| `bug_bts_15156` | master 재시작 뒤 반복해 서버를 종료해도 성공 문구가 0회 검출됨 | 기준 실행에서도 같은 실패 조건 | 이미 종료된 서버인지, 실제 종료 오류인지, 출력 기대가 다른지 |
| `cbrd_27064` | DELETE·UPDATE CDC 추출이 `rc=-10`으로 끝나 목표 건수를 채우지 못함 | 기준 실행에서도 같은 반환 코드와 추출 부족 | 최초 실패한 요청·수신 단계와 서버 오류 |
| `cbrd_27075` | UPDATE 2,000회는 완료했으나 4K·8K·16K 모두 CDC 추출 오류가 있어 검사 실패 | 기준 실행에서도 세 설정 모두 추출 오류 | 각 probe의 반환 코드와 서버/API 로그 |

기준에도 있었던 3건, head에서 추가 관찰한 3건, 비교 불가 0건입니다.
별도로 기준에서만 실패한 2건은 head에서 통과했습니다. 이 두 건을 head 실패 수에 더하거나, 이번 PR이 고쳤다고 해석하지 않습니다.
현재 head와 기준의 비교 대상 8개 testcase `cases/` 디렉터리는 Git tree가 각각 같습니다.
이 비교는 입력 소스 차이를 배제하지만 호스트 부하, 실행 순서, 난수 payload까지 같았다는 증거는 아닙니다.

### 이번 변경이 원인인가?

최신 커밋 `6a487cdb6`의 제품 코드 변경은 `SA_MODE`로 감싼 17줄 삭제입니다.
나머지 변경은 저장행 비교 fixture의 CHN assertion 6줄입니다.
[커밋 diff](https://github.com/CUBRID/cubrid/commit/6a487cdb6cbda36ac94ad9b22009cea6cb58aa2f)는 서버 빌드의 해당 분기를 바꾸지 않습니다.
따라서 서버에서 관찰한 실패를 이 분기 삭제에 바로 귀속할 근거는 약합니다.
다만 일부 testcase는 준비·정리 때 standalone 명령도 사용하며, 전체 PR은 기준 대비 29개 파일의 heap·query·locator 변경을 포함합니다.
최신 커밋의 직접 영향이 약하다는 판단으로 전체 PR의 간접 영향을 배제할 수는 없습니다.

CDC `-10`은 정확한 소스에서 `CUBRID_LOG_FAILED_CONNECT`입니다.
이는 API 요청·응답 실패의 여러 경로에서 반환되므로, 이름만 보고 최초 연결 실패나 특정 overflow 손상으로 단정할 수 없습니다.
두 CDC testcase의 손상 문구 집계는 0이지만, 그것만으로 저장 무결성을 입증할 수도 없습니다.
해당 API 소스 파일들은 기준과 head 사이에서 바뀌지 않았습니다.

### 무엇부터 조사해야 하나?

1. **`bug_bts_13242`:** 현재 검사에서 기대한 잠금 수 6·8·9와 관찰한 수 8–9·12–14·15가 다른 세 지점의 전체 덤프를 확보합니다. 트랜잭션별 잠금 소유권과 배경 세션 종료 여부를 먼저 확인합니다. 대기 시간을 늘리는 것만으로 안정화됐다고 판단하지 않습니다.
2. **CDC `thread`:** `result4.log`, `finalize.log`, 서버 오류 로그에서 최초 실패 호출을 확인합니다. `API ERROR`는 driver의 setup·connect·find_lsa·finalize 분기 모두에서 출력될 수 있습니다. 현재 요약은 어느 호출인지 알려주지 않습니다. finalize 이전 오류라면 종료 경쟁이라는 가설은 기각해야 합니다.
3. **`bug_bts_14305`:** 이 테스트는 고정된 `kill 1`을 실행합니다. 성공 응답은 트랜잭션 하나를 종료했다는 증거이며, 배경 CSQL을 종료했다는 증거는 아닙니다. `result1.log`–`result3.log`와 실제 트랜잭션 식별자를 대조합니다. 올바른 대상을 종료한 뒤 다른 오류가 기록됐다면 대상 오인 가설을 기각해야 합니다.
4. **기준에도 있던 세 실패:** `server.log`·`service.log`, CDC driver와 서버/API 오류 로그를 확보해 별도 원인을 추적합니다. 이전에도 관찰됐다는 이유로 CI 실패를 면제하지 않습니다.

추가 세 건의 PR 연관성은 `unknown`, 엔진 근본 원인에 대한 확신은 낮습니다.
기준과 공유하는 세 건을 이 PR이 처음 도입했을 가능성은 `unlikely`, 확신은 중간입니다.
직접 실패 조건과 비교 분류에 대한 확신은 높습니다.
각 가설의 반증 조건과 필요한 로그는 뒤의 원인별 분석에도 보존했습니다.
이번 작업은 소스·testcase 수정, 로컬 재현, 추가 CI 실행을 포함하지 않습니다.

### Chronicle 이력: 기존 증상인가, flaky인가?

`cubrid-tcc 0.3.0`으로 전체 경로와 shell suite를 지정해 6건의 `status`, 현재 run의 `explain`, 전체 보존 이력의 `history`를 조회했습니다.
현재 run이 처음에는 index에 없어 run `38938588691`의 shell만 한 번 `sync-data --revisit-limit 0`으로 보강한 뒤 각 `status`·`explain`을 한 번 더 확인했습니다.
아래 이전 실패 수는 보존된 index에서 현재 실패보다 앞선 기록의 수입니다. 전체 CI의 발생 빈도가 아닙니다.

| Testcase | 현재 occurrence의 execution ID | 이전 실패 수 | 확인한 이력과 한계 |
| --- | ---: | ---: | --- |
| `bug_bts_13242` | 12343 | 3 | run `38513338343`, execution 4263에서도 정렬한 잠금 덤프 비교 실패. 당시 testcase 디렉터리는 현재와 달라, 같은 잠금 수·원인이라고 보지 않음 |
| CDC `thread` | 12344 | 0 | `UNKNOWN_HISTORY`. 이전 실패를 찾지 못한 것은 최초 발생의 증명이 아님 |
| `bug_bts_15156` | 12349 | 2 | run `38507861091`, execution 4070에서도 서버 종료 성공 문구 0회. testcase 디렉터리가 현재와 같음 |
| `bug_bts_14305` | 12353 | 3 | [PR #7971](https://github.com/CUBRID/cubrid/pull/7971)의 [run `38519453863`](https://github.com/CUBRID/cubrid/actions/runs/38519453863), execution 4699에서도 중단 메시지 0회·사용자 생성 성공·종료 응답 성공. testcase 디렉터리가 현재와 같음 |
| `cbrd_27064` | 12357 | 1 | 부모 소스 `b755678cd`, 같은 TC의 run `38861566581`, execution 8315에 실패 기록. 그 Chronicle snapshot에는 JUnit이 없어 이 경로로는 세부 증상을 비교하지 못함 |
| `cbrd_27075` | 12361 | 0 | `UNKNOWN_HISTORY`. 독립적으로 검증한 merge-base 실패는 위 비교에 남아 있음 |

**6건 모두 flakiness 평가는 `UNKNOWN`입니다.** 서로 다른 소스에서 통과와 실패가 섞였다는 이유로 flaky라고 분류하지 않습니다.
`14305`의 위 비교 실행은 2026-10-14의 PR #7971, `[CBRD-27433] Match queries that differ only in spacing or letter case`입니다.
PR 연결은 Chronicle의 `run_title` 메타데이터이며, GitHub의 해당 run 제목으로도 확인했습니다.
동일한 testcase 디렉터리와 실패 조건이 다른 PR에서 먼저 관찰됐으므로 PR #7925가 이 증상을 처음 도입했다고 보기는 어렵습니다.
그러나 현재 정확한 merge-base 실행은 통과했으며, 이번 PR이 재발 조건이나 발생 빈도에 영향을 줬는지는 아직 배제하지 않습니다.
이전 Engine `65a856ab…`의 Git object는 현재 소스 checkout에 없어 해당 Engine 코드와의 직접 비교는 수행하지 못했습니다.
현재 6개 occurrence는 Engine `6a487cdb6…`, private TC `a261508a…`, 전체 경로와 run이 일치합니다.
다만 Chronicle의 50개 shard snapshot은 partial이며 attempt·job 연결이 확정되지 않았습니다.
전체 discovery도 불완전하고 `status` freshness는 `STALE`입니다.
이 이력은 맥락 자료이며, 독립 검증한 `cubrid-ci` attempt 1의 결과나 정확한 기준 비교를 대체하지 않습니다.

읽어 비교한 이력의 정확한 입력은 다음과 같습니다. 실행 시간의 선후만 확인했으며, 이 Engine들이 현재 head의 Git 조상이라고 주장하지 않습니다.

| Execution | Engine SHA | Private TC SHA | hash 검증 후 읽은 증거 |
| --- | --- | --- | --- |
| 4263 | `2e6b863efc02c8433845f61a4836df0b8fcf67cf` | `e8cefadd76191deef30ac64afc6e588a2313fd63` | `test-results/test-shell.xml`, SHA-256 `dcc667e409cd54656c74892efcdca53231359fa26b0e69001cc0577ab955658b` |
| 4699 | `65a856ab12cc9ad760298d7e46bc5940237426bb` | `3c71be06b2e9abc1b45e8928a4aa1119cdc1b9f2` | `test-results/test-shell.xml`, SHA-256 `26b98849f8462db51d00b167eccd05c2c5eac30be52f9f5559eed90d77b61acc` |
| 4070 | `254a60fb68e4e5b6c0d323c034735aaba6f6a79f` | `43c14d88a7b90c1a686ed2917e4b5904d77a1c72` | `test-results/test-shell.xml`, SHA-256 `798e17badd3a9ba7705cb90606d94c36b0b35b81b07672f1396de89b1fa5aebf` |
| 8315 | `b755678cd9a3ab465215228d5664f7f1edf24846` | `a261508a624efc7115ac181073d40bca7fc9448c` | retained file inventory. JUnit 없음, 세부 증상 미확인 |

### 이번 재검증의 증거 범위

`cubrid-ci 0.2.0 (9536bd3c2867, release)`의 doctor가 통과했습니다.
Status 한 번, exact-head collection 한 번, exact merge-base collection 한 번을 실행했습니다. 대기 옵션이나 binary 수집은 사용하지 않았습니다.
Head와 기준 모두 collection exit 0이며, red shell suite도 완전하게 수집됐습니다.

| 항목 | Head | 정확한 merge base |
| --- | --- | --- |
| Engine | `6a487cdb6cbda36ac94ad9b22009cea6cb58aa2f` | `fb567a629cdb390fff920542173fa36f454c74a0` |
| Run / attempt | `38938588691` / 1 | `36570256001` / 1 |
| Observation | `20261021T114900.425646002Z-40875-0` | `20261021T114935.562832972Z-43237-0` |
| Collection 완료 UTC | `2026-10-21T11:49:01.291002979Z` | `2026-10-21T11:49:35.883464171Z` |
| 검증한 raw 파일 수 | 786 | 780 |

기준 관계는 `2026-10-21T11:49:32.305564702Z`에 조회했으며, 당시 target `feature/oos-merge`의 tip도 `fb567a629…`입니다.
두 bundle의 schema, 유일하게 일치하는 request/result observation, SHA-256·파일 길이, 61개 shard별 JUnit·할당·runner 결과, failure metadata·메시지·diff, Engine·TC provenance를 독립 검증했습니다.
Report-mode gate는 `full`, 비교 범위는 `validated_cases_only`입니다. 이는 인과관계의 증명이 아닙니다.
Private/public TC 및 CTP의 정확한 SHA와 환경 차이는 아래 기존 분석의 표와 같습니다.
사용하지 않은 binary budget은 각각 512 MiB 전액이며, archive를 읽지 않았다는 것은 archive 부재의 증거가 아닙니다.

이번 receipt는 `/mnt/nvme/data-5/tmp/pr7925-ci-analysis.7MV2Qb`에 있습니다.
`status.json`, `result.json`, `base-result.json`, `head-validation.json`, `base-validation.json`, `assessment.json`, `report-mode.json`, `comparison.json`이 현재 CI 검증을 기록합니다.
`history-summary.json`, `history-source-comparison.json`, `*-status-refreshed.json`, `*-explain-refreshed.json`, `*-history.json`, `history-refresh.json`, `history-coverage-selected.json`, `history-evidence-*.json`, `history-*.xml`, `history-*-message.txt`가 이력 조회와 hash 검증한 원문을 기록합니다.
이 파일들은 도구가 소유한 증거 및 외부 임시 경로에 보존하며 문서 Git에는 넣지 않습니다.
공개 TC PR3679와 비공개 TC PR4360은 이번 조회에서도 모두 OPEN이며, head는 각각 `26f964b8…`, `a261508a…`로 CI 입력과 같습니다.
TC Merge Gate의 사람에 의한 병합·종료 처분은 남아 있으며, 이번 분석으로 해소되지 않습니다.
아래 2026-10-17 분석과 당시 절차·브랜치 상태는 역사적 기록으로 유지합니다.

## Result and decision boundary

The repaired collector validates all three suites from existing [run 38938588691](https://github.com/CUBRID/cubrid/actions/runs/38938588691), attempt 1.
Medium passes 975 cases. SQL passes 17,471 cases.
Shell records 3,253 passes, six failures, 30 skips, and zero unrun cases.
Each failed shell job corresponds to one failed testcase file.

The exact merge-base baseline also validates.
Three head failure signatures also occur on that baseline.
Three additional head failures have passing baseline records with identical testcase directories.
Two baseline failures have passing head records.
These comparisons establish observed differences. They do not establish that PR7925 caused those differences.

This report resolves the testcase evidence limit in the [earlier warning](ci_analysis_report_6a487cdb6_codex.md).
That warning remains an accurate record of the original incomplete observation.
The [accepted preservation decision](sa-inline-preservation-decision-20261017.md) retains its separate local verification scope.
The historical [b755678cd report](ci_analysis_report_b755678cd_run38861566581_codex.md) supplies context for another engine revision.

## Validated suite inventory

All head suites identify run `38938588691`, attempt `1`, and debug build `6a487cdb6…` from that execution.
Both release and debug build statuses are successful.

| Head suite | Collection state | CI verdict | Planned | Executed | Passed | Failed | Errors | Skipped | Unrun |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `test_medium` | completed | success | 975 | 975 | 975 | 0 | 0 | 0 | 0 |
| `test_sql` | completed | success | 17,471 | 17,471 | 17,471 | 0 | 0 | 0 | 0 |
| `test_shell` | completed | failure | 3,289 | 3,259 | 3,253 | 6 | 0 | 30 | 0 |

The shell acquisition covers all 50 shards. SQL covers ten shards. Medium covers one shard.
All 61 shard response sets are retained and validated.
The shell failures are testcase failures with reconciled records, rather than jobs without usable testcase evidence.

### Failure inventory

All rows belong to `test_shell`, and each row represents one failed testcase file.
Subchecks within a file do not increase the suite failure count.
Message line references below use each failure record's `message_path`.
Confidence is high for the observed signature and baseline classification. Confidence is low for an underlying engine cause.

| Shard and job | Full testcase path | Observed signature | Baseline classification | Category | PR relation |
| --- | --- | --- | --- | --- | --- |
| [30](https://github.com/CUBRID/cubrid/actions/runs/38938588691/job/117103553048) | `shell/_06_issues/_14_1h/bug_bts_13242/cases/bug_bts_13242.sh` | Sorted lock snapshot differs. Three polling loops reach their limit. | `additional_on_head` | Lock snapshot expectation | unknown |
| [31](https://github.com/CUBRID/cubrid/actions/runs/38938588691/job/117103552750) | `shell/_37_elderberry/cbrd_23842_cdc/thread/cases/thread.sh` | Subcheck 4 counts one `API ERROR` during server shutdown. | `additional_on_head` | CDC lifecycle | unknown |
| [36](https://github.com/CUBRID/cubrid/actions/runs/38938588691/job/117103552509) | `shell/_06_issues/_15_1h/bug_bts_15156/cases/bug_bts_15156.sh` | Server-stop success count remains zero after retries. | `also_observed_on_base` | Service lifecycle | unlikely |
| [40](https://github.com/CUBRID/cubrid/actions/runs/38938588691/job/117103552653) | `shell/_06_issues/_18_1h/bug_bts_14305/cases/bug_bts_14305.sh` | No expected interruption diagnostic. User creation and transaction-kill subchecks pass. | `additional_on_head` | Transaction interruption | unknown |
| [44](https://github.com/CUBRID/cubrid/actions/runs/38938588691/job/117103552843) | `shell/_37_elderberry/cbrd_23842_cdc/bug/cbrd_27064/cases/cbrd_27064.sh` | CDC extraction returns `rc=-10` for DELETE and UPDATE. Corruption count is zero. | `also_observed_on_base` | CDC extraction | unlikely |
| [48](https://github.com/CUBRID/cubrid/actions/runs/38938588691/job/117103552752) | `shell/_37_elderberry/cbrd_23842_cdc/bug/cbrd_27075/cases/cbrd_27075.sh` | Extraction errors across 4K, 8K, and 16K configurations. Workloads complete without counted corruption. | `also_observed_on_base` | CDC extraction | unlikely |

PR relation describes introduction of the observed signature. It does not exclude another defect or a change in failure frequency.
The baseline comparison supports six head classifications: three shared, three additional, and zero uncomparable cases.
It separately identifies two `base_only` cases.
All six head failures remain unresolved CI results.

## Collector repair and evidence validation

Collector source commit: `9536bd3c2867` in `vimkim/cubrid-ci`.
Installed version: `cubrid-ci 0.2.0 (9536bd3c2867, release)`.
The source change remains on task branch `fix/pr7925-marker-contract` pending local merge approval.

The producing [workflow at f8ae0f47](https://github.com/CUBRID/cubrid/blob/f8ae0f47b729aa27043a4c421d200c4c7403262c/.github/workflows/gha-ci.yml#L1235) captures the test command's exit status.
Its publication step writes that status as `test_rc` in `shard.done`.
The retained head markers contain 55 zero statuses and six statuses of 1.
The old parser requires `ctp_rc` and rejects every head shard before testcase reconciliation.

The repair accepts `test_rc` and the legacy `ctp_rc` alias.
Conflicting aliases, duplicate fields, malformed statuses, and inconsistent shard identities fail validation.
Status 1 permits collection only when the shard reports failed testcases.
Other nonzero statuses remain job-level failures.
Assigned counts, workflow counts, JUnit counts, failed-case identities, and suite verdicts must still reconcile before summary publication.
An exit status alone never establishes a pass.

Unchanged medium and shell markers reproduce the original parser failure in regression tests.
CLI regressions cover a complete red suite, immutable replay, unexplained status 1, and contradictory JUnit counts.
`just verify` passes 108 tests, formatting, compilation, and Clippy.
The first full run has one transient identity-fixture exit-code failure.
That test passes in isolation and during the complete rerun. Its transient cause remains unknown.
`just install` succeeds, and `cubrid-ci doctor --json` passes.

One delegated status snapshot and one exact-head collection ran for this analysis.
Head collection exits 0 at `2026-10-16T18:55:28.194883816Z`.
Observation: `20261016T185520.879050049Z-2531350-0`.
No new engine CI run occurs.

The independent validator validates the command, manifest, request, terminal observation, summaries, failure metadata, and raw indexes against their JSON schemas.
It requires the unique terminal observation whose command equals the saved result, including collection time.
Request v1 contains repository, commit, suites, and collection options. The matching terminal command binds its PR identity.
The validator also validates all 786 indexed raw file lengths and SHA-256 digests.
It independently recounts each shard's JUnit records and compares assignment, workflow, inventory, and summary counts.
All 61 build and testcase provenance records reconcile.

All 788 original provider and observation files retain their original SHA-256 digests.
The original incomplete observation remains unchanged.
The evidence root's current manifest now identifies the new complete observation.
The earlier manifest copy remains in the external validation receipts.

Neither collection requests binary artifacts. Binary consumption is zero, with the full configured budget remaining.
This option excludes archives from the analysis. It does not establish that the provider has no archives.
The report-mode gate returns `full`, with comparisons restricted to validated cases.
Its permission does not establish causality.

## Exact merge-base comparison

The baseline command independently pins PR7925 and its actual target branch.
Target tip and unique merge base both equal `fb567a629cdb390fff920542173fa36f454c74a0`.
The pinned head remains `6a487cdb6cbda36ac94ad9b22009cea6cb58aa2f`.
Relationship observation time: `2026-10-16T18:56:10.884439668Z`.

Discovery covers all paginated exact-commit statuses and GitHub Actions `check-runs` records.
It performs no repository-wide workflow scan.
All three baseline suites select existing [run 36570256001](https://github.com/CUBRID/cubrid/actions/runs/36570256001), attempt 1.
Their consumed debug build comes from run `36570061594`, attempt `1`, at the exact merge-base Engine SHA.
The workflow title mentions PR7990. The per-shard build provenance establishes the tested Engine identity.

Baseline collection exits 0 at `2026-10-16T18:57:09.216984870Z`.
Observation: `20261016T185707.991035730Z-2540136-0`.
Independent validation validates schema v3, observation v2, all suite records, and 780 indexed raw file digests.

| Baseline suite | Collection state | CI verdict | Planned | Executed | Passed | Failed | Errors | Skipped | Unrun |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `test_medium` | completed | success | 975 | 975 | 975 | 0 | 0 | 0 | 0 |
| `test_sql` | completed | success | 17,471 | 17,471 | 17,471 | 0 | 0 | 0 | 0 |
| `test_shell` | completed | failure | 3,289 | 3,259 | 3,254 | 5 | 0 | 30 | 0 |

### Input revisions and comparison limits

| Input | Head | Baseline |
| --- | --- | --- |
| Public TC SHA | `26f964b8a6e222c33765fa317eaaf4fe666d5f44` | `bdba62aee0faec05abdd861518824c69b6c1b3c5` |
| Private TC SHA | `a261508a624efc7115ac181073d40bca7fc9448c` | `c4b9d482fbd491a68510b2552df2c3cac91911fc` |
| TC branch | `tc/pr-7925` | `tc/pr-7990` |
| CTP SHA | `44e3f97c788ad82091d5b66d728852f3279b1e86` | `4d0043a7b149b3fc5d3ccb2e08c98cf8d77b34fb` |
| Build mode | debug | debug |

The validator reads all compared testcase files from the recorded local Git objects.
Git tree identities match for all eight affected `cases/` directories.
This validation covers each directory's scripts, C drivers, answers, and fixtures.
It does not establish whole-repository equality.

The [CTP comparison](https://github.com/CUBRID/cubrid-testtools/compare/4d0043a7b149b3fc5d3ccb2e08c98cf8d77b34fb...44e3f97c788ad82091d5b66d728852f3279b1e86) contains one commit and one changed file: `CTP/common/script/util_compat_test.sh`.
That change modifies CCI compatibility setup. The compared testcase scripts do not call its changed functions.
The shell initialization source is unchanged in that comparison.
The evidence does not establish image digest equality, equal host load, or equal dynamic process scheduling.
Random payloads in the CDC cases also differ between executions.
The comparison therefore identifies signatures and candidate differences, with causal attribution still open.

The two baseline-only failures are:

- `shell/_06_issues/_17_1h/cbrd_20759/hide_cubrid_replay/cases/hide_cubrid_replay.sh`: subcheck 7 reports a result-file difference on base. Head records a pass.
- `shell/_40_guava/cbrd_26349/cases/cbrd_26349.sh`: subchecks 2 and 3 report remote-column/password diagnostics on base. Head records a pass.

Their passing head records establish absence of those observed baseline failures in this run.
They do not establish that PR7925 repairs either underlying problem.

## Failure mechanisms and remaining unknowns

### Lock snapshot: bug_bts_13242

**Observed:** The testcase compares a sorted lock dump with `issue_13242.answer`.
Its source polls for an exact number of locked objects before each snapshot.
Test points 1, 5, and 6 each exhaust 60 polls.
Their expected counts are 6, 8, and 9. Observed counts are respectively 8–9, 12–14, and 15.
The final comparison fails. The baseline runs the identical testcase directory and passes.
Evidence: head message lines 521–2386 and testcase lines 23–39, 52–60, and 101–102.

**Inference:** Lock state or expected lock counts differ under this execution.
The polling limits explain why the test proceeds with snapshots that fail its expectation.
This evidence does not identify the reason for the additional locks.

**Unknown:** The retained text does not establish which transactions own every additional lock or whether timing changes the result.
The complete PR includes shared heap/query changes across 29 files.
The latest commit alone deletes an SA-only block, which does not establish a cause for this server-mode test.
PR relation remains unknown. Causal confidence is low.

**Falsifier:** Repeated controlled runs that reach the expected lock counts and still produce the same difference would reject the polling explanation.
**Next action:** Preserve complete lock dumps for all six points and compare transaction ownership under matched engine and runtime inputs.

### Service lifecycle: bug_bts_15156

**Observed:** The test kills the master, restarts services, and retries server stop.
Both head and base report a successful master-start predicate and one master process.
Both report zero matching server-stop success lines after the retry loop.
The final predicate writes NOK in both runs.
Evidence: head and base message lines 343–357, and testcase lines 63–91.

**Inference:** The repeated failure signature predates this PR head.
Its immediate cause is the server-stop predicate. An engine defect, an already stopped server, and an output expectation remain alternatives.
Introduction by PR7925 is unlikely, with medium confidence.

**Unknown:** The failure message does not include the contents of redirected `server.log` and `service.log`.
**Falsifier:** Those files could show a different operational failure despite the matching predicate.
**Next action:** Retain both redirected files and inspect server state before changing the test or engine.

### CDC lifecycle: thread

**Observed:** Only subcheck 4 fails. It stops the server while the C driver executes its finalization scenario.
The shell trace counts one `API ERROR` and one success line in `result4.log`.
The failure follows directly from the required zero-error predicate.
The identical baseline testcase passes.
Evidence: head message lines 424–431, testcase lines 156–186, and `test.c` lines 77–112.

**Inference:** The shutdown scenario encounters an API error. A finalization race is plausible.
The driver also has earlier API error branches, so the exact failing call remains unknown.
PR relation remains unknown. Causal confidence is low.

**Unknown:** The retained failure body omits the contents of `result4.log` and `finalize.log`.
**Falsifier:** `result4.log` could identify a connection or setup failure before finalization.
**Next action:** Retain those files and correlate the API call with server-stop timing.

### Transaction interruption: bug_bts_14305

**Observed:** Subcheck 1 searches `result1.log` for three expected interruption messages and finds zero matches.
The background CSQL process exits. User creation and the transaction-kill acknowledgement both pass.
The identical baseline testcase passes all predicates.
Evidence: head message lines 193–219 and testcase lines 39–57.

**Inference:** The failure concerns the interrupted client's observable output.
A diagnostic change, a timing difference, and an interruption defect remain possible.
PR relation remains unknown. Causal confidence is low.

**Unknown:** The retained failure body does not contain `result1.log`.
**Falsifier:** That file could show normal completion before the kill, rejecting a diagnostic-change explanation.
**Next action:** Retain all three result files and correlate the killed transaction with the background client.

### CDC extraction: cbrd_27064 and cbrd_27075

**Observed:** `cbrd_27064` passes its INSERT subcheck and fails DELETE and UPDATE extraction.
Head DELETE extraction returns `rc=-10` after 22 of 700 target rows. Base returns the same code after 23 rows.
Both runs return `rc=-10` before extracting any of 2,400 target UPDATE rows.
Both count zero page-corruption messages.
Evidence: head and base message lines 4–26, and the `cbrd_27064` C driver lines 111–120.

The exact [Engine API header](https://github.com/CUBRID/cubrid/blob/6a487cdb6cbda36ac94ad9b22009cea6cb58aa2f/src/api/cubrid_log.h#L55) defines `-10` as `CUBRID_LOG_FAILED_CONNECT`.
The API implementation maps multiple request, receive, and protocol failures to that code.
It does not identify one transport failure or prove page corruption.
The API source files are unchanged between the pinned merge base and head.

`cbrd_27075` completes 2,000 updates for each page size, with zero counted corruption and zero find errors.
Head extraction error counts are 2, 2, and 1 for 4K, 8K, and 16K pages.
Base reports four extraction errors for each page size.
Both runs fail all three configuration predicates because extraction errors must be zero.
Evidence: head and base message lines 4–13, and the `cbrd_27075` shell script lines 145–185.

**Inference:** Both CDC signatures predate this PR head.
The available evidence supports extraction/API failures. It does not establish the historical corruption mechanism described in the testcase comments.
Introduction by PR7925 is unlikely, with medium confidence.

**Unknown:** The retained text omits detailed per-probe driver logs and the underlying API/server error files.
Zero counted corruption messages do not prove storage integrity.
The two testcase files need not share one underlying cause.
**Falsifier:** Detailed traces could identify different failing API stages despite the matching aggregate signatures.
**Next action:** Retain driver and server error logs and identify the first failed request before changing overflow handling.

## Actions and remaining gates

1. Review and integrate the collector repair and this report through the user's local merge workflow.
2. Investigate the three additional head failures with the missing result files and controlled runtime inputs.
3. Keep the three shared signatures visible as separate follow-up work. Their baseline presence does not waive CI requirements.
4. Obtain separate direction before any engine repair, source push, or further engine CI cycle.
5. Resolve actual PR7927 integration, combined acceptance, and human testcase PR disposition under Work Item 393.

The collector and report work does not complete Work Item 393.
No engine or testcase source changes, PR comments, testcase merges, or CI triggers occur during this analysis.
The unrelated `cubrid-cci/win/cci_version.h` change remains intact.

## Evidence inventory and reproduction

Head evidence root:

```text
/home/vimkim/.local/share/cubrid-ci-data/github-actions/CUBRID-cubrid/pr-7925/6a487cdb6cbda36ac94ad9b22009cea6cb58aa2f
```

Baseline evidence root:

```text
/home/vimkim/.local/share/cubrid-ci-data/github-actions/CUBRID-cubrid/commits/fb567a629cdb390fff920542173fa36f454c74a0
```

Each root contains its matching `observations/<observation-id>/request.json` and `result.json`.
Suite summaries reside under `providers/github-actions/runs/<run>/attempts/1/<suite>/summary.json`.
Each summary names its failure metadata, message, optional extracted difference, and raw shard files.
The raw index binds the summary digest and every retained raw file digest.
Five head extracted difference files contain NOK markers without substantive output differences.
Their extraction status alone does not establish an expected-versus-actual comparison.
The lock testcase's difference file contains its actual sorted comparison.

External receipts:

```text
/mnt/nvme/data-5/tmp/pr7925-collector-20261017.8xAfQE
  status.json, doctor.json, head-result.json, base-result.json
  head-validation.json, base-validation.json, validate-collection.py
  comparison.json, comparison-coverage.json, testcase-equality.json
  original-manifest.json, original-evidence-sha256.json, preservation-validation.json
  assessment.json, report-mode.json, ctp-comparison.json, lock-polling.json
  producer-gha-ci.yml, testcase-source/, verify.log, install.log
```

These receipts and raw logs remain outside repository commits.
The earlier warning identifies the original observation and its independent API receipts.
The commands below describe the completed retrieval. A new invocation creates another collection observation.

```sh
cubrid-ci status https://github.com/CUBRID/cubrid/pull/7925 --json
cubrid-ci collect https://github.com/CUBRID/cubrid/pull/7925 \
  --commit 6a487cdb6cbda36ac94ad9b22009cea6cb58aa2f --json
cubrid-ci collect-base https://github.com/CUBRID/cubrid/pull/7925 --json
```

Exact testcase source uses `git show <recorded-tc-sha>:<full-testcase-path>` in the local testcase repository.
The validator script requires `/usr/bin/python3`, which provides the installed `jsonschema` module.
