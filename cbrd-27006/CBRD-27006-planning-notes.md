# [CBRD-27006] OOS recdes locality planning notes

- JIRA: https://jira.cubrid.org/browse/CBRD-27006
- Code commit: https://github.com/vimkim/cubrid/commit/56e22c15c4ae024c141035b62db9dfb6d17acf6c

## Purpose

이 문서는 CBRD-27006 구현 전에 정리한 계획을 public PR material로 옮긴 것이다. 원래 계획의 핵심은 하나의 `RECDES`에 여러 OOS columns가 있을 때 write/read locality를 개선하되, OOS record model을 바꾸지 않는 것이다.

Policy decisions:

- Reuse beats fresh allocation only when locality is preserved.
- Phase 1 optimizes single-chunk OOS values first.
- Lazy Resolve reads only requested columns.
- Public OOS insert APIs own insert publication.
- OOS-selected values may be serialized into stable memory before batch insertion.

## Implementation

### Write plan

`heap_attrinfo_insert_to_oos()` 는 OOS-selected attributes를 `attr_info->values[]` order로 모은다. 각 value는 stable buffer로 serialize하고, `oos_insert_many()` 에 logical order 그대로 넘긴다.

`oos_insert_many()` 는 single-chunk request run을 single-page OOS batch로 나눈다. Batch 하나는 한 OOS page에 함께 놓이는 placement unit이다.

Placement rules:

- Existing page reuse is allowed only when the whole batch fits.
- If the reused page loses the race after write-latch refix, allocate a fresh page for the whole batch.
- Do not split a batch across partially free pages merely because each value could fit somewhere.
- Multi-chunk values keep the existing chain path.
- Physical insertion order remains logical attribute order.

### Read plan

`oos_read_many()` 는 requested head OIDs를 `(volid, pageid)` 기준으로 group한다. Page groups are processed in first-seen request order, and slots inside a page are processed in request order.

Record-level Expand uses this in `heap_oos_read_values()`. Lazy Resolve uses it only from `heap_attrinfo_read_dbvalues()` and `heap_attrinfo_read_dbvalues_without_oid()` when the recdes has OOS. Single-attribute helper paths stay scalar in phase 1.

## Remarks

Non-goals:

- No OOS OID sharing or deduplication.
- No inline OOS format change.
- No multi-column combined OOS record format.
- No continuation-page locality optimization in phase 1.
- No short-head/full-continuation multi-chunk layout change.
- No replication log format change.
- No broad heap attribute read refactor outside requested-column OOS batching.

Risk notes:

- Replication OID order is fragile, so tests must cover attribute-order preservation.
- The implementation must choose the target OOS page before holding the batch write fix.
- Partial insert failure must clear transient publication state and rely on enclosing topop or transaction abort for physical cleanup.
- Batched lazy read adds temporary buffers, so ownership and error cleanup need to stay simple.
