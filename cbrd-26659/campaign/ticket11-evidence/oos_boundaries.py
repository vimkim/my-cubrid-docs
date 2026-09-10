#!/usr/bin/env python3
"""Derive OOS boundary values from the pinned engine's serialized record accounting.

Pinned engine: CUBRID feat/oos f4299ac0cd777a2a964c1f197ae5ebf9841a4936.
Every constant below is copied from that revision; the citation names the file and
symbol so a reader can re-check it with `git show <sha>:<path>`.

Usage:
    oos_boundaries.py               print the Markdown boundary tables
    oos_boundaries.py --probe-rows  print the per-page-size rows probe_boundaries.sh consumes

The script reproduces the engine's *arithmetic* (what heap_attrinfo_determine_disk_layout
compares), not the physical record image, so it is exact for the gate, the demotion stop,
the chunk split and the OOS+bigone rejection, which all use this arithmetic.
"""
import sys

# --- constants at f4299ac0c ---------------------------------------------------
# src/storage/storage_common.h: IO_MIN_PAGE_SIZE 4K, IO_MAX_PAGE_SIZE 16K, default 16K
IO_PAGE_SIZES = {"4 KiB": 4096, "8 KiB": 8192, "16 KiB": 16384}
PROBE_TAGS = {"4 KiB": ("4k", "4K"), "8 KiB": ("8k", "8K"), "16 KiB": ("16k", "16K")}
# src/storage/file_io.h: FILEIO_PAGE_RESERVED = LSA 8 + pageid 4 + volid 2 + ptype 1 + pflag 1
#   + p_reserve_1 4 + p_reserve_2 4 + tde_nonce 8 = 32; FILEIO_PAGE_WATERMARK = LSA 8
# src/storage/storage_common.c: RESERVED_SIZE_IN_PAGE = 32 + 8 = 40; DB_PAGESIZE = IO_PAGESIZE - 40
RESERVED_SIZE_IN_PAGE = 32 + 8
# src/storage/slotted_page.h: struct spage_header = 32 bytes (asserted % 8 == 0), spage_slot = 4
SPAGE_HEADER_SIZE = 32
SPAGE_SLOT_SIZE = 4
# src/storage/heap_file.c: struct heap_chain = OID 8 + VPID 8 + VPID 8 + MVCCID 8 + INT32 4 -> 40 (8-aligned)
HEAP_CHAIN_SIZE = 40
# src/storage/heap_file.h: HEAP_MAX_ALIGN = INT_ALIGNMENT = 4
HEAP_MAX_ALIGN = 4
# src/storage/oos_file.cpp: OOS_ALIGNMENT = MAX_ALIGNMENT = 8
OOS_ALIGNMENT = 8
# src/storage/oos_file.hpp: oos_record_header = int 4 + int 4 + OID 8 = 16 (pinned)
OOS_RECORD_HEADER_SIZE_PINNED = 16
# normative context (2026-09-09 identity layout): chunk header 24 (adds 8-byte LOG_LSA stamp)
OOS_RECORD_HEADER_SIZE_NORMATIVE = 24
# src/base/object_representation.h: OR_OOS_INLINE_SIZE = OR_OID_SIZE 8 + OR_BIGINT_SIZE 8 = 16 (pinned)
OR_OOS_INLINE_SIZE_PINNED = 16
# normative context: stub = head OID 8 + full length 8 + packed identity stamp 8 = 24
OR_OOS_INLINE_SIZE_NORMATIVE = 24
# src/base/object_representation_constants.h
OR_MVCC_INSERT_HEADER_SIZE = 16
OR_MVCC_MAX_HEADER_SIZE = 32
OR_NON_MVCC_HEADER_SIZE = 8
OR_MAX_BYTE = 127
OR_MAX_SHORT = 32767
OR_BYTE_SIZE, OR_SHORT_SIZE, OR_INT_SIZE = 1, 2, 4
INT_ALIGNMENT = 4
# heap_attrinfo_determine_disk_layout: mvcc_extra = OR_MVCC_MAX_HEADER_SIZE - OR_MVCC_INSERT_HEADER_SIZE
MVCC_EXTRA = OR_MVCC_MAX_HEADER_SIZE - OR_MVCC_INSERT_HEADER_SIZE
# heap_attrinfo_get_record_header_size widens the VOT entry when header + payload exceeds these
VOT_WIDENING = ((OR_BYTE_SIZE, OR_MAX_BYTE, OR_SHORT_SIZE), (OR_SHORT_SIZE, OR_MAX_SHORT, OR_INT_SIZE))
# fixed INT column disk size (tp_domain_disk_size)
INT_DISK_SIZE = 4
# probe payload used for the OOS+bigone rejection schema (schema B)
SCHEMA_B_VARBIT_BYTES = 64


def align(x, a):
    return (x + a - 1) // a * a


def align_below(x, a):
    return x // a * a


# --- page-level derived quantities --------------------------------------------
def db_pagesize(io):
    return io - RESERVED_SIZE_IN_PAGE


def spage_max_record_size(io):
    # slotted_page.c:841: SPAGE_DB_PAGESIZE - sizeof (SPAGE_HEADER) - sizeof (SPAGE_SLOT)
    return db_pagesize(io) - SPAGE_HEADER_SIZE - SPAGE_SLOT_SIZE


def heap_nonheader_page_capacity(io):
    # heap_file.c:27567: spage_max_record_size () - sizeof (HEAP_CHAIN)
    return spage_max_record_size(io) - HEAP_CHAIN_SIZE


def heap_maxslotted_reclength(io):
    # heap_file.c:3714 heap_manager_initialize:
    # DB_ALIGN_BELOW (spage_max_record_size () - DB_ALIGN (sizeof (HEAP_CHAIN), HEAP_MAX_ALIGN)
    #                 - 8 * SPAGE_SLOT_SIZE, HEAP_MAX_ALIGN)
    return align_below(spage_max_record_size(io) - align(HEAP_CHAIN_SIZE, HEAP_MAX_ALIGN)
                       - 8 * SPAGE_SLOT_SIZE, HEAP_MAX_ALIGN)


def gate_pinned(io):
    # heap_file.c:12350/12383: DB_PAGESIZE / 4 (integer division)
    return db_pagesize(io) // 4


def target_normative(io):
    # OOS-CONTEXT.md §1 (CBRD-27057): ALIGN_BELOW((cap - 4 * SPAGE_SLOT_SIZE) / 4, HEAP_MAX_ALIGN)
    cap = heap_nonheader_page_capacity(io)
    return align_below((cap - 4 * SPAGE_SLOT_SIZE) // 4, HEAP_MAX_ALIGN)


def max_chunk_payload(io, header_size):
    # oos_file.cpp:3249 oos_get_max_chunk_size_within_page:
    # DB_ALIGN_BELOW (spage_max_record_size (), OOS_ALIGNMENT) - sizeof (OOS_RECORD_HEADER)
    return align_below(spage_max_record_size(io), OOS_ALIGNMENT) - header_size


# --- record accounting (mirrors heap_attrinfo_get_record_{payload,header}_size) --
def varbit_disk_len(nbytes):
    """or_varbit_length_internal (bitlen, INT_ALIGNMENT): 1-byte prefix if bitlen < 0xFF else 5,
    plus (bitlen+7)/8 payload bytes, rounded up to 4."""
    bitlen = nbytes * 8
    prefix = 1 if bitlen < 0xFF else 1 + OR_INT_SIZE
    return align(prefix + (bitlen + 7) // 8, INT_ALIGNMENT)


def bound_bit_bytes(n_fixed):
    return ((n_fixed + 31) >> 5) * 4


def var_table_size(n_var, offset_size):
    return 0 if n_var == 0 else align(offset_size * (n_var + 1), INT_ALIGNMENT)


def header_size(n_fixed, n_var, payload, is_mvcc=True):
    """heap_attrinfo_get_record_header_size: returns (header_size, offset_size)."""
    offset_size = OR_BYTE_SIZE
    base = (OR_MVCC_INSERT_HEADER_SIZE if is_mvcc else OR_NON_MVCC_HEADER_SIZE) + bound_bit_bytes(n_fixed)
    for current, limit, wider in VOT_WIDENING:
        if offset_size == current and base + var_table_size(n_var, offset_size) + payload > limit:
            offset_size = wider
    return base + var_table_size(n_var, offset_size), offset_size


def layout(fixed_sizes, var_sizes, gate, stub, is_mvcc=True):
    """Reproduce heap_attrinfo_determine_disk_layout (DEFAULT storage hints only).
    Returns (demoted_indices, inline_size_after_oos_incl_mvcc_extra, offset_size)."""
    n_fixed, n_var = len(fixed_sizes), len(var_sizes)
    payload = sum(fixed_sizes) + sum(var_sizes)
    hdr, off = header_size(n_fixed, n_var, payload, is_mvcc)
    extra = MVCC_EXTRA if is_mvcc else 0
    demoted = []
    if hdr + payload + extra > gate:
        cands = sorted([(sz, i) for i, sz in enumerate(var_sizes) if sz > stub],
                       key=lambda t: (-t[0], -t[1]))
        for sz, i in cands:
            if hdr + payload + extra <= gate:
                break
            demoted.append(i)
            payload -= sz
            payload += stub
        hdr, off = header_size(n_fixed, n_var, payload, is_mvcc)
    # heap_attrinfo_transform_to_disk_internal adds the same MVCC extra before heap_is_big_length
    return demoted, hdr + payload + extra, off


def smallest_n(pred, lo, hi):
    """Smallest integer n in [lo, hi] with pred(n) true, assuming pred is monotone."""
    while lo < hi:
        mid = (lo + hi) // 2
        if pred(mid):
            hi = mid
        else:
            lo = mid + 1
    return lo if pred(lo) else None


# --- schema A: (id INT, v BIT VARYING); N = logical bytes of v ----------------------
def schema_a_layout(n, gate, stub):
    return layout([INT_DISK_SIZE], [varbit_disk_len(n)], gate, stub)


def schema_a_first_demoted(io, gate_fn, stub):
    return smallest_n(lambda n: bool(schema_a_layout(n, gate_fn(io), stub)[0]), 1, 20000)


def schema_a_first_multichunk(io, chunk_header):
    cap = max_chunk_payload(io, chunk_header)
    return smallest_n(lambda n: varbit_disk_len(n) > cap, 1, 40000)


def schema_a_first_2byte_vot():
    # page-size independent: depends only on OR_MAX_BYTE and the record header
    return smallest_n(lambda n: header_size(1, 1, INT_DISK_SIZE + varbit_disk_len(n))[1] == OR_SHORT_SIZE, 1, 1000)


# --- schema B: (id INT, f BIT(8*F), v BIT VARYING(64 bytes)); F = fixed bytes ---------
def schema_b_layout(io, f_bytes, stub):
    return layout([INT_DISK_SIZE, f_bytes], [varbit_disk_len(SCHEMA_B_VARBIT_BYTES)], gate_pinned(io), stub)


def schema_b_first_rejected(io, stub):
    """Smallest F for which the demoted record still exceeds heap_Maxslotted_reclength."""
    def rejected(f_bytes):
        demoted, inline_after, _ = schema_b_layout(io, f_bytes, stub)
        return bool(demoted) and inline_after > heap_maxslotted_reclength(io)
    return smallest_n(rejected, 1, 20000)


def probe_row(label):
    """One row for probe_boundaries.sh: tag io gate_in gate_out norm ch1 ch2 fok frej gate_filler.
    gate_filler is the fixed-column byte count that alone pushes a record over the pinned gate."""
    io = IO_PAGE_SIZES[label]
    tag, io_flag = PROBE_TAGS[label]
    gate_out = schema_a_first_demoted(io, gate_pinned, OR_OOS_INLINE_SIZE_PINNED)
    norm = schema_a_first_demoted(io, target_normative, OR_OOS_INLINE_SIZE_NORMATIVE)
    ch2 = schema_a_first_multichunk(io, OOS_RECORD_HEADER_SIZE_PINNED)
    frej = schema_b_first_rejected(io, OR_OOS_INLINE_SIZE_PINNED)
    return (tag, io_flag, gate_out - 1, gate_out, norm, ch2 - 1, ch2, frej - 1, frej, gate_pinned(io))


def print_probe_rows():
    for label in ("16 KiB", "8 KiB", "4 KiB"):
        print(" ".join(str(x) for x in probe_row(label)))


def fmt_row(name, src, values):
    return f"| {name} | `{src}` | " + " | ".join(f"{v:,}" for v in values) + " |"


def main():
    ios = list(IO_PAGE_SIZES.values())
    print("## Page-level constants (pinned engine arithmetic)\n")
    print("| Quantity | Source | 4 KiB | 8 KiB | 16 KiB |")
    print("|---|---|---:|---:|---:|")
    rows = [
        ("IO_PAGESIZE", "createdb --db-page-size", lambda io: io),
        ("DB_PAGESIZE = IO - 40", "storage_common.c RESERVED_SIZE_IN_PAGE", db_pagesize),
        ("spage_max_record_size()", "slotted_page.c:841", spage_max_record_size),
        ("heap_nonheader_page_capacity()", "heap_file.c:27567", heap_nonheader_page_capacity),
        ("heap_Maxslotted_reclength (REC_BIGONE above this)", "heap_file.c:3714", heap_maxslotted_reclength),
        ("Record gate, pinned: DB_PAGESIZE / 4", "heap_file.c:12350,12383", gate_pinned),
        ("Record gate, normative four-record target", "OOS-CONTEXT §1 (CBRD-27057)", target_normative),
        ("Max single-chunk payload, pinned 16 B chunk header", "oos_file.cpp:3249",
         lambda io: max_chunk_payload(io, OOS_RECORD_HEADER_SIZE_PINNED)),
        ("Max single-chunk payload, normative 24 B chunk header", "OOS-CONTEXT §2 layout",
         lambda io: max_chunk_payload(io, OOS_RECORD_HEADER_SIZE_NORMATIVE)),
    ]
    for name, src, fn in rows:
        print(fmt_row(name, src, [fn(io) for io in ios]))

    floor_pin = smallest_n(lambda n: varbit_disk_len(n) > OR_OOS_INLINE_SIZE_PINNED, 1, 64)
    floor_norm = smallest_n(lambda n: varbit_disk_len(n) > OR_OOS_INLINE_SIZE_NORMATIVE, 1, 64)
    print("\nEligibility floor (page-size independent): pinned `OR_OOS_INLINE_SIZE` = "
          f"{OR_OOS_INLINE_SIZE_PINNED} B (value must be > {OR_OOS_INLINE_SIZE_PINNED} B); "
          f"normative = {OR_OOS_INLINE_SIZE_NORMATIVE} B (value must be > {OR_OOS_INLINE_SIZE_NORMATIVE} B).")
    print(f"For a BIT VARYING value of N logical bytes the serialized size is ALIGN(1 + N, 4) while N < 32, so the "
          f"floor in logical bytes is: pinned N >= {floor_pin} eligible (N = {floor_pin - 1} is not); "
          f"normative N >= {floor_norm} eligible (N = {floor_norm - 1} is not). Values with N in "
          f"[{floor_pin}, {floor_norm - 1}] are demoted by the pinned engine but must stay inline under the normative rule.")
    print(f"VOT width (page-size independent): 1-byte entries while header+payload <= {OR_MAX_BYTE}; "
          f"2-byte while <= {OR_MAX_SHORT}; 4-byte above. Since every OOS-bearing record must be <= "
          f"heap_Maxslotted_reclength (max {heap_maxslotted_reclength(max(ios)):,} at 16 KiB), an OOS-bearing record "
          "never uses 4-byte VOT entries.")

    print("\n## Schema A: `CREATE TABLE a (id INT, v BIT VARYING)` -- N = payload bytes of v\n")
    print("| Boundary | 4 KiB | 8 KiB | 16 KiB |")
    print("|---|---:|---:|---:|")
    print("| Smallest N demoted, pinned gate (DB_PAGESIZE/4, 16 B stub) | " +
          " | ".join(f"{schema_a_first_demoted(io, gate_pinned, OR_OOS_INLINE_SIZE_PINNED):,}" for io in ios) + " |")
    print("| Smallest N demoted, normative target (four-record, 24 B stub) | " +
          " | ".join(f"{schema_a_first_demoted(io, target_normative, OR_OOS_INLINE_SIZE_NORMATIVE):,}" for io in ios) + " |")
    print("| Smallest N needing 2 chunks, pinned 16 B chunk header | " +
          " | ".join(f"{schema_a_first_multichunk(io, OOS_RECORD_HEADER_SIZE_PINNED):,}" for io in ios) + " |")
    print("| Smallest N needing 2 chunks, normative 24 B chunk header | " +
          " | ".join(f"{schema_a_first_multichunk(io, OOS_RECORD_HEADER_SIZE_NORMATIVE):,}" for io in ios) + " |")
    print(f"| Smallest N switching VOT to 2-byte entries (any page size) | " +
          " | ".join(f"{schema_a_first_2byte_vot()}" for _ in ios) + " |")

    print(f"\n## Schema B: `CREATE TABLE b (id INT, f BIT(8*F), v BIT VARYING)` with v = {SCHEMA_B_VARBIT_BYTES} B "
          "-- F = fixed bytes\n")
    print("| Boundary | 4 KiB | 8 KiB | 16 KiB |")
    print("|---|---|---|---|")
    f_pin = [schema_b_first_rejected(io, OR_OOS_INLINE_SIZE_PINNED) for io in ios]
    f_norm = [schema_b_first_rejected(io, OR_OOS_INLINE_SIZE_NORMATIVE) for io in ios]
    inline_after_pin = [schema_b_layout(io, f, OR_OOS_INLINE_SIZE_PINNED)[1] for io, f in zip(ios, f_pin)]
    print("| Smallest F rejected with ER_HEAP_OOS_OVERPASS_MAXOBJ_SIZE (-1382), pinned 16 B stub | " +
          " | ".join(f"{f:,}" for f in f_pin) + " |")
    print("| Same, normative 24 B stub | " + " | ".join(f"{f:,}" for f in f_norm) + " |")
    print("| inline_size_after_oos at that F (pinned), one byte above heap_Maxslotted_reclength | " +
          " | ".join(f"{v:,}" for v in inline_after_pin) + " |")

    # Worked derivation for 16 KiB schema A at the pinned gate, computed from the constants above.
    io = IO_PAGE_SIZES["16 KiB"]
    hdr_a = OR_MVCC_INSERT_HEADER_SIZE + var_table_size(1, OR_BYTE_SIZE) + bound_bit_bytes(1)
    fixed_part = hdr_a + INT_DISK_SIZE + MVCC_EXTRA
    l_min_pin = align(gate_pinned(io) - fixed_part + 1, INT_ALIGNMENT)
    n_pin = schema_a_first_demoted(io, gate_pinned, OR_OOS_INLINE_SIZE_PINNED)
    n_norm = schema_a_first_demoted(io, target_normative, OR_OOS_INLINE_SIZE_NORMATIVE)
    print("\n## Worked derivation, schema A, 16 KiB, pinned engine\n")
    print("```text")
    print(f"header  = OR_MVCC_INSERT_HEADER_SIZE {OR_MVCC_INSERT_HEADER_SIZE} + VOT ALIGN(1*(1+1),4)="
          f"{var_table_size(1, OR_BYTE_SIZE)} + bound bits {bound_bit_bytes(1)} = {hdr_a}")
    print(f"payload = INT {INT_DISK_SIZE} + varbit_len(N) where varbit_len(N) = ALIGN(5 + N, 4) for N >= 32")
    print(f"gate    : header + payload + mvcc_extra {MVCC_EXTRA} > DB_PAGESIZE/4 = {gate_pinned(io):,}")
    print(f"        : {hdr_a} + {INT_DISK_SIZE} + L + {MVCC_EXTRA} > {gate_pinned(io):,}  <=>  "
          f"L > {gate_pinned(io) - fixed_part:,}  <=>  L >= {l_min_pin:,}")
    print(f"        : ALIGN(5 + N, 4) >= {l_min_pin:,}  <=>  N >= {n_pin:,}   (N = {n_pin - 1:,} stays inline)")
    print(f"normative target {target_normative(io):,}: N >= {n_norm:,}; disputed band N in [{n_norm:,}, {n_pin - 1:,}] "
          "(normative demotes, pinned keeps inline)")
    print("```")


if __name__ == "__main__":
    if "--probe-rows" in sys.argv[1:]:
        print_probe_rows()
    else:
        main()
