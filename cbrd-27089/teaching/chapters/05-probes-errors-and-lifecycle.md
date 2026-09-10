# 5. Duplicate probes, errors and lifetime

## A temporary image can cause a permanent mistake

REPLACE first needs to find conflicting unique keys so existing rows can be removed. ODKU (`INSERT ... ON DUPLICATE KEY UPDATE`) needs to find the row that would conflict before choosing its update behavior. Both paths construct a candidate record for key extraction. That candidate image is not itself the row finally inserted. [C-026]

The PR adds a local boolean and passes its address to the allocator in both helpers. Neither helper needs the resulting true/false verdict: the pointer's presence selects OOS suppression. This prevents the discarded key-probe image from creating an unowned chain. REPLACE preserves `LOB_FLAG_EXCLUDE_LOB`; ODKU preserves `LOB_FLAG_INCLUDE_LOB`. Suppression changes OOS publication, not the existing LOB policy. [C-026]

The rest of each helper still does real work. REPLACE loops over unique indexes, extracts keys, prunes index targets, calls `xbtree_find_unique`, and deletes conflicting rows when found. ODKU searches for a duplicate, records its OID and can select its partition scan cache. Calling the entire helper “side-effect free” would therefore be wrong. Only the temporary transformation's OOS creation is suppressed. [C-026]

## Three different lifetimes

| Object | Owner and lifetime | End of lifetime |
|---|---|---|
| Probe/final `LC_COPYAREA` | Locator preparation owns transient bytes | Freed after pruning or after lower write call |
| `attr_info` DB_VALUEs and state | Caller-provided attribute cache survives both passes | Released by its surrounding operation; not by freeing a copy area |
| OOS value chains | Persistent records associated with the selected heap | Managed by transaction/recovery and reclamation paths, not `locator_free_copy_area` |

The distinction is essential on errors. Freeing a copy area releases a memory buffer; it does not undo previously published database records. Before the final pass, suppression prevents OOS chains from being created for the probe. Once the final pass writes chains, a later failure must use the existing transaction/error machinery. [C-008] [C-016] [C-027]

## Follow each failure exit

| Failure | Immediate action visible in the traced code | What the caller must understand |
|---|---|---|
| First copy-area allocation fails | Allocator returns null | No transform ran |
| Probe transform fails | Allocator frees its copy area and returns null | Attribute preparation may already have changed state; caller reports failure |
| Early partition pruning fails | Locator frees probe, clears pointer/area, breaks with pruning error | No final OOS pass runs |
| Final transform fails | Allocator returns null; locator sets `ER_FAILED` | OOS work may have begun; memory cleanup is not rollback |
| Unsupported OOS-plus-bigone layout | Internal transform sets error and returns before insertion | No chain is written by this transformation |
| Buffer too small | Internal loop enlarges and retries writing | Increment set and LOB markers prevent repeated successful effects |
| Lower insert/update fails | Error is propagated, final copy area is freed | Existing statement/transaction recovery obligations remain |

These are source control-flow facts, not a claim that every allocation failure was injected. One adjacent pre-existing path merits caution: after `release_buffer`, the allocator frees its original copy area and allocates a larger one; if that allocation fails, the shown return occurs before the explicit `free(allocated_data)`. We do not certify all allocation cleanup in this dependency. The book's scope is the PR ordering change. [C-008] [C-027]

## Locks, persistence and ownership

A transaction groups database work that can commit or roll back. Write-ahead logging records changes needed for recovery; a successful memory allocation has no equivalent durability meaning. A lock coordinates logical access between transactions, while a page latch protects a brief physical page operation. The PR changes the order of preparation and routing within that existing machinery. [C-017] [C-027]

The new early phase selects a destination; it does not introduce a new locking protocol. The lower locator retains subclass locks, scan-cache selection and actual row operations. Any change to skip its second pruning would need to preserve those responsibilities and the representation-ID handling. The PR is also not a new commit boundary: successful OOS insertion is not equivalent to a committed SQL row. [C-017] [C-027]

One unchanged lower layer makes the persistence distinction concrete. If `heap_oos_find_vfid` must create a file, it starts a system operation, creates the OOS file, applies the class encryption policy, logs the heap-header update, marks the page dirty and completes the system operation. Errors abort that system operation and return failure. This file-creation operation is not the SQL transaction's final commit, and the PR adds no replacement for it. [C-034]

For MVCC, old row versions can still be visible to older transactions. Their out-of-row values cannot be reclaimed merely because the current SQL UPDATE has constructed new values. The unchanged eager-cleanup helper describes a separate non-MVCC path and compares old/new references. Full vacuum retry safety, chain identity and crash recovery are neighboring OOS concerns, not solved by choosing the correct partition owner. [C-027]

## Costs and observable behavior

Partitioned OOS writes now serialize a fully-inline probe and a compact final image, and prune early as well as through the ordinary lower path. The probe can be much larger than the stored record. This introduces extra CPU and transient memory work proportional to the logical values being serialized. No latency or peak-memory benchmark is reported here. Nonpartitioned writes retain the ordinary path, and no-demotion partition writes reuse their single probe image. [C-028]

`SHOW ALL HEAP OOS` is useful because it reports separate root/child rows and per-file counts. Its `has_oos` diagnostic column means the heap has an OOS file; it must not be confused with a record's `HAS_OOS` flag. An empty-but-existing OOS file can still have a true file-existence indicator. This regression starts from a clean table, so zero file indicators have a precise meaning. [C-003]

Security: no new SQL authorization interface, parser rule or client protocol is introduced by these six files' diff. Existing locks and class lookup remain dependencies. This observation is limited to the patch; it is not an audit of all OOS access control or encryption. Network/restart experiments are not applicable to the fresh standalone observation, which opens an owned local database in process. [C-029]

## Prediction questions

1. Why does a duplicate-key helper pass a verdict pointer and never read the verdict?
2. What survives when the probe copy area is freed?
3. Why does freeing the final buffer not undo its OOS writes?
4. What responsibilities would be lost if you simply removed the lower locator's pruning block?
5. Which cost would you measure for a multi-megabyte value even if the final heap record is small?
