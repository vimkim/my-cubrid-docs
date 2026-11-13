# 중복 코드 drift 분석

Created: 2026-11-13. Last modified: 2026-11-13 (Asia/Seoul).

복사된 코드 중 한쪽에만 버그 수정이 들어간 곳을 찾는 감사 결과와, 같은 감사를 다시 돌리는 스크립트를 둔다.

| File | What it contains | Created | Last modified | Why it was created |
| --- | --- | --- | --- | --- |
| [clone-drift-audit.md](clone-drift-audit.md) | CPD·이름 쌍으로 찾은 drift 후보 8건과 근거, `e64a04a79a` 기준. D1(서버 측 JDBC `?` 개수 계산)은 재현됨 | 2026-11-13 | 2026-11-13 | CBRD-28080 같은 "한쪽만 고친 복사본" 결함을 중복 탐지로 찾기 위해 |

[tools/](tools/)는 보고서의 방법을 다시 실행하는 스크립트다. `run_all.sh <cubrid-root> <outdir> [min-tokens]`가 CPD 두 모드, lizard, 쌍 순위(`pairs.tsv`), 잡음 제거(`review.tsv`), 이름 쌍(`twins.tsv`)을 차례로 만든다. `review-recipe.md`는 쌍을 비교한 하위 에이전트에게 준 절차서다.
