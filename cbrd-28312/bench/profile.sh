#!/bin/bash
# Profile cub_server of variant $1 during each step; write perf.data per step.
set -u
BENCH=/mnt/nvme/data-5/tmp/claude-1000/-home-vimkim-gh-cb-develop/20b768f1-37f0-4831-a512-25dbba2cb615/scratchpad/bench
V=${1:?variant}
source $BENCH/env.sh $V
mkdir -p $BENCH/prof
pid=$(for p in $(pgrep -f "cub_server benchdb"); do [ "$(readlink /proc/$p/exe)" = "$CUBRID/bin/cub_server" ] && echo $p; done | head -1)
idle () { for i in $(seq 1 120); do a=$(awk '{print $14+$15}' /proc/$pid/stat); sleep 1; b=$(awk '{print $14+$15}' /proc/$pid/stat); [ $((b-a)) -le 2 ] && return; done; }
csql -C -u dba -c "drop table if exists t_in; drop table if exists t_oos; create table t_in (id int, s varchar(64), n int); create table t_oos (id int, big varchar(10000), n int);" benchdb >/dev/null
step () { idle; perf record -q -e instructions:u -c 200003 --call-graph lbr -p $pid -o $BENCH/prof/$V-$1.data -- csql -C -u dba -c "$2" benchdb > /dev/null 2>&1; }
step ins_inline "insert into t_in select id, 'val' || id, id from src;"
step upd_inline "update t_in set n = n + 1;"
step ins_oos "insert into t_oos select id, id || repeat('x', 6000), id from src where id <= 100000;"
step upd_oos_n "update t_oos set n = n + 1;"
step upd_oos_big "update t_oos set big = big || 'y' where id <= 20000;"
