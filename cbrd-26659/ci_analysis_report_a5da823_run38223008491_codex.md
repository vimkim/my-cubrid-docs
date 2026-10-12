# CBRD-26659 / PR8128: CI run38223008491 failure analysis

Created: 2026-10-12 (Asia/Seoul). Work item 324. Analysis only. Engine `a5da823b2a84e95b4b22d48abe4a3f9fd601c176`; [run38223008491, attempt 1](https://github.com/CUBRID/cubrid/actions/runs/38223008491).

The highest-priority testcase fix is the shared snapshot controller's location: CI prunes the sibling `cases/` directory containing it, whereas the focused native run retains that directory. Both `snapshot_visibility` and `rollback_vacuum` exit 127 before their behavior assertions. This is a high-confidence explanation of the local/CI discrepancy, with the direct controller stderr still unavailable in the collected text.

All **11 failures** are inventoried below: **8 shell + 3 SQL**. Thirteen of the 18 added shell entrypoints now pass, compared with zero in the preceding run. The four documented shell candidates remain red, but their known local causes must not be assigned wholesale to CI. Partition ownership directly reproduces its 14 NOKs; SA physical placement has a compatible phase signature; page reclaim lacks an internal CI failure message; rollback/vacuum is blocked before exercising its documented corruption scenario. The SQL partition case asserts in `repl_log_insert`; the two subsequent SQL failures are strongly consistent with an abort/reconnect cascade.

The coordinating Engine PR adds no source-tree change: its head and exact merge base have the same tree. A testcase delivery can expose an existing feature-branch defect or introduce a harness dependency without constituting an Engine-code regression. Observations, inferences and unknowns are separated throughout. No source/testcase edits, database reproductions, pushes, CI triggers/reruns, merges, TC closures or comments were performed. The historical [run38043651879 report](ci_analysis_report_a5da823_codex.md) remains byte-for-byte unchanged.

## Validated snapshot and evidence scope

Both build check contexts are successful. All regression shards consume the **debug artifact produced by run38043651879, attempt 1**, at the exact Engine SHA; the current build checks accepted reuse. This is not evidence of a fresh compilation or a changed Engine binary.

| Suite | State / verdict | Planned | Run | Passed | Failures | Errors | Skipped | Unrun | Run / attempt |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| test_medium | completed / SUCCESS | 975 | 975 | 975 | 0 | 0 | 0 | 0 | 38223008491 / 1 |
| test_shell | completed / FAILURE | 3307 | 3277 | 3269 | 8 | 0 | 30 | 0 | 38223008491 / 1 |
| test_sql | completed / FAILURE | 17488 | 17488 | 17485 | 3 | 0 | 0 | 0 | 38223008491 / 1 |

Every requested suite appears once. Shell has 50 shards, SQL 10 and medium 1; all 61 shard build/testcase identities and retained acquisition states reconcile. Counts satisfy `tests = passed + failures + errors + skipped` and `planned = run + unrun + skipped`. The terminal receipt's counts and testcase revisions agree with the independently collected bundle.

- PR: [CUBRID/cubrid#8128](https://github.com/CUBRID/cubrid/pull/8128), draft, head repository `vimkim/cubrid`, head ref `CBRD-26659-oos-testcases-handover`, target `feature/oos-merge`.
- Public SQL/medium TC: `1a556a0752073aaad573bf87d53f3eb75f398138`, branch `tc/pr-8128`.
- Private shell TC: `5f049c52c477aef8aa277e978276af4f233d20fd`, branch `tc/pr-8128`.
- Collector: `cubrid-ci 0.2.0 (16d7252122d1, release)`; doctor healthy. One status, one exact-head collection and one exact merge-base collection; both collection exits 0.
- Head collected `2026-10-12T10:29:40.629451937Z`, observation `20261012T102931.850041872Z-1175195-0`.
- Base collected `2026-10-12T10:29:34.087994814Z`, observation `20261012T102933.402345975Z-1175235-0`.
- Current and base manifests/command results, unique observation pairs, summary/failure/raw-index schemas, summary digests, raw lengths/digests, declared files, counts and identities were validated independently. The previous run's saved command supplies its historical manifest snapshot; the mutable root manifest was not substituted for it.
- Combined current/base/previous validation: **68 schema documents, 2340 raw files, 38 failure records = 11 + 5 + 22**. [Validation receipt](/home/vimkim/tmp/oos-ci-analysis-38223008491/validation.json), [assessment](/home/vimkim/tmp/oos-ci-analysis-38223008491/assessment.json). The report gate permits `full`, with comparison restricted to `validated_cases_only`.
- No binary archives or cores were requested; binary consumption is zero. Controller files redirected outside JUnit are not included in the validated text inventory. An extracted shell `diff.txt` can contain a generic NOK excerpt; it does not reveal the hidden controller diagnosis.

Auxiliary workflow source and seven targeted GitHub job logs were obtained through a separately recorded read-only `gh` fallback because the collector has no commands for those auxiliary text sources. They support execution context and sequence; they do not replace or upgrade collector verdicts. The workflow was read at run revision `fd540db0ca38704d4c30ac9d5bd6f9469e2e4636`, rather than at the tested Engine SHA. Its content matches Git blob `708cffe2162e575f7793a4ce9ecb605dac37dbf5`; [fallback receipt](/home/vimkim/tmp/oos-ci-analysis-38223008491/supplementary/receipt.json). All targeted log commands completed successfully.

## All 11 failure records

“Direct coverage” means this delivery added the case that exercises the behavior, not that this Engine PR changed the faulty code. Confidence in the observed verdict is separate from confidence in its cause.

| Suite / shard / seconds | Full testcase path | Category and observed signature | Exact merge-base classification | PR relation | Confidence | Evidence |
| --- | --- | --- | --- | --- | --- | --- |
| test_shell / 17 / 62.995 | `shell/_06_issues/_17_1h/cbrd_20759/hide_cubrid_replay/cases/hide_cubrid_replay.sh` | Replay/process output: qa9 and qa10 star lines absent; subchecks 7 and 8 NOK | also_observed_on_base (qa9); qa10 comparison limited | unlikely | high signature; low cause | [message](/home/vimkim/.local/share/cubrid-ci-data/github-actions/CUBRID-cubrid/pr-8128/a5da823b2a84e95b4b22d48abe4a3f9fd601c176/providers/github-actions/runs/38223008491/attempts/1/test_shell/failures/shell_06_issues_17_1h_cbrd_20759_hide_cubrid_replay_cases_hide_cubrid_replay_sh-28fe0a99ca/message.txt) / [diff](/home/vimkim/.local/share/cubrid-ci-data/github-actions/CUBRID-cubrid/pr-8128/a5da823b2a84e95b4b22d48abe4a3f9fd601c176/providers/github-actions/runs/38223008491/attempts/1/test_shell/failures/shell_06_issues_17_1h_cbrd_20759_hide_cubrid_replay_cases_hide_cubrid_replay_sh-28fe0a99ca/diff.txt) |
| test_shell / 20 / 20.339 | `shell/_40_guava/cbrd_26659_utility_sa_physical/cases/cbrd_26659_utility_sa_physical.sh` | SA loader physical placement: source OOS4/37316 and LOB transfer OK; controller status 1 | uncomparable: absent from base | direct coverage; engine regression unlikely | high phase; medium cause | [message](/home/vimkim/.local/share/cubrid-ci-data/github-actions/CUBRID-cubrid/pr-8128/a5da823b2a84e95b4b22d48abe4a3f9fd601c176/providers/github-actions/runs/38223008491/attempts/1/test_shell/failures/shell_40_guava_cbrd_26659_utility_sa_physical_cases_cbrd_26659_utility_sa_physic-ae6f63879c/message.txt) / [diff](/home/vimkim/.local/share/cubrid-ci-data/github-actions/CUBRID-cubrid/pr-8128/a5da823b2a84e95b4b22d48abe4a3f9fd601c176/providers/github-actions/runs/38223008491/attempts/1/test_shell/failures/shell_40_guava_cbrd_26659_utility_sa_physical_cases_cbrd_26659_utility_sa_physic-ae6f63879c/diff.txt) |
| test_shell / 24 / 7.361 | `shell/_40_guava/cbrd_26659_partition_owner/cases/cbrd_26659_partition_owner.sh` | Partition ownership: 14 ownership/descriptor NOKs; 21 OKs | uncomparable: absent from base | direct coverage; engine regression unlikely | high | [message](/home/vimkim/.local/share/cubrid-ci-data/github-actions/CUBRID-cubrid/pr-8128/a5da823b2a84e95b4b22d48abe4a3f9fd601c176/providers/github-actions/runs/38223008491/attempts/1/test_shell/failures/shell_40_guava_cbrd_26659_partition_owner_cases_cbrd_26659_partition_owner_sh-f4eb1b3422/message.txt) / [diff](/home/vimkim/.local/share/cubrid-ci-data/github-actions/CUBRID-cubrid/pr-8128/a5da823b2a84e95b4b22d48abe4a3f9fd601c176/providers/github-actions/runs/38223008491/attempts/1/test_shell/failures/shell_40_guava_cbrd_26659_partition_owner_cases_cbrd_26659_partition_owner_sh-f4eb1b3422/diff.txt) |
| test_shell / 29 / 1.386 | `shell/_40_guava/cbrd_27237_rollback_vacuum/cases/cbrd_27237_rollback_vacuum.sh` | Controller dependency: controller status 127 before assertions; 1.386s | uncomparable: absent from base | direct harness | high inference | [message](/home/vimkim/.local/share/cubrid-ci-data/github-actions/CUBRID-cubrid/pr-8128/a5da823b2a84e95b4b22d48abe4a3f9fd601c176/providers/github-actions/runs/38223008491/attempts/1/test_shell/failures/shell_40_guava_cbrd_27237_rollback_vacuum_cases_cbrd_27237_rollback_vacuum_sh-50405a0016/message.txt) / [diff](/home/vimkim/.local/share/cubrid-ci-data/github-actions/CUBRID-cubrid/pr-8128/a5da823b2a84e95b4b22d48abe4a3f9fd601c176/providers/github-actions/runs/38223008491/attempts/1/test_shell/failures/shell_40_guava_cbrd_27237_rollback_vacuum_cases_cbrd_27237_rollback_vacuum_sh-50405a0016/diff.txt) |
| test_shell / 32 / 9.158 | `shell/_40_guava/cbrd_26659_snapshots_reclaim/cases/cbrd_26659_snapshots_reclaim.sh` | Snapshot/page reclaim candidate: controller status 1; 9.158s; internal phase unavailable | uncomparable: absent from base | direct coverage | high verdict; medium-low cause | [message](/home/vimkim/.local/share/cubrid-ci-data/github-actions/CUBRID-cubrid/pr-8128/a5da823b2a84e95b4b22d48abe4a3f9fd601c176/providers/github-actions/runs/38223008491/attempts/1/test_shell/failures/shell_40_guava_cbrd_26659_snapshots_reclaim_cases_cbrd_26659_snapshots_reclaim_s-eb029bc997/message.txt) / [diff](/home/vimkim/.local/share/cubrid-ci-data/github-actions/CUBRID-cubrid/pr-8128/a5da823b2a84e95b4b22d48abe4a3f9fd601c176/providers/github-actions/runs/38223008491/attempts/1/test_shell/failures/shell_40_guava_cbrd_26659_snapshots_reclaim_cases_cbrd_26659_snapshots_reclaim_s-eb029bc997/diff.txt) |
| test_shell / 36 / 73.942 | `shell/_06_issues/_14_2h/bug_bts_15330/cases/bug_bts_15330.sh` | Recovery/restart: server-start status 1; server visible before restart | additional_on_head: base case passed | unlikely | high observation; medium race | [message](/home/vimkim/.local/share/cubrid-ci-data/github-actions/CUBRID-cubrid/pr-8128/a5da823b2a84e95b4b22d48abe4a3f9fd601c176/providers/github-actions/runs/38223008491/attempts/1/test_shell/failures/shell_06_issues_14_2h_bug_bts_15330_cases_bug_bts_15330_sh-d560baf49d/message.txt) / [diff](/home/vimkim/.local/share/cubrid-ci-data/github-actions/CUBRID-cubrid/pr-8128/a5da823b2a84e95b4b22d48abe4a3f9fd601c176/providers/github-actions/runs/38223008491/attempts/1/test_shell/failures/shell_06_issues_14_2h_bug_bts_15330_cases_bug_bts_15330_sh-d560baf49d/diff.txt) |
| test_shell / 42 / 294.661 | `shell/_37_elderberry/cbrd_23842_cdc/bug/cbrd_27064/cases/cbrd_27064.sh` | CDC extraction: rc=-10; delete 21/700 and update 0/2400; subchecks 2,3 NOK | also_observed_on_base | unlikely | high signature; medium cause | [message](/home/vimkim/.local/share/cubrid-ci-data/github-actions/CUBRID-cubrid/pr-8128/a5da823b2a84e95b4b22d48abe4a3f9fd601c176/providers/github-actions/runs/38223008491/attempts/1/test_shell/failures/shell_37_elderberry_cbrd_23842_cdc_bug_cbrd_27064_cases_cbrd_27064_sh-1e79382118/message.txt) / [diff](/home/vimkim/.local/share/cubrid-ci-data/github-actions/CUBRID-cubrid/pr-8128/a5da823b2a84e95b4b22d48abe4a3f9fd601c176/providers/github-actions/runs/38223008491/attempts/1/test_shell/failures/shell_37_elderberry_cbrd_23842_cdc_bug_cbrd_27064_cases_cbrd_27064_sh-1e79382118/diff.txt) |
| test_shell / 47 / 1.424 | `shell/_40_guava/cbrd_26659_snapshot_visibility/cases/cbrd_26659_snapshot_visibility.sh` | Controller dependency: controller status 127 before assertions; 1.424s | uncomparable: absent from base | direct harness | high inference | [message](/home/vimkim/.local/share/cubrid-ci-data/github-actions/CUBRID-cubrid/pr-8128/a5da823b2a84e95b4b22d48abe4a3f9fd601c176/providers/github-actions/runs/38223008491/attempts/1/test_shell/failures/shell_40_guava_cbrd_26659_snapshot_visibility_cases_cbrd_26659_snapshot_visibili-341f37e007/message.txt) / [diff](/home/vimkim/.local/share/cubrid-ci-data/github-actions/CUBRID-cubrid/pr-8128/a5da823b2a84e95b4b22d48abe4a3f9fd601c176/providers/github-actions/runs/38223008491/attempts/1/test_shell/failures/shell_40_guava_cbrd_26659_snapshot_visibility_cases_cbrd_26659_snapshot_visibili-341f37e007/diff.txt) |
| test_sql / 09 / 0.823 | `sql/_36_guava/cbrd_26659/cases/cbrd_26659_oos_partition.sql` | Partition replication/assertion: move returns -21019; server asserts replication.c:468; later -677 | uncomparable: absent from base | direct coverage; engine regression unlikely | high assertion; medium origin | [message](/home/vimkim/.local/share/cubrid-ci-data/github-actions/CUBRID-cubrid/pr-8128/a5da823b2a84e95b4b22d48abe4a3f9fd601c176/providers/github-actions/runs/38223008491/attempts/1/test_sql/failures/sql_36_guava_cbrd_26659_cases_cbrd_26659_oos_partition_sql-84f61d9df8/message.txt) / [diff](/home/vimkim/.local/share/cubrid-ci-data/github-actions/CUBRID-cubrid/pr-8128/a5da823b2a84e95b4b22d48abe4a3f9fd601c176/providers/github-actions/runs/38223008491/attempts/1/test_sql/failures/sql_36_guava_cbrd_26659_cases_cbrd_26659_oos_partition_sql-84f61d9df8/diff.txt) |
| test_sql / 09 / 0.048 | `sql/_36_guava/cbrd_26659/cases/cbrd_26659_oos_partition_routing.sql` | Probable SQL cascade: following case: -581 then -493/-494; reconnect failure | uncomparable: absent from base | plausible downstream | high sequence; medium-high cause | [message](/home/vimkim/.local/share/cubrid-ci-data/github-actions/CUBRID-cubrid/pr-8128/a5da823b2a84e95b4b22d48abe4a3f9fd601c176/providers/github-actions/runs/38223008491/attempts/1/test_sql/failures/sql_36_guava_cbrd_26659_cases_cbrd_26659_oos_partition_routing_sql-7ffa735db2/message.txt) / [diff](/home/vimkim/.local/share/cubrid-ci-data/github-actions/CUBRID-cubrid/pr-8128/a5da823b2a84e95b4b22d48abe4a3f9fd601c176/providers/github-actions/runs/38223008491/attempts/1/test_sql/failures/sql_36_guava_cbrd_26659_cases_cbrd_26659_oos_partition_routing_sql-7ffa735db2/diff.txt) |
| test_sql / 09 / 0.146 | `sql/_36_guava/cbrd_26659/cases/cbrd_26659_oos_representation.sql` | Probable SQL cascade: following case: -581 then -493/-494 | uncomparable: absent from base | plausible downstream | high sequence; medium-high cause | [message](/home/vimkim/.local/share/cubrid-ci-data/github-actions/CUBRID-cubrid/pr-8128/a5da823b2a84e95b4b22d48abe4a3f9fd601c176/providers/github-actions/runs/38223008491/attempts/1/test_sql/failures/sql_36_guava_cbrd_26659_cases_cbrd_26659_oos_representation_sql-ea38b72f44/message.txt) / [diff](/home/vimkim/.local/share/cubrid-ci-data/github-actions/CUBRID-cubrid/pr-8128/a5da823b2a84e95b4b22d48abe4a3f9fd601c176/providers/github-actions/runs/38223008491/attempts/1/test_sql/failures/sql_36_guava_cbrd_26659_cases_cbrd_26659_oos_representation_sql-ea38b72f44/diff.txt) |

## 1. Priority: snapshot_visibility and rollback_vacuum controller pruning

**Observed.** The committed visibility entrypoint invokes:

```bash
timeout --kill-after=240s 420s bash \
  ../../cbrd_26659_snapshots_reclaim/cases/snapshot_controller.sh \
  --scenario visibility > oos11.controller.log 2>&1
```

CI reports `controller_status=127`, zero whole seconds in the case timing and 1.424s in JUnit. None of the eight required controller phase assertions appears. The abort entrypoint invokes the same sibling script with `--scenario abort`, reports status 127, and takes 1.386s. Framework configuration restoration passes in both wrappers. These observations establish an early controller failure, not failed old-snapshot values or post-vacuum corruption.

The exact [workflow pruning code](/home/vimkim/tmp/oos-ci-analysis-38223008491/workflow-exact.yml:1985) builds a list of assigned case directories and deletes every other directory named `cases`. The controllers' owner case is in shard **32**, visibility in **47**, rollback/vacuum in **29**. The same controller's directory survives on shard 32, but not on 47 or 29. The auxiliary logs show the pruning step executed and reconciled 67 assigned cases on each shard. [Static pruning proof](/home/vimkim/tmp/oos-ci-analysis-38223008491/static-prune-proof.json) reconstructs retained directories from the validated per-shard case inventory; it executes no testcase and changes no repository.

The [exact visibility source](/home/vimkim/tmp/oos-ci-analysis-38223008491/exact-source/5f049c52c477aef8aa277e978276af4f233d20fd/shell/_40_guava/cbrd_26659_snapshot_visibility/cases/cbrd_26659_snapshot_visibility.sh:21) and [controller](/home/vimkim/tmp/oos-ci-analysis-38223008491/exact-source/5f049c52c477aef8aa277e978276af4f233d20fd/shell/_40_guava/cbrd_26659_snapshots_reclaim/cases/snapshot_controller.sh:5) also show that the controller resolves `oos_common` from its own location, while writing `oos11.*` in the caller's working directory. Moving it later must adjust its module lookup without changing the caller's artifact directory.

**Local comparison.** `final14-a03` records the same Engine and private TC commits. Visibility has nine OK assertions, controller exit 0, the old/new snapshot ACK sequence, three stable samples of **4 chunk records / 37316 summed record bytes**, and owned cleanup. Controller duration is 10s. User-page count remains 9 and `page_reclaim_credit=false`; this passing test intentionally proves chunk-record cleanup rather than empty-page return. I checked all **266 mapped visibility artifact hashes** against the retained proof. The caller and common runtime hashes match exact Git objects; the shared controller hash matches the dependency audit at the same private revision. The final14 executed-file inventory itself does not list that sibling controller separately, so its binding is the recorded TC revision plus audit, not a newly claimed per-file execution receipt. [Local proof validation](/home/vimkim/tmp/oos-ci-analysis-38223008491/local-proof-validation.json), [source binding](/home/vimkim/tmp/oos-ci-analysis-38223008491/local-snapshot-source-binding.json).

**Inference — high confidence, direct harness relation.** The dependency living under another testcase's prunable `cases/` directory is the immediate blocker. It explains both fast status-127 failures and why native focused selection passed: that selection filters execution while retaining the corpus needed by the caller. Increasing timeouts, changing snapshot isolation or adding a Python package does not address this observed dependency layout.

**Unknowns.** The redirected CI `oos11.controller.log` was not collected, so the literal Bash missing-file error is not directly observed. A shard filesystem capture could falsify the reconstructed absence. Later behavior under the CI runtime remains unqualified even after the dependency is restored. Local CTP assets are `9c62858b10005d721546cc007be260844033b9e9` with recorded local modifications; CI uses `44e3f97c788ad82091d5b66d728852f3279b1e86`. Local OptDebug/native containment and CI's debug artifact/CTP pods are distinct, regardless of the runtime's printed “optdebug” banner.

**Falsifier.** A verified post-prune shard 47/29 filesystem contains the expected readable controller and its captured stderr identifies a different missing command, or a controlled shard-shaped input retains the controller yet still produces the same launch failure.

**Next action.** In a separately authorized repair, move the shared controller to a non-`cases` support directory, such as `shell/_40_guava/oos_common/`, update all three callers and its relative module lookup, and audit all cross-case dependencies among the 18 entrypoints. Add an explicit readable-controller prerequisite and include a bounded controller-error tail when the wrapper fails. Preserve strict phase/ACK/value/cleanup gates. Qualify visibility independently with the sibling `cases/` directory absent. Then run the abort candidate independently; it may expose the still-unfixed local rollback/vacuum defect after the launch blocker is removed.

## 2. Check of the four documented candidate failures

All four candidates were freshly run locally at private `5f049c52c` and Engine `a5da823`. Their retained local records remain failures, with no passing credit. I verified **1045 mapped candidate artifact hashes**: partition 77, reclaim 266, SA physical 470 and rollback/vacuum 232. The documentation's local “all four reach their intended checks” statement applies to that native selection; it does not establish the same reachability in this CI execution.

| Candidate | Local observed cause | What this CI proves | Assessment of the documented cause in CI |
| --- | --- | --- | --- |
| partition_owner | 14 owning-child/descriptor NOKs, 21 OKs; exact values and cleanup pass | The same 14 named NOKs and 21 OKs; root/p0 ownership and descriptor checks fail while logical moves and duplicate-key checks pass | Directly reproduced behavior signature; high confidence |
| utility_sa_physical | Loaded SHOW has no OOS file; strict loaded physical gate rejects expected 4/37316 | Source values/schema, OOS4/37316, checkdb, unload and external LOB transfer pass; then status 1, with cleanup OK; no loaded-phase pass | Compatible with local physical-placement failure; medium confidence, not a directly observed CI `has_oos_file=0` |
| snapshots_reclaim | Full survivor values and 4/37316 drain pass; pages stay 9; `snapshot no positive page reclamation` | Shared controller is retained on its own shard; it runs and returns 1 after 8 whole seconds; only wrapper NOK and config restoration are visible | Known page-reclaim cause is plausible, medium-low confidence; first failing CI phase unknown |
| cbrd_27237_rollback_vacuum | Reaches `rollback_vacuum_reached`; post-vacuum pre-image read emits inconsistent/corrupted OOS metadata | Controller status 127 before any journal/behavior proof | Known corruption cause is **not exercised by this CI evidence**; launch blocker takes precedence |

**Partition ownership observations and inference.** CI's named physical ownership failures exactly match the retained local assertion pattern. Successful logical movement does not establish correct child heap/VFID ownership. Relation is direct through new coverage, confidence high for the conformance symptom; a new Engine change in PR8128 is unlikely because the source trees are identical. The exact owner/class/descriptor checks and fixtures are in the [recorded case directory](/home/vimkim/tmp/oos-ci-analysis-38223008491/exact-source/5f049c52c477aef8aa277e978276af4f233d20fd/shell/_40_guava/cbrd_26659_partition_owner/cases/cbrd_26659_partition_owner.sh). Internal call-path causality remains unknown.

**Partition falsifier / action.** Exact-input SHOW/diagdb evidence proving destination-child ownership satisfies the unchanged gate, or a parser defect explaining the mismatch, would falsify the inferred engine placement gap. Reproduce normal and forced routing with exact logical and physical oracles and inspect partition destination heap selection before designing an ownership fix. Preserve the correct expected ownership.

**SA physical observations and inference.** The [utility controller](/home/vimkim/tmp/oos-ci-analysis-38223008491/exact-source/5f049c52c477aef8aa277e978276af4f233d20fd/shell/_40_guava/oos_utility/utility_roundtrip.sh:193) performs SA `loaddb -S --no-logging`, validates complete loader summaries, starts the loaded database and requires exact values/schema plus OOS4/37316. The shared module lives outside `cases/` and survives shard pruning. The local `oos12.controller.log` fails at `loaded.physical status5`; CI emits all the same preceding seven PASS lines and the same subsequent cleanup sequence. That supports, but does not prove, the same loaded-placement failure. A loader error or start/verification failure in the intervening hidden phases is also possible. Relation is direct new coverage; inferred placement confidence medium.

**SA physical falsifier / action.** A CI controller log failing before loaded physical verification, or loaded SHOW satisfying OOS4/37316, falsifies that assignment. Retain `oos12.controller.log`, complete loader summaries, loaded values/schema, SHOW, parse output and diagdb in a focused attempt. Keep the separately passing SA logical case visible; its pass does not qualify physical placement.

**Reclaim observations and inference.** The exact controller's [page gate](/home/vimkim/tmp/oos-ci-analysis-38223008491/exact-source/5f049c52c477aef8aa277e978276af4f233d20fd/shell/_40_guava/cbrd_26659_snapshots_reclaim/cases/snapshot_controller.sh:225) requires fewer user pages after a stable eligible chunk drain; downstream churn is reached only after that gate. The local failure explicitly names absent positive page reclamation. CI has a running controller rather than the missing dependency, but its generic status 1 cannot prove it reached the page gate. Relation is direct coverage, inferred CI page cause medium-low. The specification distinguishes chunk-record deletion from eventual empty-page return; relaxing that gate would erase the intended coverage.

**Reclaim falsifier / action.** A retained CI journal showing an earlier setup/ACK/value/drain failure falsifies the page-cause hypothesis. A verified decrease in safely reclaimable pages with the same fixture falsifies the recorded local symptom. First retain the journal, SHOW samples, survivor values, mutation LSA/vacuum completion and cleanup receipts; then diagnose page return and growth-gate behavior. No positive churn claim is supported by the current CI message.

**Rollback local boundary.** The locally retained corruption message is genuine exact-input evidence for the recorded native attempt, not evidence that this CI exercised the same defect. The accepted OOS undo/ownership requirements require pre-image chains to remain readable through rollback and MVCC-safe cleanup. They provide the intended behavior, not a completed repair or the exact cause at this revision. After fixing controller placement, a focused abort run reaching `rollback_vacuum_reached` and then reading the exact pre-image is the next discriminating experiment. A pass under a controlled vacuum horizon or a different failing phase falsifies transfer of the local cause to CI.

Normative authority: [OOS-CONTEXT.md](/home/vimkim/gh/cubrid-oos-context/OOS-CONTEXT.md), last updated 2026-10-08, SHA-256 `b38059a3a8e9495a88c16cfe14daec89d72586e3d0ef2c86755b64305ebccb65`; source/working environment validation passed. Its implementation observations are dated context and do not prove current ticket status. This report makes no new JIRA workflow-state claim.

## 3. SQL partition assertion and two subsequent failures

**Observed.** The first divergent statement is `update oos08_part set id=12 where id=1`; the independent answer expects one updated row and receives `Error:-21019`. The [exact shard 09 job log](/home/vimkim/tmp/oos-ci-analysis-38223008491/supplementary/sql-09.log:1324) simultaneously records `repl_log_insert`, `replication.c:468`, `assert(false)`. Later statements in that testcase return `-677` (`ER_BO_CONNECT_FAILED`). This same partition-move/assertion signature was present in run38043651879.

At exact Engine `a5da823`, line 468 is the empty `tdes->oos_insert_lsa_queue` branch for `RVREPL_OOS_INSERT` or `RVREPL_DUMMY_OOS_RECORD`. This narrows the violated invariant: replication expected an OOS insertion LSA but its queue was empty. The assertion message alone does not identify which recovery index or producer/consumer path caused it. [Exact source](https://github.com/CUBRID/cubrid/blob/a5da823b2a84e95b4b22d48abe4a3f9fd601c176/src/transaction/replication.c#L459).

The shard's ordered sequence is:

| Sequence | Case | Observation |
| --- | --- | --- |
| 307 | oos_chunk_boundaries | Pass |
| 308 | oos_partition | Server assertion, NOK |
| 309 | oos_partition_routing | Immediate JDBC connection failure, recovery/reconnect attempts, NOK |
| 310 | oos_representation | NOK: create/drop return -581, following DML/query -493/-494 |
| 311 | oos_schema | Pass; later cases continue passing |

Both later cases fail from their first DDL, before their own intended logical assertions. `-581` is `ER_DB_NO_MODIFICATIONS`; `-493/-494` are parser syntax/semantic errors. Those code meanings are verified in exact `src/base/error_code.h`. The routing failure's connection stack and server recovery output are observed; the exact state that caused temporary modification refusal is not captured. All three SQL/answer pairs are byte-identical between the two PR runs, using the same Engine/build-producing run and CTP SHA.

The [effective CI config](/home/vimkim/tmp/oos-ci-analysis-38223008491/supplementary/sql-09.log:924) enables `ha_mode=yes` in the server and HA sections and uses JDBC `test_default.xml`, charset `en_US`, broker port 33120, and serial case execution within the shard. This is materially different from assuming that a standalone CSQL or non-HA native pass qualifies this assertion path.

**Inference.** There is one directly observed partition replication assertion and two probable cascade victims. Confidence is high for the violated queue invariant and medium-high for the cascade; root producer/consumer causality is unknown. PR relation is direct through the new partition reproducer, plausible downstream for routing/representation, and unlikely as a new Engine-code regression. The later cases' previous passes and subsequent case recovery support the cascade model, but do not prove they have no independent bug.

**Unknowns.** No core/backtrace, runtime `rcvindex`, queue history, affected transaction descriptor or recovery-state trace was acquired. The prior run also asserted yet the two followers passed, so restart/reconnect timing and state carryover require controlled evidence. Shared test inputs/build provenance do not establish equal execution timing or full runtime state.

**Falsifiers.** Routing or representation fails with the same signature on its own fresh healthy database; alternatively, the exact partition call stack reveals the assertion came from a different operation than the observed move. Either would require splitting the present cause grouping.

**Next action.** First reproduce the partition case alone with the CI HA/JDBC/debug settings and capture the actual recovery index plus OOS LSA queue push/pop/clear sequence around partition movement. Then run routing and representation individually on fresh databases. Finally replay the three-case order to distinguish engine assertion, restart/cascade handling and independent testcase behavior. Fix the queue producer/consumer contract only after that trace; removing the assertion or changing golden answers is not a demonstrated repair.

## 4. Existing recovery case: bug_bts_15330

**Observed.** Its complete script/SQL/Java/answer directory is identical on head, previous and exact-base TC revisions. The exact-base run passed in 92.688s and the previous PR run in 91.842s; the current run fails in 73.942s. The test launches 40 Java clients, sleeps 60 seconds, kills server/master, waits for a port condition and calls `cubrid server start db15330 > start.log 2>&1`. That restart returns 1, producing `Test Fail: recovery`. The subsequently unconditional `write_ok` is also printed; the recorded NOK remains a failure.

Crucially, its [CI failure message](/home/vimkim/.local/share/cubrid-ci-data/github-actions/CUBRID-cubrid/pr-8128/a5da823b2a84e95b4b22d48abe4a3f9fd601c176/providers/github-actions/runs/38223008491/attempts/1/test_shell/failures/shell_06_issues_14_2h_bug_bts_15330_cases_bug_bts_15330_sh-d560baf49d/message.txt:280) shows a live `cub_server db15330` in the process listing immediately before “start recovery” and the failed start command. `start.log` is redirected and absent from the collected text. No recovery assertion, corruption message or core is directly observed here.

**Inference — medium confidence, PR relation unlikely.** Concurrent reconnection/automatic server restart or an incomplete kill/start race is a stronger immediate hypothesis than assigning a new storage recovery defect. The Java workload remains active across the kill and explicit restart. A live server can make an explicit start fail. The exact start failure still needs its own log. This is `additional_on_head` relative to comparable exact-path base coverage, with changed CTP/runtime configuration limiting cause attribution; it is not a proven Engine regression.

**Falsifier.** `start.log` or server diagnostics show a real recovery failure rather than an already-running/start-race condition; or an exact repeated run fails after proving the owned server is absent and eliminating client-driven restart.

**Next action.** Reproduce this case alone with its 4KB page size, Java workload, kill sequence and CI restart settings. Retain `start.log`, `result.log`, `wait.log`, the post-kill PID/executable/birth identities and server error logs before proposing a synchronization change. Keep recovery validation and an already-running-server case distinct.

## 5. Existing replay mismatch: hide_cubrid_replay

**Observed.** All case-directory Git objects are identical across head, previous and exact-base revisions. Current CI fails subchecks 7 and 8: expected `******` in `qa9.answer` and `********` in `qa10.answer` are absent from the generated process-output result. Base failed only subcheck 7; previous run failed only subcheck 8. The current console also reports `Method "add_user" not found`, undefined/missing users, and connection errors for the affected replay scenarios.

**Inference — medium confidence, PR relation unlikely.** This is an existing replay/process-observation instability or user-setup compatibility issue, with a concrete shared `qa9` failure component on the exact base. The new combined failure set is not byte-identical to either earlier set. Missing-user/connect failures plausibly shorten the process lifetime sampled by the case; causality and sampling timing remain unknown. The inventory counts this as `also_observed_on_base` **only for the matching qa9 component**, while recording the additional qa10 component separately. It makes no “whole case had the same cause” claim.

**Falsifier.** Correct user setup and a verified replay process lifetime still produce a deterministic unrelated output defect; or exact captured process/output evidence disproves the missed-sample/setup hypothesis.

**Next action.** Reproduce separately, retain setup CSQL output and actual user catalogue, both replay command lines/results and bounded process samples. Diagnose setup first, then compare the two masking expectations. Do not rewrite the answers merely to match an empty sample.

## 6. Existing CDC extraction failure: cbrd_27064

**Observed.** Complete testcase-directory Git objects are identical across the three TC revisions. All three executions pass insert overflow and fail delete/update overflow with extractor `rc=-10`, extractor exit 1, short target counts and reported `CORRUPTION=0`. Current counts are delete **21/700**, update **0/2400**; base **23/700**, **0/2400**; previous **10/700**, **1/2400**. LSAs, timings and partial counts vary. These are matching operation/error signatures, not identical full messages or proof of an identical root cause. This is `also_observed_on_base` with high signature confidence.

**Inference — medium confidence, PR relation unlikely.** The signature is consistent with the retained CDC/OOS-history gap. The accepted [11.5 deferral decision](/home/vimkim/gh/cubrid-oos-context/docs/adr/0005-defer-oos-history-from-the-11-5-merge.md) requires the CDC cases to remain enabled and visible; it does not explain every possible `rc=-10` path. No new CDC repair is established by this PR or by a passing neighbouring case.

`cbrd_27075` passed in the current run although it failed on both earlier executions; its entire case directory is also unchanged. That is an observed pass on one run, not a verified CDC fix or proof that the deferred gap is gone.

**Falsifier.** A precise extractor/engine trace attributes the error to another configuration, driver or log-source failure rather than the inferred retained gap, or controlled same-input runs establish a different signature.

**Next action.** Keep the failure enabled. Investigate it as separate CDC follow-up work with actual extractor error meaning, offending record/LSA, vacuum timing and required before/after values. Do not exclude it, suppress the errors or weaken target counts.

## Comparison with run38043651879 and exact merge base

### Previous PR execution: same Engine and public inputs

| Metric | Previous run38043651879 | Current run38223008491 | Change |
| --- | ---: | ---: | --- |
| Shell passed / failed / skipped | 3256 / 21 / 30 | 3269 / 8 / 30 | 14 formerly failed cases pass; one formerly passed case fails |
| Added OOS shell entrypoints passed / failed | 0 / 18 | 13 / 5 | Thirteen converted cases gain a CI pass |
| SQL passed / failed | 17487 / 1 | 17485 / 3 | Partition remains red; routing and representation newly red |
| Medium passed / failed | 975 / 0 | 975 / 0 | Same count and pass |

The 13 newly passing OOS shell cases are `owner_drop`, `representation_chunks`, `dml_transitions`, `transactions`, `read_paths`, `schema_policy`, `lob_locators`, `tde_wal`, `crash_committed`, `crash_undo`, `utility_cs`, `utility_sa` and `backup_restore`. The previously failing existing `cbrd_27075` also passes. The newly failing existing `bug_bts_15330` yields **21 − 14 + 1 = 8** shell failures. Seven exact shell paths fail on both PR runs, but their signatures are not all the same. [Ordered verdict change inventory](/home/vimkim/tmp/oos-ci-analysis-38223008491/previous-verdict-changes.json).

Private TC changed `27db3d6b6d966056de474af277ee40735190f00c` → `5f049c52c477aef8aa277e978276af4f233d20fd`. Public TC remained `1a556a0752073aaad573bf87d53f3eb75f398138`. Both PR executions consumed the same debug build-producing run38043651879 at Engine `a5da823` and CTP `44e3f97c788ad82091d5b66d728852f3279b1e86`. Shell duration-based distribution changed case-to-shard assignments. The source/TC/build identity evidence is much stronger than assuming equality from run titles, but process scheduling, node/image state and shard-neighbour effects are not controlled.

The earlier run's all-18 launch failures no longer characterize the current corpus. In particular, current status 127 for the two snapshot wrappers remains a dependency failure even after conversion; it must not be attributed to Python merely because the earlier report discussed Python. The four candidate red identities are also not enough to equate their local and CI internal failure phases.

### Exact merge-base execution

The independently resolved relationship is:

- PR head `a5da823b2a84e95b4b22d48abe4a3f9fd601c176`.
- Target `feature/oos-merge`, pinned tip `fb567a629cdb390fff920542173fa36f454c74a0`.
- Exact unique merge base `fb567a629cdb390fff920542173fa36f454c74a0`.
- Relationship observed `2026-10-12T10:29:28.813323368Z`; it matches the pinned head snapshot.
- Both complete Engine trees are `016702849c2d67eb349a51ca4c8bf1a7157ea789`; `git diff <base> <head>` is empty.
- Exact-base [run36570256001, attempt 1](https://github.com/CUBRID/cubrid/actions/runs/36570256001), consuming debug build from run36570061594, attempt 1, at the exact base SHA.
- Discovery covered all paginated exact-commit status/check links, with no repository-wide workflow scan. This bounds discovery coverage rather than proving that no other CI ever existed.

| Suite | Base planned | Base passed | Base failed | Base errors | Base skipped | Base unrun | Base TC revision |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| test_medium | 975 | 975 | 0 | 0 | 0 | 0 | bdba62aee0faec05abdd861518824c69b6c1b3c5 |
| test_shell | 3289 | 3254 | 5 | 0 | 30 | 0 | c4b9d482fbd491a68510b2552df2c3cac91911fc |
| test_sql | 17471 | 17471 | 0 | 0 | 0 | 0 | bdba62aee0faec05abdd861518824c69b6c1b3c5 |

All five new failing shell paths and all three failing SQL paths are absent from the exact-base testcase tree and execution. They are **uncomparable**, not baseline passes. Complete testcase-directory trees for replay, CDC27064 and recovery15330 are identical across head/previous/base. The remaining base-only failure directories are also unchanged. These are exact Git-object comparisons of the affected directories, not whole-repository equivalence. [Source comparisons](/home/vimkim/tmp/oos-ci-analysis-38223008491/source-comparison.json), [base-only directory equality](/home/vimkim/tmp/oos-ci-analysis-38223008491/base-only-source-equality.json).

Case-level reconciliation, with matching components explicitly bounded:

| Classification | Count | Cases / boundary |
| --- | ---: | --- |
| Head failures | 11 | 8 shell + 3 SQL |
| also_observed_on_base | 2 | CDC27064 operation/error signature; replay **qa9 component only**, with broader head mismatch recorded |
| additional_on_head | 1 | recovery15330 exact path passed on base; different runtime/CTP limits causal claims |
| uncomparable | 8 | Five new shell paths plus three new SQL paths, absent from base |
| base_only | 3 | bug_bts_15156, cbrd_26349, cbrd_27075; explicit current JUnit passes, unchanged case directories |

Thus **11 = 2 + 1 + 8**, and **5 base failures = 2 matched paths + 3 base-only paths**. The replay qa10 component is retained as an extra head mismatch within the already-counted replay record; it is not counted as another testcase. “Additional on head” is an observed case comparison, not proof of an Engine regression. Matching signatures establish pre-existence of that signature, not harmlessness or a common root cause.

The exact-base CTP revision was `4d0043a7b149b3fc5d3ccb2e08c98cf8d77b34fb`, whereas both PR runs use `44e3f97c788ad82091d5b66d728852f3279b1e86`. Complete image/configuration equivalence with the base was not established. Comparisons for shared signatures and unchanged case inputs are valid within these limits; configuration-sensitive causal attribution remains unknown. No added testcase has a same-test-revision merge-base execution. Baseline evidence is available and validated; **baseline coverage of the eight new failing paths is unavailable**.

The terminal receipt records [public TC PR3688](https://github.com/CUBRID/cubrid-testcases/pull/3688) and [private TC PR4365](https://github.com/CUBRID/cubrid-testcases-private-ex/pull/4365) as open drafts. Both require human merge/closure disposition under the TC Merge Gate policy. No named required gate check was observed in that receipt; policy blockage and observed check presence are distinct. No TC disposition was changed.

## Evidence inventory and preservation

Raw collector bundles remain outside the documentation repository:

| Evidence | Durable pointer |
| --- | --- |
| Current/previous head run directories | [Head manifest snapshot](/home/vimkim/tmp/oos-ci-analysis-38223008491/head-manifest.json), [previous snapshot](/home/vimkim/tmp/oos-ci-analysis-38223008491/previous-manifest.json); immutable suite directories under `providers/github-actions/runs/<run>/attempts/1/` in the PR evidence root |
| Exact merge-base bundle | [Base manifest snapshot](/home/vimkim/tmp/oos-ci-analysis-38223008491/base-manifest.json) and `/home/vimkim/.local/share/cubrid-ci-data/github-actions/CUBRID-cubrid/commits/fb567a629cdb390fff920542173fa36f454c74a0/` |
| Validation / report gate | [validate.py](/home/vimkim/tmp/oos-ci-analysis-38223008491/validate.py), [validation.json](/home/vimkim/tmp/oos-ci-analysis-38223008491/validation.json), [assessment.json](/home/vimkim/tmp/oos-ci-analysis-38223008491/assessment.json); head/base/previous request/result snapshots in the same directory |
| Exact testcase inputs and signatures | [source-comparison.json](/home/vimkim/tmp/oos-ci-analysis-38223008491/source-comparison.json), [failure-signatures.json](/home/vimkim/tmp/oos-ci-analysis-38223008491/failure-signatures.json), `exact-source/<TC SHA>/`; read with `git show`, without checkout/fetch/reset |
| Workflow and job text | [workflow-exact.yml](/home/vimkim/tmp/oos-ci-analysis-38223008491/workflow-exact.yml), [supplementary receipt](/home/vimkim/tmp/oos-ci-analysis-38223008491/supplementary/receipt.json); plan, shell20/29/32/36/47 and SQL09 logs |
| Previous/native phase records | [Historical CI report](ci_analysis_report_a5da823_codex.md), [shell conversion report](ci-replan/shell-conversion-results-20261012.md), `final14-a03` and `candidates4-a01` under `/home/vimkim/tmp/oos-shell-conversion-20261012/` |
| Local proof reread | [local-proof-validation.json](/home/vimkim/tmp/oos-ci-analysis-38223008491/local-proof-validation.json): 266 snapshot + 1045 candidate hashes checked; existing assertions/journals and failures retained |
| User-provided terminal record | [terminal-receipt.json](/home/vimkim/tmp/oos-ci-8128-shell-conversion-20261012/terminal-receipt.json) |
| Preservation baseline | [initial-worktrees.json](/home/vimkim/tmp/oos-ci-analysis-38223008491/initial-worktrees.json); historical report SHA-256 `d3e6d458140237701fab6f056bafd0892019c8f28f76043e94f1d06170906cf8` |

Only this new run-specific report and its required README index/navigation entry are documentation changes. They remain uncommitted and unpushed under the analyzer workflow. Source and testcase indexes/worktrees are preserved; the unrelated CCI modification is `win/cci_version.h` in submodule HEAD `79d0888c26a2543d31f53eb7b6c9738db110fff4`, with unchanged diff fingerprint `ac6c1620024db5049a18f0199602de635eca6e8ef440936c05c4117a858027f9`.

Final reconciliation checked all 11 inventory records exactly once, all three suite rows, 134 local document/evidence links and syntax of all five Bash command blocks. Source/testcase checkout identities and the historical report/CCI fingerprints were preserved. [Report checks](/home/vimkim/tmp/oos-ci-analysis-38223008491/report-checks.json). Command syntax checks do not establish a reproduction verdict.

## Prioritized fix plan

These are proposed follow-up tasks; this analysis authorizes none of their execution or publication.

1. **P0 — make snapshot controller available after shard pruning.** Move shared runtime code outside testcase `cases/`, update visibility/reclaim/abort callers and the controller's module lookup, and add precise launch diagnostics. Prove visibility reaches all existing phases with the sibling case removed. Audit every added entrypoint for pruned cross-case dependencies. This addresses the passing-local/failing-CI gap and unlocks honest rollback/vacuum diagnosis.
2. **P1 — diagnose the partition replication assertion.** Reproduce `oos_partition.sql` alone with debug + HA/JDBC settings; capture `rcvindex`, transaction and OOS LSA queue state. Repair the identified producer/consumer mismatch and keep the correct partition-move answer. Separately run routing/representation fresh, then the ordered three-case sequence, to verify the two likely cascade failures disappear and to expose any independent fault.
3. **P1 — restore rollback-after-vacuum safety after the launch fix.** Require the vacuum barrier and exact old-value read, then use the retained local corrupted-pre-image evidence to investigate chain lifetime/undo ownership. Preserve identity and cleanup checks; do not turn a setup failure into assumed defect coverage.
4. **P2 — resolve partition-child ownership and SA loaded placement.** Partition ownership has directly reproduced physical NOKs. SA physical placement needs the hidden loaded-phase evidence before assigning the CI cause. Maintain logical and physical qualifications separately and retain external LOB transfer checks.
5. **P2 — establish the reclaim candidate's first failing CI phase.** Obtain controller/journal/SHOW/vacuum-horizon evidence, then resolve empty-page return and downstream churn without relaxing chunk/page distinctions or crediting unreached phases.
6. **P2 — isolate recovery15330 and replay instability.** For recovery, test the live-server/restart hypothesis with `start.log` and post-kill identities. For replay, verify user setup, connect errors and process sampling before changing synchronization or outputs. Keep these investigations independent of the converted OOS controllers.
7. **Separate retained work — CDC27064.** Continue the deferred-history diagnosis with the exact extractor record; retain the enabled failure. A current CDC27075 pass does not close that work.

Completion of a future repair requires focused artifact-backed evidence, correct expectations and cleanup, then the applicable review/publication workflow. TC PR merge/closure remains human-owned; a future CI operation requires the separately directed CI workflow. A green result is not assumed from fixing the first dependency.

## Focused reproduction commands for the next authorized phase

No commands in this section were executed as database/testcase reproductions during this analysis. Preserve failed and passing attempts separately. Native commands use the accepted `cubrid-test-shell-run` / `cubrid-test-sql-run` containment contract; they are focused local controls, not a claim of whole-corpus CTP or CI-runtime equivalence. Any CTP comparison must be explicitly requested separately.

### A. Deterministic shard-dependency check, without starting a database

This materializes a disposable Git export and applies the exact shell-directory pruning rule. Run it separately for the visibility and rollback entrypoints. It checks the missing dependency without relying on a timeout or changing the testcase checkout.

```bash
TC_REPO=/home/vimkim/gh/cubrid-testcases-private-ex/develop
TC_SHA=5f049c52c477aef8aa277e978276af4f233d20fd
CASE_NAME=cbrd_26659_snapshot_visibility  # repeat with cbrd_27237_rollback_vacuum
PRUNE_PROOF=$(mktemp -d /home/vimkim/tmp/oos-prune-proof.XXXXXX)
git -C "$TC_REPO" archive "$TC_SHA" shell/_40_guava |
  tar -xf - -C "$PRUNE_PROOF"
CALLER_DIR="$PRUNE_PROOF/shell/_40_guava/$CASE_NAME/cases"
CONTROLLER="$PRUNE_PROOF/shell/_40_guava/cbrd_26659_snapshots_reclaim/cases/snapshot_controller.sh"
test -r "$CONTROLLER" || exit 1
printf '%s\n' "$CALLER_DIR" > "$PRUNE_PROOF/keep_dirs.list"
find "$PRUNE_PROOF/shell" -name cases -type d |
  { grep -v -F -f "$PRUNE_PROOF/keep_dirs.list" || :; } |
  xargs -r rm -rf
if test -r "$CONTROLLER"; then
  printf 'controller survived pruning\n'
else
  printf 'controller absent after pruning: %s\n' "$CONTROLLER"
fi
```

Before repair the controller is predicted absent. After relocation, adjust this check to the new support path and require it to survive. Keep the dependency check separate from the subsequent native behavior verdict.

### B. One fresh contained native attempt per shell or SQL selection

The following recipe uses the preserved local install/CTP as explicit inputs; it deliberately reproduces the prior native environment. It does not claim CI image or build equivalence. A later CI-faithful run must supply a proven `a5da823` CI debug install and the recorded CTP/runtime configuration instead. The preflight rejects an Engine/install mismatch; do not bypass it.

Choose one exact case. Shell choices cover all five added failures and the three existing failures in the inventory. SQL should first run each of its three failures separately, then the full `cbrd_26659/cases` group to preserve the observed adjacency.

```bash
# Execute inside the Engine worktree after loading its environment.
ENGINE=/home/vimkim/gh/cb/CBRD-26659-oos-testcases-handover
FOCUSED=/home/vimkim/.agents/skills/cubrid-common/scripts/testkit-focused.py
REFERENCE=/home/vimkim/tmp/oos-shell-conversion-20261012/final14-a03
SUITE=shell
CASE_REL=shell/_40_guava/cbrd_26659_snapshot_visibility/cases/cbrd_26659_snapshot_visibility.sh
# SQL alternative, fresh attempt for each:
# SUITE=sql
# CASE_REL=sql/_36_guava/cbrd_26659/cases/cbrd_26659_oos_partition.sql
# CASE_REL=sql/_36_guava/cbrd_26659/cases/cbrd_26659_oos_partition_routing.sql
# CASE_REL=sql/_36_guava/cbrd_26659/cases/cbrd_26659_oos_representation.sql
# Ordered group control: CASE_REL=sql/_36_guava/cbrd_26659/cases

cd "$ENGINE" || exit 1
ATTEMPT=$(mktemp -d /home/vimkim/tmp/oos-focus-38223008491.XXXXXX)
cp -a "$REFERENCE/cubrid" "$ATTEMPT/cubrid"
cp -a "$REFERENCE/CTP" "$ATTEMPT/CTP"
mkdir -p "$ATTEMPT/home" "$ATTEMPT/slots" "$ATTEMPT/cubrid/tmp"
if test -e "$ATTEMPT/cubrid/databases"; then
  mv "$ATTEMPT/cubrid/databases" "$ATTEMPT/databases.copied"
fi
mkdir -p "$ATTEMPT/cubrid/databases"

if test "$SUITE" = shell; then
  TC_ROOT=/home/vimkim/gh/cubrid-testcases-private-ex/tc-pr-8128
  test "$(git -C "$TC_ROOT" rev-parse HEAD)" = 5f049c52c477aef8aa277e978276af4f233d20fd || exit 1
  test -z "$(git -C "$TC_ROOT" status --porcelain)" || exit 1
  SCENARIO="$TC_ROOT/shell"
  printf '%s\n' "$TC_ROOT/$CASE_REL" > "$ATTEMPT/expected-cases.txt"
  BASE_CONF="$ATTEMPT/CTP/conf/shell_ci.conf"
else
  TC_ROOT=/home/vimkim/gh/cubrid-testcases/develop
  mkdir -p "$ATTEMPT/testcases"
  git -C "$TC_ROOT" archive 1a556a0752073aaad573bf87d53f3eb75f398138 \
    sql/_36_guava/cbrd_26659 | tar -xf - -C "$ATTEMPT/testcases"
  SCENARIO="$ATTEMPT/testcases/$CASE_REL"
  if test -d "$SCENARIO"; then
    find "$SCENARIO" -name '*.sql' -type f | sort > "$ATTEMPT/expected-cases.txt"
  else
    printf '%s\n' "$SCENARIO" > "$ATTEMPT/expected-cases.txt"
  fi
  BASE_CONF="$ATTEMPT/CTP/conf/sql.conf"
fi
CONF="$ATTEMPT/conf/$SUITE.conf"
python3 "$FOCUSED" prepare-config --suite "$SUITE" --base-conf "$BASE_CONF" \
  --output-conf "$CONF" --scenario "$SCENARIO" \
  --expected-list "$ATTEMPT/expected-cases.txt" || exit 1
```

For SQL, preserve the observed HA/JDBC mode before running. This changes only the disposable attempt's configuration. Other CI settings should be compared against the recorded effective config, not silently inherited from local defaults.

```bash
if test "$SUITE" = sql; then
  python3 - "$CONF" <<'PY'
import configparser, pathlib, sys
p = pathlib.Path(sys.argv[1])
c = configparser.ConfigParser(interpolation=None)
c.optionxform = str
c.read(p)
for section in ('sql', 'sql/cubrid.conf', 'sql/cubrid_ha.conf'):
    if not c.has_section(section): c.add_section(section)
c['sql']['jdbc_config_file'] = 'test_default.xml'
c['sql']['db_charset'] = 'en_US'
c['sql/cubrid.conf']['ha_mode'] = 'yes'
c['sql/cubrid_ha.conf']['ha_mode'] = 'yes'
with p.open('w') as f: c.write(f)
PY
fi
# Inspect the complete effective config and retain its digest before execution.
sha256sum "$CONF" > "$ATTEMPT/effective-config.sha256"
```

Use the existing validation lock, a disposable registry/install/CTP/HOME, one slot, explicit native family and containment. The historical reference CTP/install are read-only inputs; every actual run writes under its new attempt. Keep outer cleanup and install-process absence checks from the focused-run workflow in addition to the artifact gate.

```bash
exec 9>/home/vimkim/tmp/oos-developer-regressions-20261008/validation.lock
flock -x 9
NATIVE=sql
if test "$SUITE" = shell; then NATIVE=shell; fi
RUN_ENV=(env
  HOME="$ATTEMPT/home"
  CUBRID="$ATTEMPT/cubrid"
  CUBRID_DATABASES="$ATTEMPT/cubrid/databases"
  CUBRID_TMP="$ATTEMPT/cubrid/tmp"
  CUBRID_CONF_FILE="$ATTEMPT/cubrid/conf/cubrid.conf"
  CTP_HOME="$ATTEMPT/CTP"
  init_path="$ATTEMPT/CTP/shell/init_path"
  CUBRID_TESTCASES_PRIVATE_EX_DIR=/home/vimkim/gh/cubrid-testcases-private-ex/tc-pr-8128
  CUBRID_TESTCASES_DIR=/home/vimkim/gh/cubrid-testcases/tc-pr-8128
  TESTKIT_SLOT_ROOT="$ATTEMPT/slots"
  PATH="$ATTEMPT/CTP/bin:$ATTEMPT/CTP/common/script:$ATTEMPT/cubrid/bin:$PATH"
  LD_LIBRARY_PATH="$ATTEMPT/cubrid/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
  TESTKIT_NATIVE="$NATIVE" TESTKIT_CONTAIN=1)
direnv exec . "${RUN_ENV[@]}" python3 "$FOCUSED" preflight --suite "$SUITE" \
  > "$ATTEMPT/preflight.log" 2>&1 || exit 1
set +e
direnv exec . "${RUN_ENV[@]}" testkit "$SUITE" -c "$CONF" \
  > "$ATTEMPT/run.log" 2>&1
RUNNER_EXIT=$?
printf '%s\n' "$RUNNER_EXIT" > "$ATTEMPT/exit.status"
if test "$SUITE" = shell; then
  RESULT_DIR="$ATTEMPT/CTP/result/shell/current_runtime_logs"
else
  RESULT_DIR=$(sed -n 's/^Result Root Dir:[[:space:]]*//p' "$ATTEMPT/run.log" | tail -1)
fi
python3 "$FOCUSED" verify --suite "$SUITE" --result-dir "$RESULT_DIR" \
  --expected-list "$ATTEMPT/expected-cases.txt" --run-log "$ATTEMPT/run.log" \
  --runner-exit "$RUNNER_EXIT" > "$ATTEMPT/verify.log" 2>&1
VERIFY_EXIT=$?
printf '%s\n' "$VERIFY_EXIT" > "$ATTEMPT/verify.exit"
printf 'attempt=%s runner=%s artifact-gate=%s\n' "$ATTEMPT" "$RUNNER_EXIT" "$VERIFY_EXIT"
# Perform and retain the focused workflow's owned resource/config cleanup audit
# before releasing the lock; retain this attempt even if its verdict is NOK.
```

The all-pass verifier should reject retained failing candidates even if the runner returns 0. Inspect their named assertions/controller journals rather than converting that rejection into passing credit. A native visibility run on the full corpus is expected to repeat the earlier pass before repair; it is insufficient to validate shard compatibility. To test pruning under native containment, export `_40_guava` into a new attempt, prune all `cases/` except the chosen caller as in A, set `SCENARIO`/expected-list/TC environment to that export, and preserve the same owned cleanup contract. Do not delete sibling directories in the real TC checkout.

### Required retained artifacts by reproduction

| Focus | Evidence that distinguishes the hypotheses |
| --- | --- |
| visibility / rollback launch | Controller readability after pruning, `oos11.controller.log`, controller exit, all required phase/ACK journals and configuration/owned-resource receipts |
| rollback after controller repair | `rollback_vacuum_reached`, pre-image values, `abort_after_vacuum_values` output/error, positive chunk model and vacuum/LSA horizon |
| partition assertion | Isolated JDBC/HA output, actual `rcvindex`, OOS insertion-LSA queue producer/consumer history, server diagnostics/backtrace, then fresh routing/representation and ordered-group outcomes |
| partition_owner | Normal/forced root and child SHOW/diagdb ownership, descriptor/class/VFID evidence, logical values, duplicate-key result and cleanup |
| utility_sa_physical | Complete unload/loader summaries, explicit LOB hashes, loaded values/schema/SHOW, `loaded.physical` parse output and cleanup |
| snapshots_reclaim | Full controller journal, old/new ACK values, three stable chunk-drain samples, page counts, first-unvacuumed page/mutation eligibility and downstream churn reachability |
| recovery15330 | `start.log`, `result.log`, `wait.log`, post-kill server identity/liveness, auto-restart settings and server recovery diagnostics |
| replay / CDC | Replay user-setup and actual process samples; CDC offending record/LSA, extractor error details and exact target-count outcomes |
