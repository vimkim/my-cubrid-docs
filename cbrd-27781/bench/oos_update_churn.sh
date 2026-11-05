#!/bin/bash
# OOS UPDATE/DELETE churn benchmark for ADR-0008 decision 7 (Work742).
# Usage: oos_update_churn.sh INSTALL OUTDIR LABEL REPEAT
# Server mode, one private database per sample, private port. Measures:
#   - elapsed time of INSERT, each UPDATE round, DELETE (client wall clock, csql -C)
#   - log bytes appended per phase and until vacuum drained (Current_append LSA of SHOW LOG HEADER)
#   - time for vacuum to drain the dropped chains (Oos_num_recs reaching the live count)
#   - vacuum worker execute time (statdump), OOS pages after drain and after a refill
set -euo pipefail
install=$(realpath "${1:?install}")
out=$(realpath -m "${2:?outdir}")
label=${3:?label}
rep=${4:?repeat}
ROWS=${ROWS:-3000}
ROUNDS=${ROUNDS:-3}
BYTES=${BYTES:-6000}

root="$out/$label-$rep"
mkdir -p "$root"
export CUBRID="$install"
export PATH="$install/bin:$PATH"
export LD_LIBRARY_PATH="$install/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
export CUBRID_DATABASES="$root"
export CUBRID_CONF_FILE="$root/cubrid.conf"
port=$((34000 + RANDOM % 2000))
cat > "$CUBRID_CONF_FILE" <<CONF
[service]
service=server
[common]
cubrid_port_id=$port
data_buffer_size=512M
log_buffer_size=64M
error_log_level=error
group_concat_max_len=33554432
CONF
touch "$root/databases.txt"
db=bench
cd "$root"
cubrid createdb --db-volume-size=1G --log-volume-size=512M -F "$root" $db en_US.utf8 > createdb.out 2>&1 </dev/null
cubrid server start $db > server_start.out 2>&1 </dev/null
cleanup () {
  cubrid server stop $db > server_stop.out 2>&1 </dev/null || true
  cubrid service stop > service_stop.out 2>&1 </dev/null || true
}
trap cleanup EXIT

q () { csql -C -u dba -c "$1" $db 2>&1 </dev/null; }
now () { date +%s.%N; }
# Current_append is printed like (12345|678); bytes ~ pageid*page + offset
append_bytes () {
  csql -C -u dba -l -c "SHOW LOG HEADER" $db 2>/dev/null </dev/null \
    | awk -F: '/Current_append/ {gsub(/[ ()\047"]/,"",$2); split($2,a,"|"); printf "%d\n", a[1]*16384 + a[2]}'
}
oos_field () {
  csql -C -u dba -l -c "SHOW HEAP OOS OF t" $db 2>/dev/null </dev/null \
    | awk -F: -v k="$1" '$1 ~ k {gsub(/ /,"",$2); print $2; exit}'
}
statv () { cubrid statdump $db 2>/dev/null </dev/null | awk -v k="$1" '$1 == k {print $3; exit}'; }

value_expr () { # per-row, per-round distinct, $BYTES bytes of MD5 output: low log compressibility
  local r=$1
  echo "CAST((SELECT GROUP_CONCAT(MD5(CONCAT(id, '-', $r, '-', k)) SEPARATOR '') FROM ks) AS BIT VARYING)"
}

q "CREATE TABLE t (id INT PRIMARY KEY, v BIT VARYING); CREATE TABLE f (id INT, s VARCHAR(2000)); COMMIT;" > schema.out
q "CREATE TABLE nums (id INT); INSERT INTO nums SELECT ROWNUM FROM db_class a, db_class b, db_class c WHERE ROWNUM <= $ROWS; COMMIT;" > nums.out
q "CREATE TABLE ks (k INT); INSERT INTO ks SELECT ROWNUM FROM db_class a, db_class b WHERE ROWNUM <= $((BYTES * 2 / 32)); COMMIT;" > ks.out

res="$out/results.csv"
[ -f "$res" ] || echo "label,rep,metric,value" > "$res"
emit () { echo "$label,$rep,$1,$2" >> "$res"; }

filler_sql="INSERT INTO f SELECT id, REPEAT('f', 1500) FROM nums WHERE id <= 200; COMMIT;"
# calibrate the filler's own log bytes while nothing else runs (median of three)
cal=()
for c in 1 2 3; do ca=$(append_bytes); q "$filler_sql" > /dev/null; cb=$(append_bytes); cal+=($((cb - ca))); done
filler_unit=$(printf '%s\n' "${cal[@]}" | sort -n | sed -n 2p)
emit filler_unit_log_bytes "$filler_unit"
b0=$(append_bytes)
t0=$(now); q "INSERT INTO t SELECT id, $(value_expr 0) FROM nums; COMMIT;" > insert.out; t1=$(now)
b1=$(append_bytes)
emit insert_sec "$(echo "$t1 - $t0" | bc)"
emit insert_log_bytes "$((b1 - b0))"
emit pages_after_insert "$(oos_field Oos_num_user_pages)"

upd_log=0
for r in $(seq 1 $ROUNDS); do
  ba=$(append_bytes)
  ta=$(now); q "UPDATE t SET v = $(value_expr $r); COMMIT;" > update_$r.out; tb=$(now)
  bb=$(append_bytes)
  emit "update${r}_sec" "$(echo "$tb - $ta" | bc)"
  emit "update${r}_log_bytes" "$((bb - ba))"
  upd_log=$((upd_log + bb - ba))
done
b_upd_end=$(append_bytes)
emit recs_after_updates "$(oos_field Oos_num_recs)"
t_upd_end=$(now)

# vacuum drain: live chunk records back to ROWS (one chunk per value). Vacuum only processes closed log
# blocks, so push the log forward with a non-OOS filler table; its own log bytes are subtracted.
filler_iters=0
drain_to () {
  local target=$1 n
  drained=0
  for i in $(seq 1 400); do
    n=$(oos_field Oos_num_recs)
    if [ -n "$n" ] && [ "$n" -le "$target" ]; then drained=1; return; fi
    q "$filler_sql" > /dev/null
    filler_iters=$((filler_iters + 1))
    sleep 0.2
  done
}
drain_to $ROWS
t_drain=$(now)
b_drain=$(append_bytes)
emit drained "$drained"
emit drain_sec_after_updates "$(echo "$t_drain - $t_upd_end" | bc)"
emit filler_iters_update_drain "$filler_iters"
emit vacuum_log_bytes_update_drain "$((b_drain - b_upd_end - filler_iters * filler_unit))"
emit recs_after_update_drain "$(oos_field Oos_num_recs)"
emit pages_after_update_drain "$(oos_field Oos_num_user_pages)"

td0=$(now); q "DELETE FROM t; COMMIT;" > delete.out; td1=$(now)
emit delete_sec "$(echo "$td1 - $td0" | bc)"
bd=$(append_bytes)
filler_iters=0
drain_to 0
emit delete_drained "$drained"
t_ddrain=$(now)
emit delete_drain_sec "$(echo "$t_ddrain - $td1" | bc)"
emit filler_iters_delete_drain "$filler_iters"
emit vacuum_log_bytes_delete_drain "$(( $(append_bytes) - bd - filler_iters * filler_unit ))"
emit recs_after_delete_drain "$(oos_field Oos_num_recs)"
emit pages_after_delete_drain "$(oos_field Oos_num_user_pages)"

q "INSERT INTO t SELECT id, $(value_expr 9) FROM nums; COMMIT;" > refill.out
emit pages_after_refill "$(oos_field Oos_num_user_pages)"

