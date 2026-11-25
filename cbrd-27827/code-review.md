# PR 8330 code review

This independent review checks whether removing the forced-zero-wait scope fixes concurrent OOS INSERT failures while preserving page selection, cleanup and recovery/replication contracts. It is for the PR author and engine reviewers. No introduced engine defect was confirmed in the inspected scope. The submitted test tool has a verified coverage gap described below.

Review date is 2026-11-04, Asia/Seoul. The delta verdict is `no-confirmed-findings`. Follow-up review required is **yes** for the requested automated regression coverage, controlled contention checks and inherited rollback/vacuum concern. This verdict is not a merge approval. Source coverage is complete; runtime evidence is bounded by the executed tests.

## Fixed scope

| Item | Value |
| --- | --- |
| PR and issue | [CUBRID/cubrid#8330](https://github.com/CUBRID/cubrid/pull/8330), [CBRD-27827](https://jira.cubrid.org/browse/CBRD-27827) |
| Base branch | `feature/oos-merge` |
| Remote base and merge base | `dcbf09e4f7fd02ff9c8fc6493ec8887fc2919d67` |
| Head | `4db11c5f12f9c67134aad7f547df8704d1e5c591` |
| Binary-capable patch SHA-256 | `fb280e72f69436275decdbe7441bb2b0e548127f2d2a1a13e64a1891549b650a` |
| Inventory | `src/storage/oos_file.cpp`, seven removed lines; new `unit_tests/oos/scripts/test_oos_concurrent_insert.py`, 130 lines. No deletion, rename, submodule or binary change. |
| Source and tests | Clean detached head. Tests come from the same engine revision. No submitted-source edit or instrumentation. |
| Specification | OOS normative specification SHA-256 `6300aa1fa6ffb54033b9c7f7ea959466e9d88f0530e1ab0d7178b4459d4fcf63`, plus the live CBRD-27827 description. |

The literal comparison was:

```sh
git diff --binary --full-index dcbf09e4f7fd02ff9c8fc6493ec8887fc2919d67 4db11c5f12f9c67134aad7f547df8704d1e5c591
```

## Safety facts and changed behavior

The affected shared state is the transaction descriptor's `wait_msecs`, the OOS stats-header latch, a candidate data-page latch and the file-manager header/table latches. The removed calls temporarily changed the transaction descriptor to forced zero wait. They did not merely change a local variable. That override also reached the ownership check's otherwise unconditional file-header read and could turn ordinary metadata contention into an INSERT error.

The candidate data-page acquisition remains explicitly conditional. A busy candidate is skipped; the buffer manager does not promote that request to an unconditional wait. Removing the override lets ownership metadata use the caller's original effective policy. A caller already using zero wait retains zero-wait behavior. Normal page-latch timeout and interruption still apply. This is not a guarantee of zero total latency for a conditional fix, which can still involve I/O or buffer-management work. [Candidate search and cleanup](https://github.com/CUBRID/cubrid/blob/4db11c5f12f9c67134aad7f547df8704d1e5c591/src/storage/oos_file.cpp#L560-L765), [ownership metadata read](https://github.com/CUBRID/cubrid/blob/4db11c5f12f9c67134aad7f547df8704d1e5c591/src/storage/file_manager.c#L6906-L7028), [policy resolution](https://github.com/CUBRID/cubrid/blob/4db11c5f12f9c67134aad7f547df8704d1e5c591/src/storage/page_buffer.c#L2247-L2256).

A candidate stays WRITE-latched while its page type, file membership and free space are checked, and through handoff to the inserter. Ownership failure unfixes it; the caller then releases the stats header. The bestspace hash mutex is released before candidate fixing or metadata lookup. The inspected ordinary reverse edges do not complete a cycle: same-file reclaim needs the same stats-header latch before deallocation, delete-side stats update acquires that header conditionally, and allocator initialization retains its new-page latch until file metadata is released. A previously allocated candidate is not a newly selected free page. These are level-3 source disproofs for those paths. The CS stress run exercises actual concurrency but does not force the newly permitted metadata-wait edge. [Caller](https://github.com/CUBRID/cubrid/blob/4db11c5f12f9c67134aad7f547df8704d1e5c591/src/storage/oos_file.cpp#L3011-L3155), [stats updates](https://github.com/CUBRID/cubrid/blob/4db11c5f12f9c67134aad7f547df8704d1e5c591/src/storage/oos_file.cpp#L1060-L1109), [reclaim](https://github.com/CUBRID/cubrid/blob/4db11c5f12f9c67134aad7f547df8704d1e5c591/src/storage/oos_file.cpp#L1561-L1663).

The patch changes neither chunk bytes nor `RVOOS_INSERT`/`RVOOS_DELETE`, publication guards, system-operation boundaries or undo/redo dispatch. A batch can have earlier chunk writes before a later failure; publication reset does not undo them, so the caller still must abort. Replica inserts use the same local selection path and publish replica-local OIDs and stamps. Existing OOS-plus-row grouping is unchanged. Shipping, commit acknowledgment, fencing and promotion have no changed implementation. No live replication, injected interruption, partial-batch abort/restart, or failover check was run.

## Coverage and independent challenge

| Changed path or boundary | Primary reviewer | Evidence and disposition |
| --- | --- | --- |
| `src/storage/oos_file.cpp`, every removed production line | Concurrency/Astra | Wait state, conditional latch, error exits, reverse edges and shutdown traced. Native focused checks and CS stress passed. |
| `unit_tests/oos/scripts/test_oos_concurrent_insert.py`, whole file | Systems/Terra | Process, error, payload, count and timeout oracles inspected; actual script run plus isolated negative controls. |
| File ownership, allocation/reclaim, mutex and metadata wait | Storage/Terra | Independent challenge of Concurrency's question; conditional candidate and released hash mutex established. Controlled stale-hint/metadata contention not run. |
| WAL, system operations, partial failure and retry | Recovery/Astra | Existing record formats and cleanup consumers traced. No new format or durable state; injected wait-failure and crash undo unrun. |
| Producer, applier and replica-local references | HA/Astra | Actual shared insertion and fixup consumers traced. No HA-specific introduced candidate; live apply unrun. |

Concurrency and Storage independently received the same question: does a busy candidate remain skippable while ownership metadata uses the original policy, without a reachable new cycle? Both established conditional candidate latching and that the hash mutex is released before metadata waits. Concurrency traced and rejected ordinary reclaim/allocation reverse edges. Storage retained broader stale-hint/reallocation schedules as unexecuted. The coordinator independently inspected the candidate, caller and file-header paths. No feasible introduced cycle was established; an exhaustive lock-order or controlled-interleaving result is not claimed. This limitation remains in the handoff.

## Fresh native verification

Both engine and tests were built from the pinned head with `debug_gcc`, C++17 and `UNIT_TEST_OOS=ON`. The installation, registry, configuration and allocated master port were isolated. Source diff remained empty. Compiler/configuration and executable hashes are retained in `evidence/build-identity.json`.

The focused command was:

```sh
ctest --test-dir /home/vimkim/gh/cb/review-pr8330-20261104/build_preset_debug_gcc \
  -R '^(test_oos_bestspace|test_oos_growth_sweep)$' --output-on-failure --verbose
```

All four entries passed with exit 0, including setup and cleanup. Bestspace and growth/reclaim tests use standalone mode and do not establish contended server latches.

The unchanged submitted driver ran against the isolated CS database with:

```sh
python3 unit_tests/oos/scripts/test_oos_concurrent_insert.py oosrev8330 \
  /mnt/nvme/data-5/tmp/cubrid-pr-audit-20261104T0957Z/pr8330/evidence/concurrent-8x1500x3 \
  --sessions 8 --rows 1500 --rounds 3 --timeout 180
```

The driver and the coordinator's stronger native checks passed with exit 0.

| Round | Stored rows | Correct ID/payload matches | OOS records |
| --- | ---: | ---: | ---: |
| 1 | 12,000 | 12,000 | 12,000 |
| 2 | 12,000 | 12,000 | 12,000 |
| 3 | 12,000 | 12,000 | 12,000 |

There were 24 separate INSERT clients. The owned server PID remained `2577500` before and after the workload. No new `core*` files appeared in the task source directory, registry directory or selected temporary directory. This was not a system-wide coredump-service audit. The owned server and service stopped successfully and no matching server PID remained. Generated tables, database and logs are retained. A stress pass does not prove absence of a race or guarantee that the metadata-conflict schedule occurred.

## Verified test gap, dispositions and follow-up

`T1` is the test-coverage gap already raised in [the reviewer's request](https://github.com/CUBRID/cubrid/pull/8330#discussion_r4454199907). The script checks `chunks > 0`, while the requested fixed FORCE_OUTLINE fixture requires `Oos_num_recs >= sessions * rows`. Executing the actual script verdict logic with controlled csql responses, two correct rows and one OOS record returns success. Zero chunks, wrong payloads, missing fields, SQL errors despite exit zero and timeouts fail. The coordinator independently replayed the six-case Python probe. This is level-4 evidence about the test driver, not proof that the engine produces the insufficient-OOS state.

The real native run above satisfied the stronger 12,000-record criterion in every round, but did not change the submitted oracle. The script also remains unregistered in CTest and does not itself check PID stability or new cores. Its default is one round. The PR body accurately describes it as a manual tool. Add the isolated CS fixture, three-round invocation and stronger oracles under the existing review request; verify that reverting the wait-policy removal makes the regression fail. That negative-control engine build was not run in this review. Treat this as a concrete automation follow-up rather than a newly confirmed engine defect.

Confirmed introduced engine findings are **zero**. Systems rejected three source error/cleanup hypotheses; Concurrency rejected six engine hypotheses plus a general false-success hypothesis in its bounded script controls; Storage rejected two simple wait/mutex hypotheses; Recovery rejected four wait/format hypotheses; HA rejected four replica/wait-state hypotheses. These source disproofs are not native interleaving proofs. The independent Python probes exposed `T1`, which is deduplicated here.

`Q1` is controlled contention after the preliminary sticky-header lookup, including user zero-wait, finite/default policies and interruption. The pause must occur after that lookup to exercise the newly changed ownership read. `Q2` is an ownership wait failure after earlier chunk writes, followed by abort, row/OOS-count comparison and a successful next transaction. `Q3` is release, mixed DELETE/vacuum and live replica insertion/apply under contention. They were not run. The handoff identifies the narrow next checks without claiming a suspected engine failure.

`B1` is the inherited rollback/vacuum risk, separate from this PR. In the common base, vacuum reclaims an UPDATE's undo-image OOS references without the accepted commit-conditional ownership protocol. After rollback restores the old row, those references can be live. The normative specification requires a committed dropped-chain notification and forbids undo images as deletion sources. `vacuum.c` and `recovery.c/h` are byte-identical between this head and the base. The current source argument is evidence level 3. This review did not reproduce that scenario at the current head. The [earlier survey](https://github.com/vimkim/my-cubrid-docs/blob/0c5c05f713ca1953725743b865c7d3c14bd1272f/cbrd-27881/CBRD-27881-oos-refactoring-candidates_dcbf09e_claude.md) records a 2026-11-03 reproduction at the exact common base. Treat that as dated baseline evidence, not a fresh current-head failure. Track it through [CBRD-27237](https://jira.cubrid.org/browse/CBRD-27237) and [CBRD-27230](https://jira.cubrid.org/browse/CBRD-27230) before OOS integration.

## Budget and artifacts

Five specialists shared these two PRs, using `gpt-6.1-terra` for Systems and Storage and `gpt-6-astra` for Concurrency, Recovery, and HA, all at xhigh. The user explicitly authorized best effort. The shared planning envelope was 20 minutes per specialist plus 30 coordinator minutes, 130 agent-minutes in total. It is one envelope across both reports, not 130 per PR. These are estimates, not spending caps. Actual tokens, subscription quota consumption, allowance windows and percentage compliance are unknown. No extra panel or reviewer retry was launched. The coordinator independently replayed candidate utility behavior, checked source attribution and ran the native checks recorded above. Specialist reports initially marked native verification partial because the coordinator owned those resources; this report includes the subsequent coordinator evidence.

The retained local run is `/mnt/nvme/data-5/tmp/cubrid-pr-audit-20261104T0957Z/pr8330/`. It contains `report.md`, `coverage.md`, `manifest.json`, `handoff.md`, the complete patch, five specialist reports, the native CS result and raw logs. The published document keeps the substantive analysis and reproducing commands; raw logs and generated inventories remain local. No CI trigger, code fix, merge or approval review was performed.
