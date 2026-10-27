# PR #8298 SQL 실패 3건의 원인과 PR 관련성 (`0d2a76e`)

- 질문: [PR #8298](https://github.com/CUBRID/cubrid/pull/8298)의 [run 40487586838](https://github.com/CUBRID/cubrid/actions/runs/40487586838)에서 실패한 SQL testcase 3건은 왜 실패했는가? 이번 PR의 변경과 관련이 있는가?
- 독자: PR #8298 작성자와 리뷰어, 그리고 CBRD-27657·CBRD-27644·CBRD-27469 담당자.
- 분석일: 2026-10-27 (Asia/Seoul). 작업 기록은 `work-tracker #533`이다.
- 범위: 위 run의 `test_sql`에서 실패한 3건만 다룬다. medium·shell, TC Merge Gate, 캐시 실험은 다루지 않는다.

## 결론

**세 실패 모두 PR #8298의 변경(버전 헤더 분리)과 관련이 낮다(`unlikely`, 확신도 높음).** 같은 TC 내용을 가진 다른 PR들의 CI에서 같은 실패 signature가 반복되었다. 그 PR들의 엔진에는 PR #8298의 변경이 없다. 원인은 두 가지다.

| Testcase | 원인 | PR 관련성 | 확신도 |
| --- | --- | --- | --- |
| `sql/_36_guava/cbrd_27657/cases/cbrd_27657.sql` | A. CBRD-27657의 TC가 엔진 수정보다 먼저 testcase develop에 병합됨 | unlikely | 높음 |
| `sql/_13_issues/_24_1h/cases/cbrd_25238.sql` | A. 같은 TC 커밋이 이 answer를 "병합하지 않는 plan"으로 재기준화함 | unlikely | 높음 |
| `sql/_36_guava/cbrd_27644/cases/cbrd_27644.sql` | B. CBRD-27644 answer가 CBRD-27469 없는 엔진에서 만들어졌고, 두 변경을 합친 develop에서 Q10 plan이 다름 | unlikely | PR 무관성은 높음. CBRD-27469가 기제라는 점은 중상(실험 미수행) |

- **원인 A**: 엔진 [PR #8218](https://github.com/CUBRID/cubrid/pull/8218)(CBRD-27657)은 아직 OPEN이다. 그런데 그 TC인 [cubrid-testcases #3816](https://github.com/CUBRID/cubrid-testcases/pull/3816)이 2026-10-27T10:06:09Z에 develop으로 병합되었다. PR #8298의 TC 브랜치는 13분 뒤에 이 커밋 바로 위에서 만들어졌다. 그래서 수정이 없는 엔진에 수정 후의 answer를 비교했다.
- **원인 B**: [PR #8177](https://github.com/CUBRID/cubrid/pull/8177)(CBRD-27644)의 마지막 CI는 CBRD-27469(`6f35e8ee8`)가 없는 head에서 통과했다. squash 결과인 `2d925cb`에는 두 변경이 함께 있다. 그 결과 Q10의 UNION ALL 첫 arm이 다른 인덱스 scan을 선택한다. 이는 두 변경의 의미 충돌로 보이며, 텍스트 충돌은 없었다.

이 문서의 판단은 collector가 검증하지 못한 원시 실패 텍스트, Git·TC 이력, Chronicle 이력과 결과 저장소의 다른 PR 결과에 근거한다. 이 run의 `cubrid-ci` 증거는 shard 01의 무관한 개수 불일치 때문에 검증을 통과하지 못했다. 그 경고 보고서는 [ci_analysis_report_0d2a76e_claude.md](ci_analysis_report_0d2a76e_claude.md)에 따로 있다.

## 분석 대상 revision

| 항목 | 값 |
| --- | --- |
| 엔진 (시험한 소스) | `CUBRID/cubrid` [`0d2a76e60f944be0ababe9c466766c553189fcda`](https://github.com/CUBRID/cubrid/commit/0d2a76e60f944be0ababe9c466766c553189fcda), PR #8298 head, 부모는 `2d925cb` |
| merge-base = 관측 시점 develop tip | [`2d925cb8685600135eb1fb1781811f6b45fdecb0`](https://github.com/CUBRID/cubrid/commit/2d925cb8685600135eb1fb1781811f6b45fdecb0), PR #8177의 squash |
| Testcase | `CUBRID/cubrid-testcases` [`9767e5d4c255f72e5a72b9b8a7b1ac00bcbb1bb1`](https://github.com/CUBRID/cubrid-testcases/commit/9767e5d4c255f72e5a72b9b8a7b1ac00bcbb1bb1) (`tc/pr-8298`, 2026-10-27T10:19:12Z), 부모 `2272d30ec` |
| CI | gha-ci run 40487586838 attempt 1, `issue_comment` 이벤트, debug 빌드, SQL 10 shard |
| 실패 shard | [shard 03](https://github.com/CUBRID/cubrid/actions/runs/40487586838/job/122136912412) (2,842건 중 1건 실패), [shard 09](https://github.com/CUBRID/cubrid/actions/runs/40487586838/job/122136912437) (455건 중 2건 실패) |
| 도구 | `cubrid-ci 0.2.0 (dd290e9f7b9b, release)`, `cubrid-tcc 0.3.0`, `cubrid-jira` |

PR #8298의 변경은 `0d2a76e` 한 커밋이다. 이 커밋은 빌드 버전 매크로를 커밋별 헤더로 분리하며 optimizer·query rewrite 코드를 바꾸지 않는다. 다만 아래 판단은 이 사실에서 출발하지 않는다. 실패 결과의 내용과 다른 PR의 같은 결과에서 판단한다.

## 시간순 사건

| 시각 (UTC) | 사건 | 영향 |
| --- | --- | --- |
| 2026-10-23 07:14 | develop에 [`6f35e8ee8`](https://github.com/CUBRID/cubrid/commit/6f35e8ee8) [CBRD-27469] analytic-order full index scan 후보 추가 | 원인 B의 한쪽 |
| 2026-10-27 05:57 | PR #8177 run 40457677044, 엔진 `9afb6fee9`(CBRD-27469 없음): `cbrd_27644` **PASS** | answer의 기준 |
| 2026-10-27 07:15 | PR #8218 run 40463421691, 엔진 `7b4a0a3ec`(수정 포함) + `tc/pr-8218`: `cbrd_27657`, `cbrd_25238` **PASS** | 원인 A의 양성 대조 |
| 2026-10-27 09:30:23 | TC #3774(CBRD-27644) 병합 → `2ae9105fa` | |
| 2026-10-27 09:31:20 | 엔진 PR #8177 병합 → `2d925cb` | 원인 B 성립 |
| 2026-10-27 10:06:09 | TC #3816(CBRD-27657) 병합 → `2272d30ec`. 엔진 PR #8218은 OPEN | 원인 A 성립 |
| 2026-10-27 10:19:12 | `tc/pr-8298` 초기화 → `9767e5d` (부모 `2272d30ec`) | PR #8298이 두 TC 변경을 모두 받음 |
| 2026-10-27 11:19–11:23 | PR #8298 shard 03·09 결과 기록, 11:44:32 `gha-ci: test_sql` FAILURE | |

TC #3816은 sync bot이 아니라 maintainer 계정이 수동 병합했다(GitHub `merged` 이벤트). 커밋 author는 `cubrid-tc-sync-bot`이다. 2026-10-27 21:40 KST 조회 시 PR #8218은 `APPROVED`, `OPEN`이다. 같은 시각 testcase develop tip `2a63df73c1`까지 세 testcase 경로를 바꾼 후속 커밋은 없다.

## 원인 A: CBRD-27657 TC가 엔진보다 먼저 병합됨

### 테스트 의도

[CBRD-27657](http://jira.cubrid.org/browse/CBRD-27657)의 결함은 다음과 같다. LEFT OUTER JOIN 왼쪽 인라인 뷰의 select list에 상관 스칼라 서브쿼리가 있고 ON 절이 그 컬럼을 참조한다고 하자. 그러면 뷰 병합이 서브쿼리를 ON 절로 옮긴다. 그 결과 짝이 없는 왼쪽 행이 NULL로 채워지지 않고 사라진다. JIRA는 CBRD-26260(`bab4485c6`)이 단일 테이블 인라인 뷰의 LEFT JOIN 병합을 허용한 뒤로 develop에서 재현된다고 기록한다. PR #8218은 이런 경우 뷰를 병합하지 않는다.

TC 커밋 [`2272d30ec`](https://github.com/CUBRID/cubrid-testcases/commit/2272d30ec113cd51a7e4c181ee31e29ebc341295)는 두 가지를 바꿨다.

- `sql/_36_guava/cbrd_27657/`을 추가했다(case 185줄, answer 413줄).
- `sql/_13_issues/_24_1h/answers/cbrd_25238.answer`를 "원래의 병합하지 않는 plan"으로 재기준화했다. 커밋 메시지는 CBRD-26260 TC 커밋이 이 answer를 덮어썼다고 설명한다.

두 변경 모두 PR #8218의 엔진 동작을 전제한다.

### 관측

`cbrd_27657`은 21개 질의에서 차이가 났다. 첫 질의(JIRA 재현 질의 1)의 actual은 JIRA의 **Actual Result**와 같은 2행이다. answer는 JIRA의 **Expected Result**인 4행이다.

```text
-- answer (수정 후 기대)      -- actual (0d2a76e)
ca    cb                       ca    cb
1     100                      1     100
5     null                     7     100
7     100
9     null
```

나머지 차이도 같은 결함을 보인다.

- USE_HASH·USE_MERGE 변형의 rewritten query가 `from ta d left outer join tb tb on (tb.cb>d.cb+(select min(x.cb) ...))` 형태다. 즉 인라인 뷰가 병합되어 서브쿼리가 ON 절에 들어갔다.
- NULL 패딩 뷰의 `NVL(cb, -1)`, `COUNT(*)` 항목은 기대값 `null` 대신 `-1`, `0`을 낸다.
- 같은 형태의 UPDATE·DELETE는 2행이 아니라 0행을 바꾼다. 그래서 뒤이은 `SELECT * FROM ta` 결과도 연쇄적으로 다르다.
- 한 질의는 `Error:-494`(`ER_PT_SEMANTIC`)를 낸다.

`cbrd_25238`은 두 질의의 plan이 다르다. answer는 인라인 뷰 `a`를 그대로 두는 plan(`class: a node`, `(select a.seq, (select max(x.sno) ...) from a_test a)`)이다. actual은 병합한 plan이다(`class: x node`, `sargs: term`, `subqs: ?`, `left outer join a_test_mbr c on c.sno=(select max(x.sno) ...)`). actual 쪽 내용은 `2272d30ec`가 지운 이전 answer와 같다. 공백 정규화 토큰 비교에서 남은 차이는 두 diff의 문맥 경계 차이(`class:`, `select`, `cost: ? card ?` 등)뿐이다.

### 이력과 비교

Chronicle 결과를 TC·엔진 ancestry와 맞추면 결과가 정확히 갈린다. ancestry는 GitHub compare API로 확인했다.

| 조건 | `cbrd_25238` | `cbrd_27657` |
| --- | --- | --- |
| TC에 `2272d30ec` 포함, 엔진에 #8218 없음 | FAIL 5/5 (PR #8200, #8298, #7881, #8269, #8263) | FAIL 5/5 (같은 run) |
| TC에 `2272d30ec` 없음, 엔진에 #8218 없음 | PASS 15/15 (2026-10-27 07:28Z 이후 run) | 해당 TC 없음 |
| `tc/pr-8218` + 엔진 #8218 head `7b4a0a3ec` | PASS (run 40463421691) | PASS (같은 run) |

실패한 5개 run의 JUnit 실패 본문을 결과 저장소에서 받아 signature를 비교했다. 방법은 [증거 파일](#증거-파일)에 적었다.

| Testcase | signature | 일치 |
| --- | --- | --- |
| `cbrd_25238` | `c1025da6f5de20ee` (2개 질의 차이) | 5개 run 모두 같음 |
| `cbrd_27657` | `964e99a03bbf8fb2` (21개 질의 차이) | 5개 run 모두 같음 |

### 판단

- 관측: 실패는 TC에 `2272d30ec`가 있고 엔진에 PR #8218이 없을 때만 나타난다. 엔진 계열과 PR은 상관이 없다. 같은 조건의 PR 5개에서 결과 본문이 같다.
- 추론: 원인은 TC와 엔진의 병합 순서가 어긋난 것이다. PR #8298의 엔진 변경은 필요 조건이 아니다. 그 변경이 없는 4개 PR에서도 같은 signature가 나왔기 때문이다.
- 영향 범위(추론): `tc/pr-N`을 2026-10-27T10:06Z 이후 testcase develop에서 초기화한 모든 PR이 PR #8218 병합 전까지 같은 2건으로 실패할 것이다.
- 반증 조건: `0d2a76e` 또는 `2d925cb` 엔진과 TC `9767e5d`에서 `cbrd_25238` 또는 `cbrd_27657`이 통과하는 결과. 또는 PR #8218을 적용한 엔진에서도 같은 signature가 나오는 결과.
- 다음 조치: PR #8218을 병합하거나, 병합 전까지 TC #3816을 되돌려야 한다. 이는 CBRD-27657 담당자와 maintainer가 결정한다. PR #8298 쪽에서 TC를 고쳐 이 실패를 가리면 안 된다.

## 원인 B: CBRD-27644 answer와 CBRD-27469의 의미 충돌

### 테스트 의도

[CBRD-27644](http://jira.cubrid.org/browse/CBRD-27644)는 분석 함수가 있는 인라인 뷰에도 조건을 push한다. 조건은 모든 분석 함수의 공통 PARTITION BY 키에 걸린 경우로 한정한다. `cbrd_27644.sql`은 Q01–Q20에서 push 여부를 plan으로 확인한다. 실패한 Q10의 목적은 "UNION ALL 인라인 뷰에는 push하지 않는다"이다.

```sql
select /*+ recompile */ T.*
from (select t1.c, t1.a, row_number () over (partition by t1.c order by t1.a) as rnum from tbl1 t1 where t1.a < 3000
      union all
      select t1.c, t1.a, 0 from tbl1 t1 where t1.a >= 9000) T
where T.c = 'test10'
order by T.a;
```

테이블 `tbl1`에는 인덱스 `cix_cub01 (a, c)`, `cix_cub02 (c, a)`, `cix_cub03 (b, a)`가 있다.

### 관측

결과 행은 같고 첫 arm의 scan만 다르다. 나머지 Q01–Q20은 일치한다.

```diff
 iscan
     class: t? node[?]
-    index: cix_cub? term[?] (covers)
+    index: cix_cub? (covers)
+    filtr: term[?]
```

- answer: key range `a < 3000`을 쓰는 covering index scan이다. 따라서 `cix_cub01 (a, c)`이다.
- actual: key range 없이 `a < 3000`을 key filter로 쓰는 covering index scan이다. covering이려면 `c`, `a`가 모두 필요하므로 `cix_cub02 (c, a)`다(`cix_cub03`은 `c`가 없다).

### 소스 근거 (`2d925cb`)

[`src/optimizer/query_planner.c:11048-11151`](https://github.com/CUBRID/cubrid/blob/2d925cb8685600135eb1fb1781811f6b45fdecb0/src/optimizer/query_planner.c#L11048-L11151)의 index scan 후보 생성을 따라가면 다음과 같다.

1. 첫 arm에는 `a < 3000`만 있다. `T.c = 'test10'`은 Q10 의도대로 UNION ALL 안으로 push되지 않는다. 그래서 `cix_cub02 (c, a)`의 선두 컬럼 `c`에 key range 항이 없고 `seg_terms`가 빈다.
2. `seg_terms`가 빈 인덱스에는 다음 후보만 있다. forced filter index, loose index scan, 그리고 interesting-order 후보인 GROUP BY·ORDER BY·analytic이다.
3. 첫 arm에는 GROUP BY도 ORDER BY도 없다. 외부 질의의 `order by T.a`는 arm의 것이 아니다. index skip scan이라면 plan에 `(index skip scan)`이 찍힌다.
4. 남는 후보는 CBRD-27469가 추가한 `QO_SCANMETHOD_INDEX_ANALYTIC_SCAN`(11142–11151행)뿐이다. `row_number () over (partition by c order by a)`의 정렬 순서는 `cix_cub02 (c, a)`의 키 순서와 같다.

[`6f35e8ee8`](https://github.com/CUBRID/cubrid/commit/6f35e8ee8) 설명에 따르면, 이 후보는 분석 정렬을 건너뛴다. `qo_plan_cmp`는 건너뛴 정렬 비용을 경쟁 sequential scan에 부과한다. `cix_cub01` key range scan과 비교할 때 이 후보가 선택된 정확한 비용 근거는 확인하지 않았다.

### 이력과 비교

| 엔진 | `2d925cb`(#8177) 포함 | `6f35e8ee8`(CBRD-27469) 포함 | 결과 | signature |
| --- | --- | --- | --- | --- |
| PR #8177 `e00fc7bf7`, `9afb6fee9` | 아님 | 아님 | PASS 2/2 | - |
| PR #8194(2회), #7566, #8200, #8298, #7881, #8269, #8263 | 포함 | 포함 | FAIL 8/8 | `1f1334b15564e946` (Q10 1개 질의) |
| PR #8168 `5a7b35cec` (`2d925cb`보다 1커밋 뒤) | 아님 | 포함 | FAIL 1/1 | `a80084156eaea41b` (14개 질의) |

PR #8168의 실패는 엔진에 CBRD-27644 기능 자체가 없어서 생긴 별도 signature다. 원인 B의 비교에서 제외한다.

### 판단

- 관측: CBRD-27469가 없는 엔진은 통과했다. #8177과 CBRD-27469가 모두 있는 엔진의 run 8개(엔진 7종)는 모두 같은 Q10 차이를 냈다. PR #8298의 변경이 없는 엔진 6종도 여기에 포함된다.
- 추론: `cbrd_27644.answer`의 Q10은 CBRD-27469 없는 엔진의 plan을 기록했다. develop `2d925cb`는 Q10 첫 arm에 analytic-order index scan을 고른다. 소스 근거상 이 scan을 만들 수 있는 후보는 CBRD-27469 경로뿐이다.
- 미확인: CBRD-27469를 되돌린 `2d925cb`에서 Q10을 실행하지 않았다. 두 plan 중 어느 쪽이 의도된 비용 선택인지도 판단하지 않았다. Q10의 검증 목적(push 안 함)은 두 plan 모두에서 성립한다.
- 반증 조건: `2d925cb`에서 `6f35e8ee8`만 되돌렸는데도 Q10 첫 arm이 `filtr` plan을 내는 결과. 또는 CBRD-27469 없는 엔진에서 같은 signature가 나오는 결과.
- 다음 조치: CBRD-27644·CBRD-27469 담당자가 결정한다. 선택지는 Q10 answer 재기준화, Q10을 인덱스 선택에 둔감하게 수정, 또는 analytic scan 비용 선택 수정이다. 기제를 확정하려면 위 반증 실험(아래 최소 재현)을 한다.

## PR #8298 관련성

| Testcase | 같은 signature가 나온 다른 PR | PR #8298 변경 없는 엔진의 실패 | 관련성 | 확신도 |
| --- | --- | --- | --- | --- |
| `cbrd_27657` | #8200, #7881, #8269, #8263 | 있음 | unlikely | 높음 |
| `cbrd_25238` | #8200, #7881, #8269, #8263 | 있음 | unlikely | 높음 |
| `cbrd_27644` | #8194, #7566, #8200, #7881, #8269, #8263 | 있음 | unlikely | 높음 |

정확한 merge-base `2d925cb`의 SQL CI는 없다. `cubrid-ci collect-base` 결과는 `test_sql: not_observed`이다. 따라서 "merge-base에서도 같은 실패"는 직접 관측이 아니다. 위 표는 merge-base를 포함한 다른 PR 엔진에서 관측한 결과로 판단을 대신한다.

## 권장 조치

1. **PR #8298**: 이 3건 때문에 소스를 바꿀 필요는 없다. 다만 필수 검사 `gha-ci: test_sql`은 빨간 상태로 남는다. 원인 A·B가 해소된 뒤 SQL을 다시 실행하면 확인할 수 있다. 실행은 별도 승인을 받아 `cubrid-ci-trigger` 절차로 한다. `tc/pr-8298`을 고쳐 실패를 가리지 않는다.
2. **원인 A (CBRD-27657)**: PR #8218 병합, 또는 그 전까지 TC #3816 되돌리기. develop TC를 받은 모든 PR에 영향을 주므로 가장 급하다.
3. **원인 B (CBRD-27644/27469)**: Q10 answer와 develop plan의 불일치를 해결한다. 이것도 develop TC를 받은 모든 PR에 영향을 준다.
4. **도구**: `cubrid-ci`가 중첩 `cases/` 디렉터리 때문에 이 run의 SQL 증거 전체를 거부했다. [경고 보고서](ci_analysis_report_0d2a76e_claude.md#진단)에 적은 원인을 `cubrid-ci`에서 처리해야 같은 shard 구성의 SQL run을 검증할 수 있다.

### 최소 재현 (원인 B 기제 확정용, 미수행)

1. `2d925cb`에서 격리 worktree를 만들고 `git revert --no-commit 6f35e8ee8`를 적용해 debug 빌드한다. 충돌이 나면 그 자체를 기록한다.
2. `cubrid-test-sql-run`으로 TC `9767e5d`의 `sql/_36_guava/cbrd_27644`를 실행한다. 되돌린 빌드와 `2d925cb` 빌드를 각각 실행한다.
3. 기대: 되돌린 빌드는 PASS, `2d925cb` 빌드는 signature `1f1334b15564e946`과 같은 Q10 차이.

## 증거 파일

원시 증거는 Git에 넣지 않는다. 경로는 이 분석 host 기준이다.

| 증거 | 위치 | 비고 |
| --- | --- | --- |
| head collector bundle | `~/.local/share/cubrid-ci-data/github-actions/CUBRID-cubrid/pr-8298/0d2a76e60f944be0ababe9c466766c553189fcda/` | observation `20261027T121408.012297150Z-98169-0`, 미검증(경고 보고서 참조) |
| PR #8298 실패 원문 | 위 bundle의 `providers/github-actions/runs/40487586838/attempts/1/test_sql/raw/shards/{03,09}/linux_sql_64bit.xml` | shard 09 XML SHA-256 `5c87f5c6…`는 결과 저장소 사본과 같음 |
| baseline bundle | `~/.local/share/cubrid-ci-data/github-actions/CUBRID-cubrid/commits/2d925cb8685600135eb1fb1781811f6b45fdecb0/` | observation `20261027T121750.877139403Z-123389-0`, `test_sql: not_observed` |
| Chronicle 질의 | `cubrid-tcc history/status/explain <case> --suite sql` | 갱신: `sync-data --since 2026-10-26T13:30:00Z --until 2026-10-27T12:20:00Z --suite sql --revisit-limit 0`, exit 0, snapshot 502개 추가. HTTP 502로 4개 run(40469821890, 40460882301, 40448567214, 40447297571) 미수집, 파일 84개 없음. 갱신 후 세 case 모두 freshness `FRESH`, flakiness 판정 `UNKNOWN` |
| 다른 PR의 실패 본문 | 결과 저장소 `http://192.168.1.48:30080/runs/<run>/sql/shard/<nn>/test-results/linux_sql_64bit.xml` | collector bundle과 별도로 받은 보조 이력 자료 |
| signature 방법 | JUnit `<failure>` 본문에서 TC URL을 담은 `** ` 헤더 줄을 뺀 뒤 SHA-256 앞 16자리 | 같은 signature는 같은 차이 내용을 뜻하며, 같은 근본 원인을 증명하지는 않음 |
| JIRA | `cubrid-jira search CBRD-27657`, `CBRD-27644`, `CBRD-25238` | 2026-10-27 조회 |

Chronicle은 실패 diff를 보관하지 않는다. 그래서 signature 비교에는 결과 저장소 XML을 썼다. Chronicle의 flakiness 판정은 `UNKNOWN`이다. 다만 같은 엔진·TC 조합에서 PASS와 FAIL이 섞인 사례는 없다. PR #8194는 같은 조합으로 두 번 실행해 두 번 같은 signature로 실패했다. 따라서 세 실패는 flaky보다는 revision 내용에 따른 결정적 실패로 본다.
