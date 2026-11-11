#!/bin/bash
# Kill cub_server while a commit runs its postpone actions (one transaction drops NTAB tables, so its
# commit runs NTAB RVFL_DESTROY postpones), restart, and check that the commit is all-or-nothing,
# that an acknowledged commit survives, and that checkdb passes.
# Usage: postpone_crash.sh INSTALL OUTDIR LABEL ITERATIONS
set -uo pipefail
install=$(realpath "${1:?}"); out=$(realpath -m "${2:?}"); label=${3:?}; iters=${4:-20}
NTAB=${NTAB:-300}; MAXDELAY_MS=${MAXDELAY_MS:-40}
root="$out/$label"; mkdir -p "$root"
export CUBRID="$install" PATH="$install/bin:$PATH" LD_LIBRARY_PATH="$install/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
export CUBRID_DATABASES="$root" CUBRID_CONF_FILE="$root/cubrid.conf"
port=$((38000 + RANDOM % 2000))
cat > "$CUBRID_CONF_FILE" <<CONF
[service]
service=server
[common]
cubrid_port_id=$port
data_buffer_size=256M
error_log_level=error
CONF
touch "$root/databases.txt"; db=crashdb; cd "$root"
res="$out/results.csv"; [ -f "$res" ] || echo "label,iter,delay_ms,acked,tables_before,tables_left,checkdb_rc,restart_rc" > "$res"
cubrid createdb --db-volume-size=512M --log-volume-size=256M -F "$root" $db en_US.utf8 > createdb.out 2>&1 </dev/null
srv_pid () { pgrep -u "$USER" -f "cub_server $db\$" | head -1; }
count_tables () { csql -C -u dba -c "SELECT 'N=' || CAST(COUNT(*) AS VARCHAR) FROM db_class WHERE class_name LIKE 'pp\_%' ESCAPE '\\'" $db 2>/dev/null </dev/null | grep -o 'N=[0-9][0-9]*' | head -1 | cut -d= -f2; }
create="$root/create.sql"; drop="$root/drop.sql"; cleanup="$root/cleanup.sql"; : > "$create"; : > "$drop"; : > "$cleanup"
for t in $(seq 1 "$NTAB"); do
  echo "CREATE TABLE pp_$t (a INT PRIMARY KEY, b VARCHAR(100)); INSERT INTO pp_$t VALUES (1, 'x');" >> "$create"
  echo "DROP TABLE pp_$t;" >> "$drop"
  echo "DROP TABLE IF EXISTS pp_$t;" >> "$cleanup"
done
echo "COMMIT;" >> "$create"; printf 'COMMIT;\nSELECT '"'"'ACKED'"'"' FROM db_root;\n' >> "$drop"; echo "COMMIT;" >> "$cleanup"
for i in $(seq 1 "$iters"); do
  cubrid server start $db > start-$i.out 2>&1 </dev/null
  csql -C -u dba --no-auto-commit -i "$cleanup" $db > cleanup-$i.out 2>&1 </dev/null
  csql -C -u dba --no-auto-commit -i "$create" $db > create-$i.out 2>&1 </dev/null
  before=$(count_tables)
  delay=$(( (i * 7) % (MAXDELAY_MS + 1) ))
  pid=$(srv_pid)
  csql -C -u dba --no-auto-commit -i "$drop" $db > drop-$i.out 2>&1 </dev/null &
  cpid=$!
  while [ "$(grep -c 'Execute OK' drop-$i.out 2>/dev/null)" -lt "$NTAB" ]; do sleep 0.0005; done
  sleep "$(printf '0.%03d' "$delay")"
  kill -9 "$pid"; wait "$cpid" 2>/dev/null
  acked=0; grep -q "'ACKED'\|ACKED" drop-$i.out && acked=1
  cubrid service stop > /dev/null 2>&1 </dev/null
  cubrid server start $db > restart-$i.out 2>&1 </dev/null; rr=$?; grep -q 'is running' restart-$i.out && rr=0
  left=$(count_tables)
  cubrid server stop $db > stop-$i.out 2>&1 </dev/null
  cubrid checkdb -S $db > checkdb-$i.out 2>&1 </dev/null; cr=$?
  echo "$label,$i,$delay,$acked,$before,$left,$cr,$rr" >> "$res"
  verdict=ok
  { [ "$left" != 0 ] && [ "$left" != "$NTAB" ]; } && verdict=PARTIAL
  { [ "$acked" = 1 ] && [ "$left" != 0 ]; } && verdict=LOST_ACKED
  { [ "$cr" != 0 ] || [ "$rr" != 0 ]; } && verdict="$verdict,CHECK_FAIL"
  echo "iter $i delay=${delay}ms before=$before acked=$acked left=$left checkdb=$cr restart=$rr $verdict"
done
cubrid service stop > /dev/null 2>&1 </dev/null
