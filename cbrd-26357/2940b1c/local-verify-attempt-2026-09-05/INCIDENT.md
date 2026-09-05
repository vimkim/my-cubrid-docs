# Incident: local CTP verification stopped the host's pgbuf-analysis master (2026-09-05)

- **Context**: verifying the six testcase edits for PR #6864 at `2940b1c` (groups A–C of
  `ci_analysis_report_2940b1c_claude.md`) with CTP on this workstation, inside a Linux namespace, against a copy of the
  `oos-storage/debug_gcc` install re-pointed to port 1600.
- **Author**: Claude (Fable 5.1), same session as the CI analysis. Files in this directory: `iso_driver.sh` (the
  driver as run), `isorun.log` (driver output), `ctp_<test>.log.gz` (CTP stdout per test),
  `test_local_bigPageSize_partial.log` (CTP runtime trace of the test that was running when the run was killed).

## What happened

| Time (KST) | Event |
|---|---|
| ~16:40 | Preflight in `unshare -ripf --mount-proc`: bind-mounted the install copy on `/mnt`, bound a scratch dir over `~/.CUBRID_SHELL_FM`, `cubrid service start/stop` on port 1600 worked; host master on 1523 untouched. |
| 16:45:14 | Driver started CTP for `file_enc_03` (first of five tests). |
| 16:45:16 | Host `cub_master` (pid 1581248, `pgbuf-analysis/debug_gcc`, port 1523, up 4 days) logged "Monitoring finished"; its `quizdb` server (pid 1588023) shut down. |
| 16:45–16:48 | `file_enc_03`, `file_enc_05`, `bug_bts_14120`, `bug_bts_9836` each reported NOK; `bigPageSize` started 16:48:02. |
| ~16:47 | `pkill -f iso_driver.sh` was sent. It killed the calling shell and the `unshare` parent, but the driver bash was PID 1 of the namespace and ignores SIGTERM, so CTP kept running. |
| ~16:50 | `kill -9` on the namespace init stopped everything. |
| 16:52 | `cubrid server start quizdb` from the pgbuf-analysis install brought master and quizdb back (pids 1767207, 1767240). |

## Root cause

Two independent gaps, both required for the escape:

1. **No network namespace.** `cubrid service stop` / `cubrid master stop` are TCP requests to `localhost:<cubrid_port_id>`.
   The PID namespace made `pkill cub` harmless and the IPC namespace isolated broker shared memory, but TCP still
   reached the host, so anything that resolved to port 1523 hit the host's master.
2. **CTP replaced the install copy's conf with nothing.** CTP shell runs, per test, `resetCUBRID_linux`
   (`Test.java:426`): `rm -rf ${CUBRID}/conf/*` then `cp -rf ~/.CUBRID_SHELL_FM/conf/* ${CUBRID}/conf/`. Earlier, its
   DEPLOY step (`DeployOneNode.java:280`) ran `rm -rf ~/.CUBRID_SHELL_FM; cp -r ${CUBRID} ~/.CUBRID_SHELL_FM`. Because
   `~/.CUBRID_SHELL_FM` was a bind mount in the namespace, `rm -rf` emptied it but could not remove the directory, so
   `cp -r /mnt ~/.CUBRID_SHELL_FM` created `~/.CUBRID_SHELL_FM/mnt/…` instead of `~/.CUBRID_SHELL_FM/conf/…`. The
   per-test restore then found no `conf/`, leaving `/mnt/conf` **empty** (confirmed: the copy's `conf/` had 0 files
   afterwards). With no `cubrid.conf`, the binaries used built-in defaults, and the default `cubrid_port_id` is
   **1523**. The testcase's `init` then executed `cubrid service stop`, which stopped the host master.

The CI analysis itself is unaffected; it never depended on local execution.

## Damage and repair

- Stopped: pgbuf-analysis `cub_master` and `quizdb` (graceful shutdown; volume files intact; `quizdb` volume last
  written 16:41, before the incident). Restarted at 16:52 with a plain `cubrid server start quizdb`. If the previous
  instance had been started by `run-monitor.sh` with `CUBRID_PGBUF_TRACE_VPID=all`, that environment is **not** set
  on the restarted server; `trace-all.log` was last modified 2026-09-01, so no trace appears to have been active.
- Not damaged: the real `oos-storage/debug_gcc` install (conf mtimes unchanged, log dir intact), the host
  `~/.CUBRID_SHELL_FM` snapshot (14 conf files, port 1523, protected by the bind mount), the private-ex clone's
  checked-out branch, other users' CUBRID processes (different uids, unreachable).
- Cleaned: the install copy and the snapshot scratch dir were deleted; run byproducts in the five testcase
  directories of the `tc/pr-6864` worktree were removed with `git clean -fdx` scoped to those directories, leaving
  only the six intended edits.

## Test results from the run are invalid

All four completed tests reported NOK **while the install had no `cubrid.conf`**, so they say nothing about the
answer fixes. Verification of groups A–C is still outstanding.

## Corrected procedure for the next attempt

Do not run CTP shell on this host without all of the following:

1. `unshare -r --mount-proc -i -p -f -n` (add the **network** namespace) and `ip link set lo up` inside, so port 1523
   inside is not the host's 1523. With `-n` the port re-pointing to 1600 becomes unnecessary but harmless.
2. Give CTP a `~/.CUBRID_SHELL_FM` it can **delete and recreate**: bind a scratch directory over `$HOME` (or over the
   parent) rather than over `~/.CUBRID_SHELL_FM` itself, or pre-create a scratch `HOME` and run CTP with
   `HOME=<scratch>` and absolute `CTP_HOME`. Verify after the first test that `${CUBRID}/conf/cubrid.conf` still exists.
3. Keep `cubrid_port_id` and broker ports in the copy's conf **and** in the CTP conf `default.*` keys consistent.
4. Kill the namespace with `kill -9` on its init PID, not `pkill -f`; namespace init ignores SIGTERM.
5. Before launching, confirm no user-owned `cub_master` is listening on the port the copy will use, and re-check the
   host masters after the first test completes.

Alternatively verify on a host or VM with no other CUBRID instance. `just ctp podman-test-new` is not a drop-in
option: it mounts the install read-only (testcases call `change_db_parameter`) and does not provide CTP's `init.sh`.
