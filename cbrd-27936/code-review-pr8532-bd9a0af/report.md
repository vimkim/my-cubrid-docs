# Code review: CUBRID/cubrid#8532 — release a committing transaction's saved space only after its commit log is appended

- PR: https://github.com/CUBRID/cubrid/pull/8532 (author hornetmj, base `develop`)
- JIRA: [CBRD-27936](http://jira.cubrid.org/browse/CBRD-27936)
- Snapshot: base `505c07dde1c279ccd758cc7ef5e6d40697da59fc`, merge base `505c07dde1c279ccd758cc7ef5e6d40697da59fc`, head `bd9a0afc7bb84aee33a5947c9b9c56ca8eabd9b8`. The PR was rechecked at the same SHAs before publication.
- Comparison: `git diff 505c07dde1c279ccd758cc7ef5e6d40697da59fc bd9a0afc7bb84aee33a5947c9b9c56ca8eabd9b8`. Patch sha256 is `63e3ad27b9e98fb09ca8481f4d0c64c306f35b420ea96533101014c7eaf64f0d`.
- Changed path: `src/transaction/log_manager.c` (`log_commit_local`, +17/−9). The diff has no other paths.
- Source links:
  - [Local-branch release at head](https://github.com/CUBRID/cubrid/blob/bd9a0afc7bb84aee33a5947c9b9c56ca8eabd9b8/src/transaction/log_manager.c#L5413-L5450)
  - [2PC-branch release at head](https://github.com/CUBRID/cubrid/blob/bd9a0afc7bb84aee33a5947c9b9c56ca8eabd9b8/src/transaction/log_manager.c#L5451-L5462)
  - [Old release point at base](https://github.com/CUBRID/cubrid/blob/505c07dde1c279ccd758cc7ef5e6d40697da59fc/src/transaction/log_manager.c#L5409-L5420)
- Line numbers in this report refer to the head commit unless they are marked as base, sync-commit, or model output.
- Review goal: decide whether vimkim, the only pending requested reviewer, should approve the PR.

## Verdict

**`no-confirmed-findings`.** Follow-up review required: **no**.

The change fixes the defect it targets, and the review found no regression. The deciding evidence was a runtime replay of the author's crash reproduction on both builds:

| Build | Result |
|---|---|
| Base | 2 of 2 runs failed. Restart recovery stopped on the `heap_update_physical` assertion. |
| Head | 3 of 3 runs passed. Recovery succeeded with the expected row values. |

The formal model also shows that the known `commit-window-saved-space` path is gone once this patch is applied. Two independent reviewers on different models traced the code by hand, and neither found a schedule in which the moved release can be unsafe. The only material comment is a wording problem in the new 2PC-branch comment (N-1). It does not affect behavior.

**Recommendation for vimkim:** approve. N-1 can be raised as an optional, non-blocking comment fix.

Merge is still blocked on two procedural gates. Neither one depends on this code review:

- **PR approval gate:** lht1199 is APPROVED (at `1acfbbc91`; the only later commit, `bd9a0afc7`, changes a comment). vimkim's review is still pending.
- **TC Merge Gate (`Check TC PRs`):** this check fails because two empty bot draft TC PRs are open: cubrid-testcases#4198 and cubrid-testcases-private-ex#4906, each with 0 changed files. Under the testcase lifecycle, close them during the final merge handoff, right before the engine merge.

## What changed

Before the change, `log_commit_local` called `spage_free_saved_spaces` right after `log_tran_do_postpone`, which is before the commit record is appended. Take a transaction U that logged no postpone, such as an in-place shrinking MVCC UPDATE or a DELETE on a non-`REUSE_OID` heap. In the window between the release and the commit record, the following could happen:

1. Another transaction T takes the bytes that U had saved, and T commits.
2. The server crashes before U's commit record is durable.
3. Restart treats U as a loser, and U's undo cannot fit back into the page.

The result is a debug assertion, or `logpb_fatal_error` in a release build, and the database cannot restart.

The PR changes the release in two places:

- **Local branch:** the release now follows `log_append_commit_log` or `log_append_repl_info_and_commit_log` (`log_manager.c:5427/5431` → `5437-5441`). It still comes before `lock_unlock_all` and the commit flush.
- **2PC branch (`is_local_tran == false`):** the release is now inside that branch (`5456-5460`). The decision record was already appended there, as before.

The abort path and the `tail_lsa == NULL` branch are unchanged.

## Confirmed findings

None.

## Comments that are not defects

| ID | Location | Statement | Suggested action |
|---|---|---|---|
| N-1 | `log_manager.c:5453-5455` (new 2PC comment) | The comment says "The commit decision is already on disk: log_2pc_append_decision flushed it". This is not always true. With `log_async_commit=yes`, `logpb_flush_pages` sets `need_wait = false` and returns without waiting (`log_page_buffer.c:4131-4152`). If prior-node allocation fails, `log_2pc_append_decision` writes no record at all (`log_2pc.c:1934-1938`). The code is still safe for the same reason as the local branch: the decision record has a smaller LSA than any log record that reuses the bytes, and the log becomes durable as a prefix. Coordinator re-read the cited lines (evidence level 2). | Optional rewording: "The commit decision record precedes, in LSA order, any log that reuses the space, so a reuse cannot become durable without the decision." Not blocking. |
| N-2 | PR description, footnote below the diagram | The footnote says "T의 commit이 디스크에 없으면 T도 loser … T가 먼저 되돌려진다". This describes a state that cannot occur. If T's log record that reuses the bytes is durable, U's commit record is durable too (durable prefix), so U is not a loser. If that record is not durable, T's page change is not on disk either (WAL). The actual safety comes from the durable prefix plus WAL, not from reverse-LSA undo order. | Optional PR-text correction. No code change. |

## Safety facts and effects outside the diff

| ID | Fact | Pinned evidence | Level | Owner |
|---|---|---|---|---|
| SF1 | U's commit LSA C is assigned under `prior_lsa_mutex` before the release. T can see the freed bytes only through the per-page save-head mutex or the hash erase. T logs afterwards, so every record that reuses the bytes has LSA > C. | `log_append.cpp:1419-1582`; `log_manager.c:4839-4844`, `5427-5441`; `slotted_page.c:393-468`, `703-751` | 3 (both reviewers, independently) | R1, R2 |
| SF2 | The durable log is a prefix of LSA order. Prior nodes drain in LSA order, and the page that holds the previous end-of-log marker is written last. `nxio_lsa` advances only after fsync, and restart analysis stops at the end-of-log marker or a torn page. | `log_page_buffer.c:3123-3146`, `3436-3520`, `3740-3894`; `log_recovery.c:2502`, `2787-2800` | 3 | R1, R2 |
| SF3 | WAL: a data page is flushed only after the log is flushed through that page's LSA. | `page_buffer.c:11709`, `11734`; `log_page_buffer.c:11964-11977` | 2-3 | R1 |
| SF4 | Restart undoes only `UNILATERALLY_ABORTED` and `ABORTED` transactions. These three states exclude U from undo: a durable `LOG_COMMIT`, a checkpoint snapshot with U in `WILL_COMMIT`, and a durable 2PC commit decision. | `log_recovery.c:4752-4758`, `1590-1598`, `1955-1962`, `4479-4508`; `log_page_buffer.c:7256`, `7504-7522` | 2-3 | R1 |
| SF5 | `spage_free_saved_spaces` takes only a lock-free-hash epoch and a leaf `head->mutex`. It takes no page latch, no `prior_lsa_mutex`, and no `LOG_CS`. The new call site holds no log mutex, so no new lock order arises. | `slotted_page.c:393-468`; `log_manager.c:4844` | 3 | R2 |
| SF6 | The old and new release points free the same list. `spage_save_space` adds entries only for an active transaction, and U has been in `WILL_COMMIT` since line 5396. Every branch frees the list and sets it to NULL before `logtb_clear_tdes`, so no leak or double free arises. | `slotted_page.c:518`, `566`, `633`; `log_impl.h:143`; `log_tran_table.c:932`, `1643`, `1734` | 2-3 | R2 |
| SF7 | The code between the old and new release points does not write heap pages. That code is `log_cleanup_modified_class_list` (in-memory caches only) and the commit-record append (prior nodes only). In any case, a non-active transaction does not subtract saved space, so U never competes with its own reservation. Postpone actions run before both release points and are unaffected. | `log_manager.c:5313-5356`, `8405`; `slotted_page.c:4611-4638` | 3 | R2 |
| SF8 | 2PC behavior is unchanged. Both before and after the change, the release follows the decision record. The only difference is that it now also follows `log_cleanup_modified_class_list`, which writes no pages. `log_2pc_recovery_commit_decision` runs only at restart, when no saved space exists, and is not compiled into default `CCI_XA` builds. | `log_2pc.c:600`, `747-760`, `2576-2593`, `2698-2702`; `build.sh:40`; `CMakeLists.txt:617-619` | 2-3 | R1 |
| SF9 | HA is not affected. Saved space exists only in memory and is never logged. The commit and replication records keep the same content and order, and the release runs after `prior_lsa_mutex` is unlocked. | `log_manager.c:4821-4844` | 3 | R1 |

Callers of `log_commit_local`:

- `log_commit` (`log_manager.c:5647`): local branch, so the fix applies. This path covers ordinary commits, the HA applier, and non-coordinator participants.
- CCI_XA DBLink coordinator (`log_2pc.c:600`): local branch, so the fix applies.
- `log_2pc_commit_second_phase` (`log_2pc.c:760`): 2PC branch, behavior unchanged.
- `log_2pc_recovery_commit_decision` (`log_2pc.c:2585`): 2PC branch with no saved space.

Restart's own commit completion goes through `log_recovery_finish_postpone` and `log_complete`, not `log_commit_local`.

**Performance (source and model only, nothing measured):** the reservation now lasts longer by the time of `log_cleanup_modified_class_list` plus the commit-record append. For ordinary DML that is one prior-node allocation plus the `prior_lsa_mutex` wait. DDL also walks the XASL cache, and an HA master also appends its pending replication items. The commit flush wait stays outside the window. During the extra window, a concurrent writer on the same page relocates its record or uses another page, which matches what the PR states. `ER_SP_NOSPACE_IN_PAGE` cannot be triggered, because only freshly allocated hint pages raise it (`heap_file.c:24040`; `locator_sr.c:16030-16084`). The 2PC branch adds one pointer test outside the local hot path.

## Coverage and verification

See [coverage.md](coverage.md). Two specialist reviewers covered every hunk, caller, and cross-domain risk. Both reviewers answered the shared challenge question independently:

> Q1: Can a durable log that reuses U's released bytes exist without U's commit record, or can restart undo U after reuse?

- **R1** (Recovery+HA, opus): **No.** Supported by SF1 through SF4, and also covers async commit, 2PC, and checkpoints.
- **R2** (Systems+Concurrency+Storage, sonnet): **No.** Supported by SF1 through SF3 and SF5, plus a concrete five-step schedule.

The two answers differ on one point. R2 said the 2PC release follows "a flushed decision". R1 found that this flush does not wait under `log_async_commit`, and the coordinator confirmed R1's reading (N-1). Both reviewers agree that the code is safe through LSA ordering.

### Checks run by the coordinator

**1. Runtime replay, evidence level 5.**

- Script: the author's Jira attachment `commit-crash-saved-space-v2.sh` (sha1 `32ee850a323065633cfab6f3ae39e0b62ac87e53`). It uses a private CUBRID directory, port, and master. Columns use `STORAGE FORCE_INLINE`, so neither row goes to OOS.
- Precondition check: the table has one heap page with less than 4,000 bytes free.
- Scenario: gdb non-stop holds U at entry to `log_append_commit_log`. T grows id=2 from 7,000 to 12,000 bytes and commits. The test sends SIGKILL to `cub_server` and restarts it.
- Pass condition: id=1 has length 8,000 and id=2 has length 12,000.
- Builds: debug_gcc. The head build ran in `/home/vimkim/gh/cb/CBRD-27936`. The base build ran in a detached worktree at `505c07dde1`.

| Build | Runs | Result |
|---|---|---|
| head `bd9a0afc7b` | 3 | **3/3 pass.** "재시작 복구 성공, id=1 8000(U 되돌림), id=2 12000(T 유지)", exit 0. Free space was 200, 216 and 196 bytes, with one page each time. |
| base `505c07dde1` | 2 | **2/2 fail.** `heap_file.c:26503: int heap_update_physical(...): Assertion 'false' failed` during restart recovery, exit 1. |

The script detects the defect at the base, and the patch removes it under the same conditions.

**2. Formal model, `cubrid-verify-heap-slot-undo` (TLC 1.7.4).**

- `check.py --rev` on base and on head: both report `OUT OF SYNC: case REC_RELOCATION has no log_sysop_commit`, exit 2. `develop` now holds the forward page through the sysop (OOS #8348), so the model's extractor no longer recognizes that code. The OOS-aware model, `cubrid-verify-vacuum-slot-undo`, does not model `commit_frees_saved`.
- To check this PR's shape anyway, the coordinator applied the PR patch cleanly to the model's sync commit `e64a04a79a58` and ran the model in a scratch worktree.
  - **Unpatched:** `UserUndoFindsRoom` reports `KNOWN FINDING commit-window-saved-space`. The shape was read as `commit_frees_saved = before_commit_record` (log_manager.c:5278 before 5296).
  - **Patched:** the shape was read as `commit_frees_saved = after_commit_record` (5300 after 5288). The model printed `note: known finding commit-window-saved-space no longer applies`. `UserUndoFindsRoom` then fails only on the separate known forward-window finding (`relocation-forward-window-steals-saved`, fixed on `develop` by #8348). With that cause removed (`fwd_release=after_sysop_end`), it passes: 185,796 distinct states. `UserUndoFindsEmptySlot` passes (210,848 states). The exit code was 3 because the covered function changed, which is expected.
- Limits:
  - The model covers DELETE undo (`RVHF_DELETE`) only, not UPDATE undo. The runtime replay covers UPDATE undo.
  - The patched run uses the patch on the older sync commit, not the head tree.
  - The 2PC branch is not modeled.

**3. CI on the PR head.** These checks pass: gha-ci build (debug and release), test_sql, test_sql_by_cci, test_medium, test_shell, code-style, cppcheck, pr-style, license, and memory-monitor-check. `Check TC PRs` fails because of the empty TC draft PRs. That is a gate, not a regression.

**4. `cubrid-static-check`: not run.** It exited 2 because the review checkout had no `compile_commands.json` at the time. CI cppcheck and code-style pass on the head.

### Not executed

- The 2PC path. It has source evidence only, and its behavior is unchanged from base.
- An async-commit variant of the replay. The source argument (SF2, the shared `nxio_lsa` watermark) covers it.
- A torn multi-page log write. That rests on the engine's existing prefix assumption, which this PR does not change.
- A release build replay. The author reports 1/1 failure on base and 1/1 pass on head.
- A performance measurement.

## Unverified risks and dropped candidates

None of the following is attributed to this PR, and none blocks a merge.

**Pre-existing, outside this PR:**

- **R2-O1.** `spage_has_enough_total_space` subtracts other transactions' reservations only for an active transaction (`slotted_page.c:4624-4636`). A non-active consumer, such as a transaction running commit postpone, could take U's reserved bytes. The PR body lists this already. Whether any postpone action grows a heap page was not traced.
  - Next check: grep the postpone redo handlers for growing `spage_insert` or `spage_update`, or add a debug assertion at `slotted_page.c:4628`.
- **R2-O2.** Saved space exists only in memory. After a restart, a 2PC-prepared transaction has no reservation. The PR body lists this already.
- **R1 note.** Under `log_async_commit=yes`, 2PC prepare and decision records are not waited on (`logpb_flush_pages`). This may weaken XA durability. Not pursued.
- **R2-O3 (hardening).** If prior-node allocation fails, `log_append_commit_log` returns a NULL `commit_lsa` and the release still runs. Base had the same exposure. A guard on `LSA_ISNULL (&commit_lsa)` would be optional, low-value hardening.

**Rejected hypotheses:**

- R1: H1 through H5. The disproved claims were:
  - T's record gets a smaller LSA.
  - A log page with T's record is written before C.
  - A checkpoint makes U a loser while in `WILL_COMMIT`.
  - 2PC behavior changes.
  - Allocation failure is worse than base.
- R2: these hypotheses were disproved:
  - A new lock order arises.
  - U fails its own write because of its own reservation.
  - Postpone actions are affected.
  - `first_save_entry` leaks or is freed twice.
  - The longer window raises assertions or errors.

All of these are disproved by source evidence, not left unverified.

**Dropped counts:** R1 had 2 candidates, both downgraded to non-defect comments (N-1, N-2). R2 had 0 defect candidates and 4 observations (O1 through O3 above; O4 notes that the removal of a stale comment is correct).

## Budget accounting

- **Mode:** bounded. The user gave no absolute budget, and no hard cap was enforced.
- **Targets:** about 45 minutes and about 50 tool calls per reviewer.
- **Agents:** 2 specialist reviewers, with no retries and no continuations.

| Agent | Tokens | Tool calls | Wall time | Target |
|---|---|---|---|---|
| R1 (opus, xhigh) | 186k | 57 | 9.1 min | Tool-call target slightly exceeded, time target met |
| R2 (sonnet, xhigh) | 217k | 69 | 9.1 min | Tool-call target exceeded, time target met |

- **Coordinator usage:** unknown. It covers scope pinning, the formal-model runs, two debug builds, five runtime replays, adjudication, and this report.
- **Per-agent attribution:** the token figures come from the harness. Account-wide telemetry was not available.

## Artifacts

All local evidence is in the run directory `/home/vimkim/temp/cubrid-code-review/pr8532-bd9a0af/`:

- `manifest.md`, `coverage.md`
- `reviewers/r1-recovery-ha.md`, `reviewers/r2-systems-concurrency.md`
- `evidence/`:
  - the patch and the PR body
  - the Jira issue and its attachments
  - the `heap-slot-undo-*.out` and `tlc-sync-*` model outputs
  - the `runtime-{head,base}-N/` replay logs. `runtime-base-1` also keeps the database volumes in the state where restart recovery fails.
  - the build logs
