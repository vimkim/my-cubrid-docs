# CBRD-26659 — Independent review of ticket 19, the public SQL-operations family

> Reviewed: 2026-09-15 (KST). Engine baseline `f4299ac0cd777a2a964c1f197ae5ebf9841a4936`, re-pinned without the unit-test seams by ticket 41; normative context `f6543de` + sha256 `c9daf3c4…`; requirement catalogue sha256 `0cc33c82…` (ticket 12).
> Reviewer: Claude Opus 5, in a session that authored none of the artifacts under review. The session was opened with `/clear` rather than a handoff or a compaction, so it reached the ticket, the specification and the evidence tree as primary sources and not through the author's account of them.
> Subject: testcase commits `4a2590f36`, `38128e190`, `5c6c1264a`, `0eb64fc87`, `94bb3cb5a`, `35c81594333c49e4faf8b645d2019cfca8aa1422` on base `b94995abf`; the evidence under [`evidence/ticket19/`](evidence/ticket19/) and [`tools/activation_check_spec.sh`](tools/activation_check_spec.sh); the eleven replay bundles under `/home/vimkim/.cub/campaign/cbrd-26659/ticket19/attempts/`; and the record [`CBRD-26659-sql-operations_f4299ac_claude.md`](CBRD-26659-sql-operations_f4299ac_claude.md) at docs commit `2317ffe`, revision 2.
> Satisfies: the [campaign specification](/home/vimkim/gh/cb/CBRD-26659-oos-testcases-handover/.scratch/oos-adversarial/spec.md) section *Review, sign-off and deferral* — "An independent agent session, never the authoring session, reviews Standards and Spec conformance per repository, validates the negative-control checkers, and audits replay and cleanup evidence before acceptance" — for the public SQL repository at these commits, in all three of its obligations. It does **not** discharge ticket 33, the whole-campaign acceptance review, and it cannot supply the user's sign-off on the two flagged promotions.

Vocabulary follows the [docs glossary](../../CONTEXT.md).

## Verdict

**REVISE. All seven of ticket 19's criteria are substantively met and the engineering is the strongest the campaign has produced: the derivation refuses any size the campaign may not assert, all three negative controls detect their planted defects under re-execution, and the replay and cleanup evidence is complete. Two findings block. The first is the serious one — an executed `original` FAIL was erased from the coverage matrix, and the ticket's own disclosure of that class of exclusion undercounts it by one invocation.**

| | |
|---|---|
| Ticket criteria | 7 of 7 met, criterion 2's trigger clause qualified by the author's finding T19-F1 |
| Negative controls | 3 of 3 validated, two of them by re-execution in this session |
| Replay and cleanup evidence | complete; drift zero on all 11 invocations, independently re-diffed; one defect in the recorded hashes (F3) |
| Answer promotions | 8 promoted, 2 correctly flagged, 6 correctly unflagged; the user's sign-off on the two is owed and is not this review's to give |
| Blocking findings | F1 (`inv-T19-0008`'s FAIL erased from the matrix), F2 (the declaration input defeats the sign-off gate on regeneration) |
| Non-blocking findings | F3 (64 of 83 recorded bundle hashes no longer verify), F4 (`accepted_exclusions` empty), F5 (a tautological self-test), F6 (glossary), F7 (three stale numbers) |
| Observations | O1 (the record checker cannot detect F1), O2 (whether sign-off gates promotion or acceptance — the user's to settle), O3 (model precedent) |

**Method and its limits.** Unlike the ticket 13 and 14 reviews, this one executed. The host was quiet, so: `tools/check_campaign_records.py` was run (passes); `review_candidates.py` was run against the clean `inv-T19-0009` bundle (exit 0) and then against copies carrying three separately planted defects (all three caught, exit 1); `make_control_c1.sh` was run into a scratch directory and its output compared against the recorded control; `sha256sum -c SHA256SUMS` was run on the bundles; and every `install_conf`, `install_databases` and `scenario_tree` before/after pair was re-diffed. No CTP invocation was made and no database was created, so the CTP runs themselves are audited from their retained manifests, logs and bundles rather than reproduced. Two Standards and Spec passes were commissioned *by this session* as parallel sub-agents working from the artifacts; their findings are merged here, and where this review disagrees with them it says so (F2's severity, F5's reach, and the `reviewer`-field claim rejected under O2). The report under review was read as a register of claims to check, not as evidence; every load-bearing number in it was verified against the artifacts or is recorded below as failing.

## Findings

### F1 — MAJOR, blocking. An executed `original` FAIL was erased from the coverage matrix, and the ticket's disclosure denies it

`inv-T19-0008` executed all nine cases against the promoted answers. Eight PASSed; `cbrd_26659_oos_sql02_update` **FAILed**, recorded as `att-T19-0075`, `kind: "original"`, `outcome: "FAIL"`, release, client-server, 16,384 B pages. That attempt, and all nine of `att-T19-0071..0079`, appear **zero times** in `matrix.json` — not in any row's `finding.history`, not in any row's `attempt_records`. The row `OOS-SQL-02/cbrd_26659_oos_sql02_update/16384-release-cs` reads `latest_outcome: "PASS"`, `ever_failed: false`, `flakiness: {attempts: 3, failures: 0}`, history `inv-T19-0004 / 0006 / 0009`. Across all 44 rows, `ever_failed` is false everywhere.

> Specification, *Outcomes, replay and minimization*: "A later pass never erases an earlier failure."
> Specification, *Campaign manifest*: "The manifest feeds the coverage matrix; the matrix is the cross-invocation aggregation."

Three things make this more than a miscount.

**The disclosure is wrong, not merely incomplete.** The ticket's Outcome and the report's §12 both say the three bootstrap invocations `inv-T19-0001..0003` are "the only place the campaign has excluded an executed `original` attempt from the matrix". It is four invocations. Five ticket-19 manifests reach the matrix (`0004`, `0005`, `0006`, `0009`, `0010`); four do not.

**The stated justification does not cover the fourth.** The bootstraps are excused because "an empty answer is how a candidate is produced rather than a finding, and merging them would set `ever_failed` on every row". `inv-T19-0008`'s answers were not empty. The report itself relies on that fact twice: §3 calls it a run "against the unchanged answers" and §13's T5 row cites its "eight byte-identical answers" as the proof that lower-casing the SQL altered no value. A comparison failure against a promoted answer is exactly the kind of earlier failure the Outcomes rule exists to preserve.

**The erased run is load-bearing.** §13's S4 row records that the update case's answer was "re-promoted from `inv-T19-0008`" after its relabelling, and testcase commit `35c815943` is that re-promotion. So the one invocation whose records the matrix does not carry is the invocation the currently promoted update answer came from.

The correct reading of the FAIL is benign — the case's step label changed and the answer had not yet been re-promoted, so it is a testcase-side relabelling, not an engine finding. That is an argument for recording it with the right attribution, not for its absence.

**What must change.** Merge `inv-T19-0008` into the matrix; set `ever_failed: true`, `flakiness.attempts: 4`, `failures: 1` on the two `cbrd_26659_oos_sql02_update` rows, with `attribution.target` naming the testcase relabelling and explicitly not the engine; and correct the ticket's Outcome and the report's §12 from three invocations to four, with the bootstrap justification stated only for the three it actually covers.

### F2 — MAJOR, blocking. The tooling input carries `flagged_for_user: false` on all nine cases, so a regeneration silently drops the sign-off gate

`tools/declarations/ticket19-public-sql-operations.json` sets `"flagged_for_user": false` on every one of its nine cases, including `cbrd_26659_oos_sql02_update` and `cbrd_26659_oos_sql06_triggers`. Both `promotions.json` and `inv-T19-0009.json` carry `true` for those two, with the reasons written out at length.

> Specification, *Review, sign-off and deferral*: "The user signs off on every answer promotion whose case touches a Specification gap or an observed-versus-normative disagreement."

The gate therefore survives only in the two hand-written records. The declaration is the portable input the campaign's own §13 T3 row introduced so that the control and the run could be reproduced from a clone; regenerating the manifest from it would produce a manifest in which no promotion is flagged and nothing in the record would say a gate had been lost. This review treats it as blocking for that reason — the flag is the artifact that tells the user which two promotions are theirs to accept, and it currently contradicts itself across two files in the same directory.

### F3 — MAJOR, non-blocking. 64 of the 83 recorded bundle hashes no longer verify against the bundle on disk

Nine attempts of an invocation share one bundle directory (`…/attempts/inv-T19-000N`), and each attempt record's `bundle.hash` was written as that directory's digest at the moment the record was written, while the directory was still growing. Only the last attempt of each invocation records the digest the finished bundle has. Recomputed across the tree: **19 of 83 attempt records match disk** (all nine of `inv-T19-0004`, whose records were written after the directory was final; the two controls; and the last attempt of each of the other eight invocations); **64 do not**. `total_bytes` diverges in the same 64 records and for the same reason.

> Ticket 36, decision 1: the bundle hash is "the sha256 of a `SHA256SUMS` listing every file in the bundle … in bytewise (`LC_ALL=C`) order", chosen because "a human can verify it with `sha256sum -c`".

For 64 attempts that verification now fails. The bundles themselves are sound: `sha256sum -c SHA256SUMS` passes with zero failures on every invocation checked, so nothing is lost or corrupt, and the hash convention itself is implemented correctly — `inv-T19-0010`'s `SHA256SUMS` digest reproduces `fcd1f2f9…` exactly. The defect is structural: the specification says "Each attempt retains one replay bundle", and the implementation gives nine attempts one bundle. Either give each attempt its own bundle root, or record one bundle per invocation with one hash and have the nine attempt records reference it, and say in the schemas document which was chosen.

### F4 — MINOR, non-blocking. The bootstrap exclusion is reasoned only in prose; `accepted_exclusions` is empty

The judgement in F1's first paragraph — that the three empty-answer bootstraps stay out of the matrix — is substantively defensible, and this review accepts it for those three: an empty answer is the mechanism by which CTP is made to execute a case and emit a candidate, the records are retained, and merging them would set `ever_failed` on every row for a reason that is not a finding. But `matrix.json`'s `accepted_exclusions` is `[]`.

> Specification, *Review, sign-off and deferral*: "Only the user converts incomplete coverage into an accepted exclusion, as a dated entry in the coverage matrix naming the requirement and reason. Agents propose; they never accept."

The proposal is written well and in three places; the dated matrix entry that would make it an accepted exclusion is absent, and only the user can write it.

### F5 — MINOR, non-blocking. A self-test check that cannot fail, and re-types the fixture's sizes instead of reading them

`derive_ticket19_sizes.py:393-394`:

```python
check("tie-invariant sumlen (multi1+single1 vs multi1+single2)",
      sumlen([20000, 3500]), sumlen([20000, 3500]))
```

Both operands are the same expression. The commissioned Standards pass called this "the tie-invariance is asserted nowhere"; that overstates it, because the guard two lines below (`"unequal sizes would NOT be tie-invariant"`) does prove `sumlen` is sensitive to its input, and with `single1` and `single2` both at 3,500 B the invariance is true by construction. The real defect is narrower and worse: the fixture's sizes live at `gen_ticket19_cases.py:920` as `[3500, 20000, 3500]` and are re-typed here as literals, so an edit that made the two columns unequal would destroy the documented tie while this self-test kept passing. That is the same drift class the report's own §2 finding 2 describes and fixes for the bulk group — two copies of one arithmetic, one edited without the other — left standing here. Read the pair from the fixture and compare the two real demotion sets.

### F6 — MINOR, non-blocking. Glossary: "activation" displaces *OOS-path evidence*, and "green" appears three times

> `CONTEXT.md`, *OOS-path evidence*, `_Avoid_: Activation, covered, large input, DISK_SIZE`. Specification, *Vocabulary*: "used exactly in every case, manifest, ticket and report."

The report uses "activation" **24 times** and the canonical term **zero**, including the §4 section heading. "Green" is `_Avoid_` under both *Outcome* and *Assertable requirement* and appears at lines 95, 100 and 330. Ticket 13's `activation_check_cs.sh` gives the *filename* a repository precedent, and this review does not ask for the new checker to be renamed — sealed records cite it by name and hash. The prose and the section heading are a different matter.

### F7 — MINOR, non-blocking. Three numbers in the report do not hold

- §3 opens "Six invocations, all on the re-pinned build" above a table of **eleven**. Stale from revision 1.
- §1 gives the campaign storage total as "46.3 of 100 GiB"; §10 gives 36. Measured: **36 GiB**, so §10 is right and §1 is wrong. Ticket 19's own 3.4 GiB is correct in both. This figure is tracked against the budget decision's 100 GiB cap, so the wrong one is the one a reader would act on.
- `expected-oracle.md` is sealed in no replay bundle and was first committed in `27dee8b`, after every run, then amended by `94495d8`. The claim carried in all eight promotion records — "which was written before any CTP invocation of these cases" — is therefore unfalsifiable from the artifacts. It is substantially mitigated rather than dismissed: the machine-checkable oracle is not the prose file but the Python derivation, which this review re-ran and which reproduces the promoted answers' `(length, digest)` pairs without the engine. Ticket 13's review called that reproducibility "the strongest part of the delivery" precisely because it does not require trusting file mtimes; ticket 19 keeps the property and should seal the oracle in the first bundle so the prose claim inherits it.

## Observations

### O1 — for ticket 15. The record checker validates shapes, not coverage completeness, so nothing mechanical could catch F1

`python3 tools/check_campaign_records.py` returns `OK: all campaign record checks passed` on this tree, and it is correct to: every record validates against ticket 12's schemas as widened by ticket 36. Its checks are `check_schema_subset`, `check_catalogue`, `check_scenario_map`, `check_record_schemas` and `check_documents`. None of them asks whether every retained attempt record with `kind: "original"` appears in the matrix. F1 was therefore invisible to tooling and reachable only by reading the manifests against the matrix, which is how both this session and the commissioned Spec pass found it independently.

The cheap fix belongs in ticket 15's checker, not in ticket 19: for every `att-*.json` with `kind: "original"`, require either a matrix `finding.history` entry or a dated `accepted_exclusions` entry naming it. That single rule would have caught F1 and would enforce F4's requirement at the same time.

### O2 — for the user. Whether sign-off gates the promotion or the acceptance, and who supplies the note

The commissioned Standards pass called the two flagged promotions a hard violation on the ground that the answers are committed while sign-off is outstanding, reading "the user signs off on every answer promotion" as gating the act of promoting. The ticket reads it the other way: its Outcome lists sign-off under "Owed before this ticket is **accepted**", and the report says so consistently in §3 and §12 and in the promotion records themselves. This review follows the ticket and does not record it as a violation — the author is following the governing document, and the debt is disclosed in four places rather than obscured. The reading is nonetheless the user's to confirm, because tickets 20 to 22 will each promote answers under it.

Two narrower points survive regardless. Ticket 36's decision 8 says the tooling verifies and writes the promotion while **"the human still supplies the review note and the flag"**; here an agent supplied both, which is a real deviation from a decision the user resolved on 2026-09-14. And this review rejects the pass's related claim that the `reviewer: "authoring session"` field breaches the specification: that field is accurate disclosure of a mechanical candidate review, the rule "never the authoring session" governs the independent review, and this record is it.

### O3 — model precedent

Ticket 13's independent review was performed by Claude Opus 5 and written by Claude Fable 5.1 after a model switch; ticket 14's was Opus 5 throughout. This review is Opus 5. The substance of the rule — a session that authored none of the artifacts and reached them without the author's framing — is satisfied; if the campaign wants the ticket 13 precedent matched by model as well, this record is the thing to re-run under a different one.

## What was verified and found sound

- **The three negative controls all detect their planted defects, two of them re-executed here.** `review_candidates.py`: clean `inv-T19-0009` bundle exits 0; a flipped digest hex digit and a `payload_ok` flipped 1→0 are both reported (`RESULT: 2 problem(s)`, exit 1); renaming every `*_ok` column fires the sixth check added by §13's T4 (`"no *_ok equality flag was recognised in any result table"`), so a generator rename that stopped the flags being recognised cannot pass silently. `make_control_c1.sh`: run into a scratch directory, it locates `multi1_md5` by column name, flips exactly one hex digit, reads only from the testcase repository and left it clean — and its output (`…cb60`) reproduces `inv-T19-C002` byte for byte, which is the "re-run from the portable declaration" the report claims; `C001` is the earlier hand-built variant (`…cb69`), consistent with §7. `activation_check_spec.sh`: the checked-in planted spec differs from the genuine one by exactly one byte (`23565` against `23564`) and the recorded run reports exactly one FAIL with all eight other assertions still PASS, so the control fails for its planted reason and for nothing else. All three mechanisms are validated, and all three controls live outside `answers/`.
- **Replay evidence is complete.** All 83 bundle indexes are `complete: true`, with a single uniform 14-item keyset matching the specification's required list item for item; every item is `present` or `not-applicable` and **none is `missing`**. All 83 `root_path`s exist. `sha256sum -c SHA256SUMS` verifies with zero failures on every invocation checked, 224 and 212 files respectively. The one defect is F3, in the recorded hashes rather than the bundles.
- **Cleanup evidence holds under re-diff.** All 83 attempt records claim `conf drift 0, databases drift 0, testcase worktree drift 0`; this review re-diffed `install_conf.before/after`, `install_databases.before/after` and `scenario_tree.before/after` in all eleven invocation bundles and every pair is byte-identical. Namespace isolation under `campaign_ns.sh` is recorded on every attempt, per ticket 37 decision 2. Both worktrees are clean; nothing is pushed; the branch is exactly `CBRD-26659-oos-testcases-handover` on base `b94995abf`; `.result` files are gitignored.
- **The matrix is internally sound apart from F1.** 44 rows; 32 case rows, every one `PASS` with `oos_evidence.status: "proven"`; 12 caseless rows, every one `latest_outcome: null` with a gap kind — the two-row form the ticket's Notes require. Excluding ticket 13's and ticket 41's cases leaves exactly 24 rows of ticket 19's own, split 12 `none` and 12 scoped, as §8 claims. The split is a faithful application of the ticket 35 F2 rule as qualified by the delta review's D1: `OOS-SQL-01` and `OOS-SQL-02` keep `none` because the case asserts every clause at the seam and only the OOS-backed premise comes from the checker, which is the situation D1 names by name; `OOS-SQL-05`, `OOS-SQL-06` and `OOS-REP-06` are scoped because a clause of each statement is unasserted at the seam, each with a caseless companion. Re-merging is a no-op, as claimed.
- **The seven criteria hold against the case files, not against §11.** All twelve of criterion 1's scenarios exist in cases: `cbrd_26659_oos_sql02_update.sql` TEST 7 is exactly 50 `update` statements with only the final value asserted, TEST 4 is three, TEST 5 and 6 are the single-chunk↔two-chunk transitions, TEST 3 the inline-attribute-only UPDATE; `cbrd_26659_oos_sql06_rollback.sql` covers ROLLBACK of INSERT+UPDATE, UPDATE-then-ROLLBACK restoring the original 4,200 B value, and `rollback to savepoint` with the pre-savepoint write surviving, each checked inside and after the transaction; `sql01` carries the bulk 100 and 1,000 groups with asserted aggregates and `distinct_payloads` equal to the row count, so the aggregates cannot pass on identical rows. Criterion 2's constraint half asserts at TEST 6 that the table is exactly the two-row fixture after every failure, including the three-row INSERT whose last row collides. Criterion 3's LOB case carries five locators, the `INSERT … SELECT` copy, and the source-row DELETE that must not take the copy's external payload.
- **The CBRD-27006 provenance is exact.** Commit `1fdcaf93511acf0f94c71e0fdacc45e42fa34e16` exists with the cited title and date; the original's sizes are 3500/20000/3500, 3600/21000/3400 and 3700/22000/3300, and the reused case reproduces every one of them (as nibble counts: 7000/40000/7000, 7200/42000/6800). The original asserts `LENGTH` and whole-value equality only and makes no topology claim, exactly as the case header states. The equal-size tie in row 1 is recorded rather than engineered away, which is the right call for a reused workload — subject to F5.
- **Activation evidence follows the execution path, which is the lesson finding T19-F1 teaches.** Nine cases, nine specs, run client-server in the case's own run mode under `campaign_ns.sh` per the user's decision O2 of ticket 35, so the evidence is `proven` and the reuse question does not arise. The four phases added by §13's S1 — `INSERT … SELECT`, the LOB copy, the subquery UPDATE and the join UPDATE — each sit on their own table so the chunk count is unambiguous, and each asserts rather than observes. The checker fails explicitly when extraction fails (`"no SHOW HEAP OOS row for … extraction failed"`) and an unresolved column yields `UNRESOLVED(col)`, which can never equal a numeric expectation, so a broken read fails rather than passing silently. All 18 `checkdb -S` runs on the two final invocations exited 0; 83 across the tree.
- **Report inventory.** Nine manifests, 83 attempt records and 83 replay-bundle indexes, as §1 claims. Eight promotions, two flagged. The promotion hash proof required by ticket 36 decision 8 is present: the manifest's `answer_promotions` carry `"RENAME VERIFIED by ctp_sql_records.py: … both sha256 …"` appended by the tooling, with `promotions.json` holding the hand-supplied note and flag as the input.
- **Ticket 36 and 37 conformance otherwise.** `assertions.executed` and `failed` null on all attempt records (36.3); `storage_gib` a footprint, not the cap (36.4); `hand_maintained: true` on the 12 caseless rows only, with `apply_matrix_scoping.py` documenting correctly why a case row must not carry it (36.6); CTP tree `/home/vimkim/CTP` (37.1); public seam on 26659 with brokers 33120–33122 (37.5).

## On what the commissioned two-axis review did not examine

Revision 2 of the record closes ten findings from a Standards and a Spec pass the authoring session commissioned, and §13 lists them in a table. The record is careful to say those passes "are not the specification's independent review", which is the discipline docs commit `cbcfc0a` established for ticket 14 — that a long list of fixed findings is what makes a change *look* cleared rather than what makes it cleared. Read from the artifacts, three things none of those ten touched:

1. **Whether every executed attempt reaches the matrix.** F1. The ten findings include two about matrix rows (`S5`, and `T2` on how the matrix is written) and none about which invocations the matrix carries. `inv-T19-0008` was created *by* the review — it is the run that proved the lower-casing of `T5` altered no value — and its own records were never merged.
2. **Whether the declaration and the hand-written records agree.** F2. `T3` moved both declarations to repository-relative paths so the control could be replayed from a clone, and `S3` added the two `flagged_for_user: true` flags to the promotion records. The two fixes were not checked against each other, and the declaration still says `false` nine times.
3. **Whether the per-attempt bundle contract survives a shared bundle root.** F3. No finding examined the bundle indexes.

The first two are consequences of the review itself, which is worth recording for tickets 20 to 22: a revision that adds records is the moment to re-run the completeness checks, not only the schema ones.

## Effect on other tickets

- **Ticket 15** owns O1's completeness rule and, if the user takes the second option, F3's bundle-root decision. Both are edits to the campaign tooling, not to ticket 19.
- **Ticket 17** takes ticket 19's timings, and they stand: 40–55 s of CTP launcher time for nine cases against ticket 13's 39 s for one, 1,099 ms for all nine cases' execution, and about 8–9 s per paired activation check. The conclusion the report draws from them — that the launcher cost is fixed, the public suite should be one invocation, and what scales is the activation checks — is supported by the figures and is the useful finding for tier placement. Only the §1 storage number (F7) needs correcting.
- **Ticket 18** owns the `OOS-REP-06` locator-demotion fixture, which ticket 19 correctly declines to assert and carries as a scoped row with a companion, and the `OOS-REP-07` clause-level rows ticket 39 item 3 requires.
- **Tickets 20 to 22** inherit `tools/activation_check_spec.sh` and its spec format, `derive_ticket19_sizes.py`'s refusing `classify()`, and `review_candidates.py`, all three of which this review exercised and found sound. They also inherit finding T19-F2 — a semicolon ending a header comment line splits a CTP case file — which applies to every commented case anyone writes, and the empty-answer bootstrap pattern. They should adopt O1's completeness check before their own matrices are merged.
- **The engine team** takes finding T19-F1, the record gate applied only on the server-side DML path. This review did not attempt to reproduce it — no `cubrid` command was run — but the four-probe table isolates the cause correctly by varying `insert_execution_mode` with no trigger present, which is the control that separates the path from the trigger, and the cited call chain through `do_check_insert_server_allowed` to `heap_attrinfo_determine_disk_layout` is consistent with the claim. Its matrix row keeps it visible; repair is out of the campaign's scope.
- **Ticket 33** is unaffected; this review is per-repository and does not discharge the campaign acceptance review.

## Ticket criteria

| # | Criterion | Status | Evidence |
|---|---|---|---|
| 1 | Cases for INSERT, UPDATE, DELETE; inline-attribute-only UPDATE; repeated updates (3 and 50+) with the final value asserted; multi-chunk UPDATE; DELETE with count; delete-all then reinsert; ROLLBACK of INSERT+UPDATE; UPDATE then ROLLBACK restoring the original; savepoints with partial rollback; bulk 100 and 1,000+ of varying sizes | met | all twelve located in case files, not only in the report's table; 50 updates counted at `cbrd_26659_oos_sql02_update.sql` TEST 7; bulk aggregates asserted with `distinct_payloads` guards |
| 2 | Constraint and trigger interactions; a violation leaves no value stored; triggers reading and writing OOS values; INSERT … SELECT; UPDATE through a join or subquery | met, trigger clause qualified | `sql06_constraints` TEST 6 asserts the table is exactly the fixture after all four failures; the *physical* "no value stored" half is unobservable at the SQL seam and is correctly carried as a scoped `OOS-SQL-06` row with a companion; triggers qualified by finding T19-F1, with the fixture built before any trigger exists |
| 3 | LOB locator columns per the accepted demotion ADR: many locators, insert-select copying, delete not taking external payload | met, demotion not asserted | `rep06_lob_neighbours` TESTs 1–5, four BLOBs and one CLOB; locator *demotion* correctly not claimed and carried as its own scoped row assigned to ticket 18 |
| 4 | The public CBRD-27006 workload reused with provenance recorded; its missing topology coverage not inherited | met | commit `1fdcaf935` verified; all nine sizes reused verbatim; topology derived under both accountings and then evidenced by `SHOW HEAP OOS` rather than inferred; the equal-size tie recorded, subject to F5 |
| 5 | Each case cites requirement IDs; expectations justified before running; whole-value checks are the oracle | met, with F7's provenance caveat | requirement IDs in every case header; the oracle reproduces in Python without the engine, re-run here; the prose oracle is unsealed, which F7 records |
| 6 | Inline comparators accompany OOS cases; activation evidence per case from paired debug runs; negative controls exist for new mechanisms | met | comparator rows in `sql01`, `sql05`, `sql02_update`; nine activation specs run in both builds, evidence `proven`; three controls for three new mechanisms, all validated above |
| 7 | Promotions reviewed; manifest and matrix updated through the tooling; each case under two minutes; work committed locally only | met, with F1 and F2 | review mechanical against 1,190 derived pairs; rename proven by hash; whole suite executes in 1.1 s against a 120 s per-case cap; nothing pushed — but the matrix omits `inv-T19-0008` (F1) and the declaration defeats the flag (F2) |
