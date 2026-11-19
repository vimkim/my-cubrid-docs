# CBRD-28073

Documents for JIRA [CBRD-28073](https://jira.cubrid.org/browse/CBRD-28073): serial NEXT VALUE keeps the storage form of every `_db_serial` column and writes nothing to OOS. It replaces PR #8492 (CBRD-28035) and PR #8496 (CBRD-28052). Engine branch `CBRD-28073-serial-nextval-keep-form` over `feature/oos-merge` `8c478d8559` since the second 2026-11-19 rebase, head `8e9d71fda0` (earlier `8d736ff51c`, `3e541fcf67`, `67220b7e23`).

Last modified: 2026-11-19 (Asia/Seoul).

| File | What it contains | Created | Last modified | Why it was created |
| --- | --- | --- | --- | --- |
| [pr-body.md](pr-body.md) | PR body (Korean) for PR #8514 against `feature/oos-merge`, updated for the rebased head `8e9d71fda0` | 2026-11-12 | 2026-11-19 | Draft PR for the CBRD-28073 fix |
| [pr-context.md](pr-context.md) | Draft context: source commit, base, authorization, operations, execution record | 2026-11-12 | 2026-11-19 | Resume and publication bookkeeping |
| [ci-analysis.md](ci-analysis.md) | CI analysis of PR #8514 (Korean): 2026-11-13 shell and sql analysis and 2026-11-18 recollection for head `31c72e8342` run 43263461440; 2026-11-18 warning-level analysis after the rebase onto `feature/oos-merge` `3e541fcf67`, head `3960d1b215` run 44245545024 | 2026-11-13 | 2026-11-18 | Separate PR-caused failures from pre-existing ones |
| [jira-comment-design-review.md](jira-comment-design-review.md) | Design review (Korean) posted as JIRA comment 4778778: root-cause diagrams, alternatives, keep_form limits, at head `3960d1b215` | 2026-11-19 | 2026-11-19 | Record why keep_form was chosen over other fixes |
| [jira-comment-alter-merge-followup.md](jira-comment-alter-merge-followup.md) | Follow-up (Korean) posted as JIRA comment 4778780: the ALTER merge path at `serial.c:2285` leaves no OOS chain | 2026-11-19 | 2026-11-19 | Close the unchecked item of the design review |
| [code-review-pr8514.md](code-review-pr8514.md) | Five-reviewer code review of PR #8514 at head `8d736ff51c`: verdict changes-required (merge conflict with CBRD-27230 silently disables the fix), Greptile P1 dispositions, HA and page-space reproductions, pre-existing serial defects; addendum verifying the rebased head `8e9d71fda0` | 2026-11-19 | 2026-11-19 | Verify Greptile P1s and make the merge safe for others |
