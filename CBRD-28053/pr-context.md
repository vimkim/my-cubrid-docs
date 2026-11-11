# CBRD-28053 PR draft context

Status: PR body draft only. Not published. The user chose on 2026-11-11 to open the PR only after the A7 store-read fix (branch `sidecar-storeread`, commits `5587aeead` and `b1267b205`, work-tracker #913) is merged into `sidecar`. That merge changes the source revision, so this draft must be reconciled and reviewed again before publication.

| Field | Value |
| --- | --- |
| Ticket | CBRD-28053 (Task, Relates CBRD-26357) |
| Source commit drafted against | `5e67e9c1122a651e08342f98816f396b0ac4f439` |
| Source repository / branch | `vimkim/cubrid` (remote `vk`) / `sidecar` |
| Remote head | Branch does not exist on `vk` (checked 2026-11-11) |
| Base | `CUBRID/CUBRID` `develop`; branch starts at `e64a04a79` |
| Target repository | `CUBRID/CUBRID` |
| Operation | create |
| Proposed title | `[CBRD-28053] Add Sidecar out-of-row storage for large columns (POC)` |
| Body | `CBRD-28053/pr-body.md` |
| Context | `CBRD-28053/pr-context.md` |
| Detailed explanation | None; the body links `sidecar/` design documents |

## Proposed operations, after the A7 merge and a new review

1. Reconcile `pr-body.md` with the new `sidecar` head (A7 fix, A4 and A6 results), and record the new full source commit here.
2. Push `sidecar` to `vk` for the first time (`git push vk sidecar`).
3. Create a draft PR `vimkim:sidecar` -> `CUBRID/CUBRID:develop` with the reviewed body and title, assigned to `vimkim`.
4. Add the PR link to CBRD-28053 (`issues/CBRD-28053-sidecar-poc-epic.md` in my-cubrid-jira, then a description update).

The TC Branch Sync bot may create a testcase PR in each of the two testcase repositories when the PR targets `develop`. Another agent works in the `sidecar` worktree, so the push must use the head that agent has committed.
