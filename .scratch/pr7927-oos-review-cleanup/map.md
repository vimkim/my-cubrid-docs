# PR7927 approved work map

Status: resolved
Approved: 2026-10-07. [Spec](spec.md).

| Task | Status | Blocked by |
|---|---|---|
| [01 Explicit-owner prepared-row access](issues/01-explicit-owner-access.md) | resolved | None |
| [02 Remove marker and enforce publication boundaries](issues/02-remove-marker.md) | resolved | 01 |
| [03 Reconcile reviewer dispositions and local replies](issues/03-reviewer-dispositions.md) | resolved | 02 |
| [04 Publish current documentation entry point](issues/04-current-documentation.md) | resolved | 02, 03 |

## Comments

2026-10-07: User approved design, testing seams and task granularity/dependencies.
Work-tracker 281 records completed design agreement; 284 records documentation
and comment assessment. Engine implementation is authorized. Unrelated source
submodule changes are preserved; no remote action is authorized.

2026-10-07: Task 01 committed at c73f01c1d with debug build/install and SQL
ownership checks. Task 02 claimed. Verification logs are preserved under the
current design evidence directory.

2026-10-07: All four tasks resolved. Source local HEAD 6b53181d3;
debug CTest 35/35, assertions-disabled focused checks and real server-loader
fixture pass. Standards 0 and Spec 0 remaining findings. Current index and
historical link/status cleanup are complete; reviewer replies remain local.
Work-tracker 281 design, 289 implementation and 284 docs/comments are complete.
No remote action or integration merge was performed.
