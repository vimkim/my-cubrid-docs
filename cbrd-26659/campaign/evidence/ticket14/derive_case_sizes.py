#!/usr/bin/env python3
"""Derive the four payload sizes of the CBRD-26659 ticket 14 durability case.

The case uses ticket 11's schema A exactly -- CREATE TABLE t (id INT, v BIT VARYING) --
so every size comes from ticket 11's own derivation module rather than from a restated
arithmetic here. Each size is computed twice, once with the pinned accounting (gate
DB_PAGESIZE/4, 16-byte inline stub, 16-byte chunk header) and once with the normative one
(CBRD-27057 four-record target, CBRD-26950 24-byte stub and chunk header), and is accepted
only when both agree. That is what keeps the case's expectations assertable instead of
merely observed: a value on which the two accountings disagree lies in a Capability gap of
the pinned engine and must not be turned into an expectation (ticket 11 section 5.2).

Usage: derive_case_sizes.py [--page-size 16384]
"""
import argparse
import importlib.util
import sys
from pathlib import Path

TICKET11 = Path("/home/vimkim/gh/my-cubrid-docs/cbrd-26659/campaign/ticket11-evidence/oos_boundaries.py")

spec = importlib.util.spec_from_file_location("oos_boundaries", TICKET11)
ob = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ob)


def demoted(n, io, gate_fn, stub):
    return bool(ob.schema_a_layout(n, gate_fn(io), stub)[0])


def chunks(n, chunk_header, io):
    """Number of chunk records holding the serialized value of an N-byte BIT VARYING."""
    cap = ob.max_chunk_payload(io, chunk_header)
    length = ob.varbit_disk_len(n)
    return -(-length // cap)


def agreeing(name, predicate_pinned, predicate_normative, lo, hi):
    """Smallest N in [lo, hi] satisfying both accountings, with the disagreement band."""
    pin = ob.smallest_n(predicate_pinned, lo, hi)
    norm = ob.smallest_n(predicate_normative, lo, hi)
    band = (min(pin, norm), max(pin, norm) - 1) if pin != norm else None
    return pin, norm, band


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--page-size", type=int, default=16384, choices=[4096, 8192, 16384])
    args = ap.parse_args()
    io = args.page_size

    print(f"ticket 11 module : {TICKET11}")
    print(f"page size        : {io}")
    print(f"pinned gate      : {ob.gate_pinned(io)}  (heap_file.c:12350 DB_PAGESIZE/4)")
    print(f"normative target : {ob.target_normative(io)}  (OOS-CONTEXT section 1, CBRD-27057)")
    print(f"max chunk payload: pinned {ob.max_chunk_payload(io, ob.OOS_RECORD_HEADER_SIZE_PINNED)}, "
          f"normative {ob.max_chunk_payload(io, ob.OOS_RECORD_HEADER_SIZE_NORMATIVE)}")
    print(f"heap_Maxslotted_reclength: {ob.heap_maxslotted_reclength(io)}")
    print()

    # --- N_OOS1: smallest N that is demoted under BOTH accountings -------------------
    pin, norm, band = agreeing(
        "demotion",
        lambda n: demoted(n, io, ob.gate_pinned, ob.OR_OOS_INLINE_SIZE_PINNED),
        lambda n: demoted(n, io, ob.target_normative, ob.OR_OOS_INLINE_SIZE_NORMATIVE),
        1, 20000)
    n_oos1 = max(pin, norm)
    print(f"smallest N demoted, pinned    : {pin}")
    print(f"smallest N demoted, normative : {norm}")
    print(f"disputed demotion band        : {band}")
    print(f"N_OOS1 (single-chunk OOS row) : {n_oos1}  -- demoted under both")
    print()

    # --- N_INLINE: largest N that stays inline under BOTH ----------------------------
    n_inline = min(pin, norm) - 1
    print(f"N_INLINE (inline comparator)  : {n_inline}  -- inline under both")
    print()

    # --- N_OOS2: smallest N needing two chunks under BOTH ----------------------------
    pin2, norm2, band2 = agreeing(
        "chunk split",
        lambda n: chunks(n, ob.OOS_RECORD_HEADER_SIZE_PINNED, io) >= 2,
        lambda n: chunks(n, ob.OOS_RECORD_HEADER_SIZE_NORMATIVE, io) >= 2,
        1, 60000)
    n_oos2 = max(pin2, norm2)
    print(f"smallest N with 2 chunks, pinned    : {pin2}")
    print(f"smallest N with 2 chunks, normative : {norm2}")
    print(f"disputed split band                 : {band2}")
    print(f"N_OOS2 (multi-chunk OOS row)        : {n_oos2}  -- two chunks under both")
    print()

    # --- chunk counts and the pinned-only sumlen -------------------------------------
    rows = [("id=1 v", n_oos1), ("id=2 v", n_oos2), ("id=3 v", n_inline), ("id=4 v", n_oos1)]
    total_recs = 0
    total_sumlen = 0
    print("per-row placement after the committed INSERT (before any UPDATE or DELETE):")
    for label, n in rows:
        dem_p = demoted(n, io, ob.gate_pinned, ob.OR_OOS_INLINE_SIZE_PINNED)
        dem_n = demoted(n, io, ob.target_normative, ob.OR_OOS_INLINE_SIZE_NORMATIVE)
        assert dem_p == dem_n, f"{label}: accountings disagree on placement"
        c_p = chunks(n, ob.OOS_RECORD_HEADER_SIZE_PINNED, io) if dem_p else 0
        c_n = chunks(n, ob.OOS_RECORD_HEADER_SIZE_NORMATIVE, io) if dem_n else 0
        assert c_p == c_n, f"{label}: accountings disagree on chunk count"
        sumlen = (ob.varbit_disk_len(n) + c_p * ob.OOS_RECORD_HEADER_SIZE_PINNED) if dem_p else 0
        total_recs += c_p
        total_sumlen += sumlen
        print(f"  {label:8s} N={n:6d}  serialized={ob.varbit_disk_len(n):6d}  "
              f"{'OOS' if dem_p else 'inline':6s}  chunks={c_p}  pinned_sumlen={sumlen}")
    print()
    print(f"EXPECT_OOS_NUM_RECS      = {total_recs}   (agrees under both accountings -- assertable)")
    print(f"OBSERVE_OOS_RECS_SUMLEN  = {total_sumlen}   (pinned 16-byte chunk header only -- record, do not assert)")
    print()

    # --- shell variable block the case consumes -------------------------------------
    print("# --- shell variables ---")
    print(f"N_OOS1={n_oos1}")
    print(f"N_OOS2={n_oos2}")
    print(f"N_INLINE={n_inline}")
    print(f"EXPECT_OOS_NUM_RECS={total_recs}")
    print(f"OBSERVE_OOS_RECS_SUMLEN={total_sumlen}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
