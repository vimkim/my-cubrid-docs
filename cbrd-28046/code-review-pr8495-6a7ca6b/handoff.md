# Handoff: review of CUBRID/cubrid#8495

1. Goal: confirm that CBRD-28046 (one log flush per commit with postpone actions) keeps durability and atomicity. The review stopped at `incomplete` because R-3 lacks execution evidence.
2. PR https://github.com/CUBRID/cubrid/pull/8495, base/merge base `2d1513a8afe6c843388e916fcdf34483b78a2051`, head `6a7ca6b4a89e5dd96bfea81b9f6655893641b9a7`, patch sha256 `6d30317c5ef1383d0c6f9f57ec0aaa9819d53621b2e6a1761c8d059e33daf12d`.
3. Report: [report.md](report.md); coverage: [coverage.md](coverage.md); crash scripts: [../test/](../test/).
4. Open: R-1 (restated: CBRD-27964 direct LOB delete before a durable commit; pre-existing, window widened for postpone transactions; fix belongs to CBRD-27964), R-2 (pre-existing `nxio_lsa` comparison in `logpb_flush_pages`), R-3 (file_destroy page discard then CWP lost). No confirmed findings.
5. Remaining scope: R-3 runtime check with a checkpoint; 2PC participant crash path; ctest and gha-ci results.
6. Environment: a debug build of the head with fault injection, run serially; release install of the head for crash scripts.
7. Budget: the three reviewer assignments are spent; new work needs a new allocation.
8. Proposed assignments: (a) R-3: `FI_TEST_FILE_MANAGER_DESTROY_HOLD`, checkpoint, crash before CWP is durable, `checkdb`. (b) R-2: instrument `logpb_flush_pages` return.
9. Finish when R-3 is verified safe or reproduced; rerun the review delta if the head moves.

Resume: run cubrid-code-review with manifest `manifest.md` in this run directory, scope base `2d1513a8af` head `6a7ca6b4a8`, unresolved R-2, R-3 (R-1 tracked in CBRD-27964).
