# CBRD-27539 PR(2) draft context

- Ticket: CBRD-27539 (Sub-task of CBRD-27537). Description scope updated on 2026-11-26 to include PR(2).
- Source: `vimkim/cubrid` branch `CBRD-27539-module-docs` (to be pushed); local commit `39259c507290a7590db73f83a1688376caaf5e4d`.
- Base: `CUBRID/cubrid` `develop` at `7ac243883e` (source rebased onto it). Claims were verified at `ca5c2153ed`; the one newer commit (#8709) changes no `.md` file.
- Observed remote head: branch does not exist on `vk` yet; no open PR for this head.
- Target repository: `CUBRID/cubrid`. Operation: `create` (draft).
- Proposed title: `[CBRD-27539] Fix module AGENTS.md and agent docs against live code`
- Body: `cbrd-27539/pr2-body.md`. Explanation: none (body links the audit report `cbrd-27539/agents-meta-audit.md`, already on `main`).
- Related: PR #8751 (PR 1, merged), CBRD-28388, CBRD-28409, CBRD-28410, CBRD-28411.

## Proposed operations (need user confirmation)

1. `git push vk CBRD-27539-module-docs` (new branch on the personal fork).
2. `gh pr create --repo CUBRID/cubrid --base develop --head vimkim:CBRD-27539-module-docs --draft --title "<title>" --body-file cbrd-27539/pr2-body.md --assignee vimkim`.

## Authorization record

- 2026-11-26: user approved the plan "PR 본문 초안을 보여드린 뒤 draft PR을 엽니다" (step 3) with "1. yes 2. yes 3. yes 4. yes". Publication still waits for confirmation after the body is shown.

## Results

- (none yet)
