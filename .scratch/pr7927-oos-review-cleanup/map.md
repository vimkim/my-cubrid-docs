# PR7927 approved work map

Status: active
Approved: 2026-10-07. [Spec](spec.md).

| Task | Status | Blocked by |
|---|---|---|
| [01 Explicit-owner prepared-row access](issues/01-explicit-owner-access.md) | resolved | None |
| [02 Remove marker and enforce publication boundaries](issues/02-remove-marker.md) | claimed | 01 |
| [03 Reconcile reviewer dispositions and local replies](issues/03-reviewer-dispositions.md) | ready-for-agent | 02 |
| [04 Publish current documentation entry point](issues/04-current-documentation.md) | ready-for-agent | 02, 03 |

## Comments

2026-10-07: User approved design, testing seams and task granularity/dependencies.
Work-tracker 281 records completed design agreement; 284 records documentation
and comment assessment. Engine implementation is authorized. Unrelated source
submodule changes are preserved; no remote action is authorized.

2026-10-07: Task 01 committed at c73f01c1d with debug build/install and SQL
ownership checks. Task 02 claimed. Verification logs are preserved under the
current design evidence directory.
