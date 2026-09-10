## Page-level constants (pinned engine arithmetic)

| Quantity | Source | 4 KiB | 8 KiB | 16 KiB |
|---|---|---:|---:|---:|
| IO_PAGESIZE | `createdb --db-page-size` | 4,096 | 8,192 | 16,384 |
| DB_PAGESIZE = IO - 40 | `storage_common.c RESERVED_SIZE_IN_PAGE` | 4,056 | 8,152 | 16,344 |
| spage_max_record_size() | `slotted_page.c:841` | 4,020 | 8,116 | 16,308 |
| heap_nonheader_page_capacity() | `heap_file.c:27567` | 3,980 | 8,076 | 16,268 |
| heap_Maxslotted_reclength (REC_BIGONE above this) | `heap_file.c:3714` | 3,948 | 8,044 | 16,236 |
| Record gate, pinned: DB_PAGESIZE / 4 | `heap_file.c:12350,12383` | 1,014 | 2,038 | 4,086 |
| Record gate, normative four-record target | `OOS-CONTEXT §1 (CBRD-27057)` | 988 | 2,012 | 4,060 |
| Max single-chunk payload, pinned 16 B chunk header | `oos_file.cpp:3249` | 4,000 | 8,096 | 16,288 |
| Max single-chunk payload, normative 24 B chunk header | `OOS-CONTEXT §2 layout` | 3,992 | 8,088 | 16,280 |

Eligibility floor (page-size independent): pinned `OR_OOS_INLINE_SIZE` = 16 B (value must be > 16 B); normative = 24 B (value must be > 24 B).
For a BIT VARYING value of N logical bytes the serialized size is ALIGN(1 + N, 4) while N < 32, so the floor in logical bytes is: pinned N >= 16 eligible (N = 15 is not); normative N >= 24 eligible (N = 23 is not). Values with N in [16, 23] are demoted by the pinned engine but must stay inline under the normative rule.
VOT width (page-size independent): 1-byte entries while header+payload <= 127; 2-byte while <= 32767; 4-byte above. Since every OOS-bearing record must be <= heap_Maxslotted_reclength (max 16,236 at 16 KiB), an OOS-bearing record never uses 4-byte VOT entries.

## Schema A: `CREATE TABLE a (id INT, v BIT VARYING)` -- N = payload bytes of v

| Boundary | 4 KiB | 8 KiB | 16 KiB |
|---|---:|---:|---:|
| Smallest N demoted, pinned gate (DB_PAGESIZE/4, 16 B stub) | 964 | 1,988 | 4,036 |
| Smallest N demoted, normative target (four-record, 24 B stub) | 940 | 1,964 | 4,012 |
| Smallest N needing 2 chunks, pinned 16 B chunk header | 3,996 | 8,092 | 16,284 |
| Smallest N needing 2 chunks, normative 24 B chunk header | 3,988 | 8,084 | 16,276 |
| Smallest N switching VOT to 2-byte entries (any page size) | 92 | 92 | 92 |

## Schema B: `CREATE TABLE b (id INT, f BIT(8*F), v BIT VARYING)` with v = 64 B -- F = fixed bytes

| Boundary | 4 KiB | 8 KiB | 16 KiB |
|---|---|---|---|
| Smallest F rejected with ER_HEAP_OOS_OVERPASS_MAXOBJ_SIZE (-1382), pinned 16 B stub | 3,889 | 7,985 | 16,177 |
| Same, normative 24 B stub | 3,881 | 7,977 | 16,169 |
| inline_size_after_oos at that F (pinned), one byte above heap_Maxslotted_reclength | 3,949 | 8,045 | 16,237 |

## Worked derivation, schema A, 16 KiB, pinned engine

```text
header  = OR_MVCC_INSERT_HEADER_SIZE 16 + VOT ALIGN(1*(1+1),4)=4 + bound bits 4 = 24
payload = INT 4 + varbit_len(N) where varbit_len(N) = ALIGN(5 + N, 4) for N >= 32
gate    : header + payload + mvcc_extra 16 > DB_PAGESIZE/4 = 4,086
        : 24 + 4 + L + 16 > 4,086  <=>  L > 4,042  <=>  L >= 4,044
        : ALIGN(5 + N, 4) >= 4,044  <=>  N >= 4,036   (N = 4,035 stays inline)
normative target 4,060: N >= 4,012; disputed band N in [4,012, 4,035] (normative demotes, pinned keeps inline)
```
