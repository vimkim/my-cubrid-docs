# CBRD-26357: engine PR #7990 body context (revision `4408135`)

Prepared: 2026-10-27, Asia/Seoul. Agent: `claude`.
Status: prepared; publication record below.
This context does not establish publication permission.

## Source and target

| Field | Value |
| --- | --- |
| Ticket | https://jira.cubrid.org/browse/CBRD-26357 |
| Operation | `update` existing body |
| Target repository | `CUBRID/cubrid` |
| PR | https://github.com/CUBRID/cubrid/pull/7990 |
| Existing title | `[CBRD-26357] Add out-of-row overflow storage` |
| Title operation | Preserve |
| PR state | `OPEN`, draft=`false` |
| Draft/ready operation | Preserve |
| Source repository | `CUBRID/cubrid` |
| Source branch | `feature/oos-merge` |
| SOURCE_COMMIT | `4408135c0833ec959da3590f12c14efa69610c7e` |
| Observed remote head | `4408135c0833ec959da3590f12c14efa69610c7e` |
| Base branch | `develop` |
| Previous body revision | [CBRD-26357-oos-engine-pr-body_5a70787_claude.md](CBRD-26357-oos-engine-pr-body_5a70787_claude.md) ([context](CBRD-26357-oos-engine-pr-context_5a70787_claude.md)) |
| Original decoded GitHub body SHA-256 | `3e03e75e83a888a82112616e7b5a31f62089514c54ab05a1c7b2e188e9e1316b` (equal to the previous body file) |

## Saved material

- Body: [CBRD-26357-oos-engine-pr-body_4408135_claude.md](CBRD-26357-oos-engine-pr-body_4408135_claude.md).
- The body still links the unchanged explanation [CBRD-26357-oos-engine_5a70787_claude.md](CBRD-26357-oos-engine_5a70787_claude.md). No new explanation for this revision.
- Docs task branch: `docs/pr7990-engine-pr-body-4408135`. Integration branch: `main` of `vimkim/my-cubrid-docs`.

## Scope of this revision

Requested by the user on 2026-10-27: make the body's unresolved items reflect the outcome of the three Greptile 4th-review P1 findings, and update what the new head requires. Other items stay unchanged.

| Finding | Thread | Outcome | Body change |
| --- | --- | --- | --- |
| P1-C, isolated fixtures delete existing databases | [r4380243555](https://github.com/CUBRID/cubrid/pull/7990#discussion_r4380243555) | Fixed in `224104a36` and `4408135c0` | New `Greptile P1` bullet: fixed |
| P1-B, `HEAP_HDR_STATS` layout versus develop-created 11.5 databases | [r4380243545](https://github.com/CUBRID/cubrid/pull/7990#discussion_r4380243545) | Confirmed; layout kept by the author's decision (ADR-0005 recreate policy). Develop changed the same struct in `e84a7f6dc` and the B-tree overflow header in `10a1df3e6` without a level change | `Greptile P1` bullet: policy and precedent. `호환성` bullet: states that boot does not reject such databases |
| P1-A, OOS slot reuse versus `RVOOS_DELETE` undo | [r4380243533](https://github.com/CUBRID/cubrid/pull/7990#discussion_r4380243533) | Confirmed defect; split out to [CBRD-27781](http://jira.cubrid.org/browse/CBRD-27781) by the author's decision. Realistic trigger: a vacuum OOS-delete system operation aborts on an error while another transaction inserts into the freed slot | `미해결` bullet: CBRD-27781 and trigger |

New head: the two commits since `5a70787fe` change only `unit_tests/oos/scripts/` and `unit_tests/oos/CMakeLists.txt` (`RESOURCE_LOCK` on fixture tests; CTest item count unchanged at 41). The `검증` bullet now names `5a70787` as the gha-ci revision and reports the local OOS CTest at `4408135` (39/39, focused selection plus the `no_logging`/`crash_recovery` fixtures; `test_oos_real_vacuum_server` and `test_oos_workspace` not run).

Out of scope and unchanged: CBRD-27237, CBRD-27230, CBRD-27057, the CDC quarantine, merge order, Purpose and Implementation.

## Evidence used

- `git diff 5a70787fe..4408135c0` in the source repository; `gh pr view 7990` metadata and body on 2026-10-27.
- Work512 evidence (local, not tracked): P1 reports for A, B, C, the code review record, and the CTest log of the 39/39 run at `4408135c0` content.
- `cubrid-jira search CBRD-27781`: open sub-task of CBRD-26978, created 2026-10-27.

## Known contradiction

The explanation [CBRD-26357-oos-engine_5a70787_claude.md](CBRD-26357-oos-engine_5a70787_claude.md) ("알려진 미해결 사항") still lists the three P1 threads as needing an answer or a fix. It describes head `5a70787fe` and was not changed in this revision.

## Proposed operations

1. Commit the body, this context, and the README rows on the docs task branch; rebase onto `main`, fast-forward `main`, and push `origin main`.
2. Update the body of PR #7990 with `gh pr edit 7990 --repo CUBRID/cubrid --body-file <body>`. Keep the title and draft/ready state.
3. Verify the published body SHA-256 equals the body file SHA-256 and record the result here.

No source push, PR comment, CI trigger, or explanation change.

## Publication record

- Authorized by the user for this revision (body update, docs commit and push) on 2026-10-27, through the delegating session.
