# Source and claim audit

Source: PR #7600, HEAD `479cd960ec04196c92bf9789b1fc340af9046c2c`, merge-base `f4299ac0cd777a2a964c1f197ae5ebf9841a4936`.

- The generator checks the checkout HEAD, parses the frozen diff, checks hunk line counts and maps all 63 hunks across 10 modified files to explanatory annotations. All added/deleted source lines are preserved. Related lines are explained as semantic blocks.
- The SQL appendix maps 28 added tests individually. Four earlier tests remain in the 32-test source suite. The separate rollback/vacuum addition is explicitly disabled.
- Current code routes the effective key before the main full-row transformation and passes the selected OOS owner without replacing source attrinfo identity. Final record routing and expected-destination guards remain. This is two routing evaluations, not two main-path full-row transformations.
- Effective-key explanations were checked against initialization, old-record/default/assigned branches, copied increment state, codec normalization and cleanup in heap_file.c. Ownership and movement explanations were checked against locator_sr.c, partition.c and the unchanged heap_oos.cpp boundary.
- Probe suppression depends on pointer presence and covers forced and ordinary demotion. It is not described as a universal side-effect-free or no-I/O guarantee. Retained two-pass APIs are distinguished from the current primary path.
- The checked-out OOS inline size is 16 bytes. The separate normative 24-byte design is not attributed to this PR.
- Existing vacuum source explicitly aborts on the missing owner-file condition. The existing move helper inserts the destination before deleting the source. Explanations follow executable statements where nearby comments could mislead.
- The 32/32 SQL result is attributed to the historical review at parent 988a4d2, including its CCI mismatch. Production and SQL changes are identical between that parent and HEAD; HEAD adds the disabled vacuum regression. No engine tests were executed to produce these documents.
- SERVER_MODE lifecycle evidence, control workload performance acceptance and final integrated evidence remain open in the historical review. The report does not certify merge readiness.
- All three GitHub PR comment streams were captured: zero inline comments, zero review records, seven discussion comments. Historical review discussion is linked rather than invented as current reviewer feedback.
- English authoring precedes the Korean version, with matched hunk/test identifiers and fixed source references. The Korean HTML uses the Korean Markdown guide and the paired annotations.

Artifact behavior is separately recorded in validation.json. Chromium checks cover offline operation, graph rendering/tours, reading-page search, desktop/mobile layout and absence of JavaScript exceptions. Browser rendering does not validate database behavior.
