#!/bin/bash
# Format discovery only: spacedb page-size line, the delimited extraction query, checkdb text.
set -u
root=/home/vimkim/.cub/campaign/cbrd-26659/ticket14
export CUBRID="/home/vimkim/.cub/install/oos-baseline-f4299ac0c/debug_gcc"
export PATH="$CUBRID/bin:$PATH"; export LD_LIBRARY_PATH="$CUBRID/lib:${LD_LIBRARY_PATH:-}"
export CUBRID_DATABASES="${root}/db"
db=t14fmt
cubrid server stop $db >/dev/null 2>&1; cubrid deletedb $db >/dev/null 2>&1
work="${root}/db/${db}"; rm -rf "$work"; mkdir -p "$work"; cd "$work" || exit 1
cubrid createdb --db-page-size=16384 --db-volume-size=32M --log-volume-size=32M "$db" en_US.utf8 >/dev/null
cubrid server start "$db" >/dev/null 2>&1
csql -u dba -c "CREATE TABLE f (id INT, v BIT VARYING);" "$db" >/dev/null 2>&1
csql -u dba --no-auto-commit -c "INSERT INTO f VALUES (1, CAST(REPEAT('AA',4036) AS BIT VARYING)); INSERT INTO f VALUES (2, CAST(REPEAT('BB',16284) AS BIT VARYING)); COMMIT;" "$db" >/dev/null 2>&1

echo "=== spacedb -S ==="
cubrid server stop "$db" >/dev/null 2>&1
cubrid spacedb -S -p "$db" 2>&1 | head -12
echo "spacedb rc=$?"
cubrid server start "$db" >/dev/null 2>&1

echo "=== extraction query ==="
csql -u dba -c "SELECT 'OOSROW|' || CAST(id AS VARCHAR) || '|' || MD5(v) || '|' || CAST(OCTET_LENGTH(v) AS VARCHAR) || '|' || CAST(BIT_LENGTH(v) AS VARCHAR) || '|' || CAST(DISK_SIZE(v) AS VARCHAR) || '|' || CAST(CASE WHEN v = CAST(REPEAT('AA',4036) AS BIT VARYING) THEN 1 ELSE 0 END AS VARCHAR) FROM f ORDER BY id;" "$db" 2>&1 | cat -A | head -20

echo "=== extraction, greppable ==="
csql -u dba -c "SELECT 'OOSROW|' || CAST(id AS VARCHAR) || '|' || MD5(v) || '|' || CAST(OCTET_LENGTH(v) AS VARCHAR) FROM f ORDER BY id;" "$db" 2>&1 | grep -o "OOSROW|[^']*"

echo "=== count query ==="
csql -u dba -c "SELECT 'CNT|' || CAST(COUNT(*) AS VARCHAR) FROM f;" "$db" 2>&1 | grep -o "CNT|[0-9]*"

echo "=== show heap oos row parse ==="
csql -u dba -c "SHOW HEAP OOS OF f;" "$db" 2>&1 | grep "dba.f" | awk '{print "has_oos="$6" pages="$9" pagesize="$10" recs="$11" sumlen="$12}'

echo "=== show heap oos on a missing table ==="
csql -u dba -c "SHOW HEAP OOS OF nosuchtable_t14;" "$db" 2>&1 | head -6; echo "rc=$?"

echo "=== checkdb ==="
cubrid server stop "$db" >/dev/null 2>&1
cubrid checkdb -S "$db" 2>&1 | head -6; echo "checkdb rc=${PIPESTATUS[0]}"

cubrid deletedb "$db" >/dev/null 2>&1
echo done
