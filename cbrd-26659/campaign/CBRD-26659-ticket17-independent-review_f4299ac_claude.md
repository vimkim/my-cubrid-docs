# CBRD-26659 — Independent review of ticket 17, representative timings and tier placement

> Reviewed: 2026-09-18 (KST), on `dev2`. Engine baseline `f4299ac0cd777a2a964c1f197ae5ebf9841a4936`, re-pinned without the unit-test seams by ticket 41; normative context `f6543de` + sha256 `c9daf3c4…`; requirement catalogue sha256 `0cc33c82…`.
> Reviewer: Claude Opus 5, in a session that authored none of the artifacts under review and that reached the ticket, the specification and the evidence as primary sources rather than through the author's account of them.
> Subject: docs commit `b990220` — the record [`CBRD-26659-representative-timings-tier-placement_f4299ac_claude.md`](CBRD-26659-representative-timings-tier-placement_f4299ac_claude.md), the evidence under [`evidence/ticket17/`](evidence/ticket17/), the eleven tools it adds under [`tools/`](tools/), and the four retained replay bundles under `/home/vimkim/.cub/campaign/cbrd-26659/ticket17/attempts/` with the probe outputs beside them. Commit `aeeb75c`, immediately before it, is unrelated user work and is not under review.
> Satisfies: the [campaign specification](/home/vimkim/gh/cb/CBRD-26659-oos-testcases-handover/.scratch/oos-adversarial/spec.md) section *Review, sign-off and deferral* — "An independent agent session, never the authoring session, reviews Standards and Spec conformance per repository, validates the negative-control checkers, and audits replay and cleanup evidence before acceptance" — for ticket 17, in all three of its obligations. It does **not** discharge ticket 33, the whole-campaign acceptance review.

Vocabulary follows the [docs glossary](../../CONTEXT.md).

## Verdict

**REVISE. The measurement work is sound and unusually well grounded: every load-bearing number in the record was re-derived here from the retained bundles, probe outputs and logs, and all of them reproduce — 57 bundles, the two seams' cost shapes, the twelve configuration cells against the live install binaries, both seed counts, the resource peaks and the storage figures. Two findings block. The first is the serious one: a multi-session barrier scenario *does* exist in the private suite, so criterion 1's central disclosure — "it does not exist in either suite" — is wrong, and the placement row ticket 23 inherits is derived where it could have been measured. The second is a regression against a contract the campaign settled two days earlier.**

| | |
|---|---|
| Ticket criteria | 5 of 6 met; criterion 1 **not met as disclosed** (four of five scenarios timed soundly, the fifth's gap misdiagnosed — F1) |
| Negative controls | 2 new checkers, both validated by re-execution: 3 of 3 planted mutations of `config_domain.py` caught by the right check, 4 of 5 planted mutations of `tier_placement.py` caught — **one escapes (F3)**; 2 of 4 planted artefact defects escape `config_domain.py check` (F4) |
| Replay and cleanup evidence | bundles sound — `sha256sum -c` clean on all four (49/212/61/63 files), `SHA256SUMS-bulky.txt` 1,328 of 1,328 verify, every index `complete`, no item wrongly `present`, drift independently re-diffed and zero on all four invocations. **8 of 12 recorded bundle digests and sizes verify against nothing (F2)** |
| Load-bearing numbers | every one re-derived from the artifacts and reproducing; three prose numbers do not hold (F6) |
| Record contract | no schema was edited, so nothing was owed to the change log; the tooling rules are honoured (probes write no manifest; `assertions` null for the SQL seam and measured integers for the shell seam; no promotion written) — except the bundle convention, F2 |
| Blocking findings | F1 (the barrier scenario exists), F2 (stale bundle digests and sizes, against the ticket 44 F3 decision) |
| Non-blocking findings | F3 (the seed arithmetic has no negative control), F4 (`config_domain.py` never verifies the binaries it says prove the cell), F5 (`invocation_measured_seconds` is a composite in five rows), F6 (three numbers), F7 (two wrong citations, the only pointers two rows have) |
| Observations | O1 (what the barrier probe actually measures), O2 (the roundtrip's oracle), O3 (an unretained calibration, re-run here), O4 (glossary debt in shared tooling), O5 (the seed probe's identity), O6 (the Tier column is a proposal for twelve of sixteen rows) |

**Method and its limits.** This review executed. `check_campaign_records.py`, `validate_records.py`, `render_docs.py --check`, `config_domain.py check`, `tier_placement.py check`, `scope_matrix.py --check` and all five self-tests were run against the tree; `extract_ctp_timings.collect` was re-run over the five bundle roots and every §4 statistic recomputed; the bundle hashes and `total_bytes` were recomputed with `campaign_records.bundle_hash`/`bundle_total_bytes`; `sha256sum -c` was run on all four bundles and on `SHA256SUMS-bulky.txt`; every `install_conf`, `install_databases`, `scenario_tree` and `user_shell_fm` before/after pair was re-diffed; both testcase worktrees were checked with `git status`; the four binaries of both pinned installs were re-hashed and compared cell by cell; `du` was run on the campaign root; and `resource_sampler.py` was re-calibrated against four busy loops. Eight defects were planted — five mutations of the two checkers and four mutations of the configuration-domain cells — **all on copies under a scratch directory; the campaign tree was not modified**. No CUBRID or CTP invocation was made and no database was created, so the ticket's runs are audited from their retained manifests, logs, journals and bundles rather than reproduced. The record was read as a register of claims to check, not as evidence.

`python3 tools/check_campaign_records.py` reports **exactly one item**, `evidence/ticket15/controls/att-T15-C04.json`, the known ticket 15 follow-up; it is still the only one, and it is not ticket 17's.

## Findings

### F1 — MAJOR, blocking. A multi-session barrier scenario *does* exist in the private suite, and criterion 1's disclosure denies it

The record's §5.6 is headed "**it does not exist**" and states: "No barrier scenario exists in either suite." `tools/barrier_cost_probe.sh` repeats it in its own header: "`barrier` appears in the campaign only as a record field … never as a scenario." The ticket's checklist, the commit message and finding F4 all rest on that sentence.

At the private worktree's pinned commit `c4fe45173`, `shell/_06_issues/_18_2h/bug_bts_22449/cases/22449.ctl` opens:

```
MC: setup NUM_CLIENTS = 4;
...
C1: COMMIT;
MC: wait until C1 ready;
...
C2: create unique index i on t1(a,b,c) with online;
MC: wait until C2 blocked;
C3: insert into t1(b) values (7);
MC: wait until C3 blocked;
C4: alter table t1 add column id int;
MC: wait until C4 blocked;
C1: commit;
MC: wait until C2 unblocked;
```

Four participants, a coordinator that releases them, explicit barriers on state each participant has established with real database operations. It is driven by an ordinary private shell case, `cases/bug_bts_22449.sh`, through `runone.sh` of CTP's isolation ctltool — and that tool is present in the campaign's own pinned CTP tree at `/home/vimkim/CTP/isolation/ctltool/` (`runone.sh`, `qactl.c`, `qacsql.c`, `Makefile`), so it is not a Capability gap either. Three further `.ctl` scenarios exist in the same repository (`cbrd_23039`, `bug_bts_14441`, `bug_bts_14506`).

> Specification, *Concurrency and recovery schedules*: "Existing isolation coordination mechanisms may be reused as dependencies inside private cases; they are not a third seam."

That sentence is pointing at this mechanism. The campaign has one, in the tree, at the pin.

Three things make this more than a miscount.

**The standard ticket 17 applied elsewhere would have admitted it.** Criterion 1 asks for representative *timings*, not for campaign-authored cases: the eleven-case private bucket is timed as a representative workload and its binding case, `cbrd_27229`, is pre-existing and not the campaign's. `bug_bts_22449` is exactly as admissible as `cbrd_27229`.

**The substitute measures a different mechanism from the one ticket 23 is pointed at.** The probe is a bespoke token-file barrier over short-lived `csql` processes (O1). If ticket 23 reuses the isolation mechanism the specification names, the number it inherits is the cost of something else.

**The consequence lands on a ticket that did not make the error.** §6's `multi-session-barrier` row — 24.88 s per case, four cases, 103.62 s per invocation — is `derived`, and its derivation begins "NO SCENARIO EXISTS". Ticket 23 is blocked by ticket 17 precisely so that it starts with a measured number.

This review accepts without reservation that the *campaign's own* four required schedule families (snapshot survival, rollback survival, slot reuse and cleanup retry, interrupted recovery) have no case at either seam — that Delivery gap is real, correctly named, and is ticket 23's to close. What is wrong is the wider claim, the search behind it, and the conclusion that no barrier scenario could be timed.

**What must change.** Correct §5.6, finding F4, the probe's header comment and the ticket's checklist to say what is true: the four required *schedule families* are a Delivery gap; a multi-session barrier *scenario* exists in the private suite and was not timed. Either time `bug_bts_22449` at the shell seam the way the eleven-case bucket was timed, or record in one line why the existing scenario is not representative — and in either case keep the mechanism probe, which remains useful, with its row relabelled to say what it is derived from.

### F2 — MAJOR, blocking. Eight of twelve attempt records and eight of twelve bundle indexes carry a digest and a size taken while the bundle was still growing

Recomputed with the campaign's own helpers against `/home/vimkim/.cub/campaign/cbrd-26659/ticket17/attempts/inv-T17-0002`:

| | live, finished bundle | recorded |
|---|---|---|
| `bundle_hash` | `sha256:f0450fd541df1f82bd1fb2fd93206588b0ce1be77c1496264574ce4403ad02ee` | eight different digests in `att-T17-0002` … `att-T17-0009`; only `att-T17-0010` matches |
| `total_bytes` | 322,170 | 318,808 / 319,241 / 319,671 / 320,098 / 320,507 / 320,916 / 321,340 / 321,755, then 322,170 |

The monotonic growth is the signature: each record was sealed as its own case finished, while eight more files were still to be written. `inv-T17-0001`, `inv-T17-0003` and `inv-T17-0004` are single-attempt bundles and all three match exactly.

> `CBRD-26659-traceability-schemas_f4299ac_claude.md`, *The campaign's bundle conventions*: "the digest and the size are the **finished** bundle's, computed after the invocation's last file is written and not as each record is built; and a record whose numbers were taken earlier is **corrected and says so**, because a hash that verifies against nothing is worse than no hash." (ticket 44 F3, user decision 2026-09-16.)

This is the defect ticket 19's review found as its F3, that the user settled on 2026-09-16, and that ticket 44 spent a correction pass removing from 64 attempt records, eight manifests and thirty matrix seals. Ticket 17 ran on 2026-09-18 and reintroduced it into sixteen records.

The bundles themselves are sound and nothing is lost: `sha256sum -c SHA256SUMS` passes with zero failures on all four (49, 212, 61 and 63 files), `SHA256SUMS-bulky.txt` verifies 1,328 of 1,328 files from the storage root, and the one record per bundle that was written last reproduces the convention exactly. The defect is entirely in the recorded numbers.

**What must change.** Recompute the eight `bundle.hash` values and the eight `total_bytes` values of `inv-T17-0002`'s records against the finished bundle, and say in each record's `notes` what it used to carry, as ticket 44 did. The tooling fix belongs beside D3 and D5 in ticket 15's tooling: a shared bundle root must be sealed once, after the invocation's last file.

### F3 — MODERATE, non-blocking. The one arithmetic criterion 4 rests on has no negative control

`selftest_tier_placement.py` states its purpose as planting "a seed count whose arithmetic was never done". It does not. Mutating one line of `tier_placement.place` —

```python
per_case = seeds * per_seed      # →   per_case = per_seed
```

— leaves **all fifteen checks passing and `tier_placement.py check` clean**, while the published table changes:

| row | correct | under the planted defect |
|---|---|---|
| ten-seed churn | 55.0 s per case, 93.9% headroom | 5.5 s, 99.4% |
| hundred-seed churn | 550.0 s per case, 84.7% headroom | 5.5 s, 99.8% |

Checks 9 and 12 inspect `seeds_all_in_one_case` and `seed_per_case`, which are computed on separate lines; neither ever inspects `per_case_seconds`, which is the value the placement decision and the headroom both use. Criterion 4's headline — "one hundred cost 550.1 s against a 3,600 s extended per-case cap" — is produced by a line no control covers.

The other four mutations were each caught by the right check: `_fits` made unconditional fails checks 6 and 10; the worst-case-uniform figure collapsed onto the measurement fails 13 and 14; a derived row without a derivation fails 7; a fits-no-tier workload squeezed into a tier fails 6.

**Fix:** one assertion — `abs(rows["churn-10"]["per_case_seconds"] - 58.0) < 0.01` — beside check 9.

### F4 — MODERATE, non-blocking. `config_domain.py` never verifies the binaries it says prove the cell

Criterion 2's clause is "proven runnable **with a matching binary**", and the specification's *Engine baseline* adds that "a build directory's presence is not proof of a matching binary". `config_domain.py`'s own docstring says it owns what "proven" means "so that the probe cannot decide it about itself". On the binary identity, it does take the probe's word:

- `binaries` is checked only for the *presence* of four non-empty keys; the recorded hashes are never compared against the campaign's pinned values, although `campaign_records.LIBRARY_HASHES` and `campaign_env.campaign_expected_hash` both hold them;
- `engine_commit` is compared against a constant in the module, but the field is a string the probe copied from `CAMPAIGN_ENGINE_COMMIT`;
- `cubrid_rel`, the one field that is read out of the running binary, is never cross-checked against either.

Planted against copies of the real cells:

| planted defect | reported? |
|---|---|
| A: `8192-release-cs`'s four binary hashes replaced with `dead…beef` | **no** — 12 cells read, 12 expected, **0 problems** |
| B: `4096-debug-sa`'s `cubrid_rel` rewritten to name build `11.5.0.0001-deadbee` | **no** — 0 problems |
| C: `16384-release-sa`'s OOS-path evidence zeroed | yes, by name |
| D: `8192-debug-cs` deleted | yes, by name |

Twelve of twelve `runnable` is the answer that most deserves suspicion, so this review checked the substance independently rather than through the checker, and **the twelve verdicts stand**:

- all twelve cells' four recorded hashes equal the live install binaries byte for byte (`libcubrid.so`, `libcubridsa.so`, `csql`, `cub_server`, both builds);
- both library hashes equal ticket 41's pinned values in `campaign_records.LIBRARY_HASHES`;
- every cell's `cubrid_rel` reads `CUBRID 11.5.0 (11.5.0.2648-f4299ac)` and names the right build;
- `campaign_set_engine` hash-gates both libraries and refuses a `cubrid_rel` without `f4299ac` **before** any probe runs, and every cell ran through it;
- the raw per-cell logs support each cell: `spacedb.txt` reads back 4096/8192/16384 as declared in all twelve, and `workload.out` carries `payload_octets 4000`, `payload_ok 1`, `tag_ok 1` and the `SHOW HEAP OOS` row the cell records, with `Oos_num_recs` 2 / `Oos_recs_sumlen` 4040 at 4 KiB and 1 / 4024 at 8 and 16 KiB — the chunk-boundary observation §3 draws is real and is visible in the logs.

So there are genuinely no Capability gaps in the configuration domain. The finding is that the checker would not have told us.

**Fix:** compare `binaries["libcubrid.so"]` and `["libcubridsa.so"]` against `campaign_records.LIBRARY_HASHES[build]`, require `cubrid_rel` to contain the pinned commit's abbreviation, and plant both in the self-test.

### F5 — MINOR, non-blocking. Five of the eight `invocation_measured_seconds` values are composites, and §6 says they are measurements

> §6: "`Invocation` is what the invocation was **measured** to cost where it was measured as a whole."

True for three rows: `public-sql-deterministic` (111.83 s, the sampler's wall for `inv-T17-0002`), `shell-crash-recover` (26.45 s, the sampler's wall for `inv-T17-0004`) and `shell-issue-bucket` (432 s, a real CTP launcher wall). Not true for the other five, each of which `build_model.py` assembles:

| row | recorded | what it is |
|---|---|---|
| ten-seed churn | 62.27 s | the probe's 58.17 s **plus a 4.1 s shell-launcher toll the probe never paid** |
| hundred-seed churn | 554.16 s | 550.06 s + 4.1 s |
| hundred seeds, reused fixture | 20.82 s | 16.72 s + 4.1 s |
| configuration sweep | 50.37 s | the **sum** of twelve separate probe walls |
| twelve-site fault campaign | 456.5 s | the **sum** of twenty-four walls read out of ticket 41's log |

Separately, four rows whose `Invocation` column is purely computed — `public-sql-bulk-churn` 49.28 s, `instrumented-fault-site` 83.4 s, `corruption-detection` 102.1 s, `bounded-fs-exhaustion` 35.1 s — carry `basis: measured` in the same row, because `basis` describes the per-case input and the rendered table has one Basis column for both. A reader of §6 cannot tell a measured invocation from a computed one.

Every one of these is conservative, none changes a tier, and the model file makes the arithmetic visible. The fix is a column or a flag, not a re-measurement: `tier_placement.py` already knows which rows carry `invocation_measured_seconds` and could mark the rest.

One related nit, in the same direction: `build_model.py` sets the SQL seam's `invocation_fixed_seconds` from the **launcher** median (41.0 s) while the shell seam's comes from the **fixed-cost** median (4.1 s). The launcher median already includes the cases, so the public rows double-count about a second. It overstates, so nothing is at risk.

### F6 — MINOR, non-blocking. Three numbers in the record do not hold

- **"The public suite has room for about 40 cases before the 900 s invocation cap becomes the constraint"** (§6, and the ticket's Outcome, and §1's "room for about forty cases"). At the model's own figures — 8.28 s per case over a 41.0 s launcher — the 900 s cap is reached at about **104** cases. The model's own `public-sql-suite-projected-40` row records 372.2 s and **58.6% invocation headroom**, which says the opposite of the prose. Nothing in the ticket's numbers makes forty a limit; §8's storage arithmetic ("a public suite of forty cases would retain about 13 GiB", against a 100 GiB cap) does not either. Tickets 20 to 22 read this line to size the fast tier, so it is worth correcting even though it errs conservatively.
- **"401–411 chunks, 2.15–2.23 MB of payload"** for the seeded churn probe (§7). Recomputed from the probe outputs: the ten-seed run is 407–411 chunks and 2.179–2.210 MB; the **hundred-seed run is 381–421 chunks and 2.026–2.278 MB**. The stated range fits neither, and understates the hundred-seed spread at both ends.
- **"a single 0.5-second sample, with 0 CPU in the sample either side"** for the 7.67-CPU peak (§8). In `samples/inv-T17-0002.json` the peak is sample 30 and the samples around it read `… 0.46, 0.307, 7.668, 0.0, 0.0 …`. The sample after is 0; the sample before is 0.307.

### F7 — MINOR, non-blocking. Two rows' only evidence pointer cites the wrong section

`corruption-detection` and `bounded-fs-exhaustion` carry `basis: "measured"` with `evidence: ["ticket 16 section 12: 98 s for six experiments"]` and `["ticket 16 section 12: 31 s"]`. Ticket 16's §12 is *Observations and decision requests*; both figures are in its §11, *Hand-offs*, where they read "the corruption procedure 98 s for six experiments; the bounded-fs procedure 31 s" and are correct. These two rows are the only ones in the model whose `evidence` is a prose sentence rather than an attempt or probe identity, and `tier_placement.py` accepts it because it only requires the list to be non-empty — so the citation is the whole of their traceability.

`evidence/ticket17/README.md` carries two more wrong cross-references: `inv-T17-0001`'s proof verdict is "explained in §7 of the record" (it is §9, finding F2) and "the record's §11 gives the exact invocations" (it is §12).

## Observations

### O1 — for ticket 23. What the barrier probe actually measures, and what it does not

Read from `barrier_cost_probe.sh` and the retained `tokens/`, `p*.sql` and `p*.out`: each participant runs a **fresh `csql` process per round** (`p1_r1.sql`, `p1_r2.sql`, `p1_r3.sql`), each works on **its own table** (`t_t17_bar_1` … `_4`), and every statement autocommits. So no session, transaction or snapshot is held across a barrier and no two participants ever contend. The three round times — 0.204, 0.204, 0.104 s — are four, four and two multiples of the 0.05 s poll interval, so the quantity measured sits at the probe's own resolution.

The record's §13 discloses the limit honestly and in the right terms: "§5.6 measures a mechanism, not a schedule. A schedule that establishes a snapshot, survives a rollback, reuses a slot or is interrupted mid-recovery will cost more than 5.6 s." §5.6's own summary — "The barrier mechanism is free; the fixture is the whole cost … That is the number ticket 23 should plan against" — reads stronger than the probe supports, because the four required families are precisely the schedules in which a participant must hold something open across the barrier. Taken with F1, ticket 23 should treat 0.17 s per barrier as a floor for coordination with no contention, not as the cost of a schedule.

### O2 — the configuration probe's "byte-identical" is engine-internal

The cell's roundtrip verdict comes from `payload_ok`, which is the engine comparing its stored value to a freshly evaluated copy of the same literal, and from a regex that only requires the recorded MD5 to be 32 hex digits — it is matched against no independently computed digest (`c20c7313e4e584bd73650d3f57841cf9` matches none of the three obvious external interpretations of a 4,000-byte `BIT VARYING`, so CUBRID's `MD5` on that type is doing something the probe does not pin down). For a feasibility probe this is proportionate — the value did make a real round trip through the out-of-row path, which `SHOW HEAP OOS` proves — but "a byte-identical value roundtrip" reads as an independent oracle and is not one. The stronger evidence is the cross-cell consistency this review checked and found exact: the same digest in all twelve cells, and the chunk count moving from one to two only at 4 KiB. That is what §3's two observations actually rest on, and it holds.

### O3 — an unretained calibration, re-run here and holding

§8 says the sampler reports logical CPUs "validated against four busy loops: 4.03". No sample, log or output of that validation is retained anywhere under `evidence/ticket17/` or the ticket's storage, while the two attribution probes (`attrib-createdb.json` peak 1.053, `attrib-server-start.json` peak 3.072, both at a 0.1 s interval, both matching §8) are. Re-run independently in this session: four busy loops give **mean 4.012 / peak 4.219** logical CPUs, one busy loop gives mean 1.001. The unit is right and the claim holds — but it now holds on this review's re-execution, not on a retained artifact. A calibration that supports the campaign's only near-ceiling number should be a file.

### O4 — for ticket 15's tooling. The glossary debt ticket 19's F6 named is still in the shared runner

The record's own prose is clean: **zero** uses of "activation" against **ten** of *OOS-path evidence*, no "green", no "NOK", and the five new probes and two new checkers use the canonical term throughout. But "activation" appears 39 times in ticket 17's sealed records — in evidence filenames (`activation_<case>_release.txt`), which ticket 19's review accepted, and in `notes` prose written by ticket 15's shared runner ("OOS-path evidence: activation proven by the paired checker", "activation markers all matched", "paired activation checker"). One further stale note in every SQL bundle index says the library hashes were "verified against ticket 11", where `campaign_env.sh` verifies them against ticket 41. Neither is ticket 17's to fix; both are now in twelve more sealed records.

### O5 — the seeded churn probe records a thinner identity than its siblings

`seeds/*/seed_cost.json` names the install prefix, build, page size, rows per seed and fixture policy, but not the engine commit, `cubrid_rel` or the library hashes — where `barrier/identity.txt` and each configuration cell record all of them. The probe ran through `campaign_set_engine`, so the binaries were gated; the retained artifact simply does not say so. Criterion 1's "full identities recorded" governs the five representative scenarios rather than criterion 4's probe, so this is an observation, not a finding.

### O6 — the Tier column is a proposal, not a computation, for twelve of sixteen rows

`tier_placement.py` reports a workload that exceeds its proposed tier's caps and one that fits no tier, but never one proposed for a larger tier than it needs; twelve of the sixteen rows fit the fast tier on time alone. The record says so plainly and gives the reason ("they are scheduled because the spec's *Execution tiers* section assigns concurrency, recovery and fault work there and because they need infrastructure the fast tier should not carry — not because they are slow"), which is the correct reading of the specification. Worth recording only so that a later reader does not mistake the column for a derivation: `smallest_fitting_tier` is the derived field, and it is in the model rather than in the table.

## What was verified and found sound

- **Every load-bearing number of §4 reproduces exactly.** Re-running `extract_ctp_timings.collect` over the five bundle roots: **57 bundles, 18 SQL and 39 shell**; SQL launcher 39–55 s median 41; SQL fixed cost 38.901–54.136 median 40.055; 97 SQL case times 26–950 ms median 63; shell fixed cost 1.816–11.649 median 4.055; 69 shell case times 1.363–111.927 s median 14.513; three eleven-case buckets at 432, 404 and 397 s with slowest cases 111.9, 92.6 and 96.2 s. The two seams' opposite cost shapes, which the whole placement rests on, are the artifacts' own.
- **Finding F1 of the record is correct, and it matters.** `summary.info` does carry one `<caseresult>` per case with its own `<totalTime>`: `inv-T19-0008` 30–260 ms summing 732, `inv-T19-0009` 39–286 summing 864, `inv-T17-0002` 28–231 summing 661 — each exactly as the record's table states. The nine whole-suite totals across ticket 19's invocations are 665, 703, 732, 843, 864, 909, 1,099, 1,828 and 2,061 ms, so 1,099 is the third highest, as the record says. Ticket 19's record line 339 is the statement contradicted, and ticket 35's F3 about the *assertion* count is untouched: `assertions.executed` is null on all ten SQL attempt records and measured (17 and 18) on the two shell records, which is the tooling rule.
- **Finding F2 of the record is correct in its diagnosis.** `ctp_sql_records.py:301` takes the scenario for the manifest from the conf (the override) while `:309` derives the directory it scans from `worktree / decl["scenario"]`, so the two disagree by construction; `inv-T17-0001` records eight `unexpected-case` mismatches naming exactly the other eight cases. Leaving it unfixed and recording it, rather than editing shared tooling from an implementation ticket, is the right call under the specification's *Reopening rule*.
- **Finding F3 of the record is correct and was handled correctly.** Ticket 17's matrix has 17 rows, all PASS with OOS-path evidence `proven`; **8 carry `gap_kind: "Delivery gap"` adopted from tickets 19 and 41 by `scope_matrix.py`, 9 carry `none`**, `ever_failed` false throughout, `accepted_exclusions` empty, and all three manifest seals (`inv-T17-0002/0003/0004`) verify against the files on disk. `scope_matrix.py --check` reports 17 rows, 0 disagreements, 0 unscoped. `check_campaign_records.py` confirms that every `original` attempt reaches a matrix history, `inv-T17-0001` included.
- **The configuration domain is proven in substance**, per F4 above: twelve cells, four binary hashes each matching the live installs, `cubrid_rel` naming the pin in all twelve, page size read back from `spacedb` in all twelve, OOS-path evidence present in all twelve, and the 4 KiB chunk-boundary difference visible in the raw `workload.out`. Install hygiene holds: six `verbatim`, six `not-applicable`, and both pinned installs are back at `cubrid_port_id=1523`.
- **Both seed counts hold, and the arithmetic is the probes' own.** `seed-cost-10-fresh` total 58.17 s (per seed 5.439–6.686, mean 5.813), `seed-cost-100-fresh` 550.06 s (5.333–7.682, mean 5.500), `seed-cost-100-reused` 16.72 s (0.096–0.117, mean 0.102). Every seed of every run reports `Has_oos_file 1` with 500 rows verified in range, so each reached the out-of-row path. Seed 1 produces byte-identical OOS figures in the ten-seed and hundred-seed runs, which is the determinism the workload claims. 55.0 s against a 900 s cap and 550.0 s against a 3,600 s cap both hold with room, and no numeric limit was changed — which is what criterion 4 asks.
- **The resource figures are the sampler's own and the ceilings hold.** `resource-summary.json` matches §8 row for row: peak 7.668 CPUs on `inv-T17-0002` (a single sample, confirmed in the raw series), p95 at most 1.121, mean at most 0.521, peak RSS 0.856 GiB of 16, peak 21 processes. The attribution is real: `cubrid createdb` alone 1.053 CPUs, `cub_server` boot 3.072 while its resident memory jumps to 0.635 GiB. Storage independently measured: `du` reads **40 GiB** disk usage and 51 GiB apparent against the 100 GiB cap, ticket 17's own tree about 4 GiB, its bundles 3 MiB; `retention.py admit` reports **50.82 GiB**, exactly the 27% conservatism D5 describes.
- **The instrumented figures are ticket 41's log, read correctly.** `instr-site-walls.json` has 24 rows over 12 sites; pair times 14.7–79.3 s, median 37.9, sum **456.5 s**; worst pair `i1` = 65.7 + 13.6, both lines present verbatim in `evidence/ticket41/instr-sites/run-all.log`. Ticket 17's own `a1` re-run records fault 7.4 s and control 6.6 s with the acknowledgement lines retained — and the disclosure that the shared instrumentation log made the runner count `acks: 2`, one dated 09/14 and one 09/18, is exact and is the kind of contamination a later ticket needs told.
- **The bulk workload's OOS-path evidence is asserted, not observed.** `activation_cbrd_26659_oos_sql01_insert_select_release.txt` carries `bulk100 … Oos_num_recs expected 100 got 100`, `Oos_recs_sumlen expected 457600 got 457600`, `bulk1000 … expected 1000 got 1000`, `expected 4169540 got 4169540` — one chunk per row for all 1,100 rows, as §5.4 claims.
- **Replay and cleanup evidence is otherwise complete.** All twelve bundle indexes are `complete: true` over one uniform fourteen-item keyset; every item is `present` or `not-applicable` and **none is `missing`**; each `not-applicable` is right for its attempt (no seed and no generator for fixed cases; no barrier for single-session cases; no injection on the unmodified engine; no core, with the launcher's scan cited). All four `root_path`s exist. `install_conf`, `install_databases`, `scenario_tree` and `user_shell_fm` before/after pairs were re-diffed by this review and every pair is byte-identical, so the "drift 0" claim is verified rather than asserted. Both testcase worktrees are clean at `35c81594333c49e4faf8b645d2019cfca8aa1422` and `c4fe45173ddbfccc6dc59212670ec91e94b8f6f1`, the commits every manifest records. Nothing was pushed.
- **The table is a computation, not a transcription.** `evidence/ticket17/placement-table.md` regenerates byte-for-byte from `tier_placement.py place`, and §6 of the record is that file's rows verbatim. `tier_placement.py check` reports 16 workloads, 0 problems, 1 risk, and the risk is the right one: the eleven-case private bucket at a worst-case-uniform 1,235 s against the 900 s cap, on a slowest case of 111.9 s against a 120 s per-case cap. Naming that as a risk rather than hiding it in a margin is the strongest single judgement in the delivery.
- **The self-tests were written before the thing they check, and eight of nine planted defects are caught.** `selftest_config_domain.py` plants nine ways of faking a proven cell and catches all nine; three mutations of `config_domain.problems` each fail the matching check. `selftest_tier_placement.py` runs fifteen checks and four of five mutations of `tier_placement.place` fail the matching checks. The two escapes are F3 and F4.
- **Verification claims in §14 all reproduce**: `validate_records.py` 280 records 0 failing; `check_campaign_records.py` the one ticket 15 item and nothing else; `render_docs.py --check` fresh; `config_domain.py check` 12/12/0; `tier_placement.py check` 16/0/1; `scope_matrix.py --check` 17/0/0; all five self-test suites 0 failing; `sha256sum -c SHA256SUMS-bulky.txt` 1,328 of 1,328, run from the campaign storage root.
- **No decision was made that was the user's to make.** Six decision requests, none decided; no numeric limit changed; `accepted_exclusions` empty; no answer promotion written; no schema edited, so nothing was owed to the traceability-schemas change log; no shared tooling modified (the commit is 14,717 insertions and no deletions).

## What this review could not verify, and why

- **The CTP and probe runs themselves were not reproduced.** No CUBRID or CTP invocation was made and no database was created, per the review's constraints, so the four invocations, the twelve configuration cells, the three seed runs, the barrier probe and the `a1` re-run are audited from their retained manifests, journals, logs and bundles. Where a number could be recomputed from those artifacts it was; where it could only be read, it was read.
- **The 98 s and 31 s figures for corruption detection and bounded-filesystem exhaustion** are ticket 16's, taken from that ticket's prose (F7 corrects the section). They were not re-derived from ticket 16's evidence tree, which is ticket 16's review to do.
- **Whether `bug_bts_22449` passes, or what it costs at the seam,** is not established here — F1 says only that it exists, is a four-client barrier scenario, and that its runner is present in the campaign's pinned CTP tree. Timing it is ticket 17's work to finish, not this review's.
- **The `--scenario-override` fix (D3) was not applied or tested**, and the eight `unexpected-case` mismatches in `inv-T17-0001` were left exactly as recorded, which is what the record intends.

## Effect on other tickets

- **Ticket 23** is the one that pays for F1. It should not take 24.88 s per schedule family as a measurement of anything but uncontended coordination plus a restart (O1), and it should look at `bug_bts_22449` and CTP's `isolation/ctltool` before building a coordination mechanism of its own — the specification points it there, and the campaign's CTP tree already carries it.
- **Tickets 20 to 22** take the public seam's shape, and it stands: a fixed ~41 s launcher, 26–950 ms cases, and 7.33 s plus 256–400 MiB per paired OOS-path evidence check, so the suite must be one invocation and the checks are the scaling work. The number they must not act on as written is F6's "about forty cases": the fast tier's 900 s cap admits about a hundred at the measured cost.
- **Ticket 15's tooling** owns F2's sealing order, F3's and F4's missing controls if the campaign wants them there rather than in ticket 17's files, D3's `--scenario-dir`, D5's `storage_used_bytes`, and O4's glossary debt in the generated `notes`.
- **The record contract (ticket 36's successor)** owns D6 and, with it, the general form of F5: a table that mixes measured and computed invocation figures under one Basis column should say which is which, the way it already requires a derived figure to carry its derivation.
- **Tickets 25, 31 and the operational-features tickets** inherit §6's `derived` rows for HA, CDC/flashback and encryption, which are correctly labelled lower bounds with their derivations stated, and owe the measurement.
- **Ticket 33** is unaffected: this review is ticket 17's and does not discharge the campaign acceptance review.
- **Decision requests D1 to D6** remain open and are the user's. This review agrees with the recommendations on D1 (reading A; the table holds either way, which the model's `seeds_all_in_one_case` / `seed_per_case` pair makes checkable) and D4 (`taskset` would change what the campaign measures), and notes that D2's recommendation — the model file is the home — is already how §6 behaves, since the rendered table regenerates from it exactly.

## Ticket criteria

| # | Criterion | Status | Evidence |
|---|---|---|---|
| 1 | Representative cases timed with full identities: the two tracer cases, a multi-session barrier scenario, a crash-and-recover scenario, a bulk or churn workload, one instrumented fault scenario | **not met as disclosed** | four of five timed soundly, each with engine commit, testcase commit, build, page size and run mode: public tracer alone 43 s / 55 ms; nine-case suite 44 s / 661 ms; the private tracer, which is the crash-and-recover case, 11.65 s release and 16.17 s debug over 28 recorded runs; bulk 231–950 ms with every row's chunk asserted; `a1` fault 7.4 s and control 6.6 s. The fifth is recorded as non-existent and it exists — **F1** |
| 2 | The configuration domain re-verified: 4/8/16 KiB × release/debug × standalone/client-server, each proven runnable with a matching binary or recorded as a Capability gap | **met**, checker thin | twelve cells run, not inspected; all four binary hashes per cell equal the live installs, `cubrid_rel` names the pin in all twelve, page size read back from the engine, OOS-path evidence present, roundtrip byte-identical; no Capability gaps. The module that judges them would not have caught a fabricated binary identity — **F4** |
| 3 | The tier-placement table finalized per workload against the per-case and invocation caps; any workload that cannot fit recorded, not squeezed | **met** | sixteen workloads computed from the caps as inputs; table regenerates byte-for-byte; 0 problems, 1 risk (the eleven-case bucket at a worst-case 1,235 s, and `cbrd_27229` at 111.9 s of a 120 s cap); no workload fits no tier. Labelling qualified by **F5** and **F7** |
| 4 | Seed counts (10 scheduled, 100 extended) checked against measured per-seed times; a decision request rather than a silent change if the caps cannot hold | **met** | 58.17 s and 550.06 s measured, against 900 s and 3,600 s per-case caps; both hold; no limit changed; D1 raised, not decided. The arithmetic that produces the per-case figure has no negative control — **F3** |
| 5 | Resource ceilings (8 logical CPUs, 16 GiB, 100 GiB under the home directory) checked against measured peak usage | **met** | peak 7.668 CPUs attributed to `cub_server` boot by two independent probes, p95 ≤ 1.121; 0.856 GiB of 16; 40 GiB of 100 by `du`, independently measured; D4 and D5 raised, not decided. One prose overstatement about the peak's neighbours — **F6** |
| 6 | The timing record and the placement table committed in the docs repository campaign folder | **met** | docs commit `b990220`, 91 files, all additions; nothing pushed; both testcase worktrees clean at the recorded commits |
