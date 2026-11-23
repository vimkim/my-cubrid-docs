# PR context: retarget PR #8493 from CBRD-27925 to CBRD-28281

- Ticket: CBRD-28281 (split from CBRD-27925; Work1049, Work878)
- PR: https://github.com/CUBRID/cubrid/pull/8493 (Draft, base `develop` since 2026-11-20)
- Observed remote head: `f1c78ce70bb469f5d1d39204cc71a5fe3d832b54` (vimkim:CBRD-27925-emptied-set); no source push in this operation
- Previous body: `cbrd-27925/pr-body-stage2.md` (equal to the live body on 2026-11-23)
- New body: `cbrd-28281/pr-body-8493.md`
- Current title: `[CBRD-27925] Reuse emptied OOS pages in place instead of deallocating`
- Proposed title: `[CBRD-28281] Reuse emptied OOS pages in place instead of deallocating`

## Changes to the body

1. Ticket link CBRD-27925 → CBRD-28281.
2. Purpose: state that ADR-0009 is already met by #8434 (CBRD-27925) and that this PR reduces the reuse cost; adoption is decided in CBRD-28281, so the PR stays Draft.
3. Remarks: replace the stale "stacked on #8434, before #8434 merges" note with the #7990 develop merge, the base change to develop, the conflict, the five own commits, and rebase after triage.

## Proposed operations

1. `gh pr edit 8493 -R CUBRID/cubrid --title "[CBRD-28281] Reuse emptied OOS pages in place instead of deallocating" --body-file cbrd-28281/pr-body-8493.md`; keep Draft; verify title and body.
2. Merge this docs branch into my-cubrid-docs `main` (ff-only) and push `main`.

User approval (2026-11-23): plan item 3 "yes" (title and body), pending review of this draft.
