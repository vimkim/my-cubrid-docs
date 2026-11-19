# Code review: PR #8514 (CBRD-28073), Keep serial row storage form in NEXT VALUE

The user (PR author) asked for a review deep enough that merging PR [#8514](https://github.com/CUBRID/cubrid/pull/8514) into `feature/oos-merge` harms nobody. Part of the job was to check Greptile's two P1 comments.

**Most consequential result:** the fix itself does what it claims. It removes the CBRD-28035 chain leak and the CBRD-28052 rollback corruption, and both were reproduced at base and found absent at head. However, the PR **cannot be merged as is**. `feature/oos-merge` gained CBRD-27230 (`b43275e944`), which reworked the same functions. The natural conflict resolution compiles and silently disables the fix, or worse, writes zeroed OOS stubs (F1).

Both Greptile P1 comments describe real failures. Neither is a regression introduced by this PR: base fails the same way or more often. One remaining HA path, the ALTER merge at `serial.c:2285`, is cheap to close in this PR (F2).

Paths such as `reviewers/R*/…` and `evidence/…` refer to the local review run directory `/home/vimkim/temp/cubrid-pr-8514-review-20261119` (raw logs, probes). The evidence needed to judge each finding is summarized in this report.

## Verdict

- **Verdict:** `changes-required`
- **Follow-up review required:** **yes**. After the rebase onto the current `feature/oos-merge`, the integration with CBRD-27230's `reused_stub` / `RVREPL_OOS_REUSE` is new code and needs a delta review. The rebase must precede the merge.
- **Coverage:** complete for the planned assignments. Limits are listed under [Coverage and verification](#coverage-and-verification).

| Item | Value |
|---|---|
| Repository | CUBRID/cubrid, PR #8514, base branch `feature/oos-merge` |
| Base (merge base = PR baseRefOid) | `71993ddb63c80dff99ce814cc3cdcabed6d61834` |
| Head | `8d736ff51c0de65c0fa37f1e549d9fa90204657a` |
| Comparison | `git diff 71993ddb63c80dff99ce814cc3cdcabed6d61834 8d736ff51c0de65c0fa37f1e549d9fa90204657a` (9 files, +546/-13, patch sha256 `7f34cd48ef8b42c6aed1871ff23990fa5a2f7bc824e1e0373cbf4303a4241a5d`) |
| Target tip at review time | `8c478d8559905330bc1a60a05dbebb273b07a16c` (base + CBRD-28023, CBRD-27230, CBRD-27841). GitHub `mergeable: CONFLICTING` |
| Snapshot | 2026-11-19, rechecked before publication. The PR did not move. |

## Confirmed findings (attributed to this PR)

### F1 [P1, merge-blocking]: Merging onto current `feature/oos-merge` conflicts, and the obvious resolution silently disables the fix

**Failure.** CBRD-27230 ([#8559](https://github.com/CUBRID/cubrid/pull/8559), `b43275e944`) made two changes:
- It added `heap_oos_column_plan::reused` plus `char reused_stub[OR_OOS_INLINE_SIZE]` with byte-copy semantics.
- It added a parameter `bool reuse_oos_stubs = false` to `heap_attrinfo_transform_to_disk_internal`, right after `pending`.

This PR adds a field of the same name (`reused`, with oid/length/stamp semantics) and a parameter `bool keep_form = false` at the same position. Merging gives three conflict hunks in `heap_file.c`, but the call in `heap_attrinfo_transform_to_disk_keep_form` merges *without* conflict:

```c
return heap_attrinfo_transform_to_disk_internal (thread_p, attr_info, old_recdes, new_recdes, LOB_FLAG_INCLUDE_LOB,
                                                 nullptr, true);   // true now binds to reuse_oos_stubs
```

The consequences:
- After a straightforward conflict resolution, `keep_form` stays `false` and the serial path goes back to base behavior: re-demote and insert a new OOS chain under a redo-only log. The CBRD-28035 and CBRD-28052 bugs return, with no compile error or warning.
- If only the call site is fixed, `heap_attrinfo_keep_column_form` still fills `plan.oid/length/identity_stamp` and never `reused_stub`. The target's writer then `memcpy`s a zero stub. A NULL-OID stub ends up in the `_db_serial` row, and the comment becomes unreadable on the first NEXT VALUE of an inherited OOS row.

**Evidence.**
- Reviewer R4 (level 4–5):
  - Trial merge onto `b43275e944`, mechanical resolution: builds; `test_oos_sql_serial` 3/3 FAIL and `test_oos_sql_serial_rollback` 2/5 FAIL, exactly like the unfixed build.
  - With a two-line correction (copy the stub with `heap_recdes_get_oos_inline_stub` into `reused_stub`, and call `(…, nullptr, false, true)`): 8/8 pass, and an inherited-OOS DB keeps 3 chains with the comment intact and `checkdb` exit 0.
  - Retained: `reviewers/R4/logs/trial_merge_mechanical_to_corrected_delta.patch`, `merge1_*`, `merge2_*`.
- Coordinator replay: `git merge --no-commit 8d736ff51c` onto tip `8c478d8559` gives conflicts only in `src/storage/heap_file.c` (3 hunks). The keep-form call site auto-merges as `nullptr, true` against the 6-argument target prototype `(…, heap_pending_record * pending = nullptr, bool reuse_oos_stubs = false)`. Saved in `evidence/coord-merge-conflict.diff` and `evidence/coord-merge-keepform-callsite.txt`. I did not rebuild the trial merge; the test failures are R4's.

**Needed action.**
- Rebase onto the current tip. Make keep-form fill `reused_stub` (or reuse CBRD-27230's stub-copy helper). Pass `keep_form` unambiguously, for example as a separate enum or flag struct, or by reordering parameters.
- Rerun the 8 serial tests, the CBRD-27230 tests, and an inherited-OOS-row check (see F5).

### F2 [P2, pre-existing code, recommended for this PR]: A head-only DB can still put a `_db_serial` comment in OOS through the ALTER merge path, after which every NEXT VALUE stops HA replication

**Failure.**
1. `serial_row_write_keep_value` ([`serial.c:2285`](https://github.com/CUBRID/cubrid/blob/8d736ff51c0de65c0fa37f1e549d9fa90204657a/src/query/serial.c#L2285)) runs when an ALTER SERIAL's row write races with a concurrent NEXT VALUE. It still calls the OOS-deciding `heap_attrinfo_transform_to_disk`, so on 4K pages it demotes a long comment to OOS.
2. Every later head NEXT VALUE preserves that stub, as keep-form is designed to, and ships an RVHF_UPDATE image with an OOS reference and no `RVREPL_OOS_INSERT` item.
3. The slave's `xlocator_repl_force` calls `locator_fixup_oos_oids_in_recdes` with an empty `oos_oids` and returns `-1040` ([`locator_sr.c:16123`](https://github.com/CUBRID/cubrid/blob/8d736ff51c0de65c0fa37f1e549d9fa90204657a/src/transaction/locator_sr.c#L16123)). The whole force area aborts (`-1170`), and applylogdb retries the same LSA forever, so the entire DB stops replicating.

**Evidence.**
- R1 ran a real two-node HA pair in user namespaces with a fresh head-only 4K DB. Session A ran 60× ALTER COMMENT while B ran prepared NEXT VALUE ×20000. In 1 of 5 runs the master `_db_serial` got an OOS file, the slave logged `-1040 missing OOS OID` and stalled at `current_val 302` against the master's `20000` (`reviewers/R1/logs/ha-stress-race-head/`).
- The deterministic variant (master row already OOS from a pre-PR build) fails at head and at base (R1 P3/P4, level 5).
- Coordinator replay of the deterministic variant at head: the slave logged `ERROR CODE = -1040 … locator_sr.c, line 16123 … applylogdb` and then `-1170 Failed to flush replication items` (`evidence/coord-R1-preoos-head.stdout`, `reviewers/R1/logs/ha-coord-preoos-head/`). I did not replay the race variant.
- This agrees with `jira-comment-alter-merge-followup.md`: the merge path *does* insert a chain, with no leak, because the chain is reclaimed in the same undoable update. That note excluded HA, and this finding supplies the HA consequence.

**Attribution.** The code at `serial.c:2285` is unchanged by the PR, and base fails more broadly: every NEXT VALUE on such a serial fails on its first replicated call (R1 P2). The PR does not introduce the stall. It leaves this path open, while the PR's goal (serial rows never gain OOS state through serial-internal writes) suggests closing it.

**Needed action.** In `serial_row_write_keep_value`, build the merged row with `heap_attrinfo_transform_to_disk_keep_form (thread_p, &write->new_info, new_recdes, merged)`. The client image is inline for system classes (`locator_finalize_oos_record` skips them), so the merge stays inline and inserts no chain. As a follow-up, the serial path could publish `RVREPL_OOS_REUSE` items, which exist on the current tip, for rows inherited from pre-PR builds.

### F3 [P3, introduced, narrow]: On 4K pages, NEXT VALUE on a long-comment serial can fail for lack of page space where base succeeded

**Failure.** `current_val` is a variable-size NUMERIC (`numeric_repr_disk_size_by_value`: 4→20 bytes, at most +16 per size class). `serial_update_serial_object` rewrites the same slot. Base escaped page-full on rows larger than the 4K demotion target (~1008 bytes) only by moving the comment into a new OOS chain under a redo-only record, which is the bug the PR fixes. Keep-form keeps the comment inline. Debug builds then assert at [`serial.c:1588`](https://github.com/CUBRID/cubrid/blob/8d736ff51c0de65c0fa37f1e549d9fa90204657a/src/query/serial.c#L1588), and release builds return `ER_QPROC_CANNOT_UPDATE_SERIAL`.

**Preconditions (all needed):**
- 4K pages. On 8K/16K pages base never demoted serial rows, so the two builds behave the same.
- A serial row over ~1008 bytes inline (comment over ~850 incompressible characters).
- A `_db_serial` heap created with `unfill_factor≈0`, or a page reserve already consumed.
- A `current_val` crossing a size class.

With the default `unfill_factor` (405-byte reserve on 4K), R3 ran 160 NEXT VALUEs and R5 ran a 40-serial variant without failure.

**Evidence.** R3 S1 (level 5): head asserted on NEXT VALUE #2, while base demoted (OOS records 1→4, leaking). R3 S6 head-release: `Cannot update serial object.` Coordinator replay of S1 (`evidence/coord-R3-S1-{head,base}.log`): head NEXT VALUE #2 and #3 gave `csql exit=134`, `serial.c:1588: … Assertion 'spage_is_updatable (…)' failed`; base gave exit 0 for all three.

**Needed action.** Document this as a known limitation in the PR body. The real fix is PE1/PE3: check for space before logging, and relocate safely or reserve the worst-case growth. That work can be a follow-up issue.

### F4 [P3]: PR description inaccuracies

- "이전 빌드에서 comment가 OOS로 옮겨진 DB는 이전과 같이 OOS 참조를 담은 이미지를 복제한다" ("a DB whose comment an earlier build moved to OOS replicates the image with the OOS reference as before"). Those images are **rejected** by the slave, at base and at head (F2, level 5). HA has now been run.
- "serial을 ALTER하면 … comment의 OOS 배치는 그때 정상 경로로 정해진다" ("on ALTER the client rewrites the row by the normal path, so OOS placement is decided then"). The client path keeps `_db_serial` inline, but the server-side merge can demote the comment (F2).
- The Test Plan table says base fails with `-1397`. At base `71993ddb63` the code is `-1398` (`ER_HEAP_OOS_CORRUPTED_RECORD`), as observed by R4 and R5. "OOS ctest 69개": `ctest -N` lists 70 at head (R4).
- The "24 serials filled a 4K page" row ran with the default reserve. It does not cover `unfill_factor=0` (F3).

### F5 [P3, missing evidence]: No automated test covers the OOS-keeping branch

All 8 new tests start from an inline comment. After this PR no SQL path creates an OOS serial row, apart from the F2 race. The `reused` branch, `payload_size += OR_OOS_INLINE_SIZE`, and the stub write therefore run only in manual checks on older-build DBs (R2, R4, R5 repeated these at level 5). The F1 half-resolution passes all 8 tests while writing zero stubs. A server-side test that runs `heap_attrinfo_transform_to_disk_keep_form` over a record holding an OOS stub (a user class is enough) and compares stub bytes and OOS record counts would close this. This is a test gap, not a demonstrated defect.

## Greptile comments: disposition

| Greptile | Claim | Verdict | Evidence |
|---|---|---|---|
| P1-1 [`serial.c:1576`](https://github.com/CUBRID/cubrid/pull/8514#discussion_r4627183025) | An existing OOS serial's NEXT VALUE fails HA apply (`locator_fixup_oos_oids_in_recdes`, empty `oos_oids`) | **Behavior confirmed, not a regression.** At base it fails on every NEXT VALUE of a long-comment serial on 4K pages (and leaks a chain). At head it fails only for rows already holding OOS: pre-PR build rows, or the F2 race. | R1 P2/P3/P4/P7 (real HA pair, level 5); R4 path trace (level 3, independent); coordinator replay |
| P1-2 [`heap_file.c:14255`](https://github.com/CUBRID/cubrid/pull/8514#discussion_r4627183032) | Keeping an inline long comment makes NEXT VALUE fail on a full page; the redo log is written before space is confirmed | **Behavior confirmed. Mostly pre-existing.** The PR only exposes the narrow window in F3. Same-slot growth failing on a full page affects ordinary rows at base and on develop (PE3). Redo-before-space-check is pre-existing and severe (PE1). | R3 S1/S2/S6 and base-release S6' (level 5); R5 independent SQ2 (level 5, release emulated in gdb); R2 recovery argument (level 3); coordinator replay of S1 |

## Pre-existing defects found (not attributed to this PR; separate CBRD issues recommended)

| ID | Priority (severity) | Defect | Evidence | Coordinator replay |
|---|---|---|---|---|
| PE1 | P1 | `serial_update_serial_object` appends the redo-only RVHF_UPDATE (`serial.c:1590`) **before** `spage_update`. The space check is a debug-only `assert`. In release, if the row does not fit, the update fails but the redo record stays. After any later log flush and a crash before the next checkpoint, restart replays the record, `heap_update_physical` fails, and `log_rv_redo_record_sync` calls `logpb_fatal_error`. **The DB cannot be restarted**, and `checkdb` fails the same way. | R3 S6 / S6' on head-release and **base-release** (level 5: `LOG FATAL ERROR: log_rv_redo_record_sync: Error applying redo record at log_lsa=(794, 1560) … data_length = 766`); R2 R2-F1 (level 3); R5 U2 saw no failure without a flush | not replayed (needs release builds) |
| PE2 | P1 | NEXT VALUE on a **relocated** `_db_serial` row writes the full image into the home `REC_RELOCATION` slot (`serial.c` passes the home page and slot, and `spage_update` keeps the slot type). The NEWHOME record is orphaned, later reads abort in `pgbuf_is_valid_page`, and `checkdb` fails in `heap_check_heap_file`. Runtime and recovery diverge, because redo changes the slot type. | R3 S4 at head and base (level 5); R5 C3 at base (level 5; at head the image did not fit and the assert fired instead) | not replayed |
| PE3 | P2 | Same-slot in-place growth with no relocation path: NEXT VALUE fails on a full page for any serial row (`unfill_factor≈0` or reserve consumed). | R3 S2 at head and base (level 5); R5 | covered by F3 replay mechanics |
| PE4 | P2 | HA: any `_db_serial` image with an OOS stub stalls applylogdb (Greptile P1-1 at base). | R1 P2/P4 (level 5) | replayed at head (F2) |
| PE5 | P3 | `serial_update_serial_object` `exit_on_error` does not call `repl_end_flush_mark` after `repl_start_flush_mark`, so the flush mark stays set for the rest of the transaction. | R4, R3 (level 2) | — |
| PE6 | P2 (base only) | Base: SA exit write-back of a cached long-comment serial asserts `log_sysop_start: tdes->is_allowed_sysop ()` (`log_manager.c:3797`), because the write-back inserted an OOS chain. **Fixed by this PR.** | R5 §4.2 (level 5) | — |

## Safety facts and effects outside the diff

| Effect | Fact that makes it safe | Owner | Evidence |
|---|---|---|---|
| Rollback, savepoint and statement rollback after NEXT VALUE | Keep-form inserts no chain. A reused chain is committed, or it belongs to an uncommitted DDL whose undo restores the full row pre-image before deleting the chain. | R2 | level 5: SA1–SA5, S1, S2, S7, S8; CBRD-28052 reproduced at base (`ERROR: out-of-row storage record metadata is inconsistent`) and absent at head on the same snapshot |
| Crash restart | RVHF_UPDATE redo is physical and LSA-guarded. A committed sysop is not undone. Chains named by redo images precede them in the WAL. | R2, R5 | level 5: `kill -9`, then recovery, then `checkdb` OK |
| Reclaim on ALTER/DROP after NEXT VALUE | `_db_serial` is MVCC-disabled (`mvcc.c:696`). Reclaim takes the old-image refs minus the new-image refs under the page latch, and keep-form leaves the ref set unchanged. | R2 | level 5: OOS count fell by exactly the dropped chain |
| Identity stamp of a reused stub | `pack(unpack(P)) == P`, and the chain is not rewritten. | R2, R4 | level 5 (reads through the chain, MD5 equal) |
| Row size accounting with a reused stub | +24 = OID + length + stamp, and the writer emits exactly 24 bytes. Offsets are 2-byte for every serial row. | R3, R4 | level 5 |
| Concurrency (15 sessions, mixed NEXT VALUE / ALTER / DROP / CREATE / ROLLBACK) | The page latch was already held across the sequence. Keep-form adds only in-memory parsing. | R5 | level 5: 0 duplicate values, no leak, `checkdb` OK |
| Serial semantics | Values, `started` and cache arithmetic are unchanged. | R5 | level 5: 78-statement script, base and head outputs identical |
| CDC / flashback | Supplemental logging excludes system classes. The serial supplemental record carries no row image. | R1 | level 2 |
| Raw-record precondition | Both serial read sites use `HEAP_RECDES_DONT_CONSUME_RAW_BYTES`, so keep-form sees the stub. | R2 | level 2 + level 5 (a reclaimed chain proves the stub was kept) |

## Coverage and verification

Reviewers ran as Claude Code agents in Herdr panes (workspace `develop` `w2M8`, tab `pr8514-review` `w2M8:t2`), with account slots ai1, ai2, ai3 in round robin. Coverage table and run manifest are kept in the local review run directory; their essentials are in this report.

| ID | Role | Account / model | Result | Report |
|---|---|---|---|---|
| R1 | HA (SQ1 owner) | ai1 / opus | complete; real HA pairs on head and base | `reviewers/R1/report.md` |
| R2 | Recovery / OOS lifetime | ai2 / opus | complete | `reviewers/R2/report.md` |
| R3 | Storage / page space (SQ2 owner) | ai3 / opus | complete; built own release builds | `reviewers/R3/report.md` |
| R4 | Systems C/C++ (SQ1 second seat) | ai1 / sonnet | complete; trial merge + builds | `reviewers/R4/report.md` |
| R5 | Concurrency / semantics / spec (SQ2 second seat) | ai2 / sonnet | complete | `reviewers/R5/report.md` |

**Shared questions.**
- **SQ1** (Greptile P1-1): R1 (opus, real HA) and R4 (sonnet, source trace) independently concluded *confirmed behavior, pre-existing, narrowed by the PR*. Only R1 found the F2 race path, which R4 noted as unassessed.
- **SQ2** (Greptile P1-2): R3 (opus) and R5 (sonnet) independently concluded *confirmed, mostly pre-existing; introduced only in the 4K long-comment window*. Both independently found PE2.

**Checks run (head `8d736ff51c` debug_gcc unless stated):**
- New ctests: `test_oos_sql_serial` 3/3 and `test_oos_sql_serial_rollback` 5/5 pass at head. At `0520b5170c` (base + test-only commit) they give 3/3 FAIL and 2/5 FAIL (R4, R5).
- The CBRD-28052 rollback scenario errors at base and is clean at head (R2 SA5).
- HA pairs: P1–P8 on head and base installs (R1).
- Page-full S1–S6 including base and head release builds (R3).
- Server-mode stress with `kill -9` (R5).
- Trial merge onto `b43275e944` with builds (R4).
- Coordinator: trial merge onto `8c478d8559`, R3 S1 replay (head and base), R1 pre-OOS HA replay (head).

**Not run or limits:**
- The full 70-test OOS ctest at head.
- 16K-page reachability of F2 (needs a near-maximal 4-byte UTF-8 comment).
- RENAME concurrent with NEXT VALUE.
- A cached serial's write-back in HA.
- The keep-form representation-mismatch branch (needs a catalog migration of `_db_serial`; DBA cannot ALTER it).
- Release-build execution for PE2.
- Coordinator replay of PE1/PE2 and of the F2 race variant.
- R1 also observed `ERROR: Invalid XASL tree node content.` 1–2 times per 20000 prepared NEXT VALUEs racing with ALTER COMMENT. It was not attributed and not tested at base.

## Unverified risks and dropped candidates

- **U1 (P3, level 2):** the `heap_attrinfo_transform_to_disk_keep_form` contract is implicit. It needs a raw (DONT_CONSUME) `old_recdes` and must not get NULL or a non-null `pending`. Violations silently inline and orphan a chain, or write NULL-OID stubs. Unreachable today. Next step: state the precondition and `assert (old_recdes != NULL)` (R2-O1, R4-F3).
- **U2 (P3, level 2):** keep-form returns `ER_GENERIC_ERROR` for an OOS row whose representation id is not the latest. Then the debug `assert (false)` at `serial.c:1579` fires, and in release NEXT VALUE fails until an ALTER rewrites the row. This is reachable only through an in-place catalog migration of `_db_serial`, which this tree does not have. Next step: a specific error code, or keep the stub bytes regardless of representation (R2, R3, R4, R5).
- **Dropped or cleared:** dangling chains after rollback, crash or vacuum; stamp corruption; offset-width growth; `started` growth; latch-order hazards; duplicate values; other redo-only writers (there are none besides `serial.c:1590`); CDC readers. Each was disproven with level 2–5 evidence in the reviewer reports.

## Budget accounting

- Bounded mode, with no user absolute budget and no hard cap enforced.
- Per-reviewer target was about 90 minutes of wall time. Actual: R2 ~20 min, R4 ~20 min, R1 ~37 min, R3 ~37 min, R5 ~45 min, all within target.
- 5 agents, no retries. One blocked approval prompt (R5, a dangerous-`rm` check inside its own directory) was declined and the agent resumed.
- Usage telemetry is unavailable for slots ai1–ai3 (`setup-token usage requires profile permission`), so per-agent token usage is unknown.
- The coordinator reserved time for replay and used it for three replays.

## Recommended next steps (in order)

1. Rebase onto the current `feature/oos-merge` and resolve F1 as described. Rerun the serial tests, the CBRD-27230 tests, and an inherited-OOS check.
2. Apply the one-line F2 change at `serial.c:2285` in this PR, or file it as a follow-up.
3. Fix the PR body (F4).
4. File separate CBRD issues for PE1 (DB restart impossible) and PE2 (catalog corruption). Both are pre-existing and reachable only on tightly filled serial pages, but both are severe.
5. Run a delta review of the rebased head.
