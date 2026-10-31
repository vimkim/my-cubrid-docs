# CBRD-27860 OOS vacuum and heap page allocation latch cycle

Related work is the R2 review on [PR 7990](https://github.com/CUBRID/cubrid/pull/7990#discussion_r4399323155) and [CBRD-27860](https://jira.cubrid.org/browse/CBRD-27860). The company PR is draft [8350](https://github.com/CUBRID/cubrid/pull/8350). Source revision is `1ef6ed6125eb6028c06b0e05282dc0041bde3f48`. Reproduction, fix and verification details are in the [R2 analysis](../cbrd-26357/PR-7990-R2-vacuum-heap-header-deadlock_dcbf09e_codex.md).

Last modified: 2026-10-31, Asia/Seoul.

| File | What it contains | Created | Last modified | Why it was created |
| --- | --- | --- | --- | --- |
| [CBRD-27860-oos-vacuum-heap-header-wait-pr-body_1ef6ed6_claude.md](CBRD-27860-oos-vacuum-heap-header-wait-pr-body_1ef6ed6_claude.md) | 회사 PR의 목적, 조건부 조회와 재시작 수정, 새 테스트의 수정 전후 결과, CTest와 미검증 범위 | 2026-10-31 | 2026-10-31 | 팀 리뷰 전 게시 내용을 검토하도록 보존 |
| [CBRD-27860-oos-vacuum-heap-header-wait-pr-context_1ef6ed6_claude.md](CBRD-27860-oos-vacuum-heap-header-wait-pr-context_1ef6ed6_claude.md) | 티켓 생성 기록, source/base, 게시 대상, 제안 작업과 승인 범위 | 2026-10-31 | 2026-10-31 | 중복 PR과 승인 범위 확장을 방지하고 게시 결과를 기록 |
