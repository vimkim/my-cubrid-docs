# PR #8299 release compiler repair

Date is 2026-10-29, Asia/Seoul. The intended reader is the PR author and reviewer.
The goal is to repair release compilation, verify the smallest change, and run one full CI cycle.
The user accepted this recovery path after the [CI investigation](ci_analysis_report_fd8624c_codex.md).

Source commit is `067aae4e4e91fec8c71c914a4c7fc3c4b13dcd65` in `vimkim/cubrid:CBRD-27785-oos-read-performance`.
Its parent is `fd8624c83f1f3c05b32d3fffb6ee4a1c9306c8b0`.
[PR #8299](https://github.com/CUBRID/cubrid/pull/8299) remains a draft targeting `feature/oos-merge`.
The task checkout is `/home/vimkim/gh/cb/CBRD-27785-unified-reader`.

## Change and contract

The change adds three lines to [heap_recdes_get_var_offset_pair](https://github.com/vimkim/cubrid/blob/067aae4e4e91fec8c71c914a4c7fc3c4b13dcd65/src/storage/heap_file.c#L11003).
The switch default now calls `assert_release(false)` and returns `ER_GENERIC_ERROR`.
Every successful path assigns both raw offset-table entries.
Both direct callers reject an error before reading those entries.
The preceding width guard already rejects unsupported widths.
The explicit switch exit gives GCC a control-flow path that preserves the output contract.
The observed defect is strict release compilation failure.
No runtime uninitialized read was established.

No signature, caller, valid-width decoding, COPY handling, grouped-read ownership, or recovery format changed.
No testcase or benchmark acceptance condition changed.
The scoped comment review found no added comments, suppressions, or findings.
The pre-commit code-style check passed.

## Strict compiler reproduction

The original compiler invocation was extracted from the failed release job's saved log.
The replay used official build image `cubridci/cubridci` at digest `sha256:f8ff31b3a5d7432cbf0f6e36ac82688f0cce0c961bbfc191ac2dc01612a8a887`.
Its compiler reports GCC 8.5.0, Red Hat 8.5.0-28.
The invocation retained `-O2`, `-DNDEBUG`, `-Wall`, and `-Werror`.
It contained no `-Wno-error` option.

| Mode | Original source | Patched source |
| --- | --- | --- |
| Standalone, SA_MODE | Exit 1. Fatal offset and next_off maybe-uninitialized diagnostics. | Exit 0. No warning or error diagnostics. |
| Server, SERVER_MODE | Exit 1. Fatal offset and next_off maybe-uninitialized diagnostics. | Exit 0. No warning or error diagnostics. |

Command and pinned-image parity were checked between the two executions.
Only the source bytes and output-artifact locations differ.
The standalone command comes from the saved CI invocation.
The server replay substitutes the corresponding server mode and export definitions.
The replay reused existing production-generated headers.
It is a targeted compiler check, not a fresh complete configure and build inside the CI container.
The hosted CI run below provides the full workflow qualification result.

The rerunnable diagnostic is `strict_compile.py` in the evidence directory below.
Its red and green directories preserve commands, compiler diagnostics, and source fingerprints.

## Rebuilt functional verification

An isolated detached checkout preserves the original benchmark build, installation, databases, and selected source environment.
Its source contains exactly the same three-line patch.
The PR file, test-copy file, and strict-green file have SHA-256 `c25c51454656520b20a1d143ae7c85f621e5a8a9413928967f82321f0cdf852b`.
The committed source blob was checked against that fingerprint after verification.

The isolated preset is `release_repair_oos`.
The build used GCC 11.5 and RelWithDebInfo with OOS unit tests enabled.
Configuration, build, and installation used the maintained preset-aware local interface.
Both standalone and server heap_file.c objects were rebuilt.
Installation completed successfully before the focused selections ran.

| Check | Result |
| --- | --- |
| Grouped-reader characterization selection | 15 of 15 CTest entries passed. |
| Crash-recovery selection | 3 of 3 CTest entries passed. |
| Source and tested-copy fingerprint equality | Passed. |
| Committed blob and strict-green fingerprint equality | Passed. |
| Staged diff and code-style checks | Passed. |

The CTest counts include setup and cleanup fixtures.
They do not establish whole-corpus equivalence.
The host preset retains its existing maybe-uninitialized warning downgrade.
The independent strict GCC 8.5 replay supplies the compiler regression evidence.

The source checkout's environment and preset files were not written.
Its selected preset remains `release_gcc`.
No before-and-after file hashes were recorded for those files, so no such hash comparison is claimed.
The detached verification checkout and isolated installation remain available under the evidence directory.

## Publication and one CI cycle

Commit `067aae4e4` was pushed normally to the existing PR head.
Immediately before posting the CI request, the PR head, draft status, destination, comments, and current checks were rechecked.
No competing request or current-head gha-ci run was present.
The previous run was completed.
Both feature testcase baseline checks passed.

Exactly one [`/run all` request](https://github.com/CUBRID/cubrid/pull/8299#issuecomment-6489386094) was posted.
All five gha-ci contexts picked up [run 40827634555](https://github.com/CUBRID/cubrid/actions/runs/40827634555) for the new source.
The required-check query reports no required checks for the feature-targeted branch.
That query does not waive the observed gha-ci contexts or TC Merge Gate.

Run 40827634555, attempt 1, completed with SUCCESS.
The current-head gha-ci contexts all report SUCCESS and link to that run.

| CI component | Terminal result |
| --- | --- |
| Release build | SUCCESS |
| Debug build | SUCCESS |
| Shell | 50 of 50 shards passed. |
| SQL | 10 of 10 shards passed. |
| Medium | 1 of 1 shard passed. |

Previously failing shell shards 07 and 16 both passed in this execution.
That observation does not establish the cause of the earlier failures or prove flakiness.
No follow-up source repair, second push, or second CI request occurred after this cycle.
The worktree policy requires reporting this result and stopping for the user's next direction.

The compiler repair requires no TC repository changes.
TC PR [#3898](https://github.com/CUBRID/cubrid-testcases/pull/3898) and [#4589](https://github.com/CUBRID/cubrid-testcases-private-ex/pull/4589) are still OPEN drafts at final verification.
They require human closure because this repair needs no TC changes.
The TC Merge Gate remains unresolved under the supplied worktree policy.
No source merge, TC merge or closure, PR-body edit, or documentation publication is part of this execution.

## Evidence and limits

Evidence directory is `/mnt/nvme/data-5/tmp/CBRD-27785-release-repair-20261029-JofT1o`.
It retains `live-state.json`, `focused-verification.json`, `strict-red/result.json`, `strict-green/result.json`, and the compiler replay script.
Host build, installation, characterization, and recovery logs are under `host/`.
The detached checkout is `host/worktree`.
Its isolated installation is `host/install`.
Publication records include `source-push.log`, `trigger-receipt.json`, and the pre-trigger snapshots.
The watcher retains `ci-current.json` and `ci-final.json`.
`completion-pr-audit.json` records the current head, all checks, body fingerprint, and open TC PRs.

The preceding investigation's SQL count mismatch and unknown shell causality remain historical limitations.
No claim that the two shell failures were flaky follows from this compiler fix.
This execution did not repeat the all-suite collector or establish that its earlier SQL count mismatch is resolved.
Residual UPDATE work remains separate under CBRD-27816 and Work Item 571.
The earlier PR-body and common-reader drafts remain local and pinned to fd8624c.
They require revision reconciliation and a separate publication decision before use.

Laziness Protocol kept the source change to three lines.
Model the Domain retained the offset-pair success contract.
Sequence Work into Verifiable Units required reproduction, source change, verification, and publication in order.
Prove It Works required matching compiler commands and rebuilt test binaries before push.
