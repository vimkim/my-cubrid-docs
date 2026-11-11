#!/bin/bash
# Stop cub_server under gdb at the moment a committed DROP TABLE is about to remove the table's LOB
# directory (the RVHF_LOB_REMOVE_DIR postpone), SIGKILL it there, restart, and report whether the table
# and its LOB files survived. Expected when the commit is durable before the removal: table gone.
# Data loss shape: table back after restart while its LOB files are gone.
# Usage: lob_crash.sh INSTALL OUTDIR LABEL
set -uo pipefail
install=$(realpath "${1:?}"); out=$(realpath -m "${2:?}"); label=${3:?}
root="$out/$label"; mkdir -p "$root"
export CUBRID="$install" PATH="$install/bin:$PATH" LD_LIBRARY_PATH="$install/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
export CUBRID_DATABASES="$root" CUBRID_CONF_FILE="$root/cubrid.conf"
port=$((40000 + RANDOM % 2000))
cat > "$CUBRID_CONF_FILE" <<CONF
[service]
service=server
[common]
cubrid_port_id=$port
data_buffer_size=128M
error_log_level=error
CONF
touch "$root/databases.txt"; db=lobdb; cd "$root"
cubrid createdb --db-volume-size=256M --log-volume-size=128M -F "$root" -B "$root/lob" $db en_US.utf8 > createdb.out 2>&1 </dev/null
cubrid server start $db > start.out 2>&1 </dev/null
csql -C -u dba -c "CREATE TABLE lt (a INT, b BLOB); INSERT INTO lt SELECT ROWNUM, BIT_TO_BLOB(X'0123456789abcdef0123456789abcdef') FROM db_class LIMIT 5; COMMIT;" $db > setup.out 2>&1 </dev/null
echo "lob files before: $(find "$root/lob" -type f | wc -l)"
pid=$(pgrep -u "$USER" -f "cub_server $db\$" | head -1)
gdb -p "$pid" -batch -ex 'set pagination off' -ex 'handle all nostop noprint pass' -ex 'handle SIGTRAP stop print nopass' \
  -ex 'break fileio_lob_remove_matching_dir' -ex 'continue' -ex 'bt 6' -ex 'finish' -ex 'kill' > gdb.out 2>&1 &
gpid=$!
until grep -q 'Breakpoint 1 at' gdb.out 2>/dev/null; do sleep 0.2; done; sleep 1
csql -C -u dba --no-auto-commit -c "DROP TABLE lt; COMMIT;" $db > drop.out 2>&1 </dev/null &
cpid=$!
wait "$gpid"; wait "$cpid"
grep -m1 'Breakpoint 1,' gdb.out; grep -E '^#[0-9]' gdb.out | head -12
echo "lob files after kill: $(find "$root/lob" -type f | wc -l)"
cubrid service stop > /dev/null 2>&1 </dev/null
pkill -9 -u "$USER" -f "cub_server $db\$" 2>/dev/null
cubrid server start $db > restart.out 2>&1 </dev/null
csql -C -u dba -c "SELECT COUNT(*) FROM db_class WHERE class_name = 'lt';" $db > check_table.out 2>&1 </dev/null
csql -C -u dba -c "SELECT a, BLOB_LENGTH(b) FROM lt;" $db > check_blob.out 2>&1 </dev/null
echo "table rows in db_class:"; grep -A2 '====' check_table.out | tail -1
echo "blob read:"; head -12 check_blob.out
echo "lob files after restart: $(find "$root/lob" -type f | wc -l)"
cubrid server stop $db > /dev/null 2>&1 </dev/null
cubrid checkdb -S $db > checkdb.out 2>&1 </dev/null; echo "checkdb rc=$?"
cubrid service stop > /dev/null 2>&1 </dev/null
