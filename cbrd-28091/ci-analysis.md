# CBRD-28091 PR #8735 CI 분석

## 스냅샷 2026-11-25: run 45567221061 attempt 1 (head `b6c1823f54`)

분석일: 2026-11-25 (Asia/Seoul). 독자: PR #8735 작성자와 develop의 `_36_guava` SQL 실패를 조사하는 개발자.

> **경고 보고서.** exact-head 증거가 완전하지 않다. `cubrid-ci verify` 결과는
> `observation: incomplete` 이고, 수집기가 integrity 검사로 `test_sql` 요약을 거부했다.
> merge-base 기준 증거도 `unavailable` 이다. `report_mode.py` 결과는 `warning`,
> `regression_conclusions_allowed: false`, `comparison_scope: none` 이다.
> **이 스냅샷으로는 회귀나 근본 원인을 확정할 수 없다.** 5절의 내용은 반증 조건이 있는 가설이며 CI 판정이 아니다.

## 1. 요약

- 검증된 `test_sql_by_cci` 요약에서 실패는 3건이며, 모두 `sql/_36_guava` 의 shard 09에 있다.
  - `cbrd_26795`
  - `cbrd_27748`
  - `cbrd_28121`
- `test_sql` 은 CI 상태가 FAILURE이고 shard 09에서 "3 failed" 이다. 하지만 수집기가 요약을 검증하지 못했다.
  - shard 로그의 `[NOK]` 줄은 위와 같은 세 테스트를 가리킨다(원본 로그 관찰, 미검증).
- 이 PR의 변경(`catcls_get_db_collation ()` 의 realloc 실패 분기)은 `_db_collation` 행이 256개를 넘을 때만 실행된다. 실패 diff는 모두 질의 계획 또는 trace 출력의 차이다.
- 관련 없는 PR #8736(CBRD-28271, run `45567167574`)도 같은 시각에 같은 세 테스트에서 `[NOK]` 이다(원본 로그 관찰, 미검증).
- 다음 조치: 7절 참조. 가설 A는 CBRD-28111 작성자 확인, 가설 B는 `cbrd_26795` 답 파일 확인이다.

## 2. CI 스냅샷

| Suite | CI 상태 | 수집 상태와 집계 | Run |
| --- | --- | --- | --- |
| `build (debug)`, `build (release)` | 성공 | 해당 없음 | [45567221061](https://github.com/CUBRID/cubrid/actions/runs/45567221061) |
| `test_medium` | 성공 | `validated`, `completed` | 같은 run |
| `test_shell` | 성공 | `validated`, `completed` | 같은 run |
| `test_sql` | 실패 | `collection_failed` (`identity_or_integrity`) | 같은 run |
| `test_sql_by_cci` | 실패 | `validated`. 17,902 계획·실행, 17,899 통과, 3 실패, 오류·건너뜀·미실행 0 | 같은 run |
| TC Merge Gate / Check TC PRs | 실패 | 격리 게이트. 최종 merge 단계까지 보류하며 회귀 실패가 아니다 | — |

## 3. 증거 범위

- Engine: `b6c1823f5484205c32eacc1de4fb9c33ab4b24d2` (PR head). Testcase: `tc/pr-8735` 의 `02b048c1841043a4fcdf1e2efc9918129ee6f320`.
- 수집기: `cubrid-ci 0.2.0 (00205d576de0, release)`. observation `20261125T112543.326980392Z-2103334-0`, 결과 `incomplete`.
- `test_sql` 진단: `result identity mismatch: stored Actions run metadata disagrees with the pinned execution` (`kind: integrity`). integrity 실패는 우회하지 않는다. 같은 날 PR #8128 분석에서도 같은 종류의 `test_sql` 거부가 기록되었다.
- binary 예산: 536,870,912 바이트 중 0 바이트 사용.
- merge base: `bfb59bdd133518da140f9af6c48bef5568df67af` (target tip과 같음). `collect-base` 결과 네 suite 모두 `not_observed`, `baseline: unavailable` 이다. develop commit에는 gha-ci suite 증거가 없다.

## 4. 검증된 실패 목록 (`test_sql_by_cci`)

| Testcase | 관찰된 차이 | 기준 비교 | PR 관련성 |
| --- | --- | --- | --- |
| `sql/_36_guava/cbrd_26795/cases/cbrd_26795.sql` | `show trace` 의 `SCAN (table: dba.px_wide_t)` 줄에 실제 출력만 `(oos time: ?, fetch: ?, ioread: ?)` 가 붙는다(diff 78줄). | `uncomparable` | `unlikely` (중간) |
| `sql/_36_guava/cbrd_27748/cases/cbrd_27748.sql` | `order by tc_ja.id limit 3` 질의에서 답은 outer `temp(sort limit)` 위의 `iscan` 이다. 실제는 outer `iscan` 과 `/* ---> skip ORDER BY */` 이다(diff 25줄). | `uncomparable` | `unlikely` (중간) |
| `sql/_36_guava/cbrd_28121/cases/cbrd_28121.sql` | `show trace` 에서 답에 있는 `skip order by: true` 줄이 실제 출력에 없다(diff 10줄). | `uncomparable` | `unlikely` (중간) |

집계: head 실패 3, 기준 공통 0, head 추가 0, 비교 불가 3, 기준 전용 0.

## 5. 가설 (CI 판정이 아님)

### 가설 A: `cbrd_27748`, `cbrd_28121` 은 CBRD-28111의 계획 변경과 갱신되지 않은 답 파일 때문이다

- **관찰**
  - 두 차이 모두 ORDER BY를 index 순서로 건너뛰는지(`skip ORDER BY`)에 관한 것이다.
  - 답 파일은 2026-11-23의 TC commit `98b4755b9`(CBRD-27748)과 `67c5593fe`(CBRD-28121)에서 왔다.
  - engine base의 마지막 commit `bfb59bdd13` 은 CBRD-28111([#8586](https://github.com/CUBRID/cubrid/pull/8586), 2026-11-25 06:03Z merge)이다. 이 변경은 ORDER BY/GROUP BY skip 후보 scan의 비용을 LIMIT까지 읽는 행만큼으로 낮추고, 10배 비용 band를 지우고, `orderby_skip` 표시를 선택된 plan에만 다시 붙인다.
  - CBRD-27748, CBRD-28121의 엔진 수정(`30eb0c4b8b`, `186674424f`)은 base에 포함되어 있다.
- **추론:** 두 테스트의 답은 CBRD-28111 이전 엔진 기준이고, CBRD-28111 이후 계획 선택이 바뀌었다.
- **미확인:** CBRD-28111 PR이 merge 전에 이 두 테스트를 실행했는지, 그때 결과가 어땠는지. merge base의 SQL 결과.
- **반증 조건:** CBRD-28111 직전 develop engine(`bfb59bdd13^`)과 같은 TC로 두 테스트가 실패하면 이 가설은 틀리다.
- **조치:** #8586 작성자에게 두 diff를 알리고, 계획 변경이 의도된 것인지 확인한다. 의도된 것이면 답 파일을 갱신해야 한다.

### 가설 B: `cbrd_26795` 는 2026-11-25 TC 갱신의 답 파일에 OOS trace가 빠진 것이다

- **관찰**
  - 차이는 `px_wide_t`(`body varchar(20000)`) scan의 trace에 OOS 통계 `(oos time: …)` 가 추가된 것뿐이다.
  - 이 출력은 `src/query/scan_manager.c:9952` 에 있고, OOS 기능(CBRD-26357, `68a9c7766f`)과 함께 base에 들어 있다.
  - 답 파일은 2026-11-25 14:44 KST의 TC commit `313d208b8`(CBRD-26795 시나리오 확장)에서 갱신되었다.
- **추론:** 새 시나리오의 넓은 행이 OOS로 저장되면서 trace에 OOS 통계가 붙는데, 답 파일은 이를 반영하지 않았다. 이 가설은 CBRD-28111과 무관하다.
- **반증 조건:** OOS가 없는 엔진에서 `px_wide_t` 의 trace에도 `(oos …)` 가 나오면 이 가설은 틀리다.
- **조치:** `313d208b8` 작성자에게 답 파일 갱신이 필요한지 확인한다.

## 6. 테스트 이력

- `cubrid-tcc history` 에서 `cbrd_26795` 는 2026-10-26 ~ 10-27 동안 39회 PASS 기록만 있다. 2026-11-25 답 갱신 이후의 기록은 없다.
- `cbrd_27748`, `cbrd_28121` 은 `not_indexed` 이다.
- 이전 실패 기록이 없으므로 flaky로 판정하지 않는다. 같은 TC 입력에서 결정적으로 재현되는 차이로 보이므로 `/run rerun` 은 권장하지 않는다.

## 7. 조치

1. 가설 A: CBRD-28111 PR #8586 작성자에게 `cbrd_27748`, `cbrd_28121` diff를 공유하고 계획 변경이 의도된 것인지 확인한다.
2. 가설 B: TC commit `313d208b8`(CBRD-26795)의 답 파일에 OOS trace를 반영해야 하는지 확인한다.
3. 수집기의 `test_sql` integrity 거부 원인을 별도로 확인한다(같은 날 PR #8128에서도 발생).
4. 이 PR(#8735)의 코드는 바꾸지 않는다. 필수 CI `test_sql` 은 develop 쪽 문제가 해결된 뒤 다시 돌린다.

## 증거 파일

- Head 수집 디렉터리: `~/.local/share/cubrid-ci-data/github-actions/CUBRID-cubrid/pr-8735/b6c1823f5484205c32eacc1de4fb9c33ab4b24d2`
- `test_sql_by_cci` 실패: `providers/github-actions/runs/45567221061/attempts/1/test_sql_by_cci/failures/*/{message.txt,diff.txt}`
