# PR 7990: non-CDC reproduction and default repair

Analysis date: 2026-10-22, Asia/Seoul. Audience: the OOS author and reviewers of [PR 7990](https://github.com/CUBRID/cubrid/pull/7990).

This follows the [original four-failure analysis](ci_analysis_report_1a8c705_codex.md). Its validated CI inventory and unavailable exact-baseline CI evidence remain unchanged. This report adds controlled local experiments. It does not establish a passing CI baseline.

## Findings and decisions

| Case | New evidence | Disposition |
| --- | --- | --- |
| `cbrd_23136` | Three optimized head stress runs and one exact-base run pass the native artifact verifier. The recorded CI allocator abort does not recur. | Root cause remains unresolved. No speculative engine fix. |
| `bug_bts_15529` | The unmodified case reproduces only the two OOS diagnostic-list differences. The repaired case passes both assertions. | Narrow answer repair committed locally as `73e2b2f44`. |
| `cbrd_26354` | Both engines use histogram join estimation. Base also produces a below-100000 estimate. Both return the same actual join count. | Histogram-dependent plan snapshots explain the mismatch class. Preserve the LIMIT/cardinality assertions. No answer change. |
| `cbrd_24916_check_index_ovfps` | Equal-input runs reproduce the exact head/base page counts. Independent disk traversal agrees with capacity output. | An isolated eight-byte header change reproduces the OOS layout. Capacity accounting agrees with physical pages. No answer change. |

CDC remains excluded. No CI trigger, remote comment, source/testcase push, testcase merge, or merge into `develop` occurred.

## Source and execution identity

| Component | Identity |
| --- | --- |
| Original engine and local head | `1a8c7057623d92205dbc1324ec43e3cc40fc4cd2` |
| Exact merge base | `3ba41d74509d9a6c19ef9adc6cf12d9ebebdbbac` |
| Private testcase inputs | `28ffb73654b812c3c156c3f2512bad066506808c` |
| Repaired private testcase branch | `fix/pr7990-callstack-defaults-20261022`, commit `73e2b2f44` |
| Native shell helper assets | Exact CI CTP `af69c0039ff084fea5ee5ff296cc5301203d4c3f` |
| Diagnostic header-size probe | Base plus local commit `b41455824`, branch `diagnostic/pr7990-base-header8-20261022` |

Head and base use separate source worktrees, installations, registries, and retained databases. Both use `OptDebug` with `-O2` and assertions enabled. The live CI workflow calls `build.sh -m optdebug` for its debug-labelled job. The previous local investigation used `Debug` with `-O0`.

The local compiler is GCC 11.5. The CI build image is `cubridci/cubridci:build_rl8.10`. Matching optimization mode does not establish an identical compiler, libc, allocator environment, or interruption schedule.

Evidence root `R` is `/home/vimkim/tmp/pr7990-noncdc-diagnosis-20261022`. Raw logs, helper scripts, copied installations, volume inventories, and intermediate diagnostics remain outside this documentation repository. Work item `487` records this continuation separately from completed items `483` and `478`.

## Allocator crash: reproduced workload, unresolved abort

The original CI stack remains the evidence for the defect: `mspace_free` aborts while `classobj_clear_attribute` disposes of an attribute name during partition-schema rollback. It does not identify the earlier invalid write or ownership violation.

Each successful local attempt ran the original `cbrd_23136` script, including its full server-kill/restart interval, under native containment. Each used a fresh install copy, HOME, registry, configuration, and writable corpus overlay. Source testcase files remained unchanged.

| Attempt under `R` | Engine | Native verdict |
| --- | --- | --- |
| `a06-crash` | Head | 1/1 PASS, zero failures/skips, 271 seconds |
| `a09-base` | Exact base | 1/1 PASS, zero failures/skips, 267 seconds |
| `a10-crash` | Head | 1/1 PASS, zero failures/skips, 266 seconds |
| `a11-crash` | Head | 1/1 PASS, zero failures/skips, 266 seconds |

The artifact verifier checks the positive dispatched and finished case sets, assertions, status files, feedback, and JUnit. Host `systemd-coredump` listings were also retained before and after each run. The original testcase searches for `core.*`. That search alone cannot establish absence of a crash on this host.

**Conclusion:** these passes do not waive the CI crash. A repeatable failing loop was not obtained. The test run exposes no GitHub Actions artifacts, and the user confirmed that no additional core or reproducer is available. A matching core or a reproducing environment is the next required input for ownership diagnosis.

### Setup attempts and corrections

Attempts `attempt-01-crash-optdebug` through `attempt-05-default-before` are inconclusive setup attempts. They stopped before the target workload. They remain retained and receive no passing credit.

The attempt path made the server handoff socket pathname exceed the Unix socket limit. `filesys::temp_directory_path` prefers `CUBRID_TMP`. Changing `TMPDIR` did not fix this. Short attempt names resolved startup. The harness now rejects excessive socket path lengths before launch.

The harness also replaces inherited `CUBRID_CONF_FILE` and `CUBRID_BROKER_CONF_FILE`, and removes the source workenv's port override. Selected cases contain no `LINUX_NOT_SUPPORTED` macro. Clearing that macro setting before execution avoids unrelated whole-corpus skip accounting without changing selected-case eligibility. Generated XML and totals were not modified.

## Diagnostic default: confirmed and repaired

The unmodified native attempt `a07-default` fails assertion 1 with exactly two differences: initial default read and reset-to-default read. Both omit `-1386,-1388,-1389` from the inherited answer. Assertion 2, the complete error-output comparison, passes in the text log. The failing run retains malformed JUnit at line 1111. Its structured evidence remains incomplete, and its files were not sanitized. The repaired run below has valid JUnit and a verified pass.

The [default array](https://github.com/CUBRID/cubrid/blob/1a8c7057623d92205dbc1324ec43e3cc40fc4cd2/src/base/system_parameter.c#L5989) adds the three OOS error constants without a debug/release conditional. The repair adds them in array order to both `test.answer` and `testdebug.answer`, at their two default-list lines. The explicit `4207500` assertion and all SQL/error assertions remain unchanged.

Repaired attempt `a08-fixed` passes 1/1 cases, both assertions, and the native artifact verifier. Its recorded patch equals committed answer content. Runtime verification uses OptDebug. The unconditional source default supports the release answer adjustment. Runtime verification did not use a release binary.

The user approved local integration. The existing private `tc/pr-7990` checkout contains `73e2b2f44`, and the merged task worktree and branch were removed without force. No private testcase push occurred.

## Statistics: histogram estimates, equal query results

`stats_diag.py` extracts the original setup SQL and all 20 query strings from the pinned testcase. It runs them on each engine in standalone mode. The worktrees retain their databases as `diag26354`. This is a controlled diagnostic experiment, not a native testcase verdict or CI baseline.

| Observation | Head | Base |
| --- | ---: | ---: |
| `t1` rows / `t2` rows | 100000 / 500 | 100000 / 500 |
| `t1.col7` distinct values | 500 | 500 |
| `t2.col1` distinct values | 500 | 500 |
| Histogram join selectivity, debugger trace | `0.002` | `0.0019998661674644025` |
| Join estimate in case 17 | 100000 | 99993 |
| Actual unbounded join rows | 99800 | 99800 |

The debugger observes `histogram_get_join_selectivity` returning `success=true` on both engines. Base's estimate follows `100000 × 500 × 0.0019998661674644025 ≈ 99993.308`. This excludes cardinality fallback as the explanation for these particular runs.

`WITH FULLSCAN` visits every heap page but still builds a finite reservoir sample. The [sampler](https://github.com/CUBRID/cubrid/blob/1a8c7057623d92205dbc1324ec43e3cc40fc4cd2/src/optimizer/histogram/histogram_sampler_sr.cpp#L68) normally keeps 300 sample rows per bucket. A 300-bucket request therefore samples 90000 of these 100000 rows. Collection uses a fixed default seed. Equal logical rows do not require equal physical scan order or equal sampled values.

The retained histogram dumps differ in most-common-value membership. Repeating collection on each unchanged database reproduces its own result. The histogram join formula combines those frequencies with the remaining distinct-value estimate. The printer's [`%G` format](https://github.com/CUBRID/cubrid/blob/1a8c7057623d92205dbc1324ec43e3cc40fc4cd2/src/optimizer/query_graph.c#L9927) then exposes different digit counts. The testcase masks digits while preserving their count.

The local base estimate `99993` differs from the original CI head estimate `99986`. This reproduces the mismatch class, not the exact CI histogram. This experiment does not isolate the particular heap-layout change responsible for the statistics difference.

A temporary diagnostic removed histograms after saving the original results. Both engines then used fallback selectivity `0.00200401` and estimated `100200` join rows. Removing histograms therefore does not reproduce the original answer either.

The original testcase deliberately restores the real top-level `card` value after formatting. Replacing it with a wildcard would remove its feature assertion. No permanent testcase change disables histogram collection or masks that value.

## Index capacity: independent physical-page comparison

`ovf_diag.py` loads the original seeded SQL into separate retained `diag24916` databases. The corrected `ovf-inspect.sql` obtains capacity with fully qualified class/index names.

| Index / metric | Base | Head | Original CI head |
| --- | ---: | ---: | ---: |
| `xx1.testidx`, overflow pages | 278 | 274 | 274 |
| `xx1.testidx`, integer average per key | 55 | 54 | 54 |
| `xx2.testidx`, overflow pages | 280 | 282 | 282 |

Both engines retain five keys and 100000 index values per index. Seeded per-key row counts agree exactly: `19932,19894,19943,20072,20159` for values zero through four.

### Independent raw-volume traversal

`read_overflow.py` reads the saved 16 KiB unencrypted volume without calling CUBRID capacity functions. It decodes slotted-page records, follows each data-page and directory-page chain, and counts unique physical page IDs. Its source format references are `file_io.h`, `slotted_page.h`, `btree_load.h`, and `btree.c` at the pinned revision.

For each index, the walker establishes 100000 unique OIDs, no repeated/cyclic pages, sorted OID chains, and equality between directory targets and data-chain pages. It also follows every OID into its heap record, checks its indexed value, and verifies IDs 1 through 100000 exactly once. Its totals agree exactly with capacity output: base `278/280`, head `274/282`. Each key has one directory page, so the difference is in data-page splits rather than omitted directory pages.

The OID-set hashes differ between head and base, although each heap uses 165 OID-bearing pages. On `xx1`'s first heap page, head stores 562 rows and base stores 563. The ordinary row records remain 20 bytes.

The [OOS heap-header field](https://github.com/CUBRID/cubrid/blob/1a8c7057623d92205dbc1324ec43e3cc40fc4cd2/src/storage/heap_file.c#L214) adds an eight-byte `VFID oos_vfid`. Raw slot zero is 1160 bytes on head and 1152 on base. This changes the first page's capacity even when user rows contain only integers and allocate no OOS value.

### Header-size isolation and integrity checks

The diagnostic branch adds an unused, null-initialized VFID at the corresponding position in the base heap header. It changes no B-tree algorithm and opens only freshly created databases under its own installation. This branch is an experiment and must not be merged as a production fix.

The probe reproduces head's `274/282` overflow-page totals and `54/56` integer averages. Its independent `raw-pages.json` equals head's file byte for byte. This includes every data/directory page ID, per-key row count, OID hash, and heap-page occupancy.

All six decoded `(id,v)` datasets, two tables on three engines, have the same SHA-256:

```text
db973285974e277f444e971099a808247bae407e145970d0fb7d4eff12578a54
```

**Causal conclusion:** increasing the base heap header by eight bytes is sufficient to reproduce the exact OOS index layout. The smaller first-page capacity changes OID assignment. The OID-ordered overflow insertion path then splits differently. These metrics describe real physical pages, with equal logical data. These cases do not indicate a capacity-accounting defect.

Head, base, and probe each complete the following native structural check with exit zero:

```bash
cubrid checkdb -S --check-btree --check-heap diag24916
```

This checks heap and B-tree structure. The independent walker supplies the additional per-entry checks for the two target indexes. It does not qualify every index or every supported on-disk format.

The initial diagnostic query used incomplete `SHOW INDEX CAPACITY` syntax and an unnecessarily expensive unindexed join. I interrupted that read and replaced it with the qualified inspection above. Full-database and class-selected `checkdb` runs were also interrupted after prolonged execution. Neither receives passing credit. A debugger stack shows the class-selected check performing per-row index-entry searches. The final structural command omits the class list and completes normally. Logs remain retained.

## Merge-resolution attribution and ticket decision

This audit compares merge `1a8c7057623d92205dbc1324ec43e3cc40fc4cd2` with OOS parent `fb567a629cdb390fff920542173fa36f454c74a0` and develop parent `3ba41d74509d9a6c19ef9adc6cf12d9ebebdbbac`. The saved `merge-parent-audit.json` and `merge-function-audit.json` record exact-object comparisons.

| Observation | Attribution | Ticket decision |
| --- | --- | --- |
| `bug_bts_15529` | The OOS parent already contains all three diagnostic constants. They came from OOS commit `2c792b423ccac027c41317c0ba28e26f5336870d`, before this merge. | Testcase maintenance under the OOS integration work. No separate engine-defect ticket indicated. |
| `cbrd_24916_check_index_ovfps` | The OOS parent already contains `oos_vfid`. Its introducing commit is also `2c792b423c`. The base-plus-padding experiment reproduces the counts without any conflict-resolution code. | Physical-layout expectation maintenance. No separate engine-defect ticket indicated by these observations. |
| `cbrd_26354` | The query graph, planner, and histogram client code equal the develop parent. Base also produces a histogram-dependent estimate mismatch. | Review testcase stability under OOS integration work. No confirmed new engine defect or conflict-resolution mistake. |
| `cbrd_23136` | The failing `classobj_clear_attribute` function equals both parents. The earlier corrupting operation remains unknown. | Track the current allocator abort as a separate CBRD bug/investigation after duplicate checking. Do not label its root cause as a merge-resolution error. |

The merge contains manual resolutions in six files. This audit does not certify every resolution. It finds no evidence that a conflict-resolution mistake explains these four symptoms. Unchanged cleanup code cannot exclude a semantic integration regression or corruption caused elsewhere.

A live JIRA lookup on 2026-10-22 confirms that [CBRD-23136](https://jira.cubrid.org/browse/CBRD-23136) is closed as fixed. It describes a double free in `sm_free_constraint_info`, rather than the current attribute-name disposal abort. The same stress test historically exposed several other defects: [CBRD-23167](https://jira.cubrid.org/browse/CBRD-23167), [CBRD-23168](https://jira.cubrid.org/browse/CBRD-23168), [CBRD-23169](https://jira.cubrid.org/browse/CBRD-23169), and [CBRD-23427](https://jira.cubrid.org/browse/CBRD-23427). Those issues are also closed and record different crash sites. These historical links do not establish a shared root cause or rule out another current duplicate.

The user authorized local integration of the default repair and publication of this report. The private testcase branch now contains `73e2b2f44` locally. Its remote publication remains outside this approval. The diagnostic padding branch remains separate as experiment evidence. Work item `490` records review of the retained branches and conditional integration of a verified production hotfix into `feature/oos-merge`.

## Reproduction records and remaining work

All native invocations use `TESTKIT_NATIVE=shell TESTKIT_CONTAIN=1 testkit shell -c CONF`. Their exact commands, source/install identities, testcase patches, selected lists, original result files, process exits, and verifier outputs remain in their respective attempt directories.

Important diagnostic records under `R` are:

- `run_shell.py`, the retained native-attempt harness, and each attempt's `verification.txt`.
- `head-stats/`, `base-stats/`, debugger traces, repeated histogram dumps, and actual join logs.
- `head-ovf/`, `base-ovf/`, `probe-ovf/`, `read_overflow.py`, and independent `raw-pages.json` outputs.
- Head/base build logs, the diagnostic probe commit and build records, and `result.json`.

The next crash step requires a matching core or repeatable failure. The default repair is ready for local testcase integration review. Any broader statistics/index testcase stabilization must preserve the feature assertions and follow the experiment limits above.
