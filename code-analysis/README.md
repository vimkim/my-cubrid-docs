# CUBRID analysis library

Created: 2026-10-21. Last modified: 2026-10-21 (Asia/Seoul).

Start here for analyses of CUBRID subsystems and build tooling. Each report has
its own source revision and verification limits. Ticket-specific findings and
PR decisions remain in the relevant ticket directory.

| Topic | Entry point | What to read here |
| --- | --- | --- |
| Page buffer | [Page-buffer index](pgbuf/README.md) | Structures, fix/unfix, latches, replacement, durability, research, and presentations |
| Build and tooling | [Build index](build/README.md) | Compiler performance, third-party CI caches, and build coordination |
| Lock Manager and MVCC | [Lock Manager book, f30f1c2](lock-lock-manager-self-lock-mvcc-lock/f30f1c2_codex/index.html) | Resource identity, ownership, waiting, deadlocks, MVCC policy, and self-locks |
| Server-side loaddb locking | [Loaddb locking book, f11fc42](cbrd-27157-server-side-loaddb-locking-transaction-mvccid-self-lo/f11fc42_codex/index.html) | BU locks, transaction ownership, and MVCCID self-locks in CBRD-27157 |
| SX page latch and asynchronous I/O | [Codex report](cbrd-27196-sx-page-latch-aio-direct-i-o-cubrid/f799e05_codex/index.html), [Claude report](cbrd-27196-sx-page-latch-aio-direct-i-o-cubrid/f799e05_claude/index.html) | Revision-specific CBRD-27196 analysis and verification |
| OOS and vacuum | [OOS/vacuum book, 07fef9d](cbrd-26950-oos-vacuum-delete-overlap-oos-lsa-generation-id-vacuu/07fef9d_claude/index.html) | Overflow deletion, identity, lifecycle, and vacuum interaction |

The former top-level `pgbuf-analysis/` and `build-analysis/` collections moved to
`pgbuf/` and `build/` on 2026-10-21. Existing report names and historical findings
were preserved. Page-buffer books already under `code-analysis/` remain at
their established paths and are linked from the page-buffer index.

Follow [repository guidance](../AGENTS.md#where-documents-belong) when adding or
revising an analysis.
