# CBRD-27858 relocation vacuum undo overwrites a reused forward slot

Related work is the R5 review on [PR 7990](https://github.com/CUBRID/cubrid/pull/7990#discussion_r4409499688) and [CBRD-27858](https://jira.cubrid.org/browse/CBRD-27858). Source revision is `628857607265880ef7bbdda4973b1b6f06e8b797`. Reproduction and verification details are in the [shared checklist](../cbrd-26357/PR-7990-hornetmj-review-checklist_20261029_codex.md#r5-relocation-undo가-재사용-슬롯을-덮어씀).

Last modified: 2026-10-30, Asia/Seoul.

| File | What it contains | Created | Last modified | Why it was created |
| --- | --- | --- | --- | --- |
| [CBRD-27858-oos-relocation-forward-slot-pr-body_6288576_claude.md](CBRD-27858-oos-relocation-forward-slot-pr-body_6288576_claude.md) | 회사 PR의 목적, 최소 수정, 수정 전후 재현, CTest와 미검증 범위 | 2026-10-30 | 2026-10-30 | 팀 리뷰 전 게시 내용을 검토하도록 보존 |
| [CBRD-27858-oos-relocation-forward-slot-pr-context_6288576_claude.md](CBRD-27858-oos-relocation-forward-slot-pr-context_6288576_claude.md) | 티켓 생성 기록, source/base, 게시 대상, 제안 작업과 승인 범위 | 2026-10-30 | 2026-10-30 | 중복 PR과 승인 범위 확장을 방지 |
