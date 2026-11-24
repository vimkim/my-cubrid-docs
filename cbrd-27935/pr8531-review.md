# Review: CUBRID/cubrid#8531 — [CBRD-27935] Keep the vacuumed forward page fixed until the relocation sysop ends

- **Review date (`Asia/Seoul`):** `2026-11-24`
- **Tracker:** `#1068` · [CBRD-27935](https://jira.cubrid.org/browse/CBRD-27935)
- **Goal.** `cubrid-code-review` of [CUBRID/cubrid#8531](https://github.com/CUBRID/cubrid/pull/8531) at a fixed snapshot.

**Most consequential result.** No confirmed defect. The change closes the restart-recovery window it targets.

- **Runtime replay at base:** the Jira reproducer, run against the base debug build, failed 2/2 on the `spage_insert_for_recovery` slot-empty assertion (`slotted_page.c:1969`).
- **Runtime replay at head:** against the head debug build it passed 2/2. The concurrent INSERT waited on the forward-page latch, restart recovery finished, all 14 committed rows survived, and `checkdb -S` passed.
- **TLA+ model:** the heap slot-undo model passes all vacuum-undo properties at head. At base the same properties fail with the recorded `relocation-forward-window-*` findings.

## Verdict and follow-up

| Field | Value |
| --- | --- |
| Verdict | `no-confirmed-findings` |
| GitHub review status | `APPROVED` submitted |
| Follow-up review required | **no** |
| Coverage | complete for all applicable invariants. See [pr8531-coverage.md](pr8531-coverage.md) and coverage limits below for the optional checks that were not run. |

Nothing has to be done before merge from the code-review side. Merge readiness still depends on two things outside this review: the TC Merge Gate (the two empty bot TC PRs must be closed by the human) and CI triage (see "Existing CI" below). Both of those failures are unrelated to this diff.

## Snapshot

| Item | Value |
| --- | --- |
| Repository / PR | [CUBRID/cubrid#8531](https://github.com/CUBRID/cubrid/pull/8531), author `hornetmj`, head `hornetmj:CBRD-27935-hold-forward-page`, base `develop` |
| Base (PR API) = merge base | `95cc1bc172a7b431948e7b8297987a9466371986` |
| Head | `d26383d2df856a1bfb6989bbff8aa7760de8055c` |
| `develop` tip at pinning | `8e052e99c508141dbdd6dc338b65e437e31d756a` (not the comparison base) |
| Comparison | `git diff 95cc1bc172a7b431948e7b8297987a9466371986 d26383d2df856a1bfb6989bbff8aa7760de8055c` |
| Patch SHA-256 | `bc6916b2612df0ba65732839802be0ef64d66e34302d5c40bb2cfefac9bf18d1` |
| Changed paths | [`src/query/vacuum.c#L2436-L2446`](https://github.com/CUBRID/cubrid/blob/d26383d2df856a1bfb6989bbff8aa7760de8055c/src/query/vacuum.c#L2436-L2446) (+5/−2), a single hunk in `vacuum_heap_record` |
| Remote recheck | 2026-11-24T12:40:37Z: head and base unchanged. One existing approval (`hgryoo`, on `d26383d2df`). |
| Requirements | CBRD-27935 and the PR description |

## What changed

In `vacuum_heap_record`, case `REC_RELOCATION` ([`vacuum.c#L2436-L2446`](https://github.com/CUBRID/cubrid/blob/d26383d2df856a1bfb6989bbff8aa7760de8055c/src/query/vacuum.c#L2436-L2446) at head), the order of the last steps changes:

| | Order |
| --- | --- |
| Before | vacuum forward slot, then `heap_add_bestpage`, then log `RVVAC_HEAP_RECORD_VACUUM`, then **`pgbuf_set_dirty(fwd, FREE)`** (latch released), then `log_sysop_commit` |
| After | the same steps up to the log record, then **`pgbuf_set_dirty(fwd, DONT_FREE)`**, then `log_sysop_commit`, then **`pgbuf_unfix_and_init(fwd)`** |

The forward page's WRITE latch is now held until `LOG_SYSOP_END` has an LSA in the prior list. The home page already followed this pattern before the patch.

## Confirmed findings

None.

## Safety facts and effects outside the diff

| # | Safety fact | Owner | Pinned evidence | Level | Result |
| --- | --- | --- | --- | --- | --- |
| S1 | The forward page stays WRITE-latched from `vacuum_heap_prepare_record` ([`vacuum.c#L2003`](https://github.com/CUBRID/cubrid/blob/d26383d2df856a1bfb6989bbff8aa7760de8055c/src/query/vacuum.c#L2003)/[`2026`](https://github.com/CUBRID/cubrid/blob/d26383d2df856a1bfb6989bbff8aa7760de8055c/src/query/vacuum.c#L2026)) until after `log_sysop_commit` returns ([`vacuum.c#L2443-L2445`](https://github.com/CUBRID/cubrid/blob/d26383d2df856a1bfb6989bbff8aa7760de8055c/src/query/vacuum.c#L2443-L2445)). `DONT_FREE` does not unfix the page (`page_buffer.c:5530-5570`). | Latch | source; runtime: the gdb hold shows `forward_page` non-NULL at head and `(nil)` at base | 5 | holds |
| S2 | `log_sysop_commit_internal` runs `log_sysop_do_postpone` (a no-op here), then `log_append_sysop_end` → `prior_lsa_next_record`. That call assigns the LSA and links the node under `prior_lsa_mutex` before it returns (`log_manager.c:3974-3988, 4564-4620`; `log_append.cpp:1381-1559`). The coordinator read this directly. | Latch, Recovery, Coordinator | source | 3 | holds |
| S3 | Every other writer of the forward page needs the WRITE latch ([`bestspace.cpp#L753`](https://github.com/CUBRID/cubrid/blob/d26383d2df856a1bfb6989bbff8aa7760de8055c/src/storage/bestspace.cpp#L753), [`962`](https://github.com/CUBRID/cubrid/blob/d26383d2df856a1bfb6989bbff8aa7760de8055c/src/storage/bestspace.cpp#L962); `heap_file.c:21726, 21792, 22246-22250`), so all of its records get LSAs after `LOG_SYSOP_END`. | Latch, Recovery | source; runtime: the INSERT blocked for the full 15 s at head and committed immediately at base | 5 | holds |
| S4 | The log flushes as an LSA prefix. `logpb_prior_lsa_append_all_list` detaches the whole prior list under `prior_lsa_mutex` (`log_page_buffer.c:3157-3200`). The in-flight ring (`log_prior_inflight`) is a read-side cache of MVCC undo images and does not reorder the drain. WAL flushes through the page LSA before a data-page write (`page_buffer.c:11574-11582`). | Coordinator (closes the recovery reviewer's U1) | source | 3 | holds |
| S5 | At restart, an outermost system-worker sysop whose `LOG_SYSOP_END` is durable is skipped (`lastparent_lsa = NULL`). An open one is undone in descending LSA order through `vacuum_rv_undo_vacuum_heap_record` → `heap_rv_redo_insert` → `spage_insert_for_recovery` (`log_recovery.c:987-1009, 1634-1660, 4756-4790, 4995-5130`; `vacuum.c:7589-7594`). | Recovery | source; runtime at base hit exactly this path | 5 (path) | holds |
| S6 | Holding the page through `log_sysop_commit` adds no reverse wait edge. The call skips postpone, repl-info (system worker), and the TDE lookup (`RV_NOT_DEFINED`), and holds only `prior_lsa_mutex` and its own `lock_topop`. Under prior-list pressure it only wakes the flush daemon and sleeps 1 ms in SERVER mode. The home page was already held through the same call. | Latch, Recovery | source | 3 | holds |
| S7 | `heap_add_bestpage` still runs before sysop commit. It only publishes a hint, and every consumer WRITE-latches before using the space. #8348 moved this call after the commit; that difference does not affect correctness. | Latch, Recovery | source | 2-3 | holds |
| S8 | HA, CDC, and format: the vacuum worker's records and their order are unchanged. A system worker emits no replication or supplemental records. `log_applier` ignores vacuum trids (`log_applier.c:5825-5829`). The log and disk format is unchanged. | Recovery | source | 2 | not applicable |

**Unproven safety facts:** none material.

## Coverage and verification

Full table: [pr8531-coverage.md](pr8531-coverage.md). Both independent seats answered the shared challenge (latch: `gpt-6.1-sol`; recovery: `claude-opus-5-5`). They agree, and each covers points the other does not.

| Check | Command / identity | Result |
| --- | --- | --- |
| Heap slot-undo TLA+ model, head | `python3 ~/.claude/skills/cubrid-verify-heap-slot-undo/scripts/check.py --rev d26383d2df856a1bfb6989bbff8aa7760de8055c` (TLC 1.7.4) | exit 3. `VacuumUndoFindsEmptySlot`, `VacuumUndoFindsRoom`, and `UserUndoFindsEmptySlot` pass (225116 states). `UserUndoFindsRoom` shows only the pre-existing `commit-window-saved-space` finding and passes once that cause is removed. The notes say all three `relocation-forward-window-*` findings no longer apply. Exit 3 means "covered code changed since the sync commit". The only change is the release point, which the script reads itself, so the model still describes the code. |
| Heap slot-undo TLA+ model, base | same script with `--rev 95cc1bc172a7b431948e7b8297987a9466371986` | exit 0, with the known findings `relocation-forward-window-slot`, `-room`, and `-steals-saved`. Each passes with `fwd_release=after_sysop_end`. |
| First-attempt TLC runs | as above (Codex) | identical to the replay |
| Vacuum/OOS slot-undo model | `check.py --rev d26383d2df…` | exit 2, `OUT OF SYNC` as expected: there is no OOS code in develop |
| Runtime reproducer, head debug | Jira attachment `vacuum-reloc-crash.sh` (read in full before running). `debug_gcc` built from `d26383d2df` with `just configure && just build-and-install`. `TEST_RUN_PORT=41000`, private `CUBRID_DATABASES`. | **2/2 pass**. The vacuum worker held at `log_sysop_commit` with `REC_RELOCATION` and forward OID `1\|643\|4`. The INSERT waited. Recovery succeeded with 14 rows / 14000 bytes, and `checkdb` passed. |
| Runtime reproducer, base debug | the same script with a disposable base worktree build of `95cc1bc172`, `TEST_RUN_PORT=42000` | **2/2 fail**. The INSERT committed while vacuum was held. On restart: `slotted_page.c:1969: spage_insert_for_recovery: Assertion 'slot_p->offset_to_record == SPAGE_EMPTY_OFFSET' failed.` |
| Static check | `cubrid-static-check --compile-db build_preset_debug_gcc/compile_commands.json 95cc1bc172… d26383d2df…` | exit 0. 0 new cppcheck, clang-tidy, or CPD findings. `vacuum_heap_record` CCN 9, length +3. |
| Existing CI at head | `cubrid-ci collect 8531 --commit d26383d2df… --suite test_shell --suite test_sql_by_cci`; `cubrid-tcc status <case>` | Run 44051622940 built `d26383d2df`. Build (debug/release), `test_medium`, and `test_sql` pass. `test_shell` has 2 NOK: `_06_issues/_26_2h/apis_1124` and `apis_1125`. Both are CCI/JDBC `sslmode` message mismatches, and they failed in 68/68 and 72/72 runs across PRs in the last 14 days, so they are not attributable. `test_sql_by_cci` failed, but its artifact collection failed (remote XML decode error), so it was not analyzed. Plain `test_sql` passed at the same head. |

**Coverage limits (optional, not blocking):**

- The runtime replay used debug builds only. The author reports release 1/1 fail at base and 1/1 pass at head; that was not replayed.
- The bytes-only variant (a writer takes another slot but uses the returned bytes) is covered by the model (`VacuumUndoFindsRoom`) and the S3 latch argument, not by a runtime run. The author did not run it either.
- The SA-mode checkpoint boundary was traced in source only.
- `test_sql_by_cci` failures were not triaged.
- The runtime proves the latch blocks a concurrent INSERT under one schedule. Formal coverage of all schedules comes from the model, within its stated bounds: one vacuum worker, two inserters, one crash.

## Unverified risks and dropped candidates

None of these risks is attributable to the PR.

| ID | Classification | Statement | Owner / next check |
| --- | --- | --- | --- |
| PRE-1 | Pre-existing, model finding (`commit-window-saved-space`, unreported in Jira) | `log_commit_local` calls `spage_free_saved_spaces` (`log_manager.c:5282`) before the commit record (`5300`). A no-postpone delete's saved bytes can be taken and committed by an INSERT. After a crash, the loser's `RVHF_DELETE` undo can hit `SP_DOESNT_FIT`. Present at base and head alike. | Separate ticket if wanted. Model it with `--set commit_frees_saved=after_commit_record`. |
| PRE-2 | Pre-existing robustness note, L2 | In `log_recovery_undo`, the system-worker branch (`log_recovery.c:4756-4762`) never sets `tran_index`. After an earlier "SYSTEM ERROR" path, a system-worker record could be skipped. This requires an analysis inconsistency first. | Optional source follow-up. |
| PRE-3 | Pre-existing, L2 | `log_append_sysop_end` allocation failure returns without appending, guarded only by an assertion (`log_manager.c:4573-4581`). | Optional. |

**Dropped candidates by reviewer:**

- **Latch reviewer: 6 hypotheses, all disproved at source level (L3).**
  - Premature reuse despite `DONT_FREE`.
  - A page/prior/`LOG_CS` cycle.
  - A double unfix or stale pointer.
  - SA self-flush deadlock.
  - A measured performance regression. Not established: the added hold is a single in-memory append.
  - END allocation failure. Pre-existing; recorded as PRE-3.
- **Recovery reviewer: 8 hypotheses (H1–H8), disproved at L2–3.**
  - A nested sysop.
  - The system tdes not being undone.
  - A page latch taken inside commit.
  - A lost dirty mark.
  - An early consumer through bestspace.
  - Other vacuum or dealloc paths.
  - An undo with no room inside the window.
  - SA checkpoint.
- **Coordinator:** no extra candidates.

## Other observations (not defects)

- The new comment at `vacuum.c:2439-2440` is accurate.
- `VACUUM_PERF_HEAP_TRACK_LOGGING` now also counts the unfix. This has no practical effect.
- Backport to `release/11.4` and `11.3` is a planning question, as noted in the PR. The PR also notes that logs already damaged by a pre-fix binary are not repaired.
- No TC is added. The author proposes a handover-time gdb-based shell TC outside CI. The two bot TC PRs (`cubrid-testcases#4197`, `cubrid-testcases-private-ex#4905`) are empty and need human closure for the TC Merge Gate (`Check TC PRs` currently fails).

## Budget accounting

| Item | Value |
| --- | --- |
| Mode | Bounded (default). No explicit user limit. **No hard cap enforced.** |
| Agents | First attempt (Codex): latch seat on `gpt-6.1-sol`, about an 8-minute target, met per its report. This session: recovery seat on `claude-opus-5-5`, 15-minute target, 5.4 min, 129.5k subagent tokens, 39 tool calls, 0 retries. The planned `gpt-6.2-sol` recovery seat never ran and was replaced. |
| Coordinator | Usage unmeasured. Spent on model replay, two debug builds, four runtime runs, static check, and CI evidence collection. |
| Overshoot | None measurable. Targets are prompts, not caps. |

## Local run archive provenance

Raw logs, TLC outputs, runtime runs, static check, CI evidence, and reviewer reports remain archived locally outside Git at `/home/vimkim/temp/cubrid-pr-8531-review.6AzCgI/`. No `handoff.md` was written, because no required check remains.
