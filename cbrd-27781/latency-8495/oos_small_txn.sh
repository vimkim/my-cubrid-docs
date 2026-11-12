#!/bin/bash
# Auxiliary B of the latency handoff: per-row commit cost. One csql session runs N transactions that
# each UPDATE one row's OOS value and COMMIT. Values come from a staging table built before timing, so
# value computation is outside the timed part. Usage: oos_small_txn.sh INSTALL OUTDIR LABEL REPEAT
set -euo pipefail
install=$(realpath "${1:?}"); out=$(realpath -m "${2:?}"); label=${3:?}; rep=${4:?}
ROWS=${ROWS:-3000}; BYTES=${BYTES:-6000}
root="$out/$label-$rep"; mkdir -p "$root"
export CUBRID="$install" PATH="$install/bin:$PATH" LD_LIBRARY_PATH="$install/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
export CUBRID_DATABASES="$root" CUBRID_CONF_FILE="$root/cubrid.conf"
port=$((36000 + RANDOM % 2000))
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
touch "$root/databases.txt"; db=bench; cd "$root"
cubrid createdb --db-volume-size=1G --log-volume-size=512M -F "$root" $db en_US.utf8 > createdb.out 2>&1 </dev/null
cubrid server start $db > server_start.out 2>&1 </dev/null
trap 'cubrid server stop $db > server_stop.out 2>&1 </dev/null || true; cubrid service stop >/dev/null 2>&1 </dev/null || true' EXIT
q () { csql -C -u dba -c "$1" $db 2>&1 </dev/null; }
now () { date +%s.%N; }
val () { echo "CAST((SELECT GROUP_CONCAT(MD5(CONCAT(n.id, '-', $1, '-', k)) SEPARATOR '') FROM ks) AS BIT VARYING)"; }
q "CREATE TABLE nums (id INT); INSERT INTO nums SELECT ROWNUM FROM db_class a, db_class b, db_class c WHERE ROWNUM <= $ROWS; COMMIT;" > nums.out
q "CREATE TABLE ks (k INT); INSERT INTO ks SELECT ROWNUM FROM db_class a, db_class b WHERE ROWNUM <= $((BYTES * 2 / 32)); COMMIT;" > ks.out
q "CREATE TABLE t (id INT PRIMARY KEY, v BIT VARYING); INSERT INTO t SELECT n.id, $(val 0) FROM nums n; COMMIT;" > t.out
q "CREATE TABLE s (id INT PRIMARY KEY, v BIT VARYING); INSERT INTO s SELECT n.id, $(val 1) FROM nums n; COMMIT;" > s.out
sql="$root/small.sql"; : > "$sql"
for i in $(seq 1 $ROWS); do echo "UPDATE t SET v = (SELECT s.v FROM s WHERE s.id = $i) WHERE id = $i; COMMIT;" >> "$sql"; done
res="$out/results.csv"; [ -f "$res" ] || echo "label,rep,metric,value" > "$res"
t0=$(now); csql -C -u dba -i "$sql" $db > small.out 2>&1 </dev/null; t1=$(now)
grep -c "1 row affected" small.out > upd_count.out || true
echo "$label,$rep,small_update_sec,$(echo "$t1 - $t0" | bc)" >> "$res"
echo "$label,$rep,small_update_rows,$(cat upd_count.out)" >> "$res"
