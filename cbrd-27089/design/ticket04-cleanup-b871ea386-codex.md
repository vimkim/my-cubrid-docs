# Ticket 04 — failure cleanup verification

Status: ticket04 resolved. Focused cleanup proofs and affected SQL suites pass. The complete configured suite remains red only on the separately preserved rollback/vacuum defect after infrastructure-only reruns. No engine behavior was changed by this ticket.

Candidate source: original PR #7600 head `b871ea386d2c5419b7abae07dda58b9b7f36377a` plus tickets 01–03 engine diff SHA-256 `3d978ff8134516d0ab26a809b6fd790bd289a6865476a215921c8fa5e6eea34a`. Every evidence JSON captures its own build/library/test provenance and private fixture. Main verification uses debug_gcc; the explicit original-PR corroboration below uses release_gcc and is labeled accordingly.

## Focused proofs

| Category | Test/evidence | Observations |
|---|---|---|
| Partial publication, preparation reset, VFID lookup, publication allocation | [eight INSERT/moving-UPDATE scenarios](ticket04-evidence/four-preparation-failures.json) | Exact errors; abort restores original values and physical OOS counts; root has no OOS; next valid destination write succeeds and is rolled back cleanly. Mixed 64-byte and 20,000-byte values force separate publication iterations. |
| Failed routing/context reuse | [routing publication preservation](ticket04-evidence/routing-failure-publication.json) | Alternating valid/invalid/valid keys preserve cached assignments, uninitialized payload, seeded OID publication vector and LSA queue; successful routes pick the correct child; no OOS files are created. |
| Effective-key codec failure | [write/read codec failures](ticket04-evidence/codec-failure-cleanup.json) | Private codec/domain metadata only, no global schema mutation. Failed read deliberately populates an owned output; helper clears it, preserves the source assignment, and succeeds on the next call. |
| Actual OOS payload allocation failure | [serializer allocation failure](ticket04-evidence/payload-allocation-cleanup.json), [observer](ticket04-evidence/fail-payload-allocation.gdb) | malloc returns NULL inside heap_attrinfo_dbvalue_to_recdes for one INSERT and one moving UPDATE. Exact OOM, rollback, owner counts and subsequent write checks pass. This is an allocation failure during serialization, not a test of every primitive codec's error behavior. |
| Final index error, written/unchanged LOBs | [LOB/index rollback](ticket04-evidence/lob-index-cleanup.json) | Original CLOB and demoted BLOB values remain readable after injected failure or duplicate-key rejection. Error log identifies the destination B-tree uniqueness check (-670); current test asserts the exact error. Next valid moving UPDATE succeeds. |
| LOB retry and external lifetime | [retry/lifetime evidence](ticket04-evidence/lob-retry-lifetime.json), [observer](ticket04-evidence/force-lob-retry.gdb) | Forced real transform retry: two column attempts, exactly two LOB copies and two logical deletions. All six aborts restore the original four external-file paths and SHA-256 values. No repeated physical deletion within a transaction interval; teardown leaves no external files. |
| Existing server publication contract | [server publication tests](ticket04-evidence/candidate-publication.json) | Existing eleven publication/reset/cleanup cases pass. Final full-suite rerun remains separately tracked. |
| Original PR corroboration | [original release cleanup run](ticket04-evidence/baseline-cleanup-release.json) | Both SQL cleanup tests pass on the unchanged original engine, using a retained test-only overlay. Not a same-build-mode performance comparison. |

Faults are test-only existing hooks or scoped debugger actions; no production fault framework was added. The regular publication-allocation test and the debugger payload-allocation variant are separate runs: the latter intentionally fails earlier and disarms the unused later hook.

The failed early smoke attempts were fixture mistakes, retained for audit: too-small values were not OOS-eligible, same-page batching did not reach the next publication iteration, and VARBIT SQL comparisons needed explicit casts. They are not reported as engine regressions.

## Retry/cleanup interpretation

Durable rollback is established by stored values and owner counts, not merely freeing buffers. For LOBs, readable originals alone would not exclude leaked new files, so the added inventory observer checks exact external-file identities/content after each abort. It also counts logical deletions during the forced retry and physical deletion identities across transaction intervals.

The scalar codec test restores the original attribute representation before any assertion or next call. It checks output ownership and unchanged assignments. It is not an exhaustive allocator-failure campaign or a proof of every possible corruption case.

Existing ticket02/03 coverage supplies OOS-plus-big-record rejection, nonpartitioned behavior, REPLACE/duplicate UPDATE, pending increments and unchanged values. The full configured-suite pass below must recheck the affected SQL binaries on the final test build; previous milestone reports are not substitutes for that run.

## Full-suite safety and infrastructure

The normal generated CTest setup/cleanup commands contain shared installation/database paths. They were not executed. [The retained runner](ticket04-evidence/run-configured-isolated.py) enumerates the actual CTest catalog, checks all 25 binary commands, and runs each unfiltered with its own setup/config/database and a recorded 600-second diagnostic timeout. Fixture setup/cleanup are replaced by fresh private databases retained for inspection.

A first premature launch overlapped a rebuild and was stopped; `full-test-oos.json` is not acceptance evidence. The post-build sequence is `verified-full-*`.

The first SERVER_MODE startup attempts failed before assertions because their private paths produced an oversized PL Unix socket address. The Java log reports `SocketException: Byte array is too large` at AFUNIXSocketAddress. Source: pl_comm.c:228 chooses CUBRID_TMP or the runtime var directory. The runner now supplies a unique short socket-only CUBRID_TMP directory under /tmp; database storage remains under the private /home fixture. No shared socket or database is reused, and no engine setting disables PL.

Final suite: all 25 configured binaries were executed without test filters. The [raw suite ledger](ticket04-evidence/configured-suite-results.json) records 21 passing binaries, three startup failures, and the known vacuum failure. With only the private socket path corrected, the three affected binaries pass: [34 server tests](ticket04-evidence/short-socket-full-server.json), [7 delete tests](ticket04-evidence/short-socket-full-delete-server.json), and [7 file-removal tests](ticket04-evidence/short-socket-full-remove-file-server.json). Thus 24/25 binaries pass after classified infrastructure reruns; this is **not an all-green suite**.

All [32 SHOW/routing/cleanup tests](ticket04-evidence/verified-full-test-oos-sql-show.json) pass on the final debug build, as do all other configured SQL binaries. The real-vacuum binary passes its first ten tests then fails RolledBackUpdateKeepsCommittedOosAfterVacuum at the same committed-value read (-2) already reproduced on the original PR. The red test remains intact. Per-binary JSON retains exact library/binary hashes; the shared database was never used.

## Review

Standards axis: no hard non-tooling-enforced violations; one optional Primitive Obsession suggestion for numeric scenario/operation tags. Existing white-box contract tests and large files follow this repository's practice.

Spec axis initially identified missing actual payload-preparation failure and missing external LOB deletion/lifetime evidence. Both were closed by the two retained diagnostics above after re-review. This does not waive the separate full-suite, runtime-acceptance, or server lifecycle gates.

CBRD-27237's known rollback/vacuum regression remains preserved and blocks tickets 05/07. No vacuum repair or acceptance waiver was made. A local implementation/documentation commit is the handoff step; no push is authorized by this work.

The commit hook normalized formatting within the added/modified01–04 code, with no unrelated pre-existing engine indentation changes. Comparing staged pre-format contents to the formatted files after removing whitespace found identical content for all six affected files. The formatted engine diff SHA-256 is `8ccb237954a348b5bef6f1b653dbe44e31816ba5c21d3b856f0d0c33684a215c`; the paired measurement worktree and its original hash remain unchanged. A fresh debug rebuild completed after formatting; the full SHOW/routing/cleanup binary is rerun separately before commit.

Local implementation commit: `213ce80f54dc54130fcef22e616cb28f4835f6d5`. It includes the prior01–03 implementation dependencies and04 tests. All [32 post-format SHOW/routing/cleanup tests](ticket04-evidence/formatted-routing-cleanup.json) pass. The separately authored05 red vacuum test remains unchanged and uncommitted in the worktree; unrelated CCI and user files were not staged. No push occurred.
