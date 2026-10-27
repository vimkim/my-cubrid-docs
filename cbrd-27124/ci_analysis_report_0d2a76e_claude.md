# PR #8298 `test_sql` CI 분석 경고 보고서 (`0d2a76e`)

> **이 collector snapshot은 회귀나 근본 원인 결론을 뒷받침하지 않는다.** `cubrid-ci` 수집이 무결성 검사에서 `collection_failed`로 끝났다. 검증된 suite summary가 없다. merge-base의 SQL CI도 없다. 세 실패의 원인 분석은 다른 증거에 근거해 [CBRD-27124-pr8298-sql-failure-causes_0d2a76e_claude.md](CBRD-27124-pr8298-sql-failure-causes_0d2a76e_claude.md)에 따로 썼다.

- 분석일: 2026-10-27 (Asia/Seoul). 요청 범위는 `test_sql`이다.
- 작업 기록: `work-tracker #533`.

## 식별 정보

| 항목 | 값 |
| --- | --- |
| Repository | `CUBRID/cubrid` |
| PR | [#8298](https://github.com/CUBRID/cubrid/pull/8298) `[CBRD-27124] Isolate per-commit build version headers` (draft, OPEN) |
| 고정한 head SHA | `0d2a76e60f944be0ababe9c466766c553189fcda` |
| status snapshot | `cubrid-ci status 8298 --json` 1회. `.pr.head_sha`가 위 SHA와 같다. |
| CI run | [40487586838](https://github.com/CUBRID/cubrid/actions/runs/40487586838) attempt 1, `gha-ci: test_sql` = FAILURE (2026-10-27T11:44:32Z 보고) |
| Collector | `cubrid-ci 0.2.0 (dd290e9f7b9b, release)`, `cubrid-ci doctor --json` = `ok: true` |
| 수집 명령 | `cubrid-ci collect https://github.com/CUBRID/cubrid/pull/8298 --commit 0d2a76e… --suite test_sql --json` 1회, exit **4** |
| Evidence directory | `~/.local/share/cubrid-ci-data/github-actions/CUBRID-cubrid/pr-8298/0d2a76e60f944be0ababe9c466766c553189fcda/` |

## Observation 결과

| 항목 | 값 |
| --- | --- |
| Observation ID | `20261027T121408.012297150Z-98169-0` |
| 시작·종료 | 2026-10-27T12:14:08Z → 12:14:14Z |
| outcome | `incomplete` |
| 스키마 검증 | request v1, result v1, `manifest.json` v2, 명령 결과 v2 모두 통과 |
| 일치 확인 | observation의 `command`가 저장한 명령 결과와 같다. manifest가 명령 결과와 같다. 요청 suite는 `[test_sql]`이다. |
| report-mode gate | `{"mode":"warning","regression_conclusions_allowed":false,"comparison_scope":"none"}` |

Gate 입력은 다음과 같다: `identity=established`, `observation=incomplete`, `manifest=validated`, `requested_summaries=none`, `result_matches_observation=true`, `requested_suites_reconciled=true`, `baseline=unavailable`.

## Suite 상태

| Suite | 상태 | CI 판정 | 검증된 counts |
| --- | --- | --- | --- |
| `test_sql` | `collection_failed` | FAILURE (CI collect 단계: `sql: 3 failed`) | 없음 |

## 취득 원장

10개 shard의 원시 응답을 모두 `retained` 상태로 보관했다. `retained`는 suite 판정이 아니다.

| Shard | 상태 | 배정 | JUnit `tests` | JUnit 실패 | `test_rc` |
| --- | --- | ---: | ---: | ---: | ---: |
| 00 | retained | 3,691 | 3,691 | 0 | 0 |
| 01 | retained | 3,533 | **3,531** | 0 | 0 |
| 02 | retained | 349 | 349 | 0 | 0 |
| 03 | retained | 2,842 | 2,842 | 1 | 1 |
| 04 | retained | 755 | 755 | 0 | 0 |
| 05 | retained | 2,639 | 2,639 | 0 | 0 |
| 06 | retained | 488 | 488 | 0 | 0 |
| 07 | retained | 2,171 | 2,171 | 0 | 0 |
| 08 | retained | 736 | 736 | 0 | 0 |
| 09 | retained | 455 | 455 | 2 | 1 |

이 표의 값은 원시 파일(`shard.done`, `linux_sql_64bit.xml`)에서 직접 읽었다. collector가 검증한 summary가 아니다. 계획 총수는 17,659건, JUnit 합계는 17,657건이다. 모든 shard의 `build.read`는 엔진 `0d2a76e…`, debug 빌드, run 40487586838 attempt 1을 기록한다. 모든 shard의 `tc.read`는 `tc_sha=9767e5d4c255f72e5a72b9b8a7b1ac00bcbb1bb1`, `tc_branch=tc/pr-8298`을 기록한다.

원시 `failed.list`에는 다음 3건이 있다.

| Shard | Testcase |
| --- | --- |
| 03 | `sql/_13_issues/_24_1h/cases/cbrd_25238.sql` |
| 09 | `sql/_36_guava/cbrd_27657/cases/cbrd_27657.sql` |
| 09 | `sql/_36_guava/cbrd_27644/cases/cbrd_27644.sql` |

## 바이너리 예산

바이너리 수집을 요청하지 않았다(`include: false`). 소비량은 0 / 536,870,912 bytes다.

## 진단

Collector 오류는 다음과 같다.

```json
{"suite":"test_sql","kind":"integrity","diagnostic":"identity_or_integrity",
 "message":"result identity mismatch: shard 01 workflow result and JUnit counts disagree"}
```

원인은 다음과 같다(원시 파일에서 확인).

- shard 01의 `summary_info`에는 `:ok` 줄이 3,533개 있다. JUnit에는 testcase가 3,531개 있다.
- 빠진 2건은 `sql/_05_plcsql/_01_testspec/_05_bug_fix/cbrd-27556/cases/33_static_sql_group_by_having_alias.sql`과 `…_alias_error.sql`이다.
- 이 디렉터리는 자체 `cases/`를 가진 `_05_bug_fix/` 아래에 다시 `cases/`를 둔다. testcase commit `930a44266`(2026-10-12)에서 추가되었다.
- CTP는 이 하위 블록의 헤더를 `total:0`으로 쓰면서 두 case를 `ok`로 나열했다. JUnit 변환은 두 case를 빠뜨렸다.
- CI collect 단계의 `count()`는 `summary_info`의 `:ok`/`:nok` 줄을 센다. 그래서 3,533건을 처리된 것으로 보고 "cases went missing" 오류를 내지 않았다.
- `cubrid-ci`는 workflow 쪽 개수(passed 3,533)와 JUnit 개수(passed 3,531)를 비교한다. 그래서 suite 전체를 거부한다(`cubrid-ci` `dd290e9`의 `src/gha_evidence.rs:1032-1038`).

이 불일치는 실패 3건이 있는 shard 03·09와 관계가 없다. 그래도 gate는 우회하지 않는다. 같은 원시 증거를 다른 경로로 신뢰해 검증된 summary로 올리지 않는다.

Baseline 수집 결과는 다음과 같다.

| 항목 | 값 |
| --- | --- |
| 명령 | `cubrid-ci collect-base https://github.com/CUBRID/cubrid/pull/8298 --suite test_sql --json` 1회, exit **3** |
| Observation ID | `20261027T121750.877139403Z-123389-0` (request v2, result v2, manifest v3, 명령 결과 v3 스키마 통과), outcome `incomplete` |
| 관계 | head `0d2a76e…`(고정 SHA와 같음), target `develop` tip `2d925cb8685600135eb1fb1781811f6b45fdecb0`, merge base `2d925cb…`(2026-10-27T12:16:46Z 관측) |
| 탐색 범위 | `exact_commit_links`: 모든 exact-commit status와 check run, repository 전체 workflow 검색 없음 |
| 결과 | 후보 run 0개, `test_sql: not_observed` |

`2d925cb`의 develop push 실행은 빌드만 한다. 기존 캐시 보고서가 쓴 run 40481418559도 빌드 자료이며 SQL baseline이 아니다.

## 모르는 것

- 이 run의 검증된 suite counts와 실패 목록. 원시 값은 위 표와 같지만 collector 검증을 통과하지 않았다.
- 정확한 merge-base `2d925cb`의 SQL 판정. 이 커밋에는 SQL CI가 없다.
- 이 snapshot만으로 본 세 실패의 PR 관련성.

## 검증된 증거를 얻기 위한 조치

1. `cubrid-ci`가 중첩 `cases/` 디렉터리의 CTP JUnit 누락을 처리해야 한다. 예를 들어 `summary_info` 줄과 JUnit 사이의 차이를 이름으로 대조해 진단할 수 있다. 수정 후 이 run을 다시 수집한다. 이 작업은 별도 도구 작업이다. 같은 TC 디렉터리가 같은 shard 구성에 들어가는 다른 SQL run도 같은 오류를 낼 가능성이 있다(추론).
2. 정확한 baseline이 필요하면 `2d925cb`에서 SQL을 실행해야 한다. 이 분석은 CI를 실행하지 않았다. 실행은 별도 승인 후 `cubrid-ci-trigger` 절차로 한다.
3. 원인 분석은 위 두 조치를 기다리지 않고 [별도 문서](CBRD-27124-pr8298-sql-failure-causes_0d2a76e_claude.md)에서 독립 증거로 진행했다.
