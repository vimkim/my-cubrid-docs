# CBRD-24029 / PR #8096: source-only database-engine review

**No confirmed defects introduced or worsened by the reviewed diff were found.** Four independent specialist reviews covered concurrency and progress, ACID and storage correctness, recovery and replication, and performance. Their results were cross-checked against the baseline and surrounding executable code. This result does not establish exhaustive correctness or constitute a formal GitHub approval.

## Review identity and evidence policy

| Item | Value |
| --- | --- |
| Pull request | [CUBRID/cubrid #8096](https://github.com/CUBRID/cubrid/pull/8096) |
| Ticket identifier | CBRD-24029; issue contents were not used as evidence |
| Review date | 2026-10-08, Asia/Seoul |
| Reviewer | Codex, with four independent specialist reviewers |
| Pinned head | `ffc50b471f9026ebdcd3802f5f6e87d260998cb7` |
| Target branch snapshot | `develop` at `ea57708a785e34b35a91e10cd0694839a53a4fe5` |
| Merge-base | `ea57708a785e34b35a91e10cd0694839a53a4fe5` |
| Diff scope | `src/storage/page_buffer.c`, 382 insertions and 35 deletions, including comments |

The diff defines the change scope. Surrounding executable implementations and their baseline versions establish behavior and invariants. Issue contents, PR descriptions, review comments, commit messages, and source comments were not used to establish intent or correctness. Tests, when present, are behavioral evidence rather than proof of complete correctness.

The exact comparison was:

```sh
git merge-base ea57708a785e34b35a91e10cd0694839a53a4fe5 ffc50b471f9026ebdcd3802f5f6e87d260998cb7
git diff --no-ext-diff ea57708a785e34b35a91e10cd0694839a53a4fe5 ffc50b471f9026ebdcd3802f5f6e87d260998cb7 -- src/storage/page_buffer.c
```

Source links below identify the reviewed head unless explicitly marked as the baseline.

## Confirmed findings

**None.** No candidate was promoted to a defect without a concrete introduced or worsened failure sequence and a baseline comparison. The following risks remain unmeasured.

## Unresolved risks

### 1. Successful assignments bound neither scanning nor LRU mutex duration

The maintenance budget limits successful assignments to five. With persistent waiters and clean but fixed or busy zone-three candidates, `count_vict_cand > 0` still permits acquiring each eligible LRU mutex. A panic-assignment pass can inspect 1,000 BCBs; an unsuccessful hint pass can trigger another pass of up to 1,000 BCBs from the bottom. Both passes run while holding the list mutex. With no assignments, the five-assignment budget remains unchanged.

For stable quota classifications, one maintenance execution can visit `2P + S` lists and perform up to `2,000(P + S)` BCB eligibility checks, where `P` and `S` are the private and shared list counts. Resetting the hint to the bottom usually reduces subsequent unsuccessful executions to one pass per list. The daemon has a 100 ms period; execution may overrun that period.

Evidence: [round-robin traversal](https://github.com/CUBRID/cubrid/blob/ffc50b471f9026ebdcd3802f5f6e87d260998cb7/src/storage/page_buffer.c#L9851-L9866), [1,000-BCB bound and assignment limit](https://github.com/CUBRID/cubrid/blob/ffc50b471f9026ebdcd3802f5f6e87d260998cb7/src/storage/page_buffer.c#L9617-L9677), [LRU mutex and fallback](https://github.com/CUBRID/cubrid/blob/ffc50b471f9026ebdcd3802f5f6e87d260998cb7/src/storage/page_buffer.c#L9915-L9968), [daemon period](https://github.com/CUBRID/cubrid/blob/ffc50b471f9026ebdcd3802f5f6e87d260998cb7/src/storage/page_buffer.c#L17468-L17475).

The additional scan work is source-proven; consequential CPU consumption, throughput loss, or page-fix tail latency is not measured. Needed evidence is a pressure benchmark with persistent pinned or busy candidates, recording scan counts, LRU mutex hold/wait distributions, CPU consumption, and p95/p99 page-fix latency.

### 2. The flush-wakeup predicate can request work that produces no victims

The predicate compares zone-three size with the candidate count. Noncandidates include dirty pages, pages being flushed, and outstanding direct-victim assignments. Consequently, that difference does not prove that dirty work exists. The predicate also accepts shared lists without consulting their computed flush priority, which can be zero.

Persistent waiters can therefore cause redundant wakeups and collection attempts. Some requests are dropped while the flush daemon is running; actual additional executions and their CPU or contention cost were not measured.

Evidence: [wakeup predicate](https://github.com/CUBRID/cubrid/blob/ffc50b471f9026ebdcd3802f5f6e87d260998cb7/src/storage/page_buffer.c#L1107-L1113), [noncandidate flag mask](https://github.com/CUBRID/cubrid/blob/ffc50b471f9026ebdcd3802f5f6e87d260998cb7/src/storage/page_buffer.c#L285-L289), [maintenance wakeup](https://github.com/CUBRID/cubrid/blob/ffc50b471f9026ebdcd3802f5f6e87d260998cb7/src/storage/page_buffer.c#L9792-L9796), [computed flush priorities](https://github.com/CUBRID/cubrid/blob/ffc50b471f9026ebdcd3802f5f6e87d260998cb7/src/storage/page_buffer.c#L14423-L14532), [running-daemon wakeup rejection](https://github.com/CUBRID/cubrid/blob/ffc50b471f9026ebdcd3802f5f6e87d260998cb7/src/thread/thread_waiter.cpp#L77-L101).

Measure extra flush executions, unsuccessful collection rates, and lock contention before treating this as a consequential performance regression.

## Code-grounded verification

### Baseline behavior and scheduling

The baseline maintenance loops execute zero iterations: each initializer sets `index` equal to the index that its loop condition requires it to differ from. The PR activates the maintenance assignment path and visits over-quota private lists, shared lists, and then under-quota private lists. The new five-assignment cap cannot be called a throughput regression against this baseline, because baseline maintenance supplies no victims. [Baseline maintenance implementation](https://github.com/CUBRID/cubrid/blob/ea57708a785e34b35a91e10cd0694839a53a4fe5/src/storage/page_buffer.c#L9559-L9589), [reviewed scheduling](https://github.com/CUBRID/cubrid/blob/ffc50b471f9026ebdcd3802f5f6e87d260998cb7/src/storage/page_buffer.c#L9746-L9763).

### Concurrency, ownership, and storage correctness

LRU traversal holds the list mutex. BCB acquisition uses trylock, followed by another eligibility check under the BCB mutex. Dirty, flushing, already assigned, invalidated, fixed, and waiting-on-latch pages remain ineligible. The quota filters do not bypass these checks. [Eligibility checks](https://github.com/CUBRID/cubrid/blob/ffc50b471f9026ebdcd3802f5f6e87d260998cb7/src/storage/page_buffer.c#L9279-L9324), [assignment scan](https://github.com/CUBRID/cubrid/blob/ffc50b471f9026ebdcd3802f5f6e87d260998cb7/src/storage/page_buffer.c#L9644-L9671).

Assignment verifies suspension and publishes the victim while holding the recipient's thread-entry mutex. The condition-variable wait releases that mutex, and successful resumption unlocks it before the recipient acquires the BCB mutex. No new waiter-entry/BCB lock inversion was established. [Publication](https://github.com/CUBRID/cubrid/blob/ffc50b471f9026ebdcd3802f5f6e87d260998cb7/src/storage/page_buffer.c#L15737-L15758), [wait/resumption](https://github.com/CUBRID/cubrid/blob/ffc50b471f9026ebdcd3802f5f6e87d260998cb7/src/thread/thread_entry.cpp#L564-L602).

A concurrent ordinary fix invalidates an outstanding direct assignment before using the page. The recipient detects that invalidation and retries rather than evicting the refixed page. The lock-free read-fix path requires an already held read latch with positive fix count, which excludes an eligible victim. [Ordinary-fix invalidation](https://github.com/CUBRID/cubrid/blob/ffc50b471f9026ebdcd3802f5f6e87d260998cb7/src/storage/page_buffer.c#L2358-L2361), [recipient revalidation and removal](https://github.com/CUBRID/cubrid/blob/ffc50b471f9026ebdcd3802f5f6e87d260998cb7/src/storage/page_buffer.c#L15883-L15935), [lock-free read eligibility](https://github.com/CUBRID/cubrid/blob/ffc50b471f9026ebdcd3802f5f6e87d260998cb7/src/storage/page_buffer.c#L7749-L7777).

Candidate accounting retains its flag-transition CAS and counter updates. Cancellation and shutdown cleanup retain their existing reserved-victim cleanup. Maintenance is stopped before the flush and post-flush daemons are destroyed. [Candidate accounting](https://github.com/CUBRID/cubrid/blob/ffc50b471f9026ebdcd3802f5f6e87d260998cb7/src/storage/page_buffer.c#L16076-L16142), [interrupt/shutdown cleanup](https://github.com/CUBRID/cubrid/blob/ffc50b471f9026ebdcd3802f5f6e87d260998cb7/src/storage/page_buffer.c#L8350-L8359), [teardown ordering](https://github.com/CUBRID/cubrid/blob/ffc50b471f9026ebdcd3802f5f6e87d260998cb7/src/storage/page_buffer.c#L17564-L17569).

### Recovery and replication

New maintenance cannot directly evict dirty or in-flight-flush pages. Its flush wakeup reaches the unchanged flush machinery, which checks whether WAL is needed and retains WAL flushing before DWB insertion or page writing for logged changes. Write-error handling restores dirty state and the oldest-unflushed LSA. [Victim-flush WAL check](https://github.com/CUBRID/cubrid/blob/ffc50b471f9026ebdcd3802f5f6e87d260998cb7/src/storage/page_buffer.c#L4033-L4047), [WAL-before-write path](https://github.com/CUBRID/cubrid/blob/ffc50b471f9026ebdcd3802f5f6e87d260998cb7/src/storage/page_buffer.c#L11099-L11167), [write-error restoration](https://github.com/CUBRID/cubrid/blob/ffc50b471f9026ebdcd3802f5f6e87d260998cb7/src/storage/page_buffer.c#L11177-L11182).

The reviewed diff changes victim scheduling and wakeups without changing log-record construction, transaction ordering, replay dispatch, checkpoint LSA advancement, replication watermarks, or failover state. No introduced durability, replay, or replication defect was established. Indirect replication throughput effects remain part of the unmeasured pressure-workload risk.

## Build, tests, and coverage limitations

| Check | Observed result |
| --- | --- |
| Exact head and merge-base resolution | Confirmed the revisions above |
| Diff and surrounding executable-code review | Four specialist passes plus parent cross-check completed |
| CMake Debug GCC configuration | Passed; GCC 11.5.0, `debug_gcc` preset |
| Compilation and installation | Passed, including server and standalone `page_buffer.c` compilation |
| `ctest --test-dir build_preset_debug_gcc --output-on-failure --verbose` | Returned zero but reported **No tests were found** |
| Final source status | Clean at the pinned head; configuration-generated CCI version header restored |

The preset-aware local build workflow executed CMake configuration, compilation, installation, and CTest. Build output was inspected for the successful completion result. CTest discovered **zero tests**, so there is no runtime test pass to claim.

No contention benchmark, race detector, forced handoff/refix interleaving, cancellation stress test, crash or I/O-failure injection, recovery restart, or replication workload was run. The unchanged DWB and replication implementations were not exhaustively re-audited. Existing scan-depth limits and heuristic synchronization also limit what this static review can establish.

The review made no engine repair, source commit, push, or PR modification. Publication of this report and its summary comment was separately requested after the review.
