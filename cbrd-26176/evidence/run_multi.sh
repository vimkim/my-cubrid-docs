#!/bin/bash
# Run N concurrent csql CS-mode clients against bsdb.
set -eu
DIR="$(dirname "$0")"
NCLIENTS="${1:-8}"

csql -C -u dba bsdb -i "$DIR/setup_multi.sql" > "$DIR/setup_multi.out" 2>&1

start=$(date +%s.%N)
pids=()
for c in $(seq 1 "$NCLIENTS"); do
  csql -C -u dba bsdb -i "$DIR/worker_$c.sql" > "$DIR/worker_$c.out" 2>&1 &
  pids+=($!)
done
for p in "${pids[@]}"; do wait "$p"; done
end=$(date +%s.%N)
echo "all $NCLIENTS clients done in $(echo "$end $start" | awk '{printf "%.2f", $1-$2}')s"
csql -C -u dba bsdb -c "select count(*), count(distinct src) from bt_multi" 2>&1 | tail -8
