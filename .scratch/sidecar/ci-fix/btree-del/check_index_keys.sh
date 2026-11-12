#!/bin/bash
# Sidecar scenario: DELETE and UPDATE of rows whose indexed or partition-key values are in the store, in csql -S
# and csql -C, with force_external=yes and no.
# - t_c, t_s (cbrd_25122): SA_MODE deletes the hot record and its store records physically before
#   locator_delete_force_internal () reads the index keys, so that read must not go through store refs.
# - t_b: a multi-column key of 6000-byte values, built from a record that holds refs, must get a buffer for the
#   values, not for the refs.
# - t_p: a partition key in the store.
# Expects: no error or assertion, every row gone, checkdb clean.
# usage: check_index_keys.sh <cubrid worktree with .cub-workenv> <work dir>
set -u
WT=${1:?worktree}; WORK=${2:?work dir}
. "$WT/.cub-workenv/env.sh"
export CUBRID_ENABLE_STRING_COMPRESSION=no
fail=0
check() { if [ "$1" = 0 ]; then echo "PASS  $2"; else echo "FAIL  $2"; fail=1; fi; }

P=$(printf 'p%.0s' $(seq 200))
cat > "$WORK/load.sql" <<EOF
create table t_c (c_a char(255), c_b int, c_c int, c_d int);
create index i_c on t_c (c_a, c_b, c_c, c_d);
insert into t_c select 'a', 1, rownum, rownum from db_class a, db_class b limit 200;
insert into t_c select 'a', 2, rownum, rownum from db_class a, db_class b limit 50;
insert into t_c select 'a', 2, null, 1;
create table t_s (k varchar(300), v int);
create index i_s on t_s (k);
insert into t_s select repeat('k', 200) || rownum, rownum from db_class a, db_class b limit 100;
create table t_b (a varchar(9000), b int, c int);
create index i_b on t_b (a, b);
insert into t_b select repeat('x', 6000) || rownum, rownum, 0 from db_class limit 20;
create table t_p (k varchar(300), v int) partition by list (k) (
  partition p1 values in ('${P}1'), partition p2 values in ('${P}2'));
insert into t_p select repeat('p', 200) || (mod(rownum, 2) + 1), rownum from db_class a, db_class b limit 100;
EOF
cat > "$WORK/dml.sql" <<'EOF'
delete from t_c where c_a = 'a' and c_b = 2 and c_c is not null;
delete from t_c;
delete from t_s where v > 10;
delete from t_s;
update t_b set a = repeat('y', 6000) || b where b > 15;
update t_b set c = 1;
delete from t_b where b > 5;
delete from t_b;
delete from t_p;
select 'LEFT', (select count(*) from t_c) + (select count(*) from t_s) + (select count(*) from t_b)
  + (select count(*) from t_p);
EOF

run() {
  local force=$1 mode=$2 db=sckey_$1 dir=$WORK/$1$2
  rm -rf "${dir:?}"; mkdir -p "$dir"; cd "$dir" || exit 2
  cubrid deletedb "$db" </dev/null >/dev/null 2>&1
  export CUBRID_SIDECAR_FORCE_EXTERNAL=$force
  cubrid createdb -F "$dir" --db-volume-size=64M --log-volume-size=64M "$db" en_US.utf8 \
    </dev/null >create.log 2>&1 || { echo "createdb $force$mode failed"; exit 2; }
  csql -u dba -S -i "$WORK/load.sql" "$db" </dev/null >load.log 2>&1
  if [ "$mode" = C ]; then cubrid server start "$db" </dev/null >server.log 2>&1; fi
  csql -u dba "-$mode" -i "$WORK/dml.sql" "$db" </dev/null >dml.log 2>&1; echo $? >dml.rc
  if [ "$mode" = C ]; then
    cubrid server stop "$db" </dev/null >>server.log 2>&1
    cubrid service stop </dev/null >>server.log 2>&1
  fi
  cubrid checkdb -S "$db" </dev/null >checkdb.log 2>&1; echo $? >checkdb.rc
  cubrid deletedb "$db" </dev/null >/dev/null 2>&1
  unset CUBRID_SIDECAR_FORCE_EXTERNAL
}

for force in yes no; do
  for mode in S C; do
    run $force $mode
    d=$WORK/$force$mode
    ! grep -qE 'ERROR|Assertion' "$d/load.log" "$d/dml.log" && [ "$(cat "$d/dml.rc")" = 0 ]
    check $? "force_external=$force csql -$mode: the load and the DML run without error [$(grep -h -m1 -E 'ERROR|Assertion' "$d/load.log" "$d/dml.log")]"
    grep -Eq "^ *'LEFT' +0 *$" "$d/dml.log"
    check $? "force_external=$force csql -$mode: every row is gone"
    check "$(cat "$d/checkdb.rc")" "force_external=$force csql -$mode: checkdb is clean"
  done
done
exit $fail
