# PR #7157: CBRD-27461 SQL failure and local comparison

Date: 2026-10-19, Asia/Seoul. Related work items: 433 and 368.

The SQL failure is independent of the page-buffer statistics changes in [PR #7157](https://github.com/CUBRID/cubrid/pull/7157). A newer regression testcase exposes an existing CONNECT BY optimizer bug. The testcase has correct expected answers. The tested PR head lacks the engine fix in [PR #8146](https://github.com/CUBRID/cubrid/pull/8146).

Controlled local runs establish the distinction. The exact PR head and merge base produce byte-identical wrong results. The merge base plus the existing optimizer fix passes. No engine or testcase source changes were needed.

## CI evidence and scope

The requested [run 39206056644, attempt 1](https://github.com/CUBRID/cubrid/actions/runs/39206056644) executed a selected set of 150 SQL cases. This inventory does not cover the complete SQL corpus.

| Requested suite | Collection | Planned / executed | Passed | Failed | Errors / skipped / unrun |
| --- | --- | --- | --- | --- | --- |
| test_sql | Complete, validated | 150 / 150 | 149 | 1 | 0 / 0 / 0 |

The single failed case is `sql/_36_guava/cbrd_27461/cases/cbrd_27461.sql`. It contains 26 query mismatches. This is a wrong-result failure, with no testcase error or crash record.

The status snapshot also reports successful debug/release builds and shell. Medium has a successful status from run 38722418817. These are contextual statuses. This investigation collected and analyzed only SQL, as requested.

| Identity | Value |
| --- | --- |
| Tested engine / PR head | `71ae9f3f615cf09025c6a29ed9841b2ad9ecaa43` |
| Consumed debug build | Run `38687274058`, attempt `1` |
| Testcase repository | `CUBRID/cubrid-testcases` |
| Tested testcase commit | `b016b6d687e713c86d4fe011664d2924b8fd41ee` |
| Testcase branch | `tc/pr-7157` |
| Collector | `cubrid-ci 0.2.0 (9536bd3c2867, release)` |
| Collection time | `2026-10-19T07:07:08.179129382Z` |
| Terminal observation | `20261019T070703.525314939Z-3569299-0` |

The workflow's GitHub `head_sha` is `1dceac8add1801aef564b27624b8fbb5b6f62d59`. This identifies the workflow revision. The shard's build provenance identifies `71ae9f3f` as the tested engine. Rerunning the workflow did not add the newer optimizer fix to that engine.

The head command, manifest, observation pair, summary, raw index, and failure metadata pass their schemas. All 28 indexed raw files match their lengths and SHA-256 digests. Counts reconcile. The report gate permits a full head report. No binary artifacts were requested or downloaded.

## Observed failure and cause

The [exact testcase source](https://github.com/CUBRID/cubrid-testcases/blob/b016b6d687e713c86d4fe011664d2924b8fd41ee/sql/_36_guava/cbrd_27461/cases/cbrd_27461.sql) creates rows `(2,1), (3,2), (4,3), (5,4), (10,9)`, with an index on `c2`.

```sql
select count(*) from tree_t
start with c2 = 1 connect by c2 = prior c1;
```

The hierarchy contains four rows. Both CI and the local PR build return `1`, the number of indexed START WITH roots. Without START WITH, another COUNT query returns the table row count `5` instead of the hierarchy count `11`. The same case also detects incorrect MIN/MAX, split GROUP BY groups, split analytic partitions, and incorrect ORDER BY limits.

[Optimizer fix `4adcd409072b189f5d965bde5750c53176d90de0`](https://github.com/CUBRID/cubrid/commit/4adcd409072b189f5d965bde5750c53176d90de0) disables optimizations that assume the scan count or index order describes the hierarchy output. Its parent is exactly this PR's merge base, `5b1867174df8dac9b6b9e9ce5a90f983f6bf19b2`.

PR #7157 changes only `src/base/perf_monitor.c` and a comment in `src/storage/page_buffer.c`. The optimizer fix changes `src/optimizer/plan_generation.c`, `src/optimizer/query_planner.c`, `src/parser/xasl_generation.c`, and `src/query/query_executor.c`. The PR head does not contain that fix.

The testcase entered the public testcase repository through [testcase PR #3731](https://github.com/CUBRID/cubrid-testcases/pull/3731), commit `2d7b259c2915ea079b82400a41928d2af280f22b`, on October 15. The testcase branch used by CI includes it. The engine fix also merged on October 15, after the engine baseline used here.

## Controlled local reproduction

All three runs use the exact CI testcase commit, with no patches. The SQL file, answer, JDBC driver, locale library, and effective configurations are identical across runs. Configuration comparison replaces only each attempt's absolute directory prefix.

| Engine | Expected / executed cases | Verdict | Query mismatches | Retained attempt |
| --- | --- | --- | --- | --- |
| PR head `71ae9f3f` | 1 / 1 | FAIL | 26 | `head-native-03` |
| Exact merge base `5b186717` | 1 / 1 | FAIL | 26 | `base-native-03` |
| Base plus optimizer fix `4adcd409` | 1 / 1 | PASS | 0 | `fixed-native-02` |

Both failing runs reproduce all 26 CI query/diff blocks exactly. Their complete `.result` files are byte-identical. The fixed engine's `.result` is byte-identical to the expected answer.

Each run has one expected case and one executed case, with no skips or testcase errors. Root and per-case summaries, `main.info`, both XML artifacts, generated results, and terminal log markers reconcile. The passing run also passes the focused runner's strict verifier. The runner returns exit zero for both verdicts, so exit status alone was not used.

The native invocation is:

```bash
TESTKIT_NATIVE=sql TESTKIT_CONTAIN=1 testkit sql -c <attempt>/conf/sql.conf
```

The builds use `debug_gcc`. The runner uses JDK `1.8.0_462`, JDBC `test_default.xml`, charset `en_US.utf8`, and one slot. The installed native runner is `cubrid-testkit dev`, SHA-256 `31be3b1e542b05d1ac7581d47f785319ce61421f4b5d94681a9c558d71445f5a`.

Every attempt has a disposable installation, CTP tree, HOME, configuration, registry, and contained process environment. Final runs reuse the generated locale library with `need_make_locale=no`. They use the JDBC driver built from pinned submodule `57d2c75d73ee820c26ac049b7ba758f5e646519a`. All runtime configuration paths point into the attempt. The host master-port override is removed.

The source CTP assets are at commit `9c62858b10005d721546cc007be260844033b9e9`, with existing local modifications. Their patch is retained outside the documentation repository. All final runs copy the same assets. These experiments establish the selected case's behavior, rather than equivalence to the complete CI environment or corpus.

Eight attempts are retained. `head-native-01` lacked the JDBC installation. `base-native-01` used the same incomplete installation and was stopped before testcase execution. `head-native-02` and `fixed-native-01` inherited a host broker configuration path and could not connect to the expected broker port. `base-native-02` stopped during snapshot setup because a preserved registry directory already existed. These five attempts are inconclusive and have no testcase verdict. The three final runs above correct those setup conditions.

## Chronicle history

`cubrid-tcc 0.3.0` reports `SEEN_BEFORE`, with five prior failed observations. Four concern other PRs. Git objects establish identical SQL and answer blobs across all listed failures and the requested run.

| Earlier run | PR | Tested engine | Recorded result |
| --- | --- | --- | --- |
| [38690982337](https://github.com/CUBRID/cubrid/actions/runs/38690982337) | #7604 | `cbd466a2` | FAIL |
| [38722418817](https://github.com/CUBRID/cubrid/actions/runs/38722418817) | #7157 | `71ae9f3f` | FAIL |
| [38848190241](https://github.com/CUBRID/cubrid/actions/runs/38848190241) | #7658 | `24d2542f` | FAIL |
| [38862915270](https://github.com/CUBRID/cubrid/actions/runs/38862915270) | #8183 | `2b07f612` | FAIL |
| [38868725373](https://github.com/CUBRID/cubrid/actions/runs/38868725373) | #8001 | `b74043df` | FAIL |

The status query contains 58 observations: 52 passes and 6 failures, including the requested run. Its overall status and flakiness assessment are `UNKNOWN` because coverage and execution context are incomplete. Mixed outcomes across different engines do not establish flakiness. These history records support prior occurrence, without proving identical root causes on the other PRs. Their engine objects are unavailable locally, so their ancestry was not inferred.

## CI baseline limitation and attribution

`cubrid-ci collect-base` independently resolves target `develop` at `4adcd4090` and exact merge base `5b1867174`. Its PR number and head match the pinned head snapshot.

The selected baseline is [run 38761274559, attempt 1](https://github.com/CUBRID/cubrid/actions/runs/38761274559). Collection exits `4` with `identity_or_integrity`: `result identity mismatch: shard 01 workflow result and JUnit counts disagree`. Observation `20261019T070832.802777751Z-3569344-0` is incomplete. Shards `00` through `09` are retained, but no complete SQL summary is validated. Retained bytes are not a suite verdict. No binary budget was consumed.

The baseline command, manifest, and observation schemas validate. The suite evidence fails integrity validation. No API fallback bypasses this error. Therefore the sole head failure is **uncomparable against CI baseline evidence**. Shared, additional-on-head, and baseline-only CI failures cannot be determined. This limit does not invalidate the head's complete 149/1 inventory.

Local experiments independently prove that the selected signature exists on the exact merge base. They do not repair the rejected CI baseline bundle.

| Claim | Assessment | Falsifier and next action |
| --- | --- | --- |
| PR #7157 introduced this signature | Unlikely, high confidence against attribution | A controlled head/base run with different results would contradict the current byte-identical outputs. Preserve the paired evidence. |
| The expected answer is incorrect | Rejected for the observed signature, high confidence | The fixed engine would also disagree if the supplied answer were incorrect. It instead matches the complete answer byte-for-byte. Keep the testcase. |
| The tested engine lacks CBRD-27461's fix | Confirmed by ancestry and controlled runs, high confidence | Applying only that existing fix must remove the signature. The base-to-fix comparison does so. Update the engine branch before the next CI run. |

The complete case already executes in less than two seconds locally. This investigation retains its checks instead of reducing their coverage, because the requested question concerns attribution and testcase validity. No new engine fix is proposed.

## Next action and retained evidence

1. Update PR #7157 onto a develop revision containing `4adcd4090` under the normal integration approval workflow.
2. Run SQL CI for the resulting engine commit and verify that CI consumes that commit and the intended testcase revision.
3. Investigate the baseline collector's shard-01 count mismatch separately if a validated historical CI comparison is still needed.

The testcase should not be removed or given the old incorrect results. This task did not change engine/testcase source, trigger CI, publish comments, or merge a branch. Generated CCI version headers were restored. The original source and testcase checkouts finish clean.

Local evidence root: `/home/vimkim/tmp/pr7157-sql-ci-20261019.eDFuFw`.

- `head-result.json`, `head-validation.json`, and `status.json`: pinned head acquisition and validation.
- `base-result.json` and `base-validation.json`: baseline relationship, incomplete acquisition, and exact integrity diagnostic.
- `assessment.json`: report gate inputs, with baseline `invalid`.
- `paired-verification.json` and `audit_replays.py`: reconciled artifacts, identical failure signatures, configurations, assets, and outputs.
- `attempt-inventory.json` and the eight attempt directories: setup outcomes, preflights, commands, process exits, and original artifacts.
- `tcc-history.json`, `tcc-status.json`, `history-inputs.json`, and `tcc-other-pr-evidence.json`: retained Chronicle history and testcase blob comparison.
- `source-relationship.json`, `pr-delta.patch`, `fix8146.patch`, and build logs: engine relationship and build evidence.
- `ctp-assets-existing.patch` and `ctp-status-before.txt`: pre-existing tool-asset modifications, preserved without edits.

The collector-owned head bundle is under `/home/vimkim/.local/share/cubrid-ci-data/github-actions/CUBRID-cubrid/pr-7157/71ae9f3f615cf09025c6a29ed9841b2ad9ecaa43`. The baseline bundle uses the adjacent `commits/5b1867174df8dac9b6b9e9ce5a90f983f6bf19b2` directory.

The auxiliary source worktree `/home/vimkim/gh/cb/pr7157-sql-baseline` ends detached at `4adcd4090`, matching its installed build. The original source remains on `CBRD-26500-pr7157-review` at `71ae9f3f`.
