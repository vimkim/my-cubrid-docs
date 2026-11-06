#!/usr/bin/env bash
set -euo pipefail
w="${1:?}"
export CUBRID=/home/vimkim/.cub/install/CBRD-27259-storage-force-inline/debug_gcc
export PATH="$CUBRID/bin:$PATH" LD_LIBRARY_PATH="$CUBRID/lib:${LD_LIBRARY_PATH:-}" CUBRID_DATABASES="$w/dbs"
: > "$CUBRID_DATABASES/databases.txt"
mkdir -p "$w/db2"; cd "$w/db2"
cubrid createdb --db-volume-size=32M --log-volume-size=32M cs1 en_US.utf8 < /dev/null > createdb.out
hex=$(python3 -I -c "import random;r=random.Random(3);print(''.join('%02x'%r.randrange(256) for _ in range(17000)))")
csql -S -u dba cs1 -c "create table q (id int primary key, a bit varying storage force_inline); commit;" < /dev/null
run () {
  local label="$1" sql="$2" before after
  before=$(grep -c 'CODE = -1393' csql.err 2>/dev/null || true); before=${before:-0}
  csql -S -u dba cs1 -c "$sql" < /dev/null > "out_$label.txt" 2>&1 || true
  after=$(grep -c 'CODE = -1393' csql.err 2>/dev/null || true); after=${after:-0}
  echo "$label: reports=$((after - before)) $(grep -m1 -o 'ERROR.*' "out_$label.txt" || true)"
}
run insert_new "insert into q values (1, X'$hex'); commit;"
run replace_existing "replace into q values (1, X'$hex'); commit;"
run insert_dup "insert into q values (1, X'$hex'); commit;"
csql -S -u dba cs1 -c "select count(*) from q" < /dev/null | grep -E '^ +[0-9]+'
cubrid deletedb cs1 < /dev/null
