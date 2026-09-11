#!/bin/bash
# Exploration only: discover the OUTPUT FORMAT of the channels the ticket 14 case will
# parse (SHOW HEAP OOS columns, MD5 of a BIT VARYING, the crash/restart sequence, and
# whether the debug oos.log is written in client-server mode). No expected value of the
# case is taken from this run; the case's expectations are derived in
# derive_case_sizes.py and written into expected-oracle.md before the case runs.
set -u

mode="${1:-debug_gcc}"
root=/home/vimkim/.cub/campaign/cbrd-26659/ticket14
export CUBRID="/home/vimkim/.cub/install/oos-baseline-f4299ac0c/${mode}"
export PATH="$CUBRID/bin:$PATH"
export LD_LIBRARY_PATH="$CUBRID/lib:${LD_LIBRARY_PATH:-}"
export CUBRID_DATABASES="${root}/db"

db=t14probe
work="${root}/db/${db}"
rm -rf "${work}"; mkdir -p "${work}"; cd "${work}" || exit 1

echo "== identity =="
cubrid_rel
sha256sum "$CUBRID/lib/libcubrid.so" "$CUBRID/lib/libcubridsa.so"

echo "== createdb =="
cubrid createdb --db-page-size=16384 --db-volume-size=64M --log-volume-size=64M "$db" en_US.utf8
echo "createdb exit=$?"

echo "== paramdump (durability-relevant) =="
cubrid paramdump "$db" 2>&1 | grep -iE "async_commit|group_commit|auto_restart|dwb|log_max_archives" | head

echo "== start server =="
cubrid server start "$db"; echo "start exit=$?"

echo "== workload =="
csql -u dba -c "CREATE TABLE t14 (id INT, v BIT VARYING);" "$db"; echo "ddl exit=$?"
csql -u dba --no-auto-commit -c "
INSERT INTO t14 VALUES (1, CAST(REPEAT('AA', 4036) AS BIT VARYING));
INSERT INTO t14 VALUES (2, CAST(REPEAT('BB', 16284) AS BIT VARYING));
INSERT INTO t14 VALUES (3, CAST(REPEAT('CC', 4011) AS BIT VARYING));
COMMIT;
" "$db"; echo "insert exit=$?"

echo "== SHOW HEAP OOS format =="
csql -u dba -c "SHOW HEAP OOS OF t14;" "$db"
echo "show exit=$?"

echo "== MD5 / lengths format =="
csql -u dba -c "SELECT id, MD5(v), OCTET_LENGTH(v), BIT_LENGTH(v), DISK_SIZE(v) FROM t14 ORDER BY id;" "$db"

echo "== independently computed md5 =="
for n in 4036 16284 4011; do
  printf 'N=%s md5=%s\n' "$n" "$(python3 -c "import hashlib,sys;print(hashlib.md5(('aa'*int(sys.argv[1])).encode()).hexdigest())" "$n")"
done
echo "-- via coreutils for AA/BB/CC patterns --"
for p in aa bb cc; do
  case $p in aa) n=4036;; bb) n=16284;; cc) n=4011;; esac
  printf '%s x %s -> %s\n' "$p" "$n" "$(yes "$p" | head -n "$n" | tr -d '\n' | md5sum | cut -d' ' -f1)"
done

echo "== crash =="
pids=$(pgrep -f "cub_server ${db}")
echo "cub_server pids=[${pids}]"
for p in $pids; do kill -9 "$p"; done
sleep 2
echo "after kill: [$(pgrep -f "cub_server ${db}" | tr '\n' ' ')]"
echo "server status:"; cubrid server status

echo "== restart =="
cubrid server start "$db"; echo "restart exit=$?"
csql -u dba -c "SELECT COUNT(*) FROM t14;" "$db"
csql -u dba -c "SELECT id, MD5(v) FROM t14 ORDER BY id;" "$db"
csql -u dba -c "SHOW HEAP OOS OF t14;" "$db"

echo "== update + delete then vacuum-ish wait, oos.log check =="
csql -u dba --no-auto-commit -c "
UPDATE t14 SET v = CAST(REPEAT('EE', 4036) AS BIT VARYING) WHERE id = 1;
DELETE FROM t14 WHERE id = 3;
COMMIT;
" "$db"; echo "dml exit=$?"
sleep 3
echo "-- oos.log --"
ls -l "$CUBRID/log/oos.log" 2>&1
head -20 "$CUBRID/log/oos.log" 2>&1

echo "== standalone eager path =="
cubrid server stop "$db"; echo "stop exit=$?"
csql -u dba -S -c "UPDATE t14 SET v = CAST(REPEAT('FF', 4036) AS BIT VARYING) WHERE id = 1;" "$db"; echo "sa update exit=$?"
echo "-- oos.log after standalone update --"
ls -l "$CUBRID/log/oos.log" 2>&1
tail -20 "$CUBRID/log/oos.log" 2>&1

echo "== checkdb =="
cubrid checkdb -S "$db"; echo "checkdb exit=$?"

echo "== cleanup =="
cubrid server stop "$db" 2>/dev/null
cubrid deletedb "$db"; echo "deletedb exit=$?"
echo "done"
