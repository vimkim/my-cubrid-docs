# CBRD-27800

Keep HA `applylogdb` from reusing the `RECDES` buffer of an unflushed replication item when `pending_oos_flush` defers flushing past `LA_MAX_UNFLUSHED_REPL_ITEMS` (200), return failed item buffers, and restart `applylogdb` on `ER_OUT_OF_VIRTUAL_MEMORY`.

Related PRs: [CUBRID/cubrid#8761](https://github.com/CUBRID/cubrid/pull/8761) (engine, author `H2SU`); TC PR `cubrid-testcases-private-ex#5173` (private, draft, no changed files yet); [CUBRID/cubrid-testcases#4482](https://github.com/CUBRID/cubrid-testcases/pull/4482) (public, draft, no changed files yet).

| File | What it contains | Created | Last modified | Why it was created |
| --- | --- | --- | --- | --- |
| [pr8761-review.md](pr8761-review.md) | Code review of PR #8761 at head `83bfa2dbff` (`changes-required`): confirmed `need_oos_rebuild` & `pending_oos_flush` retry findings (`F-01`, `F-02`), `la_realloc_recdes_data` OOM finding (`F-03`), real-code Valgrind probe results, safety facts, unverified risks, TC PR assessment | 2026-11-26 | 2026-11-26 | Review PR #8761 and linked TC PRs before approval |
