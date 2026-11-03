# PR 8350 code review

This review checks whether PR 8350 removes the vacuum and heap-allocation latch cycle without introducing ownership, concurrency, storage, recovery, or HA defects. It is for the PR author and engine reviewers. No defect introduced by the patch was confirmed in the inspected scope.

Review date is 2026-11-03, Asia/Seoul. The verdict is `no-confirmed-findings` for the pinned comparison. Static assignments are complete. Runtime coverage has the limits described below. This verdict does not certify the PR as safe to merge.

## Scope and identity

| Item | Value |
| --- | --- |
| PR | [CUBRID/cubrid#8350](https://github.com/CUBRID/cubrid/pull/8350) |
| Requirement | [CBRD-27860](https://jira.cubrid.org/browse/CBRD-27860) |
| Base branch | `feature/oos-merge` |
| Remote base SHA | `dcbf09e4f7fd02ff9c8fc6493ec8887fc2919d67` |
| Merge-base SHA | `dcbf09e4f7fd02ff9c8fc6493ec8887fc2919d67` |
| Head SHA | `1ef6ed6125eb6028c06b0e05282dc0041bde3f48` |
| Complete binary-capable patch SHA-256 | `f0b79039cc8a2819d770a1689f9eaf4d23e7ceb36d81c815edb40e4370178322` |
| Inventory | Five modified text files, 238 added lines, 25 removed lines. No rename, deletion, submodule, or binary change. |
| Submitted source | Clean pinned worktree. No source edits or instrumentation by this review. |

The literal comparison command was:

```sh
git diff --binary --full-index dcbf09e4f7fd02ff9c8fc6493ec8887fc2919d67 1ef6ed6125eb6028c06b0e05282dc0041bde3f48
```

The review consulted the live issue, the PR description, applicable repository guidance, and the existing ticket documents. Historical reproduction claims in those documents are context. They are not new experiments from this review.

## Findings and follow-up

There are no confirmed P0, P1, P2, or P3 findings attributable to this patch.

Follow-up review required is **yes** for the separately tracked baseline risks and the bounded coverage questions below. No additional change to this PR is demanded by a confirmed delta finding.

| ID | Follow-up | Owner and completion condition |
| --- | --- | --- |
| B1 | The forward-slot undo hazard remains in this snapshot. | CBRD-27858 owner. Integrate and verify [PR 8348](../cbrd-27858/code-review.md). The model still finds the old failure in PR 8350 alone. |
| B2 | OOS chunk-slot undo can collide with reuse. This is pre-existing. | [CBRD-27781](https://jira.cubrid.org/browse/CBRD-27781) owner. Protect every reusable chunk slot until its undo obligation ends, then repeat failure and restart checks. This is a data-integrity follow-up for the OOS baseline. |
| Q1 | Relocation-specific header contention was not exercised dynamically. | Vacuum maintainer. Repeat the latch test with a nonheader forward page and a changed home link during the wait. Static tracing found no new defect. |
| Q2 | Inline vacuum can retain a caller-owned home-page watcher. | Partition maintainer. Establish the complete schema-lock chain into partition redistribution before applying the background-worker release claim to this caller. This path predates the patch. |

## Source argument

The relevant data shape is `VACUUM_HEAP_HELPER`. It owns copied record bytes, the home and optional forward page references, cached file identifiers, and pending bulk-vacuum slots. Preparation discovers the current record. The later execution stage decides its MVCC eligibility and mutates pages. Both record branches use `COPY` into helper-owned storage before the new wait path. The caller checks MVCC eligibility after preparation returns. [Pinned helper and preparation](https://github.com/CUBRID/cubrid/blob/1ef6ed6125eb6028c06b0e05282dc0041bde3f48/src/query/vacuum.c#L501-L547), [caller](https://github.com/CUBRID/cubrid/blob/1ef6ed6125eb6028c06b0e05282dc0041bde3f48/src/query/vacuum.c#L1778-L1828).

Static tracing supports the intended cycle removal. An allocator holds the heap header and requests the last heap page. Vacuum tries the header conditionally. If refused, vacuum releases its forward page, logs pending home changes, and releases its home page before the unconditional header lookup. The allocator can then finish. Vacuum refixes home and rereads the slot, record type, relocation link, body, and MVCC header through `retry_prepare`. [Allocator acquisition order](https://github.com/CUBRID/cubrid/blob/1ef6ed6125eb6028c06b0e05282dc0041bde3f48/src/storage/heap_file.c#L28614-L28666), [new release and wait boundary](https://github.com/CUBRID/cubrid/blob/1ef6ed6125eb6028c06b0e05282dc0041bde3f48/src/query/vacuum.c#L2299-L2353), [retry](https://github.com/CUBRID/cubrid/blob/1ef6ed6125eb6028c06b0e05282dc0041bde3f48/src/query/vacuum.c#L2026-L2157).

The release is before the current record's sysop. `vacuum_heap_page_log_and_reset` records pending bulk changes, marks home dirty, and resets the pending count before unfixing. A failed refix returns before current-record mutation. These facts support the WAL boundary by source analysis. They do not establish runtime crash behavior. [Log and reset](https://github.com/CUBRID/cubrid/blob/1ef6ed6125eb6028c06b0e05282dc0041bde3f48/src/query/vacuum.c#L2808-L2870).

The extraction preserves the existing unconditional lookup and creation body. The new wrapper passes a conditional read latch and disables creation. Its sole caller treats failure as inconclusive and performs the authoritative lookup after releasing pages. If the header aliases home or forward, the buffer manager permits a repeated fix by the existing write holder. The matching unfix drops only the added reference. [Lookup implementation](https://github.com/CUBRID/cubrid/blob/1ef6ed6125eb6028c06b0e05282dc0041bde3f48/src/storage/heap_file.c#L13229-L13365), [reentrant latch behavior](https://github.com/CUBRID/cubrid/blob/1ef6ed6125eb6028c06b0e05282dc0041bde3f48/src/storage/page_buffer.c#L6350-L6500).

Conditional mode prevents waiting for a conflicting page latch. It does not make all of `pgbuf_fix` nonblocking. A cold page can still require a loader, victim selection, or I/O. No new cycle or measured performance regression through those paths was established. [Buffer-miss path](https://github.com/CUBRID/cubrid/blob/1ef6ed6125eb6028c06b0e05282dc0041bde3f48/src/storage/page_buffer.c#L7975-L8003).

## Coverage and verification

Each changed path has a primary owner. Recovery also reviewed the logging boundary across the concurrency and storage assignments.

| Changed path | Primary reviewer | Checked invariant | Result |
| --- | --- | --- | --- |
| `src/query/vacuum.c` | Concurrency, `gpt-6-astra` | Release before header wait, refreshed record and link, cached VFID lifetime, aliasing, page reclamation guards | Static complete. No confirmed finding. |
| `src/storage/heap_file.c` | Storage, `gpt-6.1-terra` | Lookup/create contract, conditional latch and reference balance, source-level costs | Static complete. No confirmed finding. |
| `src/storage/heap_file.h` | Systems, `gpt-6.1-terra` | Declaration, callers, server and standalone signatures | Static complete. No confirmed finding. |
| `unit_tests/oos/test_oos_real_vacuum_server.cpp` | Systems, `gpt-6.1-terra` | Oracle, record ownership, watcher cleanup, deadlines | Static complete. Regression execution recorded below. |
| `unit_tests/oos/CMakeLists.txt` | HA, `gpt-6.1-terra` | Target, fixture, timeout, serial scope | Static complete. HA runtime not run. |
| WAL, abort, restart, and page-release boundary | Recovery, `gpt-6-astra` | Prior bulk logging, current sysop boundary, interrupted refix, unchanged undo callbacks | Static complete. Bounded model executed. |
| HA producers and consumers | HA, `gpt-6.1-terra` | Standby reaches ordinary vacuum; unchanged logical replication formats and dispatch | Static complete. No cluster run. |

The HA specialist labelled overall coverage partial because cluster and crash experiments were excluded. The coordinator accepts the assigned static coverage as complete and retains those runtime limits. Roles, fencing, transport, and commit acknowledgments have no changed implementation in this patch.

| Check | Configuration and observed result |
| --- | --- |
| Debug build and installation | Linux x86_64, GCC, `debug_gcc`, `CMAKE_BUILD_TYPE=Debug`, `UNIT_TEST_OOS=ON`. Built from the clean pinned head. Build and installation passed. |
| Configured CTest | All 44 tests passed. The build, installation, and CTest command exited 0. |
| New latch regression | `OosRealVacuum.VacuumWaitsForHeapHeaderWithoutHoldingLastPage` passed. It checks a live `REC_HOME` row, the available last page, real page allocation, and the OOS value after vacuum. |
| Diff whitespace | `git diff --check` on the full pinned comparison passed. |
| Slot-undo model | Home property passed. Forward property reproduced known CBRD-27858. Chunk property reproduced known CBRD-27781. Tool exit was 0 because known findings are allowed by that tool. |
| Independent statechart checks | Home returned 0. Forward and chunk returned 1 with the corresponding known invariant failures. Those exits are expected evidence of baseline defects. |

CTest executed the configured suite through the local build coordinator. Its underlying test command is:

```sh
ctest --test-dir build_preset_debug_gcc --output-on-failure --verbose
```

The formal check was:

```sh
python3 /home/vimkim/.agents/skills/cubrid-verify-vacuum-slot-undo/scripts/check.py --repo /home/vimkim/gh/cb/pr7990-hornet-r2 --rev 1ef6ed6125eb6028c06b0e05282dc0041bde3f48 --out /home/vimkim/temp/cubrid-review-8350-8348-20261103/8350/evidence/slot-model
```

The model uses one vacuum worker, two inserters, two OOS chunks, ordinary abort, and one crash. It covers execution-stage slot ownership. It does not model this PR's preparation wait, buffer management, failed refix, multiple vacuum workers, or HA. The recovery specialist verified unchanged modeled execution and undo functions against the base. Model failures are not fresh runtime reproductions.

## Candidate dispositions and limits

| Candidate | Disposition and evidence |
| --- | --- |
| Saved record dangles after unfix. | Rejected. Both record kinds copy into `helper->rec_buf`; log-and-reset leaves that buffer intact. |
| Retry acts on the old forward OID or MVCC header. | Rejected. `retry_prepare` rereads both, and the caller decides vacuum eligibility afterward. |
| Header aliases a held heap page and deadlocks recursively. | Rejected. The existing write holder can refix for read; its added fix is balanced. |
| Cached VFID points at a newly reused file after the wait. | Rejected for the background-worker path. Dropped-file acknowledgment and unfinished-vacuum guards remain active across the wait. See [dropped-file synchronization](https://github.com/CUBRID/cubrid/blob/1ef6ed6125eb6028c06b0e05282dc0041bde3f48/src/query/vacuum.c#L6634-L6671). |
| Every caller releases every home-page reference. | This broad claim is unsupported. Inline vacuum retains an outer watcher. Q2 preserves the untraced partition-lock question. See [inline caller](https://github.com/CUBRID/cubrid/blob/1ef6ed6125eb6028c06b0e05282dc0041bde3f48/src/storage/heap_file.c#L26543-L26586). |
| New polling calls have a strict 60-second execution bound. | Rejected as a claim. Predicates can block. The whole binary has an 840-second CTest timeout. No newly reachable hang was proved. |

No release, sanitizer, SQL workload, fault-injection, or HA failover run was performed. The configured CTest includes SQL-oriented unit binaries, but this is not a native SQL regression-suite qualification.

One formatting observation remains outside correctness findings. The added polling expression on test line 944 occupies 139 columns when tabs expand to eight columns, exceeding the documented 120-column width. It contains 111 literal characters. No formatter or CI failure is inferred from this observation. Include order and the relevant server and standalone declarations were checked. [Polling expression](https://github.com/CUBRID/cubrid/blob/1ef6ed6125eb6028c06b0e05282dc0041bde3f48/unit_tests/oos/test_oos_real_vacuum_server.cpp#L943-L944).

## Budget and artifacts

The user explicitly authorized best effort. Five reviewers were assigned to this PR, each with a 15-minute target and an 8-minute checkpoint. Concurrency and recovery used `gpt-6-astra`; the other roles used `gpt-6.1-terra`. All used `xhigh`. The two-PR envelope was ten reviewers plus a 45-minute coordinator target, totaling 195 agent-minutes as a planning target. There is no enforced spending cap. Daily and weekly allowances, token usage, cached-input costs, coordinator usage, and remaining quota were not measurable. Percentage compliance is unverified. No reviewer retries or nested agents were used.

Local evidence is retained under `/home/vimkim/temp/cubrid-review-8350-8348-20261103/8350/`. It includes the manifest, complete patch, inventory, five specialist reports, exact command logs, generated model, coverage, and handoff. The shared document retains the source arguments and results. Scratch logs and generated inventories are excluded from Git.

Final GitHub metadata recheck at `2026-11-03T09:16:55.192897+00:00` found the same base and head SHAs. No delta review was required. The result remains tied to the full SHAs above.
