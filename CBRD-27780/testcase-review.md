# Review of testcase PR 4737

The goal is to determine whether the new shell testcase detects CBRD-27780 plaintext exposure and recovery regressions. A scan can report an unreadable data-volume extension as clean even when it contains the target marker. The recovery scenarios also leave two material prerequisites unproved.

**Verdict: changes-required. Follow-up review required: yes.** The scanner finding is demonstrated with the pinned testcase functions and real files. The recovery and reuse risks below need an isolated database investigation before the test can be relied on for those paths. This verdict does not assess the engine PR's correctness.

## Snapshot

[Testcase PR 4737](https://github.com/CUBRID/cubrid-testcases-private-ex/pull/4737), base `fe3a5efb915610b0fa3c13a1de1cbd2f6eb09c95`, head `0f42c42b96fe2ebc9f496f03c3ca5c34f812dc50`, merge base `fe3a5efb915610b0fa3c13a1de1cbd2f6eb09c95`. The comparison adds one 356-line script. Patch SHA-256 `5ca62aa08d2130932fbdf21538547250305ff52ebd7e5fad3387bd170c3a6792`. Engine context is PR 8402 head `35eeb2b05cf9732638207f5011c1eb9d53cd8faa`. Remote base and head were unchanged on recheck at 2026-11-11 10:47 UTC.

## Confirmed finding

### F1 [P3] An unreadable data volume is counted as zero plaintext matches

[`count_plain`](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/0f42c42b96fe2ebc9f496f03c3ca5c34f812dc50/shell/_06_issues/_26_2h/cbrd_27780/cases/cbrd_27780.sh#L116-L119) suppresses `cat` errors and returns the status and count from `wc`. [`check_no_plain`](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/0f42c42b96fe2ebc9f496f03c3ca5c34f812dc50/shell/_06_issues/_26_2h/cbrd_27780/cases/cbrd_27780.sh#L122-L137) interprets the resulting zero as an OK. The positive control checks that its own marker can be found; it cannot establish that every other volume was read. A read error on a volume can therefore hide plaintext and produce an OK for that scan. This requires an I/O or access failure; the review did not establish that the testcase itself causes one during normal execution.

Coordinator replay ran the exact two functions extracted with `git show` from the reviewed head. The fixture made the main volume readable with `S0PLAIN`, and an extension unreadable with `chmod 000` while it contained `S1HEAP`. As the unprivileged file owner, the probe produced:

```text
control hits: 1
OK scan encrypted marker
actual extension content: S1HEAP
```

The last line was read after restoring the file's permissions. Expected: a failed or inconclusive scan, never an OK. The retained [scanner replay](evidence/scanner-replay.sh) extracts these functions from the pinned Git object. Run `bash evidence/scanner-replay.sh /path/to/cubrid-testcases-private-ex` from this ticket directory as an unprivileged user. The probe substitutes only `write_ok` and `write_nok`, does not run the complete testcase, and is retained with its output. Propagate volume-read failures and require all expected data volumes to be scanned before declaring zero matches.

## Unverified risks requiring follow-up

**R1. Recovery can start without replaying a target page.** The script commits and queries rows before killing the server; its [recovery check](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/0f42c42b96fe2ebc9f496f03c3ca5c34f812dc50/shell/_06_issues/_26_2h/cbrd_27780/cases/cbrd_27780.sh#L140-L155) counts a global REDO-phase message. It does not establish that an affected page retains its old disk image at the kill or that its redo record runs. A feasible schedule flushes the updated page first; [the pinned engine skips redo when the page LSA is already current](https://github.com/CUBRID/cubrid/blob/35eeb2b05cf9732638207f5011c1eb9d53cd8faa/src/transaction/log_recovery.c#L521-L538). Both independent reviewers reached this conclusion. One executed the pinned redo predicate with fixture page LSAs: `(100,8)` versus record `(100,8)` skipped redo; `(99,8)` required redo. That narrow probe does not prove a complete pre-fix test can pass. Before merge, use a contained, instrumented baseline/fixed run to identify target VPIDs, establish the pre-crash disk image, and observe target redo; also test a deliberate flush-before-kill schedule.

**R2. The scenario 4 page-range check does not establish encrypted-page reuse.** The [predicate](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/0f42c42b96fe2ebc9f496f03c3ca5c34f812dc50/shell/_06_issues/_26_2h/cbrd_27780/cases/cbrd_27780.sh#L306-L323) compares only page numbers, assumes the interval describes the old file's pages, and treats equality with the old file ID as success. The pinned engine uses the file ID for the [file header page](https://github.com/CUBRID/cubrid/blob/35eeb2b05cf9732638207f5011c1eb9d53cd8faa/src/storage/file_manager.c#L3468-L3482), and identifies file header/table pages as [never encrypted](https://github.com/CUBRID/cubrid/blob/35eeb2b05cf9732638207f5011c1eb9d53cd8faa/src/storage/page_buffer.c#L15909-L15914). Independent replay of the exact shell predicate with old header 128, old last page 190, and new header 128 returned OK. This proves the predicate accepts that input; it does not establish an actual allocation with no overlapping encrypted data pages. Before merge, observe full volume/page IDs for an old encrypted data page and the reused new page, then verify their on-disk state at the crash.

**R3. Native execution and configuration.** No complete test ran. The local native-shell preflight failed because the develop source HEAD `e64a04a79a5842827a124b3f8313516d0da2594c` differs from installed engine commit `30043f4`. Neither is the related pinned engine head. The author reports before/after failures and passes in the PR/commit; raw artifacts were not independently verified. Obtain isolated builds of the correct baseline and PR head, and run the exact testcase using the native shell workflow with separate install, database, ports, and testkit assets. The available CTP checkout is stale and lacks `wait_until`; its locally cached `origin/develop` at `7dc9f4192bb96988d1bab78df3e45df88628b814` contains the helper. The actual CI CTP revision remains unverified.

## Coverage and checks

The complete changed file was assigned to two reviewers. Oracle coverage included controls, scanning, deallocation, and verdict propagation; recovery coverage included process ownership, page reuse, crash and key-file cleanup. Both independently challenged target-page redo. Their results and exclusions are in `testcase-coverage.md`; no standalone HA or performance review was needed for the shell-only change.

- `bash -n` on `git show` of the pinned script and `git diff --check` both passed.
- Coordinator independently reran the exact page-range predicate on synthetic inputs and the pinned scanner functions on real file fixtures. Neither is a full database execution.
- Native testkit revision `f01005295d3f664a7b0795c604cfc5f145f35aa7`: `go test ./internal/runner/shellsuite -run '^(TestVerdict|TestACaseThatExitsNonZeroKeepsItsVerdict)$' -count=1` passed. Explicit NOK results are preserved; the proposed missing-NOK-propagation concern is dropped.
- The overflow capacity source includes overflow pages in `Num_pages`; the concern that the check measures only heap pages is dropped. Exact deallocated pages remain unobserved.
- Scanner reviewer's all-files-missing probe was superseded by F1's independent readable-control/unreadable-extension replay. No broader ordinary-run failure is claimed. The missing-`wait_until` claim is not a testcase defect without establishing the actual CTP revision.
- Native-shell preflight failed as described in R3. No CUBRID service, database, or CI run was started. Existing checkout dirt and services were preserved.

## Budget and disposition

Bounded allocation was two 12-minute specialist targets plus 15 coordinator agent-minutes, total target 39 agent-minutes. Seats were `gpt-6.1-sol` xhigh and `gpt-6.1-terra` xhigh; each returned before its 8-minute checkpoint deadline. The coordinator's elapsed work was about six minutes through final ref recheck. These are wall-clock observations, not measured model usage. No hard spending cap was enforced; no per-agent usage is available, and the shared account indicator cannot attribute usage. Follow-up execution needs a new allocation; `testcase-handoff.md` gives the focused work.


Review date is 2026-11-11 in Asia/Seoul. The parent coordinator independently replayed the retained probes. Raw logs, the manifest, specialist notes, and build artifacts remain in the local run directory `/home/vimkim/temp/pr-reviews-20261111-8454-4737-8402/4737`. The evidence and limitations needed to assess this report are stated above.

The parent rechecked the PR base and head through the GitHub connector at 2026-11-11 10:54 UTC. Both still matched this snapshot.
