# PR 8402 coverage

Pinned head `35eeb2b05cf9732638207f5011c1eb9d53cd8faa`. Base and merge base `063d84e537cbde1a359f369aabb510b01fe68a00`. Status describes evidence, not a merge recommendation.

| Changed path | Owner | Reviewed invariant and evidence | Result and remaining action |
|---|---|---|---|
| `src/storage/file_manager.c` | Storage, `gpt-6.1-terra`; recovery cross-check, `gpt-6.1-sol` | Permanent allocation, f_init ordering, same-page FTAB reuse and atomic sysop. Pinned source and caller traces. | Partial. R1 and R2 require integrated rollback and restart tests. |
| `src/storage/page_buffer.c` | Concurrency, `gpt-6.1-sol`; storage and recovery cross-check | NEW_PAGE clearing, TDE flags, safe flush, deallocation and undo. Exact-body helper probes with stub boundaries described in report. | Partial. Foreign flusher admission supports the source argument, but integrated race and disk encryption are untested. R1/R2 remain open. |
| `src/storage/page_buffer.h` | Systems, `gpt-6.1-terra`; concurrency | New declarations, callers, latch and fetch contracts. Pinned source. | Partial. Signatures match in source; completed engine compile and runtime behavior not verified. |
| `src/transaction/recovery.c` | Recovery, `gpt-6.1-sol`; systems cross-check | New redo/undo registration, physical undo and callers. Pinned source, helper mutation probe. | Partial. R1 and R2 need full dispatcher, crash, and restart execution. |
| `src/transaction/recovery.h` | Recovery, `gpt-6.1-sol`; systems | Appended recovery index and physical/logical classification. Pinned source. | Partial. Prior indexes retain values in source; HA/CDC and compatibility execution not performed. |

## Shared boundary challenge

Question: Can a foreign flusher persist a page after NEW_PAGE clears it but before initialization and TDE logging? Concurrency (`gpt-6.1-sol`) and recovery (`gpt-6.1-sol`) independently traced the pinned path. Both found the write latch defers foreign safe flush. Concurrency's seven-case production-function helper supports admission decisions with stubbed I/O, waiting, holder lookup, flag operations, ownership and state predicates. The same model was used for both seats, so there was no model-family diversity on this shared challenge. Same-owner explicit flush is allowed; inspected initializers did not call it. Recovery replays records separately and is not covered by the same latch interval. Integrated interleavings remain untested.

HA was combined into recovery because the patch adds a common recovery index without changing a replication wire protocol. Recovery inspected overflow log collectors and the record type in source. It did not run replication, CDC, failover, or an overflow workload. Systems inspected existing PR review comments read-only. A reported third-party crash reproduction has no independently reviewed raw log.

Specialist status is partial for all seats because material engine execution or crash evidence is absent. Candidate disposition: R1 from storage and recovery remains unverified; R2 from systems, storage, and recovery remains unverified. Concurrency reported no additional candidate. Partial-copy and foreign-flush hypotheses were bounded under conditions in the report; no other material candidate was discarded.


Review date is 2026-11-11 in Asia/Seoul. The parent coordinator independently replayed both retained helper probes. Raw logs, the manifest, specialist notes, and build artifacts remain in the local run directory `/home/vimkim/temp/pr-reviews-20261111-8454-4737-8402/8402`. The evidence and limitations needed to assess this report are stated above.
