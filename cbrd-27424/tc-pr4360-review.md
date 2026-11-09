# TC PR4360 code review

The goal is to review the restored testcase changes in [PR4360](https://github.com/CUBRID/cubrid-testcases-private-ex/pull/4360) before requesting human review. The intended readers are reviewers of the partition-loader assertions and the CSQL lock-observation handshake.

**Follow-up verdict at PR head `1d349fe7`: `changes-required`. One confirmed inherited testcase weakness, SL-1.** Fault injection now proves that SQL diagnostics can escape this testcase's verdict. A minimal correction is verified in local commit `8de2ebcf7ab047277017af81525c837ccce982f5`, pending authorization to push the source branch. See [the follow-up evidence](#follow-up-fault-injection-and-correction).

The initial bounded review found no material defect introduced by the inspected change. That attribution remains unchanged. Its earlier zero-finding verdict and optional follow-up decision predated the fault injection below and no longer describe the required action on the current PR head.

Review date: 2026-11-09, Asia/Seoul. Related engine work is [CBRD-27424](https://jira.cubrid.org/browse/CBRD-27424) and [engine PR7925](https://github.com/CUBRID/cubrid/pull/7925). The testcase review does not re-review the merged engine implementation.

## Immutable scope

| Item | Identity |
| --- | --- |
| Repository | `CUBRID/cubrid-testcases-private-ex` |
| Base and merge base | `75a02020e19be4bfc64e47f7c7a3d5c2b02d7676` |
| Head | `1d349fe7392b41384bbf3bdb327755f10f4a4286` |
| Complete patch SHA-256 | `a675f4342d218fe3d2d1c24f20f4b33ca801e94623179e6c5d00fe8e4e758892` |
| Runtime engine | `95ff126a8464179a2fab3092b6f56468528ab954`, `debug_gcc`, version `11.5.0.2790-95ff126` |
| Changed paths | Two shell files, 156 additions and 39 deletions. No renames, deletions, binary changes or submodules. |

The comparison was resolved from Git objects and is reproducible with:

```sh
git diff --find-renames --binary 75a02020e19be4bfc64e47f7c7a3d5c2b02d7676 1d349fe7392b41384bbf3bdb327755f10f4a4286
```

Every changed hunk has an owner in [coverage](tc-pr4360-coverage.md). The testcase tree contains no applicable AGENTS.md or contribution document. Personal CUBRID policy and the review contract were applied. The linked issue was fetched on the review date; it describes standalone loader/workspace OOS support. The partition testcase additionally follows the existing [independent partition assessment](../cbrd-27089/tc-pr-4335-review_10f350029_codex.md), whose older execution claims are not treated as current-head evidence.

## Changed behavior and safety facts

### Partition-loader assertions

The [partition script](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/1d349fe7392b41384bbf3bdb327755f10f4a4286/shell/_35_cherry/issue_21654_server_side_loaddb/partition_tbls/cases/partition_tbls.sh#L55) preserves the basic failed-load and rollback checks, adds explicit `-c 100` batching, requires exact inserted/failed counts, and checks the generated child-partition fixture. Its [two-child scenarios](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/1d349fe7392b41384bbf3bdb327755f10f4a4286/shell/_35_cherry/issue_21654_server_side_loaddb/partition_tbls/cases/partition_tbls.sh#L129) verify root routing, a valid direct-child load, rejection of a sibling-bound row, rejection when no partition accepts a row, retained previously committed rows, and a subsequent valid load.

Expected load failures require a nonzero utility result, the appropriate diagnostic, and the stated object counts. Row queries also require successful `csql -c` and exact compact output. A missing table or failed ordinary query therefore cannot satisfy these row assertions solely through an empty result. Existing test1/test3 and both partition answer files are unchanged relative to the current target.

The unchanged engine [loader pruning path](https://github.com/CUBRID/cubrid/blob/95ff126a8464179a2fab3092b6f56468528ab954/src/loaddb/load_server_loader.cpp#L814) and [pruning-type selection](https://github.com/CUBRID/cubrid/blob/95ff126a8464179a2fab3092b6f56468528ab954/src/loaddb/load_server_loader.cpp#L1217) distinguish root and direct-child loads. Revalidated native execution supplies actual rollback and retained-row observations for this fixture. Evidence reaches level 5 for these inputs; it does not establish crash recovery or all batch boundaries.

### Lock observation after SELECT

The [lock script](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/1d349fe7392b41384bbf3bdb327755f10f4a4286/shell/_06_issues/_14_1h/bug_bts_13242/cases/bug_bts_13242.sh#L51) writes a ready flag from a synchronous CSQL shell command after the SELECT, holds the same transaction until the parent releases it, and checks child timeout and exit status. The parent obtains lockdb output before releasing the transaction. The [golden lock answer remains unchanged](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/1d349fe7392b41384bbf3bdb327755f10f4a4286/shell/_06_issues/_14_1h/bug_bts_13242/cases/issue_13242.answer).

The safety argument depends on actual CSQL sequencing. The [single-line loop](https://github.com/CUBRID/cubrid/blob/95ff126a8464179a2fab3092b6f56468528ab954/src/executables/csql.c#L1010) executes each SQL statement before processing subsequent session commands. The [shell-command consumer](https://github.com/CUBRID/cubrid/blob/95ff126a8464179a2fab3092b6f56468528ab954/src/executables/csql_support.c#L246) is synchronous. With `--no-auto-commit`, rollback follows that shell call. A child timeout writes a persistent flag that is checked after waiting, including when the timeout occurs during lockdb.

The actual CTP assertion functions append each OK or NOK. Its testcase consumer marks any NOK as unsuccessful. A later successful golden comparison cannot erase an earlier child or utility failure. Both specialists independently traced this boundary. The coordinator also replayed the exact pinned `wait_pid_exit` function with real Bash children exiting 42 and 0 and the actual CTP append functions.

## Verification and essential evidence

The formal review revalidated existing native artifacts and performed a new bounded child-status probe. It did not run a new full database testcase or rebuild the engine. [Portable evidence](tc-pr4360-evidence.json) records source identities, effective configuration hashes, XML hashes, every earlier attempt disposition and the probe output.

| Native evidence reused | Execution identity | Observed result |
| --- | --- | --- |
| Partition attempt 04 | Engine `95ff126a8`; tested TC `eb3d5419` | One dispatched/finished case, 28 OK, 0 NOK, 0 skips. Runner and strict verifier exit 0. |
| Lock attempt 4 | Engine `95ff126a8`; TC `1d349fe7` | One dispatched/finished case, 1 OK, 0 NOK, 0 skips. Six lockdb observations. Runner and verifier exit 0. |
| Lock attempt 5 | Same pinned identities, fresh contained runtime | Same successful counts and six lockdb observations. |
| Lock attempt 6 | Same pinned identities, fresh contained runtime | Same successful counts and six lockdb observations. |

The partition run was originally performed on TC4335's synchronization commit. The complete selected partition testcase directory has the identical Git tree `ceab8bdb68aeffc622d75561fdf876174eb0a3c4` at both that tested commit and this reviewed head. Only an unselected locking testcase differs between those two combined trees. This justifies reuse for the selected partition case without calling it a new PR4360-wide test.

Each native run used one slot, a private install/registry/HOME/CTP tree, `scenario_disk=on`, no retry, no testcase update, and explicit selection of the one named testcase. The native invocation was:

```sh
TESTKIT_NATIVE=shell TESTKIT_CONTAIN=1 testkit shell -c <private-attempt-conf>
```

The unchanged strict verifier checked exact dispatched/finished identities, positive assertions, zero failures/skips, status, feedback, XML and testcase logs. Its exit was 0 for all four accepted runs. The coordinator repeated artifact verification during this review. Bash syntax checks and `git diff --check` also passed at the pinned scope.

Earlier macro-count runs remain inconclusive because a full-corpus macro scan added 21 unselected skips before explicit selection, producing total 22 rather than 1. A separate partition attempt failed during containment setup because its restricted PATH omitted `ip`; another was prepared but not launched. None counts as a passing test. Fresh attempt configurations cleared only the unrelated global macro scan after proving neither selected script contains `LINUX_NOT_SUPPORTED`. Testcase code, the selected set, assertions, answers, timeouts, containment and the verifier were unchanged.

The new coordinator replay is reproducible from the retained [probe](tc-pr4360-wait-probe.sh):

```sh
bash tc-pr4360-wait-probe.sh
```

It executes the reviewed function and real child processes, not a rewritten model. Inherited CTP helper whitespace is normalized in the published probe; the pinned wait function bytes are unchanged. Expected and actual result were one persistent NOK after the failed child, a later OK, and no extra NOK after the successful child. Exit status was 0:

```text
probe-1 : NOK CSQL failed
probe-2 : OK  later success
actual wait_pid_exit failure/success probes passed
```

The reviewed function SHA-256 is `2047249c7be441b57074cf6fbb9cc4d647a15eba1ce3b817eb73e0127134ce76`. The CTP init artifact SHA-256 is `1a97de55d48271e5d3e04489b36e7efc0b1a5bdc9f0c00b29e3499b3e45ba9f8`.

## Initial adjudication and limits

At the initial review freeze, there were no confirmed findings or material unresolved introduced candidates. The independent shared challenge did identify a pre-existing CSQL limitation. In [default single-line execution](https://github.com/CUBRID/cubrid/blob/95ff126a8464179a2fab3092b6f56468528ab954/src/executables/csql_launcher.c#L157), the [per-statement return is ignored](https://github.com/CUBRID/cubrid/blob/95ff126a8464179a2fab3092b6f56468528ab954/src/executables/csql.c#L1023), so a SQL error can still precede a zero CSQL process exit. The new `wait` check detects process failure, not every SQL statement error.

Both BASE's piped stdin and HEAD's `-i` invocation use this same mode, and the SELECT text and golden oracle are unchanged. Neither reviewer nor the coordinator established a newly reachable false PASS under the unchanged queries. Candidate SL-1 was initially classified as a pre-existing exit-status limitation with unverified false-verdict impact. Subsequent fault injection confirms the inherited verdict weakness for an added erroneous statement, while leaving unchanged-query reachability separate.

The concurrency reviewer rejected four false-PASS hypotheses through pinned control flow and append semantics, and retained the inherited CSQL caveat. The systems reviewer retained one source-based candidate; coordinator adjudication classified it as pre-existing. No candidate was silently discarded, and none awaited coordinator replay as a confirmed defect.

No live timeout, hung lockdb, stopped shell descendant, Windows, crash/restart or HA fault-injection test was performed. The local lockdb utility still relies on outer runner containment for a bound, as it did before this patch. These limits remain explicit. Normal passing runs do not prove every interleaving safe.

## Follow-up fault injection and correction

On 2026-11-09, the author requested further investigation of SL-1. Fresh native contained executions used the same engine `95ff126a8464179a2fab3092b6f56468528ab954`. The [follow-up evidence](tc-pr4360-sql-errors.json) records counts, exact assertions, verifier output, artifact hashes and setup failures.

### SL-1, P2, confirmed inherited SQL-error blindness

The trigger adds a separate `select 1 + ;` line immediately after each original `$sql` line and before `;shell_cmd` in a disposable full-corpus copy. The six original SELECTs, handshake and golden answer remain unchanged. CSQL emits six parser errors, reaches the barrier, and exits zero. The original testcase records its successful golden comparison and passes. A ready flag and zero process exit do not establish SQL success.

This is an additional erroneous statement. It does not prove that an unchanged original SELECT can fail while retaining the expected locks. Another experiment changed the first SELECT projection to `a / (a - 1)`. Division by zero changed lock observations, and the golden comparison correctly rejected that case. This rejected false-PASS hypothesis remains recorded.

| Fresh execution | SQL diagnostics | Assertion result | Testcase verdict |
| --- | --- | --- | --- |
| Reviewed head `1d349fe7`, added erroneous statements | Six parser errors | 0 NOK, golden comparison OK | PASS, demonstrating the uncovered error path |
| Local correction `8de2ebcf7`, original testcase | None | 0 NOK, golden comparison OK | PASS, strict verifier exit 0 |
| Same correction, same added erroneous statements | Six parser errors | Six CSQL-error NOKs, then golden comparison OK | FAIL, expected rejection |

The corrected negative verdict contains:

```text
bug_bts_13242-1 : NOK CSQL reported an error
bug_bts_13242-2 : NOK CSQL reported an error
bug_bts_13242-3 : NOK CSQL reported an error
bug_bts_13242-4 : NOK CSQL reported an error
bug_bts_13242-5 : NOK CSQL reported an error
bug_bts_13242-6 : NOK CSQL reported an error
bug_bts_13242-7 : OK
```

The correction captures each tested CSQL process's stderr in a freshly truncated per-query file. After the existing wait, nonempty stderr appends a NOK and prints the diagnostic. Per-query cleanup removes the file. The [prepared patch](tc-pr4360-sql-errors.patch) changes one file, with seven additions and two deletions. It preserves the six SQL inputs, golden answer, process-exit checks and transaction barrier. An independent review of this exact delta found no blocking defect. Bash syntax and whitespace checks passed.

The check treats any CSQL stderr as failure. Future benign diagnostics could require a reviewed policy change; the positive run emitted none. Switching to `--no-single-line` would bypass the [session-command interpreter](https://github.com/CUBRID/cubrid/blob/95ff126a8464179a2fab3092b6f56468528ab954/src/executables/csql.c#L753) used by this barrier. The correction does not alter the engine or unrelated setup commands.

All fresh executions used the native command shown above, one selected case, one slot, disposable install/registry/HOME/CTP trees, `scenario_disk=on`, and no retries or updates. The same copied-configuration macro correction described above preserved selected-case eligibility. The native runner exits zero for the expected negative verdict. Its status and feedback record one failed case and six NOKs. The strict verifier rejects `fail count is 1`. Both diagnostic negative runs contain malformed failure XML, preserved and recorded. They are not successful complete artifact verification. Before-fix false-PASS XML and corrected normal-run XML parse successfully. Actual assertion feedback and testcase status establish the negative result.

Two earlier setup attempts never ran a testcase. The first selected direnv from the wrong working directory. The second selected mise shims after HOME changed, automatically installed Python within that attempt, and failed to resolve the testkit shim. Subsequent attempts used explicit installed tool paths without installing or updating testkit. All attempts remain retained.

Required next action is an authorized ordinary push of the verified correction and a base/head recheck. The source correction remains local at this document revision. Existing human review requests remain active.

## Initial review budget and current follow-up

Mode was bounded. Initial assignments were systems-loader on `gpt-6.1-terra` high and concurrency-locking on `gpt-6.1-sol` high, with distinct models on the shared challenge. Each target was eight minutes with a six-minute checkpoint. Twelve coordinator minutes were reserved, making a 28 agent-minute planning envelope. These were scope/time targets, not an enforced cumulative cap. Token, credit and per-agent provider allowance telemetry were unavailable; measured usage and remaining allowance are unknown. Two specialists returned final reports, with no dropout, retry agent or extra panel. Both reported completion within their assignment target. Coordinator wall time at document freeze was 15.0 minutes, including concurrent-review waiting and publication preparation. It exceeded the twelve-minute soft coordinator target while preserving an unrelated dirty documentation checkout and validating the publication artifacts. This is a wall-time observation, not provider usage. No additional specialist or review round was launched.

The initial optional-follow-up decision is superseded by the reproduced SL-1 weakness. The follow-up used a mechanism explainer, one implementation agent and one independent delta reviewer, with soft targets of eight, five and three minutes. The coordinator's fifteen-minute checkpoint was reached after completing diagnostic and corrected runtime checks; documentation publication and trail review continued afterward. These are planning targets, not provider-usage limits. The current PR requires the prepared correction. Recheck its base/head after publication and retain the fixture, platform, strict-stderr and negative-XML limits when assessing it.
