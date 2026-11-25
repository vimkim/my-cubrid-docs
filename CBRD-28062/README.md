# CBRD-28062: Configurable OOS trigger threshold

Ticket: https://jira.cubrid.org/browse/CBRD-28062

| Document | Purpose |
| --- | --- |
| [pr-body.md](pr-body.md) | PR description for the `oos_trigger_threshold` engine change (source `49d8df0dd5`, base `feature/oos-merge`) |
| [pr-context.md](pr-context.md) | Draft metadata, proposed operations, and execution record for that PR |
| [review-claude.md](review-claude.md) | Systemic review of PR #8632 at `44dab49185` (Claude Opus coordinator with three reviewers): serial regrowth (F1) and restoredb late check (F2), fixed in `2395d5a8f6` |
| [systemic-review-sonnet.md](systemic-review-sonnet.md) | Independent systemic review of PR #8632 at `44dab49185` (Claude Sonnet): same two defects (S2, S1) plus parameter and test findings |
| [perf-sweep.md](perf-sweep.md) | `oos_trigger_threshold` sweep (0 → 16,236) against develop: AC-P2 reads, small-column reads, INSERT/UPDATE, storage, I/O; harness and data in [perf-sweep/](perf-sweep/) |
| [ci-analysis.md](ci-analysis.md) | Warning-mode CI analysis of PR #8632 at `dc1b83a33b` (run 45549760101, 2026-11-25): `test_shell` `cbrd_27780` failure is known CBRD-28257; `test_sql` evidence failed the collector integrity check; no merge-base baseline |
| [ci-analysis-7544aced71.md](ci-analysis-7544aced71.md) | Warning-mode CI analysis of PR #8632 at `7544aced71` (run 45598259772, 2026-11-25, cubrid-ci-watch request 104): 2 shell and 3 sql_by_cci failures, all also seen on other PRs on newer develop bases; `test_sql` evidence failed the integrity check; merge-base run still running |
