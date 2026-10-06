# PR #7925: attribution of the triggered CI failures

Analysis date: 2026-10-07 KST. PR: [#7925 — Support OOS in standalone workspace writes](https://github.com/CUBRID/cubrid/pull/7925).

## Assessment

**The two CDC failures were already observed at the exact merge base. The space-accounting failure is a plausible PR-related candidate whose cause is not established.** The available evidence does not justify saying that every failure is unrelated to this PR, or that the PR has introduced an engine correctness defect.

The triggered regression run tested **`f037616cd17af92e1226afcde80fd2a6fff9121d`**, not the current local checkout `a142503dc1a6f85b498a425aa58d6a78136ccc6b`. Both commits have the identical `src/` tree, `0ca5248c8e1567c385847e941d150bc318e0fd5f`. The intervening changes removed four internal Markdown files and corrected a unit-test collection oracle and benchmark license header. This permits discussing the same production code; it does not establish regression-CI success for the newer commit. The [review guide](code_review_guide_a142503dc_codex.md) covers the local checkout.

The published PR was at `91bfde02e5699a2aaa0c5d549d7ef4d418c8bdb8` in the status snapshot. Its own regression-suite collection is `not_observed` for all three suites and has a separate [bounded warning report](ci_analysis_report_91bfde02e_codex.md). This document analyzes the independently validated historical run, rather than promoting its verdict to a newer head.

## Run identity and results

The tested run is [37463915181, attempt 1](https://github.com/CUBRID/cubrid/actions/runs/37463915181). The exact merge-base run is [36570256001, attempt 1](https://github.com/CUBRID/cubrid/actions/runs/36570256001). Every collected shard consumed a debug build with its bundle's exact Engine SHA; workflow revisions are separate identities.

| Suite | Tested PR commit: verdict | Planned | Run | Passed | Failed | Errors | Skipped | Unrun |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `test_medium` | Pass | 975 | 975 | 975 | 0 | 0 | 0 | 0 |
| `test_sql` | Pass | 17,471 | 17,471 | 17,471 | 0 | 0 | 0 | 0 |
| `test_shell` | Fail | 3,289 | 3,259 | 3,256 | 3 | 0 | 30 | 0 |

| Suite | Exact merge base: verdict | Planned | Run | Passed | Failed | Errors | Skipped | Unrun |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `test_medium` | Pass | 975 | 975 | 975 | 0 | 0 | 0 | 0 |
| `test_sql` | Pass | 17,471 | 17,471 | 17,471 | 0 | 0 | 0 | 0 |
| `test_shell` | Fail | 3,289 | 3,259 | 3,254 | 5 | 0 | 30 | 0 |

The shell count is three failed **testcases**. Two failed assertions within `cbrd_27064` still count as one failed testcase. Thirty skips are recorded outcomes, not successful executions.

## Complete failure inventory

All paths below are relative to `CUBRID/cubrid-testcases-private-ex` at `c4b9d482fbd491a68510b2552df2c3cac91911fc`.

| Failed testcase | Observed signature on tested PR commit | Exact-base comparison | Category | Relation to PR changes | Confidence |
| --- | --- | --- | --- | --- | --- |
| [`shell/_06_issues/_16_2h/cbrd_20683/cases/cbrd_20683.sh`](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/c4b9d482fbd491a68510b2552df2c3cac91911fc/shell/_06_issues/_16_2h/cbrd_20683/cases/cbrd_20683.sh) | Startup passes; `spacedb` comparison fails. Primary volume uses 18.8 M versus expected 18.5 M; permanent-data total uses 20.5 M versus 20.2 M. Volume names and counts are unchanged in the recorded diff. | `uncomparable` for causal attribution: exact testcase passes on base, but the harness differs and its relevant helper/configuration equivalence is unproven. An observed head-only failure candidate. | Storage-footprint answer mismatch after `createdb` | **Plausible**: SA bootstrap writes can reach the workspace force path. No allocation provenance proves it. | High for observed mismatch and base pass; low for precise cause |
| [`shell/_37_elderberry/cbrd_23842_cdc/bug/cbrd_27064/cases/cbrd_27064.sh`](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/c4b9d482fbd491a68510b2552df2c3cac91911fc/shell/_37_elderberry/cbrd_23842_cdc/bug/cbrd_27064/cases/cbrd_27064.sh) | INSERT passes. DELETE extraction returns `rc=-10` at 10/700; UPDATE returns `rc=-10` at 4/2,400. Both report zero log-page corruption. | `also_observed_on_base`: INSERT passes there too; DELETE fails at 23/700 and UPDATE at 0/2,400 with `rc=-10`, zero corruption. Same assertion and error family; extracted row counts vary. | CDC historical-value extraction | **Unlikely** to have been introduced by this PR. Consistent with the pre-existing OOS history limitation. | High for pre-existence; medium for history-lifetime cause in this particular run |
| [`shell/_37_elderberry/cbrd_23842_cdc/bug/cbrd_27075/cases/cbrd_27075.sh`](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/c4b9d482fbd491a68510b2552df2c3cac91911fc/shell/_37_elderberry/cbrd_23842_cdc/bug/cbrd_27075/cases/cbrd_27075.sh) | All page sizes reach `FINAL_SEQ=2000`. The 4K configuration has `EXTRACT_ERR=1`; 8K/16K have zero. `CONFIGS_OK=2/3`, total corruption zero. | `also_observed_on_base`: all workloads finish, but all three sizes have `EXTRACT_ERR=4`, `CONFIGS_OK=0/3`, zero corruption. The common 4K extraction-error signature exists on both sides. | CDC historical-value extraction | **Unlikely** to have been introduced by this PR. Fewer errors in one run do not prove a repair. | High for pre-existence; medium for precise cause |

Failure messages, including the actual numeric output diff, are cited in [the retained excerpts](ci_f037616cd/failure_excerpts.md). The collector's `diff.txt` for the CDC cases contains NOK markers; their substantive error signatures come from `message.txt`, not from treating that short diff as a complete diagnostic.

Reconciliation of the three PR failures: **two shared signatures, zero established comparable additional failures, one uncomparable head-only candidate**. There are three baseline-only failures, reported separately below. The formal classification does not hide the fact that `cbrd_20683` passed on the exact base and failed on the tested PR commit.

## Analysis: `cbrd_20683`

**Observed.** The testcase creates a fresh 4K-page database with ten prescribed volumes, starts its server, and compares the complete `spacedb` report with a static answer. It does not run an application `loaddb` workload. The CI trace records the native command `cubrid createdb --db-page-size=4K -r --more-volume-file=volume_1.info db20683 en_US`. The failing differences are used/free-space values; the startup check, volume names, volume counts, and total capacities do not fail. The original [CBRD-20683](http://jira.cubrid.org/browse/CBRD-20683) defect concerns volume names, so the current numeric mismatch is not evidence that its original pathname defect has returned.

**PR connection.** Database creation has an SA client bootstrap: [`db_init`](https://github.com/CUBRID/cubrid/blob/f037616cd17af92e1226afcde80fd2a6fff9121d/src/compat/db_admin.c#L278) calls [`boot_initialize_client`](https://github.com/CUBRID/cubrid/blob/f037616cd17af92e1226afcde80fd2a6fff9121d/src/transaction/boot_cl.c#L954), which initializes workspace, installs system metadata and commits. [`install_system_metadata`](https://github.com/CUBRID/cubrid/blob/f037616cd17af92e1226afcde80fd2a6fff9121d/src/transaction/boot_cl.c#L215) installs authorization, catalog, and information-schema objects. Catalog installation contains [`db_create_internal` instance construction](https://github.com/CUBRID/cubrid/blob/f037616cd17af92e1226afcde80fd2a6fff9121d/src/object/schema_system_catalog_install.cpp#L202). The PR adds the workspace marker at [`xlocator_force`](https://github.com/CUBRID/cubrid/blob/f037616cd17af92e1226afcde80fd2a6fff9121d/src/transaction/locator_sr.c#L7398) and demotes marked SA records before heap/index force. [`heap_oos_demote_workspace_record`](https://github.com/CUBRID/cubrid/blob/f037616cd17af92e1226afcde80fd2a6fff9121d/src/storage/heap_oos.cpp#L1337) skips root-class records; that guard alone does not exclude instances of every system table.

**Inference.** If bootstrap creates an eligible non-root workspace record, the new demotion could change heap/OOS file allocation and therefore `spacedb`'s used-size output. That would be a real behavior change relevant to the PR, even if the stored logical data and volume paths remain correct. A legitimate allocation change and an engine allocation defect require different follow-up actions. The rounded space totals cannot identify the allocating file or distinguish those possibilities.

**Unknowns.** The retained CI text does not inventory OOS files or record which bootstrap row, if any, was demoted. Base-pass JUnit does not retain the base's detailed `spacedb` output. CTP changed from `4d0043a7b149b3fc5d3ccb2e08c98cf8d77b34fb` to `44e3f97c788ad82091d5b66d728852f3279b1e86`; neither exact source object is available in the local CTP checkout. No same-harness A/B experiment was run. The baseline comparison is therefore bounded, rather than a proved engine regression.

**Falsifier.** Reproduce the head-only used-size signature on the base under the same CTP helper/configuration, or show that no eligible bootstrap record takes the added demotion path and that the allocation difference comes from an unchanged subsystem. Either would weaken the proposed workspace connection. Conversely, a matched run where head alone demotes a bootstrap record and the additional allocations account for the space delta would establish that connection.

**Next action.** Run this one shell testcase against the pinned base and PR engine with the same testcase and CTP revisions. Capture the generated volume file, final configuration, `spacedb`, per-file allocation, and the class/record identity of every workspace demotion during `createdb`. Only after explaining the allocation difference should the team decide whether to change the implementation, narrow the expected output to the original volume-path contract, or intentionally update the numeric answer. Do not update the answer merely to make this run pass.

## Analysis: the two CDC cases

**Observed.** Both tests use ordinary client/server `csql`, large variable payloads, and the CDC API. They fail at the exact base as well as the PR commit. Neither current message records log-page corruption. `cbrd_27064` loses DELETE/UPDATE extraction after successful INSERT coverage; `cbrd_27075` completes its SQL workload but records an extraction error. These observations establish failed extraction, not a crash in this run.

**PR connection.** The newly added workspace demotion helper executes its body only in SA mode. These tests drive SERVER-mode SQL writes, so they do not directly exercise that added behavior. The PR also extracts the shared layout planner used by normal SQL writers, so the mode distinction alone would be insufficient to clear every production change. The decisive evidence for non-introduction is that both error families already occur on the exact merge base with the same testcase commit.

**Inference.** The failures are consistent with the OOS historical-value lifetime limitation tracked by [CBRD-26939](http://jira.cubrid.org/browse/CBRD-26939): CDC may read a log image whose OOS value chain has already been reclaimed. The [normative OOS context](/home/vimkim/gh/cubrid-oos-context/OOS-CONTEXT.md) explicitly leaves the two CDC cases enabled and failing while durable OOS history remains deferred from the 11.5 merge. That design status supports the hypothesis; it does not independently prove the exact error site of these new observations. The current format uses 24-byte stubs; the older issue report's historical 16-byte description must not be copied as the current layout.

**Unknowns.** Binary/core archives were not requested, and the messages do not provide a server-side stack or the failing chain identity. The varying error counts may reflect scheduling, vacuum progress, or harness differences. Pre-existence does not prove identical root causes, harmlessness, or improvement from the PR.

**Falsifier.** A trace showing intact and readable historical OOS payloads while the CDC error arises solely from another protocol, connection, or extraction path would falsify the history-lifetime attribution. A controlled base-pass/head-fail run with the same inputs and a new failing path in the extracted planner would challenge the current PR relation.

**Next action.** Keep these as the separate CBRD-26939 history work. For precise root cause, preserve server-side CDC return diagnostics, the OOS reference and vacuum timeline for the focused DELETE/UPDATE extraction. Do not relax expected counts or silently exclude them from CI. Their pre-existing signatures do not waive project CI requirements.

## Baseline comparison and limits

`collect-base` resolved the PR's published head `91bfde02e...` against `feature/oos-merge` tip `fb567a629...`, observing the relationship at `2026-10-06T17:18:17.894653842Z`. Its exact merge base is `fb567a629cdb390fff920542173fa36f454c74a0`. Local Git independently returns that same merge base for tested `f037616cd...` and for the current local guide head. The historical comparison is therefore against the actual shared ancestor, not an arbitrary target tip.

Discovery covered all paginated exact-commit statuses and check runs, without a repository-wide workflow scan. The CLI selected run 37463915181/1 for the PR engine and 36570256001/1 for the base engine. Collection completed independently for both. Build receipts identify the Engine commits even though their issue-comment workflows ran from different develop revisions.

| Input | Tested PR run | Exact-base run | Comparison implication |
| --- | --- | --- | --- |
| Engine | `f037616cd17af92e1226afcde80fd2a6fff9121d` | `fb567a629cdb390fff920542173fa36f454c74a0` | Intended engine comparison |
| Public testcase commit | `bdba62aee0faec05abdd861518824c69b6c1b3c5` | Same | Identical repository revision for medium/SQL inputs |
| Private testcase commit | `c4b9d482fbd491a68510b2552df2c3cac91911fc` | Same | Identical testcase scripts, answers, and repository fixtures |
| Testcase branches | `tc/pr-7925` | `tc/pr-7990` | Branch labels differ; object identities match |
| Build mode consumed by shards | Debug | Debug | Matches |
| Workflow revision | `a9f07558634bd84250452149029e85d5fb170e37` | `f1bd99ed43a134383bc0be1d766a6f121601a499` | Workflow source is not the tested Engine identity |
| CTP commit | `44e3f97c788ad82091d5b66d728852f3279b1e86` | `4d0043a7b149b3fc5d3ccb2e08c98cf8d77b34fb` | Relevant helper/configuration equality unproven |
| Shell plan | 3,289 planned; 50 shards; 30 skips | Same totals | Case placement and runner timing differ |

Same testcase repository revisions prove matching affected Git objects; they do not prove matching CTP helpers or runtime configuration. For example, `cbrd_20683` moved from base shard 33 to PR shard 04. This is not a controlled runtime experiment.

Three failures are **baseline-only observations** and pass in the PR run:

| Full testcase path | Base | Tested PR commit |
| --- | --- | --- |
| `shell/_06_issues/_17_1h/cbrd_20759/hide_cubrid_replay/cases/hide_cubrid_replay.sh` | Failure | Passed |
| `shell/_06_issues/_15_1h/bug_bts_15156/cases/bug_bts_15156.sh` | Failure | Passed |
| `shell/_40_guava/cbrd_26349/cases/cbrd_26349.sh` | Failure | Passed |

Their passing observations do not mean this PR fixed those unrelated mechanisms. Prior analysis of the base run is [available separately](../cbrd-26357/ci_analysis_report_fb567a6_codex.md).

## Evidence integrity and review boundary

Collector: `cubrid-ci 0.2.0 (16d7252122d1, release)`. Its schema checkout is the matching source commit `16d7252122d185dc8866c99598644dd974044bd2`.

- Tested-commit collection time: `2026-10-06T17:18:42.074549889Z`; complete observation.
- Base collection time: `2026-10-06T17:19:16.809657238Z`; complete observation.
- All three requested summaries appear once in each complete bundle. Command/manifest identities, unique terminal observations, requests, run/attempt identities, per-shard Engine SHAs, suite schemas, failure metadata, and declared message/diff files reconcile.
- **780 indexed raw files per bundle** passed path containment, byte-length, and SHA-256 checks. Suite summary digests match the raw indexes. Acquisition marks all requested completed shards retained. Count equations and all 3,289 shell JUnit outcomes reconcile on each side.
- The report-mode gate returns `full` for the historical tested commit, with comparison restricted to validated cases. It returns `warning` for the published head's unobserved suites.
- No binaries were requested; consumed binary budget is zero. Text collection completeness does not establish that no core files exist.

Durable bundle roots:

```text
/home/vimkim/.local/share/cubrid-ci-data/github-actions/CUBRID-cubrid/commits/f037616cd17af92e1226afcde80fd2a6fff9121d
/home/vimkim/.local/share/cubrid-ci-data/github-actions/CUBRID-cubrid/commits/fb567a629cdb390fff920542173fa36f454c74a0
```

The [validation receipt](ci_f037616cd/validation.json) records exact observation paths, summary/message digests, every failure, opposite-side JUnit coverage, count reconciliation, and known input differences. The [failure excerpts](ci_f037616cd/failure_excerpts.md) retain the human-readable signatures. Raw evidence remains in collector-owned directories rather than being duplicated into the documentation repository.

The highest-priority PR-specific follow-up is the matched `cbrd_20683` allocation experiment. This analysis made no engine/testcase changes, repairs, reruns, CI triggers, or remote publication. The locally completed 37/37 CTest result at `a142503dc` is a separate verification result and does not replace the three external regression suites.
