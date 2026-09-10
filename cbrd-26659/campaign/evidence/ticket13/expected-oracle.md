# Ticket 13 — expected output, justified before the engine was run

> Written 2026-09-10 (KST), **before** the first CTP invocation of
> `sql/_36_guava/cbrd_26659/cases/cbrd_26659_oos_rep02_largest_first.sql`.
> Engine baseline `f4299ac0cd777a2a964c1f197ae5ebf9841a4936` (ticket 11).
> Requirement catalogue `catalogue/requirements.json` (ticket 12).
> Derivation: [`derive_case_sizes.py`](derive_case_sizes.py), whose arithmetic comes from
> ticket 11's [`oos_boundaries.py`](../../ticket11-evidence/oos_boundaries.py).

The campaign specification requires the oracle to be justified independently of the
observed engine result. This file is that justification. The CTP first-run `.result` is a
candidate; promotion to `answers/` happens only after the `.result` is reviewed against
what is written below. A `.result` that disagrees with this file is a finding, not a new
expectation.

## Requirements cited

| ID | Statement (catalogue) | Status / policy |
|---|---|---|
| `OOS-REP-01` | Records at or below the gate stay inline; no attribute is demoted. | assertable / assert |
| `OOS-REP-02` | Above the gate, eligible variable values are demoted largest-first until the record is at or below the target; smaller eligible values may remain inline; every value reads back exactly. | assertable / assert |
| `OOS-SQL-01` | An inserted OOS-backed row reads back with every attribute byte-identical. | assertable / assert |

None of the three is `BLOCKED` or `observation-only`, and neither fixture row falls in a
disputed band (below), so the answer promotion is **unflagged**: independent agent review
only, no user sign-off.

## Why the placement is assertable

`derive_case_sizes.py` computes the demotion decision twice for each row — once with the
pinned accounting (record gate `DB_PAGESIZE / 4` = 4,086 B, 16-byte inline stub) and once
with the normative accounting (CBRD-27057 four-record target = 4,060 B, CBRD-26950
24-byte stub) — and both agree row by row:

| Row | `DISK_SIZE(big)` | `DISK_SIZE(small)` | record before | pinned demotes | normative demotes | record after |
|---|---:|---:|---:|---|---|---:|
| 2 (comparator) | 1,008 | 508 | 1,564 | nothing | nothing | 1,564 |
| 1 (OOS-backed) | 3,008 | 1,208 | 4,264 | `big` | `big` | 1,272 (pinned) / 1,280 (normative) |

`small` in row 1 is 1,208 B serialized, far above both eligibility floors (16 B pinned,
24 B normative), so it is a demotion *candidate* that stays inline only because the
largest-first loop stopped. That is what makes row 1 discriminating rather than merely
large: an engine that demoted the smallest candidate first would also stop after one
demotion (record after = 3,072 B ≤ 4,086 B) and would still show one chunk, so the chunk
*count* cannot tell the two apart — the chunk *payload sum* can (3,024 B for `big`,
1,224 B for `small`). The paired diagnostic run below is what reads that sum.

`DISK_SIZE` reports the serialized logical size irrespective of placement (ticket 11 §6),
so it is used here only to confirm the size arithmetic the derivation relies on, never as
evidence that a value went out of row.

**Accounting caveat, stated deliberately.** The derivation models the fixture as one fixed
column (`id INT`, 4 bound-bit bytes) and two variable columns. The case declares
`id INT PRIMARY KEY`; should `NOT NULL` remove those 4 bound-bit bytes, every record size
above moves by 4 B. The margins absorb it: row 1 is 178 B above the pinned gate and 204 B
above the normative target, and row 1 after demotion is 2,814 B below the normative
target. No expectation in this file changes.

## Statement-by-statement expectation

Values below are the scalars CTP compares. Whitespace and the `=====` separators are the
runner's own formatting and are not part of the oracle.

| # | Statement | Expected | Why |
|---|---|---|---|
| 1 | `DROP TABLE IF EXISTS t_cbrd_26659_rep02` | success | setup, idempotent |
| 2 | `CREATE TABLE …` | success | setup |
| 3 | `evaluate '[TEST 1] …'` | the marker text | section marker |
| 4 | `INSERT … (2, 1000 B 'CC', 500 B 'DD')` | 1 row affected | one row, below both gates, accepted |
| 5 | `SELECT … WHERE id = 2` | `2, 1008, 508, 1, 1` | `DISK_SIZE` = ALIGN(5+N,4); both values read back byte-identical (OOS-REP-01, OOS-SQL-01) |
| 6 | `evaluate '[TEST 2] …'` | the marker text | section marker |
| 7 | `INSERT … (1, 3000 B 'AA', 1200 B 'BB')` | 1 row affected | record 4,264 B is above both gates but stays below `heap_Maxslotted_reclength` (16,236 B) after demotion, so it is accepted, not rejected |
| 8 | `SELECT … WHERE id = 1` | `1, 3008, 1208, 1, 1` | the demoted value and the value left inline both read back byte-identical (OOS-REP-02, OOS-SQL-01) |
| 9 | `evaluate '[TEST 3] …'` | the marker text | section marker |
| 10 | `SELECT COUNT(*), SUM(exact), SUM(aliased)` | `2, 2, 0` | both rows present; both match their own patterns exactly; no row holds one value in both columns |
| 11 | `DROP TABLE t_cbrd_26659_rep02` | success | teardown, owns only its own table |

**Assertion count = 15.** One per compared scalar carrying a justified expectation about
behavior under test: 5 (statement 5) + 5 (statement 8) + 3 (statement 10) + the two
INSERT affected-row counts. The three DDL status outputs and the three `evaluate` markers
are setup, teardown and section markers, not assertions; they are still compared by CTP.

**Expected case count = 1.** One `.sql` file under
`sql/_36_guava/cbrd_26659/cases/`.

## Paired activation-evidence expectation

The public case stays portable and contains no diagnostic statement. Activation evidence
comes from a paired run of the same fixture, in the same insert order, under `csql -S` on
the pinned release and debug installs, with `SHOW HEAP OOS OF t_cbrd_26659_rep02`
interleaved. Expected, in order:

| After | `Has_oos_file` | `Oos_num_recs` | `Oos_recs_sumlen` |
|---|---:|---:|---:|
| `CREATE TABLE` | 0 | 0 | 0 |
| `INSERT` row 2 (comparator) | 0 | 0 | 0 |
| `INSERT` row 1 (OOS-backed) | 1 | 1 | 3,024 |

The first two rows are the direct evidence for OOS-REP-01 ("a class that has never
demoted a value has no OOS file"). The third is the evidence for OOS-REP-02: one chunk,
and a payload sum that identifies the demoted value as `big`.

`Oos_recs_sumlen` = 3,024 is the *pinned* value (3,008 payload + one 16-byte chunk
header). The accepted 24-byte chunk header would give 3,032. The 16-byte header is a
Capability gap of the pinned engine (ticket 11 finding d, `OOS-REP-05`), so 3,024 is
recorded as an observation of the pin and is not written into any answer; what is asserted
is the chunk count and the fact that the sum identifies `big` rather than `small`
(3,024 or 3,032, either way far from 1,224 or 1,232).

## Negative control expectation

One deliberately wrong expected value (`big_ok` of the OOS-backed row changed from `1` to
`0`) must make the CTP comparison report a failure. If CTP reports success, the checking
mechanism itself is not trustworthy and no result from it may be promoted. The control and
its wrong answer are kept out of `sql/_36_guava/cbrd_26659/answers/`.
