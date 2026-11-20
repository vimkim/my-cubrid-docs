develop CI에서도 `cbrd_27780`이 같은 증상으로 실패한 기록을 남깁니다. 본문의 "develop CI에서의 실패 기록은 확인하지 못했다"를 보충합니다.

| PR (base `develop`) | gha-ci run | 결과 |
|---|---|---|
| CUBRID/cubrid#8514 (head `b6de23c3f9`, base `030b650ff7`) | [44705649588](https://github.com/CUBRID/cubrid/actions/runs/44705649588) | 확인 2, 4 NOK, `S1HEAP=1` |
| CUBRID/cubrid#8528 | [44705951222](https://github.com/CUBRID/cubrid/actions/runs/44705951222), [44713351787](https://github.com/CUBRID/cubrid/actions/runs/44713351787) | 확인 2, 4 NOK, `S1HEAP=1` |
| CUBRID/cubrid#8664 | [44701074949](https://github.com/CUBRID/cubrid/actions/runs/44701074949) | 확인 2, 4 NOK, `S1HEAP=1` |
| CUBRID/cubrid#8613 | [44706214451](https://github.com/CUBRID/cubrid/actions/runs/44706214451) | 통과 |
| CUBRID/cubrid#8641 | [44702880730](https://github.com/CUBRID/cubrid/actions/runs/44702880730) | 통과 |

- 모두 2026-11-20의 develop 기반 run입니다. "통과"는 그 run의 shell 실패 목록에 `cbrd_27780`이 없다는 뜻입니다.
- 개수(1)와 실패 항목(확인 2와 4)이 본문의 OOS CI run 44461741652와 같습니다. 같은 날 같은 TC가 PR에 따라 통과와 실패로 갈리므로, 본문의 간헐 실패 설명과 맞습니다.
- 로컬 containment 실행(debug, develop `030b650ff7`과 #8514 head 각 1회)에서는 `S1HEAP` 평문이 나오지 않았습니다.
