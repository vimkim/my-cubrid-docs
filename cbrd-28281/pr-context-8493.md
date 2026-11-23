# PR context: update PR #8493 after CBRD-28281 technical verification

- Ticket: CBRD-28281 (split from CBRD-27925; Work1049, Work878)
- PR: https://github.com/CUBRID/cubrid/pull/8493 (Draft, base `develop`, state `OPEN`)
- Source branch: `CBRD-27925-emptied-set` (`vimkim/cubrid`)
- Local `SOURCE_COMMIT`: `96fb566bcc1781f48773061d765dcd136098bafa` (`[CBRD-28281] Test crash between empty OOS page reinit and insert`)
- Observed remote PR head: `f1c78ce70bb469f5d1d39204cc71a5fe3d832b54` (no source push before triage; `96fb566bcc` stays local until triage approval and `develop` rebase)
- Title (unchanged): `[CBRD-28281] Reuse emptied OOS pages in place instead of deallocating`
- Original live GitHub body SHA-256 (2026-11-23): `450bb5477f37eeb5edde1721995db13fdb4bbeea33298b2dfbf56c15b2e55fdf`
- Docs task branch: `docs/cbrd-28281-verify` → integration target `main`
- Body path: `cbrd-28281/pr-body-8493.md`
- Explanation path: `cbrd-28281/adr-0011-technical-verification.md`
- Public explanation URL: `https://github.com/vimkim/my-cubrid-docs/blob/main/cbrd-28281/adr-0011-technical-verification.md`

## Changes to the body

1. Resolve the two open questions in Remarks using evidence from `adr-0011-technical-verification.md`:
   - Vacuum drain delay (`0.34 s → 2.4 s`) root cause and continuous churn impact across 3 workloads.
   - Reinit-to-insert crash window hook/tests (local commit `96fb566bcc`) and zero-undo audit.
2. Note that `f1c78ce70b` remains the remote PR head while `96fb566bcc` is held locally for `develop` rebase after CBRD-28281 triage, leaving only multi-file concurrent churn unmeasured.
3. Link the public verification report URL as the final Remarks bullet.

## Proposed operations (pending user confirmation)

1. `my-cubrid-docs`: rebase `docs/cbrd-28281-verify` onto `main`, fast-forward merge into `main`, and push `origin main` (must precede `gh pr edit` so the linked explanation URL is live).
2. `CUBRID/cubrid` PR #8493: `gh pr edit 8493 -R CUBRID/cubrid --body-file cbrd-28281/pr-body-8493.md`, keeping Draft status and existing title, with no source push.
3. Verify live body and record the execution result in `cbrd-28281/pr-context-8493.md`.

## Execution record (2026-11-23)

- User confirmed: `"1. 2. 3. 4 진행"`.
- `my-cubrid-docs` `main`: integrated `e7985b6` and pushed `origin main` (explanation URL live).
- `my-cubrid-jira` `main`: integrated `90990ef` and pushed `origin main`; JIRA `CBRD-28281` description updated and verified via `cubrid-jira search CBRD-28281`.
- `gh pr edit 8493 -R CUBRID/cubrid --body-file cbrd-28281/pr-body-8493.md` applied this body (`sha256: 41516efa57817bf125fa3729ac57ded2d5d807a0c352a06d07d45f19e14b2a0d`). Read back: title `[CBRD-28281] Reuse emptied OOS pages in place instead of deallocating`, `OPEN`, `isDraft: true`, `base: develop`, `head: f1c78ce70bb469f5d1d39204cc71a5fe3d832b54`, body equal byte-for-byte (no source push).
