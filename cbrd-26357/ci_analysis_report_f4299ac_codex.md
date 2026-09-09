# CI Failure Analysis: PR #6864 at `f4299ac`

## Executive Summary

The supplied runs contain **11 failure occurrences across 7 distinct tests**, accounted for by three causes: OOS error-number answer drift (6 occurrences / 4 tests), historical CDC reads of reclaimed OOS values (4 / 2), and an intermittent append-LSA torn read (1 / 1). The medium suite passes. Local repairs and existing PR verification are recorded below; this is not an all-CI-green claim.

## CI Snapshot

| Suite | Job/run | Success | Failure | Skipped | Error / unknown |
| --- | --- | ---: | ---: | ---: | ---: |
| CircleCI medium | 153254 | 975 | 0 | 0 | 0 / 0 |
| CircleCI SQL | 153253 | 17457 | 2 | 0 | 0 / 0 |
| CircleCI shell | 153250 | 3240 | 4 | 30 | 0 / 0 |
| Actions shell | 34207150213 | 3239 | 5 | 30 | 0 / 0 |

[SQL job](https://circleci.com/gh/CUBRID/cubrid/153253), [shell job](https://circleci.com/gh/CUBRID/cubrid/153250), [medium job](https://circleci.com/gh/CUBRID/cubrid/153254), [Actions run](https://github.com/CUBRID/cubrid/actions/runs/34207150213).

## Evidence Scope

Engine commit: `f4299ac0cd777a2a964c1f197ae5ebf9841a4936`; PR branch `feat/oos`, original PR base `develop`. Collected 2026-09-09 using cubrid-ci 0.1.0 (3e9502f72350). Collector bundles: `/home/vimkim/gh/cubrid-circleci-analyzer/data/CBRD-26357/f4299ac/`. Separate Actions API/XML bundle: `/home/vimkim/gh/cubrid-circleci-analyzer/data/api-pr6864-run34207150213/`.

Actions event is issue_comment and run metadata reports workflow SHA `14d21ef`; build-read logs, per-shard build.read and collect summary independently prove that its actual engine is f4299ac. All 50 shards published results. SQL sources/answers are pinned to testcase SHA `54ebf3b458506f1360b5a03992b4987f4783488e`. Actions shell tc.read pins `777b97745076ba2c48cf7e103857f0abbc765b5d`. CircleCI shell sources link only moving develop; exact testcase revision is unknown (collector null; additional checkout-log download returned HTTP404). Local shell replay therefore follows the exact Actions testcase revision, not an invented CircleCI revision.

## Failure Inventory

| Suite | Job / shard | Test | Root cause |
| --- | --- | --- | --- |
| test_sql | 153253 | sql/_13_issues/_14_1h/cases/bug_bts_10516.sql | answer drift |
| test_sql | 153253 | sql/_15_fbo/_02_qa_test/cases/fbo_ddl02.sql | answer drift |
| test_shell | 153250 | shell/_06_issues/_12_2h/bug_bts_9836/cases/bug_bts_9836.sh | answer drift |
| test_shell | 153250 | shell/_06_issues/_14_2h/bug_bts_14120/cases/bug_bts_14120.sh | answer drift |
| test_shell | 153250 | shell/_37_elderberry/cbrd_23842_cdc/bug/cbrd_27075/cases/cbrd_27075.sh | CDC history lifetime |
| test_shell | 153250 | shell/_37_elderberry/cbrd_23842_cdc/bug/cbrd_27064/cases/cbrd_27064.sh | CDC history lifetime |
| Actions shell | 34207150213 / 20 | shell/_06_issues/_12_2h/bug_bts_9836/cases/bug_bts_9836.sh | answer drift |
| Actions shell | 34207150213 / 34 | shell/_06_issues/_11_1h/bug_bts_4633/cases/bug_bts_4633.sh | append-LSA torn read |
| Actions shell | 34207150213 / 43 | shell/_37_elderberry/cbrd_23842_cdc/bug/cbrd_27064/cases/cbrd_27064.sh | CDC history lifetime |
| Actions shell | 34207150213 / 46 | shell/_06_issues/_14_2h/bug_bts_14120/cases/bug_bts_14120.sh | answer drift |
| Actions shell | 34207150213 / 49 | shell/_37_elderberry/cbrd_23842_cdc/bug/cbrd_27075/cases/cbrd_27075.sh | CDC history lifetime |

## Root-Cause Analysis

### Error-number answer drift — CBRD-27403

Observed: both SQL diffs contain only expected `Error:-1381` versus actual `Error:-1382`. Shell cases fail the default call-stack activation list comparison. Source diff from 2940b1c to f4299ac adds `ER_CDC_ARCHIVE_KEPT=-1379`, shifts OOS definitions, and retains symbolic references in `system_parameter.c`. This establishes a direct merge-related answer mismatch with high confidence.

The repair changes two SQL answers to -1382 and three shell answers from the old default trio -1380,-1382,-1383 to -1381,-1383,-1384. Test inputs and comparison assertions remain intact. The source definitions independently justify the new answers. Exact local shell RED/GREEN replay passes 3/3 checks for bug_bts_9836 and 2/2 for bug_bts_14120. SQL bug_bts_10516 reproduces NOK with the original answer and passes 1/1 with the fix; fbo_ddl02 likewise reproduces NOK with the original answer and passes 1/1 with the fix.

### CDC historical-image lifetime — CBRD-26939

Observed: cbrd_27064 fails after INSERT succeeds; DELETE extraction is incomplete and UPDATE extraction fails. Its stack reaches OOS page reads through CDC. cbrd_27075 crashes in oos_check_head_header through the CDC path. Existing diagnosis and accepted durable supplemental-image design identify reclaimed OOS references in historical images; the original source at f4299ac lacks the implementation.

Reuse [PR #7897](https://github.com/CUBRID/cubrid/pull/7897), head `68c6d0b31322e1cf4eacda03f58ed56be8cdde39`, which already targets feat/oos. Independent collection of its CircleCI shell job153479 explicitly confirms cbrd_27064 success (90.473s) and cbrd_27075 success (201.822s). Confidence is high for these two repairs, but that PR's whole shell suite still has 15 failures and SQL has 2. Its SQL testcase revision is `2f8cd423ab28d69d5b77ea70745aa55e7c748f5d`, unlike PR6864's `54ebf3b4`. Those answers expect successful INSERTs and then show cascading zero-row output; the two numeric-answer edits here are not proof of repairing PR7897's SQL branch. Its shell `supp19` observes 5 USER records versus expected2, consistent with the new per-DML user metadata; `cbrd_23119` has a restoredb core after an active-log mount failure, and `bigPageSize` lacks usable failure details. Attribution of the latter two remains unresolved. Preserve separate evidence at `/home/vimkim/gh/cubrid-circleci-analyzer/data/CBRD-26939/68c6d0b/`; do not represent the whole PR as passed.

### Append-LSA torn read — CBRD-27400

Observed: Actions shard34 produces an assert through log_get_undo_record and heap_get_visible_version_from_log during bug_bts_4633. Prior diagnosis contains deterministic debugger scheduling evidence for mixed pageid/offset reads during rollover. The current stack matches that established defect; CircleCI passing the same intermittent test does not falsify it.

Existing develop PR7904 provides commit a59029274. An exact four-file backport applied cleanly to f4299ac, retaining the OOS-specific LOG_LSA_QUEUE declaration. Published [draft PR #7908](https://github.com/CUBRID/cubrid/pull/7908), branch CBRD-27400-oos-append-lsa, commit `1efcabd2ff700540f8d50408609620f3be20e839`. Its original JDBC testcase passes in 168s and all 27 configured CTest tests pass in 141.65s. Standards and Spec reviews report zero findings. This verifies the local candidate, not every possible race schedule or remote CI. The separate OOS reclaim-horizon plain read remains outside the exact backport.

## Local Verification Evidence

- [Attempt identities, binary hashes and log paths](ci-fix/pr-6864/local-verification.json).
- [Backport CTest log](ci-fix/pr-6864/build-test-append-lsa-2.log): 27/27 pass.
- Shell exact RED/GREEN records: `/home/vimkim/.cache/codex/pr6864-f4299ac/shell-{red,green}-{9836,14120}/output.log` and each cases/*.result.
- SQL exact RED/GREEN records: `/home/vimkim/.cache/codex/pr6864-f4299ac/sql-red-10516-2/ctp.log`, `sql-green-10516/ctp.log`, `sql-red-fbo/ctp.log`, `sql-green-fbo/ctp.log`; complete CTP outputs below the private CTP/sql/result tree.
- Original JDBC backport result: `/home/vimkim/.cache/codex/pr6864-append-lsa/jdbc-green-4633/output.log` and cases/bug_bts_4633.result. Debug rather than CI optdebug; core writing disabled, so the original result and engine assert/abort logs were checked explicitly.

## Other Checks and Limits

- Formatting, license, cppcheck and memory-wrapper related checks on the tested head pass.
- Check TC PRs fails because companion testcase PRs3159 and3782 remain open. This is the intended merge gate; do not close or merge them merely to turn it green.
- Actions run34214479285 discovered via check metadata targets CDC build68c6d0b, not f4299ac. Its plan correctly rejects reuse of failures from old run34186373809 at2940b1c. It ran no test shards and is not another PR6864 testcase failure.
- Branch-protection required-check endpoint returns404; required-check completeness is not proven.
- No binary core downloads. Available XML stacks, diffs, logs and local reproduction support the diagnoses.
- Original dirty source submodules and user files were preserved; all repairs use isolated worktrees. Tests isolate network, IPC, PID, mount and /tmp sockets.
- Initial SQL local attempt ran zero cases because the baseline install copy lacked JDBC; it is an invalid setup attempt, not a regression result. Adding the pinned built JDBC resolved setup. Locale generation completed once and is reused unchanged.

## Next Actions

Published drafts:

- Engine backport: https://github.com/CUBRID/cubrid/pull/7908 (base feat/oos, head1efcabd).
- SQL answer fix: https://github.com/CUBRID/cubrid-testcases/pull/3469 (base tc/pr-6864, headb4e774d).
- Shell answer fix: https://github.com/CUBRID/cubrid-testcases-private-ex/pull/4116 (base tc/pr-6864, head06fb326).
- Existing CDC fix: https://github.com/CUBRID/cubrid/pull/7897 (base feat/oos, head68c6d0b).

Posted one `/run all` on PR7908 at the verified head1efcabd: https://github.com/CUBRID/cubrid/pull/7908#issuecomment-5597530397. Full remote verification is pending. The answer PRs are unmerged and therefore do not alter the original PR6864 CI testcase branch yet. No source/testcase PR was merged, no assertions were weakened, and no existing repair branch was overwritten.

Next: verify PR7908's exact engine/testcase selections, retain unrelated failures explicitly, and integrate reviewed repairs through the normal merge process. Do not claim PR6864 is green before its feature and testcase branches contain all repairs. Durable work item:86; detailed ledger:`ci-fix/pr-6864/index.md`.
