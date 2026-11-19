#!/usr/bin/env bash
# OOS crash-recovery check for CBRD-27841 (RVREPL_OOS_DELETE removal, OOS indices renumbered).
#
# Usage, inside the selected CUBRID work environment (CUBRID, CUBRID_DATABASES set):
#   oos_crash_recovery.sh DB OUTDIR
# DB is a registered database that only this test uses; the script starts and kill -9s its server.
#
# 1. t_upd: committed MVCC UPDATE of OOS values. Its old chains are reclaimed only by vacuum consuming
#    RVOOS_NOTIFY_VACUUM (ADR-0008, A'). t_del: committed DELETE of OOS rows (heap vacuum path).
# 2. A session holds an old snapshot so vacuum cannot reclaim anything before the crash.
# 3. Another session leaves an uncommitted UPDATE and INSERT of OOS values in flight.
# 4. kill -9 the server, restart it (debug builds run rv_check_rvfuns here), advance the log.
# 5. Data must equal the committed state; Oos_num_recs must fall to that of a garbage-free copy.
# 6. checkdb -S after a clean stop.
set -uo pipefail
db=${1:?database}
out=${2:?output directory}
mkdir -p "$out"
N=200
VLEN=6080    # 190 md5 hex digests: string compression cannot shrink the value below the OOS threshold
fail=0

blob () {  # SQL expression for an incompressible VLEN-byte value of row id, distinct per tag
  local tag=$1 i expr=""
  for i in $(seq 0 189); do expr+="${expr:+ || }md5('$tag' || id || '_$i')"; done
  echo "$expr"
}

log () { printf '%s %s\n' "$(date +%T)" "$*" | tee -a "$out/summary.log"; }
q () { csql -u dba -C -t -N -c "$1" "$db" </dev/null 2>>"$out/csql.err"; }
oos_recs () {
  csql -u dba -C -l -c "show heap oos of $1" "$db" </dev/null 2>>"$out/csql.err" \
    | awk -F': *' '/Oos_num_recs/ {print $2; exit}'
}
server_pid () {
  local p
  for p in $(pgrep -x cub_server); do
    [ "$(readlink "/proc/$p/exe")" = "$CUBRID/bin/cub_server" ] || continue
    tr '\0' ' ' <"/proc/$p/cmdline" | grep -qw -- "$db" && echo "$p"
  done
}
start_server () {
  timeout 180 setsid -w cubrid server start "$db" </dev/null >"$out/$1.out" 2>"$out/$1.err"
  local rc=$?
  log "server start ($1) rc=$rc pid=$(server_pid)"
  return $rc
}
check () {  # name expected actual
  if [ "$2" = "$3" ]; then log "PASS $1: $3"; else log "FAIL $1: expected $2, got $3"; fail=1; fi
}

[ -n "$(server_pid)" ] || start_server start0 || exit 1

q "drop table if exists t_upd, t_del, r_upd, r_del, filler;" >/dev/null
q "create table t_upd (id int primary key, v varchar($((VLEN * 2))), w varchar($((VLEN * 2))));" >/dev/null
q "create table t_del (id int primary key, v varchar($((VLEN * 2))), w varchar($((VLEN * 2))));" >/dev/null
q "create table filler (id int, pad varchar($((VLEN * 2))));" >/dev/null
for t in t_upd t_del; do
  q "insert into $t (id) select rownum from db_root connect by level <= $N;" >/dev/null
  q "update $t set v = $(blob v), w = $(blob w);" >/dev/null
done
load_upd=$(oos_recs t_upd)
load_del=$(oos_recs t_del)
log "loaded: t_upd rows=$(q 'select count(*) from t_upd') oos=$load_upd; t_del rows=$(q 'select count(*) from t_del') oos=$load_del"
if [ "${load_upd:-0}" -le 0 ] || [ "${load_del:-0}" -le 0 ]; then
  log "FAIL the loaded values are not stored out of row"
  exit 1
fi

# Old snapshot: vacuum may not reclaim anything committed after this point until the session ends.
setsid csql -u dba -C --no-auto-commit -c "select count(*) from t_upd; select sleep(900);" "$db" \
  </dev/null >"$out/holder.out" 2>&1 &
sleep 3

q "update t_upd set v = $(blob u);" >/dev/null
q "delete from t_del where id > $((N / 2));" >/dev/null
log "committed UPDATE of t_upd.v and DELETE of t_del ids > $((N / 2))"

# SHOW HEAP OOS needs a table lock that the in-flight session below blocks, so count first.
pre_upd=$(oos_recs t_upd)
pre_del=$(oos_recs t_del)
log "before kill: t_upd oos=$pre_upd t_del oos=$pre_del"

# In flight at the crash: must be rolled back by restart recovery.
setsid csql -u dba -C --no-auto-commit -c "update t_upd set w = $(blob z) where id <= 20;
  insert into t_upd select $N + rownum, NULL, NULL from db_root connect by level <= 10;
  update t_upd set v = $(blob x), w = $(blob y) where id > $N;
  select sleep(900);" "$db" </dev/null >"$out/inflight.out" 2>&1 &
sleep 5
cubrid tranlist -s "$db" </dev/null >"$out/tranlist_before_kill.out" 2>&1

pid=$(server_pid)
log "kill -9 cub_server pid=$pid"
kill -9 "$pid"
while [ -e "/proc/$pid" ]; do sleep 1; done

# cub_master restarts a killed server by itself (auto_restart_server); start it only if it did not.
newpid=""
for _ in $(seq 30); do newpid=$(server_pid); [ -n "$newpid" ] && break; sleep 1; done
if [ -n "$newpid" ]; then
  log "cub_master restarted the server: pid=$newpid"
else
  start_server restart || { log "FAIL restart"; exit 1; }
fi
up=""
for _ in $(seq 120); do up=$(q "select 1;"); [ "$up" = 1 ] && break; sleep 1; done
[ "$up" = 1 ] || { log "FAIL the restarted server does not answer"; exit 1; }
cubrid server status </dev/null >"$out/status_after_restart.out" 2>&1
grep -E 'RECOVERY:|Log recovery|Server status' "$CUBRID/log/server/${db}_latest.err" >"$out/recovery.log"
log "restart recovery: $(grep -E 'REDO Phase is started|UNDO Phase is started' "$out/recovery.log" | sed 's/^Log recovery: //' | tr '\n' ' ')"

# Reference tables hold the committed state. They are built from NULL rows, so they carry no OOS garbage
# and their Oos_num_recs is the value vacuum must reach. (A WHERE clause with the long md5 chains is slow
# to compile in csql, so the values are compared by a join instead.)
q "create table r_upd (id int primary key, v varchar($((VLEN * 2))), w varchar($((VLEN * 2))));
   create table r_del (id int primary key, v varchar($((VLEN * 2))), w varchar($((VLEN * 2))));
   insert into r_upd (id) select rownum from db_root connect by level <= $N;
   insert into r_del (id) select rownum from db_root connect by level <= $((N / 2));" >/dev/null
q "update r_upd set v = $(blob u), w = $(blob w);" >/dev/null
q "update r_del set v = $(blob v), w = $(blob w);" >/dev/null

# Data equals the committed state: the in-flight UPDATE/INSERT are gone, the committed ones stay.
check "t_upd rows" "$N" "$(q 'select count(*) from t_upd')"
check "t_upd values" "$N" "$(q 'select count(*) from t_upd t, r_upd r where t.id = r.id and t.v = r.v and t.w = r.w')"
check "t_del rows" "$((N / 2))" "$(q 'select count(*) from t_del')"
check "t_del values" "$((N / 2))" "$(q 'select count(*) from t_del t, r_del r where t.id = r.id and t.v = r.v and t.w = r.w')"

want_upd=$(oos_recs r_upd)
want_del=$(oos_recs r_del)
log "garbage-free reference: r_upd oos=$want_upd r_del oos=$want_del"
if [ "$pre_upd" -le "$want_upd" ]; then
  log "FAIL t_upd held no garbage before the kill ($pre_upd <= $want_upd): the run does not test vacuum after restart"
  fail=1
fi

# Advance the log past the open vacuum block, then wait for vacuum to reclaim.
got_upd=$pre_upd
got_del=$pre_del
for i in $(seq 40); do
  q "insert into filler (id) select rownum from db_root connect by level <= 100;
     update filler set pad = $(blob f);
     delete from filler;" >/dev/null
  got_upd=$(oos_recs t_upd)
  got_del=$(oos_recs t_del)
  echo "$(date +%T) round $i t_upd oos=$got_upd t_del oos=$got_del" >>"$out/vacuum_progress.log"
  [ "$got_upd" = "$want_upd" ] && [ "$got_del" = "$want_del" ] && break
  sleep 3
done
check "t_upd Oos_num_recs after vacuum (RVOOS_NOTIFY_VACUUM path)" "$want_upd" "$got_upd"
check "t_del Oos_num_recs after vacuum" "$want_del" "$got_del"

timeout 180 cubrid server stop "$db" </dev/null >"$out/stop.out" 2>&1
timeout 600 cubrid checkdb -S "$db" </dev/null >"$out/checkdb.out" 2>&1
check "checkdb -S exit code" 0 "$?"

log "RESULT $([ $fail = 0 ] && echo PASS || echo FAIL)"
exit $fail
