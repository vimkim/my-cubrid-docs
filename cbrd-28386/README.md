# CBRD-28386

[TDE] Catalog file records (class representation and statistics) keep uninitialized server memory in the bytes that no field covers.

- JIRA: <https://jira.cubrid.org/browse/CBRD-28386>
- Engine PR: not created yet (draft prepared)
- Related: [CBRD-28257](../cbrd-28257/README.md) (catalog class heap rows, CUBRID/cubrid#8693)

| File | What it contains | Created | Last modified | Why it was created |
| --- | --- | --- | --- | --- |
| [verification-report.md](verification-report.md) | Audit of the catalog record writers, before/after reproduction, regression test results and independent review findings at `d16738b08f` | 2026-11-25 | 2026-11-25 | Record the evidence for the fix |
| [pr-body.md](pr-body.md) | Draft PR body for the engine change | 2026-11-25 | 2026-11-25 | Prepare the PR description for review |
| [pr-context.md](pr-context.md) | PR draft metadata, proposed operations and their authorization | 2026-11-25 | 2026-11-25 | Resume and audit the PR publication |
