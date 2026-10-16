# PR7925: recovered CI evidence and shell failure analysis

Date: 2026-10-17, Asia/Seoul. Work Items 397 and 393.
PR: [CUBRID/cubrid #7925](https://github.com/CUBRID/cubrid/pull/7925).
Engine: `6a487cdb6cbda36ac94ad9b22009cea6cb58aa2f`.

## Result and decision boundary

The repaired collector validates all three suites from existing [run 38938588691](https://github.com/CUBRID/cubrid/actions/runs/38938588691), attempt 1.
Medium passes 975 cases. SQL passes 17,471 cases.
Shell records 3,253 passes, six failures, 30 skips, and zero unrun cases.
Each failed shell job corresponds to one failed testcase file.

The exact merge-base baseline also validates.
Three head failure signatures also occur on that baseline.
Three additional head failures have passing baseline records with identical testcase directories.
Two baseline failures have passing head records.
These comparisons establish observed differences. They do not establish that PR7925 caused those differences.

This report resolves the testcase evidence limit in the [earlier warning](ci_analysis_report_6a487cdb6_codex.md).
That warning remains an accurate record of the original incomplete observation.
The [accepted preservation decision](sa-inline-preservation-decision-20261017.md) retains its separate local verification scope.
The historical [b755678cd report](ci_analysis_report_b755678cd_run38861566581_codex.md) supplies context for another engine revision.

## Validated suite inventory

All head suites identify run `38938588691`, attempt `1`, and debug build `6a487cdb6…` from that execution.
Both release and debug build statuses are successful.

| Head suite | Collection state | CI verdict | Planned | Executed | Passed | Failed | Errors | Skipped | Unrun |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `test_medium` | completed | success | 975 | 975 | 975 | 0 | 0 | 0 | 0 |
| `test_sql` | completed | success | 17,471 | 17,471 | 17,471 | 0 | 0 | 0 | 0 |
| `test_shell` | completed | failure | 3,289 | 3,259 | 3,253 | 6 | 0 | 30 | 0 |

The shell acquisition covers all 50 shards. SQL covers ten shards. Medium covers one shard.
All 61 shard response sets are retained and validated.
The shell failures are testcase failures with reconciled records, rather than jobs without usable testcase evidence.

### Failure inventory

All rows belong to `test_shell`, and each row represents one failed testcase file.
Subchecks within a file do not increase the suite failure count.
Message line references below use each failure record's `message_path`.
Confidence is high for the observed signature and baseline classification. Confidence is low for an underlying engine cause.

| Shard and job | Full testcase path | Observed signature | Baseline classification | Category | PR relation |
| --- | --- | --- | --- | --- | --- |
| [30](https://github.com/CUBRID/cubrid/actions/runs/38938588691/job/117103553048) | `shell/_06_issues/_14_1h/bug_bts_13242/cases/bug_bts_13242.sh` | Sorted lock snapshot differs. Three polling loops reach their limit. | `additional_on_head` | Lock snapshot expectation | unknown |
| [31](https://github.com/CUBRID/cubrid/actions/runs/38938588691/job/117103552750) | `shell/_37_elderberry/cbrd_23842_cdc/thread/cases/thread.sh` | Subcheck 4 counts one `API ERROR` during server shutdown. | `additional_on_head` | CDC lifecycle | unknown |
| [36](https://github.com/CUBRID/cubrid/actions/runs/38938588691/job/117103552509) | `shell/_06_issues/_15_1h/bug_bts_15156/cases/bug_bts_15156.sh` | Server-stop success count remains zero after retries. | `also_observed_on_base` | Service lifecycle | unlikely |
| [40](https://github.com/CUBRID/cubrid/actions/runs/38938588691/job/117103552653) | `shell/_06_issues/_18_1h/bug_bts_14305/cases/bug_bts_14305.sh` | No expected interruption diagnostic. User creation and transaction-kill subchecks pass. | `additional_on_head` | Transaction interruption | unknown |
| [44](https://github.com/CUBRID/cubrid/actions/runs/38938588691/job/117103552843) | `shell/_37_elderberry/cbrd_23842_cdc/bug/cbrd_27064/cases/cbrd_27064.sh` | CDC extraction returns `rc=-10` for DELETE and UPDATE. Corruption count is zero. | `also_observed_on_base` | CDC extraction | unlikely |
| [48](https://github.com/CUBRID/cubrid/actions/runs/38938588691/job/117103552752) | `shell/_37_elderberry/cbrd_23842_cdc/bug/cbrd_27075/cases/cbrd_27075.sh` | Extraction errors across 4K, 8K, and 16K configurations. Workloads complete without counted corruption. | `also_observed_on_base` | CDC extraction | unlikely |

PR relation describes introduction of the observed signature. It does not exclude another defect or a change in failure frequency.
The baseline comparison supports six head classifications: three shared, three additional, and zero uncomparable cases.
It separately identifies two `base_only` cases.
All six head failures remain unresolved CI results.

## Collector repair and evidence validation

Collector source commit: `9536bd3c2867` in `vimkim/cubrid-ci`.
Installed version: `cubrid-ci 0.2.0 (9536bd3c2867, release)`.
The source change remains on task branch `fix/pr7925-marker-contract` pending local merge approval.

The producing [workflow at f8ae0f47](https://github.com/CUBRID/cubrid/blob/f8ae0f47b729aa27043a4c421d200c4c7403262c/.github/workflows/gha-ci.yml#L1235) captures the test command's exit status.
Its publication step writes that status as `test_rc` in `shard.done`.
The retained head markers contain 55 zero statuses and six statuses of 1.
The old parser requires `ctp_rc` and rejects every head shard before testcase reconciliation.

The repair accepts `test_rc` and the legacy `ctp_rc` alias.
Conflicting aliases, duplicate fields, malformed statuses, and inconsistent shard identities fail validation.
Status 1 permits collection only when the shard reports failed testcases.
Other nonzero statuses remain job-level failures.
Assigned counts, workflow counts, JUnit counts, failed-case identities, and suite verdicts must still reconcile before summary publication.
An exit status alone never establishes a pass.

Unchanged medium and shell markers reproduce the original parser failure in regression tests.
CLI regressions cover a complete red suite, immutable replay, unexplained status 1, and contradictory JUnit counts.
`just verify` passes 108 tests, formatting, compilation, and Clippy.
The first full run has one transient identity-fixture exit-code failure.
That test passes in isolation and during the complete rerun. Its transient cause remains unknown.
`just install` succeeds, and `cubrid-ci doctor --json` passes.

One delegated status snapshot and one exact-head collection ran for this analysis.
Head collection exits 0 at `2026-10-16T18:55:28.194883816Z`.
Observation: `20261016T185520.879050049Z-2531350-0`.
No new engine CI run occurs.

The independent validator validates the command, manifest, request, terminal observation, summaries, failure metadata, and raw indexes against their JSON schemas.
It requires the unique terminal observation whose command equals the saved result, including collection time.
Request v1 contains repository, commit, suites, and collection options. The matching terminal command binds its PR identity.
The validator also validates all 786 indexed raw file lengths and SHA-256 digests.
It independently recounts each shard's JUnit records and compares assignment, workflow, inventory, and summary counts.
All 61 build and testcase provenance records reconcile.

All 788 original provider and observation files retain their original SHA-256 digests.
The original incomplete observation remains unchanged.
The evidence root's current manifest now identifies the new complete observation.
The earlier manifest copy remains in the external validation receipts.

Neither collection requests binary artifacts. Binary consumption is zero, with the full configured budget remaining.
This option excludes archives from the analysis. It does not establish that the provider has no archives.
The report-mode gate returns `full`, with comparisons restricted to validated cases.
Its permission does not establish causality.

## Exact merge-base comparison

The baseline command independently pins PR7925 and its actual target branch.
Target tip and unique merge base both equal `fb567a629cdb390fff920542173fa36f454c74a0`.
The pinned head remains `6a487cdb6cbda36ac94ad9b22009cea6cb58aa2f`.
Relationship observation time: `2026-10-16T18:56:10.884439668Z`.

Discovery covers all paginated exact-commit statuses and GitHub Actions `check-runs` records.
It performs no repository-wide workflow scan.
All three baseline suites select existing [run 36570256001](https://github.com/CUBRID/cubrid/actions/runs/36570256001), attempt 1.
Their consumed debug build comes from run `36570061594`, attempt `1`, at the exact merge-base Engine SHA.
The workflow title mentions PR7990. The per-shard build provenance establishes the tested Engine identity.

Baseline collection exits 0 at `2026-10-16T18:57:09.216984870Z`.
Observation: `20261016T185707.991035730Z-2540136-0`.
Independent validation validates schema v3, observation v2, all suite records, and 780 indexed raw file digests.

| Baseline suite | Collection state | CI verdict | Planned | Executed | Passed | Failed | Errors | Skipped | Unrun |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `test_medium` | completed | success | 975 | 975 | 975 | 0 | 0 | 0 | 0 |
| `test_sql` | completed | success | 17,471 | 17,471 | 17,471 | 0 | 0 | 0 | 0 |
| `test_shell` | completed | failure | 3,289 | 3,259 | 3,254 | 5 | 0 | 30 | 0 |

### Input revisions and comparison limits

| Input | Head | Baseline |
| --- | --- | --- |
| Public TC SHA | `26f964b8a6e222c33765fa317eaaf4fe666d5f44` | `bdba62aee0faec05abdd861518824c69b6c1b3c5` |
| Private TC SHA | `a261508a624efc7115ac181073d40bca7fc9448c` | `c4b9d482fbd491a68510b2552df2c3cac91911fc` |
| TC branch | `tc/pr-7925` | `tc/pr-7990` |
| CTP SHA | `44e3f97c788ad82091d5b66d728852f3279b1e86` | `4d0043a7b149b3fc5d3ccb2e08c98cf8d77b34fb` |
| Build mode | debug | debug |

The validator reads all compared testcase files from the recorded local Git objects.
Git tree identities match for all eight affected `cases/` directories.
This validation covers each directory's scripts, C drivers, answers, and fixtures.
It does not establish whole-repository equality.

The [CTP comparison](https://github.com/CUBRID/cubrid-testtools/compare/4d0043a7b149b3fc5d3ccb2e08c98cf8d77b34fb...44e3f97c788ad82091d5b66d728852f3279b1e86) contains one commit and one changed file: `CTP/common/script/util_compat_test.sh`.
That change modifies CCI compatibility setup. The compared testcase scripts do not call its changed functions.
The shell initialization source is unchanged in that comparison.
The evidence does not establish image digest equality, equal host load, or equal dynamic process scheduling.
Random payloads in the CDC cases also differ between executions.
The comparison therefore identifies signatures and candidate differences, with causal attribution still open.

The two baseline-only failures are:

- `shell/_06_issues/_17_1h/cbrd_20759/hide_cubrid_replay/cases/hide_cubrid_replay.sh`: subcheck 7 reports a result-file difference on base. Head records a pass.
- `shell/_40_guava/cbrd_26349/cases/cbrd_26349.sh`: subchecks 2 and 3 report remote-column/password diagnostics on base. Head records a pass.

Their passing head records establish absence of those observed baseline failures in this run.
They do not establish that PR7925 repairs either underlying problem.

## Failure mechanisms and remaining unknowns

### Lock snapshot: bug_bts_13242

**Observed:** The testcase compares a sorted lock dump with `issue_13242.answer`.
Its source polls for an exact number of locked objects before each snapshot.
Test points 1, 5, and 6 each exhaust 60 polls.
Their expected counts are 6, 8, and 9. Observed counts are respectively 8–9, 12–14, and 15.
The final comparison fails. The baseline runs the identical testcase directory and passes.
Evidence: head message lines 521–2386 and testcase lines 23–39, 52–60, and 101–102.

**Inference:** Lock state or expected lock counts differ under this execution.
The polling limits explain why the test proceeds with snapshots that fail its expectation.
This evidence does not identify the reason for the additional locks.

**Unknown:** The retained text does not establish which transactions own every additional lock or whether timing changes the result.
The complete PR includes shared heap/query changes across 29 files.
The latest commit alone deletes an SA-only block, which does not establish a cause for this server-mode test.
PR relation remains unknown. Causal confidence is low.

**Falsifier:** Repeated controlled runs that reach the expected lock counts and still produce the same difference would reject the polling explanation.
**Next action:** Preserve complete lock dumps for all six points and compare transaction ownership under matched engine and runtime inputs.

### Service lifecycle: bug_bts_15156

**Observed:** The test kills the master, restarts services, and retries server stop.
Both head and base report a successful master-start predicate and one master process.
Both report zero matching server-stop success lines after the retry loop.
The final predicate writes NOK in both runs.
Evidence: head and base message lines 343–357, and testcase lines 63–91.

**Inference:** The repeated failure signature predates this PR head.
Its immediate cause is the server-stop predicate. An engine defect, an already stopped server, and an output expectation remain alternatives.
Introduction by PR7925 is unlikely, with medium confidence.

**Unknown:** The failure message does not include the contents of redirected `server.log` and `service.log`.
**Falsifier:** Those files could show a different operational failure despite the matching predicate.
**Next action:** Retain both redirected files and inspect server state before changing the test or engine.

### CDC lifecycle: thread

**Observed:** Only subcheck 4 fails. It stops the server while the C driver executes its finalization scenario.
The shell trace counts one `API ERROR` and one success line in `result4.log`.
The failure follows directly from the required zero-error predicate.
The identical baseline testcase passes.
Evidence: head message lines 424–431, testcase lines 156–186, and `test.c` lines 77–112.

**Inference:** The shutdown scenario encounters an API error. A finalization race is plausible.
The driver also has earlier API error branches, so the exact failing call remains unknown.
PR relation remains unknown. Causal confidence is low.

**Unknown:** The retained failure body omits the contents of `result4.log` and `finalize.log`.
**Falsifier:** `result4.log` could identify a connection or setup failure before finalization.
**Next action:** Retain those files and correlate the API call with server-stop timing.

### Transaction interruption: bug_bts_14305

**Observed:** Subcheck 1 searches `result1.log` for three expected interruption messages and finds zero matches.
The background CSQL process exits. User creation and the transaction-kill acknowledgement both pass.
The identical baseline testcase passes all predicates.
Evidence: head message lines 193–219 and testcase lines 39–57.

**Inference:** The failure concerns the interrupted client's observable output.
A diagnostic change, a timing difference, and an interruption defect remain possible.
PR relation remains unknown. Causal confidence is low.

**Unknown:** The retained failure body does not contain `result1.log`.
**Falsifier:** That file could show normal completion before the kill, rejecting a diagnostic-change explanation.
**Next action:** Retain all three result files and correlate the killed transaction with the background client.

### CDC extraction: cbrd_27064 and cbrd_27075

**Observed:** `cbrd_27064` passes its INSERT subcheck and fails DELETE and UPDATE extraction.
Head DELETE extraction returns `rc=-10` after 22 of 700 target rows. Base returns the same code after 23 rows.
Both runs return `rc=-10` before extracting any of 2,400 target UPDATE rows.
Both count zero page-corruption messages.
Evidence: head and base message lines 4–26, and the `cbrd_27064` C driver lines 111–120.

The exact [Engine API header](https://github.com/CUBRID/cubrid/blob/6a487cdb6cbda36ac94ad9b22009cea6cb58aa2f/src/api/cubrid_log.h#L55) defines `-10` as `CUBRID_LOG_FAILED_CONNECT`.
The API implementation maps multiple request, receive, and protocol failures to that code.
It does not identify one transport failure or prove page corruption.
The API source files are unchanged between the pinned merge base and head.

`cbrd_27075` completes 2,000 updates for each page size, with zero counted corruption and zero find errors.
Head extraction error counts are 2, 2, and 1 for 4K, 8K, and 16K pages.
Base reports four extraction errors for each page size.
Both runs fail all three configuration predicates because extraction errors must be zero.
Evidence: head and base message lines 4–13, and the `cbrd_27075` shell script lines 145–185.

**Inference:** Both CDC signatures predate this PR head.
The available evidence supports extraction/API failures. It does not establish the historical corruption mechanism described in the testcase comments.
Introduction by PR7925 is unlikely, with medium confidence.

**Unknown:** The retained text omits detailed per-probe driver logs and the underlying API/server error files.
Zero counted corruption messages do not prove storage integrity.
The two testcase files need not share one underlying cause.
**Falsifier:** Detailed traces could identify different failing API stages despite the matching aggregate signatures.
**Next action:** Retain driver and server error logs and identify the first failed request before changing overflow handling.

## Actions and remaining gates

1. Review and integrate the collector repair and this report through the user's local merge workflow.
2. Investigate the three additional head failures with the missing result files and controlled runtime inputs.
3. Keep the three shared signatures visible as separate follow-up work. Their baseline presence does not waive CI requirements.
4. Obtain separate direction before any engine repair, source push, or further engine CI cycle.
5. Resolve actual PR7927 integration, combined acceptance, and human testcase PR disposition under Work Item 393.

The collector and report work does not complete Work Item 393.
No engine or testcase source changes, PR comments, testcase merges, or CI triggers occur during this analysis.
The unrelated `cubrid-cci/win/cci_version.h` change remains intact.

## Evidence inventory and reproduction

Head evidence root:

```text
/home/vimkim/.local/share/cubrid-ci-data/github-actions/CUBRID-cubrid/pr-7925/6a487cdb6cbda36ac94ad9b22009cea6cb58aa2f
```

Baseline evidence root:

```text
/home/vimkim/.local/share/cubrid-ci-data/github-actions/CUBRID-cubrid/commits/fb567a629cdb390fff920542173fa36f454c74a0
```

Each root contains its matching `observations/<observation-id>/request.json` and `result.json`.
Suite summaries reside under `providers/github-actions/runs/<run>/attempts/1/<suite>/summary.json`.
Each summary names its failure metadata, message, optional extracted difference, and raw shard files.
The raw index binds the summary digest and every retained raw file digest.
Five head extracted difference files contain NOK markers without substantive output differences.
Their extraction status alone does not establish an expected-versus-actual comparison.
The lock testcase's difference file contains its actual sorted comparison.

External receipts:

```text
/mnt/nvme/data-5/tmp/pr7925-collector-20261017.8xAfQE
  status.json, doctor.json, head-result.json, base-result.json
  head-validation.json, base-validation.json, validate-collection.py
  comparison.json, comparison-coverage.json, testcase-equality.json
  original-manifest.json, original-evidence-sha256.json, preservation-validation.json
  assessment.json, report-mode.json, ctp-comparison.json, lock-polling.json
  producer-gha-ci.yml, testcase-source/, verify.log, install.log
```

These receipts and raw logs remain outside repository commits.
The earlier warning identifies the original observation and its independent API receipts.
The commands below describe the completed retrieval. A new invocation creates another collection observation.

```sh
cubrid-ci status https://github.com/CUBRID/cubrid/pull/7925 --json
cubrid-ci collect https://github.com/CUBRID/cubrid/pull/7925 \
  --commit 6a487cdb6cbda36ac94ad9b22009cea6cb58aa2f --json
cubrid-ci collect-base https://github.com/CUBRID/cubrid/pull/7925 --json
```

Exact testcase source uses `git show <recorded-tc-sha>:<full-testcase-path>` in the local testcase repository.
The validator script requires `/usr/bin/python3`, which provides the installed `jsonschema` module.
