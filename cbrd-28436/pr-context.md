# CBRD-28436 PR draft context

## Source and target

| Item | Value |
| --- | --- |
| Ticket | [CBRD-28436](https://jira.cubrid.org/browse/CBRD-28436) (Sub-task of CBRD-26978; follow-up to CBRD-26357 OOS) |
| SOURCE_COMMIT | `689429c38319244d81661d55a347b7f3de93505b` |
| Base | `CUBRID/cubrid` `develop` at `bed13689eb` |
| Local source branch | `CBRD-26357-vacuum-latch-hang` (worktree name predates the ticket) |
| Source push | `vimkim/cubrid` (remote `vk`) branch `CBRD-28436` |
| Observed remote head before push | branch absent on `vk` (2026-11-27) |
| Target | `CUBRID/cubrid`, base `develop` |
| Operation | `create` (no existing PR for head `vimkim:CBRD-28436`) |
| Proposed title | `[CBRD-28436] Flush the OOS vacuum test log through its last record` |
| Body | `cbrd-28436/pr-body.md` |

## Proposed operations

1. Push `689429c383` to `vk` as `CBRD-28436` (new branch, no force).
2. `gh pr create --repo CUBRID/cubrid --draft --base develop --head vimkim:CBRD-28436 --assignee vimkim --title <title> --body-file cbrd-28436/pr-body.md`.
3. Not included: marking ready, requesting reviewers, `/run` CI trigger.

## Authorization

2026-11-27: the user approved rebasing the fix onto `origin/develop`, pushing the topic branch to `vk`, and creating a Draft PR on `CUBRID/cubrid` for CBRD-28436, and said not to mark it ready, request reviewers, or trigger `/run all`.

## Verification before publication

- Rebased onto `develop` `bed13689eb`; commit retagged from `[CBRD-26357]` to `[CBRD-28436]` (was local `76328a4343`).
- Build: GCC `RelWithDebInfo`, `UNIT_TEST_OOS=ON`.
- `oos_setup_db` → `test_oos_real_vacuum_latch_timeout` → `_retry` → `_shutdown`: 3/3 pass (retry 10.97-11.45 s).
- `ctest -R '^(oos_setup_db|test_oos_real_vacuum.*)$'`: 7/7 pass.
- Before the fix (develop `0eec910fc1`): the same order timed out 10/10.

## Execution record

- 2026-11-27: pushed `689429c383` to `vk` `CBRD-28436` (new branch); `git ls-remote` shows the same commit.
- 2026-11-27: created draft PR [CUBRID/cubrid#8801](https://github.com/CUBRID/cubrid/pull/8801); verified draft, base `develop`, head `vimkim:CBRD-28436` at `689429c383`, assignee `vimkim`, no review requests, body equal to `pr-body.md` (sha256 prefix `eebabd9f2ec530d6`).
- Not done (per instruction): ready-for-review, reviewer requests, `/run` CI.
