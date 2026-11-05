# CBRD-27933 vacuum OOS VFID lookup failure

[CBRD-27933](https://jira.cubrid.org/browse/CBRD-27933) tracks the defect raised in the [PR #8350 review comment](https://github.com/CUBRID/cubrid/pull/8350#discussion_r4452180248). No PR exists yet. The source revision is `1ef6ed6125eb6028c06b0e05282dc0041bde3f48`, and the reproduction tests are the local CUBRID commits `ec3edd1ab` and `a8065e5fe` on branch `CBRD-27933-vacuum-oos-vfid-lookup-error`. The related latch-cycle fix is in [cbrd-27860](../cbrd-27860/README.md).

Last modified: 2026-11-05, Asia/Seoul.

| File | What it contains | Created | Last modified | Why it was created |
| --- | --- | --- | --- | --- |
| [repro-analysis.md](repro-analysis.md) | 헤더 조회 실패 경로, 재현 장치, debug와 release와 prototype A, B의 관측 결과, 분석 질문의 답, 선택지 B 채택 근거와 미실행 조건 | 2026-11-04 | 2026-11-05 | 수리 설계 전에 재실행 가능한 재현과 런타임 근거를 남기도록 작성 |
| [reviewer-reply-draft.md](reviewer-reply-draft.md) | 리뷰어가 제안한 같은 페이지 재시도 대신 블록 단위 재시도를 고른 이유를 설명하는 PR #8350 스레드 답글 초안 (미게시) | 2026-11-05 | 2026-11-05 | 수리 전에 리뷰어에게 방향 변경과 실험 근거를 알리도록 작성 |

Supporting files are linked from the analysis. [`run-repro.sh`](run-repro.sh) runs the reproduction cases and summarizes their evidence. [`gdb-debug-abort.sh`](gdb-debug-abort.sh) captures the debug abort stack. [`return-lookup-error-prototype.patch`](return-lookup-error-prototype.patch) and [`retry-block-later-prototype.patch`](retry-block-later-prototype.patch) are the throwaway engine changes for prototypes A and B.
