#!/usr/bin/env python3
"""Derive OOS boundary values from the pinned engine's serialized record accounting.

Pinned engine: CUBRID feat/oos f4299ac0cd777a2a964c1f197ae5ebf9841a4936.
Every constant below is copied from that revision; the citation names the file and
symbol so a reader can re-check it with `git show <sha>:<path>`.

The script prints Markdown tables for 4, 8 and 16 KiB I/O pages. It reproduces the
engine's *arithmetic* (what heap_attrinfo_determine_disk_layout compares), not the
physical record image, so it is exact for the gate, the demotion stop, the chunk split
and the OOS+bigone rejection, which all use this arithmetic.
"""

# --- constants at f4299ac0c ---------------------------------------------------
# src/storage/storage_common.h: IO_MIN_PAGE_SIZE 4K, IO_MAX_PAGE_SIZE 16K, default 16K
IO_PAGE_SIZES = {"4 KiB": 4096, "8 KiB": 8192, "16 KiB": 16384}
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


def align(x, a):
    return (x + a - 1) // a * a


def align_below(x, a):
    return x // a * a


# --- page-level derived quantities --------------------------------------------
def db_pagesize(io):
    return io - RESERVED_SIZE_IN_PAGE


def spage_max_record_size(io):
    # slotted_page.c: SPAGE_DB_PAGESIZE - sizeof (SPAGE_HEADER) - sizeof (SPAGE_SLOT)
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


def fixed_bit_disk_len(nbits):
    """mr_data_lengthmem_bit: STR_SIZE (precision, RAW_BITS) = (nbits + 7) / 8, no padding."""
    return (nbits + 7) // 8


def bound_bit_bytes(n_fixed):
    return ((n_fixed + 31) >> 5) * 4


def var_table_size(n_var, offset_size):
    return 0 if n_var == 0 else align(offset_size * (n_var + 1), INT_ALIGNMENT)


def header_size(n_fixed, n_var, payload, is_mvcc=True):
    """heap_attrinfo_get_record_header_size: returns (header_size, offset_size)."""
    offset_size = OR_BYTE_SIZE
    hdr = (OR_MVCC_INSERT_HEADER_SIZE if is_mvcc else OR_NON_MVCC_HEADER_SIZE)
    hdr += var_table_size(n_var, offset_size) + bound_bit_bytes(n_fixed)
    if offset_size == OR_BYTE_SIZE and hdr + payload > OR_MAX_BYTE:
        hdr -= var_table_size(n_var, offset_size)
        offset_size = OR_SHORT_SIZE
        hdr += var_table_size(n_var, offset_size)
    if offset_size == OR_SHORT_SIZE and hdr + payload > OR_MAX_SHORT:
        hdr -= var_table_size(n_var, offset_size)
        offset_size = OR_INT_SIZE
        hdr += var_table_size(n_var, offset_size)
    return hdr, offset_size


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


def main():
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
        vals = [fn(io) for io in IO_PAGE_SIZES.values()]
        print(f"| {name} | `{src}` | " + " | ".join(f"{v:,}" for v in vals) + " |")

    print("\nEligibility floor (page-size independent): pinned `OR_OOS_INLINE_SIZE` = "
          f"{OR_OOS_INLINE_SIZE_PINNED} B (value must be > {OR_OOS_INLINE_SIZE_PINNED} B); "
          f"normative = {OR_OOS_INLINE_SIZE_NORMATIVE} B (value must be > {OR_OOS_INLINE_SIZE_NORMATIVE} B).")
    floor_pin = smallest_n(lambda n: varbit_disk_len(n) > OR_OOS_INLINE_SIZE_PINNED, 1, 64)
    floor_norm = smallest_n(lambda n: varbit_disk_len(n) > OR_OOS_INLINE_SIZE_NORMATIVE, 1, 64)
    print(f"For a BIT VARYING value of N logical bytes the serialized size is ALIGN(1 + N, 4) while N < 32, so the "
          f"floor in logical bytes is: pinned N >= {floor_pin} eligible (N = {floor_pin - 1} is not); "
          f"normative N >= {floor_norm} eligible (N = {floor_norm - 1} is not). Values with N in "
          f"[{floor_pin}, {floor_norm - 1}] are demoted by the pinned engine but must stay inline under the normative rule.")
    print(f"VOT width (page-size independent): 1-byte entries while header+payload <= {OR_MAX_BYTE}; "
          f"2-byte while <= {OR_MAX_SHORT}; 4-byte above. Since every OOS-bearing record must be <= "
          "heap_Maxslotted_reclength (max 16,236 at 16 KiB), an OOS-bearing record never uses 4-byte VOT entries.")

    # Schema A: (id INT, v BIT VARYING) -- one fixed INT, one variable column.
    print("\n## Schema A: `CREATE TABLE a (id INT, v BIT VARYING)` -- N = payload bytes of v\n")
    print("| Boundary | 4 KiB | 8 KiB | 16 KiB |")
    print("|---|---:|---:|---:|")

    def a_layout(io, n, gate, stub):
        return layout([4], [varbit_disk_len(n)], gate, stub)

    def first_demote(io, gate, stub):
        return smallest_n(lambda n: bool(a_layout(io, n, gate, stub)[0]), 1, 20000)

    def first_multichunk(io, hdr):
        cap = max_chunk_payload(io, hdr)
        return smallest_n(lambda n: varbit_disk_len(n) > cap, 1, 40000)

    def first_2byte_vot(io):
        return smallest_n(lambda n: header_size(1, 1, 4 + varbit_disk_len(n))[1] == OR_SHORT_SIZE, 1, 1000)

    cols = list(IO_PAGE_SIZES.values())
    print("| Smallest N demoted, pinned gate (DB_PAGESIZE/4, 16 B stub) | " +
          " | ".join(f"{first_demote(io, gate_pinned(io), OR_OOS_INLINE_SIZE_PINNED):,}" for io in cols) + " |")
    print("| Smallest N demoted, normative target (four-record, 24 B stub) | " +
          " | ".join(f"{first_demote(io, target_normative(io), OR_OOS_INLINE_SIZE_NORMATIVE):,}" for io in cols) + " |")
    print("| Smallest N needing 2 chunks, pinned 16 B chunk header | " +
          " | ".join(f"{first_multichunk(io, OOS_RECORD_HEADER_SIZE_PINNED):,}" for io in cols) + " |")
    print("| Smallest N needing 2 chunks, normative 24 B chunk header | " +
          " | ".join(f"{first_multichunk(io, OOS_RECORD_HEADER_SIZE_NORMATIVE):,}" for io in cols) + " |")
    print("| Smallest N switching VOT to 2-byte entries (any page size) | " +
          " | ".join(f"{first_2byte_vot(io)}" for io in cols) + " |")

    # Schema B: (id INT, f BIT(n), v BIT VARYING(...)) -- fixed BIT pushes inline size past bigone.
    print("\n## Schema B: `CREATE TABLE b (id INT, f BIT(8*F), v BIT VARYING)` with v = 64 B -- F = fixed bytes\n")
    print("| Boundary | 4 KiB | 8 KiB | 16 KiB |")
    print("|---|---|---|---|")

    def b_rejected(io, f_bytes, stub):
        demoted, inline_after, _ = layout([4, f_bytes], [varbit_disk_len(64)], gate_pinned(io), stub)
        return bool(demoted) and inline_after > heap_maxslotted_reclength(io)

    print("| Smallest F rejected with ER_HEAP_OOS_OVERPASS_MAXOBJ_SIZE (-1382), pinned 16 B stub | " +
          " | ".join(f"{smallest_n(lambda f: b_rejected(io, f, OR_OOS_INLINE_SIZE_PINNED), 1, 20000):,}"
                     for io in cols) + " |")
    print("| Same, normative 24 B stub | " +
          " | ".join(f"{smallest_n(lambda f: b_rejected(io, f, OR_OOS_INLINE_SIZE_NORMATIVE), 1, 20000):,}"
                     for io in cols) + " |")
    print("| inline_size_after_oos at that F (pinned) = F + 60 | " +
          " | ".join(f"{smallest_n(lambda f: b_rejected(io, f, OR_OOS_INLINE_SIZE_PINNED), 1, 20000) + 60:,}"
                     for io in cols) + " |")

    # Worked derivation for 16 KiB schema A at the pinned gate.
    io = IO_PAGE_SIZES["16 KiB"]
    print("\n## Worked derivation, schema A, 16 KiB, pinned engine\n")
    print("```text")
    print(f"header  = OR_MVCC_INSERT_HEADER_SIZE 16 + VOT ALIGN(1*(1+1),4)=4 + bound bits 4 = 24")
    print(f"payload = INT 4 + varbit_len(N) where varbit_len(N) = ALIGN(5 + N, 4) for N >= 32")
    print(f"gate    : header + payload + mvcc_extra 16 > DB_PAGESIZE/4 = {gate_pinned(io):,}")
    print(f"        : 24 + 4 + L + 16 > {gate_pinned(io):,}  <=>  L > {gate_pinned(io) - 44:,}  <=>  L >= {align(gate_pinned(io) - 44 + 1, 4):,}")
    n_pin = first_demote(io, gate_pinned(io), OR_OOS_INLINE_SIZE_PINNED)
    print(f"        : ALIGN(5 + N, 4) >= {align(gate_pinned(io) - 44 + 1, 4):,}  <=>  N >= {n_pin:,}   (N = {n_pin - 1:,} stays inline)")
    n_norm = first_demote(io, target_normative(io), OR_OOS_INLINE_SIZE_NORMATIVE)
    print(f"normative target {target_normative(io):,}: N >= {n_norm:,}; disputed band N in [{n_norm:,}, {n_pin - 1:,}] "
          "(normative demotes, pinned keeps inline)")
    print("```")


if __name__ == "__main__":
    main()
