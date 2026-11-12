#!/usr/bin/env bash
# Does a counter-only UPDATE of _db_ha_apply_info rewrite the unchanged OOS copied_log_path as a new chain
# and reclaim the old one at commit? Prints OOS record counts before the UPDATE, inside the uncommitted
# transaction, and after commit. Usage: ha-apply-info.sh   (run from a CUBRID source worktree root)
# Environment: sources .cub-workenv/env.sh, which sets CUBRID, PATH and CUBRID_DATABASES for that
# worktree's install. Replace the source line with your own CUBRID environment if you do not have it.
set -uo pipefail
WT=$(git rev-parse --show-toplevel)
# shellcheck disable=SC1091
source "$WT/.cub-workenv/env.sh"
DB=haoosdb
DBDIR="$CUBRID_DATABASES/$DB"
OUT=$(dirname "$0")

cubrid server stop "$DB" >/dev/null 2>&1 </dev/null
cubrid deletedb "$DB" >/dev/null 2>&1 </dev/null
mkdir -p "$DBDIR"
(cd "$DBDIR" && cubrid createdb --db-page-size=4K --log-page-size=4K --db-volume-size=64M --log-volume-size=64M \
  "$DB" en_US.utf8 >/dev/null 2>&1 </dev/null) || { echo "createdb failed"; exit 1; }
cubrid server start "$DB" >/dev/null 2>&1 </dev/null || { echo "server start failed"; exit 1; }

oos_sql="show heap oos of _db_ha_apply_info;"
path="/$(head -c 4000 /dev/urandom | base64 -w0 | tr -dc 'A-Za-z0-9' | head -c 1000)"

csql --sysadm -u dba "$DB" -c "insert into _db_ha_apply_info (db_name, copied_log_path, committed_lsa_pageid, committed_lsa_offset, required_lsa_pageid, required_lsa_offset, insert_counter) values ('hadb', '$path', 1, 0, 1, 0, 0)" 2>&1 </dev/null | grep -E 'ERROR|row'
echo "== after insert"
csql -u dba "$DB" -l -c "$oos_sql" 2>&1 </dev/null | grep -E 'Oos_num_recs|ERROR'

cat >"$OUT/ha-txn.sql" <<EOF
update _db_ha_apply_info set insert_counter = insert_counter + 1, last_access_time = sys_datetime where db_name = 'hadb';
;line on
$oos_sql
commit;
$oos_sql
select insert_counter, if(copied_log_path = '$path', 'intact', 'CHANGED') from _db_ha_apply_info where db_name = 'hadb';
EOF
echo "== update inside one transaction, then commit (first count = before commit, second = after)"
csql --sysadm -u dba "$DB" --no-auto-commit -i "$OUT/ha-txn.sql" 2>&1 </dev/null | grep -E 'Oos_num_recs|intact|CHANGED|ERROR'
rm -f "$OUT/ha-txn.sql"
cubrid server stop "$DB" >/dev/null 2>&1 </dev/null
