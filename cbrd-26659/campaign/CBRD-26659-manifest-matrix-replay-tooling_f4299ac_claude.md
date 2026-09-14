# CBRD-26659 — Manifest, matrix and replay-bundle tooling (ticket 15)

> Observed: 2026-09-11 (KST). Engine baseline `f4299ac0cd777a2a964c1f197ae5ebf9841a4936` (ticket 11); normative context `f6543de` + sha256 `c9daf3c4…`; catalogue hash `0cc33c82…`.
> Author: Claude Fable 5.1 (ticket 15 subagent of session 6f4722b1), for the [Adversarial OOS testcase campaign](/home/vimkim/gh/cb/CBRD-26659-oos-testcases-handover/.scratch/oos-adversarial/spec.md) ticket 15.
> Scope: tooling under [`tools/`](tools/), evidence under [`evidence/ticket15/`](evidence/ticket15/), runs under `/home/vimkim/.cub/campaign/cbrd-26659/ticket15/`. Nothing in either testcase worktree changed; the pinned installs came back byte-identical after every run; nothing was pushed.
> Contract this tooling implements: [traceability schemas (ticket 12)](CBRD-26659-traceability-schemas_f4299ac_claude.md), section 3 "rules tooling must add" and section 11. Predecessors it absorbs: ticket 14's `run_attempt.sh`, `finalize_bundle.sh`, `campaign_ns.sh` and `validate_records.py`; ticket 13's `activation_check.sh`.
> **Build identity superseded for new runs (2026-09-14, ticket 41).** The runs recorded here used the ticket 11 build, which carries the unit-test seams. Ticket 39 item 1 re-pinned the campaign's unmodified build without them; see [engine baseline §10](CBRD-26659-engine-baseline_f4299ac_claude.md#10-revision-2-2026-09-14-the-re-pinned-build-without-the-unit-test-seams). These records and their evidence stay valid and unedited for the invocations that cite them; a new run uses the revision-2 identity.

Vocabulary follows the [docs glossary](../../CONTEXT.md): Campaign manifest, Coverage matrix, Attempt record, Replay bundle, OOS-path evidence, Failure of proof, Outcome, Accepted exclusion, Delivery gap, Capability gap, Specification gap, Engine defect.

## 1. What exists now

| File (under `cbrd-26659/campaign/tools/`) | One line |
|---|---|
| `run_ctp_sql.sh` | Runs one CTP SQL invocation under `campaign_ns.sh` against a pinned install, restores install and worktree by hash, runs the paired activation checker client-server, and hands everything to `ctp_sql_records.py`. |
| `run_ctp_shell.sh` | The same for the CTP shell runner: successor of ticket 14's `run_attempt.sh` (containment, HOME redirection, identity check, before/after hashing kept) plus the records. |
| `ctp_sql_records.py` | Turns a SQL bundle plus CTP's `main.info`/`summary.info` into a manifest, attempt records and bundle indexes; works read-only on the sealed ticket 13 bundles. |
| `ctp_shell_records.py` | Turns a shell bundle (`test_status.data`, `dispatch_tc_ALL.txt`, `.result`, `case_outcome`, evidence files) into the same three records; builds the expected side of `expected_vs_actual.txt` from the oracle table (port of `finalize_bundle.sh` revision 8). |
| `matrix_merge.py` | Merges manifests into a coverage matrix: history appended, `ever_failed` monotonic, hand-set gap kinds, caseless rows and accepted exclusions preserved verbatim, withdrawn claims never resurrected. |
| `retention.py` | Admission at the 100 GiB storage limit, retention status, triage dating of failure bundles, dry-run-by-default expiry of success-bulky bundles with protected prefixes for tickets 13, 14 and 16. |
| `validate_records.py` | Validates any ticket's manifests, attempt records, bundle indexes and matrices against ticket 12's schemas with `minischema`, plus the rules a schema cannot express. |
| `compare_records.py` | Field-by-field comparison of two records with identity-keyed alignment and a classification of every difference (prose, hash, timestamp, path, SUBSTANTIVE). |
| `activation_check_cs.sh` | Client-server counterpart of ticket 13's standalone `activation_check.sh` (same nine assertions, columns located by name), so public SQL evidence can be `proven` (user decision O2). |
| `campaign_env.sh`, `campaign_records.py`, `record_builders.py` | Shared constants (ticket 11 hashes, ports, tiers, storage), hashing, catalogue access, the schema-validated writer, identity parsing and record skeletons. |
| `selftest_matrix_merge.py` | Six synthetic checks of the merge rules (FAIL then PASS, PASS then FAIL, idempotence, verbatim preservation, hand-set gap kind, refused checker-validation attempt). |
| `declarations/*.json` | The declared case lists the manifests are proven against: ticket 13's scenario (revision 2 and revision 1), ticket 14's case, ticket 14's negative control, and two controls. The testcase repositories do not depend on these files. |

Every tool validates each record against `schemas/*.schema.json` with `tools/minischema.py` before writing it and refuses to write an invalid one (`campaign_records.write_record`). The checker `tools/check_campaign_records.py` and `tools/render_docs.py --check` still pass; `minischema.py`, `check_campaign_records.py` and `render_docs.py` were not modified.

Evidence produced here: [`evidence/ticket15/`](evidence/ticket15/) holds the four fresh invocations' records (`inv-T15-0001` to `inv-T15-0004` with their attempt records and bundle indexes; section 4), the merged [`matrix.json`](evidence/ticket15/matrix.json), a demonstration merge into a copy of ticket 13's matrix, the regenerated ticket 13 and 14 records under `regenerated/`, the control records under `controls/`, and the [field-by-field comparison](evidence/ticket15/regeneration-comparison.md). Bundles live under `/home/vimkim/.cub/campaign/cbrd-26659/ticket15/attempts/`.

## 2. Usage

The declared case list comes first. A declarations file names the repository, runner, scenario (repository-relative) and, per case, its path and requirement IDs; optionally a hand-derived assertion count with its derivation (the SQL seam has no counter), an activation checker, activation markers, resources owned and whether the case is single-session. See `tools/declarations/ticket13-public-tracer.json` and `ticket14-private-tracer.json`.

```bash
cd /home/vimkim/gh/my-cubrid-docs/cbrd-26659/campaign/tools

# one CTP SQL invocation -> manifest, attempt records, bundle indexes, packed bundle
bash run_ctp_sql.sh --declarations $PWD/declarations/ticket13-public-tracer.json --build release \
  --manifest-id inv-T18-0001 --attempt-ids att-T18-0001 --evidence-dir ../evidence/ticket18
#   options: --scenario-override DIR  --kind original|checker-validation|coexistence  --no-activation
#            --tier fast|scheduled|extended  --promotions FILE  --cap-override SECONDS (controls only)

# one CTP shell invocation
bash run_ctp_shell.sh --declarations $PWD/declarations/ticket14-private-tracer.json --build release \
  --manifest-id inv-T23-0001 --attempt-ids att-T23-0001 --evidence-dir ../evidence/ticket23 \
  --oracle ../evidence/ticket14/expected-oracle.md
#   a negative control: --scenario-override <generated dir> --kind checker-validation \
#                       --planted "<case>:<assertion>=NOK"

# records from a retained run (never writes into the bundle)
python3 ctp_sql_records.py build --bundle <bundle> --result-dir <CTP result dir> --declarations F \
  --manifest-id ID --attempt-ids a --evidence-dir DIR --read-only [--activation CASE=DIR]
python3 ctp_shell_records.py build --bundle <bundle> --declarations F --manifest-id ID \
  --attempt-ids a --evidence-dir DIR --read-only --namespace campaign_ns.sh [--oracle F]

# coverage matrix: merge manifests into an existing matrix (or start one)
python3 matrix_merge.py --manifest ../evidence/ticket18/inv-T18-0001.json \
  --existing ../evidence/ticket13/matrix.json --out ../evidence/ticket18/matrix.json

# validate any ticket's records; compare two records; retention
python3 validate_records.py ../evidence/ticket18
python3 compare_records.py hand.json regenerated.json --markdown
python3 retention.py admit --bytes 2147483648        # exit 3 = refuse to admit work
python3 retention.py status --evidence ../evidence/ticket15
python3 retention.py triage ../evidence/x/bundle-att-X.json --date 2026-09-12
python3 retention.py expire --evidence ../evidence/ticket15 [--apply]   # dry run by default
python3 selftest_matrix_merge.py
```

Attempt IDs are assigned to the declared cases in sorted name order. The wrappers refuse to overwrite an existing bundle directory, refuse to start when a campaign port is busy, when `unshare` is unavailable, when a library hash differs from ticket 11, or when `retention.py admit` says the storage limit would be reached.

## 3. Rules encoded, and where each came from

| Rule | Where encoded | Source |
|---|---|---|
| The launcher exit status is recorded, never used as proof; SQL proof reads `main.info` (`execute_case`, `success`, `fail`, `total`) and `summary.info` (`okList`, `nokList`, `notRunList`, per-case `totalTime`); `hasAnswer` is never read | `ctp_sql_records.py` | ticket 13 findings a, b, d; independent review O1 |
| A case in `notRunList` is `case-not-executed`, a failure of proof, never a pass; the manifest lists it with `outstanding.reason: prerequisite-missing` | `ctp_sql_records.py` | ticket 13 finding a; spec "Campaign manifest" |
| Declared versus repository-discovered versus CTP-discovered versus executed: `case-not-discovered`, `unexpected-case`, `case-not-executed`, `assertion-count-mismatch`, `launcher-exit-mismatch`, `setup-log-error`, `skip-recorded-as-ok`; any mismatch sets `proof.verdict` to `failure-of-proof` | both post-processors | ticket 12 section 3 |
| SQL outcome: `okList` (byte-identical result) → PASS, `nokList` → FAIL, not run → null plus outstanding; the retained answer and result are diffed again and a mismatch never records PASS | `ctp_sql_records.py` | decision 07; spec "Oracles" |
| Shell outcome: any NOK → FAIL; else the case's own `case_outcome` (PASS / SKIP with reason / UNSUPPORTED / BLOCKED); a reasoned all-SKIP run is SKIP; no OK/NOK line and no reasoned SKIP → `case-not-executed`; a skipped name that also appears as OK → `skip-recorded-as-ok` | `ctp_shell_records.py` | ticket 14 section 4, finding b; decision 07 |
| UNSUPPORTED / BLOCKED from a declaration only when a cited requirement's catalogue status says so | both post-processors | decision 07; catalogue |
| SQL assertion counts are null (`executed.assertion_count`, `assertions.executed`); the hand-derived count and derivation go into `outstanding_coverage.note`; `failed` is 1 for a FAIL (at least one) | `ctp_sql_records.py` | ticket 35 F3; schemas document section 11 |
| Shell assertion counts are measured: `^<case>-[0-9]+ : (OK\|NOK)`; SKIP lines share the numbering and are never OK | `ctp_shell_records.py` | ticket 14 finding a |
| `configurations_not_run` = the 12-combination domain minus what the CTP case ran in this invocation | `campaign_records.configurations_not_run` | ticket 35 F4 (adopted by ticket 34) |
| `requirements_without_executed_case` = catalogue requirements with status assertable or observation-only not cited by an executed case | both post-processors | inv-T14-0003 (50 entries); see finding (b) in section 6 |
| Every executed attempt gets an attempt record and a bundle index; kind original also a manifest; checker-validation and coexistence attempts get no manifest and never reach the matrix | post-processors, `matrix_merge.py` | ticket 35 F6; ticket 34 F4; schemas document section 11 |
| SQL activation evidence: `proven` only when the checker ran in the case's own run mode; `reused` needs a declared applicability block; otherwise `missing` | `record_builders.read_activation` | user decision O2 (ticket 35); ticket 12 section 3 |
| Shell activation evidence: `proven` only for a PASS whose declared activation markers all match this run's own evidence; a SKIP never has proven evidence; recovery-log observations under channel `other` with a reference | `ctp_shell_records.py` | ticket 14 section 4; ticket 34 F1; ticket 14 section 10 request 4 |
| Matrix: keyed by requirement and (case, page size, build mode, run mode, instrumentation); history appended, `ever_failed` monotonic, a later pass never erases a failure, idempotent | `matrix_merge.py` | ticket 12 section 3; decision 07 |
| Matrix: `accepted_exclusions` never written; caseless rows (`case: null`) hand-maintained and preserved verbatim; `known_issue`, `attribution`, `deterministic_claim`, `consecutive_fresh_fixture_reproductions` preserved | `matrix_merge.py` | spec "Review, sign-off"; ticket 34 delta review |
| Matrix: `gap_kind: none` only for a latest PASS with proven or reused evidence; the qualified rule (a row is not `none` when a clause is evidenced solely by a checker outside every executed suite; `OOS-SQL-01` keeps `none`) is a judgement on the requirement's text, so a hand-set gap kind is preserved and never upgraded to `none`; a row that stops being a proven/reused PASS loses `none` | `matrix_merge.py` | ticket 12 section 2; ticket 13 report section 8 at docs commit f164879 |
| Matrix: a `<REQ>/-/claim-withdrawn` caseless row keeps manifests that still cite REQ from resurrecting case rows | `matrix_merge.py` | ticket 34 F2 (OOS-REP-07) |
| Replay bundle: fourteen items, each present / missing / not-applicable with a note; `complete` iff nothing is missing; `SHA256SUMS` of every file in bytewise path order; bundle hash = sha256 of that file | `campaign_records.bundle_hash`, post-processors | spec "Outcomes, replay and minimization"; decision recorded in section 9 |
| Retention: PASS → success-bulky, expires in 7 days; non-PASS → failure, held through triage, `retention.py triage` sets triage + 30 days; a checker-validation attempt that FAILed as required is success-bulky; minimized reproducers kept; admission refused at 100 GiB; expiry deletes only expired unheld success-bulky bundles under unprotected prefixes and nulls the attempt record's `bundle` | `record_builders.retention_for`, `retention.py` | decision 08; spec "Execution tiers" |
| Containment: every CTP invocation and the activation checker run under `campaign_ns.sh`; ports 26659/33120/33121/33122 verified free; library hashes verified against ticket 11; `$CUBRID/conf` and `databases` backed up, hashed before and after, restored; HOME redirected for shell runs; the scenario tree hashed before and after and restored (`.result` files copied out, pre-existing ones put back) | wrappers, `campaign_env.sh` | ticket 14 section 2 and finding c; ticket 11 section 2; ticket 13 section 11 |
| The CTP tree and the JDK are pinned (`/home/vimkim/CTP`, the tree tickets 13 and 14 ran and fingerprinted), never inherited from the environment; `runner.ctp_fingerprint` is the sha256 of the runner jar in the tree recorded in `identity.txt` (`ctp_home=`), not of an assumed path | `campaign_env.sh`, `campaign_records.ctp_fingerprint` | this ticket, finding (g) in section 6: the login environment carries `CTP_HOME=/home/vimkim/gh/ctp/run-sql/CTP`, a second CTP checkout with different jars |
| Caps: the tier's invocation cap is enforced with `timeout`; a killed launcher is `invocation_cap_reached`, its declared cases become `outstanding.reason: cap-reached`, and the proof fails; the per-case cap is judged from the measured case time (a case over it never records PASS) | wrappers, post-processors | decision 08; ticket 14 section 5 and section 10 request 2 |

Two deviations from the predecessors, recorded rather than hidden. The SQL configuration generated by `run_ctp_sql.sh` sets `ha_port_id` and `MASTER_SHM_ID` to the campaign's 33122 where ticket 13's `sql_cbrd26659.conf` had `ha_port_id = 59901`, so that every port a master could open is a campaign-allocated one. And the oracle-table parser recognises only the "release build" / "debug build" skip conditions, exactly as `finalize_bundle.sh` revision 8 does: on a build without `SHOW HEAP OOS`, assertions 5 and 16 would compare as expected OK versus actual SKIP and the verdict would be a conservative MISMATCH, never a false MATCH; the outcome mapping is unaffected because a MISMATCH only ever forces a PASS down to FAIL, and such a run is SKIP by its `case_outcome` anyway (ticket 34's documented limit).

## 4. Fresh invocations through the wrappers

All on the pinned unmodified release install, 16 KiB pages, client-server, under `campaign_ns.sh`; every run left the install (`conf`, `databases`), the user's `~/.CUBRID_SHELL_FM` and the testcase worktree byte-identical (drift lines 0 everywhere; `git status --short` empty in both worktrees afterwards). The first pair ran the CTP tree the login environment pointed at (finding g, section 6); the second pair repeated them with the pinned tree `/home/vimkim/CTP`, the one tickets 13 and 14 ran, and is the pair compared with the hand-written records below.

| Manifest | Suite | CTP tree | Launcher | Result | Assertions | OOS-path evidence | Proof |
|---|---|---|---|---|---|---|---|
| `inv-T15-0001` / `att-T15-0001` | ticket 13's scenario `sql/_36_guava/cbrd_26659` (commit `e64c16481`) | `run-sql` (`926a1a6c…`) | CTP SQL, 39 s, exit 0; case 60 ms | PASS, result byte-identical to the answer | null (no counter); declared 27 in the note | **proven** by `activation_check_cs.sh` client-server under the namespace, nine of nine, `Oos_recs_sumlen 3024` | proven, 0 mismatches |
| `inv-T15-0002` / `att-T15-0002` | ticket 14's case `cbrd_26659_oos_dur01` (commit `c4fe45173`) | `run-sql` (`862fa83b…`) | CTP shell, 16 s, exit 0; case 12 s | PASS (`case_outcome PASS`) | 17 executed, 17 OK, 0 NOK, 1 SKIP (#18, release build) | **proven**: all four declared markers matched (`has_oos=1 chunks=4`, `recovery OK pages=2 records=83`, `after_recovery chunks=5`, `REDO Phase is started`), channel `other` | proven, 0 mismatches |
| `inv-T15-0003` / `att-T15-0003` | same scenario | pinned `/home/vimkim/CTP` (`456cabff…`, ticket 13's) | CTP SQL, 44 s, exit 0; case 51 ms | PASS | null; declared 27 | **proven**, client-server, nine of nine | proven, 0 mismatches |
| `inv-T15-0004` / `att-T15-0004` | same case | pinned `/home/vimkim/CTP` (`e7c8ef04…`, ticket 14's) | CTP shell, 17 s, exit 0; case 11 s | PASS | 17 executed, 17 OK, 0 NOK, 1 SKIP | **proven**, all four markers, channel `other` | proven, 0 mismatches |

All four bundles are `complete: true`, class `success-bulky`, expiring 2026-09-18. The merged [`evidence/ticket15/matrix.json`](evidence/ticket15/matrix.json) has four case rows (`OOS-REP-01`, `OOS-REP-02`, `OOS-SQL-01` with history `att-T15-0001`, `att-T15-0003`; `OOS-DUR-01` with `att-T15-0002`, `att-T15-0004`), all PASS with proven evidence and therefore `gap_kind: none` under the schema rule, each SQL row carrying the generated summary that asks the author to scope it under the qualified rule. The demonstration merge of the two SQL manifests into a copy of ticket 13's matrix ([`matrix-demo-ticket13-plus-T15-sql-runs.json`](evidence/ticket15/matrix-demo-ticket13-plus-T15-sql-runs.json)) shows the rules in practice: `att-T15-0001` and `att-T15-0003` appended as the third and fourth history entries of the three case rows (`flakiness.attempts` 4), `run` moved to `inv-T15-0003`, the hand-set `Delivery gap` on `OOS-REP-01` and `OOS-REP-02` preserved with their summaries, `OOS-SQL-01` still `none`, and the four caseless rows untouched in place.

## 5. Regeneration of tickets 13 and 14's records (criterion 7)

What was regenerated, from what, read-only on the sealed bundles:

| Record | Inputs | Result |
|---|---|---|
| `inv-T13-0001`, `att-T13-0001`, `bundle-att-T13-0001` | bundle `attempts/att-T13-0001` (identity.txt, timing.txt, ctp.log, conf, workload, expected.answer, candidate.result) + CTP result dir `1020240166` + the revision-1 declaration (15 assertions) + revision 2's checker output `check-release/` as the activation evidence | proven, PASS, evidence reused |
| `inv-T13-0002`, `att-T13-0002`, `bundle-att-T13-0002` | bundle `attempts/att-T13-0002` + result dir `1020415767` + `check-release/` | proven, PASS, evidence reused (the checker ran standalone) |
| `inv-T14-0003`, `att-T14-0029`, `bundle-att-T14-0029`; `inv-T14-0004`, `att-T14-0030`, `bundle-att-T14-0030` | the `run_attempt.sh` bundles under `ticket14/attempts/` and `expected-oracle.md` section 5 | proven, PASS, 17 and 18 measured assertions, evidence proven |
| `att-T14-0031`, `bundle-att-T14-0031` | bundle `att-T14-0031`, `--kind checker-validation --planted …=NOK` | FAIL, as the control must; expected-versus-actual MATCH with the planted NOK |
| matrices | ticket 13's and ticket 14's manifests re-merged into the existing hand-written matrices | **identical** (253 and 127 identical leaves, 0 differing) |

The full field-by-field tables are in [`evidence/ticket15/regeneration-comparison.md`](evidence/ticket15/regeneration-comparison.md). Summary of the leaf classes (identity-keyed alignment; the differing hash, timestamp and path classes are by construction: the bundle-hash convention, `created_at`, and evidence homes):

| Record pair | identical | prose | hash | timestamp | path | SUBSTANTIVE |
|---|---:|---:|---:|---:|---:|---:|
| `inv-T13-0001` | 74 | 9 | 1 | 0 | 4 | 4 |
| `att-T13-0001` | 38 | 7 | 1 | 0 | 1 | 2 |
| `bundle-att-T13-0001` | 47 | 14 | 2 | 2 | 2 | 1 |
| `inv-T13-0002` | 75 | 9 | 1 | 0 | 4 | 3 |
| `att-T13-0002` | 38 | 7 | 1 | 0 | 1 | 2 |
| `bundle-att-T13-0002` | 47 | 14 | 2 | 2 | 2 | 1 |
| `inv-T14-0003`, `inv-T14-0004` | 76, 77 | 10, 9 | 2, 2 | 0 | 4 | **0** |
| `att-T14-0029`, `att-T14-0030` | 39, 40 | 7, 6 | 1 | 0 | 2 | **0** |
| `bundle-att-T14-0029`, `-0030` | 53, 53 | 15 | 0 | 1 | 0 | 1 (total_bytes) |
| `att-T14-0031`, `bundle-att-T14-0031` | 37, 48 | 4, 16 | 1 | 0, 2 | 2, 1 | 1, 1 |

Every substantive difference, and what it is:

| # | Field | Hand-written | Regenerated | Kind |
|---|---|---|---|---|
| S1 | `inv-T13-000x.answer_promotions` | one `promoted` entry | `[]` | Design: a promotion is a reviewer's act (rename after review). The tool records only what the run shows: `candidate` when the answer was empty, `retained-as-failure-evidence` on a FAIL against a reviewed answer; `promoted` entries are supplied by the reviewer through `--promotions FILE`. Not a disagreement. |
| S2 | `inv-T13-0001…applicability.source_manifest` | `inv-T13-0002` | `inv-T13-0001` | Regeneration input: the revision-1 run's evidence is revision 2's checker output, which the hand-written record says truthfully; the tool was handed that output as if the checker had run in the regenerated invocation and cannot know otherwise. Not a disagreement about the run. |
| S3 | `invocation.resources.storage_gib` | 0.5 | 0.01 | Semantics undefined by the schema: ticket 13 recorded the whole storage root's usage, the tool records what the invocation wrote. Decision request D5. |
| S4 | `requirements_without_executed_case` | 43 entries | 48 entries | **Finding (b)**: ticket 13 excluded the five observation-only requirements, ticket 14 (`inv-T14-0003`, 50 entries) included them; the two hand-written manifests apply different rules. The tool follows ticket 14's reading (an observation-only requirement still needs an executed case that records the observation; excluding it would hide a Delivery gap). |
| S5 | `att-T13-000x.cleanup.scope_verified` | `true` | `false` | **Finding (c)**: ticket 13 ran CTP unconfined and argued after the fact from the `Operation not permitted` lines that nothing unrelated was killed. The tool sets `scope_verified` only when the invocation ran under `campaign_ns.sh` and the install and worktree hashes show zero drift; a post-hoc log reading does not meet the field's description "checked to touch only resources_owned". A judgement call on the hand-written value, recorded, not overwritten. |
| S6 | `att-T13-0002.resources_owned.ports` | `[26659, 33120, 33122]` | `[26659, 33120, 59901]` | **Finding (a)**: 33122 in ticket 13's configuration was `MASTER_SHM_ID`, a shared-memory key, not a port; the configured `ha_port_id` was 59901, which `att-T13-0001` lists. `att-T13-0002` mislabels the key as a port and disagrees with its sibling record. |
| S7 | `bundle-att-T13-000x.uncommitted_snapshots` | `[]` | the pinned `OOS-CONTEXT.md` snapshot | Ticket 14's bundle indexes list the snapshot (the pinned wording exists only in the uncommitted working copy, ticket 11 section 3); ticket 13's do not. The tool always lists it. Minor inconsistency between the hand-written records. |
| S8 | `bundle-att-T14-00xx.total_bytes` | `du -sb` (676,012; 768,138; 336,698,606) | sum of regular file sizes (659,535; 751,661; 336,664,766) | Convention: `du -sb` includes the directory entries' apparent sizes, which depend on the filesystem. The tool sums file sizes (ticket 13's convention: 46,360 reproduced exactly). |
| S9 | `att-T14-0031.manifest_id` | "none: checker validation is not an invocation…" | "none: checker-validation attempts have no manifest…" | Wording of the same `none` sentinel. |
| S10 | `bundle-att-T14-0031.retention.class` | `success-bulky` | `success-bulky` after this ticket's rule | Ticket 14 classed the negative control's bundle success-bulky because an expected FAIL is the checker working; the tool first wrote `failure`, then encoded that rule (`retention_for`): a checker-validation attempt that FAILed is success-bulky, one that PASSed is the failure that needs triage. Agreement after the rule was made explicit. |

Hash conventions, verified rather than assumed: ticket 13's bundle hashes (`59c49a51…`, `00c906fa…`) are the sha256 of the sealed `SHA256SUMS` files, whose per-file lines are identical as a set to what the tool computes; the aggregates differ only because ticket 13 listed files in locale order and the tool in bytewise order. Ticket 14's hashes (`292844d4…`, `3f5256fe…`, `314ab1f6…`) reproduce exactly with `find | sort | xargs sha256sum | sha256sum` under `LANG=en_US.UTF-8` and not under `LC_ALL=C`, so the bundles are unchanged and that convention is locale-dependent as well as path-dependent, which is why this ticket does not adopt it (section 9, D1).

The fresh pinned-tree runs compared with the latest hand-written records (section C of the comparison file: `inv-T15-0003` against `inv-T13-0002`, `inv-T15-0004` against `inv-T14-0003`, and their attempt records and bundle indexes) differ only in identities, timestamps, the promotion entry, the observation-only rule (S4), `storage_gib` (S3), `total_bytes` (S8) and, for the SQL run, `oos_evidence.status` `reused` → `proven` with `applicability` null: the checker ran client-server in the case's own run mode, which is what user decision O2 asked for. Section D of the same file sets the first fresh runs against the re-runs: apart from identities, timestamps and case times, the only differing fields are hashes of regenerated files, among them `runner.ctp_fingerprint`, the one field the CTP tree changed (finding g); outcomes, evidence, proof and counts are the same on both trees.

## 6. Findings for the coordinator

- **(a)** `att-T13-0002.json` `resources_owned.ports` lists 33122, which is the configuration's `MASTER_SHM_ID` (a System V shared-memory key), not a port; `att-T13-0001.json` lists the configured `ha_port_id` 59901 for the same configuration. One of the two should change; the tooling derives ports from `cubrid_port_id`, `BROKER_PORT` and `ha_port_id`.
- **(b)** `inv-T13-0001/0002` exclude the five observation-only requirements from `requirements_without_executed_case` (43 entries); `inv-T14-0003/0004` include them (50). The manifests state no rule for this choice. The tooling includes them and states its rule in the note; if the coordinator prefers ticket 13's reading, `campaign_records.assertable_requirement_ids` is the one place to change.
- **(c)** `att-T13-0001/0002` record `cleanup.scope_verified: true` for invocations that ran without containment; the claim rests on EPERM lines read after the fact. The tooling's stricter rule yields `false` for those runs. Whether ticket 13's value should stand is a judgement for the coordinator; nothing was edited.
- **(d)** Ticket 13's bundle indexes omit the pinned `OOS-CONTEXT.md` snapshot from `uncommitted_snapshots`; ticket 14's list it. Minor.
- **(e)** The two hand-written bundle-hash conventions are both order-sensitive in ways that make a hash non-reproducible by a reader with another locale or another mount point (section 5). Decision request D1.
- **(f)** Confirmed again on three fresh CTP SQL runs (`inv-T15-0001`, `C01`, `C02`): `summary.info` carries `<hasAnswer>false</hasAnswer>` whether the answer exists and matches, exists and mismatches, or is absent (finding d of the ticket 13 report holds; the tool never reads it).
- **(g) Two CTP trees exist on this host, and the first version of this tooling ran the wrong one.** The login environment exports `CTP_HOME=/home/vimkim/gh/ctp/run-sql/CTP`; `/home/vimkim/CTP`, which tickets 13 and 14 ran and fingerprinted, is a different checkout (`cubridqa-cqt.jar` `456cabff…` against `926a1a6c…`, `cubridqa-shell.jar` `e7c8ef04…` against `862fa83b…`, `shell/init_path/init.sh` differs too; `sql/bin/run.sh` and `bin/ctp.sh` are identical). `campaign_env.sh` first read `CTP_HOME=${CTP_HOME:-/home/vimkim/CTP}`, so `inv-T15-0001`, `inv-T15-0002` and controls C01 to C05 ran the `run-sql` tree while their manifests fingerprinted the `/home/vimkim/CTP` jar. Caught when the fresh SQL run's result directory turned up under `/home/vimkim/gh/ctp/run-sql/CTP/sql/result/` instead of `/home/vimkim/CTP/sql/result/`. Fixed in two places: the wrappers pin the tree (override only through `CAMPAIGN_CTP_HOME`, recorded), and the fingerprint is computed from the `ctp_home` line of `identity.txt`. The affected records were rebuilt from their bundles and now carry the truthful fingerprint (`926a1a6c…` / `862fa83b…`) and a producer note; the two campaign invocations were then repeated with the pinned tree as `inv-T15-0003` and `inv-T15-0004` (section 4), so that the fresh-run comparison with tickets 13 and 14 is like for like. The controls stand as run: their conclusions are about the tooling's mapping, not about a CTP version. Lesson for tickets 18 to 32: a manifest field that says "nothing is inherited from the environment" has to be earned by the wrapper, and a fingerprint must be taken from the artifact that ran.

## 7. Controls (criteria 2 and 3; ticket 22 will need these)

| Control | What was done | What the tooling recorded | Record |
|---|---|---|---|
| R01, retained | The answerless CTP run of ticket 13's finding a (result dir `1020205027`, `notRunList`, `execute_case:0`, launcher exit 0) post-processed from a bundle assembled from `att-T13-0001`'s bootstrap log, identity and configuration | `proof.verdict: failure-of-proof`, mismatch `case-not-executed`, case outcome null with `outstanding.reason: prerequisite-missing`; no attempt record | `controls/inv-T15-R01-answerless.json` |
| C01, fresh (39 s) | A copy of ticket 13's scenario under the ticket 15 storage without its `.answer`, and a declaration naming a second, non-existent case | **3 mismatches**: `case-not-discovered` (the phantom case is neither in the tree nor in CTP's summary), `case-not-executed` (the real case in `notRunList`, `shouldRun=false`, `isSuccessFul=true`), `case-not-discovered` (`main.info total=1` against 2 declared); `executed.case_count 0`; both cases outstanding; the launcher exited 0 | `controls/inv-T15-C01-answerless.json` |
| C02, fresh (39 s) | Ticket 13's planted digest defect (one hex digit of `big_md5`, `56d1d803…` → `56d2d803…`) as a `--kind checker-validation` run | CTP `nokList` → outcome **FAIL**; `expected_vs_actual.diff` shows the one differing line (23); no manifest (checker validation); bundle success-bulky (expected FAIL) | `controls/att-T15-C02.json`, `bundle-att-T15-C02.json` |
| C03, fresh (16 s) | Ticket 14's `make_negative_control.sh` output generated under the ticket 15 storage, run as checker validation with `--planted recovered_value_id2_multi_chunk_oos=NOK` | 17 executed, 16 OK, **1 NOK** (#13) → **FAIL**; `case_outcome FAIL`; expected-versus-actual MATCH against the oracle with the planted expectation; evidence `not-applicable` (a control certifies the checker, not the requirement) | `controls/att-T15-C03.json` |
| C04, fresh (7 s) | A synthetic shell case (`t15_skip_only.sh`, under the ticket 15 storage, never in the repository) writing only SKIP lines with reasons and `case_outcome SKIP`; CTP counts it as `Success 1` | outcome **SKIP** with the reason, 0 executed assertions, evidence `missing`, proof proven (nothing was misrepresented), bundle class `failure` held through triage; never PASS | `controls/inv-T15-C04-skiponly.json`, `att-T15-C04.json` |
| C05, fresh (14 s) | Ticket 13's scenario with `--cap-override 12`: the wrapper's `timeout` killed the launcher during setup (exit 124), the namespace tore the started master and broker down | `invocation_cap_reached: true`, `caps.invocation_seconds: 12`, **failure of proof** with 4 mismatches (`launcher-exit-mismatch` 124, `setup-log-error` "no result directory", two `case-not-discovered`), the case outstanding with `reason: cap-reached`; install and worktree drift 0 | `controls/inv-T15-C05-capreached.json` |
| Matrix self-test | `selftest_matrix_merge.py`: FAIL then PASS; PASS then FAIL; idempotence; verbatim exclusions and caseless row; hand-set gap kind; refused checker-validation attempt | 15 of 15 checks pass | run output in the ticket's Answer |
| Retention self-test | Two throwaway bundles (expired success-bulky, failure) under the ticket 15 storage: `expire` dry run, `expire --apply`, `triage`, `status` | dry run lists the expired bundle only; `--apply` deletes it, nulls the attempt record's `bundle`, marks the index; the failure bundle is untouched; `triage` sets expiry to the date plus 30 days; the ticket 13/14/16 bundles are reported as PROTECTED and never deleted | transcript in the ticket's Answer; fixtures removed afterwards |

Also verified along the way: the wrapper refused nothing it should have accepted (admission at 26.8 GiB used of 100 GiB), and `retention.py admit --limit-gib 10` returns exit 3 with "REFUSED: stop admitting work; nothing is deleted".

## 8. Timings (for ticket 17)

| Invocation | Wall (started_at to ended_at) | Launcher | Case | Notes |
|---|---:|---:|---:|---|
| `inv-T15-0001` SQL, release, 1 case (run-sql tree) | 47 s | 39 s | 60 ms | plus 7 s for the client-server activation checker (createdb, server start, three phases, stop, checkdb) |
| `inv-T15-0003` SQL, release, 1 case (pinned tree) | 52 s | 44 s | 51 ms | plus 7 s activation checker |
| `inv-T15-0002` shell, release, 1 case (run-sql tree) | 17 s | 16 s | 12 s | HOME redirection and hashing add about 1 s |
| `inv-T15-0004` shell, release, 1 case (pinned tree) | 17 s | 17 s | 11 s | |
| C01 SQL answerless | 40 s | 39 s | 0 (not run) | the CTP fixed cost is paid even when nothing executes |
| C02 SQL planted defect | 40 s | 39 s | 57 ms | |
| C03 shell negative control | 17 s | 16 s | 11 s | |
| C04 shell SKIP-only | 7 s | 7 s | 0 s | the shell seam's harness floor |
| C05 SQL cap at 12 s | 14 s | 12 s + 2 s teardown | none | evidence collected and install restored after the kill |

The SQL seam's cost is per invocation (39 to 44 s of CTP setup and teardown for one case, in line with ticket 13's 39 s), so batching cases into one invocation stands as ticket 13 advised; the activation check adds about 7 s per checked case. The shell case's 11 to 12 s match ticket 14's revision-8 figures (11 s release). Storage after all runs: about 0.5 GiB under the ticket 15 storage (bundles, of which the negative control's preserved database image is most; the activation databases 227 MiB); CTP's per-run install snapshot in the redirected HOME (about 430 MiB per shell run) is deleted by the wrapper after the hashes are taken.

## 9. Decision requests (recorded, not decided)

- **D1 Bundle-hash convention.** This ticket uses sha256 of a `SHA256SUMS` listing every file in bytewise (`LC_ALL=C`) path order; ticket 13 used the same shape in locale order, ticket 14 used `find | sort | xargs sha256sum | sha256sum` (locale- and path-dependent). Ticket 12 should fix one convention in the schemas document; existing hashes stay as recorded.
- **D2 `recovery-log` evidence channel.** Recorded under `other` with a reference, as ticket 34 did; ticket 12's decision (ticket 14 section 10, request 4).
- **D3 Cap enforcement and the outcome of a killed attempt.** The wrapper enforces the invocation cap with `timeout` and captures evidence (C05); the per-case cap is measured, not enforced, because CTP enforces its own timeout with a kill that destroys a crash case's evidence (ticket 14 section 5). A case that was running when the cap fired has no outcome in this tooling (it is outstanding `cap-reached`); the schema allows only FAIL or BLOCKED for an attempt whose deadline was reached, and which of the two a terminated attempt should carry is undecided (ticket 14 section 10, request 2).
- **D4 `assertions.failed` on the SQL seam.** The schema requires an integer; the SQL runner reports no per-assertion count, so a FAIL carries 1 ("at least one"). A nullable `failed`, as `executed` already is, would be honest.
- **D5 `invocation.resources.storage_gib`.** The schema does not say whether it is the campaign's storage cap, the storage root's usage or the invocation's footprint; ticket 13 wrote usage of the root (0.5), the tool writes the invocation's footprint.
- **D6 Untriaged FAIL classification.** The gap-kind enum has no "under triage" value; a FAIL with unknown attribution is written as `Delivery gap` with an UNTRIAGED marker in the summary, never as `Engine defect` (decision 07). Ticket 12 may want an explicit value.
- **D7 Withdrawn claims.** The merge recognises a caseless `<REQ>/-/claim-withdrawn` row by its id. An explicit matrix field would be cleaner than a naming convention.
- **D8 Evidence directory for multi-case shell invocations.** The case honours `OOS_CAMPAIGN_EVIDENCE_DIR` and refuses a non-empty one, so a multi-case invocation cannot set it; the wrapper then collects `<case dir>/*_evidence` afterwards. A root-plus-case-name convention (`OOS_CAMPAIGN_EVIDENCE_ROOT/<case>`) in tickets 23 to 32's cases would remove the special case.
- **D9 Observation-only requirements in `requirements_without_executed_case`** (finding b).
- **D10 Recording promotions.** `promoted` entries are hand acts recorded through `--promotions`; whether the tooling should verify the rename (answer hash equals the retained candidate hash) and write the entry itself is open.
- **D11 Which CTP tree is the campaign's.** This tooling pins `/home/vimkim/CTP` because tickets 13 and 14 ran and fingerprinted it; the user's login environment points at `/home/vimkim/gh/ctp/run-sql/CTP`, whose jars and `init.sh` differ (finding g). The campaign should say which tree is pinned, in ticket 11's record or ticket 12's contract, and whether the runner jars' hashes belong beside the engine hashes in the identity checks.

## 10. Capability gaps and limits of the tooling

- The SQL seam still has no assertion counter; counts stay null (ticket 35 F3). Nothing here manufactures one.
- The tool cannot judge clause coverage of a requirement's statement; the qualified gap-kind rule is applied by hand on the row and preserved by the merge (section 3).
- Ports are allocated, not isolated (an unprivileged namespace cannot bring up loopback); two campaign invocations cannot run at once, and ticket 16's ports (26671, 33140 to 33142) are a separate allocation the wrappers never check or use.
- CTP's result directories (`<CTP_HOME>/sql/result/y2026/m9/…` and `<CTP_HOME>/result/shell/current_runtime_logs`) are CTP's own state: the wrappers copy them into the bundle (`ctp_result/`, `ctp_runtime_logs/`) but do not clean them, and the shell runtime log directory is overwritten by every shell run (CTP's behaviour, as under ticket 14).
- The activation checker for the public seam is specific to the ticket 13 fixture; tickets 18 to 22 write their own checkers with the same contract (an `assertions.txt` ending in `RESULT: activation proven`, an `identity.txt` with `run_mode=`), named in their declarations.
- Instrumented runs (ticket 16) are not exercised: `instrumentation` stays null and `injection_acknowledgements` not-applicable; the declarations format has no injection block yet.

## 11. Ticket 15 criteria checklist

| Criterion | Status | Where |
|---|---|---|
| One wrapper per CTP runner produces a manifest per invocation under ticket 12's schema; the suites stay runnable by CTP alone | met | `run_ctp_sql.sh`, `run_ctp_shell.sh`; section 4; both worktrees unchanged (`git status` clean, tree hashes identical) |
| Expected identities and counts (declared case list) compared with discovered and executed cases and assertion counts; mismatches are failures of proof, never PASS | met | section 3 rules; controls R01, C01, C05 (section 7) |
| Fixed outcome mapping onto PASS, FAIL, SKIP, UNSUPPORTED, BLOCKED; a skip, an unfired hook or an unreached phase never maps to PASS | met | section 3; controls C02 (FAIL), C03 (NOK → FAIL), C04 (SKIP, not PASS); UNSUPPORTED/BLOCKED from declarations against the catalogue status |
| Matrix aggregation by requirement ID; a later pass never erases a failure; flakiness, attribution, known-issue preserved; exclusions only ever added by hand | met | `matrix_merge.py`; self-test 15/15; re-merge of both hand-written matrices identical; demonstration merge |
| Replay-bundle packing of the spec's contents with each missing item recorded as missing | met | fourteen items per index, `complete` iff nothing missing; `validate_records.py` checks present paths and hashes against the bundle |
| Retention rules applied; storage under the campaign's home location; the tooling stops admitting work at the limit | met | `retention.py`, `retention_for`; admission check before every launcher; self-test (section 7) |
| Verified by regenerating tickets 13 and 14's records from their runs and matching the hand-written manifests and matrix rows in substance | met | section 5: ticket 14 manifests and attempt records with zero substantive differences, both matrices identical after re-merge; ticket 13's differences enumerated and explained (S1 to S7) |
| Tooling and usage notes committed in the docs repository campaign folder | met | docs commits listed in the ticket's Answer |

## 12. Hand-offs

- **Tickets 18 to 22 (public SQL):** write one declarations file per scenario (requirement IDs per case, hand-derived assertion count with its derivation, an activation checker with the `activation_check_cs.sh` contract) and run `run_ctp_sql.sh`; batch cases per invocation. Bootstrap every new case with an empty `.answer` (finding a of ticket 13): the tool records the first run as a `candidate` and refuses to call a `notRunList` case a pass. After the reviewer promotes by rename, record the promotion through `--promotions`. Apply the qualified gap-kind rule by hand on the row; the merge keeps it.
- **Ticket 22 (fast regression invocation):** the failure-of-proof behaviour it needs is demonstrated by C01 and C05; the whole fast tier should be one invocation per seam (section 8).
- **Tickets 23 to 32 (private shell):** write the case's activation markers into the declarations (a regex the case's own journal or evidence file must match), write `case_outcome`, honour `OOS_CAMPAIGN_EVIDENCE_DIR`, and consider D8 for multi-case buckets. Negative controls run with `--kind checker-validation --planted …`. Crash cases keep the recovery-log excerpt as the reference file.
- **Ticket 16 (instrumentation):** the declarations format needs an `injections` block and the wrappers an `--instrumentation` identity before instrumented runs can be recorded; nothing here touches ticket 16's worktree or ports.
- **Ticket 17 (timings):** section 8.
- **Ticket 33 (final report):** `validate_records.py` over every evidence directory and `matrix_merge.py` over every manifest of kind original are the two commands the campaign matrix is built from; caseless rows and exclusions are hand-maintained and survive the merge.
- **Ticket 12 (contract):** decision requests D1 to D10.

## 13. What touched shared state

Every CTP invocation ran inside `campaign_ns.sh`. The pinned release install's `conf` and `databases` were backed up and restored on every run and hashed before and after (drift 0 in all nine runs); the user's `~/.CUBRID_SHELL_FM` was neither read nor written (drift 0); both testcase worktrees are clean and their scenario trees hash identical before and after (the `.result` file ticket 13 left in the public worktree was put back as found). CTP left result directories of its own: four SQL result directories under `/home/vimkim/gh/ctp/run-sql/CTP/sql/result/y2026/m9/` (the first runs and the controls, finding g) and one under `/home/vimkim/CTP/sql/result/y2026/m9/` (`inv-T15-0003`), and it rewrote `<CTP_HOME>/result/shell/current_runtime_logs/` on every shell run, as it does under every runner. No process outside the namespaces was signalled; `pgrep -u $USER -a cub_` shows only processes of other installs (a `develop`-era master pair, `cub_server demodb`, `cub_pl c16k`) that were running before and after. Storage: about 0.5 GiB under `/home/vimkim/.cub/campaign/cbrd-26659/ticket15/`.
