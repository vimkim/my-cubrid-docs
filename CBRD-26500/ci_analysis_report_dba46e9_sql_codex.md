# PR #7157: SQL join-plan failures and testcase synchronization

Date: 2026-10-20, Asia/Seoul. Work item: 368.

The selected failing SQL rerun contained three failed testcases, rather than two. All three compared nested-loop traces against hash-join execution. The tested testcase branch lacked an existing upstream update that preserves the intended nested-loop coverage.

The public testcase branch now contains the verified fix. Follow-up CI passes all 150 selected SQL cases, with zero failures, errors, skips, or unrun cases. TC Merge Gate is the only remaining failed required status.

The verified change copies six existing testcase files from upstream commit `60eb2b3790c3ad89a73bb0abd47dffde619f804a`. It adds join hints and updates their text in the expected answers. The expected result rows and plan assertions remain intact.

Controlled local runs establish that all three signatures predate this PR. The exact merge base and PR head produce byte-identical results with the original testcases.

## CI identity and validated inventory

Source PR: [CUBRID/cubrid #7157](https://github.com/CUBRID/cubrid/pull/7157).
Execution: [run 39256219940, attempt 1](https://github.com/CUBRID/cubrid/actions/runs/39256219940).
Failed SQL job: [118072796744](https://github.com/CUBRID/cubrid/actions/runs/39256219940/job/118072796744).

| Input | Exact identity |
| --- | --- |
| Engine | `dba46e965eaa481814922b9e76c30059f057a752` |
| SQL testcase repository | `CUBRID/cubrid-testcases` |
| SQL testcase branch | `tc/pr-7157` |
| SQL testcase commit | `b016b6d687e713c86d4fe011664d2924b8fd41ee` |
| Consumed debug build | Run `39216768822`, attempt `1` |
| Workflow revision | `e520d79dc9ad64fc6492088be99b7d31e7c8215e` |
| Collector | `cubrid-ci 0.2.0 (9536bd3c2867, release)` |
| Terminal collection observation | `20261020T092029.661675624Z-2552540-0` |

The workflow revision differs from the tested Engine. The shard's build provenance establishes the tested Engine identity.

| Requested suite | Planned | Executed | Passed | Failed | Errors | Skipped | Unrun |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `test_sql` | 150 | 150 | 147 | 3 | 0 | 0 | 0 |

This complete inventory covers the selected rerun assignment. It does not cover the complete SQL corpus. This investigation collected only SQL.

The command result and manifest use schema version 3. The observation pair uses version 2. All envelopes, failure records, summary, and raw index validate. All 28 indexed raw files match their declared sizes and SHA-256 digests. Counts reconcile. Collection excludes binary artifacts.

The report gate permits a full head report and no CI baseline comparison. The head collection succeeded with exit zero despite the red testcase verdict.

## Every failed case

All files below use the recorded testcase commit. Each group contains one SQL file and one expected answer. There are no group-local helpers or fixtures.

| Full testcase path | Failed query comparisons | Observed signature |
| --- | --- | --- |
| `sql/_36_guava/cbrd_27465/cases/cbrd_27465.sql` | 8 | `SHOW TRACE` reports hash semi/anti joins instead of nested loops and memoized index scans |
| `sql/_36_guava/cbrd_27485/cases/cbrd_27485.sql` | 6 | Cached and recompiled traces report hash joins instead of parallel nested-loop joins over partitioned inputs |
| `sql/_36_guava/cbrd_27487/cases/cbrd_27487.sql` | 1 | The EXISTS trace reports a hash semi join instead of the intended memoized nested loop |

Every declared mismatch concerns `SHOW TRACE`. The declared failures contain no result-row mismatch, crash, or testcase error.

The collect job's summary guard also exits with `sql: 3 failed`. Its log supports the same testcase verdict. It does not establish an additional execution-environment failure.

## Cause and smallest existing fix

[Engine commit 8ea02c8e8](https://github.com/CUBRID/cubrid/commit/8ea02c8e8431d0de73223a7aaa331ed84e1da912), from PR #8001, allows hash semi/anti joins. That commit is an ancestor of the exact merge base `1dceac8add1801aef564b27624b8fbb5b6f62d59`.

The original tests require specific nested-loop behavior. However, the affected statements let the optimizer select another join method. A valid hash plan therefore defeats their intended coverage and fails their trace expectations.

[Upstream testcase commit 60eb2b379](https://github.com/CUBRID/cubrid-testcases/commit/60eb2b3790c3ad89a73bb0abd47dffde619f804a), from testcase PR #3565, already addresses these exact cases:

- `cbrd_27465`: add `USE_NL` to the relevant unnested queries. Preserve the ordinary inner hash join with `USE_HASH(b)` in Case 9.
- `cbrd_27485`: add `USE_NL` to the cached and recompiled queries, preserving parallel partition coverage.
- `cbrd_27487`: add `USE_NL` to the EXISTS query that exercises memoization.

The expected answers change only where rewritten-query text displays these hints. Removing the added hint text makes each updated answer identical to its original answer. All six published files equal the upstream Git objects byte-for-byte.

Only those six files belong in the public testcase update. The other tests from upstream PR #3565 are outside this fix. The Engine remains at the tested revision.

The original source PR differs from its merge base only in `src/base/perf_monitor.c` and a comment in `src/storage/page_buffer.c`.

| Hypothesis | PR relation and confidence | Falsifier | Next action |
| --- | --- | --- | --- |
| The testcase branch lacks the join-hint update | Existing testcase compatibility issue, high confidence | The scoped upstream hints fail to restore the original plan assertions | All three updated cases pass, retain the existing assertions |
| This PR introduces the observed signatures | Controlled evidence rejects this relation, high confidence | Identical-input head/base runs produce different signatures | Preserve the paired artifacts |
| CI configuration alone causes these failures | Controlled evidence rejects this explanation for the signatures, high confidence | The original cases pass locally or produce different diffs | Preserve the exact CI/native signature audit |

## Controlled native verification

| Attempt | Engine | Testcases | Executed | Passed | Failed |
| --- | --- | --- | --- | --- | --- |
| `head-native-01` | `dba46e965` | Original CI inputs | 3 | 0 | 3 |
| `base-native-01` | `1dceac8ad` | Identical original inputs | 3 | 0 | 3 |
| `fixed-native-01` | `dba46e965` | Scoped six-file upstream update | 3 | 3 | 0 |

The two original-input runs produce byte-identical per-case results and CI failure messages. Their normalized SQL, server, and broker configurations match. They use identical JDBC and locale assets. Every expected case executes, with zero errors or skips.

The updated run passes the focused runner's strict artifact verifier. Every result file matches its expected answer byte-for-byte. Its Engine, normalized configuration, JDBC, and locale assets match the original head run.

Evidence includes all three attempts. None requires a commit-mismatch exception, and none delegates execution to legacy CTP.

Raw whitespace validation flags one trailing space in an expected rewritten-query line. That byte already exists in the upstream answer. The fixture preserves it, and validation passes with only trailing-space detection excluded.

The original native head run executes all three original files and fails all three. Its 15 query/diff blocks exactly equal CI's blocks. This provides a direct failure signal for the verified fix.

The complete original cases remain the verification targets. Reducing them would remove memoization or parallel-partition coverage that the fix must preserve.

The native command uses explicit containment:

```bash
TESTKIT_NATIVE=sql TESTKIT_CONTAIN=1 testkit sql -c <attempt>/conf/sql.conf
```

The setup uses `debug_gcc`, JDK `1.8.0_462`, JDBC `test_default.xml`, `en_US.utf8`, and one slot. It copies the installation, CTP assets, configuration, HOME, registry, and testcase groups into each retained attempt.

The native runner digest is `31be3b1e542b05d1ac7581d47f785319ce61421f4b5d94681a9c558d71445f5a`. It returns exit zero for the original failures. XML, per-case results, summaries, and terminal markers establish the verdict instead.

The attempts use the retained JDBC driver and locale library from the earlier SQL investigation. Each attempt's metadata records their digests and source paths. CTP supplies assets while the native testkit performs execution.

The CTP asset checkout is at `9c62858b10005d721546cc007be260844033b9e9`, with pre-existing local changes. The evidence retains its status and patch. The copied SQL configuration and Java test libraries match across all three attempts. These controls establish selected-case behavior, rather than equivalence to every CI tooling input.

## Publication and one CI rerun

The published public branch `tc/pr-7157` contains commit [4518b853e](https://github.com/CUBRID/cubrid-testcases/commit/4518b853e3d75cc0cfabd2b55544f3213bd04ac0) in [public TC PR #3777](https://github.com/CUBRID/cubrid-testcases/pull/3777).

The source Engine stays at `dba46e965eaa481814922b9e76c30059f057a752`. The private TC branch stays at `a58f2d8c32a5b1c42aab2521a58300beaaa0c38a`.

The single [CI request](https://github.com/CUBRID/cubrid/pull/7157#issuecomment-6287979936) is:

```text
/run rerun 39256219940
```

The source run is terminal and belongs to the same Engine head. Only SQL contains failed shards, so the rerun selects SQL. Completed shell and medium statuses remain applicable to the unchanged Engine.

Before the request, the preflight validated the PR head, testcase publication, latest chatops comments, linked statuses, and active workflow states. There was no active same-PR run.

Pickup succeeded for [run 39401841341, attempt 1](https://github.com/CUBRID/cubrid/actions/runs/39401841341). Both build contexts and SQL point to that run. The workflow, SQL shard, and collect job all finish with success.

| Follow-up SQL assignment | Planned | Executed | Passed | Failed | Errors | Skipped | Unrun |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Validated terminal execution | 150 | 150 | 150 | 0 | 0 | 0 | 0 |

A separate terminal verification collection validates observation `20261020T094949.496316026Z-2999266-0` and all 28 raw-file digests. Its shard consumes Engine `dba46e965eaa481814922b9e76c30059f057a752` and public testcase commit `4518b853e3d75cc0cfabd2b55544f3213bd04ac0`.

The terminal required view contains eight passes and one failure: `Check TC PRs`. All five gha-ci contexts, including optional debug build, report success. No stable required gha-ci context is missing.

[Public TC PR #3777](https://github.com/CUBRID/cubrid-testcases/pull/3777) and [private TC PR #4454](https://github.com/CUBRID/cubrid-testcases-private-ex/pull/4454) remain open. Their disposition requires the human. No follow-up fix, push, or rerun follows this successful execution.

## Exact CI baseline limitation

The independent baseline collection pins PR #7157's head and resolves both target tip and merge base to `1dceac8add1801aef564b27624b8fbb5b6f62d59`.

Its selected execution is [run 39278519179, attempt 1](https://github.com/CUBRID/cubrid/actions/runs/39278519179). Collection exits 4 with this integrity diagnostic:

```text
result identity mismatch: shard 01 workflow result and JUnit counts disagree
```

Observation `20261020T092056.036741692Z-2554181-0` records an incomplete collection. The collector retained shards 00 through 09. There are no failed or unattempted acquisitions, but no SQL suite summary passes validation.

The baseline command, manifest, and observation schemas validate. Their envelope validation does not resolve the suite integrity failure. No alternate download bypasses that failure.

All three head failures are therefore `uncomparable` against CI baseline evidence. Shared, additional-on-head, and base-only CI failure counts remain unknown. Controlled local results are separate evidence.

## Chronicle history and limits

Each full testcase path has queries from `find`, `explain --run 39256219940`, and `history --commits`. A bounded SQL sync added the requested execution.

| Case | Earlier failed observations | History result |
| --- | --- | --- |
| `cbrd_27465.sql` | 7 | `SEEN_BEFORE` |
| `cbrd_27485.sql` | 4 | `SEEN_BEFORE` |
| `cbrd_27487.sql` | 3 | `SEEN_BEFORE` |

These observations use different Engine and testcase revisions. They establish earlier failures of the same paths, rather than identical causes or flakiness. Global history coverage remains incomplete.

Chronicle marks the requested execution's attribution as partial, with a CTP completion diagnostic. The independent collector's reconciled summary and JUnit records establish this report's complete selected inventory.

## Retained evidence and remaining boundaries

Evidence root: `/home/vimkim/tmp/pr7157-sql-20261020.jZMCAL`.

- `status.json`, `head-result.json`, `head-manifest.json`, and `head-validation.json`: pinned identity and validated selected inventory.
- `base-result.json`, `base-manifest.json`, `base-validation.json`, and `assessment.json`: exact relationship, integrity limitation, and report gate inputs.
- `inputs/`: exact testcase source, answers, and declared CI messages and diffs.
- `head-signature-audit.json`, `audit_runs.py`, and `paired-verification.json`: artifact reconciliation and controlled comparisons.
- `validation-receipt.json`: published testcase identity and the complete retained attempt inventory.
- `upstream-tc-fix.patch` and `tc-patch-audit.json`: the scoped upstream fix and exact-file audit.
- `tcc-*.json`: bounded history collection and all three path queries.
- `collect-job.plain.log`: the collect guard's observed failure.
- `ctp-revision.txt`, `ctp-status.txt`, and `ctp-existing.patch`: the preserved asset checkout state.
- `receipt.json` and `terminal-run.json`: the single CI request and its resulting execution.
- `verification-result.json`, `verification-manifest.json`, `verification-summary.json`, and `verification-validation.json`: independent terminal provenance and 150/150 result validation.
- `checks-terminal.json`, `required-terminal.json`, and `pr-terminal.json`: final PR identity and the remaining human gate.
- Retained native attempt directories: preflights, commands, configuration, process exits, and verdict artifacts.

The completed private shell testcase update remains separate. A human must merge or close the testcase PRs. The agent must not change their disposition.

The latest-develop testcase ancestry helper reports that both TC branches lag their repositories' develop tips. This task selects only the six Engine-compatible files. It does not establish qualification against every newer testcase.

The source checkout remains clean on `CBRD-26500-pr7157-review`. Both testcase worktrees are clean. The auxiliary exact-base build worktree remains clean and retained for reproduction.

The separate develop checkout's pre-existing CCI/JDBC changes and untracked files remain untouched. Its unrelated files include `PLAN.md`, `demodb_loaddb.log`, `insert.sql`, `pagebuffer-perftest.md`, and `test.sh`.

Work item 368 includes the broader source PR workflow. The SQL fix alone does not complete that objective.
