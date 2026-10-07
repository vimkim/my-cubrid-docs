# 04: Publish current documentation entry point

**What to build:** Readers can enter through one current CBRD-27089 index and
reach agreed design, active/completed tasks, current verification and reviewer
drafts without confusing superseded explanations with current behavior.

**Blocked by:** 02 Remove marker and enforce publication boundaries; 03 Reconcile reviewer dispositions and local replies.

**Status:** resolved

- [x] One current entry point links design, spec/tasks, verification and reviewer dispositions.
- [x] Current terminology matches the approved owner/reference/finalization design.
- [x] Superseded architecture and task entry points are dated and marked historical or archived.
- [x] Historical verification and private source scratch/database/core artifacts are preserved.
- [x] Existing exact-head CI evidence is reused with its original revision and limitations.
- [x] Broken links are repaired where authentic targets exist; unavailable historical evidence is explicitly identified.
- [x] Changed Markdown link checks and diff checks pass; meaningful documentation changes are locally committed.
- [x] Work-tracker and local task status reflect actual completion and remaining limitations.

## Answer

2026-10-07: [CBRD-27089 README](../../../cbrd-27089/README.md) is the current entry point.
Current design, verification, review, tasks and local replies are linked.
Historical entry points, PR7600 scope and the withdrawn POC are labeled; original
evidence remains. Exact aecce0e CI package was reused from docs commit 71bcfef as
c6c402d. Two ADR links were repaired; 36 unavailable historical targets retain
original paths in an explicit inventory. Two source scratch notes were labeled
historical and durable text/provenance copies retained in docs; private DB/core
artifacts were untouched. Local link checks and diff checks pass. Remote CI
attribution remains a separate work item 242.
