# CBRD-26659 — SQL operations and single-session transaction lifetime, public SQL (ticket 19)

> Observed: 2026-09-15 (KST). Engine baseline `f4299ac0cd777a2a964c1f197ae5ebf9841a4936`, re-pinned
> without the unit-test seams by ticket 41 (`release_gcc_nounit`, `debug_gcc_nounit`); normative
> context `f6543de` + sha256 `c9daf3c4…`; requirement catalogue sha256 `0cc33c82…` (ticket 12).
> Author: Claude Opus 5, for the [Adversarial OOS testcase campaign](/home/vimkim/gh/cb/CBRD-26659-oos-testcases-handover/.scratch/oos-adversarial/spec.md) ticket 19.
> Records: [`evidence/ticket19/`](evidence/ticket19/) — five manifests, 46 attempt records, 46
> replay-bundle indexes, the coverage matrix, the pre-run oracle, the derivation and its
> self-test, the candidate review and its control, and the eight activation specs.
> Companions: [engine baseline](CBRD-26659-engine-baseline_f4299ac_claude.md),
> [requirement catalogue](CBRD-26659-requirement-catalogue_f4299ac_claude.md),
> [traceability schemas](CBRD-26659-traceability-schemas_f4299ac_claude.md),
> [public tracer bullet](CBRD-26659-public-tracer-bullet_f4299ac_claude.md),
> [tooling](CBRD-26659-manifest-matrix-replay-tooling_f4299ac_claude.md).

Vocabulary follows the [docs glossary](../../CONTEXT.md).

## 1. What now exists

| Item | Where |
|---|---|
| Eight new public SQL cases | `sql/_36_guava/cbrd_26659/cases/` on `CBRD-26659-oos-testcases-handover` |
| Reviewed answers | the matching `answers/` directory, promoted by rename from `inv-T19-0003` |
| Testcase commits (local only, nothing pushed) | `4a2590f36` → `38128e190` → `5c6c1264a` → `0eb64fc87`; base `b94995abf` (the verified `origin/develop` tip ticket 13 branched from) |
| Fixture derivation and its self-test | [`evidence/ticket19/derive_ticket19_sizes.py`](evidence/ticket19/derive_ticket19_sizes.py) |
| Case generator | [`evidence/ticket19/gen_ticket19_cases.py`](evidence/ticket19/gen_ticket19_cases.py) |
| Pre-run oracle | [`evidence/ticket19/expected-oracle.md`](evidence/ticket19/expected-oracle.md) |
| Candidate review | [`evidence/ticket19/review_candidates.py`](evidence/ticket19/review_candidates.py) |
| Spec-driven activation checker | [`tools/activation_check_spec.sh`](tools/activation_check_spec.sh) + eight specs under `evidence/ticket19/activation/` |
| Coverage matrix | [`evidence/ticket19/matrix.json`](evidence/ticket19/matrix.json) — 44 rows |
| Replay bundles | `~/.cub/campaign/cbrd-26659/ticket19/attempts/` (3.4 GiB; campaign total 46.3 of 100 GiB) |

The eight cases, with the requirements each cites:

| Case | Requirements | Covers |
|---|---|---|
| `cbrd_26659_oos_sql01_insert_select` | OOS-SQL-01 | single row, inline comparator, 100 rows of varying size, 1,000 rows of varying size, `INSERT … SELECT` between tables |
| `cbrd_26659_oos_sql02_update` | OOS-SQL-02 | UPDATE of the OOS-backed attribute, of the inline attribute alone, three and fifty repeats, single chunk → two chunks → single chunk, UPDATE from a subquery, UPDATE through a join |
| `cbrd_26659_oos_sql05_delete` | OOS-SQL-05 | DELETE by key, DELETE whose predicate reads the OOS-backed column, delete-all then re-insert, TRUNCATE comparator |
| `cbrd_26659_oos_sql06_rollback` | OOS-SQL-06 | INSERT + UPDATE rolled back, UPDATE rolled back, savepoint with partial rollback, each checked inside and after the transaction |
| `cbrd_26659_oos_sql06_constraints` | OOS-SQL-06 | primary-key, secondary-unique and NOT NULL violations, and a multi-row INSERT failing on its last row |
| `cbrd_26659_oos_sql06_triggers` | OOS-SQL-06, OOS-SQL-01 | a trigger reading an OOS-backed value, a trigger writing one, a REJECT leaving the stored value untouched, and the INSERT-trigger path |
| `cbrd_26659_oos_rep06_lob_neighbours` | OOS-REP-06, OOS-SQL-01, OOS-SQL-05 | four BLOB and one CLOB locator beside an OOS-backed column, `INSERT … SELECT` copying, and the source row deleted without taking the copy's external payload |
| `cbrd_26659_oos_sql02_mixed_chunks` | OOS-SQL-01, OOS-SQL-02 | the public CBRD-27006 mixed single-chunk/multi-chunk workload, reused with provenance |

## 2. The deliverable's spine: no size reaches a case unless the campaign may assert it

The specification lets a case rely on a placement only where the pinned gate (`DB_PAGESIZE/4`,
4,086 B at 16 KiB) and the normative four-record target (CBRD-27057, 4,060 B) agree, and where
the 16-byte pinned inline stub and the 24-byte normative one (CBRD-26950) do not separate the
answer. Ticket 13 checked that by hand for two rows. Ticket 19 has 1,178 OOS-backed fixture
rows, so the check is the code path instead:
`derive_ticket19_sizes.classify()` computes the demotion decision under both accountings and
**raises** when they disagree, when the record would still exceed the gate after demotion, or
when no eligible column is left inline — the last because such a row cannot tell largest-first
from any other order. `gen_ticket19_cases.py` routes every fixture row through it, so a size the
campaign may not assert cannot reach a case file at all.

The disagreement band for the family's main schema is `payload` 3,700–3,723 B. The self-test
asserts both that no fixture uses it **and that the band exists**, so the check cannot pass
vacuously. It also asserts the MD5 convention against ticket 13's promoted answer, that the
chunk-count function is not off by one at the single-chunk maximum, that all 1,100 generated
bulk values are distinct, and that every generated bulk row demotes exactly `payload` under both
accountings.

**Three things the derivation caught before the engine ran.**

1. **A tie in the reused CBRD-27006 workload.** Its row 1 has two equal-size eligible columns —
   `single1` and `single2` are both 3,500 B — so which one the largest-first loop demotes is not
   settled by the normative text, which says only "sort candidates by size descending". The
   sizes are kept verbatim, because the point of reusing a workload is to reuse it; the tie is
   recorded and no case asserts the identity of the moved column. The activation check is
   unaffected: the two columns being the same size, the chunk count and payload sum are
   identical whichever moved, which the self-test asserts together with a guard that the
   invariance comes from the equal sizes and not from the function.
2. **A label that had drifted from its value.** The bulk-1000 group's printed size and its
   printed digest were computed by two copies of the arithmetic, and one was edited without the
   other. Both now come from one `BulkGroup`, which also emits the SQL, and the self-test
   compares them.
3. **A period collision.** The bulk-1000 sizes originally cycled every 100 rows while the byte
   patterns cycled every 15, so 1,000 rows held only 300 distinct values. The size cycle is now
   97, coprime with 15, and the self-test asserts 1,000 distinct values.

## 3. Execution, review and promotion

Six invocations, all on the re-pinned build, 16 KiB pages, client-server, under
`campaign_ns.sh`, every one leaving `install conf drift 0, databases drift 0, worktree drift 0`:

| Invocation | Build | Purpose | Outcome |
|---|---|---|---|
| `inv-T19-0001` | release | first bootstrap, empty answers | 8 FAIL + 1 PASS as designed; **the trigger case's activation check refused it** (§5) |
| `inv-T19-0002` | release | bootstrap after restructuring the trigger case | 8 FAIL + 1 PASS; candidate review found two unexplained `Error:-493` (§6) |
| `inv-T19-0003` | release | bootstrap after the splitter fix | 8 FAIL + 1 PASS; **every candidate matched the oracle** |
| `inv-T19-0004` | release | green run with the promoted answers | **9 of 9 PASS**, proof `proven`, 0 mismatches |
| `inv-T19-0005` | debug | paired debug run | **9 of 9 PASS**, same answers, proof `proven` |
| `inv-T19-C001` | release | negative control, two planted defects | **FAIL, as a control must** (§7) |

Every new case was bootstrapped with an empty `.answer`, which is what makes CTP execute it and
write a candidate rather than skipping it and still exiting 0 (ticket 13 finding a).

**The review is mechanical, not by eye.** `review_candidates.py` checks each candidate against
1,190 (length, digest) pairs the derivation computes in Python without the engine, requires
every `*_ok` equality flag to be 1, requires each digest to agree with *its own* length column,
requires the aggregate totals and row counts the oracle names, and allows only the three error
identities derived from the engine's message catalogue before it ran. All eight promotions are
**unflagged**: every requirement they cite is `assertable` with policy `assert`, and no fixture
lies in a band where the two accountings disagree. The rename is proven mechanically — each
promoted answer hashes identically to its retained candidate, and `ctp_sql_records.py` appends
that proof to the review note.

Error identities were derived from the pin **before** the run and all four matched:

| Error | Code | Derivation |
|---|---|---|
| unique / primary-key violation | -670 `ER_BTREE_UNIQUE_FAILED` | `error_code.h:814`; the with-key variant `-886` is taken only when `print_key_value_on_unique_error` is on, and it defaults to false (`system_parameter.c:3133`) |
| NOT NULL violation | -631 `ER_NULL_CONSTRAINT_VIOLATION` | `error_code.h:765`, server insert path `query_executor.c:12450` |
| trigger rejection | -517 `ER_TR_REJECTED` | `error_code.h:609`; action time `BEFORE` because message 520 forbids REJECT with AFTER or DEFERRED |

CTP renders a failed statement as `Error:-<code>` and nothing else, so the answers carry the
identity and never the message text, whose B-tree and class OIDs differ between runs.

## 4. Activation evidence

Ticket 13's checker replays one hard-coded fixture. Eight cases need eight, so
`tools/activation_check_spec.sh` takes the fixture from a spec file and is otherwise the same
instrument: it starts its own `cub_server`, replays the case's own statements in the case's own
order, interleaves `SHOW HEAP OOS`, locates columns by name, and exits non-zero unless every
asserted observation holds. Because it runs client-server, in the case's own run mode, the
evidence is **`proven`** for all nine cases in both invocations — the reuse question the user
settled in decision O2 does not arise.

Each spec field is either an integer, which is asserted, or `-`, which is observed. Observation
is not leniency; it is what the authority policy requires for a quantity whose value is not
settled at the pin, and the spec states the expected value beside it. Two kinds appear:

- **chunk growth after an UPDATE** — at the pin every UPDATE allocates fresh chains even for
  attributes the statement did not assign (OOS-SQL-03, `observation-only`, superseded on paper
  by CBRD-27230), so a count after an UPDATE is current behaviour, never a requirement;
- **chunk survival after a DELETE** — OOS-SQL-05 says the chains are not removed at delete time
  in MVCC mode, and they are not, but the moment vacuum reclaims them is a background event, so
  asserting a count right after a DELETE would assert a race rather than the requirement.

What the checks do assert, all derived and all confirmed: one chunk and `Oos_recs_sumlen` 4,224
for the 4,200 B fixture row; **100 chunks and 457,600** for the bulk-100 group; **three chunks
and 23,564** for the reused workload's first row, which is where its multi-chunk topology stops
being an inference; and one chunk and 4,224 on the mirror table the trigger writes.

## 5. Finding T19-F1 — the OOS record gate is applied only on the server-side DML path

The first bootstrap's activation check refused the trigger case: its rows were not OOS-backed at
all. Isolating it produced a clean result.

| Probe (identical 4,564 B record each time) | `Has_oos_file` | `Oos_num_recs` | `Oos_recs_sumlen` |
|---|---:|---:|---:|
| INSERT into a table with no trigger | 1 | 1 | 4224 |
| INSERT into a table carrying an AFTER INSERT trigger | **0** | **0** | **0** |
| INSERT, **no trigger at all**, `insert_execution_mode` excluding server `INSERT … VALUES` | **0** | **0** | **0** |
| the same with the mode allowing it | 1 | 1 | 4224 |

The trigger is not the cause; the execution path is. `do_check_insert_server_allowed` calls
`sm_class_has_triggers (…, TR_EVENT_INSERT)` and leaves `server_allowed` at
`SERVER_INSERT_IS_NOT_ALLOWED` when a trigger is involved
(`src/query/execute_statement.c:12445-12456`); the client-side object-template path then
serializes the record itself and hands the server a finished one, so
`heap_attrinfo_determine_disk_layout` (`src/storage/heap_file.c:12310`) — the only place the
gate is applied, reached through `heap_attrinfo_transform_to_disk*` from
`src/transaction/locator_sr.c:7509` and `:7513` — is never called.

An UPDATE through the same path is worse: it **migrates an existing OOS-backed value back
inline** and drops its chain (`Oos_num_recs` 1 → 0 after an UPDATE that assigns only the inline
attribute of an already OOS-backed row on a table that has since acquired an UPDATE trigger).

**Severity.** No data is lost: every value reads back byte-identical on both paths, which is
precisely why no value-only test can see this — the hazard the campaign specification names in
its first paragraph. What is lost is the feature. For any table carrying a trigger, OOS is
silently off and the record-gate requirement OOS-REP-02 does not hold. It also interacts with
OOS-REP-08: a record above `heap_maxslotted_reclength` arriving on the client path cannot be
demoted, so it becomes a non-OOS `REC_BIGONE` instead.

**What was done about it.** Recorded as an **Engine defect** row in the matrix against
OOS-REP-02, with the probes as evidence; engine repair is out of the campaign's scope and the
final report keeps it visible. No answer file encodes it. The trigger case was restructured so
its fixture is built **before any trigger exists**, which makes the values the triggers read
genuinely OOS-backed, and a sixth group was added that inserts into a table already carrying an
INSERT trigger and asserts what that path does guarantee: every value is stored exactly.

## 6. Finding T19-F2 — a semicolon at the end of a comment line splits a case

The candidate review of `inv-T19-0002` found two `Error:-493` (`ER_PT_SYNTAX`) in the
mixed-chunks result that nothing in the case explains. CTP's SQL runner splits a case file into
statements at a line-terminal semicolon **without first stripping block comments**, so a header
comment line that happens to end with one is read as a statement boundary: the text before it
arrives as an unterminated comment and the text after it as a fragment starting mid-comment, and
both come back as syntax errors. Exactly one of the nine cases had such a line, and exactly that
one produced the errors.

The case still runs, so the two errors would have been promoted into the answer as expected
output and quietly stayed there. Rewording the line is the whole fix; the generator now refuses
to emit a case whose header comment has a line ending in a semicolon, so it cannot recur. **This
is a hazard for every ticket that writes a commented case file**, not only this one.

## 7. Negative controls

| Control | Mechanism under test | Planted defect | Result |
|---|---|---|---|
| `inv-T19-C001` (a) | the CTP comparison | one hex digit of the multi-chunk value's digest in the answer | case reported FAIL; attempt `FAIL`, which is what a `checker-validation` attempt must be |
| `inv-T19-C001` (b) | `activation_check_spec.sh` | `Oos_recs_sumlen` for row 1 set to 23,565 instead of 23,564 | `RESULT: activation NOT proven -- 1 assertion(s) failed`; evidence recorded `missing` |
| C2 (local) | `review_candidates.py` | one `tag_ok` flag flipped to 0; one hex digit of a digest changed | both reported; `RESULT: 2 problem(s)` |

The control attempt gets no manifest and never reaches the matrix, per the record contract.
Its bundle is `success-bulky` because a checker-validation attempt that FAILs is the checker
working, not a finding.

## 8. Coverage matrix

44 rows: 32 case rows, every one PASS with `proven` evidence, and 12 caseless rows. Of the 24
case rows that belong to ticket 19's own cases, 12 keep `gap_kind: none` and 12 are scoped. Of
the 12 caseless rows, 5 are ticket 41's, preserved verbatim along with the one withdrawn claim,
and 7 are new here. Re-merging the two manifests into the result is a no-op — 0 rows differ —
which is what demonstrates the hand-owned judgements survive the tooling.

Applying the ticket 35 F2 rule (as qualified by the delta review's D1) is the hand-owned part,
and `evidence/ticket19/apply_matrix_scoping.py` records it as code rather than as an edit:

| Requirement | Rows | Judgement |
|---|---|---|
| OOS-SQL-01, OOS-SQL-02 | 12 | **`none` kept.** The case asserts every clause of the statement at the seam; only the OOS-backed premise comes from the checker, which is the OOS-SQL-01 situation D1 names |
| OOS-SQL-05 | 4 + a companion | **Scoped, Delivery gap.** "The deleted record keeps its stubs and its value chains are not removed at delete time" is observed, not asserted (the vacuum race); "earlier snapshots can still read the value" needs a second session and is OOS-CL-01 |
| OOS-SQL-06 | 6 + a companion | **Scoped, Delivery gap.** "Including its OOS inline stubs whose head OIDs still reference live chains" and "no orphan chain remains" are not observable from portable SQL; `SHOW HEAP OOS` reports per-class totals, not per-record identity |
| OOS-REP-06 | 2 + a companion | **Scoped, Delivery gap.** The case asserts the LOB copy-semantics half; it does not assert that a locator was **demoted**, which needs a fixture where a locator is the largest candidate — Representation-family work, ticket 18 |
| OOS-SQL-03 | caseless | **Observation only, never a pass.** The chunk growth after an inline-attribute-only UPDATE is recorded as the pin's behaviour, so CBRD-27230's implementer has a before picture |
| OOS-SQL-04 | caseless | **Capability gap.** The accepted design is absent at the pin; asserting the pin's always-new-chain behaviour would enshrine superseded behaviour |
| OOS-SQL-07 | caseless | **Specification gap.** Blocks no case of this family — every case asserts value correctness, which holds under either answer — but stays visible |
| OOS-REP-02 | caseless | **Engine defect**, finding T19-F1 |

`hand_maintained` is set on the caseless rows only. On a case row it would freeze the history at
ticket 19's two invocations and silently drop every later run of the same case; a hand-set gap
kind needs no flag to survive, which the re-merge check demonstrates.

## 9. Timing and budget (for ticket 17)

Two different quantities are easy to confuse here, so both are given. `elapsed_seconds` in
`timing.txt` is the CTP launcher alone — the number ticket 13 reported as 39 s and ticket 15 as
44 s. `started_at` to `ended_at` is the whole invocation, which also contains the paired
activation checks, one per case.

| Quantity | Value |
|---|---|
| **CTP launcher, nine cases** | **40 s** (`elapsed_seconds` 41, 40, 40, 40, 42, 41 across six invocations) |
| Ticket 13's launcher, one case | 39 s; ticket 15's, one case, 44 s |
| **All nine cases' execution** | **1,099 ms** total (`summary.info` `totalTime`; the SQL runner reports no per-case time, only this total) |
| Whole invocation, `started_at` to `ended_at` | **114 s** for the green release run (16:54:06 → 16:56:00) |
| Of which the nine paired activation checks | ~74 s, about 8 s each — each one creates a database and starts and stops a server. They, not the launcher, are what grows with the case count |
| Invocation cap | 900 s — the cap applies to the launcher (40 s), and the whole invocation is still well inside it |
| Per-case cap | 120 s — not approached; the whole suite executes in under 1.1 s |
| Storage | 3.4 GiB for ticket 19; campaign total 46.3 of 100 GiB |

**This is the number ticket 17 needs.** Ticket 13 measured 39 s of launcher time for one case
and inferred the cost was per-invocation. Nine cases now measure 40 s of launcher time, of which
the cases themselves are 1.1 s — so the launcher's cost really is fixed, and the public suite
should be one invocation. The quantity that does scale with the case count is the paired
activation checks at about 8 s each, because each creates its own database and starts and stops
its own server; at nine cases they are already twice the launcher. If tickets 20 to 22 bring the
public suite to several dozen cases, batching the checks into fewer databases is the change that
matters, not splitting the CTP run.

## 10. Ticket 19 criteria checklist

| Criterion | Status |
|---|---|
| Cases for INSERT, UPDATE, DELETE, inline-only UPDATE, repeated updates (3 and 50), multi-chunk UPDATE, DELETE with count, delete-all then reinsert, ROLLBACK of INSERT+UPDATE, UPDATE then ROLLBACK, savepoints, bulk 100 and 1000+ | met (§1) |
| Constraint and trigger interactions; INSERT … SELECT; UPDATE through a join or subquery | met (§1); the trigger clause is qualified by finding T19-F1 (§5) |
| LOB locator columns per the demotion ADR: many locators, insert-select copying, delete not removing external payload | met (§1); locator **demotion** itself is not asserted and carries its own matrix row (§8) |
| The public CBRD-27006 workload reused with provenance, its missing topology coverage not inherited | met — provenance in the case header and §1; topology derived and asserted by the activation check, and the equal-size tie recorded rather than engineered away (§2) |
| Each case cites requirement IDs; expectations justified before running; whole-value checks are the oracle | met (§3), oracle in `expected-oracle.md` |
| Inline comparators; activation evidence per case; negative controls for new mechanisms | met (§4, §7) |
| Promotions reviewed; manifest and matrix updated through the tooling; each case under two minutes; committed locally only | met (§3, §8, §9); nothing pushed |

## 11. Open items and hand-offs

- **The specification's independent agent review is owed.** The acceptance decision requires a
  session that authored none of these artifacts to review them. It has not happened; the
  promotion reviewer field says so.
- **Three decisions this ticket made that the review should look at.** (1) The bootstrap
  invocations `inv-T19-0001..0003` executed the cases and their FAIL outcomes were **not merged
  into the matrix**: an empty answer is the mechanism by which a candidate is produced, not a
  finding, and merging them would set `ever_failed` on every row and report three failures in
  five attempts. Their manifests and attempt records are retained, and this is the only place the
  campaign has excluded an executed `original` attempt from the matrix. (2) No hand-derived
  assertion count is declared for the eight new cases; the reasoning is in the declaration.
  (3) `gap_kind` for the OOS-SQL-03 observation row is `Delivery gap` rather than `none`,
  because the schema allows `none` only for a latest PASS with proven evidence.
- **Ticket 18** owns the OOS-REP-06 locator-demotion fixture (§8) and the `OOS-REP-07`
  clause-level rows that ticket 39 item 3 requires of it.
- **Tickets 20 to 22** can reuse `tools/activation_check_spec.sh` and its spec format as they
  stand, and should keep bootstrapping each new case with an empty `.answer`. Finding T19-F2 (§6)
  applies to any commented case file.
- **The engine team**: finding T19-F1 (§5). Repair is out of the campaign's scope; the row keeps
  it visible.
- **Ticket 17**: §9.
