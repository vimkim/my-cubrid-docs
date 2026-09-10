# 1. From a SQL table to a stored record

PR #7600 makes a large value belong to the same partition heap as the row that refers to it. To understand why that requires two transformations, first distinguish a SQL name, a storage file, and a record buffer. [C-001] [C-002]

## What this book covers

We follow the six-file PR diff from base `2940b1cfbc3c2d4d0fac3f9244a960350debd380` to head `b871ea386d2c5419b7abae07dda58b9b7f36377a`. The source worktree is `/home/vimkim/gh/cb/CBRD-27089-has-oos-but-no-oos`; the six changed files match that head. Unrelated local work is excluded. The scope is partition write preparation, its immediate dependencies and the regression; it does not certify the entire OOS subsystem. [C-029]

Read chapters 1–5 for the mental model, then chapter 6 for all 30 hunks. Chapters 7–8 develop test reasoning and review exercises. Chapter 9 holds answers and chapter 10 the evidence ledger. Claim links such as [C-001] jump to exact source references. Source links are supplementary; the lessons, code listings and SVGs work offline.

## A concrete table

```sql
CREATE TABLE t_oos_show_part (
  id INT,
  data_col BIT VARYING STORAGE FORCE_OUTLINE
)
PARTITION BY RANGE (id) (
  PARTITION p0 VALUES LESS THAN (10),
  PARTITION p1 VALUES LESS THAN MAXVALUE
);
INSERT INTO t_oos_show_part VALUES (1, REPEAT(X'EE', 64));
```

This is the table and input used by the added regression. The first partition accepts values below 10; the second accepts values from 10 upward. Our `id=1` row belongs to p0. The example deliberately uses a small value with a forced storage policy, so it exercises the path that ordinary large-row tests can miss. `REPEAT(X'EE',64)` constructs 64 repeated bytes; the serialized attribute may also carry type-specific overhead. [C-003]

The local manual describes partitions as independent physical units implemented as subclasses of the partitioned table. Its range-partition section specifies exclusive upper bounds and `MAXVALUE`. That explains SQL routing; source code establishes how the selected class maps to its heap. Manual provenance is recorded in the source map. [C-004]

## Heap means row storage here

A heap file holds table records in pages. A page is a fixed-sized unit managed by the storage layer. Within a slotted page, a slot directory identifies individual records: a slot points to a record's location and length within that page. This lets page contents be organized without requiring a table's rows to appear in primary-key order. A B-tree index provides a different structure for key-based access. Here, “heap” names database storage; it is separate from a C++ process's allocation heap. [C-005]

The SQL table is represented internally as a class. A partitioned root class describes the logical table and its partitions. Child classes represent p0 and p1 and each supplies a heap identifier. In the traced UPDATE implementation the root holds no row data; an existing row comes from a child. “The partition heap” means the heap belonging to that selected child class. It does not introduce a new slotted-page format. [C-004] [C-006]

![Root class, child classes, heap pages and row slots](../assets/partition-heaps.svg)

In the diagram, p0 owns the page containing our row; p1 is a different possible destination. A SQL query using the root name can access child data through partition-aware execution. Do not interpret the root box as one physical page containing both child heaps. [C-006]

## Five identifiers and two record representations

| Name | What it identifies | How it matters in this PR |
|---|---|---|
| OID | An object address, with volume, page and slot components | A row OID identifies a row; a class OID identifies a class object. Same type, different referent. |
| Class OID | The OID of a class | The selected child's class OID is passed as the OOS owner. |
| VPID | A volume/page address | Locates a physical page. |
| VFID | A volume/file identifier | Identifies a database file, not a filesystem pathname. |
| HFID | A heap VFID plus its header page ID | Leads to the heap header and its OOS VFID. |
| `HEAP_CACHE_ATTRINFO` | In-memory attribute values and representation metadata | Survives both passes and carries their state. |
| `RECDES` | A byte buffer descriptor: data, length, allocated area, record type | A probe can be valid serialized bytes without yet being a stored row. |

These types connect identity to storage. An HFID is not the class OID; the code must look up a class's HFID. An OOS value also has an OID, but that OID refers to an OOS chunk record rather than the table row. [C-005] [C-007]

`DB_VALUE` represents a logical typed value in memory. Transformation serializes values into the byte layout expected by the engine. `record_descriptor` helps manage a buffer while `RECDES` describes its bytes. `LC_COPYAREA` supplies memory returned to the locator caller. These are stages in preparing data, not evidence that the row has already been inserted. [C-007] [C-008]

## Predict before continuing

1. Where does `id=10` belong? Which destination changes if `id=1` becomes `id=20`?
2. Why can a function receive both a class OID and an HFID?
3. Does a successful transformation imply there is already a heap row?
4. Draw the root, p0, p1 and the stored row without looking at the diagram.

Answers are in chapter 9. Continue when you can distinguish class identity, file identity and record bytes.
