#!/usr/bin/env python3
"""Emit the ticket-19 public SQL-operations cases into the public `testcases` worktree.

    gen_ticket19_cases.py [--out DIR] [--check]

Why the cases are generated rather than hand-written: every fixture size in them has to be one
the campaign may assert, and that is a property of the pinned engine's record accounting, not
of the SQL.  Generating them from `derive_ticket19_sizes.py` makes the two impossible to drift
apart -- `classify()` refuses a size the pinned and normative accountings disagree about, or an
OOS row that leaves no eligible column inline, so a fixture the campaign may not assert cannot
reach a case file at all.  The emitted SQL is ordinary, readable, reviewable SQL; nothing about
the generator is needed to run or read the cases.

`--check` regenerates into a temporary directory and compares, so CI or a reviewer can prove
the checked-in cases are exactly what this script produces.  Exit status 0 when they match.

Default output: /home/vimkim/gh/tc/cubrid-testcases-cbrd-26659/sql/_36_guava/cbrd_26659/cases
"""
from __future__ import annotations

import argparse
import filecmp
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import derive_ticket19_sizes as d  # noqa: E402

DEFAULT_OUT = Path("/home/vimkim/gh/tc/cubrid-testcases-cbrd-26659/sql/_36_guava/cbrd_26659/cases")

SCHEMA_C_NAMES = ["payload", "tag"]
TAG = 300  # every schema-C row's inline neighbour, 308 B serialized: eligible, never demoted

# ---------------------------------------------------------------------------------------------
# fixture helpers: nothing reaches a case file without passing through `oos()` or `inline()`
# ---------------------------------------------------------------------------------------------

_emitted: list[tuple[str, tuple, str]] = []


def _record(kind, sizes, where):
    _emitted.append((kind, tuple(sizes), where))


def oos(payload_bytes, where, tag_bytes=TAG):
    """Assert this schema-C row is OOS-backed under both accountings; return its byte size."""
    kind, demoted, tie = d.classify([payload_bytes, tag_bytes], SCHEMA_C_NAMES)
    if kind != "oos" or demoted != ["payload"] or tie:
        raise SystemExit(f"{where}: payload {payload_bytes} B is not an assertable OOS fixture "
                         f"(kind={kind}, demoted={demoted}, tie={tie})")
    _record("oos", (payload_bytes, tag_bytes), where)
    return payload_bytes


def inline(payload_bytes, where, tag_bytes=TAG):
    """Assert this schema-C row stays entirely inline under both accountings."""
    kind, demoted, _tie = d.classify([payload_bytes, tag_bytes], SCHEMA_C_NAMES)
    if kind != "inline":
        raise SystemExit(f"{where}: payload {payload_bytes} B is not an inline comparator "
                         f"(kind={kind}, demoted={demoted})")
    _record("inline", (payload_bytes, tag_bytes), where)
    return payload_bytes


_values: dict[tuple[str, int], None] = {}


def val(char, n_bytes):
    """The SQL expression for an n-byte BIT VARYING of the repeated hex character `char`."""
    assert char in d.HEX_ALPHABET, char
    _values[(char, n_bytes)] = None
    return f"CAST(REPEAT('{char}', {2 * n_bytes}) AS BIT VARYING)"


def chunks_note(n):
    return "one chunk" if d.chunks(n, d.ob.OOS_RECORD_HEADER_SIZE_PINNED) == 1 else \
        f"{d.chunks(n, d.ob.OOS_RECORD_HEADER_SIZE_PINNED)} chunks"


# ---------------------------------------------------------------------------------------------
# SQL fragments
# ---------------------------------------------------------------------------------------------

def header_common(inline_neighbour, md5_char, md5_bytes):
    """The paragraphs every case header shares, with the two facts that differ filled in.

    They differ because the family has two schemas: seven cases carry a 300 B `tag` beside the
    demoted column, the reused CBRD-27006 workload carries a 3,400..3,500 B `single2`.  A single
    fixed block said `tag` in both, and quoted an `'aa' * 4200` example that exists in seven of
    the eight files -- the kind of copy that is right when written and wrong a case later.
    """
    return f""" * Sizes.  BIT VARYING is used rather than a character type because character values are
 * compressed, which makes their stored size unpredictable and useless as a size boundary.
 * CAST(REPEAT('<hex digit>', 2N) AS BIT VARYING) is exactly N bytes of that repeated nibble.
 * The serialized size of such a value is ALIGN(5 + N, 4), which is what DISK_SIZE reports.
 *
 * At a 16 KiB page size the record gate is 4086 B on CUBRID feat/oos
 * f4299ac0cd777a2a964c1f197ae5ebf9841a4936, the revision this answer was generated on, and
 * 4060 B under the four-record physical target accepted in CBRD-27057.  Every size below was
 * derived by cbrd-26659/campaign/evidence/ticket19/derive_ticket19_sizes.py, which refuses any
 * size the two accountings disagree about, so this answer is stable rather than specific to
 * one revision.  {inline_neighbour}
 *
 * Value checks are deliberately redundant and independent.  Whole-value equality alone would
 * ask the engine to compare a value it read back against one it built itself, so a fault that
 * truncated both identically would go unnoticed.  OCTET_LENGTH pins the size and MD5 pins the
 * content through a different code path; CUBRID's MD5 of a BIT VARYING digests its lowercase
 * hexadecimal form, so every digest in the answer is reproducible outside CUBRID, for example
 *   python3 -c "import hashlib; print(hashlib.md5(('{md5_char * 2}'*{md5_bytes}).encode()).hexdigest())"
"""


MIXED_NEIGHBOUR = ("`single2` is 3,400 to 3,500 B: far above both eligibility floors (16 B\n"
                   " * pinned, 24 B normative), so it stays inline because the largest-first loop "
                   "already\n * stopped, not because it was too small to qualify.")

TAG_NEIGHBOUR = ("`tag` is 300 B (308 B serialized): far above both eligibility floors (16 B\n"
                 " * pinned, 24 B normative), so it stays inline because the largest-first loop "
                 "already stopped,\n * not because it was too small to qualify.")



def select_row(table, rid, payload_expr, tag_expr, alias_prefix=""):
    p = alias_prefix
    return f"""SELECT id,
       DISK_SIZE(payload)    AS {p}payload_disk,
       DISK_SIZE(tag)        AS {p}tag_disk,
       OCTET_LENGTH(payload) AS {p}payload_octets,
       OCTET_LENGTH(tag)     AS {p}tag_octets,
       MD5(payload)          AS {p}payload_md5,
       MD5(tag)              AS {p}tag_md5,
       payload = {payload_expr} AS {p}payload_ok,
       tag     = {tag_expr} AS {p}tag_ok
  FROM {table} WHERE id = {rid};"""


def evaluate(text):
    return f"EVALUATE '{text}';"


# ---------------------------------------------------------------------------------------------
# case 1 -- OOS-SQL-01: INSERT then SELECT, bulk inserts, INSERT ... SELECT
# ---------------------------------------------------------------------------------------------

def case_sql01():
    w = "sql01"
    t = "t_cbrd_26659_sql01"
    tc = "t_cbrd_26659_sql01_copy"
    b100, b1000 = "t_cbrd_26659_sql01_b100", "t_cbrd_26659_sql01_b1000"
    n10, n1000 = "n10_cbrd_26659_sql01", "n1000_cbrd_26659_sql01"

    p_oos, p_inl = oos(4200, w), inline(3000, w)
    g100, g1000 = d.BULK_100, d.BULK_1000
    for i in g100.ids():
        oos(g100.size(i), f"{w} bulk-100 row {i}")
    for i in g1000.ids():
        oos(g1000.size(i), f"{w} bulk-1000 row {i}")

    def gen_aggregate(table, group):
        return f"""SELECT COUNT(*)                            AS n_rows,
       SUM(CASE WHEN payload = {group.value_sql('id')}
                THEN 1 ELSE 0 END)           AS n_payload_exact,
       SUM(CASE WHEN OCTET_LENGTH(payload) = {group.size_sql('id')}
                THEN 1 ELSE 0 END)           AS n_len_exact,
       SUM(CASE WHEN tag = {val('7', TAG)}
                THEN 1 ELSE 0 END)           AS n_tag_exact,
       SUM(OCTET_LENGTH(payload))            AS payload_octets_total,
       MIN(OCTET_LENGTH(payload))            AS payload_octets_min,
       MAX(OCTET_LENGTH(payload))            AS payload_octets_max,
       COUNT(DISTINCT MD5(payload))          AS distinct_payloads
  FROM {table};"""

    def gen_samples(table, group):
        ids = ", ".join(str(i) for i in group.samples)
        return f"""SELECT id,
       OCTET_LENGTH(payload) AS payload_octets,
       MD5(payload)          AS payload_md5,
       payload = {group.value_sql('id')} AS payload_ok
  FROM {table} WHERE id IN ({ids}) ORDER BY id;"""

    body = f"""/*
 * CBRD-26659 -- OOS-SQL-01: an inserted OOS-backed row reads back byte-identical, for single
 * rows, for bulk inserts of varying sizes, and across INSERT ... SELECT.
 *
 * Requirements: OOS-SQL-01 (INSERT then SELECT returns the exact value).
 *
 * What this case pins down:
 *   1. one OOS-backed row and one inline comparator row read back exactly
 *   2. {g100.n_rows} rows of {min(g100.size(i) for i in g100.ids())}..{max(g100.size(i) for i in g100.ids())} B, every one OOS-backed, all read back exactly
 *   3. {g1000.n_rows} rows of {min(g1000.size(i) for i in g1000.ids())}..{max(g1000.size(i) for i in g1000.ids())} B, every one OOS-backed, all read back exactly
 *   4. INSERT ... SELECT copies OOS-backed rows between tables value for value
 *
 * What this case deliberately does NOT prove: which column was moved out of the record.  No
 * portable SQL exposes per-attribute placement -- DISK_SIZE reports the logical serialized
 * size whether or not a value was demoted -- so placement is checked separately, outside this
 * suite, by reading SHOW HEAP OOS on a table owned exclusively by that check.
 *
 * The generated groups vary the byte pattern with MOD(i, {len(d.HEX_ALPHABET)}) and the length with
 * {g100.size_sql('i')} / {g1000.size_sql('i')}; the two cycles are coprime over the row count, so all
 * {g100.n_rows} and all {g1000.n_rows} values are distinct.  COUNT(DISTINCT MD5(payload)) asserts exactly that,
 * which is what stops the aggregate checks from passing on a table of identical rows.
 *
{header_common(TAG_NEIGHBOUR, 'a', 4200)} */

DROP TABLE IF EXISTS {tc};
DROP TABLE IF EXISTS {b100};
DROP TABLE IF EXISTS {b1000};
DROP TABLE IF EXISTS {n1000};
DROP TABLE IF EXISTS {n10};
DROP TABLE IF EXISTS {t};

CREATE TABLE {t} (id INT PRIMARY KEY, payload BIT VARYING, tag BIT VARYING);

{evaluate(f'[TEST 1] inline comparator row: record below both gates ({p_inl} B payload), nothing moved out')}
INSERT INTO {t} VALUES (2, {val('c', p_inl)}, {val('d', TAG)});
{select_row(t, 2, val('c', p_inl), val('d', TAG))}

{evaluate(f'[TEST 2] OOS-backed row: record above both gates ({p_oos} B payload, {chunks_note(p_oos)})')}
INSERT INTO {t} VALUES (1, {val('a', p_oos)}, {val('b', TAG)});
{select_row(t, 1, val('a', p_oos), val('b', TAG))}

{evaluate('[TEST 3] every row still holds its own values, with no cross-row bleed')}
SELECT COUNT(*) AS n_rows,
       SUM(CASE WHEN id = 1
                     AND payload = {val('a', p_oos)}
                     AND tag     = {val('b', TAG)} THEN 1
                WHEN id = 2
                     AND payload = {val('c', p_inl)}
                     AND tag     = {val('d', TAG)} THEN 1
                ELSE 0 END) AS n_exact,
       SUM(CASE WHEN payload = tag THEN 1 ELSE 0 END) AS n_aliased
  FROM {t};

{evaluate('[TEST 4] a deterministic 1..1000 helper, built without depending on catalogue size')}
CREATE TABLE {n10} (i INT);
INSERT INTO {n10} VALUES (0), (1), (2), (3), (4), (5), (6), (7), (8), (9);
CREATE TABLE {n1000} (i INT PRIMARY KEY);
INSERT INTO {n1000} SELECT a.i * 100 + b.i * 10 + c.i + 1 FROM {n10} a, {n10} b, {n10} c;
SELECT COUNT(*) AS n_helper, MIN(i) AS min_i, MAX(i) AS max_i FROM {n1000};

{evaluate(f'[TEST 5] bulk insert of {g100.n_rows} OOS-backed rows of varying sizes')}
CREATE TABLE {b100} (id INT PRIMARY KEY, payload BIT VARYING, tag BIT VARYING);
INSERT INTO {b100}
  SELECT i, {g100.value_sql('i')}, {val('7', TAG)} FROM {n1000} WHERE i <= {g100.n_rows};
{gen_aggregate(b100, g100)}
{gen_samples(b100, g100)}

{evaluate(f'[TEST 6] bulk insert of {g1000.n_rows} OOS-backed rows of varying sizes')}
CREATE TABLE {b1000} (id INT PRIMARY KEY, payload BIT VARYING, tag BIT VARYING);
INSERT INTO {b1000}
  SELECT i, {g1000.value_sql('i')}, {val('7', TAG)} FROM {n1000};
{gen_aggregate(b1000, g1000)}
{gen_samples(b1000, g1000)}

{evaluate('[TEST 7] INSERT ... SELECT copies OOS-backed rows between tables, value for value')}
CREATE TABLE {tc} (id INT PRIMARY KEY, payload BIT VARYING, tag BIT VARYING);
INSERT INTO {tc} SELECT id, payload, tag FROM {b100};
SELECT COUNT(*) AS n_copied,
       SUM(CASE WHEN c.payload = s.payload AND c.tag = s.tag THEN 1 ELSE 0 END) AS n_identical,
       SUM(CASE WHEN OCTET_LENGTH(c.payload) = OCTET_LENGTH(s.payload) THEN 1 ELSE 0 END)
                                                                                AS n_same_length,
       SUM(CASE WHEN MD5(c.payload) = MD5(s.payload) THEN 1 ELSE 0 END)         AS n_same_digest
  FROM {tc} c, {b100} s WHERE c.id = s.id;
{gen_samples(tc, g100)}

DROP TABLE {tc};
DROP TABLE {b1000};
DROP TABLE {b100};
DROP TABLE {n1000};
DROP TABLE {n10};
DROP TABLE {t};
"""
    return "cbrd_26659_oos_sql01_insert_select", body


# ---------------------------------------------------------------------------------------------
# case 2 -- OOS-SQL-02: UPDATE correctness
# ---------------------------------------------------------------------------------------------

def case_sql02():
    w = "sql02"
    t, src = "t_cbrd_26659_sql02", "t_cbrd_26659_sql02_src"
    p0 = oos(4200, w)                       # initial OOS-backed payload
    pc = inline(3000, w)                    # inline comparator row
    p1 = oos(5000, w)                       # first replacement, still one chunk
    pm = oos(20000, w)                      # multi-chunk
    p2 = oos(4400, w)                       # back to one chunk
    psub = oos(4600, w)                     # value the subquery/join carries
    three = [oos(4300, w), oos(4500, w), oos(4700, w)]
    fifty = [oos(4200 + 10 * k, f"{w} repeat {k}") for k in range(1, 51)]
    fifty_chars = [d.HEX_ALPHABET[k % len(d.HEX_ALPHABET)] for k in range(1, 51)]

    repeats_3 = "\n".join(
        f"UPDATE {t} SET payload = {val(c, n)} WHERE id = 1;"
        for c, n in zip("123", three))
    repeats_50 = "\n".join(
        f"UPDATE {t} SET payload = {val(c, n)} WHERE id = 1;"
        for c, n in zip(fifty_chars, fifty))

    body = f"""/*
 * CBRD-26659 -- OOS-SQL-02: after an UPDATE of an OOS-backed attribute, or of an inline
 * attribute in an OOS-backed record, every later reader sees the exact new value; repeated
 * updates leave the final value correct.
 *
 * Requirements: OOS-SQL-02 (UPDATE correctness).
 *
 * What this case pins down:
 *   1. UPDATE of the OOS-backed attribute -- the new value reads back exactly
 *   2. UPDATE of the inline attribute only -- the untouched OOS-backed value is still exact
 *   3. three repeated updates, final value asserted
 *   4. single chunk -> {chunks_note(pm)} -> single chunk, each step asserted
 *   5. fifty repeated updates of varying size, final value asserted
 *   6. UPDATE whose new value comes from a subquery reading another table's OOS value
 *   7. UPDATE through a join, which also turns the inline comparator row into an OOS-backed one
 *
 * What this case deliberately does NOT assert: how many value chains the updates left behind.
 * At the pin every UPDATE allocates fresh chains even for attributes the statement did not
 * assign (OOS-SQL-03, observation-only, superseded on paper by CBRD-27230), and chain counts
 * are not visible to portable SQL.  The paired activation check observes the chunk growth of
 * step 2 as an observation; no answer file carries it.
 *
{header_common(TAG_NEIGHBOUR, 'a', 4200)} */

DROP TABLE IF EXISTS {src};
DROP TABLE IF EXISTS {t};

CREATE TABLE {t} (id INT PRIMARY KEY, payload BIT VARYING, tag BIT VARYING);
CREATE TABLE {src} (id INT PRIMARY KEY, payload BIT VARYING, tag BIT VARYING);

INSERT INTO {t} VALUES (1, {val('a', p0)}, {val('b', TAG)});
INSERT INTO {t} VALUES (2, {val('c', pc)}, {val('d', TAG)});
INSERT INTO {src} VALUES (1, {val('d', psub)}, {val('5', TAG)});

{evaluate(f'[TEST 1] the fixture: row 1 OOS-backed ({p0} B), row 2 inline comparator ({pc} B)')}
{select_row(t, 1, val('a', p0), val('b', TAG))}
{select_row(t, 2, val('c', pc), val('d', TAG))}

{evaluate(f'[TEST 2] UPDATE of the OOS-backed attribute: {p0} B -> {p1} B')}
UPDATE {t} SET payload = {val('e', p1)} WHERE id = 1;
{select_row(t, 1, val('e', p1), val('b', TAG))}

{evaluate('[TEST 3] UPDATE of the inline attribute only: the OOS-backed value still reads back exactly')}
UPDATE {t} SET tag = {val('7', TAG)} WHERE id = 1;
{select_row(t, 1, val('e', p1), val('7', TAG))}

{evaluate('[TEST 4] three repeated updates, only the final value asserted')}
{repeats_3}
{select_row(t, 1, val('3', three[2]), val('7', TAG))}

{evaluate(f'[TEST 5] single chunk -> {chunks_note(pm)}: {three[2]} B -> {pm} B')}
UPDATE {t} SET payload = {val('f', pm)} WHERE id = 1;
{select_row(t, 1, val('f', pm), val('7', TAG))}

{evaluate(f'[TEST 6] {chunks_note(pm)} -> single chunk: {pm} B -> {p2} B')}
UPDATE {t} SET payload = {val('9', p2)} WHERE id = 1;
{select_row(t, 1, val('9', p2), val('7', TAG))}

{evaluate(f'[TEST 7] fifty repeated updates of sizes {fifty[0]}..{fifty[-1]} B, only the final value asserted')}
{repeats_50}
{select_row(t, 1, val(fifty_chars[-1], fifty[-1]), val('7', TAG))}

{evaluate('[TEST 8] UPDATE whose new value is a subquery reading another table OOS value')}
UPDATE {t} SET payload = (SELECT payload FROM {src} WHERE id = 1) WHERE id = 1;
{select_row(t, 1, val('d', psub), val('7', TAG))}

{evaluate('[TEST 9] UPDATE through a join: the inline comparator row becomes OOS-backed')}
UPDATE {t} a, {src} b SET a.payload = b.payload, a.tag = b.tag WHERE a.id = 2 AND b.id = 1;
{select_row(t, 2, val('d', psub), val('5', TAG))}

{evaluate('[TEST 10] both rows are intact and distinct after every write above')}
SELECT COUNT(*) AS n_rows,
       SUM(CASE WHEN payload = {val('d', psub)} THEN 1 ELSE 0 END) AS n_carrying_src_value,
       SUM(CASE WHEN payload = tag THEN 1 ELSE 0 END)              AS n_aliased,
       COUNT(DISTINCT MD5(tag))                                    AS distinct_tags
  FROM {t};

DROP TABLE {src};
DROP TABLE {t};
"""
    return "cbrd_26659_oos_sql02_update", body


# ---------------------------------------------------------------------------------------------
# case 3 -- OOS-SQL-05: DELETE semantics
# ---------------------------------------------------------------------------------------------

def case_sql05():
    w = "sql05"
    t = "t_cbrd_26659_sql05"
    p1, p3, p4 = oos(4200, w), oos(4400, w), oos(4600, w)
    pc = inline(3000, w)

    def insert_all():
        return "\n".join([
            f"INSERT INTO {t} VALUES (1, {val('a', p1)}, {val('b', TAG)});",
            f"INSERT INTO {t} VALUES (2, {val('c', pc)}, {val('d', TAG)});",
            f"INSERT INTO {t} VALUES (3, {val('e', p3)}, {val('5', TAG)});",
            f"INSERT INTO {t} VALUES (4, {val('f', p4)}, {val('6', TAG)});",
        ])

    survey = f"""SELECT id,
       OCTET_LENGTH(payload) AS payload_octets,
       MD5(payload)          AS payload_md5,
       MD5(tag)              AS tag_md5
  FROM {t} ORDER BY id;"""

    body = f"""/*
 * CBRD-26659 -- OOS-SQL-05: a deleted OOS-backed row is gone for the deleter and for later
 * readers, the table stays reusable, and the rows that were not deleted are untouched.
 *
 * Requirements: OOS-SQL-05 (DELETE semantics).
 *
 * What this case pins down:
 *   1. DELETE of one OOS-backed row reports one affected row and leaves the others exact
 *   2. DELETE whose WHERE reads the OOS-backed column itself matches exactly one row
 *   3. DELETE of everything empties the table, and the same values re-insert and read back
 *   4. TRUNCATE is the comparator for step 3
 *
 * What this case deliberately does NOT assert: that the value chains of a deleted row are
 * still present.  OOS-SQL-05's physical clause ("its value chains are not removed at delete
 * time in MVCC mode") is not observable from portable SQL; it is visible only through
 * SHOW HEAP OOS, and only client-server, because the standalone eager path deletes
 * synchronously (ticket 11 section 6).  The paired activation check carries that half, and
 * the matrix row says so.
 *
{header_common(TAG_NEIGHBOUR, 'a', 4200)} */

DROP TABLE IF EXISTS {t};
CREATE TABLE {t} (id INT PRIMARY KEY, payload BIT VARYING, tag BIT VARYING);

{evaluate(f'[TEST 1] the fixture: rows 1, 3 and 4 OOS-backed, row 2 the inline comparator ({pc} B)')}
{insert_all()}
{survey}

{evaluate('[TEST 2] DELETE one OOS-backed row by primary key')}
DELETE FROM {t} WHERE id = 1;
{survey}

{evaluate('[TEST 3] DELETE whose predicate reads the OOS-backed column itself')}
DELETE FROM {t} WHERE payload = {val('e', p3)};
{survey}

{evaluate('[TEST 4] the surviving rows are still byte-exact')}
{select_row(t, 2, val('c', pc), val('d', TAG))}
{select_row(t, 4, val('f', p4), val('6', TAG))}

{evaluate('[TEST 5] DELETE everything, then re-INSERT the same values into the same table')}
DELETE FROM {t};
SELECT COUNT(*) AS n_rows_after_delete_all FROM {t};
{insert_all()}
{survey}

{evaluate('[TEST 6] TRUNCATE comparator, then re-INSERT once more')}
TRUNCATE {t};
SELECT COUNT(*) AS n_rows_after_truncate FROM {t};
{insert_all()}
{survey}

{evaluate('[TEST 7] every re-inserted row is byte-exact, and no two rows alias')}
SELECT COUNT(*) AS n_rows,
       SUM(CASE WHEN id = 1 AND payload = {val('a', p1)} THEN 1
                WHEN id = 2 AND payload = {val('c', pc)} THEN 1
                WHEN id = 3 AND payload = {val('e', p3)} THEN 1
                WHEN id = 4 AND payload = {val('f', p4)} THEN 1
                ELSE 0 END)                             AS n_exact,
       COUNT(DISTINCT MD5(payload))                     AS distinct_payloads,
       SUM(CASE WHEN payload = tag THEN 1 ELSE 0 END)   AS n_aliased
  FROM {t};

DROP TABLE {t};
"""
    return "cbrd_26659_oos_sql05_delete", body


# ---------------------------------------------------------------------------------------------
# case 4 -- OOS-SQL-06: rollback, savepoints
# ---------------------------------------------------------------------------------------------

def case_sql06_rollback():
    w = "sql06 rollback"
    t = "t_cbrd_26659_sql06r"
    p1 = oos(4200, w)
    pc = inline(3000, w)
    p_new = oos(4400, w)      # the row 3 that ROLLBACK must remove
    p_upd = oos(4500, w)      # the UPDATE that ROLLBACK must undo
    p_upd2 = oos(5000, w)     # the second UPDATE that ROLLBACK must undo
    p_sp = oos(4600, w)       # the value a savepoint must preserve
    p_after_sp = oos(4700, w)  # the value a partial rollback must discard
    p_sp_row = oos(4800, w)   # the row a partial rollback must discard

    survey = f"""SELECT id,
       OCTET_LENGTH(payload) AS payload_octets,
       MD5(payload)          AS payload_md5,
       MD5(tag)              AS tag_md5
  FROM {t} ORDER BY id;"""

    body = f"""/*
 * CBRD-26659 -- OOS-SQL-06: ROLLBACK and savepoint rollback restore the previous record
 * as-is, including its OOS inline stubs, with no partial effect.
 *
 * Requirements: OOS-SQL-06 (transaction atomicity and undo correctness).
 *
 * What this case pins down:
 *   1. an INSERT plus an UPDATE in one transaction, rolled back: the table is exactly as it
 *      was, and the OOS-backed row reads back byte-identical to its pre-transaction value
 *   2. an UPDATE of an OOS-backed attribute, rolled back: the original OOS value is restored
 *   3. ROLLBACK TO SAVEPOINT across OOS writes: work before the savepoint survives, work
 *      after it is discarded, and the surviving OOS value is byte-exact
 *
 * Reads inside the transaction are asserted as well as reads after it, so an engine that
 * restored the right value but showed the wrong one to the writer would still fail.
 *
 * What this case deliberately does NOT assert: that no orphan value chain remains from the
 * aborted work.  That is a physical claim portable SQL cannot make; eventual cleanup of dead
 * chains is OOS-CL-02 on the private shell seam, and the paired activation check records the
 * chunk counts this case leaves behind as an observation.
 *
{header_common(TAG_NEIGHBOUR, 'a', 4200)} */

AUTOCOMMIT OFF;

DROP TABLE IF EXISTS {t};
CREATE TABLE {t} (id INT PRIMARY KEY, payload BIT VARYING, tag BIT VARYING);
INSERT INTO {t} VALUES (1, {val('a', p1)}, {val('b', TAG)});
INSERT INTO {t} VALUES (2, {val('c', pc)}, {val('d', TAG)});
COMMIT;

{evaluate(f'[TEST 1] committed fixture: row 1 OOS-backed ({p1} B), row 2 inline ({pc} B)')}
{survey}

{evaluate('[TEST 2] INSERT plus UPDATE inside one transaction, seen by the writer')}
INSERT INTO {t} VALUES (3, {val('e', p_new)}, {val('5', TAG)});
UPDATE {t} SET payload = {val('6', p_upd)} WHERE id = 1;
{survey}
{select_row(t, 1, val('6', p_upd), val('b', TAG))}

{evaluate('[TEST 3] ROLLBACK: the inserted row is gone and the updated row is restored exactly')}
ROLLBACK;
{survey}
{select_row(t, 1, val('a', p1), val('b', TAG))}

{evaluate('[TEST 4] UPDATE of an OOS-backed attribute alone, then ROLLBACK')}
UPDATE {t} SET payload = {val('7', p_upd2)} WHERE id = 1;
{select_row(t, 1, val('7', p_upd2), val('b', TAG))}
ROLLBACK;
{select_row(t, 1, val('a', p1), val('b', TAG))}

{evaluate('[TEST 5] savepoint: an OOS write before it, more OOS writes after it')}
UPDATE {t} SET payload = {val('8', p_sp)} WHERE id = 1;
SAVEPOINT sp_cbrd_26659;
UPDATE {t} SET payload = {val('9', p_after_sp)} WHERE id = 1;
INSERT INTO {t} VALUES (4, {val('f', p_sp_row)}, {val('1', TAG)});
{survey}

{evaluate('[TEST 6] ROLLBACK TO SAVEPOINT: work after the savepoint is discarded, work before it survives')}
ROLLBACK TO SAVEPOINT sp_cbrd_26659;
{survey}
{select_row(t, 1, val('8', p_sp), val('b', TAG))}

{evaluate('[TEST 7] COMMIT: the savepoint-surviving OOS value is the durable one')}
COMMIT;
{survey}
{select_row(t, 1, val('8', p_sp), val('b', TAG))}

DROP TABLE {t};
COMMIT;
AUTOCOMMIT ON;
"""
    return "cbrd_26659_oos_sql06_rollback", body


# ---------------------------------------------------------------------------------------------
# case 5 -- OOS-SQL-06: constraint violations
# ---------------------------------------------------------------------------------------------

def case_sql06_constraints():
    w = "sql06 constraints"
    t, tn = "t_cbrd_26659_sql06c", "t_cbrd_26659_sql06c_nn"
    p1 = oos(4200, w)
    p_dup = oos(4300, w)
    p_uniq = oos(4400, w)
    p_multi = [oos(4500, w), oos(4600, w), oos(4700, w)]
    pc = inline(3000, w)

    survey = f"""SELECT id,
       OCTET_LENGTH(payload) AS payload_octets,
       MD5(payload)          AS payload_md5,
       uniq                  AS uniq
  FROM {t} ORDER BY id;"""

    body = f"""/*
 * CBRD-26659 -- OOS-SQL-06: a statement that fails a constraint leaves no value stored, and
 * the OOS-backed rows that were already there are untouched.
 *
 * Requirements: OOS-SQL-06 (transaction atomicity and undo correctness -- the statement-failure
 * dimension).
 *
 * What this case pins down:
 *   1. a primary-key violation on a row carrying OOS values stores nothing
 *   2. a secondary unique-constraint violation on a row carrying OOS values stores nothing
 *   3. a NOT NULL violation on an OOS-eligible column stores nothing
 *   4. a multi-row INSERT whose last row violates the primary key stores none of its rows
 *   5. after every failure the pre-existing OOS-backed row still reads back byte-identical
 *
 * Expected error identities, derived from the pinned engine before the engine was run:
 *   -670  ER_BTREE_UNIQUE_FAILED        src/base/error_code.h:814; raised at
 *         src/storage/btree.c:31455 because print_key_value_on_unique_error defaults to false
 *         (src/base/system_parameter.c:3133) and the CTP configuration does not set it, so the
 *         with-key variant ER_UNIQUE_VIOLATION_WITHKEY (-886) is not the one taken.
 *   -631  ER_NULL_CONSTRAINT_VIOLATION  src/base/error_code.h:765; raised on the server insert
 *         path, src/query/query_executor.c:12450.
 * CTP renders a failed statement as `Error:-<code>` and nothing else, so the answer carries the
 * identity and never a message whose text or embedded OIDs could drift.
 *
 * The primary key is the INT column, never the OOS-backed one, so a violation message can
 * never embed a multi-kilobyte key.
 *
{header_common(TAG_NEIGHBOUR, 'a', 4200)} */

DROP TABLE IF EXISTS {tn};
DROP TABLE IF EXISTS {t};
CREATE TABLE {t} (id INT PRIMARY KEY, payload BIT VARYING, tag BIT VARYING, uniq INT UNIQUE);

{evaluate(f'[TEST 1] the fixture: one OOS-backed row ({p1} B) and one inline comparator ({pc} B)')}
INSERT INTO {t} VALUES (1, {val('a', p1)}, {val('b', TAG)}, 100);
INSERT INTO {t} VALUES (2, {val('c', pc)}, {val('d', TAG)}, 200);
{survey}

{evaluate('[TEST 2] primary-key violation by a row carrying OOS values: expect Error:-670')}
INSERT INTO {t} VALUES (1, {val('e', p_dup)}, {val('5', TAG)}, 300);
{survey}
{select_row(t, 1, val('a', p1), val('b', TAG))}

{evaluate('[TEST 3] secondary unique violation by a row carrying OOS values: expect Error:-670')}
INSERT INTO {t} VALUES (3, {val('f', p_uniq)}, {val('6', TAG)}, 100);
{survey}

{evaluate('[TEST 4] NOT NULL violation on an OOS-eligible column: expect Error:-631')}
CREATE TABLE {tn} (id INT PRIMARY KEY, payload BIT VARYING NOT NULL, tag BIT VARYING);
INSERT INTO {tn} VALUES (1, NULL, {val('b', TAG)});
SELECT COUNT(*) AS n_rows_after_not_null_violation FROM {tn};

{evaluate('[TEST 5] a three-row INSERT whose last row violates the primary key: expect Error:-670 and no partial effect')}
INSERT INTO {t} VALUES
  (4, {val('1', p_multi[0])}, {val('7', TAG)}, 400),
  (5, {val('2', p_multi[1])}, {val('8', TAG)}, 500),
  (1, {val('3', p_multi[2])}, {val('9', TAG)}, 600);
{survey}

{evaluate('[TEST 6] after every failed statement the table is exactly the fixture')}
SELECT COUNT(*) AS n_rows,
       SUM(CASE WHEN id = 1 AND payload = {val('a', p1)} AND tag = {val('b', TAG)} THEN 1
                WHEN id = 2 AND payload = {val('c', pc)} AND tag = {val('d', TAG)} THEN 1
                ELSE 0 END)                 AS n_exact,
       COUNT(DISTINCT MD5(payload))         AS distinct_payloads
  FROM {t};

DROP TABLE {tn};
DROP TABLE {t};
"""
    return "cbrd_26659_oos_sql06_constraints", body


# ---------------------------------------------------------------------------------------------
# case 6 -- OOS-SQL-06 / OOS-SQL-01: triggers that read and write OOS values
# ---------------------------------------------------------------------------------------------

def case_sql06_triggers():
    w = "sql06 triggers"
    t = "t_cbrd_26659_sql06t"
    log, mirror = f"{t}_log", f"{t}_mirror"
    tins, inslog = f"{t}_ins", f"{t}_inslog"
    tr_log, tr_mirror, tr_rej = f"tr_{t}_log", f"tr_{t}_mirror", f"tr_{t}_reject"
    tr_ins = f"tr_{t}_ins"
    p1 = oos(4200, w)
    pc = inline(3000, w)
    p_rej = oos(5000, w)

    body = f"""/*
 * CBRD-26659 -- OOS-SQL-06 / OOS-SQL-01: triggers that read an OOS-backed value and triggers
 * that write one fire correctly, and a trigger that rejects a statement leaves the OOS value
 * that was already stored untouched.
 *
 * Requirements: OOS-SQL-06 (statement failure leaves no partial effect), OOS-SQL-01 (a value
 * written through the trigger path reads back exactly).
 *
 * THE FIXTURE IS BUILT BEFORE ANY TRIGGER EXISTS, deliberately.  At the pinned engine the OOS
 * record gate is applied only on the server-side DML path: an INSERT or UPDATE against a table
 * that carries a matching trigger is routed to the client-side object-template path
 * (src/query/execute_statement.c:12445, sm_class_has_triggers -> SERVER_INSERT_IS_NOT_ALLOWED),
 * which serializes the record on the client and never reaches
 * heap_attrinfo_determine_disk_layout (src/storage/heap_file.c:12310), the only place the gate
 * is applied.  A row inserted into a triggered table is therefore stored fully inline however
 * large it is, and an UPDATE through that path migrates an existing OOS-backed value back
 * inline.  Values stay byte-correct either way, which is exactly why a value-only test cannot
 * see it.  Creating the rows first means the values these triggers read really are OOS-backed.
 *
 * What this case pins down:
 *   1. rows created before any trigger exists, read back exactly (the paired activation check
 *      asserts they are OOS-backed at this point)
 *   2. an AFTER UPDATE trigger reading the row's OOS-backed attribute sees the whole value: it
 *      records its length and its digest, and both match
 *   3. an AFTER UPDATE trigger writing the row into another table produces a byte-identical
 *      copy, so a value written from inside a trigger is correct
 *   4. a BEFORE UPDATE trigger whose action is REJECT fails the statement with Error:-517,
 *      leaves the stored value exactly as it was, and fires neither AFTER trigger
 *   5. an INSERT into a table that carries an INSERT trigger stores every value exactly -- the
 *      clause this suite can assert about that path; that the row is not OOS-backed is the
 *      finding above, recorded by the activation check and the campaign report, never here
 *
 * What this case deliberately does NOT assert: the placement of anything written through a
 * trigger.  Portable SQL cannot see placement, and at this pin it would be asserting the
 * defect.
 *
 * Expected error identity, derived before the engine was run: -517 ER_TR_REJECTED
 * (src/base/error_code.h:609, message 517 in msg/en_US.utf8/cubrid.msg).  The action time is
 * BEFORE because message 520 of the same catalogue states REJECT cannot be used with AFTER or
 * DEFERRED.
 *
{header_common(TAG_NEIGHBOUR, 'a', 4200)} */

DROP TABLE IF EXISTS {inslog};
DROP TABLE IF EXISTS {tins};
DROP TABLE IF EXISTS {mirror};
DROP TABLE IF EXISTS {log};
DROP TABLE IF EXISTS {t};

CREATE TABLE {t} (id INT PRIMARY KEY, payload BIT VARYING, tag BIT VARYING);
CREATE TABLE {log} (seq INT AUTO_INCREMENT PRIMARY KEY, id INT, payload_octets INT,
                    payload_md5 VARCHAR(32));
CREATE TABLE {mirror} (id INT PRIMARY KEY, payload BIT VARYING, tag BIT VARYING);

{evaluate(f'[TEST 1] the fixture, created while the table still has no trigger: OOS-backed ({p1} B) plus an inline comparator ({pc} B)')}
INSERT INTO {t} VALUES (1, {val('a', p1)}, {val('b', TAG)});
INSERT INTO {t} VALUES (2, {val('c', pc)}, {val('d', TAG)});
{select_row(t, 1, val('a', p1), val('b', TAG))}

{evaluate('[TEST 2] a trigger that READS the OOS-backed attribute sees the whole value')}
CREATE TRIGGER {tr_log}
  AFTER UPDATE ON {t}
  EXECUTE INSERT INTO {log} (id, payload_octets, payload_md5)
          VALUES (obj.id, OCTET_LENGTH(obj.payload), MD5(obj.payload));
UPDATE {t} SET tag = {val('7', TAG)} WHERE id = 1;
SELECT id, payload_octets, payload_md5 FROM {log} ORDER BY seq;
{select_row(t, 1, val('a', p1), val('7', TAG))}

{evaluate('[TEST 3] a trigger that WRITES the value into another table produces a byte-identical copy')}
CREATE TRIGGER {tr_mirror}
  AFTER UPDATE ON {t}
  EXECUTE INSERT INTO {mirror} VALUES (obj.id, obj.payload, obj.tag);
UPDATE {t} SET tag = {val('8', TAG)} WHERE id = 1;
{select_row(mirror, 1, val('a', p1), val('8', TAG))}
SELECT COUNT(*) AS n_mirrored,
       SUM(CASE WHEN m.payload = s.payload AND m.tag = s.tag THEN 1 ELSE 0 END) AS n_identical,
       SUM(CASE WHEN MD5(m.payload) = MD5(s.payload) THEN 1 ELSE 0 END)         AS n_same_digest
  FROM {mirror} m, {t} s WHERE m.id = s.id;
SELECT id, payload_octets, payload_md5 FROM {log} ORDER BY seq;

{evaluate('[TEST 4] a BEFORE UPDATE trigger rejecting the statement: expect Error:-517')}
CREATE TRIGGER {tr_rej}
  BEFORE UPDATE ON {t}
  IF obj.id = 1
  EXECUTE REJECT;
UPDATE {t} SET payload = {val('f', p_rej)} WHERE id = 1;

{evaluate('[TEST 5] the rejected UPDATE left the stored value exactly as it was and fired no AFTER trigger')}
{select_row(t, 1, val('a', p1), val('8', TAG))}
SELECT COUNT(*) AS n_log_rows FROM {log};
SELECT COUNT(*) AS n_mirror_rows FROM {mirror};
SELECT COUNT(*) AS n_rows,
       COUNT(DISTINCT MD5(payload)) AS distinct_payloads
  FROM {t};

{evaluate(f'[TEST 6] an INSERT into a table that already carries an INSERT trigger: every value still exact')}
CREATE TABLE {tins} (id INT PRIMARY KEY, payload BIT VARYING, tag BIT VARYING);
CREATE TABLE {inslog} (id INT PRIMARY KEY, payload_octets INT, payload_md5 VARCHAR(32));
CREATE TRIGGER {tr_ins}
  AFTER INSERT ON {tins}
  EXECUTE INSERT INTO {inslog} VALUES (obj.id, OCTET_LENGTH(obj.payload), MD5(obj.payload));
INSERT INTO {tins} VALUES (1, {val('a', p1)}, {val('b', TAG)});
{select_row(tins, 1, val('a', p1), val('b', TAG))}
SELECT id, payload_octets, payload_md5 FROM {inslog} ORDER BY id;

DROP TRIGGER {tr_ins};
DROP TRIGGER {tr_rej};
DROP TRIGGER {tr_mirror};
DROP TRIGGER {tr_log};
DROP TABLE {inslog};
DROP TABLE {tins};
DROP TABLE {mirror};
DROP TABLE {log};
DROP TABLE {t};
"""
    return "cbrd_26659_oos_sql06_triggers", body


# ---------------------------------------------------------------------------------------------
# case 7 -- OOS-REP-06: LOB locator columns beside OOS-eligible columns
# ---------------------------------------------------------------------------------------------

def case_rep06_lob():
    w = "rep06 lob"
    t, tc = "t_cbrd_26659_rep06_lob", "t_cbrd_26659_rep06_lob_copy"
    p1 = oos(4200, w)
    pc = inline(3000, w)
    lob_bytes = 64
    lobs = [("b1", "a1"), ("b2", "b2"), ("b3", "c3"), ("b4", "d4")]
    clob_text = "cbrd-26659-oos-clob-neighbour"

    def blob_expr(pat):
        return f"BIT_TO_BLOB(CAST(REPEAT('{pat}', {lob_bytes}) AS BIT VARYING))"

    def blob_check(col, pat):
        return (f"BLOB_TO_BIT({col}) = CAST(REPEAT('{pat}', {lob_bytes}) AS BIT VARYING) "
                f"AS {col}_ok")

    lob_values = ", ".join(blob_expr(p) for _c, p in lobs)
    lob_checks = ",\n       ".join(blob_check(c, p) for c, p in lobs)
    lob_lengths = ",\n       ".join(f"BLOB_LENGTH({c}) AS {c}_len" for c, _p in lobs)

    body = f"""/*
 * CBRD-26659 -- OOS-REP-06: LOB locator columns are ordinary variable values beside
 * OOS-eligible columns, and copying or deleting rows that carry both keeps every payload
 * readable.
 *
 * Requirements: OOS-REP-06 (type-agnostic eligibility including LOB locators, ADR-0002),
 * OOS-SQL-01 (INSERT then SELECT returns the exact value), OOS-SQL-05 (DELETE semantics).
 *
 * ADR-0002 makes demotion type-agnostic: a BLOB or CLOB column's in-row value is its ELO
 * locator string, which is eligible like any other variable value, and only those locator
 * bytes would go to OOS -- the LOB payload itself stays in external LOB storage.  So the
 * interesting question here is not whether a locator is demoted (it is far too short to be the
 * largest candidate beside a {p1} B payload) but whether the OOS machinery beside it preserves
 * LOB copy semantics.
 *
 * What this case pins down:
 *   1. a row carrying four BLOB locators, one CLOB locator and an OOS-backed BIT VARYING
 *      column reads every one of them back exactly
 *   2. INSERT ... SELECT copies such a row: the copy's OOS value and all five LOB payloads
 *      read back exactly
 *   3. deleting the source row does not take the copy's external payload with it -- every LOB
 *      of the copy is still readable afterwards, which is the clause that would fail if the
 *      copy had borrowed the source's external file instead of copying it
 *
 * What this case deliberately does NOT assert: that the locator string itself was or was not
 * demoted.  Portable SQL cannot see it, and with a {p1} B neighbour the largest-first loop
 * stops long before a locator becomes the largest candidate.
 *
{header_common(TAG_NEIGHBOUR, 'a', 4200)} */

DROP TABLE IF EXISTS {tc};
DROP TABLE IF EXISTS {t};

CREATE TABLE {t} (id INT PRIMARY KEY, payload BIT VARYING, tag BIT VARYING,
                  b1 BLOB, b2 BLOB, b3 BLOB, b4 BLOB, c1 CLOB);
CREATE TABLE {tc} (id INT PRIMARY KEY, payload BIT VARYING, tag BIT VARYING,
                   b1 BLOB, b2 BLOB, b3 BLOB, b4 BLOB, c1 CLOB);

{evaluate(f'[TEST 1] one OOS-backed row ({p1} B) and one inline comparator ({pc} B), each with five locators')}
INSERT INTO {t} VALUES (1, {val('a', p1)}, {val('b', TAG)},
                        {lob_values}, CHAR_TO_CLOB('{clob_text}-1'));
INSERT INTO {t} VALUES (2, {val('c', pc)}, {val('d', TAG)},
                        {lob_values}, CHAR_TO_CLOB('{clob_text}-2'));
SELECT id,
       OCTET_LENGTH(payload) AS payload_octets,
       MD5(payload)          AS payload_md5,
       {lob_lengths},
       CLOB_LENGTH(c1)       AS c1_len
  FROM {t} ORDER BY id;

{evaluate('[TEST 2] every value of the OOS-backed row reads back exactly, locators included')}
SELECT id,
       payload = {val('a', p1)} AS payload_ok,
       tag     = {val('b', TAG)} AS tag_ok,
       {lob_checks},
       CLOB_TO_CHAR(c1) = '{clob_text}-1' AS c1_ok
  FROM {t} WHERE id = 1;

{evaluate('[TEST 3] INSERT ... SELECT copies both rows, OOS value and locators together')}
INSERT INTO {tc} SELECT id, payload, tag, b1, b2, b3, b4, c1 FROM {t};
SELECT id,
       payload = CASE id WHEN 1 THEN {val('a', p1)} ELSE {val('c', pc)} END AS payload_ok,
       {lob_checks},
       CLOB_TO_CHAR(c1) = CONCAT('{clob_text}-', CAST(id AS VARCHAR(2))) AS c1_ok
  FROM {tc} ORDER BY id;

{evaluate('[TEST 4] DELETE the source rows; the copy must keep every external payload')}
DELETE FROM {t};
SELECT COUNT(*) AS n_source_rows FROM {t};
SELECT id,
       OCTET_LENGTH(payload) AS payload_octets,
       MD5(payload)          AS payload_md5,
       {lob_lengths},
       CLOB_LENGTH(c1)       AS c1_len
  FROM {tc} ORDER BY id;

{evaluate('[TEST 5] and the copy still reads back exactly, value for value')}
SELECT id,
       payload = CASE id WHEN 1 THEN {val('a', p1)} ELSE {val('c', pc)} END AS payload_ok,
       tag     = CASE id WHEN 1 THEN {val('b', TAG)} ELSE {val('d', TAG)} END AS tag_ok,
       {lob_checks},
       CLOB_TO_CHAR(c1) = CONCAT('{clob_text}-', CAST(id AS VARCHAR(2))) AS c1_ok
  FROM {tc} ORDER BY id;

DROP TABLE {tc};
DROP TABLE {t};
"""
    return "cbrd_26659_oos_rep06_lob_neighbours", body


# ---------------------------------------------------------------------------------------------
# case 8 -- the reused CBRD-27006 mixed single-chunk / multi-chunk workload
# ---------------------------------------------------------------------------------------------

def case_mixed_chunks():
    t = "t_cbrd_26659_sql02_mixed"
    names = ["single1", "multi1", "single2"]
    rows = {
        1: [3500, 20000, 3500],
        2: [3600, 21000, 3400],
    }
    upd = [3700, 22000, 3300]
    for rid, sizes in rows.items():
        d.classify(sizes, names)
    d.classify(upd, names)
    _k1, _dem1, tie1 = d.classify(rows[1], names)
    assert tie1, "row 1 of the reused workload is expected to be a documented tie"

    pats = {1: ["1", "2", "3"], 2: ["4", "5", "6"]}
    upd_pats = ["7", "8", "9"]

    def row_values(rid, sizes, pats_):
        vals = ", ".join(val(c, n) for c, n in zip(pats_, sizes))
        return f"INSERT INTO {t} VALUES ({rid}, {vals});"

    def survey(expect):
        """expect: {id: (chars, sizes)}"""
        cases_ = {c: " ".join(
            f"WHEN {rid} THEN {val(ch[i], sz[i])}" for rid, (ch, sz) in expect.items())
            for i, c in enumerate(names)}
        checks = ",\n       ".join(
            f"{c} = CASE id {cases_[c]} END AS {c}_ok" for c in names)
        lens = ",\n       ".join(f"OCTET_LENGTH({c}) AS {c}_octets" for c in names)
        digs = ",\n       ".join(f"MD5({c}) AS {c}_md5" for c in names)
        return f"""SELECT id,
       {lens},
       {digs},
       {checks}
  FROM {t} ORDER BY id;"""

    e1 = {1: (pats[1], rows[1])}
    e2 = {1: (pats[1], rows[1]), 2: (pats[2], rows[2])}
    e3 = {1: (upd_pats, upd), 2: (pats[2], rows[2])}

    body = f"""/*
 * CBRD-26659 -- the public CBRD-27006 mixed single-chunk and multi-chunk workload, reused.
 *
 * Requirements: OOS-SQL-01 (INSERT then SELECT returns the exact value), OOS-SQL-02 (UPDATE
 * correctness).
 *
 * PROVENANCE.  The workload -- two INSERT row groups and one UPDATE over a four-column table
 * mixing single-chunk and multi-chunk BIT VARYING values -- is taken from
 * sql/_36_guava/cbrd_27006/cases/cbrd_27006_oos_ha_repl.sql, added to this repository by
 * commit 1fdcaf93511acf0f94c71e0fdacc45e42fa34e16 ("[CBRD-27006] Add OOS HA replication
 * regression", 2026-07-20).  The column sizes are reused verbatim: {rows[1][0]}/{rows[1][1]}/{rows[1][2]} for row 1,
 * {rows[2][0]}/{rows[2][1]}/{rows[2][2]} for row 2, {upd[0]}/{upd[1]}/{upd[2]} after the UPDATE.
 *
 * WHAT IS NOT INHERITED.  The original asserts LENGTH and whole-value equality only.  It makes
 * no claim about chunk topology, and it cannot: nothing in it distinguishes a value stored in
 * one chunk from a value stored in two, and nothing in it shows the rows were OOS-backed at
 * all.  Two things are added here rather than assumed:
 *   - the topology is derived, not observed: at 16 KiB the largest single-chunk value is
 *     16283 B under the pinned 16-byte chunk header and 16275 B under the normative 24-byte
 *     one, so {rows[1][1]}..{upd[1]} B is two chunks under both accountings, while
 *     {rows[1][2]}..{rows[1][0]} B is one chunk under both
 *   - the paired activation check reads SHOW HEAP OOS, so the chunk counts are evidence rather
 *     than inference.
 *
 * A DOCUMENTED TIE.  Row 1 of the original has two equal-size eligible columns: single1 and
 * single2 are both {rows[1][0]} B.  The normative text says candidates are sorted by size descending
 * and says nothing about equal sizes, so which of the two is demoted is not settled, and this
 * case asserts neither.  It is not engineered away, because the point of reusing the workload
 * is to reuse it: the sizes stay as CBRD-27006 wrote them and the tie is recorded instead.
 * The activation check is unaffected -- the two columns being the same size, the chunk count
 * and the payload sum are identical whichever one moved.
 *
{header_common(MIXED_NEIGHBOUR, '1', rows[1][0])} */

DROP TABLE IF EXISTS {t};
CREATE TABLE {t}
  (id INT PRIMARY KEY, single1 BIT VARYING, multi1 BIT VARYING, single2 BIT VARYING);

{evaluate(f'[TEST 1] first row group: {rows[1][0]}/{rows[1][1]}/{rows[1][2]} B, mixing single-chunk and multi-chunk values')}
{row_values(1, rows[1], pats[1])}
{survey(e1)}

{evaluate(f'[TEST 2] second row group: {rows[2][0]}/{rows[2][1]}/{rows[2][2]} B; both rows must keep their own values')}
{row_values(2, rows[2], pats[2])}
{survey(e2)}

{evaluate(f'[TEST 3] UPDATE all three values of row 1 to {upd[0]}/{upd[1]}/{upd[2]} B; row 2 must not move')}
UPDATE {t}
   SET single1 = {val(upd_pats[0], upd[0])},
       multi1  = {val(upd_pats[1], upd[1])},
       single2 = {val(upd_pats[2], upd[2])}
 WHERE id = 1;
{survey(e3)}

{evaluate('[TEST 4] no two columns of any row alias one another')}
SELECT COUNT(*) AS n_rows,
       SUM(CASE WHEN single1 = multi1 OR single1 = single2 OR multi1 = single2
                THEN 1 ELSE 0 END) AS n_aliased,
       COUNT(DISTINCT MD5(multi1)) AS distinct_multi1
  FROM {t};

DROP TABLE {t};
"""
    return "cbrd_26659_oos_sql02_mixed_chunks", body


# ---------------------------------------------------------------------------------------------
# activation specs -- the fixture each case's paired SHOW HEAP OOS checker replays
# ---------------------------------------------------------------------------------------------

HDR = d.ob.OOS_RECORD_HEADER_SIZE_PINNED


def sumlen(*sizes):
    """Oos_recs_sumlen for a set of demoted values, at the PINNED 16-byte chunk header.

    The 24-byte normative header would give a different number; that difference is the
    Capability gap already recorded against OOS-REP-05, and it never reaches an answer file --
    only this checker carries these figures.
    """
    return sum(d.varbit(n) + d.chunks(n, HDR) * HDR for n in sizes)


SPEC_HEADER = """\
# CBRD-26659 ticket 19 activation spec for {case}.
# Generated with the case itself by evidence/ticket19/gen_ticket19_cases.py; run by
# tools/activation_check_spec.sh, client-server, under campaign_ns.sh (user decision O2,
# ticket 35).  PHASE <tag> <table> <has_oos> <num_recs> <sumlen>; `-` observes instead of
# asserting.  Every asserted figure is derived, never measured: see derivation-output.txt.
"""


def spec_sql01():
    t, b100 = "t_cbrd_26659_sql01", "t_cbrd_26659_sql01_b100"
    b1000, tc = "t_cbrd_26659_sql01_b1000", "t_cbrd_26659_sql01_copy"
    n10, n1000 = "n10_cbrd_26659_sql01", "n1000_cbrd_26659_sql01"
    g, g1k = d.BULK_100, d.BULK_1000
    bulk_total = sumlen(*[g.size(i) for i in g.ids()])
    bulk1k_total = sumlen(*[g1k.size(i) for i in g1k.ids()])
    return "cbrd_26659_oos_sql01_insert_select", f"""{SPEC_HEADER.format(case='cbrd_26659_oos_sql01_insert_select')}
PHASE create {t} 0 0 0
DROP TABLE IF EXISTS {t};
CREATE TABLE {t} (id INT PRIMARY KEY, payload BIT VARYING, tag BIT VARYING);
PHASE comparator {t} 0 0 0
INSERT INTO {t} VALUES (2, {val('c', 3000)}, {val('d', TAG)});
PHASE oosbacked {t} 1 1 {sumlen(4200)}
INSERT INTO {t} VALUES (1, {val('a', 4200)}, {val('b', TAG)});
PHASE bulk100 {b100} 1 {g.n_rows} {bulk_total}
DROP TABLE IF EXISTS {b1000};
DROP TABLE IF EXISTS {b100};
DROP TABLE IF EXISTS {n1000};
DROP TABLE IF EXISTS {n10};
CREATE TABLE {n10} (i INT);
INSERT INTO {n10} VALUES (0), (1), (2), (3), (4), (5), (6), (7), (8), (9);
CREATE TABLE {n1000} (i INT PRIMARY KEY);
INSERT INTO {n1000} SELECT a.i * 100 + b.i * 10 + c.i + 1 FROM {n10} a, {n10} b, {n10} c;
CREATE TABLE {b100} (id INT PRIMARY KEY, payload BIT VARYING, tag BIT VARYING);
INSERT INTO {b100}
  SELECT i, {g.value_sql('i')}, {val('7', TAG)} FROM {n1000} WHERE i <= {g.n_rows};
# The thousand-row group too: without this phase its OOS-backed premise would be derived and
# never observed, while the case's answer asserts all thousand values read back exactly.
PHASE bulk1000 {b1000} 1 {g1k.n_rows} {bulk1k_total}
CREATE TABLE {b1000} (id INT PRIMARY KEY, payload BIT VARYING, tag BIT VARYING);
INSERT INTO {b1000}
  SELECT i, {g1k.value_sql('i')}, {val('7', TAG)} FROM {n1000};
# INSERT ... SELECT is a different execution path from INSERT ... VALUES -- CUBRID decides them
# separately (execute_statement.c, INSERT_SELECT versus INSERT_VALUES) -- and finding T19-F1
# proves the path, not the size, decides whether the record gate runs at all.  So the copy the
# case makes is observed on its own table rather than inherited from the group it copies.
PHASE copy {tc} 1 {g.n_rows} {bulk_total}
DROP TABLE IF EXISTS {tc};
CREATE TABLE {tc} (id INT PRIMARY KEY, payload BIT VARYING, tag BIT VARYING);
INSERT INTO {tc} SELECT id, payload, tag FROM {b100};
"""


def spec_sql02():
    t = "t_cbrd_26659_sql02"
    tsub, tsrc = f"{t}_chk_sub", f"{t}_chk_src"
    tjoin = f"{t}_chk_join"
    return "cbrd_26659_oos_sql02_update", f"""{SPEC_HEADER.format(case='cbrd_26659_oos_sql02_update')}
PHASE create {t} 0 0 0
DROP TABLE IF EXISTS {t};
CREATE TABLE {t} (id INT PRIMARY KEY, payload BIT VARYING, tag BIT VARYING);
PHASE oosbacked {t} 1 1 {sumlen(4200)}
INSERT INTO {t} VALUES (1, {val('a', 4200)}, {val('b', TAG)});
PHASE comparator {t} 1 1 {sumlen(4200)}
INSERT INTO {t} VALUES (2, {val('c', 3000)}, {val('d', TAG)});
# From here the counts are current behaviour, not a requirement: at the pin every UPDATE
# allocates fresh value chains, and the dead ones stay until vacuum (OOS-SQL-03,
# observation-only, superseded on paper by CBRD-27230).  Observed, never asserted.
PHASE update_payload {t} 1 - -
UPDATE {t} SET payload = {val('e', 5000)} WHERE id = 1;
PHASE update_tag_only {t} 1 - -
UPDATE {t} SET tag = {val('7', TAG)} WHERE id = 1;
PHASE update_multichunk {t} 1 - -
UPDATE {t} SET payload = {val('f', 20000)} WHERE id = 1;
# The last two steps of the case write through two further execution paths: an UPDATE whose
# value comes from a subquery, and a multi-table UPDATE.  Finding T19-F1 is exactly a path that
# silently skips the record gate, so neither is inherited from the phases above; each runs on
# its own fresh table, starting from an inline row, so the count after it is unambiguous.
PHASE subquery_update {tsub} 1 1 {sumlen(4600)}
DROP TABLE IF EXISTS {tsub};
DROP TABLE IF EXISTS {tsrc};
CREATE TABLE {tsub} (id INT PRIMARY KEY, payload BIT VARYING, tag BIT VARYING);
CREATE TABLE {tsrc} (id INT PRIMARY KEY, payload BIT VARYING, tag BIT VARYING);
INSERT INTO {tsrc} VALUES (1, {val('d', 4600)}, {val('5', TAG)});
INSERT INTO {tsub} VALUES (1, {val('c', 3000)}, {val('d', TAG)});
UPDATE {tsub} SET payload = (SELECT payload FROM {tsrc} WHERE id = 1) WHERE id = 1;
PHASE join_update {tjoin} 1 1 {sumlen(4600)}
DROP TABLE IF EXISTS {tjoin};
CREATE TABLE {tjoin} (id INT PRIMARY KEY, payload BIT VARYING, tag BIT VARYING);
INSERT INTO {tjoin} VALUES (1, {val('c', 3000)}, {val('d', TAG)});
UPDATE {tjoin} a, {tsrc} b SET a.payload = b.payload, a.tag = b.tag WHERE a.id = 1 AND b.id = 1;
"""


def spec_sql05():
    t = "t_cbrd_26659_sql05"
    return "cbrd_26659_oos_sql05_delete", f"""{SPEC_HEADER.format(case='cbrd_26659_oos_sql05_delete')}
PHASE create {t} 0 0 0
DROP TABLE IF EXISTS {t};
CREATE TABLE {t} (id INT PRIMARY KEY, payload BIT VARYING, tag BIT VARYING);
PHASE fixture {t} 1 3 {sumlen(4200, 4400, 4600)}
INSERT INTO {t} VALUES (1, {val('a', 4200)}, {val('b', TAG)});
INSERT INTO {t} VALUES (2, {val('c', 3000)}, {val('d', TAG)});
INSERT INTO {t} VALUES (3, {val('e', 4400)}, {val('5', TAG)});
INSERT INTO {t} VALUES (4, {val('f', 4600)}, {val('6', TAG)});
# OOS-SQL-05 says the value chains are not removed at delete time in MVCC mode, and they are
# not -- but the moment vacuum reclaims them is a background event, so the count here is
# OBSERVED with its expected value beside it rather than asserted against a race.
# Expected while the deletes are still undo sources: {sumlen(4200, 4400, 4600)} unchanged after one DELETE,
# and unchanged again after DELETE of the rest.
PHASE delete_one {t} 1 - -
DELETE FROM {t} WHERE id = 1;
PHASE delete_rest {t} 1 - -
DELETE FROM {t};
"""


def spec_sql06_rollback():
    t = "t_cbrd_26659_sql06r"
    return "cbrd_26659_oos_sql06_rollback", f"""{SPEC_HEADER.format(case='cbrd_26659_oos_sql06_rollback')}
# Only the committed fixture is replayed: what makes this case OOS coverage is that the rows
# the transactions write and undo are OOS-backed.  The undo semantics themselves are asserted
# by the case at the SQL seam, which is where they are observable, and csql's own autocommit
# control is a session command rather than SQL, so replaying the transactions here would test
# the checker's driver rather than the engine.
PHASE create {t} 0 0 0
DROP TABLE IF EXISTS {t};
CREATE TABLE {t} (id INT PRIMARY KEY, payload BIT VARYING, tag BIT VARYING);
PHASE fixture {t} 1 1 {sumlen(4200)}
INSERT INTO {t} VALUES (1, {val('a', 4200)}, {val('b', TAG)});
INSERT INTO {t} VALUES (2, {val('c', 3000)}, {val('d', TAG)});
"""


def spec_sql06_constraints():
    t = "t_cbrd_26659_sql06c"
    return "cbrd_26659_oos_sql06_constraints", f"""{SPEC_HEADER.format(case='cbrd_26659_oos_sql06_constraints')}
PHASE create {t} 0 0 0
DROP TABLE IF EXISTS {t};
CREATE TABLE {t} (id INT PRIMARY KEY, payload BIT VARYING, tag BIT VARYING, uniq INT UNIQUE);
PHASE fixture {t} 1 1 {sumlen(4200)}
INSERT INTO {t} VALUES (1, {val('a', 4200)}, {val('b', TAG)}, 100);
INSERT INTO {t} VALUES (2, {val('c', 3000)}, {val('d', TAG)}, 200);
# The rejected INSERT may or may not have written chunks before the unique check refused it,
# and any it wrote are dead and awaiting vacuum, so the count is observed.  What IS asserted at
# the SQL seam is that no VALUE is stored -- see the case.
PHASE after_pk_violation {t} 1 - -
INSERT INTO {t} VALUES (1, {val('e', 4300)}, {val('5', TAG)}, 300);
"""


def spec_sql06_triggers():
    t = "t_cbrd_26659_sql06t"
    log, mirror = f"{t}_log", f"{t}_mirror"
    tins, inslog = f"{t}_ins", f"{t}_inslog"
    return "cbrd_26659_oos_sql06_triggers", f"""{SPEC_HEADER.format(case='cbrd_26659_oos_sql06_triggers')}
PHASE create {t} 0 0 0
DROP TABLE IF EXISTS {inslog};
DROP TABLE IF EXISTS {tins};
DROP TABLE IF EXISTS {mirror};
DROP TABLE IF EXISTS {log};
DROP TABLE IF EXISTS {t};
CREATE TABLE {t} (id INT PRIMARY KEY, payload BIT VARYING, tag BIT VARYING);
CREATE TABLE {log} (seq INT AUTO_INCREMENT PRIMARY KEY, id INT, payload_octets INT,
                    payload_md5 VARCHAR(32));
CREATE TABLE {mirror} (id INT PRIMARY KEY, payload BIT VARYING, tag BIT VARYING);
# The fixture is built while the table still has no trigger, so these rows really are
# OOS-backed.  This is the phase that makes the case OOS coverage at all.
PHASE pre_trigger_inserts {t} 1 1 {sumlen(4200)}
INSERT INTO {t} VALUES (1, {val('a', 4200)}, {val('b', TAG)});
INSERT INTO {t} VALUES (2, {val('c', 3000)}, {val('d', TAG)});
# FINDING (campaign report, ticket 19): the OOS record gate is applied only on the server-side
# DML path.  Once the table carries a trigger, the UPDATE below is routed to the client-side
# object-template path (execute_statement.c:12445) and never reaches
# heap_attrinfo_determine_disk_layout, so it rewrites the record fully inline and drops the
# chain.  Were the gate path-independent this phase would still read 1 / {sumlen(4200)}.
# OBSERVED, not asserted: asserting either number would bless one side of the defect.
PHASE after_triggered_update {t} 1 - -
CREATE TRIGGER tr_{t}_log AFTER UPDATE ON {t}
  EXECUTE INSERT INTO {log} (id, payload_octets, payload_md5)
          VALUES (obj.id, OCTET_LENGTH(obj.payload), MD5(obj.payload));
UPDATE {t} SET tag = {val('7', TAG)} WHERE id = 1;
# Same finding on the INSERT side: a fresh table whose first INSERT carries a trigger.  Were
# the gate path-independent this phase would read 1 / 1 / {sumlen(4200)}.  All three observed.
PHASE insert_trigger_table {tins} - - -
CREATE TABLE {tins} (id INT PRIMARY KEY, payload BIT VARYING, tag BIT VARYING);
CREATE TABLE {inslog} (id INT PRIMARY KEY, payload_octets INT, payload_md5 VARCHAR(32));
CREATE TRIGGER tr_{t}_ins AFTER INSERT ON {tins}
  EXECUTE INSERT INTO {inslog} VALUES (obj.id, OCTET_LENGTH(obj.payload), MD5(obj.payload));
INSERT INTO {tins} VALUES (1, {val('a', 4200)}, {val('b', TAG)});
"""


def spec_rep06_lob():
    t, tc = "t_cbrd_26659_rep06_lob", "t_cbrd_26659_rep06_lob_copy"
    lob_bytes, clob_text = 64, "cbrd-26659-oos-clob-neighbour"
    blobs = ", ".join(
        f"BIT_TO_BLOB(CAST(REPEAT('{p}', {lob_bytes}) AS BIT VARYING))"
        for p in ("a1", "b2", "c3", "d4"))
    return "cbrd_26659_oos_rep06_lob_neighbours", f"""{SPEC_HEADER.format(case='cbrd_26659_oos_rep06_lob_neighbours')}
PHASE create {t} 0 0 0
DROP TABLE IF EXISTS {t};
CREATE TABLE {t} (id INT PRIMARY KEY, payload BIT VARYING, tag BIT VARYING,
                  b1 BLOB, b2 BLOB, b3 BLOB, b4 BLOB, c1 CLOB);
# One chunk holding the 4200 B payload: the five locator strings are eligible but far too short
# to be the largest candidate, so the largest-first loop stops after `payload` (ADR-0002).
PHASE oosbacked {t} 1 1 {sumlen(4200)}
INSERT INTO {t} VALUES (1, {val('a', 4200)}, {val('b', TAG)},
                        {blobs}, CHAR_TO_CLOB('{clob_text}-1'));
INSERT INTO {t} VALUES (2, {val('c', 3000)}, {val('d', TAG)},
                        {blobs}, CHAR_TO_CLOB('{clob_text}-2'));
# The copy, on the INSERT ... SELECT path, carrying five locators with it.  One chunk, because
# only row 1 is above the gate; the locators are eligible but far too short to be the largest
# candidate beside a 4200 B payload.
PHASE copy {tc} 1 1 {sumlen(4200)}
DROP TABLE IF EXISTS {tc};
CREATE TABLE {tc} (id INT PRIMARY KEY, payload BIT VARYING, tag BIT VARYING,
                   b1 BLOB, b2 BLOB, b3 BLOB, b4 BLOB, c1 CLOB);
INSERT INTO {tc} SELECT id, payload, tag, b1, b2, b3, b4, c1 FROM {t};
"""


def spec_mixed_chunks():
    t = "t_cbrd_26659_sql02_mixed"
    r1, r2 = [3500, 20000, 3500], [3600, 21000, 3400]
    return "cbrd_26659_oos_sql02_mixed_chunks", f"""{SPEC_HEADER.format(case='cbrd_26659_oos_sql02_mixed_chunks')}
PHASE create {t} 0 0 0
DROP TABLE IF EXISTS {t};
CREATE TABLE {t}
  (id INT PRIMARY KEY, single1 BIT VARYING, multi1 BIT VARYING, single2 BIT VARYING);
# Three chunk records for row 1: two for the {r1[1]} B value and one for the 3500 B one.  This is
# where the reused CBRD-27006 workload's chunk topology stops being an inference.  The
# equal-size tie between single1 and single2 does not reach these figures: the two columns
# being the same size, the count and the sum are identical whichever one moved.
PHASE row1 {t} 1 3 {sumlen(r1[1], r1[0])}
INSERT INTO {t} VALUES (1, {val('1', r1[0])}, {val('2', r1[1])}, {val('3', r1[2])});
PHASE row2 {t} 1 6 {sumlen(r1[1], r1[0], r2[1], r2[0])}
INSERT INTO {t} VALUES (2, {val('4', r2[0])}, {val('5', r2[1])}, {val('6', r2[2])});
"""


SPECS = [spec_sql01, spec_sql02, spec_sql05, spec_sql06_rollback, spec_sql06_constraints,
         spec_sql06_triggers, spec_rep06_lob, spec_mixed_chunks]


CASES = [case_sql01, case_sql02, case_sql05, case_sql06_rollback, case_sql06_constraints,
         case_sql06_triggers, case_rep06_lob, case_mixed_chunks]


SPEC_DIR = Path(__file__).resolve().parent / "activation"


def lowercase_sql(body: str) -> str:
    """Lower-case the SQL outside comments and string literals.

    The scenario directory's first case was deliberately lower-cased
    (`cbrd_26659_oos_rep02_largest_first.sql`, commit e64c16481) and lower case is the dominant
    style in `sql/_36_guava`, so these cases follow it rather than leaving one directory reading
    two ways.  No keyword list: every identifier, alias and hex pattern these cases emit is
    already lower case, so lower-casing everything outside comments and literals touches exactly
    the keywords.  Comments carry prose and literals carry the EVALUATE labels the answer prints,
    so both are left alone -- which is also what makes the transformation answer-neutral, and the
    answers coming back byte-identical is the proof.
    """
    out, i, n = [], 0, len(body)
    in_block, in_str = False, False
    while i < n:
        c = body[i]
        if in_block:
            out.append(c)
            if body.startswith("*/", i):
                out.append(body[i + 1])
                i += 2
                in_block = False
                continue
        elif in_str:
            out.append(c)
            if c == "'":
                in_str = False
        elif body.startswith("/*", i):
            out.append(body[i:i + 2])
            i += 2
            in_block = True
            continue
        elif c == "'":
            out.append(c)
            in_str = True
        else:
            out.append(c.lower())
        i += 1
    return "".join(out)


def check_no_semicolon_terminated_comment_line(name: str, body: str):
    """Refuse a case whose header comment has a line ending in `;`.

    CTP's SQL runner splits a case file into statements at a line-terminal semicolon WITHOUT
    first stripping block comments, so such a line inside a /* ... */ header is taken as a
    statement boundary: the text before it is sent as an unterminated comment and the text
    after it as a fragment that starts mid-comment, and both come back as ER_PT_SYNTAX (-493).
    The case still runs -- the errors land in the answer, where they would be promoted as
    expected output and quietly stay there.  Found by ticket 19's candidate review on
    cbrd_26659_oos_sql02_mixed_chunks (inv-T19-0002).
    """
    in_comment = False
    for i, line in enumerate(body.splitlines(), 1):
        if line.lstrip().startswith("/*"):
            in_comment = True
        if in_comment and line.rstrip().endswith(";"):
            raise SystemExit(
                f"{name}: line {i} of the header comment ends with a semicolon, which CTP's "
                f"statement splitter reads as a statement boundary:\n    {line.strip()}")
        if "*/" in line:
            in_comment = False


def emit(out: Path, spec_dir: Path | None = None):
    out.mkdir(parents=True, exist_ok=True)
    written = []
    for fn in CASES:
        name, body = fn()
        body = lowercase_sql(body)
        assert lowercase_sql(body) == body, f"{name}: lowercase_sql is not idempotent"
        check_no_semicolon_terminated_comment_line(name, body)
        path = out / f"{name}.sql"
        path.write_text(body)
        written.append(path)
    if spec_dir is not None:
        spec_dir.mkdir(parents=True, exist_ok=True)
        for fn in SPECS:
            name, body = fn()
            (spec_dir / f"{name}.spec").write_text(body)
    return written


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--check", action="store_true",
                    help="regenerate into a temporary directory and compare with --out")
    ap.add_argument("--oracle", action="store_true",
                    help="print the expected scalars of every literal value the cases use, "
                         "derived without running the engine")
    args = ap.parse_args()

    if args.oracle:
        with tempfile.TemporaryDirectory() as tmp:
            emit(Path(tmp))
        print("# Expected scalars of every literal value the ticket-19 cases use\n")
        print("Derived, never observed: DISK_SIZE is ALIGN(5 + N, 4) (or_varbit_length_internal),")
        print("OCTET_LENGTH is N, and MD5 is the digest of the value's lowercase hexadecimal form,")
        print("which is the 2N-character string the case writes.\n")
        print(f"{'SQL literal':<44} {'bytes':>7} {'DISK_SIZE':>10} {'OCTET_LENGTH':>13} {'MD5':>34}")
        print("-" * 112)
        for char, n in sorted(_values, key=lambda t: (t[1], t[0])):
            lit = f"REPEAT('{char}', {2 * n})"
            print(f"{lit:<44} {n:>7} {d.varbit(n):>10} {n:>13} {d.md5_of(char, n):>34}")
        print(f"\n{len(_values)} distinct literal values.")
        return 0

    if args.check:
        with tempfile.TemporaryDirectory() as tmp:
            fresh = emit(Path(tmp))
            bad = []
            for f in fresh:
                target = args.out / f.name
                if not target.exists() or not filecmp.cmp(f, target, shallow=False):
                    bad.append(target.name)
            print(f"{len(fresh)} case(s) generated; "
                  + ("all match the checked-in files" if not bad
                     else f"DIFFER: {', '.join(bad)}"))
            return 1 if bad else 0

    written = emit(args.out, SPEC_DIR)
    for p in written:
        print(f"wrote {p} ({len(p.read_text().splitlines())} lines)")
    kinds = {}
    for kind, _sizes, _where in _emitted:
        kinds[kind] = kinds.get(kind, 0) + 1
    for spec in sorted(SPEC_DIR.glob("*.spec")):
        print(f"wrote {spec}")
    print(f"verified fixtures: {kinds.get('oos', 0)} OOS-backed, {kinds.get('inline', 0)} inline; "
          "every one assertable under both the pinned and the normative accounting")
    return 0


if __name__ == "__main__":
    sys.exit(main())
