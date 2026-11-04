# CBRD-27827 concurrent OOS INSERT failure

Related work is [PR 8330](https://github.com/CUBRID/cubrid/pull/8330), [PR 8350](https://github.com/CUBRID/cubrid/pull/8350), and the R1 review on [PR 7990](https://github.com/CUBRID/cubrid/pull/7990#discussion_r4398825716) and [CBRD-27827](https://jira.cubrid.org/browse/CBRD-27827). Source revision is `4db11c5f12f9c67134aad7f547df8704d1e5c591`.

Last modified: 2026-11-04, Asia/Seoul.

| File | What it contains | Created | Last modified | Why it was created |
| --- | --- | --- | --- | --- |
| [CBRD-27827-oos-insert-header-wait-pr-body_4db11c5_codex.md](CBRD-27827-oos-insert-header-wait-pr-body_4db11c5_codex.md) | 회사 PR의 목적, 최소 수정, 로컬 검증과 한계 | 2026-10-29 | 2026-10-29 | 팀 리뷰 전 게시 내용을 검토하도록 보존 |
| [CBRD-27827-oos-insert-header-wait-pr-context_4db11c5_codex.md](CBRD-27827-oos-insert-header-wait-pr-context_4db11c5_codex.md) | source/base, 게시 대상, 제안 작업과 승인 범위 | 2026-10-29 | 2026-10-29 | 중복 PR과 승인 범위 확장을 방지 |
| [concurrent-insert-debug-stall.md](concurrent-insert-debug-stall.md) | 동시 INSERT CTest의 debug 정지가 PR #8350의 기존 latch 순환임을 보인 진단 | 2026-11-04 | 2026-11-04 | PR #8330 리뷰 답글에서 상세 근거로 연결 |
