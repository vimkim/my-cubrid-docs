# CBRD-26659 — SQL operations and single-session transaction lifetime, public SQL (ticket 19)

> Observed: 2026-09-15 (KST). Engine baseline `f4299ac0cd777a2a964c1f197ae5ebf9841a4936`, re-pinned
> without the unit-test seams by ticket 41 (`release_gcc_nounit`, `debug_gcc_nounit`); normative
> context `f6543de` + sha256 `c9daf3c4…`; requirement catalogue sha256 `0cc33c82…` (ticket 12).
> Author: Claude Opus 5, for the [Adversarial OOS testcase campaign](/home/vimkim/gh/cb/CBRD-26659-oos-testcases-handover/.scratch/oos-adversarial/spec.md) ticket 19.
> Records: [`evidence/ticket19/`](evidence/ticket19/) — nine manifests, 83 attempt records, 83
> replay-bundle indexes, the coverage matrix, the pre-run oracle, the derivation and its
> self-test, the candidate review and its control, and the eight OOS-path evidence specs.
> Revision 2 (2026-09-15) closes the two-axis review of revision 1; §13 lists every change.
> Revision 3 (2026-09-16) closes the specification's independent review; §14 lists every change.
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
| Reviewed answers | the matching `answers/` directory, promoted by rename from `inv-T19-0003` (the update case re-promoted from `inv-T19-0008` after its relabelling) |
| Testcase commits (local only, nothing pushed) | `4a2590f36` → `38128e190` → `5c6c1264a` → `0eb64fc87` → `94bb3cb5a` → `35c815943`; base `b94995abf` (the verified `origin/develop` tip ticket 13 branched from) |
| Fixture derivation and its self-test | [`evidence/ticket19/derive_ticket19_sizes.py`](evidence/ticket19/derive_ticket19_sizes.py) |
| Case generator | [`evidence/ticket19/gen_ticket19_cases.py`](evidence/ticket19/gen_ticket19_cases.py) |
| Pre-run oracle | [`evidence/ticket19/expected-oracle.md`](evidence/ticket19/expected-oracle.md) |
| Candidate review | [`evidence/ticket19/review_candidates.py`](evidence/ticket19/review_candidates.py) |
| Spec-driven OOS-path evidence checker | [`tools/activation_check_spec.sh`](tools/activation_check_spec.sh) + eight specs under `evidence/ticket19/activation/` |
| Coverage matrix | [`evidence/ticket19/matrix.json`](evidence/ticket19/matrix.json) — 44 rows |
| Replay bundles | `~/.cub/campaign/cbrd-26659/ticket19/attempts/` (3.4 GiB; campaign total **36** of 100 GiB — disk usage, as §10) |

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
   recorded and no case asserts the identity of the moved column. The OOS-path evidence check is
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

Eleven invocations — nine that produced a manifest and two negative controls, which get none —
all on the re-pinned build, 16 KiB pages, client-server, under `campaign_ns.sh`, every one
leaving `install conf drift 0, databases drift 0, worktree drift 0`:

| Invocation | Build | Purpose | Outcome |
|---|---|---|---|
| `inv-T19-0001` | release | first bootstrap, empty answers | 8 FAIL + 1 PASS as designed; **the trigger case's OOS-path evidence check refused it** (§5) |
| `inv-T19-0002` | release | bootstrap after restructuring the trigger case | 8 FAIL + 1 PASS; candidate review found two unexplained `Error:-493` (§6) |
| `inv-T19-0003` | release | bootstrap after the splitter fix | 8 FAIL + 1 PASS; **every candidate matched the oracle** |
| `inv-T19-0004` | release | first run against the promoted answers | **9 of 9 PASS**, proof `proven`, 0 mismatches |
| `inv-T19-0005` | debug | paired debug run | **9 of 9 PASS**, same answers, proof `proven` |
| `inv-T19-C001` | release | negative control, two planted defects | **FAIL, as a control must** (§7) |
| `inv-T19-0006` | release | after adding the bulk-1000 OOS-path evidence phase | **9 of 9 PASS**; 1,000 chunks and 4,169,540 observed, matching the derivation |
| `inv-T19-0008` | release | bootstrap after the review's case changes | **8 of 9 PASS** against the unchanged answers, 1 FAIL — the update case, whose step label changed. The eight byte-identical answers are what prove the lower-casing altered no value |
| `inv-T19-0009` | release | final run, promotions recorded | **9 of 9 PASS**, proof `proven` |
| `inv-T19-0010` | debug | final paired debug run | **9 of 9 PASS**, proof `proven` |
| `inv-T19-C002` | release | the control re-run from the portable declaration | **FAIL, as a control must** |

Every new case was bootstrapped with an empty `.answer`, which is what makes CTP execute it and
write a candidate rather than skipping it and still exiting 0 (ticket 13 finding a).

**The review is mechanical, not by eye.** `review_candidates.py` checks each candidate against
1,190 (length, digest) pairs the derivation computes in Python without the engine, requires
every `*_ok` equality flag to be 1, requires each digest to agree with *its own* length column,
requires the aggregate totals and row counts the oracle names, and allows only the three error
identities derived from the engine's message catalogue before it ran. **Two of the eight promotions are flagged for the user's sign-off**, which the specification
requires of "every answer promotion whose case touches a Specification gap or an
observed-versus-normative disagreement":

- `cbrd_26659_oos_sql06_triggers` — this is the case finding T19-F1 came out of, and its sixth
  group deliberately exercises the deviating path, where the pin contradicts OOS-REP-02's
  normative record gate.
- `cbrd_26659_oos_sql02_update` — its third group is the inline-attribute-only UPDATE, exactly
  where the pin (a fresh chain per record version, OOS-SQL-03) and the accepted CBRD-27230
  design (OOS-SQL-04, withheld) disagree, and its OOS-path evidence spec is the matrix's cited
  observation source for OOS-SQL-03.

Neither answer encodes the disagreement — both assert values only, which hold under either
reading — but the rule is about the case, not the answer. **These two promotions are not
accepted until the user signs off.** The other six are unflagged: every requirement they cite is
`assertable` with policy `assert`, and no fixture lies in a band where the two accountings
disagree. The rename is proven mechanically — each
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

## 4. OOS-path evidence

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
for the 4,200 B fixture row; **100 chunks and 457,600** for the bulk-100 group and **1,000
chunks and 4,169,540** for the bulk-1000 group; **three chunks and 23,564** for the reused
workload's first row, which is where its multi-chunk topology stops being an inference; and one
chunk and 4,224 on the mirror table the trigger writes.

**Evidence follows the execution path, not the case.** Finding T19-F1 is precisely a path that
skips the record gate, so a phase that proves `INSERT … VALUES` demotes proves nothing about the
other paths a case uses. Four more phases were added for that reason, each on its own table so
its chunk count is unambiguous rather than mixed with the dead chains of earlier steps:

| Phase | Path it proves runs the gate | Asserts |
|---|---|---|
| `sql01/copy` | `INSERT … SELECT` between tables | 100 chunks, 457,600 |
| `rep06/copy` | `INSERT … SELECT` carrying five LOB locators | 1 chunk, 4,224 |
| `sql02/subquery_update` | UPDATE whose value is a subquery over another table | 1 chunk, 4,624 |
| `sql02/join_update` | multi-table UPDATE | 1 chunk, 4,624 |

Each of the last two starts from an inline row on a fresh table, so the single chunk afterwards
is the one that write created.

Each check also runs `checkdb -S` on the database it built. **All eighteen exited 0** — nine on
the release build and nine on the debug build, the latter being the one that would abort on a
failed internal assertion. Ticket 16 recorded that `checkdb` does not examine OOS payloads or
chunk headers, so this is not a statement about OOS contents; it is a statement that none of
these workloads left the heap, the indexes or the file tables inconsistent.

## 5. Finding T19-F1 — the OOS record gate is applied only on the server-side DML path

The first bootstrap's OOS-path evidence check refused the trigger case: its rows were not
OOS-backed at all. Isolating it produced a clean result.

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
| `inv-T19-C001`/`C002` (a) | the CTP comparison | one hex digit of the multi-chunk value's digest in the answer | case reported FAIL; attempt `FAIL`, which is what a `checker-validation` attempt must be |
| `inv-T19-C001`/`C002` (b) | `activation_check_spec.sh` | `Oos_recs_sumlen` for row 1 set to 23,565 instead of 23,564 | `RESULT: activation NOT proven -- 1 assertion(s) failed`; evidence recorded `missing` |
| C2 (local) | `review_candidates.py` | one `tag_ok` flag flipped to 0; one hex digit of a digest changed | both reported; `RESULT: 2 problem(s)` |

The control is reproducible from a clone: `evidence/ticket19/make_control_c1.sh` builds the
planted scenario by reading the promoted answer and flipping the last hex digit of the digest it
finds under the `multi1_md5` column — located by column name, so a later re-promotion cannot
turn the control into a no-op — and the planted spec is checked in beside it. The script only
ever reads from the testcase repository.

The control attempt gets no manifest and never reaches the matrix, per the record contract.
Its bundle is `success-bulky` because a checker-validation attempt that FAILs is the checker
working, not a finding.

## 8. Coverage matrix

44 rows: 32 case rows, every one with a latest outcome of PASS and `proven` evidence, and 12
caseless rows. Of the 24 case rows that belong to ticket 19's own cases, 12 keep `gap_kind: none`
and 12 are scoped. Of the 12 caseless rows, 5 are ticket 41's, preserved verbatim along with the
one withdrawn claim, and 7 are new here. Re-merging every manifest into the result is a no-op —
0 rows differ — which is what demonstrates the hand-owned judgements survive the tooling.

**One row records a failure** (ticket 44 F1, 2026-09-16).
`OOS-SQL-02/cbrd_26659_oos_sql02_update/16384-release-cs` carries `ever_failed: true` and one
failure in four attempts, from `att-T19-0075` of `inv-T19-0008`. Its latest outcome is still
PASS, because `inv-T19-0009` is later; its `attribution.target` is `harness` and says the cause
was this revision's relabelling of the case's third step against an answer not yet re-promoted,
explicitly not the engine. The invocation was missing from the matrix altogether until ticket 44
merged it — see §14.

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

## 9. Factors covered, and what is excluded

The specification asks that "selected factors, feasible combinations and exclusions are listed
so the claim is auditable". For this family:

| Factor | Levels covered |
|---|---|
| operation | INSERT, INSERT … SELECT, UPDATE (direct, subquery, join), DELETE (by key, by OOS-column predicate, all), TRUNCATE, ROLLBACK, savepoint rollback, statement failure |
| row count per statement | 1, 3, 100, 1,000 |
| value size | 3,000 B inline comparator; 4,100–5,000 B single chunk; 20,000–22,000 B two chunks |
| column shape | one demoted column beside one inline eligible column; two demoted beside one inline (reused workload); five LOB locators beside a demoted column |
| build mode | release and debug, every case, every invocation |
| page size | 16 KiB only |
| run mode | client-server only |

Excluded, each for a stated reason rather than by omission:

- **Prepared statements with host variables** (an attack dimension of OOS-SQL-01 and OOS-SQL-02).
  A CTP SQL case is a file of statements; the runner exposes no way to bind host variables, so
  the seam cannot express it. It belongs to the private shell seam, where a client program can
  be written. **Not covered anywhere in the campaign yet.**
- **4 and 8 KiB pages.** The fast tier is 16 KiB by the budget decision; ticket 11 left
  client-server at 4 and 8 KiB to ticket 17.
- **Standalone mode.** OOS-SQL-05's physical clause is explicitly mode-dependent, and the public
  suite runs client-server only.
- **More than five LOB locator columns.** The ticket asks for "many locator columns"; four BLOBs
  and one CLOB is what these cases carry. A record built from ten or more locators and nothing
  else is the fixture that would make a locator the largest candidate, and that is the
  OOS-REP-06 locator-demotion row's work, which §8 assigns to ticket 18.

## 10. Timing and budget (for ticket 17)

Two different quantities are easy to confuse here, so both are given. `elapsed_seconds` in
`timing.txt` is the CTP launcher alone — the number ticket 13 reported as 39 s and ticket 15 as
44 s. `started_at` to `ended_at` is the whole invocation, which also contains the paired
OOS-path evidence checks, one per case.

| Quantity | Value |
|---|---|
| **CTP launcher, nine cases** | **40–55 s** (`elapsed_seconds` 41, 40, 40, 40, 42, 41, 41, 55, 42 across nine invocations; the 55 is the one run that shared the host with another build) |
| Ticket 13's launcher, one case | 39 s; ticket 15's, one case, 44 s |
| **All nine cases' execution** | **1,099 ms** total (`summary.info` `totalTime`; the SQL runner reports no per-case time, only this total) |
| Whole invocation, `started_at` to `ended_at` | **114 s** for the first all-PASS release run; **137 s** for the final one, which added four OOS-path evidence phases (17:24:00 → 17:26:17) |
| Of which the nine paired OOS-path evidence checks | ~74 s initially and ~82 s at the end, about 8–9 s each — each one creates a database and starts and stops a server. They, not the launcher, are what grows with the case count |
| Invocation cap | 900 s — the cap applies to the launcher (40 s), and the whole invocation is still well inside it |
| Per-case cap | 120 s — not approached; the whole suite executes in under 1.1 s |
| Storage | 3.4 GiB for ticket 19; campaign total 36 of 100 GiB. **Disk usage** (`du`), which is what the budget decision's 100 GiB working-storage cap measures. Apparent size (`du --apparent-size`) reads 4.0 and 46.3 GiB, because CUBRID's volumes are sparse; §1 carried the apparent figure for the campaign beside the disk figure for ticket 19 until ticket 44 F7 |

**This is the number ticket 17 needs.** Ticket 13 measured 39 s of launcher time for one case
and inferred the cost was per-invocation. Nine cases now measure 40 s of launcher time, of which
the cases themselves are 1.1 s — so the launcher's cost really is fixed, and the public suite
should be one invocation. The quantity that does scale with the case count is the paired
OOS-path evidence checks at about 8 s each, because each creates its own database and starts
and stops its own server; at nine cases they are already twice the launcher. If tickets 20 to 22 bring the
public suite to several dozen cases, batching the checks into fewer databases is the change that
matters, not splitting the CTP run.

## 11. Ticket 19 criteria checklist

| Criterion | Status |
|---|---|
| Cases for INSERT, UPDATE, DELETE, inline-only UPDATE, repeated updates (3 and 50), multi-chunk UPDATE, DELETE with count, delete-all then reinsert, ROLLBACK of INSERT+UPDATE, UPDATE then ROLLBACK, savepoints, bulk 100 and 1000+ | met (§1) |
| Constraint and trigger interactions; INSERT … SELECT; UPDATE through a join or subquery | met (§1); the trigger clause is qualified by finding T19-F1 (§5) |
| LOB locator columns per the demotion ADR: many locators, insert-select copying, delete not removing external payload | met (§1); locator **demotion** itself is not asserted and carries its own matrix row (§8) |
| The public CBRD-27006 workload reused with provenance, its missing topology coverage not inherited | met — provenance in the case header and §1; topology derived and asserted by the OOS-path evidence check, and the equal-size tie recorded rather than engineered away (§2) |
| Each case cites requirement IDs; expectations justified before running; whole-value checks are the oracle | met (§3), oracle in `expected-oracle.md` |
| Inline comparators; OOS-path evidence per case; negative controls for new mechanisms | met (§4, §7) |
| Promotions reviewed; manifest and matrix updated through the tooling; each case under two minutes; committed locally only | met (§3, §8, §9); nothing pushed |

## 12. Open items and hand-offs

- **The user's sign-off is owed on two promotions**, `cbrd_26659_oos_sql06_triggers` and
  `cbrd_26659_oos_sql02_update` (§3). Until it is given, those two answers are promoted in the
  repository but not accepted by the campaign.
- ~~**The specification's independent agent review is owed.**~~ Done 2026-09-15 by a session that
  authored none of these artifacts: verdict **REVISE**, seven of seven criteria substantively met,
  all three negative controls validated by re-execution, two blocking findings. Its record is
  [`CBRD-26659-ticket19-independent-review_f4299ac_claude.md`](CBRD-26659-ticket19-independent-review_f4299ac_claude.md)
  and its findings are closed by campaign ticket 44 in §14. The two-axis review closed in §13 was
  commissioned by the authoring session and is not that review, which is what the promotion
  reviewer field says.
- **Three decisions this ticket made that the review looked at.** (1) **Four** invocations, not
  three, had their executed `original` attempts left out of the matrix, and revision 2 of this
  section said three. The bootstrap invocations `inv-T19-0001..0003` are the three the stated
  justification covers: an empty answer is the mechanism by which a candidate is produced, not a
  finding, and merging them would set `ever_failed` on every row of the family and report three
  failures in five attempts. `inv-T19-0008` is the fourth, and **its answers were not empty** —
  it ran the lower-cased cases against the answers promoted from `inv-T19-0003`, eight of them
  came back byte-identical, which is what §13's T5 row rests on, and it is the invocation the
  promoted update answer was re-promoted from. Nothing excused it, and the independent review's
  F1 found it. Since 2026-09-16 `inv-T19-0008` is merged and the three bootstraps are a dated
  `accepted_exclusions` entry the user accepted, so the matrix now carries every executed
  attempt or names the exclusion (§14). (2) No hand-derived assertion count is declared for the
  eight new cases; the reasoning is in the declaration. (3) `gap_kind` for the OOS-SQL-03
  observation row is `Delivery gap` rather than `none`, because the schema allows `none` only for
  a latest PASS with proven evidence.
- **Ticket 18** owns the OOS-REP-06 locator-demotion fixture (§8) and the `OOS-REP-07`
  clause-level rows that ticket 39 item 3 requires of it.
- **Tickets 20 to 22** can reuse `tools/activation_check_spec.sh` and its spec format as they
  stand, and should keep bootstrapping each new case with an empty `.answer`. Finding T19-F2 (§6)
  applies to any commented case file.
- **The engine team**: finding T19-F1 (§5). Repair is out of the campaign's scope; the row keeps
  it visible.
- **Ticket 17**: §9.

## 13. Revision 2 — closing the commissioned two-axis review (2026-09-15)

A Standards and a Spec review were commissioned by the authoring session over revision 1. They
are not the specification's independent review (§12), but their findings were real and are
closed here.

| # | Axis | Finding | Resolution |
|---|---|---|---|
| S1 | Spec | OOS-path evidence covered `INSERT … VALUES` only, while the matrix claimed `proven` for rows resting on `INSERT … SELECT`, subquery UPDATE and join UPDATE. Finding T19-F1 is itself proof that the path decides whether the gate runs | **Blocking, fixed.** Four phases added (§4), each on its own table. All four assert and all four hold |
| S2 | Spec | No factor list or exclusions, so the coverage claim was not auditable; prepared statements with host variables were silently absent | **Fixed.** §9 lists factors and levels, and four exclusions with reasons. Host variables are recorded as not covered anywhere in the campaign yet |
| S3 | Spec | The user sign-off gate was skipped: all eight promotions were `flagged_for_user: false` | **Fixed.** Two are now flagged with the reason in the promotion record (§3). Six remain unflagged |
| S4 | Spec | `cbrd_26659_oos_sql02_update` printed "the OOS-backed value must not move" into its **promoted answer**, and "must not move" is CBRD-27230 reuse, which the catalogue withholds — at the pin it does move | **Blocking, fixed.** Relabelled to "still reads back exactly", which holds under both readings, and the answer re-promoted from `inv-T19-0008` |
| S5 | Spec | The triggers case earned OOS-SQL-01 rows at `gap_kind: none` although its sixth group is on the path that is not OOS-backed | **Fixed.** Those two rows now say which groups carry the coverage and that group 6 contributes none |
| T1 | Standards | The shared header block said `tag` and quoted an `'aa' * 4200` example in the reused four-column workload, which has neither | **Fixed.** The two facts that differ per schema are now parameters; every case's example names a value that case contains |
| T2 | Standards | `apply_matrix_scoping.py` wrote the matrix raw, bypassing `write_record`'s validate-before-write gate | **Fixed.** It writes through `write_record` |
| T3 | Standards | Absolute machine paths in both declarations, so the control could not be replayed from a clone | **Fixed.** The checker resolves a relative spec against the campaign directory; both declarations carry repository paths, and `make_control_c1.sh` rebuilds the control |
| T4 | Standards | `review_candidates.py` documented a `--strict` flag that does not exist | **Fixed**, and a sixth check added: a case yielding no equality flag at all now fails, so a rename that stopped the flags being recognised cannot pass silently |
| T5 | Standards | Uppercase SQL, while the case already in this directory and the dominant style of `sql/_36_guava` are lower case | **Fixed.** `lowercase_sql` leaves comments and string literals alone; eight of the nine answers came back byte-identical from `inv-T19-0008`, which is the proof it changed no value |

Two findings were considered and deliberately not acted on:

- **`activation_check_spec.sh` duplicates about 54 lines of `activation_check_cs.sh`**, and the
  older one is a one-phase special case of the newer. Retiring it would be right on the merits,
  but tickets 13, 15 and 41's sealed records cite it by name and by hash, and ticket 13's case
  still runs it in this ticket's declaration. The duplication is boilerplate — server start,
  port refusal, identity file — and is left in place rather than destabilising sealed evidence.
- **Building that checker here at all**, when ticket 15 owns the campaign tooling. Ticket 15 is
  resolved and its checker replays exactly one hard-coded fixture; eight cases need eight. The
  new checker is spec-driven and is handed to tickets 20 to 22 in §12, which is the shape ticket
  15's own hand-off asked for.

`bit_length` was also noted as dropped relative to ticket 13's case. It is redundant with
`octet_length` — the same fact times eight — and its absence is not claimed otherwise in any
header. No change.

## 14. Revision 3 — closing the specification's independent review (2026-09-16)

The review the specification requires ran on 2026-09-15, by a session that authored none of these
artifacts and reached them without this report's framing. Verdict **REVISE**: seven of seven
criteria substantively met, all three negative controls validated by re-execution, replay and
cleanup evidence complete, drift zero on all eleven invocations under an independent re-diff, and
two blocking findings. Its record is
[`CBRD-26659-ticket19-independent-review_f4299ac_claude.md`](CBRD-26659-ticket19-independent-review_f4299ac_claude.md).
Campaign ticket 44 carries its findings; every change below is in this repository. **No case,
answer or testcase commit changed and no CTP invocation was made**: commits `4a2590f36` through
`35c815943` stand exactly as they were, and `gen_ticket19_cases.py --check` still reports all
eight cases identical to the checked-in files.

| # | Finding | Resolution |
|---|---|---|
| F1 | **Blocking.** `inv-T19-0008` executed nine cases, one FAILed, and none of its nine attempt records appeared in any matrix row — while §12 said the three bootstraps were the only executed `original` attempts the campaign had excluded | **Fixed.** Merged through `tools/matrix_merge.py`: 15 (requirement, case) rows gain an attempt, and `OOS-SQL-02/cbrd_26659_oos_sql02_update/16384-release-cs` takes `ever_failed: true` with one failure in four (§8). `evidence/ticket19/apply_ticket44_findings.py` writes the `harness` attribution the merge cannot decide. §12 is corrected from three excluded invocations to four, with the bootstrap justification stated only for the three it covers |
| F2 | **Blocking.** `tools/declarations/ticket19-public-sql-operations.json` said `flagged_for_user: false` on all nine cases while `promotions.json` and `inv-T19-0009` said `true` for two, so a manifest regenerated from the portable declaration would carry no sign-off gate | **Fixed**, and made unrepeatable. The declaration carries `true` and the reason for both cases, and `ctp_sql_records.verified_promotions` now refuses a `promoted` entry whose flag differs from the declaration's, or whose declaration omits it. `tools/selftest_promotions.py` carries both refusals |
| F3 | 64 of 83 recorded bundle hashes no longer verified: nine attempts share one bundle root and each record's digest was taken while the directory was still growing | **Fixed**, after the contract question it rests on was settled. The user chose **one bundle per invocation, referenced by its attempt records** on 2026-09-16; it is recorded in the traceability-schemas change log and in the two schemas' field descriptions. `evidence/ticket19/apply_ticket44_record_corrections.py` corrects the 64 attempt records and bundle indexes, the 64 matching `bundle_hash` entries in eight manifests, and the 30 matrix `run.manifest_hash` seals over those manifests. Each attempt record's `notes` say what it used to carry; nothing was re-hashed silently and no bundle was touched |
| F4 | The bootstrap exclusion was reasoned in prose and `accepted_exclusions` was `[]` | **Accepted by the user on 2026-09-16.** Seven dated entries, one per requirement the bootstrap cases cite, each naming the attempt ids it excludes and derived from the three manifests rather than typed |
| F5 | `derive_ticket19_sizes.py`'s tie-invariance check compared one literal with itself and re-typed the fixture's sizes | **Fixed.** The reused CBRD-27006 sizes have one home, `REUSED_27006_ROWS`, which the `FIXTURES` table, `gen_ticket19_cases.case_mixed_chunks()` and the self-test all read. The self-test derives both demotion sets from it and asserts the tie still exists; making the two columns unequal now fails the self-test, which was checked |
| F6 | The report used "activation" 24 times and the glossary's *OOS-path evidence* zero, and "green" three times | **Fixed.** Fifteen prose occurrences, the §4 heading among them, use the canonical term; the eight filename and path occurrences and the checker's literal `RESULT: activation NOT proven` output are unchanged, because sealed records of tickets 13, 15 and 41 cite the checker by name and hash. "Green" is gone from §3 and §10 |
| F7 | Three numbers did not hold: §3's "Six invocations" above a table of eleven; §1's 46.3 GiB against §10's 36; and the promotion records' claim that the oracle "was written before any CTP invocation", which no artifact can show | **Fixed.** §3 says eleven, nine with manifests and two controls. §1 says 36 GiB and both places now name the measure: disk usage, which is what the budget's 100 GiB cap is in — 46.3 was the apparent size of the same tree, inflated by the holes in CUBRID's sparse volumes. All 24 promotion reviewer notes drop the unfalsifiable clause, say they dropped it, and rest on the checkable half of the same sentence: the derivation reproduces each answer's `(length, digest)` pairs without the engine. Sealing the oracle in a bundle belongs to the next invocation that runs |
| O1 | The record checker validates shapes, so nothing mechanical could have caught F1 | **Landed** in ticket 15's checker: `check_matrix_completeness` requires every retained `original` attempt to reach a matrix history or a dated exclusion naming the attempt id. `tools/selftest_matrix_completeness.py` plants F1's defect back and requires the check to report it. **It reports one item on the current tree and it is not ticket 19's**: `att-T15-C04`, a ticket 15 control recorded as `original` with a manifest while its two siblings are `checker-validation` without one. Left reported rather than narrowed away; ticket 15 owns it |
| O2 | Whether the sign-off gates the promotion or the acceptance, and who supplies the review note and flag | **Settled by the user on 2026-09-16: acceptance**, as this ticket read it. Tickets 20 to 22 promote under that reading. The deviation from ticket 36 decision 8 — an agent supplied the review note and the flag for these eight promotions — is **ratified** as a disclosed one-off; the flag now lives in the declaration as well, which is what makes it checkable |

**Still owed, and owed to the user alone.** The sign-off on `cbrd_26659_oos_sql06_triggers` and
`cbrd_26659_oos_sql02_update` (§3, §12). Until it is given those two answers are promoted in the
repository and not accepted by the campaign, which is unchanged by this revision.

**For tickets 20 to 22.** Two of the review's blocking findings were consequences of revision 2
itself: `inv-T19-0008` was created *by* that revision, and the declaration and the promotion
records were repaired in the same pass without being checked against each other. A revision that
adds records is the moment to re-run the completeness checks, not only the schema ones — which is
now a check rather than a note (O1), and should be run before their matrices are merged.

## 15. Revision 4 — the delivered cases say what they are (2026-09-21)

Campaign ticket 45 item 2 decided on 2026-09-18 that the generator is not delivered and that the
cases it emitted say so themselves, once, dated and without a pointer; campaign ticket 47 applied
it. Every generated case's header now ends with a provenance paragraph — generated once by the
campaign on 2026-09-19 from the pinned engine's record accounting at
`f4299ac0cd777a2a964c1f197ae5ebf9841a4936`, fixture sizes derived from that accounting rather than
chosen, hand-maintained from that date — and the sentence that named `derive_ticket19_sizes.py` by
path keeps its derivation statement and loses the path, under the same rule: a pointer into this
repository advertises a dependency a CUBRID reviewer cannot follow. It does not say "do not edit",
because from that date nothing but a person maintains the cases. The hand-written ninth case,
`cbrd_26659_oos_rep02_largest_first`, says it is hand-written, so the directory reads one way. The
private case's fixture comment lost its `derive_case_sizes.py` pointer the same way.
`gen_ticket19_cases.py` emits the statement from one dated constant and its docstring now records
that it is not delivered; `--check` still reports all eight cases identical to the checked-in files
and the activation specs it also emits are byte-unchanged. **No case body, no answer and no
promotion changed**; the sign-off owed in §12 is exactly as it was.

The change is comment lines only — no statement, literal or whitespace outside a comment — so the
proof is the one §13's T5 rested on: the scenario ran once more through `run_ctp_sql.sh` on the
pinned release build, `inv-T47-0001` (2026-09-19, CTP invocation 43 s), all nine cases in `okList`,
every result byte-identical to its answer, OOS-path evidence `proven` on all nine, drift zero; the
private case ran once through `run_ctp_shell.sh`, `inv-T47-0002` (2026-09-21, 17 s), PASS with the
same 17 executed, 17 OK, 1 SKIP as `inv-T41-0002`. Both runs used the one port block the wrappers
know, so they ran one after the other rather than in ticket 37's two lanes. Testcase commits
`4f06f9bdd` (public, after `35c815943`) and `66b66f1f0` (private, after `c4fe45173`), nothing
pushed. Records are under `evidence/ticket47/`, and both manifests were merged into a **per-ticket
copy** of this ticket's matrix, `evidence/ticket47/matrix.json` — 44 rows before and after, 16
rows gain one history entry, no gap kind or hand-set field changed — because which matrix file is
canonical is ticket 48 item 48.6's decision to make, so `evidence/ticket19/matrix.json` is as it
was. §1's table still names the generator and the derivation as this repository's artifacts, which
they remain; what changed is that the delivered cases no longer cite them.
