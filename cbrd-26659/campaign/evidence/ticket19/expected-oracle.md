# CBRD-26659 ticket 19 — expected output, justified before the engine ran

> Written 2026-09-15 (KST), **before** any CTP invocation of these cases, as the campaign
> specification requires ("Justify the expected whole value before running the engine. The first
> `.result` is a candidate; review it against the requirement, then promote by rename").
> Engine baseline `f4299ac0cd777a2a964c1f197ae5ebf9841a4936` (ticket 11, re-pinned by ticket 41);
> normative context `f6543de` + sha256 `c9daf3c4…`; requirement catalogue sha256 `0cc33c82…`.
> Derivation: [`derive_ticket19_sizes.py`](derive_ticket19_sizes.py) →
> [`derivation-output.txt`](derivation-output.txt), self-test → [`selftest-output.txt`](selftest-output.txt).
> Per-literal expected scalars: [`oracle-values.txt`](oracle-values.txt), produced by
> `gen_ticket19_cases.py --oracle`.

## 0. How to read this document

Ticket 19's cases make three kinds of claim, and they are justified differently.

| Kind | Example | How the expectation is justified |
|---|---|---|
| **Scalar value** | `payload_octets`, `payload_md5`, `payload_disk` | Arithmetic on the case's own literal, §1. Never observed. |
| **Boolean equality flag** | `payload_ok`, `tag_ok`, `b1_ok` | Required to be `1`. A `0` is a failure, never an answer. |
| **Behavioural outcome** | affected-row counts, error identities, what survives a ROLLBACK | Derived from the normative specification or from the pinned engine's source and message catalogue, cited per case below. |

Every `*_ok` flag in every case is expected to be **1**, and every `n_aliased` is expected to be
**0**. Those two facts are not repeated per statement below; only the outcomes that need a
reason are.

Nothing in this document was read off an engine run. A syntax smoke of the generated SQL was
run under `csql -S` on a throwaway database before the CTP invocation, and it is recorded in
§11 for what it is: a check that the statements parse and execute, not a source of any
expectation. Where §11 and this document disagree, this document is the oracle and the
difference is a finding.

## 1. The scalar rules

Every literal value in every case is `CAST(REPEAT('<h>', 2N) AS BIT VARYING)` for a hex
character `<h>` and a byte count `N`. Three scalars follow from that, with no engine involved:

| Scalar | Value | Source |
|---|---|---|
| `OCTET_LENGTH` | `N` | the value is exactly N bytes |
| `DISK_SIZE` | `ALIGN(5 + N, 4)` for `N ≥ 32` | `or_varbit_length_internal`, reproduced in ticket 11's `oos_boundaries.varbit_disk_len` |
| `MD5` | `md5("<h>" * 2N)` | CUBRID digests a BIT VARYING's lowercase hexadecimal form. Verified against ticket 13's promoted answer: `REPEAT('AA', 3000)` has `big_md5` `56d1d803c5f755f96819a2996fb65e43`, and `hashlib.md5(('aa'*3000).encode())` is the same — asserted by `derive_ticket19_sizes.py --self-test` |

[`oracle-values.txt`](oracle-values.txt) tabulates all 87 distinct literal values the eight cases use, with
these three scalars each. A candidate `.result` is reviewed against that table.

## 2. Why each fixture is an OOS fixture, and why that is assertable

The campaign may only assert a placement the pinned gate (`DB_PAGESIZE/4` = 4,086 B at 16 KiB)
and the normative four-record target (CBRD-27057 = 4,060 B) agree about, and that the 16-byte
pinned inline stub and the 24-byte normative stub (CBRD-26950) do not separate.
`derive_ticket19_sizes.classify()` enforces exactly that, and `gen_ticket19_cases.py` routes
**every** fixture row through it, so a size the campaign may not assert cannot reach a case
file. 1,178 OOS-backed rows and 7 inline comparator rows were verified this way (the count fell
by one when the trigger case was restructured; see section 8).

Schema C — `(id INT PRIMARY KEY, payload BIT VARYING, tag BIT VARYING)` — carries seven of the
eight cases. `tag` is always 300 B (308 B serialized), far above both eligibility floors (16 B
pinned, 24 B normative), and always stays inline **because the largest-first loop already
reached the target**, not because it was ineligible. `classify()` refuses a fixture that leaves
no eligible column inline, because such a row cannot tell largest-first from any other order.

The disagreement band for schema C is `payload` 3,700–3,723 B. No fixture uses it; the
self-test asserts that, and asserts that the band exists at all, so the check cannot pass
vacuously.

## 3. `cbrd_26659_oos_sql01_insert_select` — OOS-SQL-01

Requirement: **OOS-SQL-01**, "An inserted OOS-backed row reads back with every attribute
byte-identical to the inserted value, for single rows and bulk inserts of varying sizes."
Status `assertable`, policy `assert`.

| Statement group | Expected | Why |
|---|---|---|
| TEST 1, comparator row `id 2` | `payload_disk` 3008, `payload_octets` 3000, `tag_disk` 308, `tag_octets` 300, digests per §1, both flags 1 | record 3,364 B, below both gates: nothing demoted |
| TEST 2, OOS row `id 1` | `payload_disk` 4208, `payload_octets` 4200, `tag_disk` 308, `tag_octets` 300, digests per §1, both flags 1 | record 4,564 B, above both gates; `payload` alone is demoted under both accountings, leaving 372 B |
| TEST 3 | `n_rows` 2, `n_exact` 2, `n_aliased` 0 | both rows present, each holding its own value |
| TEST 4, helper | `n_helper` 1000, `min_i` 1, `max_i` 1000 | `a.i*100 + b.i*10 + c.i + 1` over three copies of 0..9 is a bijection onto 1..1000 |
| TEST 5, bulk-100 aggregate | `n_rows` 100, `n_payload_exact` 100, `n_len_exact` 100, `n_tag_exact` 100, `payload_octets_total` **455350**, `min` 4207, `max` 4900, `distinct_payloads` **100** | sizes are `4200 + 7i` for i = 1..100; the sum is `100·4200 + 7·5050` |
| TEST 5, samples | i = 1 → 4207 B `fe9a95e8f4ef30b0786b190dc13e2b94`; i = 50 → 4550 B `17ba3c759c10da08ec9582e4b191b38e`; i = 100 → 4900 B `32badabf72dc71e7306e874bab4bc8ab` | §1 applied to `char = HEX_ALPHABET[i mod 15]` |
| TEST 6, bulk-1000 aggregate | `n_rows` 1000, three exactness counts 1000, `payload_octets_total` **4147025**, `min` 4100, `max` 4196, `distinct_payloads` **1000** | sizes are `4100 + (i mod 97)`; 97 and 15 are coprime, so the 1,000 (pattern, length) pairs are all distinct — asserted by the self-test |
| TEST 6, samples | i = 1 → 4101 B `f103a64ccac79fd90fd3baa02da1fac5`; i = 500 → 4115 B `275d2a2cf5ad3946107f94fe7b54d3f2`; i = 1000 → 4130 B `52e965b79bc742b2be02890f3fd823c6` | as above |
| TEST 7, INSERT … SELECT | `n_copied` 100, `n_identical` 100, `n_same_length` 100, `n_same_digest` 100; the three samples repeat TEST 5's values | the copy must be value-for-value identical |

`distinct_payloads` is load-bearing: without it every aggregate above would also pass on a
table of 100 identical rows.

INSERT affected-row counts: 1 for each single-row INSERT, 1000 for the helper, 100 and 1000 for
the two bulk INSERT … SELECTs, 100 for the copy. DDL statements report 0.

## 4. `cbrd_26659_oos_sql02_update` — OOS-SQL-02

Requirement: **OOS-SQL-02**, "After an UPDATE of an OOS-backed attribute, or of an inline
attribute in an OOS-backed record, the updater and every later reader see the exact new value;
repeated updates leave the final value correct." Status `assertable`, policy `assert`.

| Step | Expected after it | Why |
|---|---|---|
| TEST 2, `payload` 4200 → 5000 B | row 1 reads `payload_octets` 5000, `payload_disk` 5008, md5 `671bea2aef111343e3b962b6a4c8d51c`, `tag` unchanged (`b`, 300 B) | the new value must be complete and the untouched attribute must not move |
| TEST 3, `tag` only | row 1 still reads `payload_octets` 5000 and the same digest; `tag` now `7`, 300 B | **the clause that matters**: an UPDATE that assigns only the inline attribute must leave the OOS-backed one exactly readable. At the pin the engine nevertheless allocates a fresh chain for it (OOS-SQL-03, observation-only) — that is invisible here and is not asserted |
| TEST 4, three updates | only the final value asserted: `3`, 4700 B, disk 4708 | "repeated updates leave the final value correct" |
| TEST 5, → 20000 B | `payload_octets` 20000, `payload_disk` 20008, md5 `b5f63998fd2419a0f87ffec3fc00eddb` | 20,008 B serialized is two chunks under the pinned 16-byte chunk header (max payload 16,288 B) **and** under the normative 24-byte one (16,280 B), so the topology claim is assertable |
| TEST 6, → 4400 B | `payload_octets` 4400, disk 4408, md5 `cc4706ab217b1c4c78cb21f802543076` | back to one chunk under both |
| TEST 7, fifty updates | only the final value asserted: char `6`, 4700 B | sizes `4200 + 10k` for k = 1..50, every one an assertable OOS fixture |
| TEST 8, subquery | row 1 reads the source table's value: `d`, 4600 B | the new value is produced by reading another table's OOS-backed attribute, so both the read and the write path are on the OOS path |
| TEST 9, join | row 2, formerly the 3,000 B inline comparator, now reads `d`, 4600 B and tag `5`, 300 B | an inline → OOS transition performed by a multi-table UPDATE |
| TEST 10 | `n_rows` 2, `n_carrying_src_value` 2, `n_aliased` 0, `distinct_tags` 2 | both rows now carry the same payload but different tags, which is why `distinct_tags` and not `distinct_payloads` is the aliasing guard here |

Affected-row counts: 1 for every UPDATE above (each matches one row), including the join.

## 5. `cbrd_26659_oos_sql05_delete` — OOS-SQL-05

Requirement: **OOS-SQL-05**, "A deleted OOS-backed row is gone for the deleter and for later
readers…". Status `assertable`, policy `assert`, with the authority note that the physical
half ("chains are not removed at delete time in MVCC mode") is assertable only through
SHOW HEAP OOS and only client-server.

| Step | Expected | Why |
|---|---|---|
| TEST 1 | four rows, ids 1–4, the survey lists their lengths and digests per §1 | rows 1, 3, 4 OOS-backed (4200, 4400, 4600 B), row 2 the inline comparator (3000 B) |
| TEST 2, `DELETE … WHERE id = 1` | **1** affected row; the survey lists ids 2, 3, 4 | ordinary primary-key delete |
| TEST 3, `DELETE … WHERE payload = <4400 B literal>` | **1** affected row; the survey lists ids 2, 4 | the predicate reads the OOS-backed column itself, so the scan must reconstruct the whole value to compare it; exactly one row matches because all payloads are distinct |
| TEST 4 | rows 2 and 4 still byte-exact | the delete of others must not disturb them |
| TEST 5 | `DELETE FROM t` affects **2**; `n_rows_after_delete_all` **0**; re-INSERT restores all four rows byte-exact | "delete all then re-insert", the table stays reusable |
| TEST 6 | `TRUNCATE` reports 0; `n_rows_after_truncate` **0**; re-INSERT restores all four rows | TRUNCATE is the comparator for TEST 5 |
| TEST 7 | `n_rows` 4, `n_exact` 4, `distinct_payloads` 4, `n_aliased` 0 | every re-inserted value is its own |

**Not asserted here:** that the deleted rows' value chains are still present. Portable SQL
cannot see it, and the claim is mode-dependent (ticket 11 §6: the standalone eager path deletes
synchronously). The paired activation check carries that half and the matrix row says so.

## 6. `cbrd_26659_oos_sql06_rollback` — OOS-SQL-06

Requirement: **OOS-SQL-06**, "ROLLBACK, savepoint rollback and statement failure restore the
previous record as-is, including its OOS inline stubs whose head OIDs still reference live
chains; no partial effect…". Status `assertable`, policy `assert`.

The case runs with `AUTOCOMMIT OFF`, the idiom the CTP SQL runner already accepts (for example
`sql/_13_issues/_12_1h/cases/bug_bts_6458.sql`).

| Step | Expected | Why |
|---|---|---|
| TEST 1 | two committed rows: 1 (`a`, 4200 B) and 2 (`c`, 3000 B) | the durable fixture |
| TEST 2, inside the transaction | three rows; row 1 reads `6`, 4500 B | the writer must see its own uncommitted OOS write |
| TEST 3, after `ROLLBACK` | two rows; **row 1 reads `a`, 4200 B, digest `1e895dba5e680251ad3db6a20449ca21`** | the undo must restore the original OOS value, not merely a value of the right length |
| TEST 4 | inside: `7`, 5000 B; after `ROLLBACK`: `a`, 4200 B again | an UPDATE-only transaction, so the restore is not masked by the INSERT of TEST 2 |
| TEST 5 | row 1 reads `9`, 4700 B and row 4 exists (`f`, 4800 B) | writes straddling the savepoint |
| TEST 6, after `ROLLBACK TO SAVEPOINT` | three rows? **No — two rows (1 and 2), and row 1 reads `8`, 4600 B** | everything after the savepoint is discarded (the 4700 B update and row 4); the 4600 B update, which happened before it, survives |
| TEST 7, after `COMMIT` | unchanged from TEST 6: row 1 reads `8`, 4600 B | the savepoint-surviving value is the durable one |

**Not asserted here:** that the aborted work left no orphan chain. That is a physical claim
portable SQL cannot make; eventual cleanup is OOS-CL-02 on the private shell seam.

## 7. `cbrd_26659_oos_sql06_constraints` — OOS-SQL-06 (statement failure)

Error identities were derived from the pinned engine **before** it was run:

| Error | Code | Derivation |
|---|---|---|
| unique / primary-key violation | **-670** `ER_BTREE_UNIQUE_FAILED` | `src/base/error_code.h:814`. `src/storage/btree.c:31437-31456` takes the with-key variant `ER_UNIQUE_VIOLATION_WITHKEY` (-886) only when `print_key_value_on_unique_error` is on; that parameter defaults to **false** (`src/base/system_parameter.c:3133-3139`) and the CTP configuration generated by `run_ctp_sql.sh` does not set it |
| NOT NULL violation | **-631** `ER_NULL_CONSTRAINT_VIOLATION` | `src/base/error_code.h:765`, raised on the server insert path `src/query/query_executor.c:12450` |

CTP renders a failed statement as `Error:-<code>` and nothing else (for example
`sql/_01_object/_04_trigger/_001_basic/answers/1011.answer`), so the answer carries the
identity and never the message text, whose B-tree and class OIDs would differ between runs.
The primary key is the INT column, never the OOS-backed one, so no violation can embed a
multi-kilobyte key.

| Step | Expected | Why |
|---|---|---|
| TEST 1 | two rows: 1 (`a`, 4200 B, uniq 100) and 2 (`c`, 3000 B, uniq 200) | the fixture |
| TEST 2 | `Error:-670`; the survey still lists exactly rows 1 and 2; row 1 still reads `a`, 4200 B | a PK violation by a row carrying OOS values stores nothing, and does not disturb the row it collided with |
| TEST 3 | `Error:-670`; survey unchanged | the same for a secondary unique constraint |
| TEST 4 | `Error:-631`; `n_rows_after_not_null_violation` **0** | a NOT NULL violation on an OOS-eligible column stores nothing |
| TEST 5 | `Error:-670`; survey still exactly rows 1 and 2 | **statement atomicity**: the three-row INSERT fails on its third row and must store neither of the first two. This is the clause of OOS-SQL-06 that would break loudly if the OOS write of rows 4 and 5 were published before the key check |
| TEST 6 | `n_rows` 2, `n_exact` 2, `distinct_payloads` 2 | the table is exactly the fixture |

## 8. `cbrd_26659_oos_sql06_triggers` — OOS-SQL-06, OOS-SQL-01

> **Revised 2026-09-15 after the first bootstrap invocation (`inv-T19-0001`).** The case's
> original shape created its rows *after* the triggers, and the paired activation check refused
> it: the rows were not OOS-backed at all. The cause is finding **T19-F1** (§13), an engine
> defect this ticket found. The case was restructured so its fixture is created before any
> trigger exists — which is what makes the values the triggers read genuinely OOS-backed — and
> this section was rewritten before the invocation that produced the promoted answers. The
> expectations below are unchanged in kind: every value must read back exactly.

Error identity derived before the run: **-517** `ER_TR_REJECTED` (`src/base/error_code.h:609`,
message 517). The action time is `BEFORE` because message 520 of the same catalogue states the
REJECT action cannot be used with `AFTER` or `DEFERRED`.

| Step | Expected | Why |
|---|---|---|
| TEST 1 | rows 1 (`a`, 4200 B, disk 4208) and 2 (`c`, 3000 B); row 1's flags 1 | the fixture is inserted while the table still has no trigger, so it takes the server-side path and really is OOS-backed — asserted by the paired activation check at that phase |
| TEST 2 | the log holds exactly `(1, 4200, 1e895dba5e680251ad3db6a20449ca21)`; row 1 still reads `a`, 4200 B with tag now `7` | **a trigger read the whole OOS-backed value**: an AFTER UPDATE trigger recorded `OCTET_LENGTH(obj.payload)` and `MD5(obj.payload)`, and both equal §1's values. A trigger that saw a truncated value would record a different digest |
| TEST 3 | mirror row 1 reads `a`, 4200 B with tag `8`; `n_mirrored` 1, `n_identical` 1, `n_same_digest` 1; the log now holds two rows, both `(1, 4200, 1e895dba…)` | **a trigger wrote the value**: the mirror row was produced entirely by the trigger's own INSERT, and is byte-identical to the row it copied |
| TEST 4 | `Error:-517` | the BEFORE UPDATE trigger rejects the statement |
| TEST 5 | row 1 still reads `a`, 4200 B, tag `8`; `n_log_rows` **2**, `n_mirror_rows` **1**; `n_rows` 2, `distinct_payloads` 2 | the rejected statement left the stored value exactly as it was **and fired neither AFTER trigger** — the counts are unchanged from TEST 3, which is how "no partial effect" is observable here |
| TEST 6 | row 1 of the INSERT-trigger table reads `a`, 4200 B exactly; its log holds `(1, 4200, 1e895dba…)` | the values an INSERT-trigger path stores are exact. That the row is **not** OOS-backed is finding T19-F1, recorded by the activation check and §13 — never by this answer |

**Not asserted here:** the placement of anything written through a trigger. Portable SQL cannot
see placement, and at this pin asserting it would be asserting the defect.

## 9. `cbrd_26659_oos_rep06_lob_neighbours` — OOS-REP-06, OOS-SQL-01, OOS-SQL-05

Requirement: **OOS-REP-06**, "Type-agnostic eligibility including LOB locators (ADR-0002)",
status `assertable`. The normative context states the rule and the copy semantics: eligibility
is type-agnostic, a BLOB/CLOB column's in-row value is its ELO locator string, only those
locator bytes would go to OOS, and "LOB copy semantics are preserved on the OOS path:
`heap_attrinfo_dbvalue_to_recdes` performs the same `db_elo_copy_with_prefix` step as the
inline writer before serializing."

| Step | Expected | Why |
|---|---|---|
| TEST 1 | two rows; `b1_len`…`b4_len` **64** each, `c1_len` **31** and **31** | each BLOB is `BIT_TO_BLOB` of a 64-byte BIT VARYING; each CLOB is the 29-character prefix plus `-1` / `-2` |
| TEST 2 | every flag 1 for row 1 | the OOS-backed payload, the inline tag, four BLOBs and one CLOB all read back exactly from a single row |
| TEST 3 | two rows copied; every flag 1 | `INSERT … SELECT` copies the OOS value and the locators together |
| TEST 4 | `n_source_rows` **0**; the copy still reports `b1_len`…`b4_len` 64 and `c1_len` 31 | **the clause that matters**: deleting the source must not take the copy's external payload with it. `db_elo_copy_with_prefix` gives the copy its own external file; had the copy borrowed the source's, these lengths would fail or error after the delete |
| TEST 5 | every flag 1 | and the copy's contents, not just its lengths, survive |

`DELETE FROM <source>` affects **2** rows.

**Not asserted here:** whether the locator string itself was demoted. Portable SQL cannot see
it, and beside a 4,200 B payload the largest-first loop stops long before a ~60-byte locator
becomes the largest candidate.

## 10. `cbrd_26659_oos_sql02_mixed_chunks` — OOS-SQL-01, OOS-SQL-02 (reused workload)

Provenance: the workload is `sql/_36_guava/cbrd_27006/cases/cbrd_27006_oos_ha_repl.sql`, added
by commit `1fdcaf93511acf0f94c71e0fdacc45e42fa34e16` ("[CBRD-27006] Add OOS HA replication
regression", 2026-07-20). Column sizes are reused verbatim: 3500/20000/3500 for row 1,
3600/21000/3400 for row 2, 3700/22000/3300 after the UPDATE.

What is **not** inherited: the original asserts `LENGTH` and whole-value equality only. It
makes no claim about chunk topology and cannot — nothing in it separates a one-chunk value from
a two-chunk one, and nothing in it shows the rows were OOS-backed at all. This case adds a
derived topology (20,000–22,000 B is two chunks under both chunk-header sizes, 3,300–3,600 B is
one under both) and a paired activation check that reads the counts rather than inferring them.

**A documented tie.** Row 1 has two equal-size eligible columns — `single1` and `single2` are
both 3,500 B — so which of them the largest-first loop demotes is not settled by the normative
text, which says only "sort candidates by size descending". This case asserts neither. The
sizes are kept as CBRD-27006 wrote them, because the point of reusing a workload is to reuse
it; the tie is recorded rather than engineered away. The activation check is unaffected: the
two columns being the same size, the chunk count and `Oos_recs_sumlen` are identical whichever
one moved — asserted by `derive_ticket19_sizes.py --self-test`, together with a guard that the
invariance comes from the equal sizes and not from the function.

| Step | Expected | Why |
|---|---|---|
| TEST 1 | row 1: octets 3500 / 20000 / 3500, digests per §1, three flags 1 | first row group |
| TEST 2 | rows 1 and 2, each with its own values; row 2 octets 3600 / 21000 / 3400 | the second INSERT must not disturb the first |
| TEST 3 | row 1 now 3700 / 22000 / 3300; row 2 unchanged | the UPDATE rewrites all three values of one row, including the multi-chunk one |
| TEST 4 | `n_rows` 2, `n_aliased` 0, `distinct_multi1` 2 | no column aliases another |

## 11. The syntax smoke, and what it is not

Before the CTP invocation the eight generated files were run once under `csql -S` on a
throwaway database (`/home/vimkim/.cub/campaign/cbrd-26659/ticket19/smoke`, database
`t19smoke`, pinned release install, standalone, outside every campaign port), with
`AUTOCOMMIT OFF;` / `AUTOCOMMIT ON;` translated to csql's `;autocommit` commands. Its only
purpose was to find statements that do not parse or execute. Six cases produced no error at
all; the two that are meant to produce errors produced exactly the ones derived above and no
others:

| Case | csql errors | Identities |
|---|---|---|
| `…_sql06_constraints` | 4 | three "unique constraint violations" (message 670 → -670) and one "SQL statement violated NOT NULL constraint" (631 → -631) |
| `…_sql06_triggers` | 1 | "The operation has been rejected by trigger" (517 → -517) |

The smoke ran **standalone**, so its physical behaviour differs from the case's own
client-server run in exactly the way OOS-SQL-05's authority note describes; no value in this
document comes from it, and no `.answer` is derived from it.

## 12. Promotion policy for these cases

Every requirement cited by ticket 19's cases — OOS-SQL-01, OOS-SQL-02, OOS-SQL-05, OOS-SQL-06,
OOS-REP-06 — is `assertable` with policy `assert`, and no fixture lies in a band where the
pinned and normative accountings disagree. Promotions are therefore **unflagged**: they need
the specification's independent agent review, not the user's sign-off.

Two requirements of the family are deliberately **not** claimed by any case, and appear in the
matrix as caseless rows instead:

- **OOS-SQL-04** (UPDATE chain reuse, CBRD-27230) — status `UNSUPPORTED`, authority `withhold`:
  the accepted design is absent at the pin, so reuse and notify-record expectations are
  withheld. Asserting the pin's always-new-chain behaviour would enshrine superseded
  behaviour as required.
- **OOS-SQL-07** (deferred-reuse text) — status `BLOCKED`, `Specification gap`, authority
  `withhold`: whether CBRD-27230 is a merge gate is an open question for the user.

**OOS-SQL-03** (M1 always-new-chain on UPDATE) is `observation-only`, policy `observe`. No
answer file carries it; the paired activation check records the chunk growth after the
inline-attribute-only UPDATE of §4 TEST 3 as an observation, and its matrix row is an
observation row, never a pass.

## 13. Finding T19-F1 — the OOS record gate is applied only on the server-side DML path

Found by the first bootstrap invocation's activation check (`inv-T19-0001`,
`activation/cbrd_26659_oos_sql06_triggers/assertions.txt`), then isolated to a three-table
probe and confirmed without any trigger at all.

**What happens.** A row whose record is 4,564 B — well above both the pinned 4,086 B gate and
the normative 4,060 B target — is stored **fully inline, with no OOS file created**, whenever
the statement is routed to CUBRID's client-side object-template path. Two independent ways in:

| Probe | `Has_oos_file` | `Oos_num_recs` | `Oos_recs_sumlen` |
|---|---:|---:|---:|
| INSERT into a table with no trigger (server path) | 1 | 1 | 4224 |
| the identical INSERT into a table carrying an AFTER INSERT trigger | **0** | **0** | **0** |
| the identical INSERT, no trigger, `insert_execution_mode` excluding server INSERT … VALUES | **0** | **0** | **0** |
| the same, `insert_execution_mode` allowing it | 1 | 1 | 4224 |

The trigger is therefore not the cause; the execution path is. An UPDATE through the same path
is worse: it **migrates an existing OOS-backed value back inline** and drops its chain
(`Oos_num_recs` 1 → 0 after an UPDATE that assigns only the inline attribute of an already
OOS-backed row on a table that has since acquired an UPDATE trigger).

**Why.** `do_check_insert_server_allowed` calls `sm_class_has_triggers (…, TR_EVENT_INSERT)`
and leaves `server_allowed` at `SERVER_INSERT_IS_NOT_ALLOWED` when a trigger is involved
(`src/query/execute_statement.c:12445-12456`); the same function bails out for several other
reasons, of which `insert_execution_mode` is the one probed above. The client path serializes
the object itself and hands the server a finished record, so
`heap_attrinfo_determine_disk_layout` (`src/storage/heap_file.c:12310`) — reached only through
`heap_attrinfo_transform_to_disk*` from `src/transaction/locator_sr.c:7509,7513` and the query
executor, and the **only** place the OOS record gate is applied — is never called.

**Severity.** No data is lost: every value reads back byte-identical on both paths, which is
precisely why no value-only test can see this. What is lost is the feature: for any table
carrying a trigger, OOS is silently off, records of any size stay in the heap, and the
record-gate requirement OOS-REP-02 does not hold. It also interacts with OOS-REP-08: a record
above `heap_maxslotted_reclength` arriving on the client path cannot be demoted, so it becomes
a non-OOS `REC_BIGONE` instead of being rejected or demoted.

**Disposition.** Recorded as an **Engine defect** in the coverage matrix against OOS-REP-02,
with the probes as evidence. Engine repair is out of the campaign's scope (map, "Out of
scope"); the final report keeps it visible. No answer file encodes it: the affected case
asserts values only, and the placement it would have asserted is observed by the activation
check instead.
