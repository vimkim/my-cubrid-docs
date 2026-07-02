# [CBRD-27006] OOS insert publication is owned by public OOS insert APIs

## Purpose

OOS insert publication means appending the OOS OID entries that later drive replication logging. Before CBRD-27006, this responsibility could be split between OOS insert helpers and their callers, which became fragile once scalar insert and batch insert had to share one contract.

- AS-IS: A caller could receive an OOS OID from `oos_insert()` and then push it into `thread_p->oos_oids` itself.
- TO-BE: Public OOS insert APIs publish OOS OIDs themselves. Callers clear tracking state before the OOS write operation and do not push returned OIDs again.

## Implementation

`oos_insert()` publishes the returned head OOS OID on success. `oos_insert_many()` publishes each request result in logical request order. For multi-chunk values, the existing dummy marker and head OID behavior is preserved, so replication can still distinguish a boundary marker from the real head OID.

This contract is important for mixed single-chunk and multi-chunk rows. Dummy markers and real head OIDs must stay in attribute order because `locator_fixup_oos_oids_in_recdes()` consumes `thread_p->oos_oids` while walking the replicated heap record's OOS-marked attributes.

The scalar caller in `src/transaction/locator_sr.c` no longer pushes the returned OID itself. The public OOS header exposes `oos_insert()` and `oos_insert_many()`, but does not need a caller-side publication helper.

## Remarks

Reviewer focus:

- Confirm that each logical OOS attribute publishes exactly one real head OID, with the existing dummy marker only for multi-chunk replication boundaries.
- Confirm that callers clear transient OOS publication state before insert and do not add duplicate OIDs after the public insert API returns.
- Confirm that failure paths clear transient publication state when `oos_insert_many()` has already published partial results.
