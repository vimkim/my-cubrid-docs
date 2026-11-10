# Handoff: follow-up for the PR #8434 review at 8e139f4db

1. **Goal and stop reason.** The author wants evidence-backed review before PR #8434 is marked Ready. The review found no confirmed defect. It stopped with `incomplete` for two reasons: the growth-lock throughput risk U-1 is unmeasured, and two test gaps (U-6) remain.
2. **Identity.**
   - PR: https://github.com/CUBRID/cubrid/pull/8434, compared in PR mode.
   - Base and merge base: `95ff126a8464179a2fab3092b6f56468528ab954`. Head: `8e139f4dbb2635058032d0b9dafd5f624c726754`.
   - Patch SHA-256: `95b4fec7dc07ac3e130feee256c258013cf83751ce701d1a9b0fbb119e468f61`.
3. **Locations.** The [report](report.md) and [coverage](coverage.md) sit next to this file. The previous review is `../code-review-pr8434-3e8072f/`. ADR-0008, ADR-0009, and ADR-0010 are in `cubrid-oos-context/docs/adr/`.
4. **Open IDs.**
   - U-1: performance, needed.
   - U-6: tests, optional.
   - U-2 to U-5: P3 source-only risks for author triage.
   - Design questions: an indefinite retry on a persistent header read error; OOM fail-stop on unpack; serial-path latency.
   - No reviewer disagreement. The shared questions Q1 and Q2 were answered the same way independently.
5. **Remaining scope.**
   - Measure U-1. Run 16-64 threads inserting values that fill one page each into one OOS file. Compare `c255c7c3b` with `8e139f4db` in the same build type with a warm cache, recording throughput and futex wakeups (`perf trace` or `perf stat -e syscalls:sys_enter_futex`).
   - Optionally, a CLR-redo crash variant: crash again during the undo phase of a loser that holds an RVOOS_INSERT.
   - Optionally, a test that reaches `file_alloc` while a second grower waits on the growth lock.
6. **Environment.**
   - Worktree `/home/vimkim/gh/cb/CBRD-27781-postpone-commit`, preset `debug_gcc`. Configure with `-DUNIT_TESTS=OFF -DUNIT_TEST_OOS=ON -DUNIT_TEST_SPAGE=ON -DUNIT_TEST_PAGE_BUFFER=ON`. Plain `just configure` turns the unit-test seams off.
   - Use a release build for U-1. The machine is shared and heavily loaded, so state the load average with every number (see `benchmark-checklist`).
7. **Budget.** The original envelope is spent. Each item above needs a new allocation.
8. **Proposed assignments.**
   - One performance seat for U-1. It is complete when before-and-after numbers with variance exist and the futex count supports or refutes the herd.
   - One test seat for U-6. It is complete when both probes run against head.
9. **Finish conditions.** U-1 is measured, or the author accepts it as recorded. If a fix lands, review the delta against the safety facts Q1 and Q2 and the lock-order fact in the report.

Resume request: `/cubrid-code-review` follow-up for CUBRID/cubrid#8434, base `95ff126a8`, head `8e139f4db`, manifest in the review run directory. Open items: U-1 (measure) and U-6 (tests).
