# [CBRD-27006] OOS locality glossary

## Purpose

This file preserves the local terminology used while implementing CBRD-27006. It is intentionally small and only covers terms introduced or sharpened for this change.

## Implementation

**Single-page OOS batch**:
A contiguous group of OOS values from one heap record that is treated as one placement unit because it belongs together on a single OOS page.

_Avoid_: subrun, page-sized subrun

**OOS insert publication**:
The complete registration of a successful OOS insert result while master-side replication tracking is active. It comprises OOS OID publication and OOS LSA publication while preserving logical attribute order.

_Avoid_: replication transmission, commit publication, OOS OID publication

**OOS insert publication state**:
The transient, ordered pairing of published OOS OID entries and their corresponding WAL locations for one logical OOS insert operation with master-side replication tracking active.

_Avoid_: OOS data, replication log, OOS insert result list

**OOS OID publication**:
The OID side of OOS insert publication, produced for a successful result while master-side replication tracking is active.

_Avoid_: OOS insert publication, caller-side OOS OID push

**OOS LSA publication**:
The WAL-location side of OOS insert publication, produced by OOS WAL processing while master-side replication tracking is active.

_Avoid_: OOS insert publication, replication-log creation

**Logical OOS insert preparation**:
The record-scoped operation that stores all attributes selected for OOS demotion and produces one coherent publication state. It ends when that state is ready for handoff; later heap-record assembly is outside its boundary.

_Avoid_: serialization call, batch API call, individual OOS value insert

**Replication-apply OID accumulation**:
The transient, ordered list of slave-local head OOS OIDs produced by consecutive OOS apply items and consumed by their following heap-row apply. It has no LSA side and is not OOS insert publication state.

_Avoid_: slave publication state, OID/LSA publication, per-item OID result

## Remarks

Use "OOS OID", "OOS file", "OOS record", "single-page OOS batch", and the state terms above consistently in PR discussion. Say "OOS OID publication" only for the tracked master-side OID entry; reserve "OOS insert publication" for the complete tracked OID/LSA registration. When replication tracking is disabled, an API-produced OID without an LSA is not a complete publication. On the slave apply path, say "replication-apply OID accumulation" because those OIDs rewrite the following heap row and have no LSA side. These terms match the CBRD-27006 implementation and avoid implying a new OOS format or OID-sharing behavior.
