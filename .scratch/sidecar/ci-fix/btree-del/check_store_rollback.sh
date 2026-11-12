#!/bin/bash
# Sidecar scenario: repeated INSERTs of store values that a unique violation rolls back (cbrd_24771).
# The undo of a store insert must give the page's space back to the store's bestspace, so the next round reuses it.
# A store slot is used once (sidecar_read_store_record_at), so each rolled-back value still keeps its 4-byte slot.
# Expects, in csql -C and csql -S: rounds 2 to 10 grow the store by at most one extension of 4 pages, the step the
# store file was seen to grow by; before the fix it grew by about 4 pages a round.
# usage: check_store_rollback.sh <cubrid worktree with .cub-workenv> <work dir>
set -u
WT=${1:?worktree}; WORK=${2:?work dir}
. "$WT/.cub-workenv/env.sh"
export CUBRID_ENABLE_STRING_COMPRESSION=no CUBRID_SIDECAR_FORCE_EXTERNAL=yes
fail=0
check() { if [ "$1" = 0 ]; then echo "PASS  $2"; else echo "FAIL  $2"; fail=1; fi; }

cat > "$WORK/load.sql" <<'EOF'
create table t_r (id int primary key, v varchar(400));
insert into t_r select rownum, repeat('v', 300) || rownum from db_class a, db_class b limit 200;
create table t_src (id int, v varchar(400));
insert into t_src select rownum + 1000, repeat('w', 300) || rownum from db_class a, db_class b limit 200;
insert into t_src values (1, 'duplicate of a committed id');
EOF
echo "insert into t_r select * from t_src order by id desc;" > "$WORK/round.sql"

store_pages() {
  csql -u dba "-$1" -l -c "show heap sidecar of t_r" "$2" </dev/null 2>&1 | sed -n 's/^ *Num_pages *: *\([0-9]*\).*/\1/p'
}

run() {
  local mode=$1 db=scrb_$1 dir=$WORK/$1 first last
  rm -rf "${dir:?}"; mkdir -p "$dir"; cd "$dir" || exit 2
  cubrid deletedb "$db" </dev/null >/dev/null 2>&1
  cubrid createdb -F "$dir" --db-volume-size=64M --log-volume-size=64M "$db" en_US.utf8 \
    </dev/null >create.log 2>&1 || { echo "createdb $mode failed"; exit 2; }
  csql -u dba -S -i "$WORK/load.sql" "$db" </dev/null >load.log 2>&1
  if [ "$mode" = C ]; then cubrid server start "$db" </dev/null >server.log 2>&1; fi
  for i in $(seq 10); do
    csql -u dba "-$mode" -i "$WORK/round.sql" "$db" </dev/null >>round.log 2>&1
    echo "round $i store pages $(store_pages "$mode" "$db")" >> pages.log
  done
  if [ "$mode" = C ]; then
    cubrid server stop "$db" </dev/null >>server.log 2>&1
    cubrid service stop </dev/null >>server.log 2>&1
  fi
  first=$(awk 'NR==1 {print $5}' pages.log); last=$(awk 'END {print $5}' pages.log)
  violations=$(grep -c "Operation would have caused one or more unique constraint violations" round.log)
  [ "$violations" = 10 ]; check $? "csql -$mode: each of the 10 rounds fails on the unique key [$violations]"
  [ -n "$first" ] && [ -n "$last" ] && [ "$last" -le $((first + 4)) ]
  check $? "csql -$mode: the store reuses the pages the rollbacks free [round 1: $first, round 10: $last]"
  cubrid checkdb -S "$db" </dev/null >checkdb.log 2>&1
  check $? "csql -$mode: checkdb is clean"
  cubrid deletedb "$db" </dev/null >/dev/null 2>&1
}

run C
run S
exit $fail
