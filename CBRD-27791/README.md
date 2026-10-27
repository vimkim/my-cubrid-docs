# CBRD-27791: OOS batch read

관련 [CBRD-27791](https://jira.cubrid.org/browse/CBRD-27791), parent [CBRD-26978](https://jira.cubrid.org/browse/CBRD-26978), [PR #7990](https://github.com/CUBRID/cubrid/pull/7990).
현재 산출물은 미수정 엔진의 분석·재측정과 후속 구현 계획이다.

| File | What it contains | Created | Last modified | Why it was created |
| --- | --- | --- | --- | --- |
| [상세 분석·재측정](CBRD-27791-oos-batch-read-analysis_dcbf09e_codex.md) | 기존 trace 감사, native SQL과 bounded replay 대조, source 책임·한계 | 2026-10-28 | 2026-10-28 | 엔진에서 검토할 batch 범위와 근거를 확인한다. |
| [구현·검증 계획](CBRD-27791-oos-batch-read-plan_dcbf09e_codex.md) | 소유 층·Interface 후보, 작업 의존 관계, 집중 정확성·성능 검증과 중단 기준 | 2026-10-28 | 2026-10-28 | 후속 구현을 review 가능한 단계로 나눈다. |

선별 기계 요약·재생 도구·fixture는 상세 분석에서 연결한다. 원시 로그와 trace는 Git에 넣지 않는다.
