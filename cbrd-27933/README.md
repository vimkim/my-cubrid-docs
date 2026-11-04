# CBRD-27933 vacuum OOS VFID lookup failure

[CBRD-27933](https://jira.cubrid.org/browse/CBRD-27933) tracks the defect raised in the [PR #8350 review comment](https://github.com/CUBRID/cubrid/pull/8350#discussion_r4452180248). No PR exists yet. The source revision is `1ef6ed6125eb6028c06b0e05282dc0041bde3f48`, and the reproduction test is the local CUBRID commit `ec3edd1ab` on branch `CBRD-27933-vacuum-oos-vfid-lookup-error`. The related latch-cycle fix is in [cbrd-27860](../cbrd-27860/README.md).

Last modified: 2026-11-04, Asia/Seoul.

| File | What it contains | Created | Last modified | Why it was created |
| --- | --- | --- | --- | --- |
| [repro-analysis.md](repro-analysis.md) | 헤더 조회 실패 경로, 재현 장치, debug와 release와 prototype의 관측 결과, 분석 질문의 답, 구현 선택지와 미실행 조건 | 2026-11-04 | 2026-11-04 | 수리 설계 전에 재실행 가능한 재현과 런타임 근거를 남기도록 작성 |

Supporting files are linked from the analysis. [`run-repro.sh`](run-repro.sh) runs the reproduction cases and summarizes their evidence. [`gdb-debug-abort.sh`](gdb-debug-abort.sh) captures the debug abort stack. [`return-lookup-error-prototype.patch`](return-lookup-error-prototype.patch) is the engine change that the prototype runs applied.
