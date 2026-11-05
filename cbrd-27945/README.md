# CBRD-27945 metadata recursion reservation on develop

[CBRD-27945](https://jira.cubrid.org/browse/CBRD-27945) investigates an OOS candidate in which recursive file metadata allocation reserves a sector while a reclaimable empty page exists. This directory records whether the same candidate is a defect on CUBRID develop `2362424f25bcebd1bd9733bddd59a993e2852ac5`. No PR exists. The model was first written on the local CUBRID branch `CBRD-27945-develop-investigation` (commits `d424d5965`, `c2955e167`), which is not pushed. The copy here is the published one.

Last modified: 2026-11-05, Asia/Seoul.

| File | What it contains | Created | Last modified | Why it was created |
| --- | --- | --- | --- | --- |
| [develop-applicability.md](develop-applicability.md) | develop 결함 여부 판정, heap header latch와 vacuum postpone 순서, 모델 결과, 요구사항 검색 결과, 한계와 범위 밖 단서 | 2026-11-05 | 2026-11-05 | OOS 후보가 develop 결함인지 판정하고 근거를 남기도록 작성 |
| [develop-heap-reservation/README.md](develop-heap-reservation/README.md) | TLA+ 모델의 실행 방법, 소스에서 추출하는 사실, action과 소스의 대응, fixture별 판정표, 제외한 경로 | 2026-11-05 | 2026-11-05 | 판정에 쓴 모델을 다시 돌리고 검토할 수 있도록 작성 |

Supporting files are linked from the model README. [`DevelopHeapReservation.tla`](develop-heap-reservation/DevelopHeapReservation.tla) is the model. [`run.py`](develop-heap-reservation/run.py) extracts the source facts, runs TLC over the fixtures, and runs the source-mutation self-test. [`statechart-view.mjs`](develop-heap-reservation/statechart-view.mjs) and [`statechart-A1.cfg`](develop-heap-reservation/statechart-A1.cfg) draw the A1 chart with the statechart tool. The `.gitignore` keeps local `runs/` output out of Git.
