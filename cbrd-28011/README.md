# CBRD-28011

SQL trace shows the OOS share of a scan's fetch, ioread and time.

- PR: https://github.com/CUBRID/cubrid/pull/8491 (draft, base `feature/oos-merge`).
- TC PR: https://github.com/CUBRID/cubrid-testcases/pull/4148.

| File | What it contains | Created | Last modified | Why it was created |
| --- | --- | --- | --- | --- |
| [pr-body.md](pr-body.md) | Draft PR body (target `feature/oos-merge`) | 2026-11-11 | 2026-11-11 | Prepare the PR description |
| [pr-context.md](pr-context.md) | Draft context and proposed publication operations | 2026-11-11 | 2026-11-11 | Record PR publication context |
| [code-review.md](code-review.md) | Review of PR #8491 at head `a4fec6f8e2`: verdict, safety facts, runtime trace evidence, open risk R-1 | 2026-11-12 | 2026-11-12 | Independent code review of the PR |
| [oos-read-validation-handoff.md](oos-read-validation-handoff.md) | Fresh-session investigation of review 5914646248, OOS reference lifetime, allocation checks, and runtime evidence | 2026-11-17 | 2026-11-17 | Verify the reviewer's premises independently of earlier chat conclusions |
| [oos-read-validation.md](oos-read-validation.md) | Answer to review 5914646248: two reproduced SQL paths to a stale OOS head (UPDATE rollback + vacuum, PL/CSQL COMMIT + DROP), fetch attribution of the allocation check, debug and release probe sensitivity, Korean reply draft | 2026-11-17 | 2026-11-17 | Answer the reviewer with runtime evidence at `a4fec6f8e2` |
