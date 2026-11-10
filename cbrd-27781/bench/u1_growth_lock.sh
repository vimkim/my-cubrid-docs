#!/bin/bash
# U-1 (PR #8434 review at 8e139f4db): throughput of concurrent inserts that grow one OOS file.
# Usage: u1_growth_lock.sh INSTALL OUTDIR LABEL REP
# One private database and port per (LABEL, REP). Server mode, csql -C clients.
#
# Insert points: for each N in $CONC, N sessions insert into the same table t. Every value is
# $BYTES bytes of MD5 hex cast to BIT VARYING (low compressibility), so one value fills most of
# one OOS page and every insert allocates a new OOS page. Total rows per point is $TOTAL,
# split evenly; each statement inserts $BATCH rows and commits (csql autocommit).
# Mixed point: t is first filled with $TOTAL rows; then N/2 sessions delete those rows in
# batches while N/2 sessions insert $TOTAL/2 new rows, so vacuum feeds the emptied-page set
# while the file grows.
#
# Per point it records wall time, rows/s, per-statement latency (csql prints each statement's time), load average
# before/after, server context switches and task-clock (perf stat -p), and OOS user pages.
# DIAG=cs records a call graph at every server context switch (perf record -e context-switches);
# DIAG=strace counts the server's futex calls (strace -c). Both slow the server: diagnosis only.
set -euo pipefail
install=$(realpath "${1:?install}")
out=$(realpath -m "${2:?outdir}")
label=${3:?label}
rep=${4:?rep}
CONC=${CONC:-"1 8 16 32 64"}
MIXED=${MIXED:-"16 64"}
TOTAL=${TOTAL:-51200}
BATCH=${BATCH:-10}
BYTES=${BYTES:-12000}
NSRC=${NSRC:-200}

root="$out/runs/$label-$rep"
rm -rf "${root:?}"
mkdir -p "$root"
export CUBRID="$install"
export PATH="$install/bin:$PATH"
export LD_LIBRARY_PATH="$install/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
export CUBRID_DATABASES="$root"
export CUBRID_CONF_FILE="$root/cubrid.conf"
export CUBRID_TMP="$root/tmp"
mkdir -p "$CUBRID_TMP"
port=${PORT:?PORT}
cat > "$CUBRID_CONF_FILE" <<CONF
[service]
service=server
[common]
cubrid_port_id=$port
data_buffer_size=2G
log_buffer_size=64M
max_clients=200
error_log_level=error
group_concat_max_len=33554432
CONF
touch "$root/databases.txt"
db=u1bench
cd "$root"
cubrid createdb --db-volume-size=6G --log-volume-size=1G -F "$root" $db en_US.utf8 > createdb.out 2>&1 </dev/null
cubrid server start $db > server_start.out 2>&1 </dev/null
cleanup () {
  cubrid server stop $db > server_stop.out 2>&1 </dev/null || true
  cubrid service stop > service_stop.out 2>&1 </dev/null || true
  # keep outputs, drop the volumes and logs (several GB per run)
  [ "${KEEP_DB:-0}" = 1 ] || rm -rf "${root:?}/u1bench"* "${root:?}/lob"
}
trap cleanup EXIT

q () { csql -C -u dba -c "$1" $db 2>&1 </dev/null; }
now () { date +%s.%N; }
la () { cut -d' ' -f1 /proc/loadavg; }
spid () { pgrep -u "$(id -u)" -f "cub_server $db\$" | while read -r p; do
  [ "$(tr '\0' '\n' < /proc/$p/environ | grep -m1 '^CUBRID_DATABASES=')" = "CUBRID_DATABASES=$root" ] && echo "$p"; done; }
oos_pages () {
  csql -C -u dba -l -c "SHOW HEAP OOS OF t" $db 2>/dev/null </dev/null \
    | awk -F: '$1 ~ /Oos_num_user_pages/ {gsub(/ /,"",$2); print $2; exit}'
}
vcsw () { # sum of voluntary context switches over all server threads
  cat /proc/"$1"/task/*/status 2>/dev/null | awk '/^voluntary_ctxt_switches/ {s+=$2} END {print s+0}'
}

pid=$(spid)
[ -n "$pid" ] || { echo "server not found" >&2; exit 1; }
echo "$pid" > server.pid
readlink "/proc/$pid/exe" > server.exe
sha256sum "$(cat server.exe)" > server.sha256

# src: $NSRC distinct page-filling values; ks drives GROUP_CONCAT to $BYTES bytes.
q "CREATE TABLE ks (k INT); INSERT INTO ks SELECT ROWNUM FROM db_class a, db_class b WHERE ROWNUM <= $((BYTES * 2 / 32)); COMMIT;" > ks.out
q "CREATE TABLE nums (id INT); INSERT INTO nums SELECT ROWNUM FROM db_class a, db_class b, db_class c WHERE ROWNUM <= $NSRC; COMMIT;" > nums.out
q "CREATE TABLE src (id INT PRIMARY KEY, v BIT VARYING); INSERT INTO src SELECT id, CAST((SELECT GROUP_CONCAT(MD5(CONCAT(id, '-', k)) SEPARATOR '') FROM ks) AS BIT VARYING) FROM nums; COMMIT;" > src.out
q "SELECT COUNT(*), MIN(BIT_LENGTH(v))/8, MAX(BIT_LENGTH(v))/8 FROM src;" > src_check.out

res="$out/results.csv"
[ -f "$res" ] || echo "label,rep,point,n,metric,value" > "$res"
emit () { echo "$label,$rep,$1,$2,$3,$4" >> "$res"; }

# session script: $1 file, $2 sid, $3 nrows, $4 kind (ins|del), $5 first id for del
mk_session () {
  local f=$1 sid=$2 nrows=$3 kind=$4 first=${5:-0} i a b
  : > "$f"
  for ((i = 0; i < nrows; i += BATCH)); do
    if [ "$kind" = ins ]; then
      a=$(( (sid * 37 + i) % (NSRC - BATCH) + 1 )); b=$((a + BATCH - 1))
      echo "INSERT INTO t (sid, v) SELECT $sid, v FROM src WHERE id BETWEEN $a AND $b;" >> "$f"
    else
      a=$((first + i)); b=$((a + BATCH - 1))
      echo "DELETE FROM t WHERE id BETWEEN $a AND $b;" >> "$f"
    fi
  done
}

run_sessions () { # $1 point dir; sessions are $1/s*.sql; returns after all finish
  local d=$1 f
  local pids=()
  for f in "$d"/s*.sql; do
    csql -C -u dba -i "$f" $db > "${f%.sql}.out" 2>&1 </dev/null &
    pids+=($!)
  done
  local rc=0
  for p in "${pids[@]}"; do wait "$p" || rc=1; done
  return $rc
}

measure () { # $1 point name, $2 n, $3 point dir, $4 rows inserted, $5 rows deleted
  local name=$1 n=$2 d=$3 ins=$4 del=$5
  local la0 la1 t0 t1 v0 v1 perfpid errs
  la0=$(la); v0=$(vcsw "$pid")
  perf stat -e context-switches,cpu-migrations,task-clock -x, -o "$d/perf.csv" -p "$pid" &
  perfpid=$!
  local diagpid=""
  case "${DIAG:-}" in
    cs) perf record -q -e context-switches -c 1 --call-graph dwarf,8192 -o "$d/cs.data" -p "$pid" > "$d/diag.out" 2>&1 & diagpid=$! ;;
    strace) strace -f -c -e trace=futex -o "$d/strace.txt" -p "$pid" > "$d/diag.out" 2>&1 & diagpid=$! ;;
  esac
  sleep 0.3
  [ -z "$diagpid" ] || sleep 2
  t0=$(now)
  run_sessions "$d" || true
  t1=$(now)
  kill -INT "$perfpid"; wait "$perfpid" || true
  if [ -n "$diagpid" ]; then kill -INT "$diagpid"; wait "$diagpid" || true; fi
  v1=$(vcsw "$pid"); la1=$(la)
  local wall; wall=$(echo "$t1 - $t0" | bc)
  errs=$(cat "$d"/s*.out | grep -ci 'error' || true)
  emit "$name" "$n" wall_sec "$wall"
  emit "$name" "$n" rows_inserted "$ins"
  emit "$name" "$n" rows_deleted "$del"
  emit "$name" "$n" insert_rows_per_sec "$(echo "scale=1; $ins / $wall" | bc)"
  emit "$name" "$n" errors "$errs"
  emit "$name" "$n" load_before "$la0"
  emit "$name" "$n" load_after "$la1"
  emit "$name" "$n" server_vcsw "$((v1 - v0))"
  emit "$name" "$n" server_ctxsw "$(awk -F, '$3=="context-switches" {print $1}' "$d/perf.csv")"
  emit "$name" "$n" server_task_clock_ms "$(awk -F, '$3=="task-clock" {print $1}' "$d/perf.csv")"
  # per-statement latency of the insert sessions (ms), from the time csql prints per statement
  local lat="$d/ins_latency_ms.txt"
  for f in "$d"/s*.sql; do
    grep -q '^INSERT' "$f" || continue
    # csql prints "10 rows affected. (0.016232 sec) Committed. (...)" per statement
    awk '/rows? affected\. \(/ {s=$0; sub(/.*affected\. \(/, "", s); sub(/ sec.*/, "", s); print s*1000}' "${f%.sql}.out"
  done | sort -n > "$lat"
  local cnt; cnt=$(wc -l < "$lat")
  if [ "$cnt" -gt 0 ]; then
    emit "$name" "$n" ins_stmt_count "$cnt"
    emit "$name" "$n" ins_stmt_p50_ms "$(awk -v c="$cnt" 'NR==int(c*0.50+0.5){print; exit}' "$lat")"
    emit "$name" "$n" ins_stmt_p99_ms "$(awk -v c="$cnt" 'NR==int(c*0.99+0.5){print; exit}' "$lat")"
    emit "$name" "$n" ins_stmt_max_ms "$(tail -1 "$lat")"
  fi
}

reset_table () {
  q "DROP TABLE IF EXISTS t; CREATE TABLE t (id INT AUTO_INCREMENT PRIMARY KEY, sid INT, v BIT VARYING); COMMIT;" > "$1/reset.out"
}

# warmup: one small growth run so code and src pages are resident
mkdir -p warm; reset_table warm
mk_session warm/s0.sql 0 200 ins; run_sessions warm

for n in $CONC; do
  d="$root/ins-$n"; mkdir -p "$d"; reset_table "$d"
  per=$((TOTAL / n))
  for ((s = 0; s < n; s++)); do mk_session "$d/s$s.sql" "$s" "$per" ins; done
  measure insert "$n" "$d" $((per * n)) 0
  got=$(q "SELECT COUNT(*) FROM t;" | awk '/^ *[0-9]+ *$/ {print $1; exit}')
  emit insert "$n" rows_in_table "$got"
  emit insert "$n" oos_user_pages "$(oos_pages)"
done

for n in $MIXED; do
  d="$root/mixed-$n"; mkdir -p "$d"; reset_table "$d"
  # prefill TOTAL rows (ids 1..TOTAL) with one session, then let vacuum settle
  mk_session "$d/prefill.sql.tmp" 0 "$TOTAL" ins
  csql -C -u dba -i "$d/prefill.sql.tmp" $db > "$d/prefill.out" 2>&1 </dev/null
  sleep 5
  emit mixed "$n" oos_user_pages_before "$(oos_pages)"
  half=$((n / 2)); per_i=$((TOTAL / 2 / half)); per_d=$((TOTAL / half))
  for ((s = 0; s < half; s++)); do
    mk_session "$d/s$s.sql" "$s" "$per_i" ins
    mk_session "$d/s$((s + half)).sql" "$((s + half))" "$per_d" del $((1 + s * per_d))
  done
  measure mixed "$n" "$d" $((per_i * half)) $((per_d * half))
  got=$(q "SELECT COUNT(*) FROM t;" | awk '/^ *[0-9]+ *$/ {print $1; exit}')
  emit mixed "$n" rows_in_table "$got"
  emit mixed "$n" oos_user_pages "$(oos_pages)"
done

cubrid statdump $db > statdump.out 2>&1 </dev/null || true
