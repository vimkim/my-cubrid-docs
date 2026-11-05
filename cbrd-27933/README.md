# CBRD-27933 vacuum OOS VFID lookup failure

[CBRD-27933](https://jira.cubrid.org/browse/CBRD-27933) tracks the defect raised in the [PR #8350 review comment](https://github.com/CUBRID/cubrid/pull/8350#discussion_r4452180248). The fix PR is drafted in [pr-body.md](pr-body.md) and not yet created. The source revision is `1ef6ed6125eb6028c06b0e05282dc0041bde3f48`, the PR #8350 head before its squash merge as `d52b1889e`. The reproduction tests are the local CUBRID commits `ec3edd1ab` and `a8065e5fe` on branch `CBRD-27933-vacuum-oos-vfid-lookup-error`, now rebased onto `d52b1889e` as `36a31b6d3` and `85fc8b67f`. The related latch-cycle fix is in [cbrd-27860](../cbrd-27860/README.md).

Last modified: 2026-11-05, Asia/Seoul.

| File | What it contains | Created | Last modified | Why it was created |
| --- | --- | --- | --- | --- |
| [repro-analysis.md](repro-analysis.md) | 헤더 조회 실패 경로, 재현 장치, debug와 release와 prototype A, B의 관측 결과, 분석 질문의 답, 선택지 B 채택 근거, PR #8350 병합 뒤 재실행, 미실행 조건 | 2026-11-04 | 2026-11-05 | 수리 설계 전에 재실행 가능한 재현과 런타임 근거를 남기도록 작성 |
| [fix-decisions.md](fix-decisions.md) | 선택지 B, debug assert 정책, 회귀 테스트 빌드, 기준 브랜치의 결정과 이유. POC 측정과, 정식 구현에서 바뀐 것(새 오류 코드, 장애 주입 정정, 블록 처리 방식, 재실행 간격) | 2026-11-05 | 2026-11-05 | 수리 전에 정한 내용과 그 근거를 남기도록 작성 |
| [reviewer-reply-draft.md](reviewer-reply-draft.md) | PR #8350 스레드에 게시한 답글 세 개. 블록 단위 재시도를 고른 이유, 병합 뒤 기준의 재실행, POC 결과 공유 | 2026-11-05 | 2026-11-05 | 수리 전에 리뷰어에게 방향 변경과 실험 근거를 알리도록 작성 |
| [pr-body.md](pr-body.md) | 수리 PR 본문 초안. 목적, 구현, 검증과 제한 | 2026-11-05 | 2026-11-05 | 수리 PR을 올리기 전에 본문을 검토받도록 작성 |
| [pr-context.md](pr-context.md) | PR 본문의 소스 커밋, 대상 브랜치, 게시 작업 목록 | 2026-11-05 | 2026-11-05 | PR 게시를 이어서 하거나 다시 확인할 수 있도록 작성 |

Supporting files are linked from the analysis. [`run-repro.sh`](run-repro.sh) runs the reproduction cases and summarizes their evidence. [`gdb-debug-abort.sh`](gdb-debug-abort.sh) captures the debug abort stack. [`return-lookup-error-prototype.patch`](return-lookup-error-prototype.patch) and [`retry-block-later-prototype.patch`](retry-block-later-prototype.patch) are the throwaway engine changes for prototypes A and B.
