#!/usr/bin/env bash
set -euo pipefail
w="${1:?}"
export CUBRID=/home/vimkim/.cub/install/CBRD-27259-storage-force-inline/debug_gcc
export PATH="$CUBRID/bin:$PATH" LD_LIBRARY_PATH="$CUBRID/lib:${LD_LIBRARY_PATH:-}" CUBRID_DATABASES="$w/dbs"
: > "$CUBRID_DATABASES/databases.txt"
cd "$w/db"
rm -f csql.err
cubrid createdb --db-volume-size=32M --log-volume-size=32M cf1 en_US.utf8 < /dev/null > createdb.out
python3 -I - > ins.sql <<'PY'
import random, string
r = random.Random(7)
print("create table t (id int, a varchar(30000) storage force_inline);")
for n in range(16150, 16230):
    s = ''.join(r.choice(string.ascii_letters + string.digits) for _ in range(n))
    print(f"insert into t values ({n}, '{s}');")
print("commit;")
PY
csql -S -u dba cf1 -i ins.sql < /dev/null > ins.out 2>&1
echo "notifications: $(grep -c 'CODE = -1393' csql.err 2>/dev/null || echo 0)"
grep -o 'needs [0-9]* bytes, more than the maximum record size ([0-9]* bytes)' csql.err | sort | uniq -c | head
cubrid diagdb -d 9 cf1 < /dev/null > diag.out 2>&1 || true
echo "diagdb BIGONE mentions: $(grep -ci bigone diag.out || true)"
grep -iE 'REC_BIGONE|BIGONE' diag.out | sort | uniq -c | head
cubrid deletedb cf1 < /dev/null
