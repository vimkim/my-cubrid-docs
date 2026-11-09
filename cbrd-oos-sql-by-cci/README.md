# OOS feature branch의 test_sql_by_cci 실패

새 gha-ci suite `test_sql_by_cci`에서 `feature/oos-merge`가 develop보다 더 실패하는 case를 분류한다.
관련 PR: [CUBRID/cubrid#8434](https://github.com/CUBRID/cubrid/pull/8434) (분석한 run의 PR), [CUBRID/cubrid#7990](https://github.com/CUBRID/cubrid/pull/7990) (feature merge PR). 상위 이슈: CBRD-26978.

| File | What it contains | Created | Last modified | Why it was created |
| --- | --- | --- | --- | --- |
| [report.md](report.md) | 57개 실패의 (a)/(b)/(c) 분류, 비교한 run과 commit, 원인 근거 | 2026-11-09 | 2026-11-09 | OOS가 직접 고칠 실패만 골라내기 위해 |
| [jira-draft.md](jira-draft.md) | `feature/oos-merge`에서만 실패하는 28개를 다루는 JIRA 이슈 초안 (미등록) | 2026-11-09 | 2026-11-09 | 새 이슈 등록 여부를 판단하기 위해 |
