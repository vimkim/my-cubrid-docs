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

---

# Revision 2 — after the two-axis review (2026-09-10, before the revised case was run)

The independent Spec review of revision 1 raised four findings that change what this
oracle must contain. Revision 1's numbers are all unchanged and were all confirmed by the
reviewer's own hand calculation; what follows is added, not corrected.

## Why the whole-value equality flags were not enough

Review finding: `big = CAST(REPEAT('AA', 3000) AS BIT VARYING)` asks the engine to compare
a value it read back through the OOS path against a value it constructed itself. A defect
that truncated the read *and* truncated the comparison operand identically would still
report `1`. The spec requires oracles "justified independently of the observed engine
result", and a self-comparison is not that.

Three independent characterizations of the same values are therefore added. Each is
predicted here from first principles and none is taken from an engine run:

- `OCTET_LENGTH` — byte count, predicted as N.
- `BIT_LENGTH` — bit count, predicted as N × 8.
- `MD5` — a digest over the whole value, computed by a different code path than `=`.
  CUBRID's `MD5` of a `BIT VARYING` digests its **lowercase hexadecimal** representation,
  established by probe and reproduced independently in Python: for `REPEAT('AA', 3000)`
  the digest is `md5("aa" * 3000)`. A truncated or corrupted read cannot produce the same
  digest, and unlike the equality flag the digest is *visible* in the answer, so a wrong
  value shows as a changed digest rather than as a silent `0`.

| Value | N | `OCTET_LENGTH` | `BIT_LENGTH` | `MD5` (of the lowercase hex form) |
|---|---:|---:|---:|---|
| row 1 `big`, pattern AA | 3,000 | 3,000 | 24,000 | `56d1d803c5f755f96819a2996fb65e43` |
| row 1 `small`, pattern BB | 1,200 | 1,200 | 9,600 | `6d5d5cbc57eac18ff5c9af115e2e7e69` |
| row 2 `big`, pattern CC | 1,000 | 1,000 | 8,000 | `b8db77f08f4e9f30dfc31dcd13b53eee` |
| row 2 `small`, pattern DD | 500 | 500 | 4,000 | `d9a0e8de165479413f12fc6065062298` |

Verification command, independent of CUBRID:

```
python3 -c "import hashlib; print(hashlib.md5(('aa'*3000).encode()).hexdigest())"
```

## What the public case can and cannot prove

Review finding, accepted: the committed `.sql` **cannot detect a largest-first
regression**. It emits `DISK_SIZE`, lengths, digests and equality flags, and ticket 11 §5.2
already established that `DISK_SIZE` "reports the logical serialized size regardless of
placement (it is not a placement oracle)". An engine that demoted `small` instead of `big`
would produce a byte-identical answer and CTP would report success.

This is not a defect in the case; it follows from the ownership decision, which makes the
public suite portable SQL only, and from the spec's rule that "activation evidence for
public cases comes from corresponding instrumented or debug validation runs". No portable
SQL exposes per-attribute placement at this pin.

The consequence is recorded honestly rather than papered over:

- The public case is the oracle for **value correctness** (`OOS-SQL-01`) and for the
  logical half of `OOS-REP-01` and `OOS-REP-02`.
- The **placement discrimination** for `OOS-REP-02` comes only from the paired activation
  run, which is not part of the public regression.
- Because that run was a passive evidence collector in revision 1, it could not fail. It
  is therefore promoted to a **validated checker**: it now asserts the three expected
  `SHOW HEAP OOS` observations and exits non-zero on any mismatch, and it has its own
  negative control.
- The residual gap — that nothing in the *committed public suite* fails when largest-first
  breaks — is recorded as a Delivery gap row in the matrix against `OOS-REP-02`.

## Expected activation-checker observations (unchanged values, now asserted)

| After | `Has_oos_file` | `Oos_num_recs` | `Oos_recs_sumlen` |
|---|---:|---:|---:|
| `CREATE TABLE` | 0 | 0 | 0 |
| comparator row (id 2) | 0 | 0 | 0 |
| OOS-backed row (id 1) | 1 | 1 | 3,024 |

`3024 = 3008 payload + one 16-byte chunk header`. Demoting `small` instead would give
`1208 + 16 = 1224`; that difference is the checker's discriminating power. The sum is the
pinned value: the accepted 24-byte chunk header (CBRD-26950) would give 3,032, so only the
chunk *count* and the identification of *which* value was demoted are treated as stable;
the exact sum is recorded as an observation of the pin.

## Revised assertion count

The revised case emits, per row group: `id`, `DISK_SIZE` ×2, `OCTET_LENGTH` ×2,
`BIT_LENGTH` ×2, `MD5` ×2, equality ×2 = 11 scalars, for two row groups = 22; plus
statement 10's 3 scalars and the two INSERT affected-row counts. **Assertion count = 27.**

CTP reports no assertion counter of its own (it reports only `Total`, `Success`, `Fail`
and `execute_case`). The manifest therefore records this count as **derived** from a
whole-text match — a byte-identical `.result` entails that every one of the 27 scalars
matched — and not as an independently measured execution count. Ticket 15's wrapper is
where a real counter belongs.
