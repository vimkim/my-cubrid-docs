# Ticket 21 standards review

Reviewed `git diff f4299ac0cd777a2a964c1f197ae5ebf9841a4936...HEAD` at `ab3d8d645`, including the production and test changes. Sources: root and `src/AGENTS.md`, the loaddb/query/storage/transaction guidance, and `unit_tests/AGENTS.md`. Applied the approved prepared-row ownership/error-boundary contract; omitted tooling-enforced formatting checks.

1. **Documented violation — guard new C++ member calls in legacy C files.** `src/query/query_executor.c:11959,11967,12000,12184,12192,12218` introduces `prepared.prepare (...)`, `prepared.read_values (...)`, and `prepared.record (...)` outside INDENT guards. `src/storage/heap_file.c:14545,15109` likewise introduces `prepared->read_value (...)` outside guards. The supplied root guidance requires “any C++-specific syntax in those files” to be wrapped in exact `/* *INDENT-OFF* */` / `/* *INDENT-ON* */` markers; `.scratch/oos-deferred-write/map.md` repeats that requirement. Guard these statements as well as the already guarded owner declarations. This concerns the explicit marker contract, not whitespace/style that the formatter checks.

2. **Judgment call — possible Duplicated Code in runtime isolation.** `unit_tests/oos/scripts/test_oos_replication.py:45` and `test_oos_transactions.py:93` repeat `writable = {"var", "log", "tmp", "databases", "conf"}`, the installation-child symlink loop, writable-directory creation, and runtime `CUBRID` assignment. Extract that complete operation into the shared fixture helper already imported by both runners. Keeping this isolation boundary in one place prevents future installation-directory changes from fixing only one runner.

## Resolution review

Reviewed the subsequent `git diff HEAD` and new `unit_tests/oos/scripts/README.verification.md`. Both original findings are resolved in the working tree:

- All eight identified C++ member-call statements now have exact INDENT guards; surrounding code retains its indentation.
- `LoaderFixture.isolate_runtime` owns the shared runtime construction, and replication/transaction fixtures both call it with their installation path. The extracted operation preserves the previous behavior.

The verification README uses standard CTest/configuration commands, distinguishes external runners from CTest, and states evidence limitations without claiming unperformed checks passed. No additional standards findings. Build and external-run verification remain with the parent workflow. The displayed dirty `cubrid-cci` submodule is outside these repairs and was not reviewed internally.

Standards: 2 original findings, both resolved; 0 outstanding findings.
