# CBRD-27230 PR draft context

- Ticket: CBRD-27230
- SOURCE_COMMIT: f0d6b03a56408e3839b1a590918d0bd9f818e74b
- Source repository/branch: github.com/vimkim/cubrid, `CBRD-27230-oos-update-dedup` (remote `vk`); remote branch absent at preparation (2026-11-16).
- Target repository: CUBRID/cubrid; base `feature/oos-merge` (user decision 2026-11-16: "base 를 origin/feature/oos-merge 로 하고, 8434 가 머지된 이후에만 들어갈 수 있다고 명시").
- Stack: 17 commits ahead of origin/feature/oos-merge = 14 commits of PR #8434 (head b049fa155c, OPEN, base feature/oos-merge) + 62a91231c7, 654bb63f15, f0d6b03a56.
- Operation: create, draft status, assign `vimkim`.
- Proposed title: `[CBRD-27230] Reuse unassigned OOS chains on UPDATE`
- Docs: task branch `docs/CBRD-27230-pr`, integration branch `main`; body `cbrd-27230/pr-body.md`, context `cbrd-27230/pr-context.md`. Linked explanations already on main: `cbrd-27230/design-a-prime-detail.md`, `cbrd-27230/perf/report.md`.

## Proposed operations

1. my-cubrid-docs: rebase `docs/CBRD-27230-pr` onto main, fast-forward main, push origin main.
2. Source push: `git push vk CBRD-27230-oos-update-dedup` (new branch on vimkim/cubrid).
3. `gh pr create --draft --repo CUBRID/cubrid --base feature/oos-merge --head vimkim:CBRD-27230-oos-update-dedup --title "<title>" --body-file cbrd-27230/pr-body.md --assignee vimkim`.
4. Per AGENTS.override standing authorization: trigger CUBRID CI once after the push, wait, report result and run URL, then stop. TC repos: report TC PRs the bot creates; no TC changes planned (unit tests only).

## Publication record

(filled during publication)
