# CBRD-26659: shell TC PR body publication context

Prepared: 2026-10-27, Asia/Seoul. Agent: `codex`.
Status: published and checked. GitHub body matches the approved file.
This context does not establish publication permission.

## Source and target

| Field | Value |
| --- | --- |
| Ticket | https://jira.cubrid.org/browse/CBRD-26659 |
| Operation | `update` existing body |
| Target repository | `CUBRID/cubrid-testcases-private-ex` |
| PR | https://github.com/CUBRID/cubrid-testcases-private-ex/pull/4365 |
| Existing title | `[CBRD-26659] Draft: TC changes for PR CUBRID/cubrid#8128` |
| Title operation | Preserve |
| PR state | `OPEN`, draft=`true` |
| Draft/ready operation | Preserve |
| Source repository | `CUBRID/cubrid-testcases-private-ex` |
| Source branch | `tc/pr-8128` |
| SOURCE_COMMIT | `8486abdac52ffc1ea4cae3c8a28fad888014caea` |
| Observed remote head | `8486abdac52ffc1ea4cae3c8a28fad888014caea` |
| Base branch | `feature/oos-merge` |
| Observed base commit | `dd12b36a249e48a63725113af59ed4b013c3894a` |
| Engine for recorded CI | `c4c4f5c5ed55fb0130c72bb261061ec441662554` |
| Original decoded GitHub body SHA-256 | `bb2bbe9343b602887d731b29212defa0c28d5c250776838883c48ef534d17eab` |
| Prepared body file SHA-256 | `7d4a5537bdd04487afc3972c8e14ed93cab48138bffa369a2a828c1cee283354` |

## Saved material

- Body: [CBRD-26659-oos-shell-regressions-pr-body_8486abd_codex.md](CBRD-26659-oos-shell-regressions-pr-body_8486abd_codex.md).
- Context: `cbrd-26659/CBRD-26659-oos-shell-regressions-pr-context_8486abd_codex.md`.
- Previous published description: [CBRD-26659-oos-shell-regressions-pr-body_27db3d6_codex.md](CBRD-26659-oos-shell-regressions-pr-body_27db3d6_codex.md).
- Docs task branch: `docs/work456-tc-pr-bodies-20261027`.
- Docs integration branch: `main`, remote `origin` of `vimkim/my-cubrid-docs`.
- Initial docs integration commit: `def505f`.
- Detailed explanation: none. The body links existing revision-pinned TC inventories.

The earlier description remains historical. Its October 8 native counts do not
establish results for SOURCE_COMMIT. The new body describes the complete current
PR diff and current execution selection. This description update does not change testcase bodies or answers.

## Evidence and limits

- The PR diff and Work456 operation O45 reconcile all 133 OOS shell entries, including CBRD27237. Ticket-prefix matching is not the population rule.
- `disabled/oos-pr8128-inventory.tsv` records all 133 entries and each observation's CI run and TC revision. Selection is 69 enabled and 64 disabled.
- The disabled selection contains 61 observed failures and 8 cases over 60 seconds, with 5 entries in both groups. These counts describe selection across the named observations, not one combined test run.
- OOS execution uses Bash/jq and the C++17 native helper. It requires no Python runtime helper. The complete PR diff contains no added Python file.
- Run [40335925801](https://github.com/CUBRID/cubrid/actions/runs/40335925801) is a shell-only PASS at this private TC head and the Engine above. The checked shell collection records 3,553 planned, 3,523 passed, 0 failed, 30 skipped, and 0 unrun.
- All 69 enabled OOS entries executed and passed. The run skipped no OOS entry and recorded none over 60 seconds. Maximum OOS duration was 45.180 seconds. All 64 disabled entry paths were absent from execution.
- SQL and medium PASS statuses belong to the separate run40324320840 and unchanged public TC head4f6557f7f. The new shell-only run did not execute those suites.
- Disabled failures receive no passing-coverage credit. Broader Work456 independent qualification remains incomplete. Performance comparison and HA Work463 remain deferred.
- The current checks contain no automated TC Merge Gate entry for `feature/oos-merge`. Both TC PRs remain open for human review and merge.

## Exact proposed operations for both TC bodies

One confirmation will cover this shared operation list:

1. Reread both saved bodies. Check both remote PR heads, branches, bases, draft states, and original body fingerprints. Reconcile any changed source revision or GitHub body before publication.
2. Rebase `docs/work456-tc-pr-bodies-20261027` onto the current local `main`. Review the incoming files and links. Fast-forward the docs destination and push `origin main`. The retained files are the two new bodies, their two contexts, and `cbrd-26659/README.md`.
3. Update only the body of public TC PR3688 from `CBRD-26659-oos-sql-regressions-pr-body_4f6557f_codex.md` and private TC PR4365 from `CBRD-26659-oos-shell-regressions-pr-body_8486abd_codex.md`. Preserve titles, draft/ready states, head branches, and bases.
4. Read both GitHub bodies and check their decoded UTF-8 bytes against the approved files. Record per-PR results and body fingerprints in these contexts. Update only publication status in the docs README. Commit and push the docs execution records under the same integration approval.
5. After checking integration and publication, remove only this merged docs task worktree and remove its local topic branch without force. Preserve valuable local material.

These operations do not include source/TC commits or pushes, CI triggers, JIRA
writes, PR merges or closures, or remote branch deletion. TC PR merge, closure,
and branch deletion remain human actions.

## Publication record

- Confirmation: the user said `yes publish` after the assistant presented both body drafts and the shared operation list.
- Docs integration/push: commit `57ce44eb6e5e18802b77f70e604e63d40725627b` was fast-forwarded into `main` and pushed to `origin main` before the GitHub edits.
- GitHub body update: https://github.com/CUBRID/cubrid-testcases-private-ex/pull/4365, checked at `2026-10-26T15:21:46.991266+00:00`.
- Checked remote body fingerprint: `7d4a5537bdd04487afc3972c8e14ed93cab48138bffa369a2a828c1cee283354`. Decoded UTF-8 bytes equal the approved body file.
- GitHub returned the same source revision, head/base branches, OPEN state, title, and draft state.
- This attempt changed only the two PR bodies and the approved docs. It did not push source/TC commits or trigger CI.
