# [CBRD-27006] OOS locality glossary

## Purpose

This file preserves the local terminology used while implementing CBRD-27006. It is intentionally small and only covers terms introduced or sharpened for this change.

## Implementation

**Single-page OOS batch**:
A contiguous group of OOS values from one heap record that is treated as one placement unit because it belongs together on a single OOS page.

Avoid: subrun, page-sized subrun

**OOS insert publication**:
The public OOS insert API's responsibility to append the OOS OID entries that later drive replication logging.

Avoid: caller-side OOS OID push, split publication

## Remarks

Use "OOS OID", "OOS file", "OOS record", "single-page OOS batch", and "OOS insert publication" consistently in PR discussion. These terms match the CBRD-27006 implementation and avoid implying a new OOS format or OID-sharing behavior.
