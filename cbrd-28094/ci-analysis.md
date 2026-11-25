# CBRD-28094 PR #8734 CI analysis (warning report)

> **이 스냅샷으로는 회귀(regression) 여부나 근본 원인을 결론 내릴 수 없습니다.**
> `cubrid-ci` 가 `test_sql` 증거를 무결성 오류로 검증하지 못했고(`observation: incomplete`),
> merge-base 기준 결과도 없습니다(`baseline: unavailable`). 아래 내용은 관찰과 제한된 추론입니다.

## 요약

- 대상: [CUBRID/cubrid#8734](https://github.com/CUBRID/cubrid/pull/8734), head `f64df11ae676aa2b840b8a996e7d87c810763789`, merge base `bfb59bdd133518da140f9af6c48bef5568df67af` (`develop`).
- `gha-ci` run [45567269730](https://github.com/CUBRID/cubrid/actions/runs/45567269730) attempt 1에서 `test_sql` 이 실패했습니다. shard 09의 3개 testcase가 `unexpected result` 입니다.
- 같은 merge base를 쓰는 관련 없는 PR 2개(#8735, #8736)도 같은 3개 testcase에서 **바이트 단위로 같은** 실패 메시지를 냅니다(TC SHA URL만 정규화). 이 PR의 변경은 디버그 로그 메시지만 바꿉니다.
- 추론(검증 안 됨): 이 실패는 이 PR이 아니라 현재 `develop` 엔진과 TC `develop` 의 answer 사이 불일치에서 온 것으로 보입니다. PR relation: `unlikely`, confidence: medium.
- 분석 범위: `test_sql` 만. `test_sql_by_cci` 는 사용자 요청으로 제외했고, `test_shell` 은 관찰 시점에 아직 실행 중이었습니다.

## 관찰 범위

| 항목 | 값 |
| --- | --- |
| 관찰 시각 (UTC) | 2026-11-25T10:51 (head), 10:58 (baseline 시도) |
| Collector | `cubrid-ci 0.2.0 (00205d576de0, release)` |
| Head collection | exit 4, `collection_failed` (`kind: integrity`) |
| `verify` assessment | `identity: established`, `observation: incomplete`, `manifest: validated`, `requested_summaries: none` |
| Report mode | `warning`, `regression_conclusions_allowed: false` |
| Baseline (`collect-base`) | exit 3, `test_sql: not_observed` → `baseline: unavailable` |
| Testcase revision | `tc/pr-8734` `0175561299c1dfe3c14fde0e57ec25342a23df3b` (TC `develop` `7e99b9007d` + init commit) |
| Shard 09 build | `sha=f64df11ae6`, `mode=debug`, `ns=pr` |

## Suite 상태 (2026-11-25T10:51Z)

| Context | 상태 | 비고 |
| --- | --- | --- |
| `gha-ci: build (release)` | pass | |
| `gha-ci: build (debug)` | pass | |
| `gha-ci: test_medium` | pass | |
| `gha-ci: test_sql` | **fail** | shard 09: 571건 중 568 성공, 3 실패 (`summary_info`) |
| `gha-ci: test_shell` | pending | 분석 범위 밖 |
| `gha-ci: test_sql_by_cci` | fail | 사용자 요청으로 제외 (required 아님) |
| `Check TC PRs` | fail | TC merge gate. TC PR이 열려 있어서 생긴 실패이며, 마지막 merge handoff에서 처리합니다. |

## 진단 (collector)

`test_sql` 증거 검증이 다음 오류로 실패했습니다.

> result identity mismatch: shard 01 JUnit omits 19 testcases that summary_info reports (summary_info 3557/0/0, JUnit 3538/0/0 passed/failed/skipped)

빠진 19건은 모두 `sql/_05_plcsql/_01_testspec/_05_bug_fix/` 아래 testcase입니다. shard 01은 실패 0건으로 보고되므로 실패 판정에는 영향이 없을 가능성이 높지만, collector는 이 suite 전체를 검증되지 않은 증거로 처리합니다. #8735와 #8736의 수집도 **같은 메시지**로 실패합니다. 따라서 이 불일치는 PR 변경이 아니라 CI 보고 경로나 TC 구성에서 오는 것으로 보입니다(추론).

## 실패 목록 (검증되지 않은 raw 증거)

출처: 보존된 `raw/collect/failed.list` 와 shard 09 JUnit `linux_sql_64bit_optdebug.xml`.

| Testcase | 증상 | #8735 / #8736 | Known issue | History | PR relation |
| --- | --- | --- | --- | --- | --- |
| `sql/_36_guava/cbrd_27748/cases/cbrd_27748.sql` | plan에서 `temp(sort limit)` 이 사라지고 `/* ---> skip ORDER BY */` 가 추가됨 | 같은 메시지 | 기록 없음 | 기록 없음 | `unlikely` |
| `sql/_36_guava/cbrd_28121/cases/cbrd_28121.sql` | `show trace` 에서 `skip order by: true` 줄이 빠짐 | 같은 메시지 | 기록 없음 | 기록 없음 | `unlikely` |
| `sql/_36_guava/cbrd_26795/cases/cbrd_26795.sql` | `show trace` 의 `px_wide_t` heap scan 줄에 `(oos time: ?, fetch: ?, ioread: ?)` 가 추가됨 | 같은 메시지 | 기록 없음 | 2026-10-27까지 39회 PASS. 현재 실패는 색인되지 않음 | `unlikely` |

- Known issue: `cubrid-tcr show` 결과 세 testcase 모두 issue, rule, signature가 없습니다. 실패 요약이 검증되지 않아 `cubrid-tcr check --ci-attempt` 는 실행할 수 없었습니다.
- History: `cubrid-tcc 0.3.0`. `sync-data --run 45567269730` 은 성공했지만 `history` 는 `UNKNOWN_HISTORY`, `target_failure_not_indexed` 를 반환했습니다. 색인은 2026-10-27 이후 데이터가 없습니다.

## 추론과 반증 조건

**원인 후보: `develop` 엔진과 TC `develop` answer 불일치** (관찰 + 추론)

- 관찰: 세 testcase 모두 최근 TC `develop` 에서 바뀌었고, 세 변경 모두 `tc/pr-8734` 에 들어 있습니다.
  - `cbrd_28121`: `67c5593fe` (2026-11-23)
  - `cbrd_27748`: `98b4755b9` (2026-11-23)
  - `cbrd_26795`: `313d208b8` (2026-11-25)
- 관찰: 엔진 `develop` tip `bfb59bdd13` (2026-11-25)은 [CBRD-28111] ORDER BY LIMIT 계획 선택을 바꿉니다. `cbrd_27748` 과 `cbrd_28121` 의 차이는 ORDER BY 생략 여부입니다. `cbrd_26795` 의 차이는 OOS trace 출력입니다.
- 관찰: PR #8734의 diff는 디버그 로그 포맷 문자열과 인자만 바꿉니다. optimizer, plan 출력, trace 출력 코드는 바꾸지 않습니다.
- 추론: 엔진 변경과 TC answer 갱신의 시점이 어긋나서 `develop` 기준 모든 PR에서 같은 실패가 나는 것으로 보입니다.
- 반증 조건: merge base `bfb59bdd13` 의 `develop` 실행에서 세 testcase가 통과하거나, 이 PR을 뺀 같은 base의 다른 PR이 같은 TC SHA에서 통과하면 이 추론은 틀립니다.
- 모르는 것: `develop` push 실행 결과(현재 `not_observed`), 어느 쪽(엔진 또는 answer)을 고쳐야 하는지, shard 01 JUnit 누락의 원인.

## 다음 조치

1. `test_shell` 결과를 기다립니다.
2. 세 testcase 실패를 이 PR과 무관한 `develop` 공통 실패로 보고, 해당 TC/엔진 담당자(CBRD-28111, CBRD-27748, CBRD-26795 / CBRD-28121)에게 알리거나 새 이슈로 등록할지 결정합니다.
3. `develop` 쪽 수정이 들어온 뒤 `/run rerun 45567269730` 또는 `/run sql` 로 `test_sql` 을 다시 확인합니다. 이 PR의 소스 변경은 필요하지 않습니다(추론).
4. collector의 shard 01 JUnit 누락 판정은 `cubrid-ci` 쪽 후속 확인 대상입니다.

## 증거 파일

- Head: `~/.local/share/cubrid-ci-data/github-actions/CUBRID-cubrid/pr-8734/f64df11ae676aa2b840b8a996e7d87c810763789/` (`providers/github-actions/runs/45567269730/attempts/1/test_sql/raw/`)
- 비교 PR: 같은 저장소의 `pr-8735/b6c1823f5484205c32eacc1de4fb9c33ab4b24d2/`, `pr-8736/fd7d071ed5c625612d6035a5028d99f74b0922d7/`
