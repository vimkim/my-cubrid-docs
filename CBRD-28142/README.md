# CBRD-28142

Backups taken while vacuum is disabled (`vacuum_disable=yes`) must keep every log archive that vacuum will read once re-enabled.

Related PRs: [CUBRID/cubrid#8721](https://github.com/CUBRID/cubrid/pull/8721) (engine, author `hornetmj`); TC PR cubrid-testcases-private-ex#5126 (private).

| File | What it contains | Created | Last modified | Why it was created |
| --- | --- | --- | --- | --- |
| [pr8721-review.md](pr8721-review.md) | Code review of PR #8721 at head `5d6b8cc8fb`: no confirmed findings, safety facts with head/base TC runs and archive-gap probes, non-blocking suggestions for the engine and TC | 2026-11-26 | 2026-11-26 | Review PR #8721 and its TC PR and decide approval |
