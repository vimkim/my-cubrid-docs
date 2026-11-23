#!/bin/bash
# A/B bulk DML benchmark. usage: run.sh REPS [ORDER...]
# Each rep: per variant, fresh tables, then timed statements. Records wall time and
# cub_server process-wide instructions:u / cycles:u during each statement.
set -u
BENCH=/mnt/nvme/data-5/tmp/claude-1000/-home-vimkim-gh-cb-develop/20b768f1-37f0-4831-a512-25dbba2cb615/scratchpad/bench
REPS=${1:-5}
OUT=$BENCH/results.csv
[ -f "$OUT" ] || echo "rep,variant,step,rows,wall_s,instructions,cycles" > "$OUT"

server_pid () { pgrep -f "cub_server benchdb" -a | awk -v c="$CUBRID" '{print $1}' | while read p; do
  [ "$(readlink /proc/$p/exe)" = "$CUBRID/bin/cub_server" ] && echo $p; done | head -1; }

wait_idle () { # wait until the server uses < 2% of one CPU over 1s (max 120 s)
  local pid=$1 i a b
  for i in $(seq 1 120); do
    a=$(awk '{print $14+$15}' /proc/$pid/stat); sleep 1; b=$(awk '{print $14+$15}' /proc/$pid/stat)
    [ $((b - a)) -le 2 ] && return 0
  done; echo "warn: not idle" >&2; }

sql () { csql -C -u dba -c "$1" benchdb > $BENCH/last_sql.out 2>&1 || { echo "SQL FAILED: $1" >&2; cat $BENCH/last_sql.out >&2; return 1; }; }

timed () { # rep variant step rows sql
  local pid=$(server_pid) f=$BENCH/perf.tmp t0 t1
  wait_idle $pid
  t0=$(date +%s.%N)
  perf stat -x, -e instructions:u,cycles:u -p $pid -o $f -- csql -C -u dba -c "$5" benchdb > $BENCH/last_sql.out 2>&1
  local rc=$?
  t1=$(date +%s.%N)
  [ $rc -eq 0 ] || { echo "FAILED $3" >&2; cat $BENCH/last_sql.out >&2; }
  local ins=$(awk -F, '/instructions/{print $1}' $f) cyc=$(awk -F, '/cycles/{print $1}' $f)
  echo "$1,$2,$3,$4,$(echo "$t1 - $t0" | bc),$ins,$cyc" >> $OUT
}

one_variant () { # rep variant
  source $BENCH/env.sh $2
  sql "drop table if exists t_in; drop table if exists t_oos; create table t_in (id int, s varchar(64), n int); create table t_oos (id int, big varchar(10000), n int);"
  timed $1 $2 ins_inline 1000000 "insert into t_in select id, 'val' || id, id from src;"
  timed $1 $2 upd_inline 1000000 "update t_in set n = n + 1;"
  timed $1 $2 ins_oos 100000 "insert into t_oos select id, id || repeat('x', 6000), id from src where id <= 100000;"
  timed $1 $2 upd_oos_n 100000 "update t_oos set n = n + 1;"
  timed $1 $2 upd_oos_big 20000 "update t_oos set big = big || 'y' where id <= 20000;"
}

for r in $(seq 1 $REPS); do
  if [ $((r % 2)) -eq 1 ]; then order="A B"; else order="B A"; fi
  for v in $order; do one_variant $r $v; done
  echo "rep $r done $(date +%T)" >&2
done
