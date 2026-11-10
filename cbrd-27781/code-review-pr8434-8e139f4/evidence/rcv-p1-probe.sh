#!/bin/bash
# RCV-P1 coordinator probe: restart undo of an uncommitted multi-chunk OOS insert (new RVOOS_INSERT undo image).
# Run from the CUBRID worktree through `direnv exec .`. Uses its own database under a scratch directory.
set -u
OUT=${1:?output dir}
DB=rcvp1db
DBDIR=$OUT/db
mkdir -p "$DBDIR"
exec > "$OUT/probe.log" 2>&1
set -x
cubrid --version
cubrid deletedb "$DB" </dev/null >/dev/null 2>&1
(cd "$DBDIR" && cubrid createdb --db-volume-size=64M --log-volume-size=64M "$DB" en_US.utf8 </dev/null)
cubrid server start "$DB" </dev/null >"$OUT/start1.out" 2>&1
csql -u dba "$DB" -c "create table t (id int primary key, v varchar); create table w (id int);" </dev/null

# Loser: autocommit off, a 200 KB value (several OOS chunks), then sleep with the transaction open.
csql -u dba --no-auto-commit "$DB" -c "insert into t values (1, repeat('L', 200000)); select sleep(120);" </dev/null >"$OUT/loser.out" 2>&1 &
LOSER=$!
sleep 8
# Winner: a committed insert forces the log (group commit) past the loser's records.
csql -u dba "$DB" -c "insert into w values (2); insert into t values (3, repeat('W', 200000));" </dev/null
sleep 2
SPID=$(pgrep -f "cub_server $DB" | head -1)
echo "server pid $SPID"
kill -9 "$SPID"
wait "$LOSER"
sleep 2
cubrid server start "$DB" </dev/null >"$OUT/start2.out" 2>&1
echo "restart exit $?"
csql -u dba "$DB" -c "select id, length(v) from t order by id; select count(*) from w;" </dev/null
csql -u dba "$DB" -c "insert into t values (4, repeat('N', 200000)); select id, length(v) from t order by id;" </dev/null
cubrid server stop "$DB" </dev/null
cubrid checkdb -S "$DB" </dev/null
echo "checkdb exit $?"
grep -iE "assert|fatal|error" $CUBRID/log/server/${DB}_*.err 2>/dev/null | tail -20
cubrid deletedb "$DB" </dev/null
