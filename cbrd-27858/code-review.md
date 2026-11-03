# PR 8348 code review

This review checks whether PR 8348 prevents vacuum undo from overwriting a reused forward slot without introducing lifetime, latch-order, recovery, storage, or HA defects. It is for the PR author and engine reviewers. No defect introduced by the patch was confirmed in the inspected scope.

Review date is 2026-11-03, Asia/Seoul. The verdict is `no-confirmed-findings` for the pinned comparison. Static assignments are complete. Runtime coverage has the limits described below. This verdict does not certify the PR as safe to merge.

## Scope and identity

| Item | Value |
| --- | --- |
| PR | [CUBRID/cubrid#8348](https://github.com/CUBRID/cubrid/pull/8348) |
| Requirement | [CBRD-27858](https://jira.cubrid.org/browse/CBRD-27858) |
| Base branch | `feature/oos-merge` |
| Remote base SHA | `dcbf09e4f7fd02ff9c8fc6493ec8887fc2919d67` |
| Merge-base SHA | `dcbf09e4f7fd02ff9c8fc6493ec8887fc2919d67` |
| Head SHA | `628857607265880ef7bbdda4973b1b6f06e8b797` |
| Complete binary-capable patch SHA-256 | `5242f97e1ac86cfba9a5e8f176888768dc8e755372d1f34a2624f88fa0ac9705` |
| Inventory | One modified text file, six added lines, two removed lines. No rename, deletion, submodule, or binary change. |
| Submitted source | Clean pinned worktree. No source edits or instrumentation by this review. |

The literal comparison command was:

```sh
git diff --binary --full-index dcbf09e4f7fd02ff9c8fc6493ec8887fc2919d67 628857607265880ef7bbdda4973b1b6f06e8b797
```

The review consulted the live issue, the PR description, applicable repository guidance, and existing ticket documents. Historical crash and failure-injection claims are context. This review did not repeat those experiments.

## Findings and follow-up

There are no confirmed P0, P1, P2, or P3 findings attributable to this patch.

Follow-up review required is **yes** for the pre-existing OOS chunk risk below. It is separate from the forward-slot change.

| ID | Follow-up | Owner and completion condition |
| --- | --- | --- |
| B1 | OOS chunk pages are released while the enclosing sysop can still undo their slot deletions. | [CBRD-27781](https://jira.cubrid.org/browse/CBRD-27781) owner. Preserve chunk-slot ownership through its undo obligation, then repeat ordinary-abort and restart checks. The bounded model reproduces this pre-existing failure at both base and head. |
| Q1 | New runtime failure-injection and kill/restart checks were not run. | Vacuum maintainer. Replay the issue's controlled abort and crash schedules with concurrent INSERTs at this exact head. Static and model evidence supports the forward fix. |
| Q2 | Extended forward-page hold time is unmeasured. | Storage maintainer if contention is material. Measure a representative relocated OOS workload. No performance regression is claimed from inspection. |

## Source argument

The data shape is `VACUUM_HEAP_HELPER`, whose home and forward page pointers represent separate buffer references. A relocation vacuum starts one sysop, removes the home and forward slots, logs both changes, and optionally deletes OOS values. Undo must be able to reinsert the old forward record at its original slot. A concurrent writer must therefore stay outside that slot until the sysop commits or completes abort undo. [Relocation execution](https://github.com/CUBRID/cubrid/blob/628857607265880ef7bbdda4973b1b6f06e8b797/src/query/vacuum.c#L2494-L2580), [undo callback](https://github.com/CUBRID/cubrid/blob/628857607265880ef7bbdda4973b1b6f06e8b797/src/query/vacuum.c#L7771-L7780).

The patch changes `pgbuf_set_dirty(..., FREE)` to `DONT_FREE`. Successful execution releases forward only after `log_sysop_commit`. On an OOS failure, it retains forward throughout `log_sysop_abort`, returns the error, and lets `vacuum_heap_page` release the original reference. Undo's own fix by the same thread is recursive and balanced. This is a source argument for both normal and error-path ownership. [Changed boundary](https://github.com/CUBRID/cubrid/blob/628857607265880ef7bbdda4973b1b6f06e8b797/src/query/vacuum.c#L2551-L2578), [caller cleanup](https://github.com/CUBRID/cubrid/blob/628857607265880ef7bbdda4973b1b6f06e8b797/src/query/vacuum.c#L1807-L1840).

Static concurrency tracing found no reachable new cycle in the inspected paths. Heap-pair acquisition uses the existing ordered conditional retry. OOS deletion holds one chunk page at a time and does not request a heap page. The inspected INSERT path releases its scoped OOS-page reference before heap placement. OOS empty-page reclaim runs after the heap pages are released. These source arguments exclude the proposed heap-to-OOS-to-heap cycle for those paths. They do not prove whole-engine deadlock freedom. [Ordered preparation](https://github.com/CUBRID/cubrid/blob/628857607265880ef7bbdda4973b1b6f06e8b797/src/query/vacuum.c#L2037-L2126), [OOS insertion ownership](https://github.com/CUBRID/cubrid/blob/628857607265880ef7bbdda4973b1b6f06e8b797/src/storage/oos_file.cpp#L2152-L2316), [deferred reclaim](https://github.com/CUBRID/cubrid/blob/628857607265880ef7bbdda4973b1b6f06e8b797/src/query/vacuum.c#L1970-L1987).

`log_sysop_commit` appends the sysop end before returning, but it does not itself force an immediate flush. Global log ordering places that end before any INSERT log produced after the forward page is released. If the durable prefix excludes the end, it also excludes that later INSERT. WAL prevents the later page image from becoming durable without its log. If a later INSERT is durable, the preceding sysop end is durable too, and restart undo skips the committed sysop. This is the source argument for the interval after page release. [Sysop commit](https://github.com/CUBRID/cubrid/blob/628857607265880ef7bbdda4973b1b6f06e8b797/src/transaction/log_manager.c#L3981-L4012), [log-order publication](https://github.com/CUBRID/cubrid/blob/628857607265880ef7bbdda4973b1b6f06e8b797/src/transaction/log_append.cpp#L1386-L1534), [WAL page-flush check](https://github.com/CUBRID/cubrid/blob/628857607265880ef7bbdda4973b1b6f06e8b797/src/storage/page_buffer.c#L10910-L10935), [restart undo](https://github.com/CUBRID/cubrid/blob/628857607265880ef7bbdda4973b1b6f06e8b797/src/transaction/log_recovery.c#L4945-L5010).

The HA applier buffers logical replication records and treats sysop end or transaction commit as an apply boundary. Physical vacuum WAL uses local recovery callbacks. The patch changes no log type, payload, recovery index, or applier parser. These are source conclusions. HA failover and mixed-version operation were not exercised. [Applier dispatch](https://github.com/CUBRID/cubrid/blob/628857607265880ef7bbdda4973b1b6f06e8b797/src/transaction/log_applier.c#L7299-L7455), [recovery dispatch](https://github.com/CUBRID/cubrid/blob/628857607265880ef7bbdda4973b1b6f06e8b797/src/transaction/recovery.c#L753-L756).

## Coverage and verification

| Changed path or boundary | Primary reviewer | Checked invariant | Result |
| --- | --- | --- | --- |
| `src/query/vacuum.c`, all changed hunks | Recovery, `gpt-6-astra` | Forward slot unavailable through sysop end, abort and restart undo | Static complete. No confirmed finding. |
| Page lifetime and cleanup | Systems, `gpt-6.1-terra` | Success, OOS failure, caller cleanup, recursive refix, no-OOS and alias cases | Static complete. No confirmed finding. |
| Extended latch hold | Concurrency, `gpt-6-astra` | Heap pair ordering, OOS and header acquisition, competing INSERT and vacuum | Static complete. No confirmed finding. |
| Page and space publication | Storage, `gpt-6.1-terra` | Dirty state, bestspace discovery, physical slot reuse, reference balance | Static complete. No confirmed finding. |
| HA and log compatibility | HA, `gpt-6.1-terra` | Producer, applier, restart, format and ordering boundaries | Static complete. HA runtime not run. |

The HA specialist labelled overall coverage partial because cluster, crash, and mixed-version experiments were excluded. The coordinator accepts the assigned static coverage as complete and retains those runtime limits. Roles, fencing, transport, and commit acknowledgments have no changed implementation in this patch.

| Check | Configuration and observed result |
| --- | --- |
| Debug build and installation | Linux x86_64, GCC, `debug_gcc`, `CMAKE_BUILD_TYPE=Debug`, `UNIT_TEST_OOS=ON`. Built from the clean pinned head. Build and installation passed with exit 0. |
| Configured CTest | All 44 tests passed. CTest exited 0. The two PR suites ran serially with distinct installation and registry paths. |
| Diff whitespace | `git diff --check` on the full pinned comparison passed. |
| Base slot-undo model | Home passed. Forward reproduced CBRD-27858. Chunk reproduced CBRD-27781. Exit 0 permits known findings. |
| Head slot-undo model | Home and forward passed. Chunk still reproduced CBRD-27781. Exit 3 requests review of covered-function drift. |
| Statechart rechecks at head | Home and forward returned 0. Chunk returned 1 with the known invariant failure. |

CTest executed the configured suite through the local build coordinator. Its underlying command was `ctest --test-dir build_preset_debug_gcc --output-on-failure --verbose`.

The formal commands used the following pinned revisions:

```sh
python3 /home/vimkim/.agents/skills/cubrid-verify-vacuum-slot-undo/scripts/check.py --repo /home/vimkim/gh/cb/pr7990-hornet-r5 --rev dcbf09e4f7fd02ff9c8fc6493ec8887fc2919d67 --out /home/vimkim/temp/cubrid-review-8350-8348-20261103/8348/evidence/base-slot-model
python3 /home/vimkim/.agents/skills/cubrid-verify-vacuum-slot-undo/scripts/check.py --repo /home/vimkim/gh/cb/pr7990-hornet-r5 --rev 628857607265880ef7bbdda4973b1b6f06e8b797 --out /home/vimkim/temp/cubrid-review-8350-8348-20261103/8348/evidence/slot-model
```

The recovery specialist accepted model correspondence after examining the complete pinned diff, generated constants, slot and undo functions, and caller cleanup. The only changed covered function is `vacuum_heap_record`. The extracted shape changes forward release from before OOS deletion to after sysop end, and error release from before abort to after abort. Home and chunk release shapes do not change. The model groups sysop commit and release into one action. The omitted interval still holds the latch, and the separate durable-prefix argument above addresses the model's assumption that records are immediately durable.

The model covers one vacuum worker, two inserters, two OOS chunks, both home OID-reuse settings, relocation with and without OOS, ordinary abort, and one crash. It does not cover multiple vacuum workers, buffer behavior, HA, repeated crashes, or the full WAL implementation. Its passing forward property and `NoDeadlock` result are not whole-engine proofs.

The shortest known chunk counterexample is a deleted first chunk, failure before the next chunk, reuse of the first chunk's slot by INSERT, and abort undo into that slot. Those release and undo functions are unchanged by this PR. This review classifies it as B1 rather than a new forward-slot finding. [Chunk release](https://github.com/CUBRID/cubrid/blob/628857607265880ef7bbdda4973b1b6f06e8b797/src/storage/oos_file.cpp#L3305-L3317).

## Candidate dispositions and limits

| Candidate | Disposition and evidence |
| --- | --- |
| OOS failure leaks the retained forward page. | Rejected. Abort runs while it is held, then the caller's existing non-null cleanup releases it. |
| Undo deadlocks refixing its own forward page. | Rejected. The buffer manager's existing write holder can fix it recursively and undo balances the extra reference. |
| Publishing the page in bestspace exposes the slot early. | Rejected. Discovery does not grant the write latch. A writer cannot mutate the slot while vacuum holds that latch. |
| No-OOS relocation leaks the page. | Rejected. It skips OOS deletion, commits the same sysop, then reaches the new unfix. |
| Retaining forward protects all OOS chunk slots. | Rejected as a claim. Chunk pages have independent references and are still released inside `oos_delete_chain`. B1 remains separate. |

No release, sanitizer, new failure-injection, kill/restart, native SQL regression-suite, or HA failover run was performed. Missing runtime coverage is not a confirmed code defect. No material standards violation was found in the inspected hunks. This PR adds no automated regression test for the reported overwrite schedule.

## Budget and artifacts

The user explicitly authorized best effort. Five reviewers were assigned to this PR, each with a 15-minute target and an 8-minute checkpoint. Concurrency and recovery used `gpt-6-astra`; the other roles used `gpt-6.1-terra`. All used `xhigh`. The two-PR envelope was ten reviewers plus a 45-minute coordinator target, totaling 195 agent-minutes as a planning target. There is no enforced spending cap. Daily and weekly allowances, token usage, cached-input costs, coordinator usage, and remaining quota were not measurable. Percentage compliance is unverified. No reviewer retries or nested agents were used.

Local evidence is retained under `/home/vimkim/temp/cubrid-review-8350-8348-20261103/8348/`. It includes the manifest, complete patch, inventory, specialist reports, exact command logs, generated model, coverage, and handoff. The shared document retains the source arguments and results. Scratch logs and generated inventories are excluded from Git.

Final GitHub metadata recheck at `2026-11-03T09:17:24.013949+00:00` found the same base and head SHAs. No delta review was required. The result remains tied to the full SHAs above.
