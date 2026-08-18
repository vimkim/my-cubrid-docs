# CUBRID database volume format and a read-only raw-page parser

Source baseline: CUBRID `develop` commit `e6ed61e87d68` (2026-08-18 local checkout).

This report describes what can be learned by reading CUBRID database volume files such as `testdb` and `testdb_x001` without modifying or mounting them. It is deliberately conservative: CUBRID does not expose these native in-memory structures as a stable, portable file-format API. Exact offsets below are for the current source/build ABI and must be verified again for another CUBRID version, compiler ABI, or architecture.

## Executive answer

Yes, a normal CUBRID data volume is an array of fixed-size physical pages, so page `N` begins at:

```text
byte_offset = N * volume_io_page_size
```

The default I/O page size is 16 KiB, but a parser must not assume 16 KiB: this source accepts power-of-two sizes from 4 KiB through 16 KiB, which means 4, 8, or 16 KiB (`src/storage/storage_common.h:89-101`, `src/storage/storage_common.c:99-155`). The volume header in physical page 0 records the actual I/O page size (`src/storage/disk_manager.c:73-111`, `src/storage/disk_manager.c:585-615`). CUBRID itself computes disk offsets as `pageid * page_size` and reads one complete page with `pread` (`src/storage/file_io.c:3933-3967`).

Every physical data page has a plaintext reserved prefix containing its page LSA, `pageid`, `volid`, debug page type, TDE flags, and TDE nonce. It also has a duplicate LSA watermark at the end (`src/storage/file_io.h:164-235`). Consequently, the physical VPID `(volid, pageid)`, page-type byte, encryption algorithm flag, nonce, and LSA remain identifiable even when TDE is enabled. The middle user area is directly parsable only when that page's TDE flag is clear, or after correct decryption.

The important limitation is ownership. A page does **not** contain a universal direct “table/index/file owner” field. A parser can read its VPID and page type directly, but it must reconstruct file ownership by discovering file headers and traversing their partial/full sector tables. A heap or B-tree file descriptor then gives direct identifiers such as class OID, HFID, BTID, and attribute ID; resolving those to class or index names requires catalog interpretation. `diagdb` and `spacedb` perform this reconstruction through a restarted CUBRID engine, not by independently parsing arbitrary raw bytes.

The practical conclusion is:

| Question | Raw answer | Confidence/source |
|---|---|---|
| Is this physical page `N` in volume `V`? | Read prefix `pageid`/`volid` and cross-check the offset and volume header | Direct |
| What broad page type is it? | Read prefix `ptype` | Direct, but explicitly a debugging classification |
| Is its payload encrypted? | Read prefix `pflag` | Direct, per page |
| Is its sector reserved? | Read the volume sector bitmap | Reconstructed from volume metadata |
| Which CUBRID file allocated it? | Traverse each file header's allocation tables | Reconstructed |
| Is that file heap/B-tree/etc.? | Read `FILE_HEADER.type` | Direct once the file header is found/decrypted |
| Which class/index name owns it? | Interpret the file descriptor and system catalogs | Reconstructed logical metadata |
| Is the raw live image transactionally consistent? | Not knowable from a page alone | Unavailable without coordinated snapshot/recovery semantics |

## 1. Which files are database volumes?

Given a database name such as `testdb`, the primary permanent data volume is usually the file named `testdb`. Default extension volumes use names such as `testdb_x001`; temporary volume names use `_t`; the volume-information sidecar is `_vinf`; the double-write buffer is `_dwb`; and TDE key material uses `_keys`. Active/archive log suffixes are `_lgat` and `_lgar` (`src/storage/file_io.h:81-94`). Default extension naming is implemented as `<database>_x%03d`, but users may choose another path/name (`src/storage/file_io.c:5634-5665`, `src/transaction/boot_sr.c:5995-6063`).

Do not discover volumes only by filename globbing. The `_vinf` file is a convenient volume list, but CUBRID can recreate it by following the volume linkage stored inside permanent volume headers (`src/transaction/log_page_buffer.c:4721-4759`). For a forensic parser, use both and report disagreements:

1. Treat the user-supplied primary-volume path as the root of trust.
2. Read page 0 and validate its magic and volume ID.
3. Follow the header's next-volume ID/name information where readable.
4. Compare the resulting chain with `_vinf` and discovered sibling files.

Log, backup, DWB, and key files have different formats and must not be fed to the data-volume page parser merely because they share the database prefix.

## 2. Physical page framing

### 2.1 Page size and alignment

The current defaults and limits are:

```text
IO_DEFAULT_PAGE_SIZE = 16 * 1024
IO_MIN_PAGE_SIZE      =  4 * 1024
IO_MAX_PAGE_SIZE      = 16 * 1024
```

`IO_PAGESIZE` is the complete on-disk page; `DB_PAGESIZE` is the usable middle area after subtracting the reserved prefix and trailing watermark (`src/storage/storage_common.h:89-101`, `src/storage/storage_common.c:43-48`). CUBRID validates page sizes as powers of two within the limits (`src/storage/storage_common.c:99-155`). A volume's physical page count is computed as file size divided by page size (`src/storage/file_io.c:4921-4932`).

Thus a default database is 16 KiB aligned, but “all CUBRID databases are 16 KiB aligned” is false. A parser should discover and validate the size before walking the volume.

### 2.2 Current physical page envelope

`FILEIO_PAGE` contains a reserved prefix, the user area, and a watermark placed at the very end of the configured page (`src/storage/file_io.h:164-199`). Under the current GCC/x86-64 ABI used by this checkout, the layout is:

```text
physical page offset

0        +-----------------------------------------+
         | leading LOG_LSA                  8 bytes|
8        | pageid                           4 bytes|
12       | volid                            2 bytes|
14       | ptype                            1 byte |
15       | pflag                            1 byte |
16       | p_reserve_1                      4 bytes|
20       | p_reserve_2                      4 bytes|
24       | tde_nonce                        8 bytes|
32       +-----------------------------------------+
         | user page area: DB_PAGESIZE             |
P - 8    +-----------------------------------------+
         | trailing duplicate LOG_LSA       8 bytes|
P        +-----------------------------------------+
```

For a 16 KiB page, the user area is `16,384 - 32 - 8 = 16,344` bytes, spanning offsets 32 through 16,375. The watermark begins at 16,376. These numerical offsets are ABI observations derived from the structures, not a declared cross-platform wire format. A production parser should assert them against a small helper built from the exact target source headers rather than silently casting bytes.

The `LOG_LSA` itself is an eight-byte C++ bitfield with a 48-bit log page ID and 16-bit log offset (`src/transaction/log_lsa.hpp:35-63`). Bitfield layout is especially compiler/ABI sensitive.

### 2.3 VPID semantics

The prefix stores `pageid` and `volid` directly (`src/storage/file_io.h:168-175`). Therefore a parser may construct:

```text
VPID = { volid: prefix.volid, pageid: prefix.pageid }
```

and validate it against the physical location:

```text
prefix.pageid == physical_offset / page_size
prefix.volid  == page_0.volume_header.volid
```

However, this VPID describes the physical slot, not its current logical owner. CUBRID initializes/checks the prefix VPID as a buffer identity (`src/storage/page_buffer.c:5384-5420`). On page deallocation it changes the type to `PAGE_UNKNOWN` and clears flags, but intentionally does not establish a new logical owner field (`src/storage/page_buffer.c:15098-15161`). Old data and the VPID can therefore remain in a deallocated slot.

### 2.4 The page-type byte

The current `PAGE_TYPE` values are (`src/storage/storage_common.h:148-166`):

| Value | Symbol | Broad interpretation |
|---:|---|---|
| 0 | `PAGE_UNKNOWN` | Unknown, deallocated, or not typed |
| 1 | `PAGE_FTAB` | File header/allocation-table page |
| 2 | `PAGE_HEAP` | Heap page |
| 3 | `PAGE_VOLHEADER` | Volume header, normally page 0 |
| 4 | `PAGE_VOLBITMAP` | Volume sector-allocation bitmap |
| 5 | `PAGE_QRESULT` | Query result |
| 6 | `PAGE_EHASH` | Extendible hash |
| 7 | `PAGE_OVERFLOW` | Overflow object |
| 8 | `PAGE_AREA` | Query-area page |
| 9 | `PAGE_CATALOG` | Catalog page |
| 10 | `PAGE_BTREE` | B-tree page |
| 11 | `PAGE_LOG` | Currently unused in this enum |
| 12 | `PAGE_DROPPED_FILES` | Dropped-files metadata |
| 13 | `PAGE_VACUUM_DATA` | Vacuum metadata |

The source explicitly labels this field as used for debugging. It is useful as a classifier and strong consistency check, but it is not a substitute for parsing file metadata or page-specific headers. Treat unknown future values as “unrecognized,” not corruption.

## 3. Discovering page size and volume identity

Physical page 0 is the volume header (`DISK_VOLHEADER_PAGE = 0`, `src/storage/disk_manager.h:35`). Its user area begins with a native `DISK_VOLUME_HEADER` containing:

- the magic `CUBRID/Volume`;
- the I/O page size and volume ID;
- purpose/type and sector size/counts;
- sector allocation-table locations;
- database and volume creation times;
- checkpoint LSA;
- boot heap-file ID for the primary volume;
- next-volume linkage and variable strings.

See `src/storage/disk_manager.c:73-111`, the magic definition at `src/storage/storage_common.h:402-404`, and initialization at `src/storage/disk_manager.c:585-615`.

For the current ABI, the following bootstrap offsets are sufficient:

| Physical offset in page 0 | Field | Current size |
|---:|---|---:|
| 8 | prefix page ID | 4 |
| 12 | prefix volume ID | 2 |
| 14 | prefix page type | 1 |
| 32 | volume magic | 25 |
| 58 | volume I/O page size | 2 |
| 60 | inner volume ID | 2 |

CUBRID itself has an O_RDONLY volume inspection path that finds `DISK_VOLUME_HEADER` at `offsetof(FILEIO_PAGE, page)` and checks the magic and database creation time (`src/storage/disk_manager.c:6219-6289`). That is the closest in-tree precedent for bootstrapping a raw-volume reader.

A robust detector should try the supported candidate sizes `{4096, 8192, 16384}` and require all of the following before accepting one:

- magic is exactly `CUBRID/Volume` at the ABI's user-area offset;
- header `iopagesize` equals the candidate;
- physical file size is a multiple of the candidate;
- prefix page ID is 0 and type is `PAGE_VOLHEADER`;
- prefix and inner volume IDs agree;
- leading and trailing LSAs agree;
- declared sector/page counts are plausible for the file length.

Do not scan for the magic at arbitrary offsets and accept the first hit. Accidental payload bytes are not sufficient evidence of a volume or ABI.

## 4. Volume allocation map: reserved sector, not file owner

CUBRID groups pages into fixed 64-page sectors (`src/storage/storage_common.h:105-121`). The volume header points to sector-allocation bitmap pages. The bitmap uses 64-bit units and one bit per sector (`src/storage/disk_manager.c:217-264`). Bitmap pages start after the volume header in current formatting, carry `PAGE_VOLBITMAP`, and have system sectors reserved (`src/storage/disk_manager.c:3165-3170`, `src/storage/disk_manager.c:4902-4940`).

This map answers whether a sector is reserved at the volume layer. It does **not** say which file owns the sector or whether each individual page is an allocated user page. The engine's disk-map query derives a page's sector and checks that sector bit; system pages are handled as valid separately (`src/storage/disk_manager.c:4160-4232`).

Recommended raw states at this stage are therefore:

```text
SYSTEM_PAGE
SECTOR_UNRESERVED
SECTOR_RESERVED_OWNER_UNKNOWN
BITMAP_INCONSISTENT
```

Do not label all 64 pages in a reserved sector “allocated to a file.” File-level tables refine that answer.

## 5. Reconstructing file and object ownership

### 5.1 File header identity

Every CUBRID file has a header VPID derived from its VFID:

```text
header_vpid.volid  = vfid.volid
header_vpid.pageid = vfid.fileid
```

This mapping and the file-table offset helpers are in `src/storage/file_manager.c:195-211`. A file header occupies the user area of a `PAGE_FTAB` page and contains a native `FILE_HEADER` (`src/storage/file_manager.c:85-167`). Important fields include:

- `self` VFID;
- tablespace information;
- fixed 64-byte file descriptor;
- total/user/file-table/free page counts;
- total/partial/full sector counts;
- `FILE_TYPE` and flags;
- offsets to the partial-sector, full-sector, and numerable-page tables;
- sticky-first page and links to additional table pages.

The current file types are tracker, heap, heap with reusable slots, multi-page object heap, B-tree, B-tree overflow key, extendible hash, directory, catalog, dropped-files, vacuum data, query area, temporary, and unknown (`src/storage/file_manager.h:38-55`).

A raw scanner can distinguish a candidate file header from a continuation `PAGE_FTAB` page by validating the candidate's `self` against the prefix VPID and enforcing the same count/offset invariants as `file_header_sanity_check` (`src/storage/file_manager.c:928-1025`). Under the current ABI `sizeof(FILE_HEADER) == 216`; important user-area-relative offsets are `self=8`, `descriptor=40`, page counts `104..120`, sector counts `124..136`, type `140`, flags `144`, and table offsets `150/152/154`. These are version/ABI facts, not portable serialization constants.

### 5.2 File allocation tables

File tables are extensible-data chains. Partial-sector records contain a volume/sector ID and a 64-bit page bitmap; a set bit means that page is allocated and an unset bit is reserved capacity. Full-sector records mean all 64 pages are allocated (`src/storage/file_manager.c:217-268`, `src/storage/file_manager.h:151-167`, `src/storage/file_manager.c:7673-7793`, `src/storage/file_manager.c:7826-7848`).

The engine's own page-map traversal:

1. visits partial-sector records and their set bits;
2. visits every page of full sectors;
3. identifies and skips file-header/table-chain pages when returning user pages.

See `src/storage/file_manager.c:7169-7218`, `src/storage/file_manager.c:7225-7273`, and `src/storage/file_manager.c:7315-7368`.

The parser can reproduce this traversal read-only and build:

```text
VPID -> {
  allocation: ALLOCATED_FTAB | ALLOCATED_USER | RESERVED_FREE,
  owner_vfid,
  file_type,
  descriptor,
  evidence: header/table VPID and record index
}
```

If two file maps claim one VPID, if a file claims an unreserved volume sector, or if counts disagree, retain a `CONFLICT` record with both claims. Never pick one silently.

### 5.3 Finding all files

The authoritative engine route begins with the primary volume header's boot HFID, reads the boot database parameter record, obtains the file-tracker VFID, and traverses the tracker. Tracker items are 16-byte entries containing file ID, volume ID, file type, and metadata (`src/storage/file_manager.c:493-523`, `src/storage/file_manager.c:9871-9964`, `src/transaction/boot_sr.c:2310-2327`). The initial tracker VFID is persisted during database creation (`src/transaction/boot_sr.c:4952-4983`).

Implement this route for the strongest result. It requires enough slotted-page/heap-record support to read the boot record.

A simpler first version may scan every **plaintext** `PAGE_FTAB` page for a structurally valid `FILE_HEADER`, using `self == prefix VPID`, legal type, table-offset bounds, and count invariants to reject continuations and false positives. Then it follows each validated header's tables. Label this route `DISCOVERED_BY_SCAN`, because it can miss encrypted headers, damaged headers, or a future layout and may encounter stale bytes. Cross-check scanned headers against the tracker when tracker parsing becomes available.

### 5.4 From VFID to heap/table/index identity

The fixed file descriptor makes some object identity directly available once the file header is parsed:

| File kind | Descriptor contains |
|---|---|
| Heap | class OID and HFID |
| Heap overflow | HFID and class OID |
| B-tree | class OID and attribute ID |
| B-tree overflow key | BTID and class OID |
| E-hash | class OID and attribute ID |

The definitions and the explicit on-disk compatibility warning are in `src/storage/file_manager.h:80-149`. These are numeric identifiers, not human-readable table/index names. The file-manager diagnostic code resolves names through the catalog after reading the descriptor (`src/storage/file_manager.c:1424-1475`). A “simple parser” should report both levels honestly:

```text
direct:        file_type=BTREE, class_oid=(...), attr_id=...
catalog state: name resolution not implemented / resolved to ...
```

## 6. What `diagdb` and `spacedb` actually teach us

`diagdb` is not an offline byte parser. It calls `db_restart` in standalone mode; its emergency option skips recovery but still mounts and interprets the database through engine code (`src/executables/util_sa.c:1519-1604`). Its modes then invoke tracker dumps, volume-capacity/bitmap dumps, heap/index dumps, and catalog traversals (`src/executables/util_sa.c:1613-1659`, `src/executables/util_sa.c:1727-1800`).

`spacedb` likewise restarts/connects to the database and asks the server for space data (`src/executables/util_cs.c:924-1056`). The storage layer reads volume headers/cache state for disk totals (`src/storage/disk_manager.c:6016-6135`) and traverses the file tracker plus individual file headers to group file purposes and sum counts (`src/storage/file_manager.c:7900-7935`, `src/storage/file_manager.c:12172-12272`).

The reusable lesson is their hierarchy, not their invocation model:

```text
database
  -> volume headers and volume sector maps
  -> boot metadata and file tracker
  -> each file header and file allocation map
  -> heap/B-tree/catalog page-specific interpretation
```

An independent parser must recreate this hierarchy and the validations it normally inherits from buffer latches, recovery, the DWB, TDE, and catalog code.

## 7. TDE: what remains visible and what becomes opaque

TDE is per page. `pflag` bit 0 means AES and bit 1 means ARIA (`src/storage/file_io.h:62-66`). Page-buffer helpers map those flags to `TDE_ALGORITHM_AES`, `ARIA`, or `NONE` (`src/storage/page_buffer.c:5050-5151`).

For a data page, CUBRID encrypts exactly the middle `DB_PAGESIZE` area beginning after `FILEIO_PAGE_RESERVED`; it excludes both the leading prefix and trailing watermark (`src/storage/tde.h:42-46`, `src/storage/tde.c:913-1000`). Therefore the following remain plaintext:

- leading and trailing LSAs;
- VPID;
- `ptype` and `pflag`;
- reserved integers;
- TDE nonce.

The volume/file/slotted-page metadata in the middle is opaque whenever its page is encrypted. Do not infer “TDE is disabled for the database” merely from one clear page; inspect each page's flag. Conversely, if all relevant pages have zero encryption flags in a consistent snapshot, their payloads can be parsed directly.

The implementation uses AES-256-CTR or ARIA-256-CTR (`src/storage/tde.c:1066-1131`, `src/storage/tde.c:1144-1208`). The permanent-page nonce is tied to its page LSA, while temporary pages use a counter retained in the prefix (`src/storage/tde.c:913-1000`). CTR mode here has no authentication tag. A successful-looking decryption does not by itself authenticate the key or bytes; structural and cross-page validation remains essential.

The `_keys` file must not be treated as a simple standalone decryption password. Engine initialization combines boot-database key information with key-file handling (`src/transaction/boot_sr.c:2329-2335`). A safe first parser should inventory encrypted pages and stop at the payload boundary unless exact-version key loading/decryption is intentionally implemented and reviewed.

## 8. LSA watermark is not a general checksum

CUBRID writes the same page LSA into the prefix and final watermark (`src/storage/file_io.h:201-235`). Its low-level sanity check reports corruption when those two LSAs differ (`src/storage/file_io.c:11933-11946`). This can detect some torn writes that separate the beginning and end of a page.

It is **not** a checksum of the middle payload. Equal LSAs do not establish that:

- the middle bytes are intact;
- the page was read from one atomic transaction snapshot;
- related pages are mutually consistent;
- decrypted plaintext is authentic;
- the page's transaction is committed.

Call this check `lsa_watermark_equal`, not `checksum_valid`.

## 9. A staged read-only parser

### Stage 0: freeze assumptions

Record target CUBRID version/commit, platform endianness, compiler ABI, and expected page-size candidates. Generate or manually verify a layout manifest from the exact headers. Refuse unsupported layouts by default.

Open every volume `O_RDONLY`. Prefer a database closed cleanly, a restored backup, or a coordinated filesystem/storage snapshot. Preserve source paths, file sizes, mtimes, and optional whole-file hashes in the report.

### Stage 1: bootstrap volumes

For each candidate primary/extension file:

1. Read enough bytes for page 0.
2. validate the prefix, volume magic, inner volume ID, and candidate page size;
3. validate file-size divisibility and page-count/count-field plausibility;
4. validate leading/trailing LSA equality;
5. extract database creation time and volume-link information;
6. group volumes by database creation time and reject conflicting IDs.

### Stage 2: inventory physical pages

Read complete pages with positional I/O. For page index `n`, record:

```text
PageEnvelope {
  source_volume_path
  physical_offset
  expected_vpid
  stored_vpid
  page_type
  tde_algorithm
  tde_nonce
  leading_lsa
  trailing_lsa
  lsa_watermark_equal
  envelope_validity
  payload_state: PLAINTEXT | ENCRYPTED_OPAQUE
}
```

Do not discard malformed pages. Emit a record with explicit validation failures.

### Stage 3: parse volume/system space

Parse page 0 and its sector bitmap pages. Mark system pages, reserved sectors, and unreserved sectors. Validate bitmap extent against header counts. This produces volume reservation state only.

### Stage 4: discover files

Preferred route: parse the boot heap record, obtain the tracker VFID, and traverse tracker extensible data. Minimal route: scan plaintext `PAGE_FTAB` pages and accept only `FILE_HEADER` candidates that satisfy strict self/count/offset/type invariants. Retain discovery provenance.

### Stage 5: reconstruct file maps

For every accepted file header:

1. mark its header and continuation-table pages `ALLOCATED_FTAB`;
2. follow partial-sector chains and map set bits to `ALLOCATED_USER`;
3. map unset bits in owned partial sectors to `RESERVED_FREE`;
4. follow full-sector chains and map all pages `ALLOCATED_USER` except known FTAB pages;
5. attach VFID, file type, and descriptor to every claim;
6. reconcile claims with the volume sector bitmap and header counts;
7. report conflicts without destructive repair or guesswork.

### Stage 6: optionally decode page families

Only after ownership/type checks agree should the parser interpret the middle payload. Slotted pages have a native `SPAGE_HEADER` and four-byte bitfield slots; the source explicitly warns that compiler bitfield behavior matters (`src/storage/slotted_page.h:63-91`). Slots are stored backward from the end of `DB_PAGESIZE` (`src/storage/slotted_page.c:4578-4586`).

For heap pages, slot 0 holds a heap header or chain record; chain records include previous/next VPIDs (`src/storage/heap_file.h:62`, `src/storage/heap_file.c:184-217`, `src/storage/heap_file.c:268-277`). The heap diagnostic follows `next_vpid` and dumps the associated file table (`src/storage/heap_file.c:14686-14803`).

For B-trees, slot 0 contains `BTREE_NODE_HEADER`; `node_level == 1` is a leaf and greater values are non-leaf, with sibling links in the header (`src/storage/btree_load.h:131-132`, `src/storage/btree_load.h:224-234`, `src/storage/btree.c:9955-9990`).

Decoding row values or index keys is a later project: it additionally needs representation/schema information, MVCC record interpretation, overflow handling, and compression rules. The first parser should stop at page/header/slot inventory unless those dependencies are implemented.

## 10. Minimal parsing pseudocode

The example deliberately uses explicit byte loaders and a versioned layout table rather than C structure casts:

```text
SUPPORTED_PAGE_SIZES = [4096, 8192, 16384]

detect_volume(fd, abi):
    prefix_and_header = pread_exact(fd, 0, 4096)
    for P in SUPPORTED_PAGE_SIZES:
        if file_size(fd) % P != 0:
            continue
        h = parse_volume_page0(prefix_and_header, abi)
        if h.magic != "CUBRID/Volume":
            continue
        if h.io_page_size != P:
            continue
        whole_page0 = pread_exact(fd, 0, P)
        e = parse_envelope(whole_page0, P, abi)
        if e.pageid == 0 and e.ptype == PAGE_VOLHEADER \
           and e.volid == h.volid and e.leading_lsa == e.trailing_lsa:
            return Volume(P, h.volid, h, fd)
    fail("unsupported, damaged, or wrong-ABI volume")

scan_pages(volume, abi):
    for n in 0 .. volume.file_size / volume.page_size - 1:
        raw = pread_exact(volume.fd, n * volume.page_size,
                          volume.page_size)
        e = parse_envelope(raw, volume.page_size, abi)
        expected = VPID(volume.volid, n)
        checks = [e.vpid == expected,
                  e.pflag contains only known bits,
                  e.leading_lsa == e.trailing_lsa]
        payload = raw[abi.prefix_size : volume.page_size-abi.watermark_size]
        yield RawPage(expected, e, checks,
                      OPAQUE if e.pflag != 0 else payload)

discover_file_headers(pages, abi):
    for p in pages where p.ptype == PAGE_FTAB and p.payload is plaintext:
        f = parse_file_header(p.payload, abi)
        if f.self == VFID(p.vpid.volid, p.vpid.pageid) \
           and legal_file_type(f.type) \
           and table_offsets_in_bounds(f) \
           and file_counts_are_consistent(f):
            yield CandidateFile(f, provenance=DISCOVERED_BY_SCAN)

build_ownership(files, volumes):
    claims = multimap<VPID, OwnershipClaim>()
    for f in files:
        add_file_table_pages(claims, f)
        for partial in walk_partial_sector_tables(f):
            for bit in 0..63:
                vpid = sector_bit_to_vpid(partial.vsid, bit)
                claims[vpid].add(allocated_user(f) if bit_is_set(partial, bit)
                                 else reserved_free(f))
        for vsid in walk_full_sector_tables(f):
            for bit in 0..63:
                claims[sector_bit_to_vpid(vsid, bit)].add(allocated_user(f))
    reconcile_with_volume_bitmaps_and_counts(claims, volumes)
    return preserve_all_conflicts(claims)
```

Required loader rules:

- bounds-check every load, multiplication, table offset, count, VPID, and chain link;
- impose loop and item-count limits on every linked/extensible table;
- detect cycles with visited VPIDs;
- never follow a VPID into a different or unknown database-creation group;
- never decrypt or decompress in place in the source mapping;
- never cast an unaligned byte pointer to a CUBRID struct;
- use tri-state/diagnostic results instead of assertions that terminate the whole scan.

## 11. Live-volume and portability hazards

### Online reads are not a coherent snapshot

The normal page-buffer read path checks the double-write buffer before the main volume and decrypts afterward (`src/storage/page_buffer.c:8435-8507`). Flush encrypts the middle payload before writing through DWB/main-volume machinery (`src/storage/page_buffer.c:10673-10835`). It also enforces WAL ordering by flushing the relevant log before the page (`src/storage/page_buffer.c:10776-10795`). A custom `pread` reader bypasses all of these semantics.

While the server is online, one raw page can change between two reads; file headers and their allocation chains can describe different instants; and the latest complete copy may temporarily reside in `<db>_dwb` rather than the main volume. Reading each page twice and requiring identical bytes reduces obvious races but does not create a database-wide transaction snapshot. Label such output `ONLINE_BEST_EFFORT`, never “consistent.”

### Torn pages and recovery

The duplicate LSA catches only a subset of torn writes. Recovery/WAL/DWB can make a database recoverable even when a direct raw-volume image is not internally current or consistent. A raw parser should diagnose; it must not attempt repair unless a separate, explicitly authorized recovery design is implemented.

### Endianness, compiler ABI, and version drift

Volume headers, file headers, slotted-page headers, and allocation records are accessed by the engine as native structs. Several include compiler bitfields. Padding, enum width, signedness, bit ordering, and endian interpretation can change outside the producing ABI. The source also warns that changing file descriptors requires a disk-compatibility change (`src/storage/file_manager.h:80-149`).

For safety:

1. bind a parser layout manifest to a CUBRID release/commit and ABI;
2. verify structure sizes/offsets with a helper compiled from that exact tree;
3. store byte order and compiler details with scan output;
4. reject, rather than guess, an unknown format;
5. validate every direct field against independent relationships.

## 12. Validation against CUBRID utilities

For a clean, non-TDE test database, validate the parser without granting it write access:

1. copy/snapshot the database files after clean shutdown;
2. run the parser against the copy;
3. restart an equivalent copy with the exact CUBRID build and collect `diagdb` volume bitmap, file tracker, heap, and B-tree output;
4. collect `spacedb` page/sector/file-purpose totals;
5. compare volume IDs/sizes, reserved sectors, file VFIDs/types/counts, page-type totals, and heap/B-tree chains;
6. repeat with 4, 8, and 16 KiB databases, extension volumes, freed/reused pages, and selected page corruptions;
7. repeat with AES and ARIA TDE to confirm that envelopes remain readable and encrypted payloads remain deliberately opaque.

The comparison target is not textual equality. It is agreement on invariant counts and identities, with documented differences caused by online recovery, DWB, catalog-name resolution, or encrypted payload availability.

## 13. Recommended first deliverable

The smallest useful and defensible parser should provide:

- page-size and volume-chain discovery;
- one record per physical page with VPID, page type, TDE state, nonce, LSA pair, and envelope validation;
- volume sector-reservation maps;
- plaintext `FILE_HEADER` discovery plus file-map reconstruction;
- VFID/file type/numeric descriptor attribution;
- explicit provenance and confidence for every ownership claim;
- machine-readable JSON/CSV plus a human summary;
- no row/key decoding and no TDE key handling in the first version.

That scope answers “where does this page belong?” as far as raw storage metadata safely permits, while making the boundary between direct bytes and reconstructed logical meaning visible.

## Source index

| Topic | Primary source locations |
|---|---|
| Page sizes and user size | `src/storage/storage_common.h:89-101`; `src/storage/storage_common.c:43-48`, `99-155` |
| Physical offset/read | `src/storage/file_io.c:3933-3967`, `4921-4932` |
| Page prefix/watermark | `src/storage/file_io.h:164-235` |
| Page type | `src/storage/storage_common.h:148-166`; `src/storage/page_buffer.c:5252-5280` |
| VPID initialization/reuse | `src/storage/page_buffer.c:5384-5420`, `15098-15161` |
| Volume header | `src/storage/disk_manager.h:35`; `src/storage/disk_manager.c:73-111`, `585-615` |
| Sector bitmap | `src/storage/disk_manager.c:217-264`, `4160-4232`, `4902-4940` |
| File header/types/descriptors | `src/storage/file_manager.c:85-211`, `928-1025`; `src/storage/file_manager.h:38-55`, `80-167` |
| File-map traversal | `src/storage/file_manager.c:7169-7368`, `7673-7848` |
| File tracker/bootstrap | `src/storage/file_manager.c:493-523`, `9871-9964`; `src/transaction/boot_sr.c:2310-2327`, `4952-4983` |
| TDE boundary/algorithms | `src/storage/tde.h:42-46`; `src/storage/tde.c:913-1000`, `1066-1208` |
| Normal I/O, DWB, WAL | `src/storage/page_buffer.c:8435-8507`, `10673-10835` |
| `diagdb` | `src/executables/util_sa.c:1499-1800` |
| `spacedb` | `src/executables/util_cs.c:924-1056`; `src/storage/disk_manager.c:6016-6135`; `src/storage/file_manager.c:12172-12272` |
| Slotted/heap/B-tree pages | `src/storage/slotted_page.h:63-91`; `src/storage/heap_file.c:14686-14803`; `src/storage/btree.c:9955-9990` |
