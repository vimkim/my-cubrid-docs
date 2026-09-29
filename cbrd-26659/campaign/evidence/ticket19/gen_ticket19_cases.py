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

Not delivered (campaign ticket 45 item 1).  The eight cases cross into `cubrid-testcases` on
their own, each carrying a dated provenance statement in its header instead of a pointer here
(ticket 45 item 2, applied by ticket 47), and they are hand-maintained on arrival.  So `--check`
is meaningful only against this campaign's checked-in copy of the cases: a case edited on the
CUBRID side is not detected by anything, which is the decision's accepted cost.

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

# The date in every emitted case's provenance statement (ticket 45 item 2): the day the checked-in
# cases were emitted, from which they are hand-maintained.  A later emission that changes a case
# is a new generation and sets this to its own date.
PROVENANCE_DATE = "2026-09-19"

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

def header_common(inline_neighbour, md5_char, md5_bytes, provenance_date=PROVENANCE_DATE):
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
 * derived from the engine's record accounting under both, and a size the two disagree about
 * was refused rather than asserted, so this answer is stable rather than specific to
 * one revision.  {inline_neighbour}
 *
 * Value checks are deliberately redundant and independent.  Whole-value equality alone would
 * ask the engine to compare a value it read back against one it built itself, so a fault that
 * truncated both identically would go unnoticed.  OCTET_LENGTH pins the size and MD5 pins the
 * content through a different code path; CUBRID's MD5 of a BIT VARYING digests its lowercase
 * hexadecimal form, so every digest in the answer is reproducible outside CUBRID, for example
 *   python3 -c "import hashlib; print(hashlib.md5(('{md5_char * 2}'*{md5_bytes}).encode()).hexdigest())"
 *
 * Provenance.  Generated once by the CBRD-26659 campaign on {provenance_date} from the pinned engine's
 * record accounting at commit f4299ac0cd777a2a964c1f197ae5ebf9841a4936, so the fixture sizes
 * are derived from that accounting, not chosen.  Hand-maintained from that date.
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
    # the sizes live in derive_ticket19_sizes.py, which the tie-invariance self-test reads too
    rows = {rid: list(sizes) for rid, sizes in d.REUSED_27006_ROWS.items()}
    upd = list(d.REUSED_27006_UPDATE)
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


# ==============================================================================================
# Ticket 18 -- the public Representation family.
#
# Same generator, same refusal: no size reaches a case file without passing through
# `derive_ticket19_sizes.classify()`.  Ticket 18 adds three expectations to it, because three
# of its boundaries are not the ticket-19 shape:
#
#   `oos-exhausted`  the largest-first loop runs out of candidates with the record still above
#                    the gate, which is the only shape in which a value below the eligibility
#                    floor can be shown to stay inline for its own sake (OOS-REP-04);
#   `disputed`       the fixture sits inside a band where the pinned and the normative
#                    accounting place the value differently.  Such a row may carry VALUE
#                    assertions only -- whole values, lengths and digests are placement-blind --
#                    and its placement is observed, never asserted.  Ticket 18's criteria ask
#                    for exactly two of these, the record gate and the eligibility floor;
#   the placement hints, which are not classified at all: the accounting reproduces
#                    heap_attrinfo_determine_disk_layout for DEFAULT storage only.
# ==============================================================================================

# Ticket 45 item 2 gives the emitted cases a dated provenance statement, and the generator's own
# rule is that "a later emission that changes a case is a new generation and sets this to its
# own date".  Ticket 18's nine cases are emitted on their own date; ticket 19's eight do not
# change and keep theirs, which is what makes `--check` still report all of them identical.
# Whether the family keeps one date or a date per case is campaign ticket 48 item 48.10, still
# open; this follows the rule the code already carries.
PROVENANCE_DATE_T18 = "2026-09-21"

T18_TAG = d.T18_TAG


def t18_fixture(expect, var_bytes, names, where, fixed=()):
    """Route one ticket-18 fixture row through the derivation and record what it is."""
    kind, demoted, tie = d.classify(var_bytes, names, expect=expect, fixed_bytes=fixed)
    _record(kind, tuple(n for n in var_bytes if n is not None), where)
    return kind, demoted, tie


def t18_oos(payload_bytes, where, tag_bytes=T18_TAG):
    t18_fixture("oos", [payload_bytes, tag_bytes], d.T18_SCHEMA_C, where)
    return payload_bytes


def t18_inline(payload_bytes, where, tag_bytes=T18_TAG):
    t18_fixture("inline", [payload_bytes, tag_bytes], d.T18_SCHEMA_C, where)
    return payload_bytes


def t18_disputed(payload_bytes, where, tag_bytes=T18_TAG):
    """A schema-C row inside the record-gate band: value assertions only, placement observed."""
    t18_fixture("disputed", [payload_bytes, tag_bytes], d.T18_SCHEMA_C, where)
    return payload_bytes


def t18_hinted(sizes, where):
    """A placement-hint fixture, deliberately NOT classified.

    `oos_boundaries.layout()` says in its own docstring that it reproduces the arithmetic of
    heap_attrinfo_determine_disk_layout, and that arithmetic is the DEFAULT path: FORCE_OUTLINE
    demotes before the gate is consulted at all and PREFER_INLINE reorders the candidate list.
    Deriving a placement for a hinted column would be deriving it from an accounting that does
    not model the hint, and OOS-REP-13 withholds the expectation in any case.  What is recorded
    here is that the row exists and what its values are; where the engine puts them is what the
    paired checker observes and no case asserts.
    """
    _record("hinted", tuple(sizes), where)
    return sizes


def fixedbit(char, n_bytes):
    """A fixed BIT(8N) value of N bytes of the repeated hex character `char`.

    The fixed filler's only job is to put the record over a gate that demoting every eligible
    variable value cannot bring it back under, which is what makes "the loop ran out of
    candidates" observable (OOS-REP-02's second stop condition, OOS-REP-04's whole claim).
    """
    assert char in d.HEX_ALPHABET, char
    # CUBRID's MD5 of a fixed BIT(8N) digests the same 2N-character hexadecimal form as it does
    # for a BIT VARYING, so a filler's (length, digest) pair is predictable by exactly the rule
    # of `val()` and belongs in the same table.  Ticket 18's first candidate review is what
    # established that: four filler digests were reported as unpredicted, and all four turned
    # out to be `md5(char * 2N)`.
    _values[(char, n_bytes)] = None
    return f"CAST(REPEAT('{char}', {2 * n_bytes}) AS BIT({8 * n_bytes}))"


def col_checks(cols, table, where_clause, order=None):
    """One result row per column: its length, its digest, and whole-value equality.

    Seven of ticket 18's nine cases carry more columns than ticket 19's widest, and the
    eighteen-column record carries fifty-four scalars.  Printing them as one wide row makes a
    diff unreadable and a reviewer's eye the oracle; printing one row per column keeps every
    check on its own line.  `cols` is a list of (label, column, expected SQL expression).
    """
    parts = []
    for i, (label, column, expr) in enumerate(cols, 1):
        head = "SELECT" if i == 1 else "UNION ALL SELECT"
        parts.append(f"""{head} {i} AS col, '{label}' AS name,
       OCTET_LENGTH({column}) AS octets, MD5({column}) AS digest,
       {column} = {expr} AS ok
  FROM {table} WHERE {where_clause}""")
    return "\n".join(parts) + f"\n ORDER BY {order or 'col'};"


NOT_PROVEN_PLACEMENT = """ *
 * What this case deliberately does NOT prove: which column was moved out of the record, or
 * that any column was.  No portable SQL exposes per-attribute placement -- DISK_SIZE reports
 * the logical serialized size whether or not a value was demoted -- so placement is checked
 * separately, outside this suite, by reading SHOW HEAP OOS on tables owned exclusively by that
 * check."""


def t18_header(title, requirements, pins, extra, inline_neighbour, md5_char, md5_bytes,
               not_proven=NOT_PROVEN_PLACEMENT):
    """The header block of a ticket-18 case: what it pins down, then the shared paragraphs."""
    pin_lines = "\n".join(f" *   {i}. {p}" for i, p in enumerate(pins, 1))
    return f"""/*
 * CBRD-26659 -- {title}
 *
 * Requirements: {requirements}.
 *
 * What this case pins down:
{pin_lines}
{not_proven}
{extra}
 *
{header_common(inline_neighbour, md5_char, md5_bytes, PROVENANCE_DATE_T18)} */
"""

# ---------------------------------------------------------------------------------------------
# case 10 -- OOS-REP-01 / OOS-REP-02: both sides of the record gate, and the band between them
# ---------------------------------------------------------------------------------------------

def case_rep01_gate_boundary():
    w = "rep01"
    t = "t_cbrd_26659_rep01"
    inl = t18_inline(d.T18_GATE_INLINE_BOTH, w)
    oos_ = t18_oos(d.T18_GATE_OOS_BOTH, w)
    lo = t18_disputed(d.T18_GATE_BAND_LO, w)
    hi = t18_disputed(d.T18_GATE_BAND_HI, w)
    rec_inl = d.record_before([inl, TAG])
    rec_oos = d.record_before([oos_, TAG])
    gp, gn = d.ob.gate_pinned(d.PAGE_SIZE), d.ob.target_normative(d.PAGE_SIZE)

    extra = f""" *
 * The two gates and the band between them.  At a 16 KiB page the pinned engine compares the
 * serialized record against {gp} B and the four-record physical target accepted in CBRD-27057
 * gives {gn} B, so for this schema the two disagree over a payload of {lo} to {hi} B: the
 * target demotes there and the pinned gate does not.  Rows 1 and 2 sit ONE BYTE outside that
 * band on either side, which is the sharpest pair of boundary values the campaign may assert.
 * Rows 3 and 4 sit at its two edges, deliberately, and they assert values only -- a whole
 * value, its length and its digest are the same whether the value was moved out of the record
 * or not, so these two rows hold under either reading of the gate.  Where the pinned engine
 * actually put them is recorded as an observation and asserted nowhere."""
    body = t18_header(
        "OOS-REP-01 and OOS-REP-02: a record below the gate keeps every column inline, a record "
        "above it is\n * accepted and readable once its largest eligible column has moved, and "
        "every value reads back exactly.",
        "OOS-REP-01 (records at or below the gate stay inline), OOS-REP-02 (largest-first "
        "demotion\n * above the gate)",
        [f"a {inl} B payload leaves a {rec_inl} B record, at or below both gates",
         f"a {oos_} B payload leaves a {rec_oos} B record, above both gates",
         f"a {lo} B and a {hi} B payload, the two edges of the band where the pinned gate and "
         f"the\n *      four-record target disagree: values only",
         "all four rows read back exactly, with no value bleeding into another row"],
        extra, TAG_NEIGHBOUR, 'a', inl)
    body += f"""
DROP TABLE IF EXISTS {t};

CREATE TABLE {t} (id INT PRIMARY KEY, payload BIT VARYING, tag BIT VARYING);

{evaluate(f'[TEST 1] the largest record that stays inline under both gates ({inl} B payload, record {rec_inl} B)')}
INSERT INTO {t} VALUES (1, {val('a', inl)}, {val('b', TAG)});
{select_row(t, 1, val('a', inl), val('b', TAG))}

{evaluate(f'[TEST 2] the smallest record demoted under both gates ({oos_} B payload, record {rec_oos} B, {chunks_note(oos_)})')}
INSERT INTO {t} VALUES (2, {val('c', oos_)}, {val('d', TAG)});
{select_row(t, 2, val('c', oos_), val('d', TAG))}

{evaluate(f'[TEST 3] the low edge of the disputed band ({lo} B payload): values only, placement observed elsewhere')}
INSERT INTO {t} VALUES (3, {val('e', lo)}, {val('f', TAG)});
{select_row(t, 3, val('e', lo), val('f', TAG))}

{evaluate(f'[TEST 4] the high edge of the disputed band ({hi} B payload): values only, placement observed elsewhere')}
INSERT INTO {t} VALUES (4, {val('9', hi)}, {val('8', TAG)});
{select_row(t, 4, val('9', hi), val('8', TAG))}

{evaluate('[TEST 5] every row still holds its own values, with no cross-row bleed')}
SELECT COUNT(*) AS n_rows,
       SUM(CASE WHEN id = 1 AND payload = {val('a', inl)} AND tag = {val('b', TAG)} THEN 1
                WHEN id = 2 AND payload = {val('c', oos_)} AND tag = {val('d', TAG)} THEN 1
                WHEN id = 3 AND payload = {val('e', lo)} AND tag = {val('f', TAG)} THEN 1
                WHEN id = 4 AND payload = {val('9', hi)} AND tag = {val('8', TAG)} THEN 1
                ELSE 0 END) AS n_exact,
       COUNT(DISTINCT MD5(payload)) AS n_distinct_payloads,
       SUM(CASE WHEN payload = tag THEN 1 ELSE 0 END) AS n_aliased
  FROM {t};

DROP TABLE {t};
"""
    return "cbrd_26659_oos_rep01_gate_boundary", body


# ---------------------------------------------------------------------------------------------
# case 11 -- OOS-REP-02: which column moves, and how many
# ---------------------------------------------------------------------------------------------

def case_rep02_demotion_order():
    w = "rep02"
    t, tc = "t_cbrd_26659_rep02ord", "t_cbrd_26659_rep02ord_casc"
    unequal = list(d.T18_ORDER_UNEQUAL)
    tie = list(d.T18_ORDER_TIE)
    casc = list(d.T18_ORDER_CASCADE)
    comparator = [900, 800, TAG]
    t18_fixture("oos", unequal, d.T18_SCHEMA_ORDER, f"{w} unequal")
    t18_fixture("oos", tie, d.T18_SCHEMA_ORDER, f"{w} tie")
    t18_fixture("inline", comparator, d.T18_SCHEMA_ORDER, f"{w} comparator")
    t18_fixture("oos", casc, d.T18_SCHEMA_CASCADE, f"{w} cascade")

    extra = f""" *
 * Why the sizes are what they are.  Row 2's two candidates differ by {unequal[0] - unequal[1]} B, so the payload
 * sum a paired SHOW HEAP OOS reports is {d.varbit(unequal[0]) + 16} if the larger moved and {d.varbit(unequal[1]) + 16} if the smaller
 * did: the observation can tell largest-first from any other order, which is the whole point of
 * the row.  Row 3's two candidates are the SAME size, and the normative text says only "sort
 * candidates by size descending" -- it does not say what happens to a tie.  So this case asserts
 * that exactly one of them moved and that both values read back exactly, and never which one:
 * the payload sum is the same either way, which is what makes that silence safe.  Row 4 needs
 * two demotions before the record fits, and its third-largest eligible column stays inline --
 * not because it was too small to qualify, but because the loop had already stopped."""
    body = t18_header(
        "OOS-REP-02: eligible values are demoted largest first, one at a time, until the record "
        "fits.",
        "OOS-REP-02 (largest-first demotion above the gate)",
        ["a record below both gates keeps all three variable columns inline",
         f"two unequal candidates ({unequal[0]} and {unequal[1]} B): one demotion is enough",
         f"two equal candidates ({tie[0]} B each): exactly one moves, and the case never says "
         f"which",
         f"four variable columns ({casc[0]}, {casc[1]}, {casc[2]} and {TAG} B): two must move, "
         f"and the\n *      third-largest stays inline"],
        extra, TAG_NEIGHBOUR, 'a', unequal[0])
    body += f"""
DROP TABLE IF EXISTS {tc};
DROP TABLE IF EXISTS {t};

CREATE TABLE {t} (id INT PRIMARY KEY, big1 BIT VARYING, big2 BIT VARYING, tag BIT VARYING);

{evaluate(f'[TEST 1] inline comparator: a {d.record_before(comparator)} B record, below both gates, nothing moved out')}
INSERT INTO {t} VALUES (1, {val('1', comparator[0])}, {val('2', comparator[1])}, {val('3', TAG)});
{col_checks([('big1', 'big1', val('1', comparator[0])), ('big2', 'big2', val('2', comparator[1])),
             ('tag', 'tag', val('3', TAG))], t, 'id = 1')}

{evaluate(f'[TEST 2] two unequal candidates in a {d.record_before(unequal)} B record: the larger alone is enough')}
INSERT INTO {t} VALUES (2, {val('a', unequal[0])}, {val('b', unequal[1])}, {val('c', TAG)});
{col_checks([('big1', 'big1', val('a', unequal[0])), ('big2', 'big2', val('b', unequal[1])),
             ('tag', 'tag', val('c', TAG))], t, 'id = 2')}

{evaluate(f'[TEST 3] two equal candidates in a {d.record_before(tie)} B record: one moves, and this case never says which')}
INSERT INTO {t} VALUES (3, {val('d', tie[0])}, {val('e', tie[1])}, {val('f', TAG)});
{col_checks([('big1', 'big1', val('d', tie[0])), ('big2', 'big2', val('e', tie[1])),
             ('tag', 'tag', val('f', TAG))], t, 'id = 3')}

{evaluate('[TEST 4] the two equal values are still distinguishable from each other')}
SELECT COUNT(*) AS n_rows,
       SUM(CASE WHEN big1 = big2 THEN 1 ELSE 0 END) AS n_aliased,
       SUM(CASE WHEN OCTET_LENGTH(big1) = OCTET_LENGTH(big2) THEN 1 ELSE 0 END) AS n_same_length
  FROM {t} WHERE id = 3;

{evaluate(f'[TEST 5] four variable columns, a {d.record_before(casc)} B record: two must move, the third-largest stays')}
CREATE TABLE {tc} (id INT PRIMARY KEY, big1 BIT VARYING, big2 BIT VARYING,
                   big3 BIT VARYING, tag BIT VARYING);
INSERT INTO {tc} VALUES (1, {val('6', casc[0])}, {val('7', casc[1])}, {val('8', casc[2])}, {val('9', TAG)});
{col_checks([('big1', 'big1', val('6', casc[0])), ('big2', 'big2', val('7', casc[1])),
             ('big3', 'big3', val('8', casc[2])), ('tag', 'tag', val('9', TAG))], tc, 'id = 1')}

{evaluate('[TEST 6] every row still holds its own values, with no cross-row bleed')}
SELECT COUNT(*) AS n_rows,
       COUNT(DISTINCT MD5(big1)) AS n_distinct_big1,
       SUM(CASE WHEN big1 = tag OR big2 = tag THEN 1 ELSE 0 END) AS n_aliased
  FROM {t};

DROP TABLE {tc};
DROP TABLE {t};
"""
    return "cbrd_26659_oos_rep02_demotion_order", body



# ---------------------------------------------------------------------------------------------
# case 12 -- OOS-REP-04: the eligibility floor, with the largest-first loop out of candidates
# ---------------------------------------------------------------------------------------------

def case_rep04_eligibility_floor():
    w = "rep04"
    t, tcmp = "t_cbrd_26659_rep04", "t_cbrd_26659_rep04_cmp"
    F, Fc = d.T18_FLOOR_FILLER, d.T18_FLOOR_COMPARATOR_FILLER
    pay = d.T18_FLOOR_PAYLOAD
    below, band, above = d.T18_FLOOR_BELOW, d.T18_FLOOR_BAND, d.T18_FLOOR_ABOVE
    t18_fixture("oos-exhausted", [pay, below], d.T18_SCHEMA_FLOOR, f"{w} below", (F,))
    t18_fixture("oos-exhausted", [pay, above], d.T18_SCHEMA_FLOOR, f"{w} above", (F,))
    t18_fixture("disputed", [pay, band], d.T18_SCHEMA_FLOOR, f"{w} band", (F,))
    t18_fixture("inline", [500, below], d.T18_SCHEMA_FLOOR, f"{w} comparator", (Fc,))
    after = d.demoted_under([pay, below], "pinned", (F,))[1]
    gate = d.ob.gate_pinned(d.PAGE_SIZE)

    extra = f""" *
 * Why a {F} B fixed column.  A value stays inline for two quite different reasons -- because it
 * is below the eligibility floor, or because the largest-first loop had already brought the
 * record under the gate and stopped -- and a fixture cannot tell them apart while the loop
 * stops.  The fixed BIT({8 * F}) filler here leaves the record at {after} B after `payload` has
 * moved out, still above the {gate} B gate, so the loop runs until its candidates are exhausted.
 * Anything left inline after that is left inline because it was never a candidate.
 *
 * The three small values.  {below} B serializes to {d.varbit(below)} B, at or below the pinned {d.ob.OR_OOS_INLINE_SIZE_PINNED} B floor and below
 * the normative {d.ob.OR_OOS_INLINE_SIZE_NORMATIVE} B one, so neither accounting makes it a candidate.  {above} B serializes to
 * {d.varbit(above)} B, above both, so both make it one.  {band} B serializes to {d.varbit(band)} B, which the pinned floor
 * demotes and the normative floor does not -- the band, carried here for its values only, which
 * are the same whichever way the engine placed them."""
    body = t18_header(
        "OOS-REP-04: a value at or below the eligibility floor is never demoted, even while the "
        "record is\n * still above the gate and the demotion loop is still looking for "
        "candidates.",
        "OOS-REP-04 (eligibility floor where pinned and normative agree), OOS-REP-02 (the loop "
        "stops\n * when candidates are exhausted)",
        [f"a record below both gates keeps everything inline",
         f"a {below} B value stays inline with the record still {after} B, above the gate",
         f"a {above} B value is a candidate under both accountings",
         f"a {band} B value, inside the floor band: values only"],
        extra,
        f"`small` is {below} to {above} B, which is the boundary this case is about, so the usual "
        "note\n * about an eligible neighbour left inline does not apply to it: the filler, not "
        "the loop,\n * is what keeps the record above the gate.",
        'a', pay)
    body += f"""
DROP TABLE IF EXISTS {tcmp};
DROP TABLE IF EXISTS {t};

CREATE TABLE {tcmp} (id INT PRIMARY KEY, filler BIT({8 * Fc}), payload BIT VARYING, small BIT VARYING);
CREATE TABLE {t} (id INT PRIMARY KEY, filler BIT({8 * F}), payload BIT VARYING, small BIT VARYING);

{evaluate(f'[TEST 1] inline comparator: a {d.record_before([500, below], (Fc,))} B record, below both gates, nothing moved out')}
INSERT INTO {tcmp} VALUES (1, {fixedbit('1', Fc)}, {val('2', 500)}, {val('3', below)});
{col_checks([('filler', 'filler', fixedbit('1', Fc)), ('payload', 'payload', val('2', 500)),
             ('small', 'small', val('3', below))], tcmp, 'id = 1')}

{evaluate(f'[TEST 2] a {below} B value stays inline although the record is still above the gate after `payload` moved')}
INSERT INTO {t} VALUES (1, {fixedbit('a', F)}, {val('b', pay)}, {val('c', below)});
{col_checks([('filler', 'filler', fixedbit('a', F)), ('payload', 'payload', val('b', pay)),
             ('small', 'small', val('c', below))], t, 'id = 1')}

{evaluate(f'[TEST 3] a {above} B value is a demotion candidate under both accountings')}
INSERT INTO {t} VALUES (2, {fixedbit('d', F)}, {val('e', pay)}, {val('f', above)});
{col_checks([('filler', 'filler', fixedbit('d', F)), ('payload', 'payload', val('e', pay)),
             ('small', 'small', val('f', above))], t, 'id = 2')}

{evaluate(f'[TEST 4] a {band} B value, inside the band the two floors disagree about: values only')}
INSERT INTO {t} VALUES (3, {fixedbit('8', F)}, {val('9', pay)}, {val('7', band)});
{col_checks([('filler', 'filler', fixedbit('8', F)), ('payload', 'payload', val('9', pay)),
             ('small', 'small', val('7', band))], t, 'id = 3')}

{evaluate('[TEST 5] every row still holds its own values, with no cross-row bleed')}
SELECT COUNT(*) AS n_rows,
       COUNT(DISTINCT MD5(payload)) AS n_distinct_payloads,
       COUNT(DISTINCT MD5(small)) AS n_distinct_smalls,
       COUNT(DISTINCT OCTET_LENGTH(small)) AS n_distinct_small_lengths,
       SUM(CASE WHEN OCTET_LENGTH(filler) = {F} THEN 1 ELSE 0 END) AS n_filler_exact
  FROM {t};

DROP TABLE {t};
DROP TABLE {tcmp};
"""
    return "cbrd_26659_oos_rep04_eligibility_floor", body


# ---------------------------------------------------------------------------------------------
# case 13 -- OOS-REP-07: the single-chunk to multi-chunk boundary
# ---------------------------------------------------------------------------------------------

def case_rep07_chunk_boundary():
    w = "rep07"
    t = "t_cbrd_26659_rep07"
    one, two, three = d.T18_CHUNK_ONE_BOTH, d.T18_CHUNK_TWO_BOTH, d.T18_CHUNK_THREE_BOTH
    cmp_ = t18_inline(d.T18_TRANSITION_INLINE, w)
    for n in (one, two, three):
        t18_oos(n, f"{w} {n}")
    cap_p = d.ob.max_chunk_payload(d.PAGE_SIZE, d.ob.OOS_RECORD_HEADER_SIZE_PINNED)
    cap_n = d.ob.max_chunk_payload(d.PAGE_SIZE, d.ob.OOS_RECORD_HEADER_SIZE_NORMATIVE)

    extra = f""" *
 * Where the boundary is, and why these two values.  A chunk record holds
 * ALIGN_BELOW(spage_max_record_size, 8) minus one chunk header, which is {cap_p} B at the pinned
 * {d.ob.OOS_RECORD_HEADER_SIZE_PINNED}-byte header and {cap_n} B at the {d.ob.OOS_RECORD_HEADER_SIZE_NORMATIVE}-byte header of the accepted identity layout.  The
 * boundary therefore moves with the header, and the eight logical bytes between the two
 * positions are a range no case may claim a chunk count for.  {one} B is one chunk under both
 * headers and {two} B is two under both, which makes them the sharpest pair this campaign may
 * assert, and {three} B is three under both.  The counts themselves are not visible from SQL and are
 * not in this answer -- they are what the paired SHOW HEAP OOS check asserts.
 *
 * Two clauses of OOS-REP-07 are NOT claimed here and are recorded as gaps of their own: that
 * the chunks are "inserted tail first", which neither the SQL nor the shell seam can observe,
 * and that "total_data_length excludes every chunk header", which depends on the 24-byte
 * identity layout that is absent at this engine revision."""
    body = t18_header(
        "OOS-REP-07: a value larger than one chunk is stored as a chain and reads back complete "
        "and\n * byte-identical.",
        "OOS-REP-07 (multi-chunk value chains). Not OOS-REP-02: every row here has a single\n * candidate, so there is no demotion order to observe",
        [f"an inline comparator of {cmp_} B, below both gates",
         f"{one} B: the largest value that is a single chunk under both chunk headers",
         f"{two} B: the smallest value that needs two chunks under both",
         f"{three} B: three chunks under both, so the chain is followed more than once",
         "every value reads back byte-identical, whatever its chunk count"],
        extra, TAG_NEIGHBOUR, 'a', one)
    body += f"""
DROP TABLE IF EXISTS {t};

CREATE TABLE {t} (id INT PRIMARY KEY, payload BIT VARYING, tag BIT VARYING);

{evaluate(f'[TEST 1] inline comparator: {cmp_} B payload, below both gates, nothing moved out')}
INSERT INTO {t} VALUES (1, {val('1', cmp_)}, {val('2', TAG)});
{select_row(t, 1, val('1', cmp_), val('2', TAG))}

{evaluate(f'[TEST 2] {one} B: one chunk under both chunk headers')}
INSERT INTO {t} VALUES (2, {val('a', one)}, {val('b', TAG)});
{select_row(t, 2, val('a', one), val('b', TAG))}

{evaluate(f'[TEST 3] {two} B: two chunks under both chunk headers')}
INSERT INTO {t} VALUES (3, {val('c', two)}, {val('d', TAG)});
{select_row(t, 3, val('c', two), val('d', TAG))}

{evaluate(f'[TEST 4] {three} B: three chunks under both chunk headers')}
INSERT INTO {t} VALUES (4, {val('e', three)}, {val('f', TAG)});
{select_row(t, 4, val('e', three), val('f', TAG))}

{evaluate('[TEST 5] every chain reads back whole, and no two rows share a value')}
SELECT COUNT(*) AS n_rows,
       COUNT(DISTINCT MD5(payload)) AS n_distinct_payloads,
       SUM(OCTET_LENGTH(payload)) AS payload_octets_total,
       MIN(OCTET_LENGTH(payload)) AS payload_octets_min,
       MAX(OCTET_LENGTH(payload)) AS payload_octets_max,
       SUM(CASE WHEN payload = tag THEN 1 ELSE 0 END) AS n_aliased
  FROM {t};

{evaluate('[TEST 6] a multi-chunk value survives being read through a predicate on itself')}
SELECT id, OCTET_LENGTH(payload) AS payload_octets, MD5(payload) AS payload_md5
  FROM {t} WHERE payload = {val('e', three)};

DROP TABLE {t};
"""
    return "cbrd_26659_oos_rep07_chunk_boundary", body


# ---------------------------------------------------------------------------------------------
# case 14 -- OOS-REP-08: the OOS + bigone rejection and its two neighbours that must succeed
# ---------------------------------------------------------------------------------------------

def case_rep08_bigone_rejection():
    w = "rep08"
    tcmp = "t_cbrd_26659_rep08_cmp"
    tok = "t_cbrd_26659_rep08_ok"
    trej = "t_cbrd_26659_rep08_rej"
    tbig = "t_cbrd_26659_rep08_big"
    v = d.T18_BIGONE_VARBIT
    Fok, Frej = d.T18_BIGONE_ACCEPTED, d.T18_BIGONE_REJECTED
    Fc, Fbig, small = d.T18_BIGONE_COMPARATOR_FILLER, d.T18_NONOOS_FILLER, d.T18_NONOOS_SMALL
    t18_fixture("oos-exhausted", [v], d.T18_SCHEMA_BIGONE, f"{w} accepted", (Fok,))
    t18_fixture("inline", [v], d.T18_SCHEMA_BIGONE, f"{w} comparator", (Fc,))
    t18_fixture("inline", [small], ["s"], f"{w} non-oos bigone", (Fbig,))
    maxslot = d.ob.heap_maxslotted_reclength(d.PAGE_SIZE)
    after_ok = d.demoted_under([v], "pinned", (Fok,))[1]
    after_rej = d.demoted_under([v], "pinned", (Frej,))[1]
    after_big = d.demoted_under([small], "pinned", (Fbig,))[1]

    extra = f""" *
 * The threshold.  A record longer than heap_Maxslotted_reclength, {maxslot} B at a 16 KiB page,
 * cannot live in one slotted page and becomes a multipage REC_BIGONE.  That is fine on its own,
 * and it is fine for a record to carry OOS stubs -- but not both at once, so a record that still
 * exceeds {maxslot} B after every eligible value has been demoted is rejected outright, before
 * any chunk is written.  With a BIT({8 * Fok}) filler the demoted record measures {after_ok} B and is
 * accepted; one filler of BIT({8 * Frej}) makes it {after_rej} B and it is refused.  Eight bytes of
 * filler between those two are where the 24-byte stub of the accepted identity layout would
 * refuse and this engine revision accepts, and no row of this case enters that range.
 *
 * The two neighbours that must succeed are the point of the case as much as the rejection is.
 * One is the accepted record above: OOS-backed, above the gate, below the threshold.  The other
 * carries a BIT({8 * Fbig}) filler and a {small} B variable value, {d.varbit(small)} B serialized and so below both
 * eligibility floors: nothing is demoted, the record is {after_big} B, and it becomes an ordinary
 * REC_BIGONE with no OOS file at all.  A rejection that also refused that record would be a
 * defect, not a guard."""
    body = t18_header(
        "OOS-REP-08: a record that would still be too long after demotion is rejected before any "
        "chunk is\n * written, and the two records either side of it succeed.",
        "OOS-REP-08 (OOS + bigone rejection)",
        [f"an inline comparator: a BIT({8 * Fc}) filler and a {v} B value, below both gates",
         f"a BIT({8 * Fok}) filler: OOS-backed, accepted, {after_ok} B after demotion",
         f"a BIT({8 * Frej}) filler: rejected with Error:-1382, and NO ROW STORED",
         f"a BIT({8 * Fbig}) filler with a {small} B value: no OOS, an ordinary REC_BIGONE, accepted"],
        extra,
        "`v` is the only variable column of the rejection schema, so nothing here rests on one "
        "column\n * being left inline while another moves; the fixed filler is what drives every "
        "boundary.",
        'a', v)
    body += f"""
DROP TABLE IF EXISTS {tbig};
DROP TABLE IF EXISTS {trej};
DROP TABLE IF EXISTS {tok};
DROP TABLE IF EXISTS {tcmp};

CREATE TABLE {tcmp} (id INT PRIMARY KEY, filler BIT({8 * Fc}), v BIT VARYING);
CREATE TABLE {tok} (id INT PRIMARY KEY, filler BIT({8 * Fok}), v BIT VARYING);
CREATE TABLE {trej} (id INT PRIMARY KEY, filler BIT({8 * Frej}), v BIT VARYING);
CREATE TABLE {tbig} (id INT PRIMARY KEY, filler BIT({8 * Fbig}), s BIT VARYING);

{evaluate(f'[TEST 1] inline comparator: a {d.record_before([v], (Fc,))} B record, below both gates')}
INSERT INTO {tcmp} VALUES (1, {fixedbit('1', Fc)}, {val('2', v)});
{col_checks([('filler', 'filler', fixedbit('1', Fc)), ('v', 'v', val('2', v))], tcmp, 'id = 1')}

{evaluate(f'[TEST 2] accepted: OOS-backed and {after_ok} B after demotion, just under the {maxslot} B threshold')}
INSERT INTO {tok} VALUES (1, {fixedbit('a', Fok)}, {val('b', v)});
{col_checks([('filler', 'filler', fixedbit('a', Fok)), ('v', 'v', val('b', v))], tok, 'id = 1')}

{evaluate('[TEST 3] rejected: expect Error:-1382 (ER_HEAP_OOS_OVERPASS_MAXOBJ_SIZE)')}
INSERT INTO {trej} VALUES (1, {fixedbit('c', Frej)}, {val('d', v)});

{evaluate('[TEST 4] and NO ROW is stored by the rejected statement')}
SELECT COUNT(*) AS n_rows FROM {trej};

{evaluate(f'[TEST 5] a non-OOS record above the same threshold is an ordinary REC_BIGONE and succeeds')}
INSERT INTO {tbig} VALUES (1, {fixedbit('e', Fbig)}, {val('f', small)});
{col_checks([('filler', 'filler', fixedbit('e', Fbig)), ('s', 's', val('f', small))], tbig, 'id = 1')}

{evaluate('[TEST 6] the accepted rows are still exactly what was inserted, and the rejected table is empty')}
SELECT COUNT(*) AS n_comparator FROM {tcmp};
SELECT COUNT(*) AS n_accepted FROM {tok};
SELECT COUNT(*) AS n_rejected FROM {trej};
SELECT COUNT(*) AS n_bigone FROM {tbig};

DROP TABLE {tbig};
DROP TABLE {trej};
DROP TABLE {tok};
DROP TABLE {tcmp};
"""
    return "cbrd_26659_oos_rep08_bigone_rejection", body

# ---------------------------------------------------------------------------------------------
# case 15 -- OOS-REP-09: NULL and zero-length values in eligible columns
# ---------------------------------------------------------------------------------------------

def case_rep09_null_empty():
    w = "rep09"
    t = "t_cbrd_26659_rep09"
    oos_, inl = d.T18_TRANSITION_OOS, d.T18_TRANSITION_INLINE
    t18_fixture("oos", [oos_, None, 0, TAG], d.T18_SCHEMA_NULLS, f"{w} oos")
    t18_fixture("inline", [inl, None, 0, TAG], d.T18_SCHEMA_NULLS, f"{w} comparator")

    extra = f""" *
 * NULL and empty are not the same thing, and the difference matters to eligibility.  A NULL
 * variable value occupies no payload bytes at all, so it can never be a demotion candidate.  A
 * zero-length value still carries its one-byte length prefix, ALIGN(1, 4) = {d.varbit(0)} B serialized,
 * which is below both eligibility floors and so cannot be one either.  Both therefore stay
 * inline while their {oos_} B neighbour moves out, and both read back as themselves: NULL as
 * NULL, and the empty value as a value of zero bytes that is not NULL.
 *
 * The UPDATE group matters because a column that becomes NULL after having held an OOS-backed
 * value is the case where an implementation could plausibly leave a stub behind pointing at a
 * chain it no longer owns.  What this seam can say is that the column reads back NULL and then,
 * once reassigned, reads back the new value exactly."""
    body = t18_header(
        "OOS-REP-09: a NULL or zero-length value in an OOS-eligible column is never demoted and "
        "reads back\n * as itself.",
        "OOS-REP-09 (NULL and empty eligible values). Not OOS-REP-02: the claim here is which\n * values are candidates, not the order the candidates are taken in",
        [f"an inline comparator carrying the same NULL and empty columns",
         f"a NULL and a zero-length value beside a {oos_} B value that is demoted",
         "NULL reads back NULL, not an empty value, and the empty value reads back not-NULL",
         "an OOS-backed column set to NULL and then reassigned reads back exactly"],
        extra, TAG_NEIGHBOUR, 'a', oos_)
    nulls = [('payload', 'payload', None), ('nullable', 'nullable', None),
             ('empty', 'empty', None), ('tag', 'tag', None)]
    del nulls
    body += f"""
DROP TABLE IF EXISTS {t};

CREATE TABLE {t} (id INT PRIMARY KEY, payload BIT VARYING, nullable BIT VARYING,
                  empty BIT VARYING, tag BIT VARYING);

{evaluate(f'[TEST 1] inline comparator: a {d.record_before([inl, None, 0, TAG])} B record, below both gates')}
INSERT INTO {t} VALUES (1, {val('1', inl)}, NULL, CAST('' AS BIT VARYING), {val('2', TAG)});
{col_checks([('payload', 'payload', val('1', inl)), ('tag', 'tag', val('2', TAG))], t, 'id = 1')}

{evaluate(f'[TEST 2] a {oos_} B value is demoted beside a NULL and a zero-length column')}
INSERT INTO {t} VALUES (2, {val('a', oos_)}, NULL, CAST('' AS BIT VARYING), {val('b', TAG)});
{col_checks([('payload', 'payload', val('a', oos_)), ('tag', 'tag', val('b', TAG))], t, 'id = 2')}

{evaluate('[TEST 3] NULL reads back NULL and the empty value reads back as zero bytes, not NULL')}
SELECT id,
       nullable IS NULL                    AS nullable_is_null,
       empty IS NULL                       AS empty_is_null,
       OCTET_LENGTH(empty)                 AS empty_octets,
       empty = CAST('' AS BIT VARYING)     AS empty_ok,
       OCTET_LENGTH(nullable)              AS nullable_octets
  FROM {t} ORDER BY id;

{evaluate('[TEST 4] the OOS-backed column set to NULL: it reads back NULL and its neighbours are untouched')}
UPDATE {t} SET payload = NULL WHERE id = 2;
SELECT id,
       payload IS NULL                     AS payload_is_null,
       tag = {val('b', TAG)}               AS tag_ok,
       nullable IS NULL                    AS nullable_is_null,
       OCTET_LENGTH(empty)                 AS empty_octets
  FROM {t} WHERE id = 2;

{evaluate(f'[TEST 5] and reassigning a {oos_} B value to it reads back exactly')}
UPDATE {t} SET payload = {val('c', oos_)} WHERE id = 2;
{col_checks([('payload', 'payload', val('c', oos_)), ('tag', 'tag', val('b', TAG))], t, 'id = 2')}

{evaluate('[TEST 6] the empty column set to NULL and back to empty')}
UPDATE {t} SET empty = NULL WHERE id = 1;
SELECT id, empty IS NULL AS empty_is_null FROM {t} WHERE id = 1;
UPDATE {t} SET empty = CAST('' AS BIT VARYING) WHERE id = 1;
SELECT id, empty IS NULL AS empty_is_null, OCTET_LENGTH(empty) AS empty_octets
  FROM {t} WHERE id = 1;

DROP TABLE {t};
"""
    return "cbrd_26659_oos_rep09_null_empty", body


# ---------------------------------------------------------------------------------------------
# case 16 -- OOS-REP-10: ten or more demoted attributes in one record
# ---------------------------------------------------------------------------------------------

def case_rep10_many_stubs():
    w = "rep10"
    t = "t_cbrd_26659_rep10"
    sizes = list(d.T18_WIDE_SIZES)
    names = list(d.T18_SCHEMA_WIDE)
    small = d.T18_WIDE_COMPARATOR
    t18_fixture("oos", sizes, names, f"{w} wide")
    t18_fixture("inline", [small] * len(names), names, f"{w} comparator")
    demoted = d.demoted_under(sizes, "pinned")[0]
    n_demoted = len(demoted)
    chars = [d.HEX_ALPHABET[i % len(d.HEX_ALPHABET)] for i in range(len(names))]
    cmp_chars = [d.HEX_ALPHABET[(i + 3) % len(d.HEX_ALPHABET)] for i in range(len(names))]

    extra = f""" *
 * Why {len(names)} columns and why these sizes.  The demotion loop stops as soon as the record fits, so
 * making a record carry ten or more stubs means making it need ten or more demotions: {len(names)} columns
 * of {sizes[0]} down to {sizes[-1]} B, each {d.T18_WIDE_STEP} B smaller than the last, leave a {d.record_before(sizes)} B record that is still
 * above the gate after {n_demoted - 1} of them have moved and under it after {n_demoted}.  The sizes are all
 * DIFFERENT, so largest-first is a total order with no tie in it, and the payload sum a paired
 * SHOW HEAP OOS reports identifies WHICH {n_demoted} moved rather than only how many.  The {len(names) - n_demoted} columns
 * left inline are all far above both eligibility floors: they stayed because the loop stopped.
 *
 * Each column is checked on its own line rather than as one wide row of {3 * len(names)} scalars, so a
 * difference names the column it is in."""
    body = t18_header(
        f"OOS-REP-10: one record carrying {n_demoted} demoted attributes reads back with every value "
        "exact.",
        "OOS-REP-10 (many OOS-backed attributes in one record), OOS-REP-02 (largest-first)",
        [f"an inline comparator with all {len(names)} columns at {small} B, below both gates",
         f"one record of {len(names)} columns, {sizes[0]} down to {sizes[-1]} B, needing {n_demoted} demotions",
         f"all {len(names)} values read back byte-identical",
         f"all {len(names)} values are distinct from one another, so no column borrowed another's value"],
        extra,
        f"the {len(names) - n_demoted} smallest columns are {sizes[n_demoted]} down to {sizes[-1]} B: far above both "
        "eligibility floors\n * (16 B pinned, 24 B normative), so they stay inline because the "
        "largest-first loop already\n * stopped, not because they were too small to qualify.",
        'a', sizes[0])
    cols = ",\n                  ".join(f"{n} BIT VARYING" for n in names)
    wide_values = ",\n          ".join(val(c, n) for c, n in zip(chars, sizes))
    cmp_values = ",\n          ".join(val(c, small) for c in cmp_chars)
    body += f"""
DROP TABLE IF EXISTS {t};

CREATE TABLE {t} (id INT PRIMARY KEY,
                  {cols});

{evaluate(f'[TEST 1] inline comparator: all {len(names)} columns at {small} B, a {d.record_before([small] * len(names))} B record')}
INSERT INTO {t} VALUES (1,
          {cmp_values});
{col_checks([(n, n, val(c, small)) for n, c in zip(names, cmp_chars)], t, 'id = 1')}

{evaluate(f'[TEST 2] one record of {len(names)} columns, {sizes[0]} down to {sizes[-1]} B: a {d.record_before(sizes)} B record needing {n_demoted} demotions')}
INSERT INTO {t} VALUES (2,
          {wide_values});
{col_checks([(n, n, val(c, s)) for n, c, s in zip(names, chars, sizes)], t, 'id = 2')}

{evaluate(f'[TEST 3] all {len(names)} values of the wide record are distinct from one another')}
SELECT COUNT(DISTINCT digest) AS n_distinct_digests, COUNT(*) AS n_columns
  FROM ({chr(10).join('  ' + ('SELECT' if i == 0 else 'UNION ALL SELECT') + f' MD5({n}) AS digest FROM {t} WHERE id = 2' for i, n in enumerate(names))}) x;

{evaluate('[TEST 4] the two rows do not share a value in any column')}
SELECT COUNT(*) AS n_rows,
       SUM(CASE WHEN {names[0]} = {names[1]} THEN 1 ELSE 0 END) AS n_aliased_first_pair,
       SUM(CASE WHEN {names[-2]} = {names[-1]} THEN 1 ELSE 0 END) AS n_aliased_last_pair,
       SUM(OCTET_LENGTH({names[0]})) AS first_octets_total,
       SUM(OCTET_LENGTH({names[-1]})) AS last_octets_total
  FROM {t};

DROP TABLE {t};
"""
    return "cbrd_26659_oos_rep10_many_stubs", body

# ---------------------------------------------------------------------------------------------
# case 17 -- OOS-REP-11 / OOS-REP-01: inline and OOS transitions, and the VOT width across them
# ---------------------------------------------------------------------------------------------

def case_rep11_transitions():
    w = "rep11"
    t, tv = "t_cbrd_26659_rep11", "t_cbrd_26659_rep11_vot"
    inl, oos_ = d.T18_TRANSITION_INLINE, d.T18_TRANSITION_OOS
    narrow_tag = d.T18_VOT_NARROW_TAG
    one_b, two_b = list(d.T18_VOT_ONE_BYTE), list(d.T18_VOT_TWO_BYTE)
    t18_inline(inl, f"{w} inline")
    t18_oos(oos_, f"{w} oos")
    t18_oos(oos_, f"{w} narrow", tag_bytes=narrow_tag)
    t18_fixture("inline", one_b, d.T18_SCHEMA_VOT, f"{w} vot one byte")
    t18_fixture("inline", two_b, d.T18_SCHEMA_VOT, f"{w} vot two bytes")

    extra = f""" *
 * The variable-offset table.  A record's header carries one offset per variable column plus a
 * terminator, and the entries are one byte wide while header plus payload stays at or below
 * OR_MAX_BYTE = 127 and two bytes wide above it.  With two variable columns the table is
 * ALIGN(1 x 3, 4) = 4 B at one-byte entries and ALIGN(2 x 3, 4) = 8 B at two, so the header
 * itself changes across that boundary; with a single variable column both widths round to the
 * same 4 B and nothing moves, which is why this case uses two.  Rows 1 and 2 sit either side of
 * it with {two_b[1] - one_b[1]} B of difference and nothing else changed.
 *
 * Demotion moves the boundary the other way.  A record whose payload is large enough to be
 * demoted necessarily had two-byte entries; once its largest value is replaced by a 16-byte stub
 * the remaining payload can fall back under 127 and the entries narrow to one byte again.  Row 3
 * is that record: a {oos_} B payload beside a {narrow_tag} B neighbour.  The width is not visible from SQL and
 * this case does not claim it; what the case claims is that the values are unaffected by it.
 *
 * An OOS-bearing record never reaches four-byte entries at any supported page size, because
 * such a record must fit heap_Maxslotted_reclength, {d.ob.heap_maxslotted_reclength(d.PAGE_SIZE)} B at 16 KiB, which is below
 * OR_MAX_SHORT = 32767.  That is a structural exclusion, not an untested combination."""
    body = t18_header(
        "OOS-REP-11: an attribute moves between inline and out-of-row as the record crosses the "
        "gate, and\n * the logical value is never affected by the transition.",
        "OOS-REP-11 (inline and OOS transitions across writes), OOS-REP-01 (records below the "
        "gate\n * stay inline)",
        [f"two records either side of the one-byte to two-byte offset-width boundary",
         f"a {oos_} B payload beside a {narrow_tag} B neighbour: two-byte entries before the "
         f"demotion,\n *      one-byte entries after it",
         f"one row taken {inl} B (inline) then {oos_} B (demoted) then {inl} B again, its value "
         f"asserted\n *      at every step",
         "a second transition on the same row, so the sequence is not a one-off"],
        extra, TAG_NEIGHBOUR, 'a', oos_)
    body += f"""
DROP TABLE IF EXISTS {tv};
DROP TABLE IF EXISTS {t};

CREATE TABLE {tv} (id INT PRIMARY KEY, a BIT VARYING, b BIT VARYING);

{evaluate(f'[TEST 1] one-byte offset entries: a {d.record_before(one_b)} B record of {one_b[0]} and {one_b[1]} B')}
INSERT INTO {tv} VALUES (1, {val('1', one_b[0])}, {val('2', one_b[1])});
{col_checks([('a', 'a', val('1', one_b[0])), ('b', 'b', val('2', one_b[1]))], tv, 'id = 1')}

{evaluate(f'[TEST 2] two-byte offset entries: a {d.record_before(two_b)} B record of {two_b[0]} and {two_b[1]} B')}
INSERT INTO {tv} VALUES (2, {val('3', two_b[0])}, {val('4', two_b[1])});
{col_checks([('a', 'a', val('3', two_b[0])), ('b', 'b', val('4', two_b[1]))], tv, 'id = 2')}

CREATE TABLE {t} (id INT PRIMARY KEY, payload BIT VARYING, tag BIT VARYING);

{evaluate(f'[TEST 3] two-byte entries before the demotion and one-byte after it: {oos_} B beside {narrow_tag} B')}
INSERT INTO {t} VALUES (1, {val('a', oos_)}, {val('b', narrow_tag)});
{col_checks([('payload', 'payload', val('a', oos_)), ('tag', 'tag', val('b', narrow_tag))],
            t, 'id = 1')}

{evaluate(f'[TEST 4] a row below both gates: {inl} B payload, nothing moved out')}
INSERT INTO {t} VALUES (2, {val('c', inl)}, {val('d', TAG)});
{select_row(t, 2, val('c', inl), val('d', TAG))}

{evaluate(f'[TEST 5] the same row taken above both gates: {inl} B -> {oos_} B')}
UPDATE {t} SET payload = {val('e', oos_)} WHERE id = 2;
{select_row(t, 2, val('e', oos_), val('d', TAG))}

{evaluate(f'[TEST 6] and back below them: {oos_} B -> {inl} B')}
UPDATE {t} SET payload = {val('f', inl)} WHERE id = 2;
{select_row(t, 2, val('f', inl), val('d', TAG))}

{evaluate(f'[TEST 7] a second crossing on the same row, so the sequence is not a one-off')}
UPDATE {t} SET payload = {val('9', oos_)} WHERE id = 2;
{select_row(t, 2, val('9', oos_), val('d', TAG))}
UPDATE {t} SET payload = {val('8', inl)} WHERE id = 2;
{select_row(t, 2, val('8', inl), val('d', TAG))}

{evaluate('[TEST 8] both rows still hold their own values after four transitions')}
SELECT COUNT(*) AS n_rows,
       COUNT(DISTINCT MD5(payload)) AS n_distinct_payloads,
       SUM(CASE WHEN payload = tag THEN 1 ELSE 0 END) AS n_aliased
  FROM {t};

DROP TABLE {t};
DROP TABLE {tv};
"""
    return "cbrd_26659_oos_rep11_transitions", body


# ---------------------------------------------------------------------------------------------
# case 18 -- OOS-REP-13: the placement hints, observed and asserted nowhere
# ---------------------------------------------------------------------------------------------

def case_rep13_placement_hints():
    w = "rep12"
    tf, tp, td = ("t_cbrd_26659_rep12_force", "t_cbrd_26659_rep12_prefer",
                  "t_cbrd_26659_rep12_alias")
    ta = "t_cbrd_26659_rep12_alter"
    forced, preferred, other = d.T18_HINT_FORCED, d.T18_HINT_PREFERRED, d.T18_HINT_OTHER
    t18_hinted([forced, TAG], f"{w} force_outline")
    t18_hinted([preferred, other, TAG], f"{w} prefer_inline")
    t18_hinted([preferred, other, TAG], f"{w} prefer_outline alias")
    t18_hinted([preferred, other, TAG], f"{w} alter")

    extra = f""" *
 * This case asserts no placement, and it is the only case of this family that could.  STORAGE
 * PREFER_INLINE and STORAGE FORCE_OUTLINE are accepted by the grammar and implemented in the
 * engine, and neither is an accepted design: the normative context lists per-column inline
 * preference as proposed and not merged, and force-outline is not there at all.  Source
 * existence is not acceptance, so where a hinted value is placed is an implementation
 * observation and never a requirement -- recorded, kept visible, and asserted nowhere.  What
 * this case does assert is what is true whatever the policy turns out to be: the values read
 * back exactly, the DDL behaves, and a hint on a column that cannot carry one is refused.
 *
 * STORAGE PREFER_OUTLINE is a third spelling and, at this engine revision, an explicit alias of
 * STORAGE DEFAULT -- the parse tree gives them the same value.  It is here so that a reader who
 * finds four spellings in the grammar sees which three are distinct.
 *
 * Expected error.  A storage hint is accepted only on a variable-length normal attribute, so a
 * hint on an INT column is refused with Error:-495 (ER_PT_EXECUTE).  The refusal itself is
 * written by do_validate_oos_storage_setting, which returns ER_PT_SEMANTIC internally; the code
 * the client sees is the one the execution phase reports for a statement whose parser error list
 * is non-empty after do_statement, which is ER_PT_EXECUTE."""
    body = t18_header(
        "OOS-REP-13: the placement hints are exercised for logical correctness only; where the "
        "engine puts\n * a hinted value is observed and never asserted.",
        "OOS-REP-13 (placement-hint policy authority, BLOCKED: no placement expectation is "
        "fixed)",
        ["STORAGE FORCE_OUTLINE on a small column of a record far below the gate",
         "STORAGE PREFER_INLINE on the largest column of a record above the gate",
         "STORAGE PREFER_OUTLINE, which is an alias of STORAGE DEFAULT at this revision",
         "a hint on a column that is not variable-length is refused with Error:-495",
         "ALTER adding and removing a hint leaves every stored value exact"],
        extra,
        "no eligibility note applies here: the hints are what decide placement in these tables, "
        "and\n * this case makes no claim about it.",
        'a', preferred,
        not_proven=""" *
 * What this case deliberately does NOT prove: anything at all about placement.  Its outcome is
 * BLOCKED, not PASS, because the requirement it cites is an open specification question and a
 * case cannot pass a question.  The engine's placement under each hint is recorded by a paired
 * SHOW HEAP OOS check as an observation.""")
    body += f"""
DROP TABLE IF EXISTS {ta};
DROP TABLE IF EXISTS {td};
DROP TABLE IF EXISTS {tp};
DROP TABLE IF EXISTS {tf};

{evaluate(f'[TEST 1] STORAGE FORCE_OUTLINE on a {forced} B column of a record far below the gate')}
CREATE TABLE {tf} (id INT PRIMARY KEY, hinted BIT VARYING STORAGE FORCE_OUTLINE,
                   tag BIT VARYING);
INSERT INTO {tf} VALUES (1, {val('a', forced)}, {val('b', TAG)});
{col_checks([('hinted', 'hinted', val('a', forced)), ('tag', 'tag', val('b', TAG))], tf, 'id = 1')}

{evaluate(f'[TEST 2] STORAGE PREFER_INLINE on the {preferred} B largest column of a record above the gate')}
CREATE TABLE {tp} (id INT PRIMARY KEY, hinted BIT VARYING STORAGE PREFER_INLINE,
                   other BIT VARYING, tag BIT VARYING);
INSERT INTO {tp} VALUES (1, {val('c', preferred)}, {val('d', other)}, {val('e', TAG)});
{col_checks([('hinted', 'hinted', val('c', preferred)), ('other', 'other', val('d', other)),
             ('tag', 'tag', val('e', TAG))], tp, 'id = 1')}

{evaluate('[TEST 3] STORAGE PREFER_OUTLINE, an alias of STORAGE DEFAULT at this revision')}
CREATE TABLE {td} (id INT PRIMARY KEY, hinted BIT VARYING STORAGE PREFER_OUTLINE,
                   other BIT VARYING, tag BIT VARYING);
INSERT INTO {td} VALUES (1, {val('f', preferred)}, {val('9', other)}, {val('8', TAG)});
{col_checks([('hinted', 'hinted', val('f', preferred)), ('other', 'other', val('9', other)),
             ('tag', 'tag', val('8', TAG))], td, 'id = 1')}

{evaluate('[TEST 4] a hint on a column that is not variable-length: expect Error:-495')}
CREATE TABLE {ta} (id INT PRIMARY KEY, n INT STORAGE FORCE_OUTLINE);

{evaluate('[TEST 5] and the refused statement created no table')}
SELECT COUNT(*) AS n_classes FROM db_class WHERE class_name = '{ta}';

{evaluate('[TEST 6] ALTER adding and then removing a hint leaves every stored value exact')}
CREATE TABLE {ta} (id INT PRIMARY KEY, hinted BIT VARYING, other BIT VARYING, tag BIT VARYING);
INSERT INTO {ta} VALUES (1, {val('7', preferred)}, {val('6', other)}, {val('5', TAG)});
ALTER TABLE {ta} MODIFY hinted BIT VARYING STORAGE FORCE_OUTLINE;
{col_checks([('hinted', 'hinted', val('7', preferred)), ('other', 'other', val('6', other)),
             ('tag', 'tag', val('5', TAG))], ta, 'id = 1')}
ALTER TABLE {ta} MODIFY hinted BIT VARYING STORAGE DEFAULT;
{col_checks([('hinted', 'hinted', val('7', preferred)), ('other', 'other', val('6', other)),
             ('tag', 'tag', val('5', TAG))], ta, 'id = 1')}

{evaluate('[TEST 7] every hinted table still holds exactly one row and its own values')}
SELECT COUNT(*) AS n_rows, COUNT(DISTINCT MD5(hinted)) AS n_distinct FROM {tf};
SELECT COUNT(*) AS n_rows, COUNT(DISTINCT MD5(hinted)) AS n_distinct FROM {tp};
SELECT COUNT(*) AS n_rows, COUNT(DISTINCT MD5(hinted)) AS n_distinct FROM {td};
SELECT COUNT(*) AS n_rows, COUNT(DISTINCT MD5(hinted)) AS n_distinct FROM {ta};

DROP TABLE {ta};
DROP TABLE {td};
DROP TABLE {tp};
DROP TABLE {tf};
"""
    return "cbrd_26659_oos_rep13_placement_hints", body


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


# ---------------------------------------------------------------------------------------------
# ticket 18 activation specs -- one table per phase, so a count is never a running total
# ---------------------------------------------------------------------------------------------

SPEC_HEADER_T18 = """\
# CBRD-26659 ticket 18 activation spec for {case}.
# Generated with the case itself; run by tools/activation_check_spec.sh, client-server, under
# campaign_ns.sh (user decision O2, ticket 35).  PHASE <tag> <table> <has_oos> <num_recs>
# <sumlen>; `-` observes instead of asserting.  Every asserted figure is derived, never
# measured.  Every phase owns its own table, so a chunk count is that phase's own and not a
# running total over the ones before it.
#
# Where a figure is observed rather than asserted, the line above it says what the accepted
# design would require and what the pinned engine is known to do.  Observation is what the
# authority policy requires of a quantity whose value is not settled at this revision; it is
# not leniency, and the difference between the two is the campaign's finding, not its oracle.
"""


def _spec_table(name, cols="id INT PRIMARY KEY, payload BIT VARYING, tag BIT VARYING"):
    return f"DROP TABLE IF EXISTS {name};\nCREATE TABLE {name} ({cols});"


def spec_rep01_gate_boundary():
    case = "cbrd_26659_oos_rep01_gate_boundary"
    p = "t_cbrd_26659_rep01_chk"
    inl, oos_ = d.T18_GATE_INLINE_BOTH, d.T18_GATE_OOS_BOTH
    lo, hi = d.T18_GATE_BAND_LO, d.T18_GATE_BAND_HI
    gp, gn = d.ob.gate_pinned(d.PAGE_SIZE), d.ob.target_normative(d.PAGE_SIZE)
    return case, f"""{SPEC_HEADER_T18.format(case=case)}
PHASE inline {p}_inline 0 0 0
{_spec_table(f'{p}_inline')}
INSERT INTO {p}_inline VALUES (1, {val('a', inl)}, {val('b', TAG)});
PHASE oosbacked {p}_oos 1 1 {sumlen(oos_)}
{_spec_table(f'{p}_oos')}
INSERT INTO {p}_oos VALUES (1, {val('c', oos_)}, {val('d', TAG)});
# The two band rows.  The four-record physical target accepted in CBRD-27057 puts the gate at
# {gn} B and would demote both of these; the pinned engine compares against DB_PAGESIZE/4 = {gp} B
# and keeps them inline, which is the conformance gap OOS-REP-03 records.  The pinned engine's
# answer must not become the expectation, and the accepted design's must not be asserted at an
# engine that does not implement it, so both are OBSERVED.  Expected under the accepted target:
# Has_oos_file 1, Oos_num_recs 1, Oos_recs_sumlen {sumlen(lo)} and {sumlen(hi)} respectively.
PHASE band_low {p}_band_lo - - -
{_spec_table(f'{p}_band_lo')}
INSERT INTO {p}_band_lo VALUES (1, {val('e', lo)}, {val('f', TAG)});
PHASE band_high {p}_band_hi - - -
{_spec_table(f'{p}_band_hi')}
INSERT INTO {p}_band_hi VALUES (1, {val('9', hi)}, {val('8', TAG)});
"""


def spec_rep02_demotion_order():
    case = "cbrd_26659_oos_rep02_demotion_order"
    p = "t_cbrd_26659_rep02ord_chk"
    unequal, tie, casc = (list(d.T18_ORDER_UNEQUAL), list(d.T18_ORDER_TIE),
                          list(d.T18_ORDER_CASCADE))
    three = "id INT PRIMARY KEY, big1 BIT VARYING, big2 BIT VARYING, tag BIT VARYING"
    four = ("id INT PRIMARY KEY, big1 BIT VARYING, big2 BIT VARYING, big3 BIT VARYING, "
            "tag BIT VARYING")
    return case, f"""{SPEC_HEADER_T18.format(case=case)}
PHASE comparator {p}_cmp 0 0 0
{_spec_table(f'{p}_cmp', three)}
INSERT INTO {p}_cmp VALUES (1, {val('1', 900)}, {val('2', 800)}, {val('3', TAG)});
# The payload sum is what makes this a largest-first observation rather than a count: {sumlen(unequal[0])} is
# `big1` moved and {sumlen(unequal[1])} would be `big2`, so an engine that demoted the smaller candidate
# would fail here even though both produce one chunk.
PHASE unequal {p}_uneq 1 1 {sumlen(unequal[0])}
{_spec_table(f'{p}_uneq', three)}
INSERT INTO {p}_uneq VALUES (1, {val('a', unequal[0])}, {val('b', unequal[1])}, {val('c', TAG)});
# The two candidates are the same size, so the payload sum is {sumlen(tie[0])} whichever of them the
# tie-break took.  That is exactly why it may be asserted: it carries the count and the size
# without carrying the tie-break, which the normative text does not fix.
PHASE tie {p}_tie 1 1 {sumlen(tie[0])}
{_spec_table(f'{p}_tie', three)}
INSERT INTO {p}_tie VALUES (1, {val('d', tie[0])}, {val('e', tie[1])}, {val('f', TAG)});
PHASE cascade {p}_casc 1 2 {sumlen(casc[0], casc[1])}
{_spec_table(f'{p}_casc', four)}
INSERT INTO {p}_casc VALUES (1, {val('6', casc[0])}, {val('7', casc[1])}, {val('8', casc[2])}, {val('9', TAG)});
"""


def spec_rep04_eligibility_floor():
    case = "cbrd_26659_oos_rep04_eligibility_floor"
    p = "t_cbrd_26659_rep04_chk"
    F, Fc = d.T18_FLOOR_FILLER, d.T18_FLOOR_COMPARATOR_FILLER
    pay = d.T18_FLOOR_PAYLOAD
    below, band, above = d.T18_FLOOR_BELOW, d.T18_FLOOR_BAND, d.T18_FLOOR_ABOVE
    cols = f"id INT PRIMARY KEY, filler BIT({8 * F}), payload BIT VARYING, small BIT VARYING"
    cols_c = f"id INT PRIMARY KEY, filler BIT({8 * Fc}), payload BIT VARYING, small BIT VARYING"
    return case, f"""{SPEC_HEADER_T18.format(case=case)}
PHASE comparator {p}_cmp 0 0 0
{_spec_table(f'{p}_cmp', cols_c)}
INSERT INTO {p}_cmp VALUES (1, {fixedbit('1', Fc)}, {val('2', 500)}, {val('3', below)});
# One chunk, not two: `payload` moved and the {below} B `small` did not, although the record is still
# above the gate and the loop was still looking.  That is the eligibility floor and nothing else.
PHASE below_floor {p}_below 1 1 {sumlen(pay)}
{_spec_table(f'{p}_below', cols)}
INSERT INTO {p}_below VALUES (1, {fixedbit('a', F)}, {val('b', pay)}, {val('c', below)});
# Two chunks: at {above} B `small` is a candidate under both accountings and the exhausted loop takes it.
PHASE above_floor {p}_above 1 2 {sumlen(pay, above)}
{_spec_table(f'{p}_above', cols)}
INSERT INTO {p}_above VALUES (1, {fixedbit('d', F)}, {val('e', pay)}, {val('f', above)});
# The band.  At {band} B the value serializes to {d.varbit(band)} B: above the pinned {d.ob.OR_OOS_INLINE_SIZE_PINNED}-byte floor and at the
# normative {d.ob.OR_OOS_INLINE_SIZE_NORMATIVE}-byte one, so the pinned engine demotes it and the accepted identity layout of
# CBRD-26950 would not.  Expected under the accepted layout: Oos_num_recs 1, Oos_recs_sumlen
# {sumlen(pay)}.  Observed, never asserted (OOS-REP-05, UNSUPPORTED at this revision).
PHASE floor_band {p}_band - - -
{_spec_table(f'{p}_band', cols)}
INSERT INTO {p}_band VALUES (1, {fixedbit('8', F)}, {val('9', pay)}, {val('7', band)});
"""


def spec_rep07_chunk_boundary():
    case = "cbrd_26659_oos_rep07_chunk_boundary"
    p = "t_cbrd_26659_rep07_chk"
    one, two, three = d.T18_CHUNK_ONE_BOTH, d.T18_CHUNK_TWO_BOTH, d.T18_CHUNK_THREE_BOTH
    cmp_ = d.T18_TRANSITION_INLINE
    return case, f"""{SPEC_HEADER_T18.format(case=case)}
PHASE comparator {p}_cmp 0 0 0
{_spec_table(f'{p}_cmp')}
INSERT INTO {p}_cmp VALUES (1, {val('1', cmp_)}, {val('2', TAG)});
PHASE one_chunk {p}_one 1 1 {sumlen(one)}
{_spec_table(f'{p}_one')}
INSERT INTO {p}_one VALUES (1, {val('a', one)}, {val('b', TAG)});
PHASE two_chunks {p}_two 1 2 {sumlen(two)}
{_spec_table(f'{p}_two')}
INSERT INTO {p}_two VALUES (1, {val('c', two)}, {val('d', TAG)});
PHASE three_chunks {p}_three 1 3 {sumlen(three)}
{_spec_table(f'{p}_three')}
INSERT INTO {p}_three VALUES (1, {val('e', three)}, {val('f', TAG)});
"""


def spec_rep08_bigone_rejection():
    case = "cbrd_26659_oos_rep08_bigone_rejection"
    p = "t_cbrd_26659_rep08_chk"
    v = d.T18_BIGONE_VARBIT
    Fok, Frej = d.T18_BIGONE_ACCEPTED, d.T18_BIGONE_REJECTED
    Fc, Fbig, small = d.T18_BIGONE_COMPARATOR_FILLER, d.T18_NONOOS_FILLER, d.T18_NONOOS_SMALL
    return case, f"""{SPEC_HEADER_T18.format(case=case)}
PHASE comparator {p}_cmp 0 0 0
{_spec_table(f'{p}_cmp', f'id INT PRIMARY KEY, filler BIT({8 * Fc}), v BIT VARYING')}
INSERT INTO {p}_cmp VALUES (1, {fixedbit('1', Fc)}, {val('2', v)});
PHASE accepted {p}_ok 1 1 {sumlen(v)}
{_spec_table(f'{p}_ok', f'id INT PRIMARY KEY, filler BIT({8 * Fok}), v BIT VARYING')}
INSERT INTO {p}_ok VALUES (1, {fixedbit('a', Fok)}, {val('b', v)});
# The rejected INSERT.  OOS-REP-08 says the rejection happens BEFORE any chunk is written, so
# the assertion is that the class still has no OOS file at all -- not merely that the row is
# absent, which the case itself shows.  csql continues past the error, which is what lets the
# SHOW HEAP OOS after it run.
PHASE rejected {p}_rej 0 0 0
{_spec_table(f'{p}_rej', f'id INT PRIMARY KEY, filler BIT({8 * Frej}), v BIT VARYING')}
INSERT INTO {p}_rej VALUES (1, {fixedbit('c', Frej)}, {val('d', v)});
# The non-OOS neighbour: a record above the same threshold whose only variable value is below
# both eligibility floors.  Nothing is demoted, so nothing is rejected and no OOS file exists.
PHASE nonoos_bigone {p}_big 0 0 0
{_spec_table(f'{p}_big', f'id INT PRIMARY KEY, filler BIT({8 * Fbig}), s BIT VARYING')}
INSERT INTO {p}_big VALUES (1, {fixedbit('e', Fbig)}, {val('f', small)});
"""


def spec_rep09_null_empty():
    case = "cbrd_26659_oos_rep09_null_empty"
    p = "t_cbrd_26659_rep09_chk"
    oos_, inl = d.T18_TRANSITION_OOS, d.T18_TRANSITION_INLINE
    cols = ("id INT PRIMARY KEY, payload BIT VARYING, nullable BIT VARYING, "
            "empty BIT VARYING, tag BIT VARYING")
    return case, f"""{SPEC_HEADER_T18.format(case=case)}
PHASE comparator {p}_cmp 0 0 0
{_spec_table(f'{p}_cmp', cols)}
INSERT INTO {p}_cmp VALUES (1, {val('1', inl)}, NULL, CAST('' AS BIT VARYING), {val('2', TAG)});
# One chunk, not three: the NULL column and the zero-length column are not candidates, so only
# `payload` moved.  A count of two or three here would be the finding.
PHASE oosbacked {p}_oos 1 1 {sumlen(oos_)}
{_spec_table(f'{p}_oos', cols)}
INSERT INTO {p}_oos VALUES (1, {val('a', oos_)}, NULL, CAST('' AS BIT VARYING), {val('b', TAG)});
# After the OOS-backed column is set to NULL.  At this revision an UPDATE allocates fresh chains
# and the dead ones stay until vacuum (OOS-SQL-03, observation-only), and when the new value is
# NULL there is no new chain at all -- so what remains here is a background question, not a
# requirement.  Observed.
PHASE updated_to_null {p}_oos - - -
UPDATE {p}_oos SET payload = NULL WHERE id = 1;
"""


def spec_rep10_many_stubs():
    case = "cbrd_26659_oos_rep10_many_stubs"
    p = "t_cbrd_26659_rep10_chk"
    sizes, names = list(d.T18_WIDE_SIZES), list(d.T18_SCHEMA_WIDE)
    small = d.T18_WIDE_COMPARATOR
    chars = [d.HEX_ALPHABET[i % len(d.HEX_ALPHABET)] for i in range(len(names))]
    cmp_chars = [d.HEX_ALPHABET[(i + 3) % len(d.HEX_ALPHABET)] for i in range(len(names))]
    cols = "id INT PRIMARY KEY, " + ", ".join(f"{n} BIT VARYING" for n in names)
    demoted = d.demoted_under(sizes, "pinned")[0]
    return case, f"""{SPEC_HEADER_T18.format(case=case)}
PHASE comparator {p}_cmp 0 0 0
{_spec_table(f'{p}_cmp', cols)}
INSERT INTO {p}_cmp VALUES (1, {', '.join(val(c, small) for c in cmp_chars)});
# {len(demoted)} chunks from one record.  The sizes are all different, so the payload sum names WHICH
# {len(demoted)} of the {len(names)} columns moved and not only how many: a loop that took them in any other
# order would reach a different sum.
PHASE wide {p}_wide 1 {len(demoted)} {sumlen(*[sizes[i] for i in demoted])}
{_spec_table(f'{p}_wide', cols)}
INSERT INTO {p}_wide VALUES (1, {', '.join(val(c, n) for c, n in zip(chars, sizes))});
"""


def spec_rep11_transitions():
    case = "cbrd_26659_oos_rep11_transitions"
    p = "t_cbrd_26659_rep11_chk"
    inl, oos_ = d.T18_TRANSITION_INLINE, d.T18_TRANSITION_OOS
    narrow = d.T18_VOT_NARROW_TAG
    one_b, two_b = list(d.T18_VOT_ONE_BYTE), list(d.T18_VOT_TWO_BYTE)
    vot_cols = "id INT PRIMARY KEY, a BIT VARYING, b BIT VARYING"
    return case, f"""{SPEC_HEADER_T18.format(case=case)}
PHASE vot_inline {p}_vot 0 0 0
{_spec_table(f'{p}_vot', vot_cols)}
INSERT INTO {p}_vot VALUES (1, {val('1', one_b[0])}, {val('2', one_b[1])});
INSERT INTO {p}_vot VALUES (2, {val('3', two_b[0])}, {val('4', two_b[1])});
PHASE vot_narrowed {p}_narrow 1 1 {sumlen(oos_)}
{_spec_table(f'{p}_narrow')}
INSERT INTO {p}_narrow VALUES (1, {val('a', oos_)}, {val('b', narrow)});
PHASE inline_before {p}_trans 0 0 0
{_spec_table(f'{p}_trans')}
INSERT INTO {p}_trans VALUES (1, {val('c', inl)}, {val('d', TAG)});
# Crossing the gate upward really does create a chain: this is the one transition assertion of
# the case, and it is assertable because the row was inline before and both accountings agree
# that {oos_} B is above the gate.
PHASE crossed_up {p}_trans 1 1 {sumlen(oos_)}
UPDATE {p}_trans SET payload = {val('e', oos_)} WHERE id = 1;
# Crossing back down.  The value goes inline again, but at this revision the chain the previous
# UPDATE created is not reclaimed synchronously (OOS-SQL-03, observation-only, superseded on
# paper by CBRD-27230), so the count after this statement is current behaviour and a moving
# target for vacuum.  Observed.
PHASE crossed_down {p}_trans - - -
UPDATE {p}_trans SET payload = {val('f', inl)} WHERE id = 1;
"""


def spec_rep13_placement_hints():
    case = "cbrd_26659_oos_rep13_placement_hints"
    p = "t_cbrd_26659_rep13_chk"
    forced, preferred, other = d.T18_HINT_FORCED, d.T18_HINT_PREFERRED, d.T18_HINT_TAG
    other = d.T18_HINT_OTHER
    return case, f"""{SPEC_HEADER_T18.format(case=case)}
# Every figure in this spec is OBSERVED.  Whether STORAGE PREFER_INLINE ordering and the
# STORAGE FORCE_OUTLINE gate bypass are required behaviour is undecided (OOS-REP-13, BLOCKED),
# so there is no expectation to assert and the engine's answer must not become one.  What the
# observation is for is that a merge reviewer can see what this revision does.
#
# At this revision, from the source: FORCE_OUTLINE demotes any non-NULL variable value larger
# than the inline stub before the record gate is consulted at all, so the {forced} B value below is
# expected to be moved out of a record far under the gate; PREFER_INLINE sinks its column to the
# tail of the candidate list, so the {preferred} B hinted column is expected to stay inline while the
# {other} B one moves; and PREFER_OUTLINE is an alias of DEFAULT in the parse tree, so the third
# table is expected to behave exactly like an unhinted one.
PHASE force_outline {p}_force - - -
DROP TABLE IF EXISTS {p}_force;
CREATE TABLE {p}_force (id INT PRIMARY KEY, hinted BIT VARYING STORAGE FORCE_OUTLINE, tag BIT VARYING);
INSERT INTO {p}_force VALUES (1, {val('a', forced)}, {val('b', TAG)});
PHASE prefer_inline {p}_prefer - - -
DROP TABLE IF EXISTS {p}_prefer;
CREATE TABLE {p}_prefer (id INT PRIMARY KEY, hinted BIT VARYING STORAGE PREFER_INLINE, other BIT VARYING, tag BIT VARYING);
INSERT INTO {p}_prefer VALUES (1, {val('c', preferred)}, {val('d', other)}, {val('e', TAG)});
PHASE prefer_outline {p}_alias - - -
DROP TABLE IF EXISTS {p}_alias;
CREATE TABLE {p}_alias (id INT PRIMARY KEY, hinted BIT VARYING STORAGE PREFER_OUTLINE, other BIT VARYING, tag BIT VARYING);
INSERT INTO {p}_alias VALUES (1, {val('f', preferred)}, {val('9', other)}, {val('8', TAG)});
PHASE default_control {p}_default - - -
DROP TABLE IF EXISTS {p}_default;
CREATE TABLE {p}_default (id INT PRIMARY KEY, hinted BIT VARYING, other BIT VARYING, tag BIT VARYING);
INSERT INTO {p}_default VALUES (1, {val('7', preferred)}, {val('6', other)}, {val('5', TAG)});
"""


SPECS_T18 = [spec_rep01_gate_boundary, spec_rep02_demotion_order, spec_rep04_eligibility_floor,
             spec_rep07_chunk_boundary, spec_rep08_bigone_rejection, spec_rep09_null_empty,
             spec_rep10_many_stubs, spec_rep11_transitions, spec_rep13_placement_hints]



CASES_T19 = [case_sql01, case_sql02, case_sql05, case_sql06_rollback, case_sql06_constraints,
             case_sql06_triggers, case_rep06_lob, case_mixed_chunks]

CASES_T18 = [case_rep01_gate_boundary, case_rep02_demotion_order,
             case_rep04_eligibility_floor, case_rep07_chunk_boundary,
             case_rep08_bigone_rejection, case_rep09_null_empty,
             case_rep10_many_stubs, case_rep11_transitions,
             case_rep13_placement_hints]

CASES = CASES_T19 + CASES_T18


SPEC_DIR = Path(__file__).resolve().parent / "activation"
# Ticket 18's specs live beside ticket 18's records, not beside ticket 19's: one ticket's
# evidence directory holds one ticket's evidence, which is what the record contract assumes and
# what a per-ticket `validate_records.py` run reads.
SPEC_DIR_T18 = Path(__file__).resolve().parents[1] / "ticket18" / "activation"
SPEC_GROUPS = [(SPEC_DIR, SPECS), (SPEC_DIR_T18, SPECS_T18)]


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


def emit(out: Path, spec_groups=None):
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
    for spec_dir, specs in (spec_groups or []):
        spec_dir.mkdir(parents=True, exist_ok=True)
        for fn in specs:
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

    written = emit(args.out, SPEC_GROUPS)
    for p in written:
        print(f"wrote {p} ({len(p.read_text().splitlines())} lines)")
    kinds = {}
    for kind, _sizes, _where in _emitted:
        kinds[kind] = kinds.get(kind, 0) + 1
    for spec_dir, _specs in SPEC_GROUPS:
        for spec in sorted(spec_dir.glob("*.spec")):
            print(f"wrote {spec}")
    print(f"verified fixtures: {kinds.get('oos', 0)} OOS-backed, {kinds.get('inline', 0)} inline; "
          "every one assertable under both the pinned and the normative accounting")
    return 0


if __name__ == "__main__":
    sys.exit(main())
