# PR 6864 CI repair

## Identity and scope

- Work tracker: 86; actor: codex-01a084d8.
- PR: https://github.com/CUBRID/cubrid/pull/6864 (open, feat/oos -> develop).
- Source: /home/vimkim/gh/cb/oos-storage at f4299ac0cd777a2a964c1f197ae5ebf9841a4936.
- Requested repair PRs: separate root-cause branches targeting feat/oos.
- Preserve existing modified CCI/JDBC submodules and untracked user files.
- User authorized the proposed investigation, implementation, separate ticketed draft PRs and CI verification workflow on 2026-09-09. No permission to weaken assertions or choose unspecified behavior.

## Current stage

Published repairs; awaiting PR7908 remote CI. CircleCI analyzed: SQL 153253, shell 153250, medium 153254. Actions 34207150213 executes build SHA f4299ac despite its workflow metadata head being develop SHA 14d21ef; build-read log and collect summary establish engine identity. Actions testcase revision: private-ex 777b97745076ba2c48cf7e103857f0abbc765b5d.

Evidence: /home/vimkim/gh/cubrid-circleci-analyzer/data/CBRD-26357/f4299ac/ and separate API bundle /home/vimkim/gh/cubrid-circleci-analyzer/data/api-pr6864-run34207150213/.

## Initial inventory

- Medium 153254: 975 tests, zero failures.
- Actions 34207150213: 3244 executed, 3239 passed, 5 failed, 30 skipped; all 50 shards published.
- Actions failures: bug_bts_9836 (shard 20), bug_bts_4633 (34), cbrd_27064 (43), bug_bts_14120 (46), cbrd_27075 (49). Full paths in API failed.log summary.
- CircleCI SQL153253:17457 passed,2 failed; shell153250:3240 passed,4 failed,30 skipped. All11 failure occurrences across7tests accounted for in the report.
- Check TC PRs (34204701926) fails because companion TC PRs 3159 and 3782 remain open; this is the intended merge gate, not an engine error. Later Actions plan failure 34214479285 belongs to CDC PR7897 (target build 68c6d0b), not this tested head; its own rerun request incorrectly referenced old run 34186373809 at 2940b1c. Exclude it from PR6864 runtime counts. Earlier cancelled run 34214219609 retained only as unclassified history.

## Coordination and local safety

Existing CDC work item 70 / CBRD-26939 and append-LSA work item 80 / CBRD-27400 may cover failures. Verify before duplicating work or changing their branches.

Read local verification incident (2026-09-05, updated 2026-09-08): safe execution must isolate PID, IPC, network, mount, and /tmp Unix sockets; private install and configuration. Never run unisolated shell CTP against shared services.

## Next action

Follow PR7908 CI using trigger receipt5597530397. No duplicate trigger. Review/integrate published engine and testcase PRs before revalidating original PR6864.

## Local progress (2026-09-09)

- Baseline f4299ac built in isolated worktree `/home/vimkim/gh/cb/oos-ci-f4299ac`; initial bootstrap stow-path issue resolved by explicit stow target followed by normal prepare/bootstrap. Original source worktree unchanged.
- Baseline installation copied to `/home/vimkim/.cache/codex/pr6864-f4299ac/install` before backport edits.
- `bug_bts_9836`: exact original failure reproduced, patched answers 3/3 subchecks pass. `bug_bts_14120`: original first-check failure reproduced, patched run passes both subchecks.
- Answer patch set: separate SQL worktree `/home/vimkim/gh/tc/oos-ci-error-codes-sql`, shell `/home/vimkim/gh/tc/oos-ci-error-codes-shell`. Five answer files total; no testcase statements changed.
- Backport branch `CBRD-27400-oos-append-lsa` at 1efcabd with the committed exact a590292 backport on f4299ac; build succeeds; Standards and Spec independent reviews both zero findings. OOS-specific reclaim-horizon atomic-read follow-up remains outside this exact JDBC backport.
- Existing CDC PR7897 targets feat/oos; existing append-LSA PR7904 targets develop. No duplicate CDC PR created.
- Initial JIRA access returned HTTP503. Access recovered; duplicate search completed, CBRD-27403 was created, and its final description was published and read back.

## Publication receipts

- CBRD-27403 created and read back; initial create attempt with an invalid QA Scenario field failed HTTP400 without creating an issue. Removed that optional field, succeeded once (id1419890).
- Engine backport PR7908 -> feat/oos, head1efcabd2ff700540f8d50408609620f3be20e839.
- SQL companion PR3469 -> tc/pr-6864, commitb4e774d1f.
- Shell companion PR4116 -> tc/pr-6864, commit06fb3262e.
- CDC existing PR7897 reused; CircleCI153479 confirms both targeted CDC tests pass, but15 other shell failures and2SQL failures remain in that PR's wider suite.
- PR7908 trigger receipt: /run all, comment5597530397, same remote head1efcabd after posting. Never duplicate this trigger while queued.
- Detailed backport doc committed/pushed using isolated docs worktree branch codex/pr6864-ci-fixes, commitf3597ba, to origin/main. This avoided publishing unrelated unpushed docs work in the primary docs worktree.
- New issue report committed/pushed as my-cubrid-jira af35d0e.
- Exact local RED/GREEN for both SQL and both shell cases complete. Original JDBC backport case OK;27/27CTest passed. All attempts and install hashes in local-verification.json.

## Current next step

Await PR7908 remote CI; all proposed patches are published as drafts. Original PR6864 remains failing until maintainers merge the engine and testcase repairs. Wider failures on CDC PR7897 remain explicit follow-up; do not weaken its checks or manufacture success from its two targeted passes.

## Direct Testcase Publication (2026-09-09 08:04 UTC)

User requested direct pushes to both canonical tc/pr-6864 branches and closure of companion PR3469/4116. SQL fast-forwarded to b4e774d1f; shell to06fb3262e; both remote full SHAs verified. GitHub automatically marked both PRs MERGED because the pushed commits include their exact heads. No separate merge/close command, force push, new CI trigger, or tc/pr-7908 branch creation. Earlier unmerged-answer notes are historical and superseded by this receipt.
