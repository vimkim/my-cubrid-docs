#!/bin/bash
# CBRD-26659 campaign ticket 16 -- run one injection-site scenario against the instrumentation install.
#
# usage: t16_run.sh <site> <fault|control>
#
# Every run creates its own database under $T16/db, starts the campaign's own cub_master (port 26671) if
# needed, runs the site's workload through csql, collects the "FAULT INJECTION ACK" lines from the server
# error log, and stops only the server it started. Output: $T16/sites/<site>/<mode>/.
#
# "control" runs the same workload with fault_injection_ids set to 1 (FI_TEST_HANG, a code no site tests),
# so every site is compiled in and reachable but disabled; an acknowledgement in a control run is a failure.
set -u

SITE=${1:?site}
MODE=${2:?fault|control}
case "$MODE" in fault|control) ;; *) echo "mode must be fault or control" >&2; exit 2;; esac

# shellcheck disable=SC1091
source /home/vimkim/.cub/campaign/cbrd-26659/ticket16/tools/t16env.sh

RUN=$T16/sites/$SITE/$MODE
ulimit -c 200000 2>/dev/null || true   # cap core dumps at ~200 MB; a crash is still proven by a truncated core + the .err
rm -rf "$RUN"; mkdir -p "$RUN" "$T16/cores"
JOURNAL=$RUN/journal.txt
DB="t16_${SITE}_${MODE:0:1}"
DBDIR=$T16/db/$DB
ERRGLOB="$CUBRID/log/server/${DB}_2*.err"   # timestamped files only; the _latest.err symlink would double-count

log () { printf '%s %s\n' "$(date +%H:%M:%S.%N | cut -c1-12)" "$*" | tee -a "$JOURNAL"; }
now () { date +%s.%N; }

# ---- fault arming --------------------------------------------------------------------------------------
CODE=1          # set per site below; control runs always use 1
FIRE_AT=0
arm_sql () {   # runtime arming statement (the fault run uses the site's code, the control run code 1)
  local code=$1 fire=$2
  printf "SET SYSTEM PARAMETERS 'fault_injection_ids=%s; fault_injection_fire_at_occurrence=%s';\n" "$code" "$fire"
}
disarm_sql () { printf "SET SYSTEM PARAMETERS 'fault_injection_ids=1';\n"; }

# ---- server lifecycle ----------------------------------------------------------------------------------
SERVER_PID=""
MASTER_PID=""
ports_free () {
  local p busy=0
  for p in 26671 33140 33141 33142; do
    if ss -ltn | awk '{print $4}' | grep -qE ":$p\$"; then
      if [ "$p" = 26671 ] && ss -ltnp "sport = :26671" | grep -q "cub_master"; then
        log "port 26671 already held by cub_master pid $(ss -ltnp 'sport = :26671' | grep -o 'pid=[0-9]*' | head -1) (campaign master, reused)"
      else
        log "PORT $p BUSY"; busy=1
      fi
    fi
  done
  return $busy
}
db_create () {
  if grep -q "^$DB[[:space:]]" "$CUBRID_DATABASES/databases.txt" 2>/dev/null; then
    cubrid deletedb "$DB" > "$RUN/deletedb-previous.out" 2>&1
    log "previous database $DB deleted (rc=$?) before re-creation"
  fi
  rm -rf "$DBDIR"; mkdir -p "$DBDIR"
  local t0; t0=$(now)
  cubrid createdb --db-volume-size=64M --log-volume-size=64M --file-path="$DBDIR" --log-path="$DBDIR" "$DB" en_US > "$RUN/createdb.out" 2>&1
  local rc=$?
  log "createdb $DB rc=$rc ($(printf '%.1f' "$(echo "$(now) - $t0" | bc)") s)"
  return $rc
}
server_start () {
  local t0; t0=$(now)
  (cd "$T16/cores" && cubrid server start "$DB") > "$RUN/server-start-$1.out" 2>&1
  local rc=$?
  cubrid server status > "$RUN/server-status-$1.out" 2>&1
  SERVER_PID=$(grep -E "Server $DB " "$RUN/server-status-$1.out" | grep -o 'pid [0-9]*' | awk '{print $2}')
  MASTER_PID=$(ss -ltnp 'sport = :26671' | grep -o 'pid=[0-9]*' | head -1 | cut -d= -f2)
  log "server start ($1) rc=$rc server_pid=${SERVER_PID:-none} master_pid=${MASTER_PID:-none} ($(printf '%.1f' "$(echo "$(now) - $t0" | bc)") s)"
  printf 'start=%s server_pid=%s master_pid=%s\n' "$1" "${SERVER_PID:-none}" "${MASTER_PID:-none}" >> "$RUN/pids.txt"
  [ -n "$SERVER_PID" ]
}
server_stop () {
  cubrid server stop "$DB" > "$RUN/server-stop-$1.out" 2>&1
  local rc=$?
  sleep 1
  cubrid server status > "$RUN/server-status-after-stop-$1.out" 2>&1
  log "server stop ($1) rc=$rc; still listed: $(grep -c "Server $DB " "$RUN/server-status-after-stop-$1.out")"
}
server_alive () { [ -n "$SERVER_PID" ] && kill -0 "$SERVER_PID" 2>/dev/null; }
wait_server_gone () {   # up to $1 seconds
  local i=0
  while [ $i -lt "$1" ] && server_alive; do sleep 1; i=$((i+1)); done
  if server_alive; then log "server pid $SERVER_PID still alive after $1 s"; return 1; fi
  log "server pid $SERVER_PID gone after $i s"
}

# ---- workload and evidence -----------------------------------------------------------------------------
run_sql () {   # run_sql <label> <sqlfile>
  local t0; t0=$(now)
  csql -u dba "$DB" -i "$2" > "$RUN/csql-$1.out" 2>&1
  local rc=$?
  log "csql $1 rc=$rc ($(printf '%.2f' "$(echo "$(now) - $t0" | bc)") s)"
  return $rc
}
acks () {   # acknowledgement lines so far, each with the preceding error-log header (time, site file:line, tran, client)
  grep -h -B1 "FAULT INJECTION ACK" $ERRGLOB 2>/dev/null || true
}
ack_count () { grep -h "FAULT INJECTION ACK" $ERRGLOB 2>/dev/null | wc -l; }
wait_for_ack () {   # wait_for_ack <seconds> [min_count]
  local i=0 want=${2:-1}
  while [ $i -lt "$1" ]; do
    if [ "$(ack_count)" -ge "$want" ]; then log "ack observed after $i s"; return 0; fi
    sleep 1; i=$((i+1))
  done
  log "no ack after $1 s (count=$(ack_count))"
  return 1
}
collect () {
  mkdir -p "$RUN/server-err"
  cp $ERRGLOB "$RUN/server-err/" 2>/dev/null || true
  acks > "$RUN/acks.txt"
  log "acks: $(ack_count)"
  sed 's/^/  /' "$RUN/acks.txt" | tee -a "$JOURNAL"
  ls "$T16/cores" > "$RUN/cores-listing.txt" 2>/dev/null
}
sql () { cat > "$RUN/$1.sql"; }   # sql <label> <<EOF ... EOF

# common SQL fragments
V8K="CAST(REPEAT('AA', 8000) AS BIT VARYING)"        # one chunk, two per 16 KiB page
V20K="CAST(REPEAT('BB', 20000) AS BIT VARYING)"      # two chunks
V40K="CAST(REPEAT('CC', 40000) AS BIT VARYING)"      # three chunks
V3="CAST(REPEAT('FA', 8000) AS BIT VARYING)"        # one chunk, distinct pattern for the UPDATE
CREATE_T="CREATE TABLE t (id INT, v BIT VARYING);"
CREATE_T2="CREATE TABLE t (id INT, v1 BIT VARYING, v2 BIT VARYING);"
VERIFY_T="SELECT COUNT(*) FROM t; SELECT id, (v = $V8K) AS eq8k, (v = $V20K) AS eq20k, (v = $V40K) AS eq40k FROM t ORDER BY id; SHOW HEAP OOS OF t;"
FILLER="CREATE TABLE IF NOT EXISTS filler (id INT, v BIT VARYING); INSERT INTO filler SELECT ROWNUM, CAST(REPEAT('DD', 12000) AS BIT VARYING) FROM db_class a, db_class b LIMIT 60; COMMIT;"

# ---- scenarios -----------------------------------------------------------------------------------------
# Each scenario sets CODE and FIRE_AT, writes its SQL and drives the server. RESULT is filled at the end.
RESULT="unset"

scenario_common_start () {   # <extra conf lines...>
  t16_conf "" "$@"
  cp "$CUBRID/conf/cubrid.conf" "$RUN/cubrid.conf"
  ports_free || { log "ports busy; abort"; exit 3; }
  db_create || exit 4
  server_start 1 || exit 5
}

site_a1 () {   # group 1: bad_alloc while publishing an OOS OID (insert / value construction)
  CODE=700000; FIRE_AT=0
  scenario_common_start
  sql w <<EOF
$CREATE_T
$(arm_sql "$([ $MODE = fault ] && echo $CODE || echo 1)" $FIRE_AT)
INSERT INTO t VALUES (1, $V8K);
$(disarm_sql)
INSERT INTO t VALUES (2, $V8K);
$VERIFY_T
EOF
  run_sql w "$RUN/w.sql"
  server_stop 1
}

site_b1 () {   # group 1: bad_alloc in the grouped Resolve prefetch (read / expansion)
  CODE=700001; FIRE_AT=0
  scenario_common_start
  sql w <<EOF
$CREATE_T2
INSERT INTO t VALUES (1, CAST(REPEAT('AA', 6000) AS BIT VARYING), CAST(REPEAT('BB', 6000) AS BIT VARYING));
SHOW HEAP OOS OF t;
$(arm_sql "$([ $MODE = fault ] && echo $CODE || echo 1)" $FIRE_AT)
SELECT id, (v1 = CAST(REPEAT('AA', 6000) AS BIT VARYING)) AS eq1, (v2 = CAST(REPEAT('BB', 6000) AS BIT VARYING)) AS eq2 FROM t;
$(disarm_sql)
SELECT id, (v1 = CAST(REPEAT('AA', 6000) AS BIT VARYING)) AS eq1, (v2 = CAST(REPEAT('BB', 6000) AS BIT VARYING)) AS eq2 FROM t;
EOF
  run_sql w "$RUN/w.sql"
  server_stop 1
}

vacuum_workload () {   # shared by c1, j1, k1: insert OOS rows, UPDATE them (old chains become dead versions
                       # reclaimed by the forward-walk = RVHF_UPDATE_NOTIFY_VACUUM), arm, then advance the log
  sql w1 <<EOF
$CREATE_T
INSERT INTO t SELECT ROWNUM, $V8K FROM db_class a LIMIT 8;
COMMIT;
SHOW HEAP OOS OF t;
UPDATE t SET v = $V3;
COMMIT;
SHOW HEAP OOS OF t;
$(arm_sql "$([ $MODE = fault ] && echo $CODE || echo 1)" $FIRE_AT)
$FILLER
EOF
  run_sql w1 "$RUN/w1.sql"
}
vacuum_settle () {   # poll until the deleted chunks are gone from SHOW HEAP OOS, or a timeout
  local i=0 recs
  sql poll <<EOF
SHOW HEAP OOS OF t;
EOF
  while [ $i -lt 150 ]; do
    csql -l -u dba "$DB" -i "$RUN/poll.sql" > "$RUN/csql-poll.out" 2>&1
    recs=$(awk '/Oos_num_recs/ {print $NF}' "$RUN/csql-poll.out" | head -1)
    if [ "$MODE" = fault ] && [ "$(ack_count)" -ge 1 ]; then log "ack seen while polling (recs=${recs:-?}) after $i s"; sleep 3; break; fi
    if [ "${recs:-x}" = "8" ]; then log "vacuum reclaimed the old chains: Oos_num_recs=8 after $i s"; break; fi
    sleep 2; i=$((i+2))
  done
  csql -l -u dba "$DB" -i "$RUN/poll.sql" > "$RUN/csql-poll-final.out" 2>&1
  log "final SHOW HEAP OOS: $(grep -E 'Oos_num_recs|Oos_num_user_pages' "$RUN/csql-poll-final.out" | tr -s ' ' | tr '\n' ';')"
}

site_c1 () {   # group 1: bad_alloc growing the reclaim hint list during a vacuum chain delete (cleanup)
  CODE=700002; FIRE_AT=1
  scenario_common_start "log_compress=no"   # repeated-byte payloads would otherwise compress to almost nothing and never complete a vacuum block
  vacuum_workload
  vacuum_settle
  server_stop 1
}

site_d1 () {   # group 2: data I/O error on the flush of a PAGE_OOS page (direct write path, DWB off)
  CODE=700003; FIRE_AT=1
  scenario_common_start "double_write_buffer_size=0" "data_buffer_size=16M"
  sql w <<EOF
$CREATE_T
$(arm_sql "$([ $MODE = fault ] && echo $CODE || echo 1)" $FIRE_AT)
INSERT INTO t SELECT ROWNUM, CAST(REPEAT('EE', 12000) AS BIT VARYING) FROM db_class a, db_class b LIMIT 1500;
SELECT COUNT(*), SUM(v = CAST(REPEAT('EE', 12000) AS BIT VARYING)) AS n_equal FROM t;
SHOW HEAP OOS OF t;
EOF
  run_sql w "$RUN/w.sql"
  wait_for_ack 5 || true
  server_stop 1
  cubrid checkdb -S "$DB" > "$RUN/checkdb.out" 2>&1; log "checkdb -S rc=$?"
  server_start 2
  sql v <<EOF
SELECT COUNT(*), SUM(v = CAST(REPEAT('EE', 12000) AS BIT VARYING)) AS n_equal FROM t;
EOF
  run_sql v "$RUN/v.sql"
  server_stop 2
}

site_e1 () {   # group 2: log I/O error on the write of an active log page (fatal for the server)
  CODE=700004; FIRE_AT=1
  scenario_common_start
  sql w <<EOF
$CREATE_T
INSERT INTO t VALUES (1, $V8K);
$(arm_sql "$([ $MODE = fault ] && echo $CODE || echo 1)" $FIRE_AT)
INSERT INTO t VALUES (2, $V20K);
SELECT COUNT(*) FROM t;
EOF
  run_sql w "$RUN/w.sql"
  if [ "$MODE" = fault ]; then wait_server_gone 20 || true; else log "control: server alive=$(server_alive && echo yes || echo no)"; fi
  cubrid server status > "$RUN/server-status-after-fault.out" 2>&1
  if server_alive; then server_stop 1; fi
  server_start 2
  sql v <<EOF
$VERIFY_T
EOF
  run_sql v "$RUN/v.sql"
  server_stop 2
}

site_f1 () {   # group 3: oos_insert_many fails at its second iteration (after one value is published)
  CODE=700005; FIRE_AT=2
  scenario_common_start
  sql w <<EOF
$CREATE_T2
$(arm_sql "$([ $MODE = fault ] && echo $CODE || echo 1)" $FIRE_AT)
INSERT INTO t VALUES (1, $V20K, $V40K);
$(disarm_sql)
SELECT COUNT(*) FROM t;
SHOW HEAP OOS OF t;
INSERT INTO t VALUES (2, $V20K, $V40K);
SELECT id, (v1 = $V20K) AS eq1, (v2 = $V40K) AS eq2 FROM t ORDER BY id;
SHOW HEAP OOS OF t;
EOF
  run_sql w "$RUN/w.sql"
  server_stop 1
}

crash_site () {   # shared by g1, h1: arm, insert a multi-chunk value, expect the server to vanish, restart, verify
  sql w <<EOF
$CREATE_T
INSERT INTO t VALUES (1, $V8K);
$(arm_sql "$([ $MODE = fault ] && echo $CODE || echo 1)" $FIRE_AT)
INSERT INTO t VALUES (2, $1);
SELECT COUNT(*) FROM t;
EOF
  run_sql w "$RUN/w.sql"
  if [ "$MODE" = fault ]; then wait_server_gone 20 || true; else log "control: server alive=$(server_alive && echo yes || echo no)"; fi
  cubrid server status > "$RUN/server-status-after-fault.out" 2>&1
  if server_alive; then server_stop 1; fi
  server_start 2
  sql v <<EOF
$VERIFY_T
EOF
  run_sql v "$RUN/v.sql"
  server_stop 2
}
site_g1 () {   # group 3: crash between the chunk inserts of one chain (after the tail chunk)
  CODE=700006; FIRE_AT=1
  scenario_common_start
  crash_site "$V40K"
}
site_h1 () {   # group 3: crash after all chunks are inserted and published, before the heap insert
  CODE=700007; FIRE_AT=1
  scenario_common_start
  crash_site "$V20K"
}

site_i1 () {   # group 4: undo of RVOOS_INSERT fails during a transaction rollback
  CODE=700008; FIRE_AT=1
  scenario_common_start
  sql w <<EOF
$CREATE_T
;autocommit off
INSERT INTO t VALUES (1, $V20K);
$(arm_sql "$([ $MODE = fault ] && echo $CODE || echo 1)" $FIRE_AT)
ROLLBACK;
SELECT COUNT(*) FROM t;
COMMIT;
EOF
  run_sql w "$RUN/w.sql"
  if [ "$MODE" = fault ]; then wait_server_gone 30 || true; else log "control: server alive=$(server_alive && echo yes || echo no)"; fi
  cubrid server status > "$RUN/server-status-after-fault.out" 2>&1
  # capture the acknowledgement from the first server's log before restarting
  acks > "$RUN/acks-after-fault.txt" 2>/dev/null || true
  if server_alive; then server_stop 1; fi
  server_start 2 || true
  if server_alive; then
    sql v <<EOF
$VERIFY_T
EOF
    run_sql v "$RUN/v.sql"
    server_stop 2
  else
    log "server did not restart cleanly; recovery status in server-start-2.out"
  fi
}

site_j1 () {   # group 4: vacuum forward-walk delete of a value chain fails (bounded leak path)
  CODE=700009; FIRE_AT=1
  scenario_common_start "log_compress=no"   # repeated-byte payloads would otherwise compress to almost nothing and never complete a vacuum block
  vacuum_workload
  vacuum_settle
  server_stop 1
}

site_k1 () {   # group 4: write fix of an empty-page reclaim candidate is skipped
  CODE=700010; FIRE_AT=0
  scenario_common_start "log_compress=no"   # repeated-byte payloads would otherwise compress to almost nothing and never complete a vacuum block
  vacuum_workload
  vacuum_settle
  # The vacuum fast path defers the emptied pages (LSA gate: the worker's own head LSA is the horizon) and a
  # growth in the same server lifetime reuses them through bestspace before any sweep. After a restart the
  # bestspace cache is empty and the boot rule forces a growth-gate sweep on the first allocation, with a
  # horizon that has passed the deletes: that sweep is the remaining way to reach the phase-2 WRITE fix.
  server_stop 1
  server_start 2
  sql w2 <<EOF
$(arm_sql "$([ $MODE = fault ] && echo $CODE || echo 1)" $FIRE_AT)
INSERT INTO t SELECT ROWNUM + 1000, $V40K FROM db_class a, db_class b LIMIT 12;
COMMIT;
SHOW HEAP OOS OF t;
EOF
  run_sql w2 "$RUN/w2.sql"
  wait_for_ack 3 || true
  server_stop 2
}

site_l1 () {   # group 4: redo of RVOOS_INSERT fails during restart recovery, then the recovery is retried
  CODE=700011; FIRE_AT=1
  # keep the OOS data pages dirty in the buffer (never flushed) so restart recovery must REDO the RVOOS_INSERTs
  # page_flush_interval=0 makes the flush daemon loop continuously (everything is flushed at once); use a long interval
  scenario_common_start "data_buffer_size=1G" "page_flush_interval=600000" "double_write_buffer_size=0"
  sql w <<EOF
$CREATE_T
INSERT INTO t SELECT ROWNUM, $V20K FROM db_class a, db_class b LIMIT 30;
COMMIT;
SELECT COUNT(*) FROM t;
EOF
  run_sql w "$RUN/w.sql"
  log "kill -9 own cub_server pid $SERVER_PID (dirty OOS pages not flushed; redo needed at restart)"
  kill -9 "$SERVER_PID"; wait_server_gone 10 || true
  # arm through cubrid.conf (recovery runs before any client can SET SYSTEM PARAMETERS)
  if [ "$MODE" = fault ]; then t16_conf "$CODE" "fault_injection_fire_at_occurrence=$FIRE_AT"; else t16_conf "1" "fault_injection_fire_at_occurrence=$FIRE_AT"; fi
  cp "$CUBRID/conf/cubrid.conf" "$RUN/cubrid.conf.armed"
  server_start 2 || true
  sleep 2; cubrid server status > "$RUN/server-status-recovery-attempt.out" 2>&1
  if server_alive; then log "server survived the armed restart"; else log "server did not come up under the armed restart (expected in fault mode)"; fi
  if server_alive; then server_stop 2; fi
  # recovery retry with the fault removed
  t16_conf ""
  cp "$CUBRID/conf/cubrid.conf" "$RUN/cubrid.conf.retry"
  server_start 3
  sql v <<EOF
$VERIFY_T
EOF
  run_sql v "$RUN/v.sql"
  server_stop 3
}

# ---- main ----------------------------------------------------------------------------------------------
T_START=$(now)
log "=== site=$SITE mode=$MODE db=$DB install=$CUBRID"
"$CUBRID/bin/cubrid_rel" 2>&1 | grep CUBRID | tee -a "$JOURNAL"
sha256sum "$CUBRID/lib/libcubrid.so" | tee -a "$JOURNAL"
"site_$SITE" || log "site function returned $?"
collect
T_END=$(now)
log "=== done site=$SITE mode=$MODE code=$CODE fire_at=$FIRE_AT wall=$(printf '%.1f' "$(echo "$T_END - $T_START" | bc)") s"
