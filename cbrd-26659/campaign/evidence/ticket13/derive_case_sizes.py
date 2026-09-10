#!/usr/bin/env python3
"""Derive and justify the sizes of the ticket-13 tracer-bullet SQL case.

The case is `sql/_36_guava/cbrd_26659/cases/cbrd_26659_oos_rep02_largest_first.sql`
in the public `testcases` repository on branch CBRD-26659-oos-testcases-handover.

Everything printed here is computed from the pinned engine's serialized record
accounting as captured by ticket 11's `oos_boundaries.py` (same directory tree),
never from an engine run.  It answers the two questions the campaign spec demands
before an expectation may be asserted:

  1. Do the pinned gate (DB_PAGESIZE/4, 4,086 B at 16 KiB) and the normative
     four-record target (CBRD-27057, 4,060 B at 16 KiB) *agree* on which columns
     of each fixture row are demoted?  Only then is the placement assertable
     (OOS-REP-02 / OOS-REP-01 authority notes).
  2. Does the 16-byte pinned inline stub versus the 24-byte normative stub
     (CBRD-26950) change that answer?  Only then is it assertable.

If both accountings agree, the case's expected chunk count and chunk payload sum
are a *discriminating* oracle for largest-first demotion: demoting the wrong
column yields a different `Oos_recs_sumlen`.

Usage: python3 derive_case_sizes.py
Exit status 0 when every fixture row is assertable under both accountings.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "ticket11-evidence"))
import oos_boundaries as ob  # noqa: E402

PAGE_SIZE = 16384  # the fast tier's default page size (spec: Execution tiers)
INT_DISK = ob.INT_DISK_SIZE

# The case fixture: schema (id INT PRIMARY KEY, big BIT VARYING, small BIT VARYING).
# Distinct byte patterns per value, per the spec's test-data conventions.
FIXTURE = [
    # row id, big N bytes, big pattern, small N bytes, small pattern, intent
    (1, 3000, "AA", 1200, "BB", "OOS-backed: record over both gates, only `big` demoted"),
    (2, 1000, "CC", 500, "DD", "inline comparator: record under both gates, nothing demoted"),
]

ACCOUNTINGS = (
    # label, gate, stub
    ("pinned    (gate DB_PAGESIZE/4, 16 B stub)", ob.gate_pinned, ob.OR_OOS_INLINE_SIZE_PINNED,
     ob.OOS_RECORD_HEADER_SIZE_PINNED),
    ("normative (CBRD-27057 target, 24 B stub)", ob.target_normative, ob.OR_OOS_INLINE_SIZE_NORMATIVE,
     ob.OOS_RECORD_HEADER_SIZE_NORMATIVE),
)


def row_layout(big_n, small_n, gate, stub):
    """Which of (big, small) the engine demotes, and the resulting inline size."""
    var_sizes = [ob.varbit_disk_len(big_n), ob.varbit_disk_len(small_n)]
    demoted, inline_after, offset_size = ob.layout([INT_DISK], var_sizes, gate, stub)
    return demoted, inline_after, offset_size, var_sizes


def main():
    print(f"# Ticket 13 case-size derivation (page size {PAGE_SIZE} B)\n")
    print(f"pinned record gate      = {ob.gate_pinned(PAGE_SIZE):>6} B  (heap_file.c:12350,12383)")
    print(f"normative record target = {ob.target_normative(PAGE_SIZE):>6} B  (OOS-CONTEXT §1, CBRD-27057)")
    print(f"max single-chunk payload (pinned)    = {ob.max_chunk_payload(PAGE_SIZE, ob.OOS_RECORD_HEADER_SIZE_PINNED):>6} B")
    print(f"max single-chunk payload (normative) = {ob.max_chunk_payload(PAGE_SIZE, ob.OOS_RECORD_HEADER_SIZE_NORMATIVE):>6} B")
    print()

    assertable = True
    chunk_totals = {}
    for label, gate_fn, stub, chunk_hdr in ACCOUNTINGS:
        gate = gate_fn(PAGE_SIZE)
        max_chunk = ob.max_chunk_payload(PAGE_SIZE, chunk_hdr)
        print(f"## {label}")
        n_recs = 0
        sumlen = 0
        for rid, big_n, big_pat, small_n, small_pat, intent in FIXTURE:
            demoted, inline_after, off, var_sizes = row_layout(big_n, small_n, gate, stub)
            names = ["big", "small"]
            demoted_names = [names[i] for i in demoted]
            for i in demoted:
                chunks = -(-var_sizes[i] // max_chunk)  # ceil
                n_recs += chunks
                sumlen += var_sizes[i] + chunks * chunk_hdr
            print(f"  row {rid}: DISK_SIZE(big)={var_sizes[0]:>5}  DISK_SIZE(small)={var_sizes[1]:>5}"
                  f"  VOT width={off}  record before={sum(var_sizes) + INT_DISK + 16 + ob.bound_bit_bytes(1) + ob.var_table_size(2, off) + ob.MVCC_EXTRA:>5}"
                  f"  demoted={demoted_names or ['-']}  record after={inline_after:>5}")
        print(f"  class totals: Oos_num_recs={n_recs}  Oos_recs_sumlen={sumlen}")
        chunk_totals[label] = (n_recs, sumlen)
        print()

    # --- assertability: both accountings must agree, row by row -------------------
    print("## Assertability")
    for rid, big_n, big_pat, small_n, small_pat, intent in FIXTURE:
        results = []
        for label, gate_fn, stub, _hdr in ACCOUNTINGS:
            demoted, _inline, _off, _vs = row_layout(big_n, small_n, gate_fn(PAGE_SIZE), stub)
            results.append(tuple(demoted))
        agree = len(set(results)) == 1
        assertable &= agree
        print(f"  row {rid}: pinned demotes {list(results[0]) or '-'}, "
              f"normative demotes {list(results[1]) or '-'} -> "
              f"{'ASSERTABLE' if agree else 'NOT ASSERTABLE (disputed band)'}   [{intent}]")

    pinned_recs, pinned_sumlen = chunk_totals[ACCOUNTINGS[0][0]]
    norm_recs, norm_sumlen = chunk_totals[ACCOUNTINGS[1][0]]
    print()
    print("## Activation-evidence expectation (SHOW HEAP OOS OF the case's own class)")
    print(f"  Oos_num_recs    = {pinned_recs} under both accountings"
          if pinned_recs == norm_recs else
          f"  Oos_num_recs    pinned {pinned_recs} vs normative {norm_recs}: NOT assertable")
    print(f"  Oos_recs_sumlen = {pinned_sumlen} at the pin "
          f"(normative {norm_sumlen}; differs only by the 24-byte chunk header, "
          f"a Capability gap of the pin, so only the chunk *count* is asserted)")

    # discriminating power: what a smallest-first engine would show instead
    print()
    print("## Discriminating power of Oos_recs_sumlen (why this proves largest-first)")
    for label, gate_fn, stub, chunk_hdr in ACCOUNTINGS[:1]:
        gate = gate_fn(PAGE_SIZE)
        rid, big_n, _bp, small_n, _sp, _i = FIXTURE[0]
        vs = [ob.varbit_disk_len(big_n), ob.varbit_disk_len(small_n)]
        print(f"  largest-first  (correct): demote big   -> sumlen {vs[0] + chunk_hdr}")
        print(f"  smallest-first (defect) : demote small -> sumlen {vs[1] + chunk_hdr}")
        # a smallest-first engine would also stop after one demotion:
        hdr, off = ob.header_size(1, 2, INT_DISK + stub + vs[0], True)
        print(f"    (a smallest-first engine also stops after one demotion: record after = "
              f"{hdr + INT_DISK + stub + vs[0] + ob.MVCC_EXTRA} <= {gate}, so the chunk *count* "
              f"alone cannot tell them apart -- the payload sum can)")

    print()
    if assertable:
        print("RESULT: every fixture row is assertable under both accountings.")
        return 0
    print("RESULT: at least one fixture row falls in a disputed band; do not assert it.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
