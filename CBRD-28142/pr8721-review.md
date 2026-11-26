# Code review — CUBRID/cubrid#8721 + cubrid-testcases-private-ex#5126 (CBRD-28142)

**Goal.** A thorough review of "[CBRD-28142] Keep every log archive left in a backup taken while vacuum is disabled". Scope: backup archive selection with `vacuum_disable=yes`, numbering and removal boundaries, restore and recovery correctness, concurrency, and whether TC #5126 checks the fix reliably.

**Most consequential result.** No confirmed defect in the engine change. The fix does what it claims. I checked it at the head SHA with a debug build:
- The fixed TC passed twice.
- The TC failed on the base build.
- Three targeted probes passed: the archive-removal gate, a missing oldest archive, and a missing middle archive, each with `-S` and/or `-C`.

The TC deterministically catches the `-S` defect. It does **not** independently catch the original `-C` defect, and its header claims more than it checks. These points are non-blocking.

| Item | Value |
|---|---|
| Engine PR | https://github.com/CUBRID/cubrid/pull/8721 (author hornetmj; reviewers lht1199, vimkim) |
| base / head / merge-base | `af6f1df42bb044376159ab06784526e57cb56647` / `5d6b8cc8fb9a547eba365f1ce217b5b4858b1dd6` / `af6f1df42bb044376159ab06784526e57cb56647` |
| Comparison | `git diff af6f1df42bb044376159ab06784526e57cb56647 5d6b8cc8fb9a547eba365f1ce217b5b4858b1dd6` (sha256 `02d2d0b5…7bc7e`); 1 file, `src/transaction/log_page_buffer.c` +65/−27 |
| TC PR | https://github.com/CUBRID/cubrid-testcases-private-ex/pull/5126, base `79455ba64871906d730337654bb34f6ef0516091`, head `82dbac26b05382af705533f2d1ec0ce576494ff4`; 1 new file `shell/_40_guava/cbrd_28142/cases/cbrd_28142.sh` (+145) |
| Snapshot | 2026-11-26 KST |

## Verdict and follow-up

- **Verdict: `no-confirmed-findings`** → recommendation **APPROVE**, with the non-blocking comments below.
- **Follow-up review required: no.** All suggestions are optional. If the author changes the code or TC in response, a delta review is needed.
- Merge-gate note: the PR is not vimkim's. Merging belongs to the author through the usual flow, and the TC Merge Gate is still open (both TC PRs open).

## What changed and why it is safe

At base, with `vacuum_disable=yes`, `vacuum_min_log_pageid_to_keep()` returns 0 (`vacuum.c:6156-6160`). `logpb_backup` then resolves page 0 with `logpb_get_archive_number`:
- **If archive 000 exists**, it returns 0 and the online backup copies every archive.
- **If archive 000 is gone** (an earlier removal, or a DB restored from a backup that left old archives out), a debug build hits `assert(false)`. A release build falls back to `last_arv_num_for_syscrashes`, so it silently leaves out archives that vacuum will later read.
- **For SA (`-S`)**, the whole archive selection and copy sat under `#if defined(SERVER_MODE)`, so an SA backup copied **no** archive at all.

The patch adds a `PRM_ID_DISABLE_VACUUM` branch that applies to both server and SA:
- It scans forward from `hdr.last_deleted_arv_num+1` to the first archive that exists, then sets `first_arv_needed = MIN(first_arv_needed, oldest)`.
- It moves `logpb_backup_needed_archive_logs` out of `SERVER_MODE`. Only the removal pin (`backup_first_arv_num_needed`) stays server-only.
- The vacuum-enabled path is moved into the `else` unchanged.

| Safety fact | Owner | Evidence | Level |
|---|---|---|---|
| S1. No archive is removed while vacuum is disabled, by any path (`log_max_archives`, `force_remove_log_archives`, `backupdb -r`, HA). So archives from `last_deleted+1` to `nxarv-1` are a superset of what recovery or re-enabled vacuum will read. | R2, R1 | Gate `vacuum_is_safe_to_remove_archives()` at `log_page_buffer.c:6292,6548`. The flag is set only in `vacuum_update_keep_from_log_pageid` (`vacuum.c:6236-6240`), which disabled-vacuum boot never reaches. **Probe P1:** `log_max_archives=1 force_remove_log_archives=yes`, `backupdb -C -r` → archives 000–006 intact, `last deleted −1`, restore = source. | 5 |
| S2. `vacuum_disable` cannot change at runtime, so the branch cannot flip mid-backup. | R2, coordinator | `system_parameter.c:3883-3887` flags `PRM_FOR_SERVER \| PRM_HIDDEN`, no `PRM_USER_CHANGE`. | 2 |
| S3. The forward scan, the frozen range `[first..nxarv-1]` and the active-log copy all happen in one LOG_CS hold. Archive creation needs LOG_CS and removal is gated, so the scan cannot race. | R2 | `log_page_buffer.c:8755-8856` | 3 |
| S4. The vacuum-enabled path behaves exactly as at base. The new `first_arv_needed >= 0` guard is a no-op in SERVER_MODE (the value is always ≥ 0 there). | R1, R2 | Diff reading. | 3 |
| S5. The SA copy path touches no server-only state. The pin is reset on success and in `error:` (`9001`, `9035`) in server mode only. | R1, R2 | Source. Head TC `-S` phase and P2/P3 exercise SA copying in a debug build with no assert. | 4 |
| S6. A missing **middle** archive fails the backup cleanly and leaves no partial output. | R1, R2 | **Probe P3:** `backupdb -S` rc=1, `ER_IO_MOUNT_FAIL (-10)` naming `lgar002`, backup dir empty, no core. | 5 |
| S7. A missing **leading** archive is skipped and the backup succeeds, in both server and SA mode. | R2 | **Probes P2 (`-S`) and P2C (`-C`):** rc=0, copies 001.., server alive, restore lists all archives except 000. | 5 |
| S8. Compile variants: no new warnings. `log_page_buffer.c` is never built in CS. | R1, worker | `-Wunused*` rerun: SA 7 = base 7, SERVER 12 = base 12. cppcheck and clang-tidy bugprone report 0 new. | 4 |
| S9. HA is not affected. | R3 | The branch only runs when vacuum is disabled. The scan uses the node's own `log_Archive_path`/prefix, while copylogdb keeps its archives in `ha_copy_log_base`. No backup-header or record format change. | 3 |

Shared challenge Q1 (R1 sonnet, R2 opus, answered independently): *Can a disabled-vacuum backup under the patch omit an archive that recovery or re-enabled vacuum will read?* Both answered **no**, except for archives already absent from disk before the backup (operator deletion, or a DB restored from a pre-patch backup). The patch cannot recover those. It only makes the gap fail loudly when it is in the middle; a leading gap is skipped quietly (see N1).

## Confirmed findings

None.

## Non-blocking comments (recommendations, not defects)

- **N1 (engine, suggestion). A skipped leading gap is visible only in a debug log line.**
  - Location: `log_page_buffer.c` new hunk around L8790-8802, `_er_log_debug ("Backup skips log archives …")`.
  - P2 and P2C: rc=0. The message is written only to `<db>_backupdb.err` or the server `.err`. Nothing appears on the console or in the `-o` verbose report.
  - P2C: restoring that backup while vacuum is **enabled** during `restoredb` ends in FATAL, rc 254, `unable to find log page 1277` in `vacuum_recover_lost_block_data`.
  - A trap that makes this easy to hit: `restoredb` loads only `[common]` (`boot_sr.c:2874`), so a `vacuum_disable=yes` in `[@db]` is ignored.
  - With vacuum still disabled, the restore succeeds.
  - Precondition: the leading archive was already missing on the source. That is a damaged source, or the legitimate shape of a DB restored from an earlier backup that did not need those archives.
  - Suggestion: report the skipped range at a user-visible severity (e.g. `er_set (ER_NOTIFICATION_SEVERITY…)`), or add a line to the `-o` report. Failing the backup would be wrong, because the restored-DB shape is legitimate.
- **N2 (PR description).** The body says `logpb_backup_ensure_fresh_checkpoint` (CBRD-27071) raises `last_arv_num_for_syscrashes` before the backup.
  - That function is absent at both base and head. #8119 (`268a2ed4d3`, CBRD-27298) removed it, and that commit is in base but not in `f8bc815754`.
  - The root cause still holds through the last periodic checkpoint.
  - The body also calls `5d6b8cc8fb` "develop merge only", but that merge brought #8119's `logpb_backup` changes into the branch, and T1–T15 ran on `f8bc815754` before it.
  - This review re-ran the TC plus P1/P2/P2C/P3 at the head SHA, but not T1/T9/T14. I suggest correcting the text.
- **N3 (engine, minor).**
  - The comment "archives are not removed while vacuum is disabled" holds because of `vacuum_is_safe_to_remove_archives()`, not because `vacuum_min_log_pageid_to_keep()` returns 0. Consider naming the gate in the comment.
  - `vacuum_first_pageid` is unused in SA. This is pre-existing; it could move under `SERVER_MODE`.
  - `logpb_backup` cyclomatic complexity goes from 100 to 108 (lizard). The scan could be a small helper.
- **N4 (cost, documented by the author).**
  - Every backup taken while disabled, including level 1 and 2, copies every remaining archive. That set only grows while vacuum is disabled, and checkpoints are blocked during the transfer.
  - The forward scan does one stat per absent leading archive under LOG_CS and repeats on each backup. It is negligible on local disk and was not measured.
  - Acceptable for a hidden diagnostic parameter.
- **T1 (TC, coverage).** The `-C` phase does not catch the original `-C` defect on its own.
  - In the TC, archive 000 always exists, so pre-fix `-C` already copies every archive.
  - On base the C phase fails only as a cascade of the `-S` loss: the C-phase `before` is `003..006`, then FATAL page 0, an assert, and a core.
  - Suggested deterministic mode, with vacuum disabled and the server stopped: delete `lgar000` → `backupdb -C` → restore → compare the archive lists, and skip the vacuum-enabled step. Expected: debug base hits the assert and release base loses archives; head passes (as P2C showed at head).
- **T2 (TC, oracle strength).** `[S enabled]` passed on the debug base even though the restored DB had no archives.
  - The DB never ran with vacuum enabled while it accumulated log, so vacuum had nothing to read from the missing archives.
  - The real fail-before checks are `[S archives]` and the C-phase cascade.
  - The TC header ("vacuum then asks for a log page… server stops") claims more than this data shape shows. The header text should be adjusted.
- **T3 (TC, low flake risk).**
  - `before == after` requires exact set equality. A log wrap between the snapshot and the frozen set would give a false NOK. R3 estimates under 1% per run; a subset check is safer.
  - The FATAL check on the server error log passes silently if that log file is missing; a readability guard would close this.
  - Two head runs gave identical results and archive lists.

## Verification actually run

All runs used a `debug_gcc` build (Debug, `-O0`, asserts on) on the same host, through the native `cubrid-testkit` shell runner (`TESTKIT_CONTAIN=1`).

| Check | Revision | Result | Artifacts |
|---|---|---|---|
| `cubrid-static-check af6f1df42b… 5d6b8cc8fb…` | head | 0 new cppcheck, clang-tidy or CPD findings. Lizard: `logpb_backup` CCN 100→108 (exit 1 caused only by the lizard flag). | retained locally |
| Build and install (`just configure-build-and-install`) | head, base | rc 0 / rc 0. No warnings in `log_page_buffer.c`. | retained locally |
| `-Wunused*` syntax-only rerun of `log_page_buffer.c`, SA and SERVER | head vs base | Same warning sets (7/7, 12/12). | retained locally |
| TC `shell/_40_guava/cbrd_28142` ×2 | head + TC `82dbac26b0` | **PASS 7/7** both runs (100 s, 94 s). S archives `000 001 002` = source; C archives `000..006` = source. | retained locally |
| TC ×1 | base + TC `82dbac26b0` | **FAIL as expected:** NOK `[S archives]` (restored list empty); `backupdb -C` FATAL `unable to find log page 0`, `assert(false)` at `log_page_buffer.c:8805`, `cub_server` core. | retained locally |
| P1 removal gate: `vacuum_disable=yes log_max_archives=1 force_remove_log_archives=yes`, `backupdb -C -r` | head | PASS: none removed; restore = source (000–006). | retained locally |
| P2 leading gap, `-S` | head | rc 0; copies 001–006; skip only in `.err`. | retained locally |
| P2C leading gap, `-C` | head | rc 0; server alive; restore with vacuum disabled in `[common]` → OK (001–004). Restore with vacuum effectively enabled → FATAL rc 254 (N1). | retained locally |
| P3 middle gap, `-S` | head | rc 1, `ER_IO_MOUNT_FAIL` naming `lgar002`, no partial backup. | retained locally |

Not run:
- A release build.
- The original `-C` timing defect with vacuum disabled while it still has unvacuumed blocks (the author's T1).
- Incremental `-l 1/2` while disabled (the author's T5/T14).
- `restoredb -d`.
- A DB with `last_deleted_arv_num > -1` from a real removal while vacuum was enabled.
- An HA pair.

These are covered by source reasoning (R2: incremental restore takes archives from the highest level only, and each disabled-level backup is complete) and by the author's pre-merge runs.

## Pre-existing issues (not attributed to this PR; unverified unless stated)

- **PE-1 (R2, L3).** In the enabled branch, `vacuum_min_log_pageid_to_keep` is read (8814) after `logpb_flush_pages_direct` (8759). The vacuum master can advance keep between the two, so the backup can leave out the archive holding the block that the restored vacuum data still references. The window is milliseconds. Fix direction: read keep before the flush.
- **PE-2 (R2, L2).** `logpb_remove_archive_logs_exceed_limit` removes archives based on the in-memory keep, without first making sure the vacuum-data record that advanced it is flushed.
- **PE-3 (R2, L2).** The SA boot ignores the return value of `xvacuum` (`boot_sr.c` ~2676).
- **PE-4.** The out-of-scope items the PR lists are confirmed in source: the debug assert in `vacuum_rv_redo_start_job` (`vacuum.c:6197`, `page_data_max_count == 0` when disabled) and T14r's −1179.
- **PE-5 (worker).** `restoredb` loads only `[common]` parameters (`boot_sr.c:2874`) and ignores `[@db]`.

## Coverage

| Area | Owner | Result |
|---|---|---|
| Declaration and `#if` moves, error paths, boundaries, compile variants | R1 (sonnet) | clean |
| Disabled-vacuum branch, archive-removal gate, LOG_CS concurrency, SA semantics, restore and incremental levels | R2 (opus), R1 | holds; N1 visibility |
| HA | R3 (sonnet) | not applicable (source) |
| TC fail-before / pass-after / flakiness | R3 + test worker | `-S` verified; T1–T3 |

All changed hunks have an owner and a terminal result. HA was judged not applicable from source.

## Budget

- Mode: bounded (default). No hard cap was enforced.
- Agents: 3 reviewer subagents (R1 sonnet ~274k tokens / 14 min; R2 opus ~210k / 12 min; R3 sonnet ~336k / 19 min), plus 1 Herdr worker tab (Claude) for builds, the TC and the probes (~30 min wall).
- No retries. Coordinator usage was not measured.
- Every target was met by wall time. Token totals are reported by the harness and cannot be attributed against an allowance.

## Evidence retention

Raw build logs, TC run directories, probe scripts and server error logs are retained in the reviewer's local run directory. The testcase lives in a private repository, so this report describes its behaviour without reproducing its source.
