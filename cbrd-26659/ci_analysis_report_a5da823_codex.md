# CBRD-26659 / PR 8128: expected failures and CI runtime gap

Created: 2026-10-12 (Asia/Seoul). Engine revision: `a5da823b2a84e95b4b22d48abe4a3f9fd601c176`. Collector: `cubrid-ci 0.2.0 (16d7252122d1, release)`.

Some red results were anticipated because the published corpus deliberately retains five failing or unfinished reproducers. All 18 added shell entrypoints failing was outside the successful local qualification. Nine explicitly report `python3 unavailable`; seven Python controller wrappers exit 127; two crash wrappers fail at their Python schedule invocation. They complete in roughly 1–2 seconds. The user subsequently selected conversion to repository shell conventions. That current action supersedes the earlier Python-provisioning recommendation; replacement evidence is in the [conversion record](/home/vimkim/gh/my-cubrid-docs/cbrd-26659/ci-replan/shell-conversion-results-20261012.md).

The current shell run does not establish the OOS behavior checks inside those 18 cases. The local 14-case OptDebug pass remains valid historical evidence for its recorded native runner and environment. It does not qualify the CTP/debug CI environment used here. The missed integration prerequisite is Python availability on the CI testcase command path.

The coordinating [engine draft PR 8128](https://github.com/CUBRID/cubrid/pull/8128) has an empty commit and the same Git tree as its merge base. Engine and testcase fixes, runtime-image changes, reproduction, pushes and CI triggers are follow-up actions; this analysis has performed evidence collection and source reads only.

## Snapshot and evidence validation

[Head run 38043651879, attempt 1](https://github.com/CUBRID/cubrid/actions/runs/38043651879) finished **failure**. Both release and debug builds passed. Regression suites used debug builds. The status snapshot was fetched on 2026-10-12; exact-head collection is `2026-10-12T05:22:38.284178690Z`. All three requested suites are complete in the independently validated manifest and matching observation.

| Suite | Planned | Passed | Failed | Errors | Skipped | Never run | Verdict |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| SQL | 17488 | 17487 | 1 | 0 | 0 | 0 | fail |
| Shell | 3307 | 3256 | 21 | 0 | 30 | 0 | fail |
| Medium | 975 | 975 | 0 | 0 | 0 | 0 | pass |

All 61 shard identities match the tested engine commit. SQL/medium used public TC `1a556a0752073aaad573bf87d53f3eb75f398138`; shell used private TC `27db3d6b6d966056de474af277ee40735190f00c`. Both are the published `tc/pr-8128` payloads. Zero never-run cases means the collector reconciled dispatched testcase entries; it does not mean each entry reached its behavior assertions.

The paired head/base checks validated 47 schema documents, 1560 raw-file lengths and SHA-256 digests, and 27 failure metadata/message records (22 head, 5 base). No binaries or cores were requested. The report gate returned `mode=full`, with comparison restricted to validated cases. Doctor was healthy; one status, one exact-head collection and one exact merge-base collection were run without waiting for another CI execution.

Head bundle: [/home/vimkim/.local/share/cubrid-ci-data/github-actions/CUBRID-cubrid/pr-8128/a5da823b2a84e95b4b22d48abe4a3f9fd601c176](/home/vimkim/.local/share/cubrid-ci-data/github-actions/CUBRID-cubrid/pr-8128/a5da823b2a84e95b4b22d48abe4a3f9fd601c176/manifest.json). Matching head observation: `20261012T052227.392221019Z-2155925-0`. Validation receipt: [/home/vimkim/tmp/oos-ci-analysis-8128-20261012/validation.json](/home/vimkim/tmp/oos-ci-analysis-8128-20261012/validation.json). Report-mode assessment: [/home/vimkim/tmp/oos-ci-analysis-8128-20261012/assessment.json](/home/vimkim/tmp/oos-ci-analysis-8128-20261012/assessment.json).

Observed CI suite spans were SQL 521 seconds (8.7 minutes), shell 1962 seconds (32.7 minutes), medium 187 seconds (3.1 minutes). These are full-corpus CI spans across multiple shards, separate from the earlier serial local timings.

## Complete head failure inventory

The nine explicit prerequisite failures, seven status-127 wrappers, two crash wrappers, one SQL failure and three existing shell case failures account for all 22 head records. Medium has no failures. The category for the added shell cases is runtime prerequisite/controller launch. The SQL category is a known-failing partition reproducer. Existing case categories are CDC checks and replay output mismatch. The links below point to the validated local evidence rather than mutable testcase branch URLs.

| Suite | Full testcase path | Result | Observed signature | Baseline classification | PR relation | Confidence | Evidence |
| --- | --- | --- | --- | --- | --- | --- | --- |
| test_shell | `shell/_40_guava/cbrd_26659_utility_cs/cases/cbrd_26659_utility_cs.sh` | failure | controller status 127 | uncomparable: absent from base corpus | direct: new runtime dependency | medium-high | [message](/home/vimkim/.local/share/cubrid-ci-data/github-actions/CUBRID-cubrid/pr-8128/a5da823b2a84e95b4b22d48abe4a3f9fd601c176/providers/github-actions/runs/38043651879/attempts/1/test_shell/failures/shell_40_guava_cbrd_26659_utility_cs_cases_cbrd_26659_utility_cs_sh-4586172d80/message.txt) |
| test_shell | `shell/_40_guava/cbrd_26659_utility_sa_physical/cases/cbrd_26659_utility_sa_physical.sh` | failure | controller status 127 | uncomparable: absent from base corpus | direct: new runtime dependency | medium-high | [message](/home/vimkim/.local/share/cubrid-ci-data/github-actions/CUBRID-cubrid/pr-8128/a5da823b2a84e95b4b22d48abe4a3f9fd601c176/providers/github-actions/runs/38043651879/attempts/1/test_shell/failures/shell_40_guava_cbrd_26659_utility_sa_physical_cases_cbrd_26659_utility_sa_physic-ae6f63879c/message.txt) |
| test_shell | `shell/_40_guava/cbrd_26659_utility_sa/cases/cbrd_26659_utility_sa.sh` | failure | controller status 127 | uncomparable: absent from base corpus | direct: new runtime dependency | medium-high | [message](/home/vimkim/.local/share/cubrid-ci-data/github-actions/CUBRID-cubrid/pr-8128/a5da823b2a84e95b4b22d48abe4a3f9fd601c176/providers/github-actions/runs/38043651879/attempts/1/test_shell/failures/shell_40_guava_cbrd_26659_utility_sa_cases_cbrd_26659_utility_sa_sh-00f7b76bc4/message.txt) |
| test_shell | `shell/_40_guava/cbrd_27237_rollback_vacuum/cases/cbrd_27237_rollback_vacuum.sh` | failure | controller status 127 | uncomparable: absent from base corpus | direct: new runtime dependency | medium-high | [message](/home/vimkim/.local/share/cubrid-ci-data/github-actions/CUBRID-cubrid/pr-8128/a5da823b2a84e95b4b22d48abe4a3f9fd601c176/providers/github-actions/runs/38043651879/attempts/1/test_shell/failures/shell_40_guava_cbrd_27237_rollback_vacuum_cases_cbrd_27237_rollback_vacuum_sh-50405a0016/message.txt) |
| test_shell | `shell/_40_guava/cbrd_26659_snapshot_visibility/cases/cbrd_26659_snapshot_visibility.sh` | failure | controller status 127 | uncomparable: absent from base corpus | direct: new runtime dependency | medium-high | [message](/home/vimkim/.local/share/cubrid-ci-data/github-actions/CUBRID-cubrid/pr-8128/a5da823b2a84e95b4b22d48abe4a3f9fd601c176/providers/github-actions/runs/38043651879/attempts/1/test_shell/failures/shell_40_guava_cbrd_26659_snapshot_visibility_cases_cbrd_26659_snapshot_visibili-341f37e007/message.txt) |
| test_shell | `shell/_40_guava/cbrd_26659_representation_chunks/cases/cbrd_26659_representation_chunks.sh` | failure | python3 unavailable | uncomparable: absent from base corpus | direct: new runtime dependency | high | [message](/home/vimkim/.local/share/cubrid-ci-data/github-actions/CUBRID-cubrid/pr-8128/a5da823b2a84e95b4b22d48abe4a3f9fd601c176/providers/github-actions/runs/38043651879/attempts/1/test_shell/failures/shell_40_guava_cbrd_26659_representation_chunks_cases_cbrd_26659_representation_-7c07ddd5ba/message.txt) |
| test_shell | `shell/_40_guava/cbrd_26659_backup_restore/cases/cbrd_26659_backup_restore.sh` | failure | controller status 127 | uncomparable: absent from base corpus | direct: new runtime dependency | medium-high | [message](/home/vimkim/.local/share/cubrid-ci-data/github-actions/CUBRID-cubrid/pr-8128/a5da823b2a84e95b4b22d48abe4a3f9fd601c176/providers/github-actions/runs/38043651879/attempts/1/test_shell/failures/shell_40_guava_cbrd_26659_backup_restore_cases_cbrd_26659_backup_restore_sh-f1b80bdffa/message.txt) |
| test_shell | `shell/_40_guava/cbrd_26659_partition_owner/cases/cbrd_26659_partition_owner.sh` | failure | python3 unavailable | uncomparable: absent from base corpus | direct: new runtime dependency | high | [message](/home/vimkim/.local/share/cubrid-ci-data/github-actions/CUBRID-cubrid/pr-8128/a5da823b2a84e95b4b22d48abe4a3f9fd601c176/providers/github-actions/runs/38043651879/attempts/1/test_shell/failures/shell_40_guava_cbrd_26659_partition_owner_cases_cbrd_26659_partition_owner_sh-f4eb1b3422/message.txt) |
| test_shell | `shell/_40_guava/cbrd_26659_lob_locators/cases/cbrd_26659_lob_locators.sh` | failure | python3 unavailable | uncomparable: absent from base corpus | direct: new runtime dependency | high | [message](/home/vimkim/.local/share/cubrid-ci-data/github-actions/CUBRID-cubrid/pr-8128/a5da823b2a84e95b4b22d48abe4a3f9fd601c176/providers/github-actions/runs/38043651879/attempts/1/test_shell/failures/shell_40_guava_cbrd_26659_lob_locators_cases_cbrd_26659_lob_locators_sh-b2889a8352/message.txt) |
| test_shell | `shell/_06_issues/_17_1h/cbrd_20759/hide_cubrid_replay/cases/hide_cubrid_replay.sh` | failure | subcheck 8 / qa10.answer mismatch; base failed subcheck 7 / qa9.answer | uncomparable: different signature | unlikely: case inputs unchanged | high for differing signature; cause unknown | [message](/home/vimkim/.local/share/cubrid-ci-data/github-actions/CUBRID-cubrid/pr-8128/a5da823b2a84e95b4b22d48abe4a3f9fd601c176/providers/github-actions/runs/38043651879/attempts/1/test_shell/failures/shell_06_issues_17_1h_cbrd_20759_hide_cubrid_replay_cases_hide_cubrid_replay_sh-28fe0a99ca/message.txt) |
| test_shell | `shell/_40_guava/cbrd_26659_crash_undo/cases/cbrd_26659_crash_undo.sh` | failure | crash controller failed | uncomparable: absent from base corpus | direct: new runtime dependency | medium-high | [message](/home/vimkim/.local/share/cubrid-ci-data/github-actions/CUBRID-cubrid/pr-8128/a5da823b2a84e95b4b22d48abe4a3f9fd601c176/providers/github-actions/runs/38043651879/attempts/1/test_shell/failures/shell_40_guava_cbrd_26659_crash_undo_cases_cbrd_26659_crash_undo_sh-84f54e2cb8/message.txt) |
| test_shell | `shell/_37_elderberry/cbrd_23842_cdc/bug/cbrd_27064/cases/cbrd_27064.sh` | failure | subchecks 2 and 3 NOK | also_observed_on_base | unlikely: unchanged CDC case | high for matching failure excerpt; cause unknown | [message](/home/vimkim/.local/share/cubrid-ci-data/github-actions/CUBRID-cubrid/pr-8128/a5da823b2a84e95b4b22d48abe4a3f9fd601c176/providers/github-actions/runs/38043651879/attempts/1/test_shell/failures/shell_37_elderberry_cbrd_23842_cdc_bug_cbrd_27064_cases_cbrd_27064_sh-1e79382118/message.txt) |
| test_shell | `shell/_40_guava/cbrd_26659_schema_policy/cases/cbrd_26659_schema_policy.sh` | failure | python3 unavailable | uncomparable: absent from base corpus | direct: new runtime dependency | high | [message](/home/vimkim/.local/share/cubrid-ci-data/github-actions/CUBRID-cubrid/pr-8128/a5da823b2a84e95b4b22d48abe4a3f9fd601c176/providers/github-actions/runs/38043651879/attempts/1/test_shell/failures/shell_40_guava_cbrd_26659_schema_policy_cases_cbrd_26659_schema_policy_sh-c9b0851678/message.txt) |
| test_shell | `shell/_40_guava/cbrd_26659_snapshots_reclaim/cases/cbrd_26659_snapshots_reclaim.sh` | failure | controller status 127 | uncomparable: absent from base corpus | direct: new runtime dependency | medium-high | [message](/home/vimkim/.local/share/cubrid-ci-data/github-actions/CUBRID-cubrid/pr-8128/a5da823b2a84e95b4b22d48abe4a3f9fd601c176/providers/github-actions/runs/38043651879/attempts/1/test_shell/failures/shell_40_guava_cbrd_26659_snapshots_reclaim_cases_cbrd_26659_snapshots_reclaim_s-eb029bc997/message.txt) |
| test_shell | `shell/_40_guava/cbrd_26659_read_paths/cases/cbrd_26659_read_paths.sh` | failure | python3 unavailable | uncomparable: absent from base corpus | direct: new runtime dependency | high | [message](/home/vimkim/.local/share/cubrid-ci-data/github-actions/CUBRID-cubrid/pr-8128/a5da823b2a84e95b4b22d48abe4a3f9fd601c176/providers/github-actions/runs/38043651879/attempts/1/test_shell/failures/shell_40_guava_cbrd_26659_read_paths_cases_cbrd_26659_read_paths_sh-2f7b743f3b/message.txt) |
| test_shell | `shell/_40_guava/cbrd_26659_transactions/cases/cbrd_26659_transactions.sh` | failure | python3 unavailable | uncomparable: absent from base corpus | direct: new runtime dependency | high | [message](/home/vimkim/.local/share/cubrid-ci-data/github-actions/CUBRID-cubrid/pr-8128/a5da823b2a84e95b4b22d48abe4a3f9fd601c176/providers/github-actions/runs/38043651879/attempts/1/test_shell/failures/shell_40_guava_cbrd_26659_transactions_cases_cbrd_26659_transactions_sh-130febe7cc/message.txt) |
| test_shell | `shell/_40_guava/cbrd_26659_crash_committed/cases/cbrd_26659_crash_committed.sh` | failure | crash controller failed | uncomparable: absent from base corpus | direct: new runtime dependency | medium-high | [message](/home/vimkim/.local/share/cubrid-ci-data/github-actions/CUBRID-cubrid/pr-8128/a5da823b2a84e95b4b22d48abe4a3f9fd601c176/providers/github-actions/runs/38043651879/attempts/1/test_shell/failures/shell_40_guava_cbrd_26659_crash_committed_cases_cbrd_26659_crash_committed_sh-b6d2b3af8a/message.txt) |
| test_shell | `shell/_40_guava/cbrd_26659_owner_drop/cases/cbrd_26659_owner_drop.sh` | failure | python3 unavailable | uncomparable: absent from base corpus | direct: new runtime dependency | high | [message](/home/vimkim/.local/share/cubrid-ci-data/github-actions/CUBRID-cubrid/pr-8128/a5da823b2a84e95b4b22d48abe4a3f9fd601c176/providers/github-actions/runs/38043651879/attempts/1/test_shell/failures/shell_40_guava_cbrd_26659_owner_drop_cases_cbrd_26659_owner_drop_sh-babcab9a78/message.txt) |
| test_shell | `shell/_37_elderberry/cbrd_23842_cdc/bug/cbrd_27075/cases/cbrd_27075.sh` | failure | subcheck 1 NOK | also_observed_on_base | unlikely: unchanged CDC case | high for matching failure excerpt; cause unknown | [message](/home/vimkim/.local/share/cubrid-ci-data/github-actions/CUBRID-cubrid/pr-8128/a5da823b2a84e95b4b22d48abe4a3f9fd601c176/providers/github-actions/runs/38043651879/attempts/1/test_shell/failures/shell_37_elderberry_cbrd_23842_cdc_bug_cbrd_27075_cases_cbrd_27075_sh-f42063033e/message.txt) |
| test_shell | `shell/_40_guava/cbrd_26659_dml_transitions/cases/cbrd_26659_dml_transitions.sh` | failure | python3 unavailable | uncomparable: absent from base corpus | direct: new runtime dependency | high | [message](/home/vimkim/.local/share/cubrid-ci-data/github-actions/CUBRID-cubrid/pr-8128/a5da823b2a84e95b4b22d48abe4a3f9fd601c176/providers/github-actions/runs/38043651879/attempts/1/test_shell/failures/shell_40_guava_cbrd_26659_dml_transitions_cases_cbrd_26659_dml_transitions_sh-3b8c4d2f46/message.txt) |
| test_shell | `shell/_40_guava/cbrd_26659_tde_wal/cases/cbrd_26659_tde_wal.sh` | failure | python3 unavailable | uncomparable: absent from base corpus | direct: new runtime dependency | high | [message](/home/vimkim/.local/share/cubrid-ci-data/github-actions/CUBRID-cubrid/pr-8128/a5da823b2a84e95b4b22d48abe4a3f9fd601c176/providers/github-actions/runs/38043651879/attempts/1/test_shell/failures/shell_40_guava_cbrd_26659_tde_wal_cases_cbrd_26659_tde_wal_sh-d13b3320e1/message.txt) |
| test_sql | `sql/_36_guava/cbrd_26659/cases/cbrd_26659_oos_partition.sql` | failure | partition move: expected success becomes Error:-21019; later result mismatches | uncomparable: absent from base corpus | direct: new known-failing reproducer | high for observation; cause unassigned | [message](/home/vimkim/.local/share/cubrid-ci-data/github-actions/CUBRID-cubrid/pr-8128/a5da823b2a84e95b4b22d48abe4a3f9fd601c176/providers/github-actions/runs/38043651879/attempts/1/test_sql/failures/sql_36_guava_cbrd_26659_cases_cbrd_26659_oos_partition_sql-84f61d9df8/message.txt) |

The historical CI counts and comparisons below remain tied to run38043651879 and the published Python-based TC head. The [2026-10-12 conversion record](/home/vimkim/gh/my-cubrid-docs/cbrd-26659/ci-replan/shell-conversion-results-20261012.md) owns replacement revisions, new native evidence and current limitations; earlier local receipts do not automatically qualify rewritten helpers.

## Failure groups and interpretation

### Added shell runtime prerequisites: 18 cases

**Observed:** nine cases fail `command -v python3` and emit `python3 unavailable`. Seven wrappers execute Python controllers and record exit 127. Two crash wrappers invoke `timeout ... python3 .../oos_crash.py` and emit their schedule-failure message. The exact committed shell sources were read with `git show 27db3d6...:<path>`; the full Python-invocation inventory is [/home/vimkim/tmp/oos-ci-analysis-8128-20261012/added-shell-inventory.json](/home/vimkim/tmp/oos-ci-analysis-8128-20261012/added-shell-inventory.json).

**Inference:** unavailable Python on the testcase command path is the common immediate blocker. Confidence is high for the nine explicit checks and medium-high for the other nine wrappers. Relation to this delivery is direct: the added cases introduced the Python requirement. The controller output files are redirected and not included as separate text in the collected failure messages, so status 127 alone does not identify every wrapper's missing command conclusively.

**Unknowns:** whether Python is absent from the image or installed outside the testcase command path; the minimum compatible Python version across all helpers; whether later behavior checks will pass after the dependency is supplied. Package availability and helper compatibility were not tested by this read-only analysis. Finish also emits missing `cubrid.conf.org` warnings in some logs; their causal effect has not been established.

**Falsifier:** a controlled case launch with a verified compatible `python3` on the same command path still fails at the same launch point, or the retained controller log names a different unavailable command.

**Current next action (2026-10-12):** the user selected repository-convention shell conversion. The earlier Python-provisioning recommendation is superseded. Follow the [recent convention study](/home/vimkim/gh/my-cubrid-docs/cbrd-26659/ci-replan/shell-conventions-20261012.md) and [conversion/qualification record](/home/vimkim/gh/my-cubrid-docs/cbrd-26659/ci-replan/shell-conversion-results-20261012.md), preserving independent expectations and owned cleanup. The workflow explicitly documents Python absence; the sampled image setup installs jq. Fresh native qualification and actual CI-runtime qualification remain separate. A later CI operation needs a new explicit request.

### SQL partition reproducer: 1 case

**Observed:** the partition move `update oos08_part set id=12 where id=1` yields `Error:-21019` where the independent answer expects success. Subsequent statements preserve id 1 instead of 12 and produce additional errors. The saved [SQL shard 09 log](/home/vimkim/tmp/oos-developer-regressions-publication-20261010/CI-8128-sql-09-clean.log) records a `repl_log_insert` assertion in `replication.c:468` during this case. This case was explicitly excluded from the 16-case native passing selection in the [reviewed SQL PR body](/home/vimkim/gh/my-cubrid-docs/cbrd-26659/CBRD-26659-oos-sql-regressions-pr-body_1a556a0_codex.md).

**Inference:** a red result for this retained reproducer was anticipated. The precise assertion cause remains unassigned. Relation is direct through newly exercised coverage, with high confidence in the observed failure and no exact-baseline execution of this new case.

**Falsifier:** evidence of different tested inputs, or a controlled exact-input run contradicting the recorded move failure.

**Next action:** retain the correct success expectation and handle partition move/assertion diagnosis as separate engine-defect work. No weakened answer or incidental engine fix is justified by this analysis.

### Existing CDC failures: 2 cases

**Observed:** CBRD-27064 fails subchecks 2 and 3; CBRD-27075 fails subcheck 1 in both independently validated runs. Each head/base extracted failure excerpt has an identical SHA-256 digest. The full testcase directories (scripts, answers and fixtures) have identical Git objects between the tested TC revisions.

**Inference:** these same observed failure signatures predate the coordinating PR. Relation to the new testcase delivery is unlikely; signature confidence is high. Identical snippets do not prove an identical root cause. CTP versions differ and remain a configuration limitation.

**Falsifier:** a newly identified distinct failure signature or changed prerequisite/configuration shows the apparent match hides a different failure.

**Next action:** keep both failures visible as existing CDC follow-up work and investigate independently. Their pre-existence does not waive CI requirements.

### Existing replay case: 1 case

**Observed:** `hide_cubrid_replay` failed on both runs, but head fails subcheck 8 / `qa10.answer`, whereas base fails subcheck 7 / `qa9.answer`. The whole testcase directory is unchanged.

**Inference:** the path had a baseline failure, but this head signature is **uncomparable** with that baseline signature. Relation to newly added case files is unlikely; exact cause remains unknown. It is not counted as a shared signature or a proven regression.

**Falsifier:** sufficient controlled input/configuration evidence demonstrates a stable common cause or a reproducible new signature.

**Next action:** isolate the replay comparison and inspect the corresponding captured output independently of the Python prerequisite work.

## Exact merge-base comparison and limits

The pinned feature target and exact merge base are `fb567a629cdb390fff920542173fa36f454c74a0`; the pinned head is `a5da823b2a84e95b4b22d48abe4a3f9fd601c176`. Local `git diff --name-only <base> <head>` is empty: their complete Engine trees are equal.

[Baseline run 36570256001, attempt 1](https://github.com/CUBRID/cubrid/actions/runs/36570256001), attached to that exact Engine commit, supplied complete SQL, shell and medium evidence. The CLI searched all paginated exact-commit statuses and check links, without a repository-wide workflow scan. The merge-base relationship was observed on 2026-10-12. Baseline bundle: [/home/vimkim/.local/share/cubrid-ci-data/github-actions/CUBRID-cubrid/commits/fb567a629cdb390fff920542173fa36f454c74a0](/home/vimkim/.local/share/cubrid-ci-data/github-actions/CUBRID-cubrid/commits/fb567a629cdb390fff920542173fa36f454c74a0/manifest.json). Matching baseline observation: `20261012T052413.560267120Z-2194993-0`.

| Suite | Baseline planned | Passed | Failed | Skipped | Head change in corpus |
| --- | ---: | ---: | ---: | ---: | --- |
| SQL | 17471 | 17471 | 0 | 0 | 17 added cases |
| Shell | 3289 | 3254 | 5 | 30 | 18 added entrypoints |
| Medium | 975 | 975 | 0 | 0 | Same case count |

Baseline public TC was `bdba62aee0faec05abdd861518824c69b6c1b3c5`; private TC was `c4b9d482fbd491a68510b2552df2c3cac91911fc`. The new 19 head failures (18 shell plus partition SQL) have no exact-path baseline execution. They are uncomparable for regression attribution, even though Engine trees are equal. The replay signature adds one further uncomparable record. Thus head accounting is **22 = 2 matching baseline signatures + 20 uncomparable**, with **0 proven additional-on-head comparable failures**.

Two baseline failures are absent from the head failure inventory: `shell/_06_issues/_15_1h/bug_bts_15156/cases/bug_bts_15156.sh` and `shell/_40_guava/cbrd_26349/cases/cbrd_26349.sh`. Head JUnit records explicitly report both passed. Their full testcase directories are unchanged. They are recorded as two baseline-only observed failures; no repair attribution is made.

Both runs use debug builds, but the CTP revision changed from `4d0043a7b149b3fc5d3ccb2e08c98cf8d77b34fb` to `44e3f97c788ad82091d5b66d728852f3279b1e86`. Other image/configuration equivalence was not established. Local OptDebug/native results are a further distinct execution environment. No whole-test-repository or whole-runtime equivalence claim is made.

## Recommended sequence

1. Remove direct/transitive Python runtime dependencies from the 18 new entrypoints and 11 helpers, using researched Bash/awk/jq/FIFO conventions. This replaces the earlier provisioning proposal; retain the historical dependency failure as evidence.
2. Prove representative shell cases reach their assertions in that runtime, with their independent expected results and cleanup checks intact. A separate local CTP comparison requires the user's explicit request under the personal runner policy.
3. After that verification and a separately directed CI operation, rerun the failed cases. With unchanged tested source/testcase heads and eligible retained artifacts, `/run rerun 38043651879` is the candidate failure-only operation. Head changes require a fresh `/run all` instead; trigger preflight must reassess active runs and feature TC baselines at that time.
4. Triage actual behavior failures separately. Four shell candidates (`partition_owner`, `snapshots_reclaim`, `cbrd_27237_rollback_vacuum`, `utility_sa_physical`) and the SQL partition candidate were deliberately outside the earlier native passing selections. The replacement must allow those cases to reach their intended checks; this does not promise a green run. Their expected results remain unchanged.
5. Keep [public TC PR 3688](https://github.com/CUBRID/cubrid-testcases/pull/3688) and [private TC PR 4365](https://github.com/CUBRID/cubrid-testcases-private-ex/pull/4365) available for teammate review. Human disposition of known failing coverage and separate defect work precede a claim of full CI qualification.

## Acquisition commands and retained evidence

```sh
cubrid-ci doctor --json
cubrid-ci --version
cubrid-ci status 8128 --json
cubrid-ci collect https://github.com/CUBRID/cubrid/pull/8128 --commit a5da823b2a84e95b4b22d48abe4a3f9fd601c176 --json
cubrid-ci collect-base https://github.com/CUBRID/cubrid/pull/8128 --json
```

All commands completed successfully. Schema and identity checks, raw digests, source-object reads, count reconciliation, and the report-mode gate were checked locally. Acquisition/result JSON, inventories, comparison checks and report assessment remain outside Git in `/home/vimkim/tmp/oos-ci-analysis-8128-20261012`. Binary archives and cores were not collected; engine root causes and controller-file contents beyond the collected messages remain unknown. Engine/TC worktrees and indexes were preserved, including the user's CCI edits.
