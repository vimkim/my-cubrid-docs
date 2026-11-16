# Decisions: cub_cas crash on column_name_serial_03.sql in local shard 09 runs (PR 8504, f69816c086)

Goal: classify the cub_cas crash on `sql/_33_elderberry/cbrd_24141/cases/column_name_serial_03.sql` (shard 09 case
122, seen in lf3 and lf4 of the LOG FATAL work) as a Sidecar defect, a develop defect, or a local setup artifact, and
find its root cause if it is a code defect.

Labels: 측정 (measured), 추론 (inferred), 추측 (guess).

## Setup

- Tools: `tools/mkattempt.sh` and `tools/runattempt.sh` copied from `../logfatal/tools`. Changes: broker SQL and
  error logs go to `<attempt>/srvlog/broker` (outside the testkit overlay, so they survive the run);
  `NO_STACKDUMP=1` leaves `call_stack_dump_on_error` at its default (no). `tools/one.sh` runs one attempt with
  `tools/caswatch.sh`, which attaches gdb to each cub_cas of the attempt and, on a fatal signal, runs
  `tools/atcrash.gdb` (registers, the `css_receive_data` locals, the connection's `buffer_queue` and `data_queue`,
  the stack words). `GDB_PRE` adds breakpoints before the run continues.
- Cores: `core_pattern` pipes to systemd-coredump, which fails on these process names. The "empty core file" of lf3
  and lf4 is not a kernel core. It is `$CUBRID/log/coredump/<proc>_<time>.coredump`, which `cas_sig_handler` writes
  through `er_print_crash_callstack`; testkit reported it empty (측정, run.log: `it is empty`). gdb in the watcher
  replaces it. gdb needs `set sysroot /` because testkit runs the CAS in its own namespaces.
- JDBC jar (측정, `evidence/jdbc-jar.txt`): the jar the tools copy, `cubrid-jdbc-11.4.0.0088.jar`, has the same sha1
  as the jar built in worktree `build-partition-key-20261112`, whose `cubrid-jdbc` submodule is checked out at
  c3933fc. f69816c086 and 173d92e454 both pin c3933fc. So the driver matches the install. Step 2 of the brief
  (try a matching jar) is already met by the current setup; there is no other jar to try.
- `sidecar_force_external`: the debug install's conf does not set it, and its default is yes (system_parameter.c),
  the same as CI (측정).
- `call_stack_dump_on_error=yes` is a deviation from CI. The LOG FATAL work added it from lf3 on (diagnostic only);
  CTP's `conf/sql.conf` does not set it (측정). lf1 and lf2 ran without it.
- Base: detached worktree `/home/vimkim/gh/cb/sidecar-cascrash-base` at 173d92e454, debug_gcc install
  `~/.cub/install/sidecar-cascrash-base/debug_gcc`.

## Attempts

All on debug_gcc, shard 09 order at TC 40cdeddd1d. "watch" means the crash watcher only (no breakpoints, the CAS
runs at full speed). "rare bp" adds breakpoints on rare client paths (ping error, unexpected data, queue cleanup);
the cleanup breakpoint fires on every commit and slows the CAS. "force" uses `tools/force-ping-timeout.gdb`: the
first ping with request id 6840 returns the poll-timeout error without reading; it also puts a conditional
breakpoint on every receive, which slows the CAS more.

| Attempt | Head | Cases | Stack dump | gdb | Result |
|---|---|---|---|---|---|
| cc1 | f69816c086 | 122 | yes | none | OK 1/1 |
| cc2 | f69816c086 | 1..122 | yes | watch (no symbols) | case 122 NOK, cub_cas SIGSEGV at pc 0x7fa102000000 |
| cc3 | f69816c086 | 120..122 | yes | watch | OK 3/3 |
| cc4 | f69816c086 | 1..122 | yes | watch | case 122 NOK, SIGSEGV, rid 6840 |
| cc5 | f69816c086 | 1..122 | yes | watch + atcrash | case 122 NOK, SIGSEGV, rid 6840, stale buffer in hand |
| cc6 | f69816c086 | 1..122 | yes | bp on every queue/take of rid 6840 | OK 122/122; first-lap rid 6840 is the case 18 ping; no second lap |
| cc7 | f69816c086 | 1..122 | no | rare bp | OK 122/122, no ping timeout |
| cc8 | 173d92e454 | 1..122 | yes | rare bp | OK 122/122, no ping timeout (stall hit a `create table`) |
| cc9 | f69816c086, `sidecar_force_external=no` | 1..122 | yes | rare bp | OK 122/122, ping timeout at rid 6841 |
| cc10 | f69816c086 | 1..122 | no | rare bp | OK 122/122, no ping timeout |
| cc11 | 173d92e454 | 1..122 | yes | rare bp | OK 122/122, ping timeout at rid 6841 |
| cc12 | 173d92e454 | 1..122 | no | rare bp | OK 122/122, no ping timeout |
| cc13 | 173d92e454 | 1..122 | no | force (1 ms timeout) | OK; forcing failed: the reply came within 1 ms |
| cc14 | f69816c086 | 1..122 | no | force (return) | OK; ping 6840 timed out by force, late reply queued as unexpected data; no second lap |
| cc15 | 173d92e454 | 1..122 | no | force (return) | same as cc14 |
| cc16 | 173d92e454 | 1..122 | yes | watch | OK 122/122, no ping timeout (stall hit a `create table`) |
| cc17 | 173d92e454 | 1..122 | yes | watch | OK 122/122, no ping timeout (stall hit a `create table`) |
| cc18 | 173d92e454 | 1..160 | no | force (return) | same as cc14; no second lap even at 160 cases |
| cc19 | f69816c086 | 1..399, 20M log (the lf4 setup) | yes | watch | 395 OK, 4 NOK: 122 (`Error:-187`), 206 (CAS abort in `free`), 208 and 211 (leftover `TEST_USER2` from 206) |
| cc20 | 173d92e454 | 1..122 | no | force ping #43 only | ping #43 is rid 6840 at statement 319; CAS aborts in `free` at case 122; testkit verdict OK |
| cc21 | f69816c086 | 1..122 | no | force ping #43 only | same as cc20 |

"force ping #43 only" is `tools/force-ping-43.gdb`: a breakpoint on `net_client_ping_server` alone (about 500 hits
per run), and only the 43rd call returns the poll-timeout error. The 43rd `check_cas` is the one that timed out
naturally in cc4 and cc5 (42 `check_cas` lines precede `SERVER DOWN`). The per-receive breakpoints of cc6 and
cc13..cc18 slowed the CAS so much that its request ids did not wrap before the last case, so those runs could not
show the second lap.

## Mechanism

1. 측정 (cc4, cc5, `evidence/cc4-cc5-crash-state.txt`): the CAS dies in `tran_server_commit` ->
   `net_client_request` -> `css_receive_data_from_server` -> `connection_cl::css_receive_data` with request id
   6840. `css_receive_data` took `buf` = a stack address 8 bytes below its own `rsp` with size 4 from
   `css_get_data_buffer` (the user buffer queue). `css_net_recv (conn, buf, ...)` then wrote the 4-byte reply over
   its own return address, and the return jumped to 0x7f..02000000 (the low 4 bytes are the reply). At the crash
   the queue still held the commit's own 8-byte reply buffer, so the buffer it took was an older entry with the same
   key 6840. Both crashes had request id 6840 and the stale address at `process_request` rbp - 0x3f8.
2. 측정 (cc6, `evidence/cc6-rid6840-ping.txt`): the first request with id 6840 is the `check_cas` ping of case 18
   (`fn_check_cas` -> `ux_check_connection` -> `db_ping_server` -> `net_client_ping_server`), which queues its
   4-byte stack `reply_buf`. 추론 (frame arithmetic): that `reply_buf` sits at `process_request` rbp - 0x3f8, the
   same slot as the stale buffer of cc4 and cc5.
3. 측정 (cc5, `evidence/cc5-ping-timeout.txt`): that ping, sent at 20:45:32.742, failed at 20:45:38.355 with -186
   (`ER_NET_SERVER_DATA_RECEIVE`) after its 5000 ms timeout; the CAS logged `SERVER DOWN`. With statement pooling on,
   `ux_check_connection` keeps the connection. The server log is silent from 20:45:32.738 to 20:45:39.646: a vacuum
   worker logged notification -1127 (`Delete an empty overflow page`, `i__db_domain_data_type`) and, with
   `call_stack_dump_on_error=yes`, dumped its call stack. The delayed ping reached `server_ping` at 39.646.
   추론: the debug server's stack dump holds the error-log path for about 7 to 11 s, and request handlers that log
   (`server_ping` logs first) wait behind it.
4. 측정 (code, f69816c086 and 173d92e454 identical): `net_client_ping_server` (network_cl.c:3439) returns on a
   receive error without removing its `reply_buf` from `conn->buffer_queue`. The cleanup paths do not remove it
   either: `css_remove_all_unexpected_packets`, which every `tran_server_commit` calls through
   `net_cleanup_client_queues` (측정, cc8 bt in `evidence/commit-clears-queues.txt`), clears the data, request,
   abort and error queues and leaves `buffer_queue` ("DO NOT REMOVE THE DATA BUFFERS QUEUED BY THE USER"). When
   `css_receive_data` reads a reply for another request id, it asks `css_return_data_buffer (conn, 0, ...)`, so a
   late ping reply gets a malloc'd buffer, not the stale one. In the forced runs the late reply landed in
   `data_queue` that way (측정, cc14 and cc15) and the next commit dropped it. In the natural timeouts of cc9 and
   cc11 the breakpoint on that path did not fire, so where their late reply went is not established (open). In cc4
   and cc5 the stale entry was still queued at the wrap (측정, step 1). `css_is_valid_request_id` checks the
   data, request, abort and error queues but not `buffer_queue`, so when the 16-bit request id wraps, 6840 is handed out again. `css_get_data_buffer` returns the first entry with the key,
   which is the dead ping buffer. The connect path (`connection_cl.cpp` `error_receive_data`) and the CDC client
   (`cubrid_log.c`, `css_queue_find_and_remove_header_entry_ptr`) do remove their buffer on a receive error; the
   ping path does not.
5. 추론: which request reuses the id decides the damage. In cc4 and cc5 it was a commit whose `css_net_recv`
   return slot is exactly `process_request` rbp - 0x3f8 in the debug (-O0) build, so the CAS died. With another
   request at that id (cc9 and cc11 timed out at 6841) the 4-byte write lands elsewhere in the stack with no
   visible effect within the run.

## Why head crashed and base did not in these runs

- 측정 (`tools/race.py`, `evidence/race.txt`): the -1127 stall starts at about the same point of case 18 on both
  heads. On f69816c086 (cc4, cc5, cc9) the CAS was 7 to 29 ms past statement 317..319 and about to send the
  `check_cas` ping, so the ping waited out its timeout. On 173d92e454 the stall hit statement 324
  (`create table t3`, no timeout) in cc8 and cc16, and statement 318 in cc11, which then timed out like the head.
- 추론: it is a race between an asynchronous vacuum notification and the CAS's ping. The head reaches the
  window a few statements earlier, which makes the ping lose more often in these runs. The defect itself is the same
  develop code on both heads, and the base also timed out (cc11).
- Natural ping-timeout rate with the stack dump on and the CAS at full speed: f69816c086 3/3 (cc4, cc5, cc19; cc2
  crashed the same way but ran before the broker logs were kept), 173d92e454 0/2 (cc16, cc17). With the slower
  rare-breakpoint gdb: f69816c086 1/1 (cc9), 173d92e454 1/2 (cc8, cc11). Every run whose statement-319 ping timed
  out at full speed failed at case 122: 6/6 (cc2, cc4, cc5, cc19 natural; cc20, cc21 forced). The request id 6840
  is measured in cc4, cc5, cc20 and cc21.
- 측정 (cc20, cc21, `evidence/cc20-base-forced.txt`): with the stack dump off and only the 43rd ping forced to time
  out, both heads fail the same way. Ping #43 got rid 6840 at statement 319 on both, and both CASes aborted at case
  122 in `free` called from `net_client_request_internal` (network_cl.c:544, `COMPARE_AND_FREE_BUFFER (replybuf,
  reply)` on the receive-error path) under `tran_server_abort`: the reply pointer it frees is the stale stack
  buffer. So the base has the same defect, and the crash follows from the timeout alone, with no Sidecar code and no
  diagnostic setting.
- 측정 (cc19, `evidence/cc19-lf4-rerun.txt`): the lf4 setup gives the same 4 NOK count as lf4. Case 122 got
  `-187 Communications buffer not used` (network_cl.c:549): the reply came into the stale buffer instead of the
  request's own `replybuf`, which then stayed queued under the same id as a new stale entry. 추론: the next wrap
  reached it at case 206, where `free` on that stack address aborted the CAS. 208 and 211 failed on a `TEST_USER2`
  that 206 left behind (측정, result diffs). lf4's case names are unknown (its logs are gone), so the match is by
  count and setup.

## Classification

- Local setup: the trigger is `call_stack_dump_on_error=yes`, which the LOG FATAL attempts added from lf3 on and CI
  does not use. Without it no run stalled and no ping timed out (cc7, cc10, cc12: 0/3), matching CI's pass of
  case 122 and lf2's pass.
- Underneath it is a pre-existing develop defect in the client network layer: a ping that times out leaves a stack
  buffer queued for its request id, and after the request id wraps the next request with that id receives into the
  dead stack slot. It reproduces on 173d92e454: a natural timeout in cc11, and the CAS abort at case 122 in cc20 when
  the same ping is forced to time out. It is not a Sidecar defect and not a JDBC driver mismatch.
- lf4's other 3 NOK share the cause (inferred from cc19, see above).
- `sidecar_force_external=no` on the head (cc9) changed nothing in the mechanism: the ping still timed out.

## Fix

None in this task. The defect is in develop code that the Sidecar PR does not touch, and fixing it on a branch of
f69816c086 would mix a develop fix into the Sidecar work. A fix would remove the queued reply buffer when
`net_client_ping_server` (and any other request with a queued user buffer) gives up on the reply, as the connect
path and `cubrid_log.c` already do, or make `css_is_valid_request_id` refuse an id with a live user buffer. The
check a fix should pass is `NO_STACKDUMP=1 GDB_PRE=tools/force-ping-43.gdb tools/one.sh <name> <install> <worktree>
1 122`: today the CAS aborts at case 122 (cc20, cc21); after a fix it must not.
