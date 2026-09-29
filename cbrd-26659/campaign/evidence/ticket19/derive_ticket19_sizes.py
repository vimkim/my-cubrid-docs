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


# ==============================================================================================
# Ticket 18 -- the public Representation family.  Same rules, same refusals, one more schema
# shape (a fixed BIT filler) and three more expectations (`oos-exhausted`, `disputed`, and the
# placement hints, which this accounting deliberately does not model).
# ==============================================================================================

# Variable-column name lists, in declaration order.  They are the names `classify()` indexes,
# so they never include the INT primary key or the fixed BIT filler.
T18_SCHEMA_C = ["payload", "tag"]
T18_SCHEMA_ORDER = ["big1", "big2", "tag"]
T18_SCHEMA_CASCADE = ["big1", "big2", "big3", "tag"]
T18_SCHEMA_FLOOR = ["payload", "small"]
T18_SCHEMA_NULLS = ["payload", "nullable", "empty", "tag"]
T18_SCHEMA_VOT = ["a", "b"]
T18_SCHEMA_BIGONE = ["v"]
T18_WIDE_COLUMNS = 18
T18_SCHEMA_WIDE = [f"v{i:02d}" for i in range(1, T18_WIDE_COLUMNS + 1)]

T18_TAG = 300  # the inline neighbour of the schema-C rows, as in ticket 19

# --- the record gate (OOS-REP-01, OOS-REP-02, and OOS-REP-03's band) ---------------------------
# Schema C's two accountings part company over `payload` 3,700..3,723 B: the normative
# four-record target demotes there and the pinned DB_PAGESIZE/4 gate does not.  The two sizes
# either side of it are the sharpest pair of boundary fixtures the campaign may assert, and the
# two inside it are the conformance gap itself, carried as `disputed`.
T18_GATE_INLINE_BOTH = 3699
T18_GATE_BAND_LO = 3700
T18_GATE_BAND_HI = 3723
T18_GATE_OOS_BOTH = 3724

# --- the eligibility floor (OOS-REP-04, and OOS-REP-05's band) ---------------------------------
# A fixed BIT(8 * 5000) filler puts the record 5,080 B over a 4,086 B gate that demoting
# `payload` cannot bring it back under, so the loop runs out of candidates with `small` still
# inline.  That is the only shape in which "below the floor" and "the loop had already stopped"
# are distinguishable.  15 B serializes to 16 (at or below the pinned floor, so never a
# candidate under either accounting); 24 B serializes to 28 (a candidate under both); 20 B
# serializes to 24, which the pinned 16-byte floor demotes and the normative 24-byte floor does
# not -- OOS-REP-05's band, read as a logical-byte range of [16, 23].
T18_FLOOR_FILLER = 5000
T18_FLOOR_PAYLOAD = 4200
T18_FLOOR_BELOW = 15
T18_FLOOR_BAND = 20
T18_FLOOR_ABOVE = 24
T18_FLOOR_COMPARATOR_FILLER = 100

# --- largest-first order (OOS-REP-02) ----------------------------------------------------------
T18_ORDER_UNEQUAL = [2000, 1900, T18_TAG]        # only `big1` moves, and sumlen says which
T18_ORDER_TIE = [2000, 2000, T18_TAG]            # equal candidates: which one moved is not fixed
T18_ORDER_CASCADE = [2200, 2100, 2000, T18_TAG]  # two must move; the third-largest stays inline

# --- ten or more demoted attributes (OOS-REP-10) -----------------------------------------------
# Eighteen variable columns of distinct descending sizes, so the largest-first order is total and
# the demoted set is identified by its payload sum rather than only by its count.
T18_WIDE_BASE, T18_WIDE_STEP = 700, 10
T18_WIDE_SIZES = [T18_WIDE_BASE - T18_WIDE_STEP * i for i in range(T18_WIDE_COLUMNS)]
T18_WIDE_COMPARATOR = 30  # every column of the inline comparator row

# --- chunk topology (OOS-REP-07) ---------------------------------------------------------------
# The chunk boundary moves with the chunk header, so the assertable pair is the largest value
# that is one chunk under BOTH headers and the smallest that is two under both.  The eight
# logical bytes between them (16,276..16,283) are OOS-REP-05's band and no case enters them.
T18_CHUNK_ONE_BOTH = 16275
T18_CHUNK_TWO_BOTH = 16284
T18_CHUNK_THREE_BOTH = 32576
T18_CHUNK_BAND_LO, T18_CHUNK_BAND_HI = 16276, 16283

# --- OOS + bigone rejection (OOS-REP-08) -------------------------------------------------------
# Schema B of ticket 11 section 5.2: (id INT, filler BIT(8*F), v BIT VARYING) with v = 64 B.
# F = 16,168 is accepted under both accountings and F = 16,177 is rejected under both; the eight
# bytes between are where the normative 24-byte stub rejects and the pin accepts, and no case
# enters them either.  The non-OOS neighbour carries a 10 B variable value, below both floors,
# so `has_oos` is false and the record becomes an ordinary REC_BIGONE.
T18_BIGONE_VARBIT = 64
T18_BIGONE_ACCEPTED = 16168
T18_BIGONE_REJECTED = 16177
T18_BIGONE_BAND_LO, T18_BIGONE_BAND_HI = 16169, 16176
T18_NONOOS_FILLER = 20000
T18_NONOOS_SMALL = 10
T18_BIGONE_COMPARATOR_FILLER = 100

# --- VOT width and inline/OOS transitions (OOS-REP-11, OOS-REP-01) -----------------------------
# With two variable columns the variable-offset table is ALIGN(1 * 3, 4) = 4 B at one-byte
# entries and ALIGN(2 * 3, 4) = 8 B at two, so the header itself changes across the boundary --
# with one variable column both widths round to the same 4 B and nothing moves.  The pair below
# straddles the OR_MAX_BYTE = 127 limit on header + payload.
T18_VOT_NARROW_TAG = 30       # schema C: two-byte entries before demotion, one-byte after
T18_VOT_ONE_BYTE = [40, 40]
T18_VOT_TWO_BYTE = [40, 44]
T18_TRANSITION_INLINE = 3000  # below both gates
T18_TRANSITION_OOS = 4200     # above both gates

# --- placement hints (OOS-REP-12, OOS-REP-13) --------------------------------------------------
# Deliberately NOT routed through `classify()`.  `oos_boundaries.layout()` reproduces
# heap_attrinfo_determine_disk_layout for DEFAULT storage hints only, which its own docstring
# says; FORCE_OUTLINE demotes before the gate is even consulted and PREFER_INLINE reorders the
# candidate list.  Deriving a placement for them would be deriving it from an accounting that
# does not model them, and the authority policy withholds the expectation anyway (OOS-REP-13,
# BLOCKED).  The hint fixtures therefore carry sizes and value digests, and no placement claim.
T18_HINT_FORCED = 40          # far below every gate; FORCE_OUTLINE demotes it anyway at the pin
T18_HINT_PREFERRED = 2000     # the largest candidate of an over-gate record, hinted PREFER_INLINE
T18_HINT_OTHER = 1900
T18_HINT_TAG = T18_TAG

# Every ticket-18 fixture row, in the order the report prints them:
#   (label, variable column names, variable byte sizes, expectation, expected demoted names,
#    fixed filler byte sizes beside the INT key)
FIXTURES_T18 = [
    ("rep01 gate: largest record inline under both", T18_SCHEMA_C,
     [T18_GATE_INLINE_BOTH, T18_TAG], "inline", [], ()),
    ("rep01 gate: smallest record demoted under both", T18_SCHEMA_C,
     [T18_GATE_OOS_BOTH, T18_TAG], "oos", ["payload"], ()),
    ("rep01 gate: band low (normative demotes, pin does not)", T18_SCHEMA_C,
     [T18_GATE_BAND_LO, T18_TAG], "disputed", [], ()),
    ("rep01 gate: band high (normative demotes, pin does not)", T18_SCHEMA_C,
     [T18_GATE_BAND_HI, T18_TAG], "disputed", [], ()),
    ("rep02 order: two unequal candidates, largest moves", T18_SCHEMA_ORDER,
     T18_ORDER_UNEQUAL, "oos", ["big1"], ()),
    ("rep02 order: equal-size tie, one moves", T18_SCHEMA_ORDER,
     T18_ORDER_TIE, "oos", ["big1|big2"], ()),
    ("rep02 order: two of three move, third-largest stays", T18_SCHEMA_CASCADE,
     T18_ORDER_CASCADE, "oos", ["big1", "big2"], ()),
    ("rep02 order: inline comparator", T18_SCHEMA_ORDER, [900, 800, T18_TAG], "inline", [], ()),
    ("rep04 floor: 15 B stays inline, candidates exhausted", T18_SCHEMA_FLOOR,
     [T18_FLOOR_PAYLOAD, T18_FLOOR_BELOW], "oos-exhausted", ["payload"], (T18_FLOOR_FILLER,)),
    ("rep04 floor: 24 B is a candidate under both", T18_SCHEMA_FLOOR,
     [T18_FLOOR_PAYLOAD, T18_FLOOR_ABOVE], "oos-exhausted", ["payload", "small"],
     (T18_FLOOR_FILLER,)),
    ("rep04 floor: 20 B band (pin demotes, normative does not)", T18_SCHEMA_FLOOR,
     [T18_FLOOR_PAYLOAD, T18_FLOOR_BAND], "disputed", [], (T18_FLOOR_FILLER,)),
    ("rep04 floor: inline comparator", T18_SCHEMA_FLOOR, [500, T18_FLOOR_BELOW], "inline", [],
     (T18_FLOOR_COMPARATOR_FILLER,)),
    ("rep07 chunks: one chunk under both headers", T18_SCHEMA_C,
     [T18_CHUNK_ONE_BOTH, T18_TAG], "oos", ["payload"], ()),
    ("rep07 chunks: two chunks under both headers", T18_SCHEMA_C,
     [T18_CHUNK_TWO_BOTH, T18_TAG], "oos", ["payload"], ()),
    ("rep07 chunks: three chunks under both headers", T18_SCHEMA_C,
     [T18_CHUNK_THREE_BOTH, T18_TAG], "oos", ["payload"], ()),
    ("rep07 chunks: inline comparator", T18_SCHEMA_C, [T18_TRANSITION_INLINE, T18_TAG],
     "inline", [], ()),
    ("rep08 bigone: accepted under both", T18_SCHEMA_BIGONE, [T18_BIGONE_VARBIT], "oos-exhausted",
     ["v"], (T18_BIGONE_ACCEPTED,)),
    ("rep08 bigone: inline comparator", T18_SCHEMA_BIGONE, [T18_BIGONE_VARBIT], "inline", [],
     (T18_BIGONE_COMPARATOR_FILLER,)),
    ("rep09 nulls: NULL and empty beside a demoted sibling", T18_SCHEMA_NULLS,
     [T18_TRANSITION_OOS, None, 0, T18_TAG], "oos", ["payload"], ()),
    ("rep09 nulls: inline comparator", T18_SCHEMA_NULLS,
     [T18_TRANSITION_INLINE, None, 0, T18_TAG], "inline", [], ()),
    ("rep10 wide: twelve of eighteen demoted", T18_SCHEMA_WIDE, list(T18_WIDE_SIZES), "oos",
     T18_SCHEMA_WIDE[:12], ()),
    ("rep10 wide: inline comparator", T18_SCHEMA_WIDE,
     [T18_WIDE_COMPARATOR] * T18_WIDE_COLUMNS, "inline", [], ()),
    ("rep11 vot: one-byte entries, all inline", T18_SCHEMA_VOT, list(T18_VOT_ONE_BYTE),
     "inline", [], ()),
    ("rep11 vot: two-byte entries, all inline", T18_SCHEMA_VOT, list(T18_VOT_TWO_BYTE),
     "inline", [], ()),
    ("rep11 vot: two-byte before demotion, one-byte after", T18_SCHEMA_C,
     [T18_TRANSITION_OOS, T18_VOT_NARROW_TAG], "oos", ["payload"], ()),
    ("rep11 transitions: below both gates", T18_SCHEMA_C, [T18_TRANSITION_INLINE, T18_TAG],
     "inline", [], ()),
    ("rep11 transitions: above both gates", T18_SCHEMA_C, [T18_TRANSITION_OOS, T18_TAG],
     "oos", ["payload"], ()),
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


def var_disk(n):
    """Serialized size of one variable column's value, where `None` means SQL NULL.

    A NULL variable value occupies no payload bytes at all: `mr_lengthval_varbit_internal`
    starts at 0 and only adds the prefix and the bits when the value holds a string, so a NULL
    column contributes 0 to `heap_attrinfo_get_record_payload_size` and can never be a demotion
    candidate.  A zero-length value is different -- it still carries its one-byte length prefix,
    ALIGN(1, 4) = 4 B -- and the two are distinguished here because OOS-REP-09 is about both.
    """
    return 0 if n is None else varbit(n)


def row_layout(var_bytes, gate, stub, fixed_bytes=()):
    """Which variable columns the engine demotes, and the record size after.

    Every ticket-19 schema has exactly one fixed column, the INT primary key.  Ticket 18's
    eligibility-floor and OOS+bigone schemas add one fixed `BIT(8*F)` filler beside it, whose
    only job is to push the record over a gate that no variable column can bring it back under;
    `fixed_bytes` carries that filler's disk size, and stays empty for every ticket-19 schema.
    """
    var_sizes = [var_disk(n) for n in var_bytes]
    demoted, inline_after, offset_size = ob.layout([INT_DISK, *fixed_bytes], var_sizes, gate, stub)
    return demoted, inline_after, offset_size, var_sizes


def record_before(var_bytes, fixed_bytes=()):
    """Serialized record size before any demotion (what the gate is compared against)."""
    var_sizes = [var_disk(n) for n in var_bytes]
    payload = INT_DISK + sum(fixed_bytes) + sum(var_sizes)
    hdr, _ = ob.header_size(1 + len(fixed_bytes), len(var_sizes), payload)
    return hdr + payload + ob.MVCC_EXTRA


def chunks(n, chunk_header):
    """Chunk records one OOS value of n logical bytes occupies."""
    cap = ob.max_chunk_payload(PAGE_SIZE, chunk_header)
    return -(-varbit(n) // cap)


class NotAssertable(Exception):
    """Raised when a fixture's placement is not the same under both accountings."""


EXPECTATIONS = ("oos", "inline", "oos-exhausted", "disputed")


def demoted_under(var_bytes, accounting, fixed_bytes=()):
    """The demoted column indices under one accounting: `accounting` is "pinned" or "normative"."""
    _lbl, gate_fn, stub, _hdr = ACCOUNTINGS[0 if accounting == "pinned" else 1]
    demoted, after, _off, _vs = row_layout(var_bytes, gate_fn(PAGE_SIZE), stub, fixed_bytes)
    return tuple(sorted(demoted)), after, gate_fn(PAGE_SIZE)


def classify(var_bytes, schema_names=None, *, expect="oos", fixed_bytes=()):
    """Classify one fixture row, refusing anything the campaign may not assert.

    Returns (kind, demoted_names, tie).  `expect` names the claim the caller intends to make,
    and each value carries its own obligation, checked here so that a fixture can never quietly
    become a different kind of fixture than the case says it is:

      "oos"            the ticket-19 rule and the default.  Both accountings demote the same
                       non-empty set, the record is at or below the gate afterwards, and an
                       ELIGIBLE column is left inline -- without one the row cannot tell
                       largest-first from any other order.
      "inline"         both accountings demote nothing.
      "oos-exhausted"  both accountings demote the same non-empty set and the record is still
                       ABOVE the gate afterwards, because the candidates ran out.  That is the
                       "or candidates are exhausted" branch of OOS-REP-02, and it is the only
                       shape in which a value below the eligibility floor can be shown to stay
                       inline for its own sake rather than because the loop had already stopped
                       (OOS-REP-04).  The obligation is the mirror image of "oos": NO eligible
                       column may be left inline, because a loop that still wants to shrink the
                       record cannot have passed one over.  Together the two say that every
                       column left inline is below the floor, which is the whole claim.
      "disputed"       the two accountings demote DIFFERENT sets, which is the band ticket 11
                       named and the default refuses.  A case may carry such a row only for
                       assertions that hold under both readings -- whole values, their lengths
                       and their digests are placement-blind -- and its placement is recorded
                       as an observation against the requirement the authority policy names
                       (OOS-REP-03 for the record gate, OOS-REP-05 for the stub and the floor),
                       never asserted.  The returned demoted set is the PINNED one; use
                       `demoted_under` for both.

    Raises NotAssertable whenever the row is not the kind the caller said it was.

    A tie between equal-size candidates is NOT an error: it is reported by returning the
    demoted set the pinned accounting produces together with `tie=True` in the third element,
    so the caller can refrain from asserting the identity of the moved column.
    """
    if expect not in EXPECTATIONS:
        raise NotAssertable(f"unknown expectation {expect!r}; one of {EXPECTATIONS}")
    names = list(schema_names or [f"v{i}" for i in range(len(var_bytes))])
    seen = []
    for _lbl, gate_fn, stub, _hdr in ACCOUNTINGS:
        demoted, after, _off, vs = row_layout(var_bytes, gate_fn(PAGE_SIZE), stub, fixed_bytes)
        seen.append((tuple(sorted(demoted)), after, tuple(vs), stub, gate_fn(PAGE_SIZE)))
    agree = seen[0][0] == seen[1][0]
    rendered = (f"pinned demotes {[names[i] for i in seen[0][0]] or 'nothing'} and the normative "
                f"one demotes {[names[i] for i in seen[1][0]] or 'nothing'}")
    if expect == "disputed":
        if agree:
            raise NotAssertable(
                f"sizes {var_bytes}: both accountings agree ({rendered}), so this row is not in "
                "a disagreement band and must not be carried as one")
        return "disputed", [names[i] for i in seen[0][0]], False
    if not agree:
        raise NotAssertable(
            f"sizes {var_bytes}: the pinned accounting demotes "
            f"{[names[i] for i in seen[0][0]] or 'nothing'} and the normative one demotes "
            f"{[names[i] for i in seen[1][0]] or 'nothing'}; no case may assert this fixture")
    demoted = seen[0][0]
    if not demoted:
        return "inline", [], False
    for _d, after, vs, stub, gate in seen:
        if expect == "oos-exhausted":
            if after <= gate:
                raise NotAssertable(
                    f"sizes {var_bytes}: the record is {after} B after demotion, at or below the "
                    f"gate {gate}, so its candidates were not exhausted and an ineligible column "
                    "left inline proves nothing about the eligibility floor")
            left_eligible = [i for i in range(len(vs)) if i not in demoted and vs[i] > stub]
            if left_eligible:
                raise NotAssertable(
                    f"sizes {var_bytes}: {[names[i] for i in left_eligible]} is eligible and was "
                    f"left inline while the record is still {after} B, above the gate {gate}; "
                    "the largest-first loop cannot produce that, so the fixture is mis-derived")
            continue
        if after > gate:
            raise NotAssertable(f"sizes {var_bytes}: the record still exceeds the gate "
                                f"({after} > {gate}) after demotion")
        if not any(vs[i] > stub for i in range(len(vs)) if i not in demoted):
            raise NotAssertable(f"sizes {var_bytes}: no eligible column is left inline, so the "
                                "fixture does not discriminate largest-first from any other order")
    sizes = [var_bytes[i] for i in demoted]
    tie = len(set(var_bytes)) != len(var_bytes) and len(set(sizes)) != len(sizes) or (
        any(var_bytes.count(s) > 1 for s in sizes))
    kind = "oos-exhausted" if expect == "oos-exhausted" else "oos"
    return kind, [names[i] for i in demoted], tie


def md5_of(hex_char, n_bytes):
    """CUBRID MD5 of CAST(REPEAT('<hex_char>', 2n) AS BIT VARYING): the digest of its lowercase
    hexadecimal form, which is exactly the 2n-character string the case writes."""
    return hashlib.md5((hex_char * (2 * n_bytes)).encode()).hexdigest()


def band_of(schema_names, make_sizes, lo, hi, fixed_bytes=()):
    """The contiguous range of a size parameter over which the two accountings disagree.

    `make_sizes(n)` builds the fixture's variable-size list from the parameter.  Returned as
    (low, high) or (None, None).  Searching for the band rather than asserting a remembered pair
    of numbers is what makes the band a derived fact: an accounting change moves it here first.
    """
    found = [n for n in range(lo, hi + 1)
             if demoted_under(make_sizes(n), "pinned", fixed_bytes)[0]
             != demoted_under(make_sizes(n), "normative", fixed_bytes)[0]]
    return (min(found), max(found)) if found else (None, None)


def report_ticket18():
    """The ticket-18 Representation fixtures: placement, exhaustion, chunk topology, bands.

    Returns True when every fixture is the kind its case says it is.  A `disputed` row is not a
    failure -- it is a fixture the campaign carries deliberately, for value assertions only --
    so it is reported in its own column rather than counted against the run.
    """
    ok = True
    print("## Ticket 18 (Representation) placement: is each fixture the kind its case claims?\n")
    header = (f"{'fixture':<56} {'variable columns (B)':>26} {'record':>7} "
              f"{'pinned':>20} {'normative':>20} {'verdict':>14}")
    print(header)
    print("-" * len(header))
    for label, names, var_bytes, expect, want, fixed in FIXTURES_T18:
        rec = record_before(var_bytes, fixed)

        def render(idxs):
            return "+".join(names[i] for i in idxs) if idxs else "nothing"
        pin, _ap, _gp = demoted_under(var_bytes, "pinned", fixed)
        nrm, _an, _gn = demoted_under(var_bytes, "normative", fixed)
        try:
            kind, demoted, tie = classify(var_bytes, names, expect=expect, fixed_bytes=fixed)
            want_names = set()
            for w in (want or ["nothing"]):
                want_names |= set(w.split("|"))
            got_names = set(demoted) or {"nothing"}
            met = expect == "disputed" or (got_names <= want_names and len(demoted) == len(want))
            verdict = ("DISPUTED" if kind == "disputed" else
                       ("TIE" if tie else kind.upper())) if met else "WRONG SET"
            ok = ok and met
        except NotAssertable as exc:
            verdict = "REFUSED"
            ok = False
            print(f"  NOT ASSERTABLE: {label}: {exc}")
        shown = ",".join("NULL" if n is None else str(n) for n in var_bytes)
        if len(shown) > 26:
            shown = shown[:23] + "..."
        print(f"{label:<56} {shown:>26} {rec:>7} {render(pin):>20} {render(nrm):>20} "
              f"{verdict:>14}")
    print()

    print("## Ticket 18 disagreement bands, searched rather than remembered\n")
    gate_lo, gate_hi = band_of(T18_SCHEMA_C, lambda n: [n, T18_TAG], 3000, 4400)
    floor_lo, floor_hi = band_of(T18_SCHEMA_FLOOR, lambda n: [T18_FLOOR_PAYLOAD, n], 1, 64,
                                 (T18_FLOOR_FILLER,))
    print(f"record gate, schema C `payload`     {gate_lo}..{gate_hi} B   "
          f"(case fixtures {T18_GATE_INLINE_BOTH} and {T18_GATE_OOS_BOTH} sit one byte outside; "
          f"{T18_GATE_BAND_LO} and {T18_GATE_BAND_HI} sit inside, deliberately)")
    print(f"eligibility floor, `small`          {floor_lo}..{floor_hi} B    "
          f"(case fixtures {T18_FLOOR_BELOW} and {T18_FLOOR_ABOVE} sit outside; "
          f"{T18_FLOOR_BAND} sits inside, deliberately)")
    hdr_p, hdr_n = ob.OOS_RECORD_HEADER_SIZE_PINNED, ob.OOS_RECORD_HEADER_SIZE_NORMATIVE
    chunk_band = [n for n in range(16200, 16400) if chunks(n, hdr_p) != chunks(n, hdr_n)]
    print(f"single-to-multi chunk boundary      {min(chunk_band)}..{max(chunk_band)} B   "
          f"(case fixtures {T18_CHUNK_ONE_BOTH} and {T18_CHUNK_TWO_BOTH} sit outside; no case "
          "enters this one)")
    maxslot = ob.heap_maxslotted_reclength(PAGE_SIZE)

    def rejected(f_bytes, accounting):
        dem, after, _gate = demoted_under([T18_BIGONE_VARBIT], accounting, (f_bytes,))
        return bool(dem) and after > maxslot
    big_band = [f for f in range(16100, 16250)
                if rejected(f, "pinned") != rejected(f, "normative")]
    print(f"OOS + bigone rejection, filler `F`  {min(big_band)}..{max(big_band)} B   "
          f"(case fixtures {T18_BIGONE_ACCEPTED} and {T18_BIGONE_REJECTED} sit outside; no case "
          "enters this one)")
    print()

    print("## Ticket 18 chunk topology and the payload sums its checker asserts\n")
    topo = f"{'value':<56} {'bytes':>7} {'serialized':>11} {'pinned':>8} {'normative':>10} {'verdict':>10}"
    print(topo)
    print("-" * len(topo))
    for label, n, want_chunks in [
        ("rep07 one chunk under both headers", T18_CHUNK_ONE_BOTH, 1),
        ("rep07 two chunks under both headers", T18_CHUNK_TWO_BOTH, 2),
        ("rep07 three chunks under both headers", T18_CHUNK_THREE_BOTH, 3),
        ("rep01/rep04/rep09/rep11 4200 B payload", T18_TRANSITION_OOS, 1),
        ("rep01 3724 B payload", T18_GATE_OOS_BOTH, 1),
    ]:
        cp, cn = chunks(n, hdr_p), chunks(n, hdr_n)
        good = cp == cn == want_chunks
        ok = ok and good
        print(f"{label:<56} {n:>7} {varbit(n):>11} {cp:>8} {cn:>10} "
              f"{'ASSERTABLE' if good else 'NOT':>10}")
    print()
    print(f"{'fixture row':<56} {'demoted (B)':>24} {'chunks':>7} {'sumlen':>9}")
    print("-" * 100)
    for label, names, var_bytes, expect, _want, fixed in FIXTURES_T18:
        if expect not in ("oos", "oos-exhausted"):
            continue
        dem, _a, _g = demoted_under(var_bytes, "pinned", fixed)
        sizes = [var_bytes[i] for i in dem]
        n_chunks = sum(chunks(n, hdr_p) for n in sizes)
        sumlen = sum(varbit(n) + chunks(n, hdr_p) * hdr_p for n in sizes)
        shown = ",".join(str(n) for n in sizes)
        if len(shown) > 24:
            shown = shown[:21] + "..."
        print(f"{label:<56} {shown:>24} {n_chunks:>7} {sumlen:>9}")
    print()
    return ok


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

    assertable = report_ticket18() and assertable

    print("RESULT:", "every fixture is the kind its case claims, under both accountings"
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

    # ------------------------------------------------------------------------------------------
    # Ticket 18.  Three new expectations and four disagreement bands, each of which has to be
    # able to FAIL: a check that cannot reject the wrong fixture is not a check.
    # ------------------------------------------------------------------------------------------
    def refuses(label, var_bytes, names, expect, fixed=()):
        try:
            classify(var_bytes, names, expect=expect, fixed_bytes=fixed)
        except NotAssertable:
            return
        failures.append(f"{label}: classify accepted a fixture it must refuse "
                        f"({var_bytes}, expect={expect})")

    refuses("a gate-band row claimed as an assertable OOS row",
            [T18_GATE_BAND_LO, T18_TAG], T18_SCHEMA_C, "oos")
    refuses("a gate-band row claimed as an inline row",
            [T18_GATE_BAND_LO, T18_TAG], T18_SCHEMA_C, "inline")
    refuses("an agreeing row claimed as disputed",
            [T18_GATE_OOS_BOTH, T18_TAG], T18_SCHEMA_C, "disputed")
    refuses("a row that ends below the gate claimed as candidates-exhausted",
            [T18_TRANSITION_OOS, T18_TAG], T18_SCHEMA_C, "oos-exhausted")
    refuses("a candidates-exhausted row claimed as an ordinary OOS row",
            [T18_FLOOR_PAYLOAD, T18_FLOOR_BELOW], T18_SCHEMA_FLOOR, "oos", (T18_FLOOR_FILLER,))
    refuses("an unknown expectation", [T18_TRANSITION_OOS, T18_TAG], T18_SCHEMA_C, "whatever")

    # Every band is searched, and every ticket-18 fixture that claims to sit outside one does.
    gate_band = band_of(T18_SCHEMA_C, lambda n: [n, T18_TAG], 3000, 4400)
    check("the record-gate band for schema C", gate_band, (T18_GATE_BAND_LO, T18_GATE_BAND_HI))
    check("the largest record inline under both is one byte below the band",
          T18_GATE_INLINE_BOTH, gate_band[0] - 1)
    check("the smallest record demoted under both is one byte above the band",
          T18_GATE_OOS_BOTH, gate_band[1] + 1)
    floor_band = band_of(T18_SCHEMA_FLOOR, lambda n: [T18_FLOOR_PAYLOAD, n], 1, 64,
                         (T18_FLOOR_FILLER,))
    check("the eligibility-floor band", floor_band, (16, 23))
    check("the sub-floor fixture is one byte below the band", T18_FLOOR_BELOW, floor_band[0] - 1)
    check("the above-floor fixture is one byte above the band", T18_FLOOR_ABOVE, floor_band[1] + 1)
    check("the band fixture is inside the band",
          floor_band[0] <= T18_FLOOR_BAND <= floor_band[1], True)
    hp, hn = ob.OOS_RECORD_HEADER_SIZE_PINNED, ob.OOS_RECORD_HEADER_SIZE_NORMATIVE
    chunk_band = [n for n in range(16200, 16400) if chunks(n, hp) != chunks(n, hn)]
    check("the single-to-multi chunk band", (min(chunk_band), max(chunk_band)),
          (T18_CHUNK_BAND_LO, T18_CHUNK_BAND_HI))
    check("one chunk under both headers", (chunks(T18_CHUNK_ONE_BOTH, hp),
                                           chunks(T18_CHUNK_ONE_BOTH, hn)), (1, 1))
    check("two chunks under both headers", (chunks(T18_CHUNK_TWO_BOTH, hp),
                                            chunks(T18_CHUNK_TWO_BOTH, hn)), (2, 2))
    check("three chunks under both headers", (chunks(T18_CHUNK_THREE_BOTH, hp),
                                              chunks(T18_CHUNK_THREE_BOTH, hn)), (3, 3))
    check("the normative chunk function is not off by one either",
          (chunks(T18_CHUNK_BAND_LO - 1, hn), chunks(T18_CHUNK_BAND_LO, hn)), (1, 2))

    maxslot = ob.heap_maxslotted_reclength(PAGE_SIZE)

    def big_rejected(f_bytes, accounting):
        dem, after, _g = demoted_under([T18_BIGONE_VARBIT], accounting, (f_bytes,))
        return bool(dem) and after > maxslot
    big_band = [f for f in range(16100, 16250)
                if big_rejected(f, "pinned") != big_rejected(f, "normative")]
    check("the OOS + bigone band", (min(big_band), max(big_band)),
          (T18_BIGONE_BAND_LO, T18_BIGONE_BAND_HI))
    check("the accepted bigone neighbour is accepted under both",
          (big_rejected(T18_BIGONE_ACCEPTED, "pinned"),
           big_rejected(T18_BIGONE_ACCEPTED, "normative")), (False, False))
    check("the rejected bigone fixture is rejected under both",
          (big_rejected(T18_BIGONE_REJECTED, "pinned"),
           big_rejected(T18_BIGONE_REJECTED, "normative")), (True, True))
    check("the non-OOS bigone neighbour carries no OOS value at all",
          bool(demoted_under([T18_NONOOS_SMALL], "pinned", (T18_NONOOS_FILLER,))[0])
          or bool(demoted_under([T18_NONOOS_SMALL], "normative", (T18_NONOOS_FILLER,))[0]), False)
    check("and it really is above the bigone threshold",
          demoted_under([T18_NONOOS_SMALL], "pinned", (T18_NONOOS_FILLER,))[1] > maxslot, True)

    # NULL is not an empty value, and neither is ever a candidate.
    check("a NULL variable column occupies no payload bytes", var_disk(None), 0)
    check("a zero-length value still carries its length prefix", var_disk(0), 4)
    for label, n in (("NULL", None), ("zero-length", 0)):
        for acc in ("pinned", "normative"):
            dem, _a, _g = demoted_under([T18_TRANSITION_OOS, n, 0, T18_TAG], acc)
            check(f"a {label} column is never demoted ({acc})", 1 in dem or 2 in dem, False)

    # Ten or more: exactly the twelve largest move, under both accountings.
    for acc in ("pinned", "normative"):
        dem, _a, _g = demoted_under(T18_WIDE_SIZES, acc)
        check(f"rep10 demotes twelve attributes ({acc})", len(dem), 12)
        check(f"rep10 demotes the twelve largest ({acc})", list(dem), list(range(12)))
    check("rep10 is ten or more, which is what OOS-REP-10 asks", len(T18_WIDE_SIZES) >= 12, True)
    check("rep10's sizes are all distinct, so largest-first is a total order",
          len(set(T18_WIDE_SIZES)), len(T18_WIDE_SIZES))

    # Largest-first is only evidenced if the checker's payload sum can tell the two orders apart.
    def sumlen_of(sizes):
        return sum(varbit(n) + chunks(n, hp) * hp for n in sizes)
    u_pin, _a, _g = demoted_under(T18_ORDER_UNEQUAL, "pinned")
    check("rep02 unequal: exactly one column moves", len(u_pin), 1)
    check("rep02 unequal: it is the largest", u_pin, (0,))
    check("rep02 unequal: the payload sum tells the two orders apart",
          sumlen_of([T18_ORDER_UNEQUAL[0]]) != sumlen_of([T18_ORDER_UNEQUAL[1]]), True)
    t_pin, _a, _g = demoted_under(T18_ORDER_TIE, "pinned")
    check("rep02 tie: exactly one column moves", len(t_pin), 1)
    alternatives = [i for i in range(len(T18_ORDER_TIE))
                    if i not in t_pin and T18_ORDER_TIE[i] == T18_ORDER_TIE[t_pin[0]]]
    check("rep02 tie: there is exactly one alternative the tie-break could have taken",
          len(alternatives), 1)
    # Guarded, not assumed: ticket 44 F5 is the precedent -- a tie check that keeps passing
    # after the tie is edited away is worse than no check.  Making the two columns unequal makes
    # the count check above fail and skips the invariance below rather than raising IndexError.
    if len(alternatives) == 1:
        check("rep02 tie: the payload sum is the same either way, so the checker asserts no "
              "tie-break", sumlen_of([T18_ORDER_TIE[t_pin[0]]]),
              sumlen_of([T18_ORDER_TIE[alternatives[0]]]))
    c_pin, _a, _g = demoted_under(T18_ORDER_CASCADE, "pinned")
    check("rep02 cascade: two columns move and the third-largest stays", list(c_pin), [0, 1])

    # VOT width: the two-column pair straddles OR_MAX_BYTE, and demotion narrows the entries back.
    def vot_of(var_bytes, fixed=()):
        payload = INT_DISK + sum(fixed) + sum(var_disk(n) for n in var_bytes)
        return ob.header_size(1 + len(fixed), len(var_bytes), payload)[1]
    check("rep11 one-byte VOT fixture", vot_of(T18_VOT_ONE_BYTE), 1)
    check("rep11 two-byte VOT fixture", vot_of(T18_VOT_TWO_BYTE), 2)
    check("rep11 the two differ by one byte of `b`, not by anything else",
          (T18_VOT_ONE_BYTE[0], T18_VOT_TWO_BYTE[0]), (40, 40))
    check("rep11 the VOT is two bytes wide before demotion",
          vot_of([T18_TRANSITION_OOS, T18_VOT_NARROW_TAG]), 2)
    check("rep11 and one byte wide after it",
          row_layout([T18_TRANSITION_OOS, T18_VOT_NARROW_TAG], ob.gate_pinned(PAGE_SIZE),
                     ob.OR_OOS_INLINE_SIZE_PINNED)[2], 1)
    check("rep11 the narrowing is not an artefact of the pinned stub",
          row_layout([T18_TRANSITION_OOS, T18_VOT_NARROW_TAG], ob.target_normative(PAGE_SIZE),
                     ob.OR_OOS_INLINE_SIZE_NORMATIVE)[2], 1)
    check("an OOS-bearing record never reaches four-byte VOT entries at 16 KiB",
          ob.heap_maxslotted_reclength(PAGE_SIZE) <= ob.OR_MAX_SHORT, True)

    # Every ticket-18 fixture is the kind its case claims.  This is the same gate `main()` runs,
    # repeated here so `--self-test` alone is enough to refuse a bad fixture table.
    for label, names, var_bytes, expect, want, fixed in FIXTURES_T18:
        try:
            kind, demoted, _tie = classify(var_bytes, names, expect=expect, fixed_bytes=fixed)
        except NotAssertable as exc:
            failures.append(f"{label}: {exc}")
            continue
        if expect == "disputed":
            continue
        want_names = set()
        for w in (want or ["nothing"]):
            want_names |= set(w.split("|"))
        got = set(demoted) or {"nothing"}
        if not (got <= want_names and len(demoted) == len(want)):
            failures.append(f"{label}: demotes {sorted(got)}, expected {sorted(want_names)}")

    for f in failures:
        print(f"SELF-TEST FAIL  {f}")
    print("SELF-TEST:", "all checks pass" if not failures else f"{len(failures)} failure(s)")
    return 0 if not failures else 1


if __name__ == "__main__":
    if "--self-test" in sys.argv:
        sys.exit(self_test())
    sys.exit(main())
