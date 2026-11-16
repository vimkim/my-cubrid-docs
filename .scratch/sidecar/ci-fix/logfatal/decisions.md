# Decisions: test_sql shard 09 LOG FATAL (PR 8504, run 43404071059)

Goal: classify the shard 09 `LOG FATAL ERROR: log_fetch_from_archive` as a Sidecar defect, a local develop-fix
defect, a pre-existing develop defect, or CI flakiness, and find the root cause if it is a code defect.

Labels: 측정 (measured), 추론 (inferred), 추측 (guess).

## Evidence gathering

- 측정: run 43404071059 has no artifacts (`gh api .../runs/43404071059/artifacts` total_count=0). The server error
  logs `basic_20261113_1916.err` and `basic_20261113_1927.err` are not available.
- 측정: the full shard 09 job log (job 131816417371) downloaded to `job-131816417371.log` (246077 lines). Case order
  in `shard09-order.tsv` (435 cases seen; 1..398 OK, 399 FATAL, 400.. connect failures).
- 측정: CI conf for sql = CTP `conf/sql.conf` with `ha_mode=yes`, `java_stored_procedure=yes`, `test_mode=yes`,
  `lock_timeout=10sec`; the database is created with default sizes (`cubrid createdb basic en_US.utf8`). Build is
  `optdebug` (`cubridci/cubridci:develop|-m optdebug`).
- 측정: the installed `conf/cubrid.conf` of this source tree sets `log_max_archives=0` and `log_volume_size=512M`.
  CTP edits that file, so CI ran with `log_max_archives=0` (추론: the CI image installs the same conf).
- 측정: `sidecar_force_external` defaults to yes at f69816c086 (CI commit d3403c0533).
- 측정 (code): `logpb_fetch_from_archive` prints `Unable to mount ... basic_lgar000` only when
  `log_Gl.hdr.nxarv_num > 0`; with no archive ever made it sets ER_LOG_NOTIN_ARCHIVE instead. 추론: at the FATAL the
  log had made at least one archive and archive 000 had been deleted.

## Local reproduction setup

- Tools: `tools/mkattempt.sh` builds `~/tk/<name>` (copied install + CTP + the selected shard 09 cases at TC
  40cdeddd1d, native `prepare-config`); `tools/runattempt.sh` runs native testkit sql under containment and verifies.
- Deviation: the debug install `~/.cub/install/sidecar-poc1/debug_gcc` (11.5.0.2962-f69816c, Nov 13 14:37) has no
  JDBC jar. Reinstalling could disturb another session's running `testdb` server, so each attempt copy gets
  `cubrid-jdbc-11.4.0.0088.jar` from another local install. The worktree `.env` selects release_gcc; the runner loads
  the debug_gcc environment through `cub-workenv env` without editing `.env`.
- 측정: the prefix attempt's expected list equals CI's shard 09 order for cases 1..399 (`diff` empty).

## Attempts

| Attempt | Head | Build | Cases | Result |
|---|---|---|---|---|
| lf1 | f69816c086 | debug | 399 only | OK 1/1, no FATAL |
| lf2 | f69816c086 | debug | 1..399 (CI order) | OK 399/399, no FATAL. Server logs lost (see below) |
| lf3 | f69816c086 | debug | 1..399, CI log size (512M), server log kept | no FATAL; 398 OK, 1 NOK (case 122, cub_cas crash with empty core, unrelated); 5 archives, 8 checkpoints, redo never lowered |
| lf4 | f69816c086 | debug | 1..399, 20M log volume | no FATAL; 4 NOK (case 122 cub_cas crash, others not examined); 138 archives, 8 checkpoints, redo never lowered |
| pb1 / pb2 | f69816c086 / 173d92e454 | debug | one SQL probe (CBRD-28058 workload, checkpoint_interval=1min) | no FATAL on either; 추론: the automatic checkpoints ran during the 300 DROPs and emptied the interval table, so the probe did not set up the trigger |

- 측정: testkit containment writes `$CUBRID` through a per-slot overlay and removes the slot root after the run
  (`cubrid-testkit internal/contain/slots.go` closeAll). The `basic` server error logs of lf1 and lf2 are gone, so
  whether lf2's log wrapped is unknown. A LOG FATAL exits without a core (`logpb_fatal_error_internal`), so the
  stack exists only in the error log. From lf3 on, `[sql/cubrid.conf]` gets `error_log=<attempt>/srvlog/cubrid.err`
  and `call_stack_dump_on_error=yes` (diagnostic only).
- Deviation: the runner's preflight against the registered install fails (lf3/lf4: `CUBRID is not set`, because
  `PRESET_MODE` was not exported; earlier: jar missing). The run itself uses the explicit attempt environment.
  Fixed for later attempts by exporting `PRESET_MODE`; the jar check still fails against the registered install.

## Prior occurrences (측정, cubrid-ci evidence on this host)

The same FATAL (`LOG FATAL ERROR: log_fetch_from_archive`, then restart `Unable to mount ... basic_lgar000`) is in
CI logs of heads that carry no Sidecar code:

| Head | Run, suite, shard | Last case started |
|---|---|---|
| develop 2d1513a8af | 43047833612 test_sql_by_cci 09 | `_36_guava/cbrd_27469` (from CBRD-28058 comment) |
| PR 8299 855f220d53 | 42801815682 test_sql 03 | `_13_issues/_26_2h/cbrd_27732_merge.sql` (2178/2881) |
| PR 8416 89496263eb | 42865557030 test_sql 03 and 09 | `cbrd_27732_merge.sql`; `_36_guava/cbrd_27478.sql` (411/524) |
| PR 8495 77281a4582 | 43297344774 test_sql 03 | `cbrd_27732_merge.sql` (2180/2891) |
| PR 8495 6a7ca6b4a8 | 43163141709 test_sql_by_cci 09 | `cbrd_27482_coalesce.sql` |
| PR 8510 2e04e056af | 43188099115 test_sql_by_cci 09 | (shard 09) |
| PR 8504 84e24e39f4 | 43184757385 test_sql_by_cci 09 | (shard 09); the "passing" previous head of this PR |

- 측정: JIRA CBRD-28058 (status Develop, assignee another engineer) describes this FATAL: after CBRD-27151
  (063d84e53) a DROP/TRUNCATE discards dirty pages and records their log range in a 256-slot table; when the table
  is full, `pgbuf_discard_interval_open` merges new destroys into the most recent slot, the merged slot never closes,
  and `pgbuf_discard_redo_bound_apply` lowers a checkpoint's redo LSA into an archive already removed
  (`log_max_archives=0`). Stack from a colleague's local CTP shard 09 run on develop 98b892cf4 (ha_mode=yes):
  `logpb_fetch_from_archive <- logpb_checkpoint <- checkpoint daemon`; restart:
  `... logpb_fetch_page <- log_recovery_redo <- log_recovery`.
- 측정: 063d84e53 is an ancestor of both f69816c086 and the develop merge base 173d92e454. No commit in
  `173d92e454..origin/develop` touches page_buffer.c or log_page_buffer.c (fetched 2026-11-16). The branch's own
  changes to these files (d514d5ea18, Sidecar P1c page-fix work) do not touch the discard-interval code.

## CBRD-28058 reproduction (tools/issue-repro.sh)

The issue's procedure on a private copy of each install: own databases, `CUBRID_TMP` and cub_master port,
`ha_mode=no`, `log_max_archives=0`, `checkpoint_every_size=10G`, `checkpoint_interval=3600s`, 20M log volume,
checkpoints only by `;checkpoint`. `redo_lowered` means a checkpoint's redo page is below the previous one's
(from the `Checkpoint finished` lines).

| Attempt | Head | Variant | FATAL | redo lowered |
|---|---|---|---|---|
| ir1 | f69816c086 | issue as written (3 final checkpoints) | 0 | 2396 -> 1525 |
| ir2 | 173d92e454 | issue as written | 0 | no |
| ir3, ir4, ir5, ir6 | f69816c086 | 8 final checkpoints | 0 | no |
| ir7 | 173d92e454 | 8 final checkpoints | 0 | 2396 -> 1525 |
| ir8, ir9, ir10 | 173d92e454 | 8 final checkpoints | 0 | no |
| ir4 | f69816c086 | 8 final checkpoints | inconclusive: the main script vanished after 8 checkpoints, its DROP loop kept running; stopped by PID and `cubrid server stop` | no |
| ir11, ir12 | f69816c086 | 8 final checkpoints, FULL_UPDATE | 0 | no |
| ir13, ir14 | f69816c086 | 8 final checkpoints, FULL_UPDATE | 1 each: `unable to find log page 1525`, restart fails | (FATAL at the lowering checkpoint) |
| ir15..ir18 | 173d92e454 | 8 final checkpoints, FULL_UPDATE | 0 | no |
| ir19..ir21, ir23..ir26 | 173d92e454 | 8 final checkpoints, FULL_UPDATE | 0 | no |
| ir22 | 173d92e454 | 8 final checkpoints, FULL_UPDATE | 1: `unable to find log page 1525`, restart fails | (FATAL at the lowering checkpoint) |
| ir27 | f69816c086 | 8 final checkpoints, FULL_UPDATE | 0 | 2395 -> 1525 |
| ir28..ir30 | f69816c086 | 8 final checkpoints, FULL_UPDATE | 0 | no |

- 측정: in ir1 and ir7 the third checkpoint lowered redo from 2396 to 1525, the same page CBRD-28058 reports
  (`unable to find log page 1525`). Page 1525 was in `lfdb_lgar001` (pages 1278..2555), which the server had kept
  (only `lgar000` was removed), so the checkpoint read it and no FATAL followed.
- 측정: the lowering happens on the develop merge base without any Sidecar commit (ir7). Rate of the lowering: head
  1/5, base 1/5. Rate of the FATAL: 0/5 and 0/5.
- 추론: the FATAL needs one more condition: the archive that holds the lowered redo page must be removed before the
  lowering checkpoint. That needs an intermediate checkpoint that keeps the merged interval (last >= previous redo)
  without lowering (last < its redo), and then enough log to make the next archive.

## Result

- 측정 (FATAL rate, all variants): f69816c086 2/12 (+1 inconclusive), 173d92e454 1/17. FULL_UPDATE variant only:
  2/8 vs 1/12. 추론: the difference is not significant at these counts (Fisher exact, two-sided, about 0.5), and
  the base without any Sidecar commit and without the local develop fixes d514d5ea18 and 7c5028d5bd reproduces it.
- 측정 (stack, ir13 head and ir22 base, `evidence/*-checkpoint-fatal-stack.txt`): `logpb_fetch_from_archive` <-
  `logpb_checkpoint` (log_page_buffer.c:7781 head, :7775 base) <- `log_checkpoint_execute` (checkpoint daemon). The
  page is 1525, the start of the merged discard interval of the 300 DROPs; archive `lgar001` (1278..2555) was gone.
- 측정 (restart, `evidence/*-restart-fatal-stack.txt`): `fileio_mount` fails on `lgar001`, then
  `logpb_fetch_from_archive` <- `logpb_read_page_from_file` <- `logpb_fetch_page` <- `log_recovery_redo`
  (log_recovery.c:3491) <- `log_recovery` (:883) <- `log_initialize_internal` <- `boot_restart_server`. Same as CI's
  repeated restart failure.
- 측정 (trigger, `evidence/ckpt2-vs-fatal.txt`): all three FATAL runs had their step-3 checkpoint finish after
  `lgar001` was made (redo 3166..3168). That checkpoint released `lgar001` for removal; the next archive removed it;
  the next checkpoint lowered redo to 1525. Runs whose step-3 checkpoint ran before `lgar001` existed (redo
  2395..2397) either did not lower or lowered into a present archive (ir1, ir7, ir27).
- 추론 (code, f69816c086): `pgbuf_discard_redo_bound_apply` (page_buffer.c:3887) lowers `tmp_chkpt.redo_lsa` at
  log_page_buffer.c:7488. The END_CHKPT record with that redo is appended (:7634), flushed (:7671) and the header
  flushed (:7705) before the archive check at :7780 calls `logpb_fetch_from_archive (..., is_fatal=true)`. So the
  lowered redo is durable when the server dies, and every restart redoes from page 1525.
- 측정 (CI-like runs): lf2..lf4 on f69816c086, 0/3. The CI-sized run lf3 did wrap the 512M log (5 archives), which
  matches CI's `nxarv_num > 0`, but no checkpoint lowered redo there.
- Classification: pre-existing develop defect CBRD-28058 (regression of CBRD-27151, 063d84e53). Not a Sidecar
  defect, not caused by the branch's local develop fixes. In CI it shows as an intermittent shard loss.
- A/B with 84e24e39f4: skipped. 측정: its own CI run 43184757385 already shows the same FATAL in test_sql_by_cci
  shard 09, so its "pass" on test_sql shard 09 was timing, and a build would add nothing.
- Fix: none. CBRD-28058 is assigned to another engineer and in Develop. A local fix here would duplicate that work
  and is not needed to classify the failure. The reproduction script `tools/issue-repro.sh` (FULL_UPDATE=1
  N_CKPT=8) is the check a fix should pass; at about 1 in 6 to 1 in 12 runs it needs many repeats.
- Side finding (측정, not analysed): lf3 and lf4 case 122 `_33_elderberry/cbrd_24141/cases/column_name_serial_03.sql`
  NOK with a cub_cas crash whose core file was empty. CI shard 09 passed this case. Out of scope here.
