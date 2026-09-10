# CBRD-26939 diagnosis — 2940b1c

Work tracker: 70. Investigation in progress; no engine changes or architecture decision yet.

## Verified identities

- PR https://github.com/CUBRID/cubrid/pull/6864 HEAD 2940b1cfbc3c2d4d0fac3f9244a960350debd380 matches worktree.
- GHA https://github.com/CUBRID/cubrid/actions/runs/34186373809 collect job 101943866056 verifies that engine across 50 shards, testcase 01af62db73351ea3fdb445ccd03a19c39084d1cc.
- Workflow headSha 69c3094 is the workflow revision, not the tested engine identity.
- Latest failures: cbrd_27064 and bug_bts_4633. Older expected CDC pair must not be substituted.
- Existing source worktree has user-owned submodule differences and untracked files; preserved.

## Latest observed CI symptoms

- cbrd_27064: INSERT passes; DELETE 16/700, UPDATE 3/2400, rc=-10, corruption count zero.
- bug_bts_4633: JDBC concurrency on integer-only tables. Script reports OK, but runner detects cub_server core in log_get_undo_record through heap_get_visible_version_from_log, heap scan and query execution. No CDC frames in the captured stack.
- Raw shard31 XML and extracted failure text are adjacent to this file.

## Current local reproduction

Private install /home/vimkim/.cache/codex/cbrd-26939-2940b1c/install copied from /home/vimkim/.cub/install/oos-storage/debug_gcc, cubrid_rel 11.5.0.2634-2940b1c.
Runner: bash /home/vimkim/.cache/codex/cbrd-26939-2940b1c/enter.sh run
Isolation: user/mount/PID/IPC/network namespaces, fresh /tmp hides host Unix sockets, loopback hosts resolution, port 1600. Private CTP copy prevents shared config mutations. Preflight starts/stops only private master/broker.
Original testcase copied with loopback hostname and retained cleanup artifacts. No workload/answer changes.
Initial local DELETE red: 0/700, rc=-10, corruption zero. Full UPDATE run ongoing at last write. Next: preserve full results, narrow DELETE-only loop, minimize and repeat before hypotheses or engine probes.

## JIRA context

Fresh cubrid-jira search CBRD-26939: Open, Unresolved, updated 2026-08-14. It names both older CDC failures and proposes durable supplemental payload vs retention vs hybrid; decision remains TBD. Its original evidence is commit 725a32c and has no local reproduction. Normative OOS context last updated 2026-08-28 retains physical undo stubs; do not expand ordinary recovery undo as a CDC fix.

## Feedback-loop progress (2026-09-08)

Full original run exited 1, INSERT passed, DELETE failed at 0/700 with rc=-10. UPDATE result was contaminated by server failure; not an independent reproduction. Two core files were observed and a symbolized DELETE stack was saved before CTP cleanup removed the cores. The DELETE core backtrace identifies pgbuf_fix_debug(OLD_PAGE) -> oos_read_within_page -> oos_read -> heap_attrinfo_read_dbvalues -> cdc_make_dml_loginfo(CDC_DELETE).

Independent DELETE-only run: 56/700, rc=-10. Single payload size: 18/700, rc=-10. Reduced to 50 rows: 11/50, rc=-10. Smaller 1, 10, 25, 40-row runs passed. Corruption count stays zero. Minimization/repeatability still in progress; no ranked hypotheses tested yet.
