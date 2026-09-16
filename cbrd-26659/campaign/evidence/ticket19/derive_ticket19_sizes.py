#!/usr/bin/env python3
"""Derive and justify every fixture size of the ticket-19 public SQL-operations family.

The cases live in `sql/_36_guava/cbrd_26659/cases/` of the public `testcases` repository on
branch CBRD-26659-oos-testcases-handover.

Everything printed here is computed from the pinned engine's serialized record accounting as
captured by ticket 11's `oos_boundaries.py`, never from an engine run.  Like ticket 13's
`derive_case_sizes.py`, which this script follows, it answers the two questions the campaign
specification demands before an expectation may be asserted:

  1. Do the pinned gate (DB_PAGESIZE/4, 4,086 B at 16 KiB) and the normative four-record target
     (CBRD-27057, 4,060 B at 16 KiB) *agree* on which columns of each fixture row are demoted?
  2. Does the 16-byte pinned inline stub versus the 24-byte normative stub (CBRD-26950) change
     that answer?

Only when both agree is a row's OOS-backed-ness a premise the case may rely on.  Ticket 19's
assertions are value-correctness assertions (OOS-SQL-01, -02, -05, -06) that hold whatever the
placement is; the agreement matters because it is what makes the *fixture* an OOS fixture
rather than one that merely looks large.  The same is true of the single-chunk versus
multi-chunk topology used by the UPDATE case: the chunk count must be the same under both
chunk-header sizes or the topology claim is not assertable.

It also prints the expected MD5 digests of the sampled values.  CUBRID's MD5 of a BIT VARYING
digests its lowercase hexadecimal form, so every digest here is reproducible outside CUBRID:

    python3 -c "import hashlib; print(hashlib.md5(('aa'*3000).encode()).hexdigest())"

verified against ticket 13's promoted answer (`big_md5` for REPEAT('AA', 3000) is
56d1d803c5f755f96819a2996fb65e43).

Usage: python3 derive_ticket19_sizes.py [--self-test]
Exit status 0 when every fixture is assertable under both accountings.
"""
import hashlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "ticket11-evidence"))
import oos_boundaries as ob  # noqa: E402

PAGE_SIZE = 16384  # the fast tier's page size (spec: Execution tiers)
INT_DISK = ob.INT_DISK_SIZE

# The hex alphabet the cases index with MOD(i, 15) + 1.  '0' is deliberately absent: an
# all-zero-byte value is a weak fixture, because a fault that zero-fills a buffer would
# reproduce it exactly (spec: Test data conventions, "distinct byte patterns").
HEX_ALPHABET = "123456789abcdef"

ACCOUNTINGS = (
    ("pinned    (gate DB_PAGESIZE/4, 16 B stub, 16 B chunk header)",
     ob.gate_pinned, ob.OR_OOS_INLINE_SIZE_PINNED, ob.OOS_RECORD_HEADER_SIZE_PINNED),
    ("normative (CBRD-27057 target, 24 B stub, 24 B chunk header)",
     ob.target_normative, ob.OR_OOS_INLINE_SIZE_NORMATIVE, ob.OOS_RECORD_HEADER_SIZE_NORMATIVE),
)

# Schema C carries most of the family: (id INT PRIMARY KEY, payload BIT VARYING,
# tag BIT VARYING).  `tag` is always an eligible candidate (far above both 16 B and 24 B
# eligibility floors) that nevertheless stays inline because the largest-first loop stops after
# `payload`.  That is what makes each fixture discriminating rather than merely large.
#
# Schema D is the reused CBRD-27006 workload's own shape, four columns wide:
# (id INT PRIMARY KEY, single1 BIT VARYING, multi1 BIT VARYING, single2 BIT VARYING).
SCHEMA_C = ("id", "payload", "tag")
SCHEMA_D = ("id", "single1", "multi1", "single2")

# The reused CBRD-27006 workload's own sizes, quoted verbatim from commit 1fdcaf935.  One home:
# the FIXTURES table below, `gen_ticket19_cases.case_mixed_chunks()` and the tie-invariance
# self-test all read them from here.  They were typed out in all three, so an edit that made row
# 1's two single-chunk columns unequal would have destroyed the documented tie while the
# self-test kept passing on a copy of the old sizes (ticket 44 F5).
REUSED_27006_ROWS = {1: [3500, 20000, 3500], 2: [3600, 21000, 3400]}
REUSED_27006_UPDATE = [3700, 22000, 3300]

# Every fixture row the family depends on:
#   (label, column names, variable-column byte sizes, expected demoted column names)
FIXTURES = [
    ("sql01/sql02/sql05/sql06 OOS-backed row", SCHEMA_C, [4200, 300], ["payload"]),
    ("sql01/sql02/sql05/sql06 inline comparator row", SCHEMA_C, [3000, 300], []),
    ("sql02 replacement value (still single-chunk)", SCHEMA_C, [5000, 300], ["payload"]),
    ("sql02 multi-chunk value", SCHEMA_C, [20000, 300], ["payload"]),
    ("sql02 back to single-chunk value", SCHEMA_C, [4400, 300], ["payload"]),
    ("sql01 bulk-100 smallest row (i = 1)", SCHEMA_C, [4207, 300], ["payload"]),
    ("sql01 bulk-100 largest row (i = 100)", SCHEMA_C, [4900, 300], ["payload"]),
    ("sql01 bulk-1000 smallest row (i mod 97 = 0)", SCHEMA_C, [4100, 300], ["payload"]),
    ("sql01 bulk-1000 largest row (i mod 97 = 96)", SCHEMA_C, [4196, 300], ["payload"]),
    ("rep06 LOB-neighbour OOS row", SCHEMA_C, [4200, 300], ["payload"]),
    # Row 1 of the reused workload has two equal-size eligible columns (single1 and single2 are
    # both 3,500 B), so which of them the largest-first loop demotes is a TIE the normative text
    # does not settle -- it says "sort candidates by size descending", and says nothing about
    # equal sizes.  The sizes are kept verbatim for provenance; the tie is recorded instead of
    # being engineered away, and no case asserts which column moved.  See the tie-invariance
    # check below: `Oos_recs_sumlen` is the same either way, so the activation evidence is sound.
    ("mixed-chunks row 1 (reused CBRD-27006 sizes)", SCHEMA_D, list(REUSED_27006_ROWS[1]),
     ["multi1", "single1|single2"]),
    ("mixed-chunks row 2 (reused CBRD-27006 sizes)", SCHEMA_D, list(REUSED_27006_ROWS[2]),
     ["multi1", "single1"]),
    ("mixed-chunks row 1 after the UPDATE (reused sizes)", SCHEMA_D, list(REUSED_27006_UPDATE),
     ["multi1", "single1"]),
]

# Values whose whole-value digest a case prints, so the expected digest is derivable here.
#   (label, hex character, logical bytes)
DIGEST_SAMPLES = [
    ("sql01 single OOS-backed payload", "a", 4200),
    ("sql01 single OOS-backed tag", "b", 300),
    ("sql01 inline comparator payload", "c", 3000),
    ("sql01 inline comparator tag", "d", 300),
    ("sql02 initial payload", "a", 4200),
    ("sql02 payload after the first UPDATE", "e", 5000),
    ("sql02 multi-chunk payload", "f", 20000),
    ("sql02 payload after shrinking back", "9", 4400),
    ("sql06 payload before ROLLBACK", "a", 4200),
    ("sql06 payload the ROLLBACK must restore", "a", 4200),
]


class BulkGroup:
    """One generated row group, defined once so the label, the digest and the case SQL agree.

    `size_sql` and `char_sql` are the exact SQL expressions the case writes, and `size`/`char`
    evaluate the same arithmetic in Python.  The self-test checks that every row of the group
    is a distinct value, which is what the spec's "distinct byte patterns" convention asks and
    what a size cycle sharing a period with the pattern cycle would silently break.
    """

    def __init__(self, name, n_rows, size_expr, size_sql_template, samples):
        self.name = name
        self.n_rows = n_rows
        self._size = size_expr
        self._size_sql = size_sql_template   # carries a single {c} placeholder for the column
        self.samples = samples

    def ids(self):
        return range(1, self.n_rows + 1)

    def size(self, i):
        return self._size(i)

    def char(self, i):
        return HEX_ALPHABET[i % len(HEX_ALPHABET)]

    # The generated rows are written by an INSERT ... SELECT reading the helper table's `i`
    # and verified by a SELECT reading the target table's `id`.  Both spellings come from
    # here so a verification query can never silently read the wrong column.
    def size_sql(self, col):
        return self._size_sql.format(c=col)

    def char_sql(self, col):
        return f"SUBSTR('{HEX_ALPHABET}', MOD({col}, {len(HEX_ALPHABET)}) + 1, 1)"

    def value_sql(self, col):
        return (f"CAST(REPEAT({self.char_sql(col)}, 2 * ({self.size_sql(col)})) "
                f"AS BIT VARYING)")


BULK_100 = BulkGroup("bulk-100", 100, lambda i: 4200 + 7 * i, "4200 + 7 * {c}", (1, 50, 100))
BULK_1000 = BulkGroup("bulk-1000", 1000, lambda i: 4100 + (i % 97), "4100 + MOD({c}, 97)",
                      (1, 500, 1000))


def varbit(n):
    return ob.varbit_disk_len(n)


def row_layout(var_bytes, gate, stub):
    """Which variable columns the engine demotes, and the record size after.

    Every ticket-19 schema has exactly one fixed column, the INT primary key.
    """
    var_sizes = [varbit(n) for n in var_bytes]
    demoted, inline_after, offset_size = ob.layout([INT_DISK], var_sizes, gate, stub)
    return demoted, inline_after, offset_size, var_sizes


def record_before(var_bytes):
    """Serialized record size before any demotion (what the gate is compared against)."""
    var_sizes = [varbit(n) for n in var_bytes]
    payload = INT_DISK + sum(var_sizes)
    hdr, _ = ob.header_size(1, len(var_sizes), payload)
    return hdr + payload + ob.MVCC_EXTRA


def chunks(n, chunk_header):
    """Chunk records one OOS value of n logical bytes occupies."""
    cap = ob.max_chunk_payload(PAGE_SIZE, chunk_header)
    return -(-varbit(n) // cap)


class NotAssertable(Exception):
    """Raised when a fixture's placement is not the same under both accountings."""


def classify(var_bytes, schema_names=None):
    """Classify one fixture row, refusing anything the campaign may not assert.

    Returns (kind, demoted_names) where kind is "oos" or "inline".  Raises NotAssertable when
    the pinned and normative accountings disagree about which columns are demoted -- that is
    the band the spec forbids a case to rely on -- and when an OOS row leaves no eligible
    column inline, because such a row cannot tell largest-first from any other order.

    A tie between equal-size candidates is NOT an error: it is reported by returning the
    demoted set the pinned accounting produces together with `tie=True` in the third element,
    so the caller can refrain from asserting the identity of the moved column.
    """
    names = list(schema_names or [f"v{i}" for i in range(len(var_bytes))])
    seen = []
    for _lbl, gate_fn, stub, _hdr in ACCOUNTINGS:
        demoted, after, _off, vs = row_layout(var_bytes, gate_fn(PAGE_SIZE), stub)
        seen.append((tuple(sorted(demoted)), after, tuple(vs), stub, gate_fn(PAGE_SIZE)))
    if seen[0][0] != seen[1][0]:
        raise NotAssertable(
            f"sizes {var_bytes}: the pinned accounting demotes "
            f"{[names[i] for i in seen[0][0]] or 'nothing'} and the normative one demotes "
            f"{[names[i] for i in seen[1][0]] or 'nothing'}; no case may assert this fixture")
    demoted = seen[0][0]
    if not demoted:
        return "inline", [], False
    for _d, after, vs, stub, gate in seen:
        if after > gate:
            raise NotAssertable(f"sizes {var_bytes}: the record still exceeds the gate "
                                f"({after} > {gate}) after demotion")
        if not any(vs[i] > stub for i in range(len(vs)) if i not in demoted):
            raise NotAssertable(f"sizes {var_bytes}: no eligible column is left inline, so the "
                                "fixture does not discriminate largest-first from any other order")
    sizes = [var_bytes[i] for i in demoted]
    tie = len(set(var_bytes)) != len(var_bytes) and len(set(sizes)) != len(sizes) or (
        any(var_bytes.count(s) > 1 for s in sizes))
    return "oos", [names[i] for i in demoted], tie


def md5_of(hex_char, n_bytes):
    """CUBRID MD5 of CAST(REPEAT('<hex_char>', 2n) AS BIT VARYING): the digest of its lowercase
    hexadecimal form, which is exactly the 2n-character string the case writes."""
    return hashlib.md5((hex_char * (2 * n_bytes)).encode()).hexdigest()


def main():
    print(f"# Ticket 19 fixture derivation (page size {PAGE_SIZE} B)\n")
    print(f"pinned record gate            = {ob.gate_pinned(PAGE_SIZE):>6} B  (heap_file.c:12350,12383)")
    print(f"normative record target       = {ob.target_normative(PAGE_SIZE):>6} B  (OOS-CONTEXT section 1, CBRD-27057)")
    print(f"pinned max chunk payload      = {ob.max_chunk_payload(PAGE_SIZE, ob.OOS_RECORD_HEADER_SIZE_PINNED):>6} B")
    print(f"normative max chunk payload   = {ob.max_chunk_payload(PAGE_SIZE, ob.OOS_RECORD_HEADER_SIZE_NORMATIVE):>6} B")
    print(f"pinned eligibility floor      = {ob.OR_OOS_INLINE_SIZE_PINNED:>6} B  (value must be strictly greater)")
    print(f"normative eligibility floor   = {ob.OR_OOS_INLINE_SIZE_NORMATIVE:>6} B")
    print()

    assertable = True
    tied = []

    print("## Placement: does each fixture row demote the same columns under both accountings?\n")
    header = (f"{'fixture':<52} {'variable columns (B)':>24} {'record':>7} "
              f"{'pinned':>17} {'normative':>17} {'verdict':>10}")
    print(header)
    print("-" * len(header))
    for label, schema, var_bytes, want in FIXTURES:
        rec = record_before(var_bytes)
        var_names = schema[1:]
        seen = []
        for _, gate_fn, stub, _hdr in ACCOUNTINGS:
            demoted, _after, _off, _vs = row_layout(var_bytes, gate_fn(PAGE_SIZE), stub)
            seen.append(tuple(sorted(demoted)))
        def render(idxs):
            return "+".join(var_names[i] for i in idxs) if idxs else "nothing"
        got_pinned, got_norm = render(seen[0]), render(seen[1])
        agree = seen[0] == seen[1]
        has_tie = any("|" in w for w in want)
        got_names = set(got_pinned.split("+")) if seen[0] else {"nothing"}
        want_names = set()
        for w in (want or ["nothing"]):
            want_names |= set(w.split("|"))
        # a tied expectation is met when every demoted column is one the expectation allows and
        # the count matches; an untied one must match exactly.
        met = (got_names <= want_names) and len(seen[0]) == len(want)
        ok = agree and met
        verdict = "ASSERTABLE" if ok and not has_tie else ("TIE" if ok else "NOT")
        tied.append(label) if (ok and has_tie) else None
        assertable = assertable and ok
        print(f"{label:<52} {','.join(str(n) for n in var_bytes):>24} {rec:>7} "
              f"{got_pinned:>17} {got_norm:>17} {verdict:>10}")
    if tied:
        print()
        print("TIE means the two accountings agree with each other, but the fixture has two")
        print("equal-size eligible columns, so which of them moved is not settled by the")
        print("normative text.  No case asserts the identity of the moved column for:")
        for label in tied:
            print(f"  - {label}")
    print()

    print("## The demotion loop stops: an eligible column is left inline in every OOS fixture\n")
    print(f"A 300 B `tag` serializes to {varbit(300)} B and a 3,400 B `single2` to {varbit(3400)} B; both are far above")
    print(f"both eligibility floors ({ob.OR_OOS_INLINE_SIZE_PINNED} B pinned, {ob.OR_OOS_INLINE_SIZE_NORMATIVE} B normative), so each stays inline because the")
    print("largest-first loop already reached the target, not because it was ineligible.")
    for label, schema, var_bytes, want in FIXTURES:
        if not want:
            continue
        var_names = schema[1:]
        for acc_label, gate_fn, stub, _hdr in ACCOUNTINGS:
            demoted, after, _off, vs = row_layout(var_bytes, gate_fn(PAGE_SIZE), stub)
            if after > gate_fn(PAGE_SIZE):
                print(f"  NOT ASSERTABLE: {label} still exceeds the gate after demotion "
                      f"({after} B > {gate_fn(PAGE_SIZE)} B) under {acc_label}")
                assertable = False
            left = [i for i in range(len(vs)) if i not in demoted]
            if not any(vs[i] > stub for i in left):
                print(f"  WEAK FIXTURE: {label} leaves no eligible column inline under {acc_label}; "
                      "it does not discriminate largest-first from any other order")
                assertable = False
    print("  every OOS fixture leaves at least one eligible column inline under both accountings.")
    print()

    print("## Chunk topology: is the single/multi-chunk claim the same under both chunk headers?\n")
    topo = (f"{'value':<58} {'bytes':>7} {'serialized':>11} {'pinned':>8} {'normative':>10} {'verdict':>10}")
    print(topo)
    print("-" * len(topo))
    for label, n, want_chunks in [
        ("sql02 initial payload (single chunk)", 4200, 1),
        ("sql02 replacement payload (single chunk)", 5000, 1),
        ("sql02 multi-chunk payload", 20000, 2),
        ("sql02 payload after shrinking back (single chunk)", 4400, 1),
        ("mixed-chunks single1 / single2 (single chunk)", 3500, 1),
        ("mixed-chunks multi1 (multi chunk)", 20000, 2),
        ("bulk-100 largest payload (single chunk)", 4900, 1),
    ]:
        cp = chunks(n, ob.OOS_RECORD_HEADER_SIZE_PINNED)
        cn = chunks(n, ob.OOS_RECORD_HEADER_SIZE_NORMATIVE)
        ok = cp == cn == want_chunks
        assertable = assertable and ok
        print(f"{label:<58} {n:>7} {varbit(n):>11} {cp:>8} {cn:>10} "
              f"{'ASSERTABLE' if ok else 'NOT':>10}")
    print()

    print("## Chunk payload sums the activation checker asserts (Oos_recs_sumlen)\n")
    print("Oos_recs_sumlen counts serialized payload plus one chunk header per chunk record, at")
    print(f"the PINNED {ob.OOS_RECORD_HEADER_SIZE_PINNED}-byte header.  The 24-byte normative header would give a different")
    print("number; that difference is the Capability gap already recorded against OOS-REP-05, and")
    print("no answer file carries these figures -- only the checker does.\n")
    hdr_p = ob.OOS_RECORD_HEADER_SIZE_PINNED
    print(f"{'fixture row':<52} {'demoted (B)':>20} {'chunks':>7} {'sumlen':>9}")
    print("-" * 92)
    for label, schema, var_bytes, want in FIXTURES:
        if not want:
            continue
        demoted, _a, _o, _vs = row_layout(var_bytes, ob.gate_pinned(PAGE_SIZE),
                                          ob.OR_OOS_INLINE_SIZE_PINNED)
        sizes = [var_bytes[i] for i in sorted(demoted)]
        n_chunks = sum(chunks(n, hdr_p) for n in sizes)
        sumlen = sum(varbit(n) + chunks(n, hdr_p) * hdr_p for n in sizes)
        print(f"{label:<52} {','.join(str(n) for n in sizes):>20} {n_chunks:>7} {sumlen:>9}")
    print()

    print("## Expected MD5 digests (derivable outside CUBRID)\n")
    print(f"{'value':<58} {'char':>5} {'bytes':>7} {'md5':>34}")
    print("-" * 106)
    for label, ch, n in DIGEST_SAMPLES:
        print(f"{label:<58} {ch:>5} {n:>7} {md5_of(ch, n):>34}")
    print()

    print("## Bulk-group arithmetic the aggregate assertions depend on\n")
    for group in (BULK_100, BULK_1000):
        sizes = [group.size(i) for i in group.ids()]
        print(f"{group.name}: rows {len(sizes)}, sizes {min(sizes)}..{max(sizes)}, "
              f"distinct values {len({(group.char(i), group.size(i)) for i in group.ids()})}, "
              f"sum(OCTET_LENGTH) {sum(sizes)}, sum(BIT_LENGTH) {8 * sum(sizes)}")
    for group in (BULK_100, BULK_1000):
        print(f"{group.name} sampled rows: "
              + ", ".join(f"i={i} -> char '{group.char(i)}', {group.size(i)} B, "
                          f"md5 {md5_of(group.char(i), group.size(i))}"
                          for i in group.samples))
    print()

    print("RESULT:", "every ticket-19 fixture is assertable under both accountings"
          if assertable else "AT LEAST ONE FIXTURE IS NOT ASSERTABLE -- do not write the case")
    return 0 if assertable else 1


def self_test():
    """Refuse to be trusted without the checks that would have caught a silent mis-derivation.

    1. the MD5 convention reproduces ticket 13's promoted answer;
    2. a value one byte above the pinned single-chunk maximum really is two chunks, and one
       byte below it is one, so `chunks` is not off by one;
    3. a fixture the pinned and normative gates disagree about is reported NOT assertable, so
       the agreement check can actually fail.
    """
    failures = []

    def check(label, got, want):
        if got != want:
            failures.append(f"{label}: got {got!r}, want {want!r}")

    check("ticket 13 big_md5", md5_of("a", 3000), "56d1d803c5f755f96819a2996fb65e43")
    check("ticket 13 small_md5", md5_of("b", 1200), "6d5d5cbc57eac18ff5c9af115e2e7e69")

    # The tied fixture's activation assertion must not depend on the tie: demoting single1 or
    # single2 has to give the same chunk count and the same Oos_recs_sumlen, or the checker
    # would be asserting the tie-break the specification does not fix.  Both demotion sets are
    # DERIVED from the workload's own sizes, not re-typed: the earlier form compared one literal
    # with itself, so an edit that made the two columns unequal would have removed the tie and
    # left this passing (ticket 44 F5).
    hdr = ob.OOS_RECORD_HEADER_SIZE_PINNED
    def sumlen(sizes):
        return sum(varbit(n) + chunks(n, hdr) * hdr for n in sizes)

    row1 = list(REUSED_27006_ROWS[1])
    row1_names = list(SCHEMA_D[1:])
    demoted_1, _a1, _o1, _v1 = row_layout(row1, ob.gate_pinned(PAGE_SIZE), ob.OR_OOS_INLINE_SIZE_PINNED)
    moved = sorted(demoted_1)
    # what the tie-break could have moved instead: an inline column the same size as one that
    # moved.  While single1 and single2 are equal there is exactly one such alternative; make
    # them unequal and there is none, and this check -- not a comparison of a literal with
    # itself -- is what fails.
    alternatives = [sorted((set(moved) - {out}) | {into})
                    for out in moved
                    for into in range(len(row1))
                    if into not in moved and row1[into] == row1[out]]
    check("the reused workload's row 1 still has a tie to be invariant under", len(alternatives), 1)

    def render(idxs):
        return "+".join(row1_names[i] for i in idxs)

    for alt in alternatives:
        check(f"tie-invariant sumlen ({render(moved)} vs {render(alt)})",
              sumlen([row1[i] for i in moved]), sumlen([row1[i] for i in alt]))
        check(f"tie-invariant chunk count ({render(moved)} vs {render(alt)})",
              sum(chunks(row1[i], hdr) for i in moved), sum(chunks(row1[i], hdr) for i in alt))
    check("the reused workload's row 1 occupies three chunks",
          sum(chunks(row1[i], hdr) for i in moved), 3)
    # and a guard that the invariance is a property of the equal sizes, not of the function:
    check("unequal sizes would NOT be tie-invariant", sumlen([20000, 3500]) == sumlen([20000, 3600]),
          False)

    hdr_p = ob.OOS_RECORD_HEADER_SIZE_PINNED
    cap = ob.max_chunk_payload(PAGE_SIZE, hdr_p)
    largest_single = max(n for n in range(cap - 32, cap + 1) if varbit(n) <= cap)
    check("largest single-chunk value is one chunk", chunks(largest_single, hdr_p), 1)
    check("one byte more is two chunks", chunks(largest_single + 1, hdr_p), 2)

    # A payload in the band where the two gates disagree must NOT read as assertable.
    band_lo, band_hi = None, None
    for n in range(3000, 4400):
        p = bool(row_layout([n, 300], ob.gate_pinned(PAGE_SIZE), ob.OR_OOS_INLINE_SIZE_PINNED)[0])
        q = bool(row_layout([n, 300], ob.target_normative(PAGE_SIZE),
                            ob.OR_OOS_INLINE_SIZE_NORMATIVE)[0])
        if p != q:
            band_lo = n if band_lo is None else band_lo
            band_hi = n
    check("a disagreement band exists for schema C", band_lo is not None, True)
    if band_lo is not None:
        p = tuple(sorted(row_layout([band_lo, 300], ob.gate_pinned(PAGE_SIZE),
                                    ob.OR_OOS_INLINE_SIZE_PINNED)[0]))
        q = tuple(sorted(row_layout([band_lo, 300], ob.target_normative(PAGE_SIZE),
                                    ob.OR_OOS_INLINE_SIZE_NORMATIVE)[0]))
        check("the two accountings really differ inside the band", p != q, True)
        print(f"schema C disagreement band: payload {band_lo}..{band_hi} B "
              f"(no schema C fixture uses it)")
        for label, schema, var_bytes, _want in FIXTURES:
            if schema is not SCHEMA_C:
                continue
            if band_lo <= var_bytes[0] <= band_hi:
                failures.append(f"{label}: payload {var_bytes[0]} lies inside the disagreement band")

    # Every generated row must be a distinct value, and every generated row must be OOS-backed
    # under both accountings; a size cycle whose period shares a factor with the 15-character
    # pattern cycle would silently produce duplicate values.
    for group in (BULK_100, BULK_1000):
        values = {(group.char(i), group.size(i)) for i in group.ids()}
        check(f"{group.name}: every generated row is a distinct value", len(values), group.n_rows)
        for i in group.ids():
            for _lbl, gate_fn, stub, _h in ACCOUNTINGS:
                demoted, _a, _o, _v = row_layout([group.size(i), 300], gate_fn(PAGE_SIZE), stub)
                if tuple(sorted(demoted)) != (0,):
                    failures.append(f"{group.name} row i={i} ({group.size(i)} B) does not demote "
                                    f"exactly `payload` under {_lbl}")
                    break
            else:
                continue
            break

    for f in failures:
        print(f"SELF-TEST FAIL  {f}")
    print("SELF-TEST:", "all checks pass" if not failures else f"{len(failures)} failure(s)")
    return 0 if not failures else 1


if __name__ == "__main__":
    if "--self-test" in sys.argv:
        sys.exit(self_test())
    sys.exit(main())
