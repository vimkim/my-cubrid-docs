# PR #7538 `test_shell` differential diagnosis

## Executive conclusion

**Observed:** the normalized `cubrid-ci` inventories report 22 failures for PR #7538 and 19 for the pinned `feat/oos` baseline. Their set difference is three current-only tests and no baseline-only tests.

**Observed:** the downloaded JUnit artifacts tell a more precise story. They contain 23 failing tests for the current job and 21 for the baseline. On that artifact-grounded view, only two tests are current-only:

- `shell/_08_shard/_50_cubridsus/bug_bts_10792/cases/bug_bts_10792.sh`
- `shell/_24_apricot/_01_cursor_holdability/_01_cursor_functional/cases/_01_cursor_functional.sh`

`log_enc_04`, the third normalized addition, also failed on the baseline with the same decisive signature. The baseline CircleCI tests API omitted it even though the baseline JUnit XML recorded the failure. The reported arithmetic difference is therefore:

```text
reported +3 = 2 genuine run-result additions
            + 1 asymmetric normalization omission (`log_enc_04` on baseline)
```

The evidence does not justify a PR #7538 code change:

- `bug_bts_10792` fails an exact timing/count boundary in broker/shard logs and is most consistent with run variability.
- `_01_cursor_functional` changes exception class/message despite identical engine `cubrid-jdbc` gitlinks; testcase or packaged-runtime drift remains the leading explanation, but the exact baseline testcase checkout was not retained.
- `log_enc_04` is inherited baseline behavior, not a PR regression.

A targeted rerun is useful only for the two artifact-current-only tests, after pinning the same testcase checkout and preserving the installed JDBC JAR identity for both engine revisions. No rerun is needed to decide that `log_enc_04` is not introduced by PR #7538.

## Scope and exact identities

| Field | Current PR snapshot | Pinned baseline snapshot |
|---|---|---|
| PR | CUBRID #7538, `[CBRD-26067] Add STORAGE FORCE_OUTLINE column option` | CUBRID #6864, `feat/oos` tracking PR |
| Engine commit | `82a0a4bb1cf070b785a9c3d73ba40c425ddd6096` | `0ad6afc0ff871f5aa6c002923868fc6527149ea0` |
| Branch | `CBRD-26067-storage-force-outline` | `feat/oos` |
| Base | `feat/oos` | `develop` |
| CircleCI `test_shell` job | [142418](https://circleci.com/gh/CUBRID/cubrid/142418) | [142161](https://circleci.com/gh/CUBRID/cubrid/142161) |
| Job interval (UTC) | 2026-07-31 06:51:56.797 – 07:39:59.998 | 2026-07-30 15:10:35.365 – 15:57:21.368 |
| Bundle collected (UTC) | 2026-07-31 10:18:36.335575814 | 2026-07-31 09:06:30.613342470 |
| Build | `11.5.0.2464-82a0a4b`, 64-bit optdebug | `11.5.0.2460-0ad6afc`, 64-bit optdebug |
| Test count | 3,249 | 3,244 |
| Evidence | `/home/vimkim/gh/cubrid-circleci-analyzer/data/CBRD-26067/82a0a4b/test_shell` | `/home/vimkim/gh/cubrid-circleci-analyzer/data/CBRD-26357/0ad6afc/test_shell` |

The local worktree `HEAD`, the current manifest `resolved_commit`, and current summary commit all match the full current SHA. The baseline manifest and summary both match the full pinned baseline SHA. The merge-base is exactly `0ad6afc0ff871f5aa6c002923868fc6527149ea0`.

Evidence was collected and validated with `cubrid-ci 0.1.0 (6f1272cb94f7, release)`.

The PR-only non-merge commits are:

```text
dfe30e5b09abf8411ade72f914d01d71b325d900 Add STORAGE FORCE_OUTLINE column option
64e5dbbbf699c1b69ec5ddff436eca1dddc54069 Fix code style check
d9756dd85864f51cd8205e319b7ef7a31439c049 Refine FORCE_OUTLINE storage policy
```

## Testcase revision and environment identity

**Observed:** neither `summary.json` contains a `testcase_revision` field, and both `sources/index.json` files are empty.

**Observed:** the current job's retained step log records this exact checkout:

```text
cubrid-testcases-private-ex @ 3e3a78fd780cb0869024472e51c3f30edf14ec26
```

**Unknown:** the baseline retained test-step logs begin after checkout, so they do not prove the baseline testcase SHA.

**Inferred, not proved:** the current checkout log records a forced update from `5e3c3aef` to `3e3a78fd`. Commit `5e3c3aefb8324888ad6b6f081d2b7ce9733a560c` existed before the baseline run and is the likely baseline checkout, but it must not be treated as an established identity without the missing checkout evidence.

The retained `main_snapshot.properties` files differ only in `AUTO_TEST_VERSION`. They otherwise show the same Java 1.8 runtime and operating-system environment. The engine tree entries are identical across the two engine commits:

```text
cubrid-jdbc 41afc2a33b8ee2ae6f39ef6bd1a7e5091f705102
cubrid-cci  2fb8d6d02c41386be0d56c3cfc6a14ad7e17ac15
```

The installed JDBC JAR checksum was not retained, so identical gitlinks do not prove byte-identical packaged JARs.

## Count reconciliation

### Normalized CircleCI tests API view

| Result | Current | Baseline | Difference |
|---|---:|---:|---:|
| success | 3,197 | 3,195 | +2 |
| failure | 22 | 19 | +3 |
| error | 0 | 0 | 0 |
| skipped | 30 | 30 | 0 |
| unknown | 0 | 0 | 0 |
| total | 3,249 | 3,244 | +5 |

Normalized failure sets:

```text
current failures:  22
baseline failures: 19
current - baseline: 3
baseline - current: 0
intersection:       19
```

Normalized `current - baseline`:

```text
shell/_08_shard/_50_cubridsus/bug_bts_10792/cases/bug_bts_10792.sh
shell/_24_apricot/_01_cursor_holdability/_01_cursor_functional/cases/_01_cursor_functional.sh
shell/_36_damson/cbrd_23608_tde/log_enc_04/cases/log_enc_04.sh
```

Normalized `baseline - current` is empty.

### Raw JUnit artifact view

The JUnit XML was independently parsed by taking every `testcase` element with a `failure` child.

| Artifact result | Current | Baseline | Difference |
|---|---:|---:|---:|
| unique failing testcases | 23 | 21 | +2 |
| current - baseline | 2 | — | — |
| baseline - current | — | 0 | — |
| intersection | 21 | 21 | — |

Two normalization omissions explain the count mismatch between API data and artifacts:

- `bug_bts_5730` failed in both jobs' JUnit XML but appears in neither normalized inventory.
- `log_enc_04` failed in both jobs' JUnit XML, but appears only in the current normalized inventory.

This report inventories the requested 22 normalized current failures exactly once below, then treats the hidden shared `bug_bts_5730` separately as a collector discrepancy.

## Ranked hypotheses

| Rank | Hypothesis | Prediction | Falsifier | Result |
|---:|---|---|---|---|
| 1 | Normalization artifact contributes to `+3` | A baseline JUnit failure is absent from its normalized set | Both raw artifact sets reproduce the normalized three-test delta | Confirmed for `log_enc_04`; artifact delta is +2 |
| 2 | `bug_bts_10792` is run-variable | Failure occurs at a timing/count boundary and can change under repeat | Stable failure only on PR head with identical pinned inputs, stable pass on baseline | Supported: current has `cnt3=14`, `cnt4=14`, `cnt2=14`, so strict `>` fails |
| 3 | `_01_cursor_functional` is testcase/runtime drift | Engine JDBC source identity is unchanged while expected/actual Java exception behavior differs | Exact testcase sources and installed JARs are identical, and engine-only bisection selects the PR | Partially supported; baseline testcase SHA and JAR hashes are missing |
| 4 | Shared failures are inherited OOS/develop behavior | Current and baseline show materially the same decisive signatures | A shared test changes to a PR-specific signature | Confirmed for all 19 normalized shared tests at the available signature depth |
| 5 | FORCE_OUTLINE changes default attributes or exposes an old assumption | A non-FORCE schema reaches changed policy state or changed output requires that state | Default attributes are explicitly decoded as `DEFAULT`, and target tests never set FORCE_OUTLINE | Falsified by source/state tracing for these failures |

## PR-only path and causality boundary

The exact diff `0ad6afc..82a0a4b` changes 20 files: parser/schema round-trip, schema flags, `OR_ATTRIBUTE` policy representation, `heap_attrinfo_determine_disk_layout()`, messages, unload printing, and OOS SQL unit tests. It does not change broker/shard code, JDBC code, TDE/recovery code, or either driver submodule.

The relevant state flow is:

```text
explicit STORAGE FORCE_OUTLINE syntax
  -> SM_ATTFLAG_OOS_FORCE_OUTLINE
  -> OR_ATTRIBUTE::oos_storage = FORCE_OUTLINE
  -> heap_attrinfo_determine_disk_layout()
     selects only variable, non-NULL values whose serialized size is > 16B
```

For an ordinary attribute, `or_get_current_representation()` explicitly assigns `OR_ATTRIBUTE_OOS_STORAGE_DEFAULT`. In the layout function, the new early loop selects only `oos_storage == FORCE_OUTLINE`. The ordinary record-size-gated OOS loop then skips already-selected values and preserves the existing DEFAULT/PREFER_INLINE priority behavior.

All three normalized additions use ordinary schemas. Their retained traces contain no `STORAGE FORCE_OUTLINE`, `STORAGE PREFER_INLINE`, LIKE/unload/load propagation of the flag, or ALTER operation capable of adding it:

- `bug_bts_10792`: two ordinary `student(s_no int, s_name varchar(10000000))` tables, followed by a shard broker/JDBC load.
- `_01_cursor_functional`: JDBC cursor/holdability API behavior; failure occurs while creating unsupported statement modes.
- `log_enc_04`: encrypted ordinary tables and recovery-index inspection; its baseline artifact fails identically.

The records may still enter the pre-existing OOS path under DEFAULT policy, but the PR does not change that policy path. No observed failure requires a FORCE_OUTLINE flag or a PR-changed state.

## Compact inventory of all 22 normalized current failures

| # | Testcase | Node / runtime | Decisive signature | Classification |
|---:|---|---|---|---|
| 1 | `shell/_06_issues/_12_2h/bug_bts_9836/cases/bug_bts_9836.sh` | 24 / 61.548s | call-stack activation-list expectation mismatch | shared; configuration expectation |
| 2 | `shell/_06_issues/_14_2h/bug_bts_14120/cases/bug_bts_14120.sh` | 36 / 10.227s | server activation-list expectation mismatch | shared; configuration expectation |
| 3 | `shell/_06_issues/_24_2h/cbrd_25481/cases/cbrd_25481.sh` | 32 / 166.727s | transaction aborted in multiple-large-JSON loaddb subcase | shared; known TT_LOADDB/OOS cluster |
| 4 | `shell/_06_issues/_26_1h/cbrd_26527/cases/cbrd_26527.sh` | 21 / 12.622s | cannot extract `MULTIPAGE_OBJECT_HEAP` HFID | shared; OOS/utility expectation |
| 5 | `shell/_08_shard/_50_cubridsus/bug_bts_10792/cases/bug_bts_10792.sh` | 4 / 21.691s | subcase 2: `14 > 14` is false | artifact-current-only; run variability likely |
| 6 | `shell/_24_apricot/_01_cursor_holdability/_01_cursor_functional/cases/_01_cursor_functional.sh` | 12 / 23.863s | `SQLException(UnsupportedOperationException)` vs expected `SQLFeatureNotSupportedException` | artifact-current-only; testcase/runtime drift |
| 7 | `shell/_35_cherry/issue_21522_json/cbrd_23430/cases/cbrd_23430.sh` | 11 / 10.521s | failed to connect to `jsondb` | shared; service/runtime failure |
| 8 | `shell/_35_cherry/issue_21654_server_side_loaddb/bigPageSize/cases/bigPageSize.sh` | 3 / 18.265s | missing `Total 256 object(s) inserted` completion line | shared; loaddb/OOS-era baseline failure |
| 9 | `shell/_35_cherry/issue_21654_server_side_loaddb/loaddb_CS/_01_utility/_17_loaddb/itrack_10006/cases/itrack_10006.sh` | 31 / 6.738s | loaddb subcase NOK; server-side load abort family | shared; known TT_LOADDB/OOS cluster |
| 10 | `shell/_35_cherry/issue_21654_server_side_loaddb/loaddb_CS/_05_addition/bug_xdbms_sus880/cases/bug_xdbms_sus880.sh` | 8 / 8.241s | empty query result/server no longer running | shared; known TT_LOADDB/OOS cluster |
| 11 | `shell/_36_damson/cbrd_23608_tde/file_enc_01/cases/file_enc_01.sh` | 15 / 9.638s | extra/missing TDE page-algorithm trace lines | shared; TDE/OOS output drift |
| 12 | `shell/_36_damson/cbrd_23608_tde/file_enc_02/cases/file_enc_02.sh` | 12 / 6.455s | extra AES file/page trace pair | shared; TDE/OOS output drift |
| 13 | `shell/_36_damson/cbrd_23608_tde/file_enc_03/cases/file_enc_03.sh` | 31 / 6.661s | differing AES/deallocation trace counts | shared; TDE/OOS output drift |
| 14 | `shell/_36_damson/cbrd_23608_tde/file_enc_04/cases/file_enc_04.sh` | 15 / 6.531s | differing NONE page-algorithm trace counts | shared; TDE/OOS output drift |
| 15 | `shell/_36_damson/cbrd_23608_tde/file_enc_05/cases/file_enc_05.sh` | 3 / 8.764s | differing page deallocation/NONE trace counts | shared; TDE/OOS output drift |
| 16 | `shell/_36_damson/cbrd_23608_tde/file_enc_07/cases/file_enc_07.sh` | 33 / 12.612s | extra AES page-algorithm traces | shared; TDE/OOS output drift |
| 17 | `shell/_36_damson/cbrd_23608_tde/log_enc_04/cases/log_enc_04.sh` | 45 / 30.757s | `RVHF_INSERT_NEWHOME is missing` | normalized-only addition; artifact-shared baseline failure |
| 18 | `shell/_36_damson/cbrd_23608_tde/tbl_enc_08/cases/tbl_enc_08.sh` | 23 / 6.747s | unexpected OOS `MULTIPAGE_OBJECT_HEAP` in diag output | shared; TDE/OOS output drift |
| 19 | `shell/_36_damson/cbrd_23608_tde/tbl_enc_14/cases/tbl_enc_14.sh` | 4 / 6.676s | unexpected OOS `MULTIPAGE_OBJECT_HEAP` in diag output | shared; TDE/OOS output drift |
| 20 | `shell/_37_elderberry/cbrd_23842_cdc/bug/cbrd_27064/cases/cbrd_27064.sh` | artifact node 8 / 86.011s | CDC extractor `rc=-10`, severe target-count shortfall | shared; CDC extractor baseline failure |
| 21 | `shell/_37_elderberry/cbrd_23842_cdc/bug/cbrd_27075/cases/cbrd_27075.sh` | artifact node 42 / 193.171s | page-size configurations report extractor/find errors, `CONFIGS_OK=0` | shared; CDC extractor baseline failure |
| 22 | `shell/_39_fig_cake/cbrd_25365/cases/cbrd_25365.sh` | 47 / 1252.250s | timeout plus missing creation-time values | shared; timeout/runtime failure |

The normalized metadata cannot assign nodes to the two CDC tests (`node_index: null`); their downloaded JUnit artifacts establish nodes 8 and 42 respectively.

## Detailed analysis: `bug_bts_10792`

**Observed signature:** result `failure`, node 4, 21.691s, current testcase checkout `3e3a78fd...`. Subcase 1 passes. The Java workload runs for 30 seconds against two shard databases, then the script counts broker log messages:

```text
cnt2 = 14  New CAS connected
cnt3 = 14  CAS MEMORY USAGE ... EXCEEDED MAX SIZE
cnt4 = 14  CAS MEMORY USAGE ... EXCEEDED HARD LIMIT
test: cnt3 > cnt2 && cnt4 > cnt2
actual: 14 > 14 -> false
```

The retained server-log check reports zero `Internal Error` entries. The target node has no core or separately uploaded error artifact, and both database servers stop normally.

**Baseline comparison:** the baseline raw tests API records `success`, 21.883s. The testcase existed in the baseline test tree. Its exact checkout SHA is unknown. The likely pre-update tree's last change to this testcase was `d1a12c94f` on 2026-02-04, and its strict-count test matches the current execution trace.

**Relevant PR path:** none. The PR changes neither broker/shard code nor JDBC, and this schema does not set FORCE_OUTLINE. Merely declaring a large-capacity `VARCHAR` does not externalize a value; the observed failure is in broker event counts.

**Root-cause category:** run/environment variability is the leading category. The result is a strict inequality at an exact count tie, after a time-bounded concurrent workload.

**PR relation:** `unlikely`.

**Confidence:** high that no direct PR path is demonstrated; medium that nondeterminism is the complete root cause because no repeat series was run.

**Falsifier or missing evidence:** repeated, pinned runs that consistently fail only on `82a0a4b` and pass on `0ad6afc`, with the same testcase SHA and broker configuration, would falsify the variability classification and require engine bisection.

**Recommended next action:** run only this testcase several times against both exact engine builds with one pinned testcase checkout, recording `cnt1`–`cnt4`. Do not change the answer or threshold before establishing the distribution.

## Detailed analysis: `_01_cursor_functional`

**Observed signature:** result `failure`, node 12, 23.863s, current testcase checkout `3e3a78fd...`. The first semantic difference occurs in test5, “error on updatable holdable,” and repeats in test7, “error on scrollable sensitive result”:

```text
actual:   java.sql.SQLException: java.lang.UnsupportedOperationException
          Caused by: java.lang.UnsupportedOperationException

expected: java.sql.SQLFeatureNotSupportedException: Not supported method
          at cubrid.jdbc.driver.CUBRIDException.notSupported(...)
```

Other preceding cursor output matches. The target node has no core or separately uploaded error artifact.

**Baseline comparison:** the baseline raw tests API and baseline node-20 JUnit XML record `success`, 19.691s. The Java runtime is the same major/version in both retained snapshots. The exact baseline testcase SHA is unknown.

**Relevant PR path:** none found. The engine commits have the identical `cubrid-jdbc` gitlink, and the PR does not touch JDBC, connection, cursor, or Java code. No FORCE_OUTLINE schema state is used.

**Root-cause category:** testcase/input or packaged-runtime drift is most likely, but remains unresolved. A changed `Main.java`, answer context, or installed JAR can explain the exception-class difference. Identical gitlinks weaken an engine-source explanation but do not prove identical installed JAR bytes.

**PR relation:** `unlikely`.

**Confidence:** medium-high that the observed exception mismatch is outside the direct FORCE_OUTLINE path; medium on the drift category because the two missing identities prevent a byte-for-byte comparison.

**Falsifier or missing evidence:** proving identical target testcase sources and identical installed JDBC JAR checksums for both jobs, followed by an engine-only reproduction that changes at a PR commit, would falsify the drift classification.

**Recommended next action:** recover the exact baseline testcase checkout from job retention, diff this testcase's script/Java/answer files against `3e3a78fd...`, and compare installed `cubrid_jdbc.jar` checksums. Only then run the single testcase on both engine builds.

## Detailed analysis: `log_enc_04`

**Observed signature:** normalized result `failure`, node 45, 30.757s, current testcase checkout `3e3a78fd...`. The test creates encrypted ordinary tables, performs heap operations and partition reorganization, extracts recovery indexes, and gets:

```text
RVHF_MVCC_REDISTRIBUTE = 1
RVHF_INSERT            = 8
RVHF_UPDATE            = 6
RVHF_DELETE            = 2
RVHF_INSERT_NEWHOME    = 0
RVHF_INSERT_NEWHOME is missing!
```

The target node has no core or separately uploaded error artifact.

**Baseline comparison:** the baseline normalized raw tests API omits the testcase, but baseline node-30 JUnit XML records a failure at 31.282s with the same decisive line: `RVHF_INSERT_NEWHOME is missing!`. It is therefore artifact-shared, not truly current-only.

**Relevant PR path:** the test uses large ordinary `VARCHAR` values that may enter existing DEFAULT OOS behavior, but never sets FORCE_OUTLINE. More decisively, the exact baseline engine already has the same missing recovery index.

**Root-cause category:** inherited baseline behavior or a testcase expectation issue. Root cause within that baseline behavior was not re-solved because it cannot explain a PR-only regression.

**PR relation:** `unlikely`.

**Confidence:** high.

**Falsifier or missing evidence:** a corrected artifact parser showing the baseline XML testcase did not actually fail would be required to make it current-only; the retained XML directly contradicts that.

**Recommended next action:** no PR #7538 code action. Fix or investigate the CircleCI-tests/JUnit normalization discrepancy separately; investigate the baseline recovery-index expectation only under its own scope.

## Evidence-backed grouping of the 19 normalized shared failures

Every normalized shared testcase has the same broad decisive signature in both jobs. Runtime and exact counts vary, but none changes into a new PR-specific failure mode.

### Known TT_LOADDB/OOS lazy-file cluster (3)

- `cbrd_25481`
- `itrack_10006`
- `bug_xdbms_sus880`

The required prior report, `/home/vimkim/gh/my-cubrid-docs/cbrd-26357/0ad6afc/failed_tcs/cbrd_25481-report.md`, traces these to the same server-side `TT_LOADDB`/OOS lazy-file creation failure family and demonstrates one local PoC addressing all three. Current artifacts retain that family: aborted large-JSON load, loaddb NOK, and empty query/server-not-running behavior. These failures are inherited from the exact baseline. The supporting report is evidence about this shared cluster, not proof about either true addition.

### TDE/OOS diagnostic-output drift (8)

- `file_enc_01`, `file_enc_02`, `file_enc_03`, `file_enc_04`, `file_enc_05`, `file_enc_07`
- `tbl_enc_08`, `tbl_enc_14`

Both jobs show materially the same TDE page-algorithm trace-count mismatches. The two table tests both expose the OOS `MULTIPAGE_OBJECT_HEAP` entry absent from their expected diagnostic output. These are baseline expectation/conformance failures, not introduced by this PR.

### Other OOS-era utility/loaddb expectations (2)

- `cbrd_26527`: both jobs fail to extract a `MULTIPAGE_OBJECT_HEAP` HFID for the table.
- `bigPageSize`: both jobs reach “Start object loading” but omit the expected `Total 256 object(s) inserted` line, with zero `Internal Error` matches.

The names are shared and the decisive signatures match. Their deeper baseline causes remain unresolved here.

### Configuration expectation drift (2)

- `bug_bts_9836`
- `bug_bts_14120`

Both jobs show the same call-stack activation-list expectation differences. No PR-only path is involved.

### Service/timeout failures (2)

- `cbrd_23430`: both jobs fail to connect to `jsondb` at the same point.
- `cbrd_25365`: both run about 1,252 seconds, time out, and then report missing creation-time fields in later checks.

These are inherited runtime failures; this report does not assign a deeper common root cause.

### CDC extractor failures (2)

- `cbrd_27064`: both jobs report extractor `rc=-10` and severe expected-count shortfalls for delete/update overflow cases.
- `cbrd_27075`: both jobs report extractor/find errors across page-size configurations and `CONFIGS_OK=0`, with `CORRUPTION=0`.

Counts and duration vary, but the failure modes are materially the same and pre-exist the PR.

## Hidden shared artifact failure

`shell/_35_cherry/issue_21654_server_side_loaddb/loaddb_CS/_06_issues/_11_2h/bug_bts_5730/cases/bug_bts_5730.sh` fails in both JUnit artifact sets but is absent from both normalized inventories. Current artifact node 49 reports subcase 3 NOK; baseline artifact node 30 reports the corresponding server-side-loaddb path failure. Because the omission is symmetric, it does not affect the current-minus-baseline delta, but it proves that normalized failure counts are not complete representations of the retained JUnit results.

## Direct answer: why are there three more than `feat/oos`?

There are three more only in the normalized CircleCI-tests view:

1. `bug_bts_10792` passed on the baseline and failed at a strict broker-log count tie on the current run.
2. `_01_cursor_functional` passed on the baseline and failed because the observed JDBC exception class/message differed from the answer.
3. `log_enc_04` appears current-only only because the baseline tests API omitted it; baseline JUnit XML proves it failed there too.

Thus the raw artifact-grounded difference is two, with no disappearing baseline failures. Neither true addition has a demonstrated PR #7538 call path.

## Recommended disposition

- **PR code change:** no. Current evidence does not establish a direct or plausible FORCE_OUTLINE regression.
- **Targeted rerun:** yes, only for `bug_bts_10792` and `_01_cursor_functional`, and only after pinning one testcase SHA for both engine builds. Preserve broker counts and installed JDBC JAR hashes.
- **`log_enc_04`:** no PR action; it is inherited baseline behavior.
- **CI evidence tooling:** separately reconcile the CircleCI tests API with JUnit XML so failures such as `bug_bts_5730` and baseline `log_enc_04` are not silently omitted.
- **Known TT_LOADDB cluster:** continue under its existing baseline/OOS investigation, not under CBRD-26067.

## Limitations and smallest resolving checks

1. **Baseline testcase SHA is unknown.** Smallest check: recover the checkout line from complete baseline node logs or preserved job metadata. Do not substitute inferred `5e3c3aef...` as fact.
2. **Exact testcase sources were not downloaded into either bundle.** Smallest check: once both SHAs are known, compare only the three target testcase directories.
3. **Installed JDBC JAR identity is unknown.** Smallest check: preserve SHA-256 and manifest/version for `/home/CUBRID/jdbc/cubrid_jdbc.jar` in a paired rerun.
4. **No paired local reproduction was run.** A head-only reproduction would not isolate PR causality, and the exact baseline binary/testcase combination was not available locally. Smallest check: single-TC runs against both exact engine builds with one testcase tree.
5. **Normalized and artifact failure sets disagree.** Smallest check: make the collector report or reject any mismatch between tests API failures and JUnit `failure` elements.

## Review status

The `cubrid-ci-analyze` workflow requests a `grill-with-docs` review. That review capability is not available in this runtime, so this report is **not represented as grilled**. It was self-audited against both manifests, both summaries, normalized inventories, all normalized failure metadata/messages/diffs, raw tests API snapshots, JUnit XML, relevant step logs, the exact engine diff, OOS normative context, live CBRD-26067 context, and the required prior `cbrd_25481` report.

## Evidence files

Primary current evidence:

```text
/home/vimkim/gh/cubrid-circleci-analyzer/data/CBRD-26067/82a0a4b/manifest.json
/home/vimkim/gh/cubrid-circleci-analyzer/data/CBRD-26067/82a0a4b/test_shell/summary.json
/home/vimkim/gh/cubrid-circleci-analyzer/data/CBRD-26067/82a0a4b/test_shell/failed-tc.txt
/home/vimkim/gh/cubrid-circleci-analyzer/data/CBRD-26067/82a0a4b/test_shell/attempts/142418/raw/tests.json
/home/vimkim/gh/cubrid-circleci-analyzer/data/CBRD-26067/82a0a4b/test_shell/artifacts/
```

Primary baseline evidence:

```text
/home/vimkim/gh/cubrid-circleci-analyzer/data/CBRD-26357/0ad6afc/manifest.json
/home/vimkim/gh/cubrid-circleci-analyzer/data/CBRD-26357/0ad6afc/test_shell/summary.json
/home/vimkim/gh/cubrid-circleci-analyzer/data/CBRD-26357/0ad6afc/test_shell/failed-tc.txt
/home/vimkim/gh/cubrid-circleci-analyzer/data/CBRD-26357/0ad6afc/test_shell/attempts/142161/raw/tests.json
/home/vimkim/gh/cubrid-circleci-analyzer/data/CBRD-26357/0ad6afc/test_shell/artifacts/
```

Context:

```text
/home/vimkim/gh/cubrid-oos-context/OOS-CONTEXT.md
/home/vimkim/gh/my-cubrid-jira/issues/CBRD-26067-storage-force-outline.md
/home/vimkim/gh/my-cubrid-docs/cbrd-26357/0ad6afc/failed_tcs/cbrd_25481-report.md
```
