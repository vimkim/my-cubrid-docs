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

- 2026-11-26: user confirmed both operations ("1. 2. yes").
- Body fingerprint at publication: sha256 `4a9aba1569e92d0e1746350c50cd23688a89894d39c45cc6a61bafe802a1ddea`; material check passed.
- Source push: `vk/CBRD-27539-module-docs` = `39259c507290a7590db73f83a1688376caaf5e4d` (verified with `git ls-remote`).
- Draft PR created: https://github.com/CUBRID/cubrid/pull/8765 (draft, base `develop`, head `39259c5072`, assignee `vimkim`). Published body equals `pr2-body.md`.

## Revision 2 (doc split) — proposal

- Source: local commit `f9d2cc1349558c82c7459103aeaa788ca29b9e74` on top of the published `39259c5072` (fast-forward; no rebase).
- Live PR #8765 body fingerprint before update: sha256 `4a9aba1569e92d0e1746350c50cd23688a89894d39c45cc6a61bafe802a1ddea` (matches the revision-1 upload).
- Proposed operations (need user confirmation):
  1. `git push vk CBRD-27539-module-docs` (fast-forward to `f9d2cc1349`).
  2. `gh pr edit 8765 --repo CUBRID/cubrid --body-file cbrd-27539/pr2-body.md` (body only; title, draft status, assignee unchanged).

## Revision 2 — results

- 2026-11-26: user confirmed both operations ("yes").
- Source push: `vk/CBRD-27539-module-docs` = `f9d2cc1349558c82c7459103aeaa788ca29b9e74` (fast-forward, verified).
- PR #8765 body updated; live body sha256 `716906e00255c6b7925846104ab8b1b074876f07387e1e4eba96f9f84046ca5c` equals `pr2-body.md`. Head `f9d2cc1349`, still draft, title and assignee unchanged.

## Revision 3 — results

- 2026-11-26: user confirmed pushing `cf800fa8cc` ("yes"): `docs/pull-requests.md` now says `tc-merge-gate.yml` blocks while any `tc/pr-<N>` testcase PR is open (even an empty draft) and compares branch content only after those PRs close. Found from PR #8765's own `Check TC PRs` failure.
- Source push: `vk/CBRD-27539-module-docs` = `cf800fa8ccc3ddddd18d38a0f02f1a7b9a2510ba` (fast-forward, verified; PR head matches). PR body unchanged.

## Revision 4 (source-specific checklists back to module AGENTS.md) — results

- 2026-11-26: user asked whether `docs/error-codes.md`, `docs/recovery-index.md`, and `docs/xasl-changes.md` belong in root `docs/` (reviewers may find source-only procedures there odd); agreed to move each into the owning module's `AGENTS.md` and approved all steps ("응 다 진행해줘").
- Source commit `6397314dafdbfac3e43140f949c5520ad204fb4f`: sections added to `src/base/AGENTS.md`, `src/transaction/AGENTS.md`, `src/xasl/AGENTS.md`; pointers fixed in root, `src/`, `src/compat/`, `src/query/`. Moved lines compared line by line with the deleted files (only relative links changed); link and anchor check 0 failures; `git diff --check` clean. Root `AGENTS.md` 426 words.
- Live body fingerprint before update matched revision 2 (`716906e0…`). Source push `vk/CBRD-27539-module-docs` = `6397314daf` (fast-forward, verified).
- PR #8765 body updated; live body sha256 `3f362554077f1af3587eb321f05cc7ebb6745eda0bd58151d311cbaa71b47ced` equals `pr2-body.md`. Still ready for review; title unchanged.
- Note: `hgryoo` had already approved at 08:52 UTC (before this push); greptile left one P2 inline comment on `unit_tests/AGENTS.md`.
