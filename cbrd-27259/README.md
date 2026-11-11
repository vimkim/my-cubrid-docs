# CBRD-27259

`STORAGE FORCE_INLINE` and fixed-type `STORAGE DEFAULT` for OOS columns.

- JIRA: https://jira.cubrid.org/browse/CBRD-27259
- PR: https://github.com/CUBRID/cubrid/pull/8416 (draft, source commit `9ae07b949`, base `feature/oos-merge`)

| File | What it contains | Created | Last modified | Why it was created |
| --- | --- | --- | --- | --- |
| [pr-body.md](pr-body.md) | First published PR description (source commit `e19d8c613`) | 2026-11-05 | 2026-11-05 | Text to upload as the PR body |
| [pr-context.md](pr-context.md) | Source, target, publication operations, and their results | 2026-11-05 | 2026-11-05 | Resume and review the PR publication |
| [pr-body-rev2.md](pr-body-rev2.md) | Revised PR description that adds the non-OOS `REC_BIGONE` notification | 2026-11-05 | 2026-11-05 | Update the PR body for source commit `9ae07b949` |
| [pr-context-rev2.md](pr-context-rev2.md) | Source, target, operations, and results for the revised body | 2026-11-05 | 2026-11-05 | Review and resume the body update |
| [pr-body-rev3.md](pr-body-rev3.md) | PR description for the `REC_BIGONE` rejection (source commit `6d6a01ef4`) | 2026-11-09 | 2026-11-11 | Replace the revision 2 body, which described the removed notification |
| [pr-context-rev3.md](pr-context-rev3.md) | Source, target, operations, results, and open CI items for revision 3 | 2026-11-11 | 2026-11-11 | Review and resume the body update |
| [pr-body-rev4.md](pr-body-rev4.md) | PR description after the base merge: message 1396, `loaddb` rejection remark, TC PR links | 2026-11-11 | 2026-11-11 | Keep the body accurate after the merge and the loader test change |
| [pr-context-rev4.md](pr-context-rev4.md) | Source, changes, operations, and open CI decision for revision 4 | 2026-11-11 | 2026-11-11 | Review and resume the body update |
| [ci-analysis.md](ci-analysis.md) | Failure attribution for gha-ci run 42865557030 on head `89496263e` | 2026-11-11 | 2026-11-11 | Separate failures caused by the PR from those caused by the base merge |
| [pr-body-rev5.md](pr-body-rev5.md) | PR description after review 5857391949: ALTER `FORCE_INLINE` row check, DDL limitation (CBRD-28051), assert follow-up (CBRD-27924) | 2026-11-11 | 2026-11-11 | Keep the body accurate after commit `87f6f85` |
| [review-20261111/](review-20261111/) | Analyses of the three comments in review 5857391949, reply drafts, and the CBRD-28051 description | 2026-11-11 | 2026-11-11 | Decide and answer each review comment with evidence |
