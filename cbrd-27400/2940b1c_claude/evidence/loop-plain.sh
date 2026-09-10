#!/bin/bash
# Run the scenario-7-only workload N times with no debugger attached; report cores per iteration.
set -u
N=${1:-10}
W=/home/vimkim/gh/cb/oos-bug-bts-4633/.scratch/bts4633
for i in $(seq 1 "$N"); do
  name=$(printf 'plain-s7-%02d' "$i")
  CASES_DIR=/mnt/shell-s7/cases REPRO_TIMEOUT=300 bash "$W/enter-plain.sh" "$name" > "$W/evidence/$name.console" 2>&1
  rc=$?
  cores=$(ls "$W/runtime/$name"/core* 2>/dev/null | wc -l)
  done_lines=$(grep -c 'Deadlock count' "$W/runtime/$name/java.log" 2>/dev/null || echo 0)
  echo "ITER $i name=$name rc=$rc cores=$cores deadlock_lines=$done_lines $(date +%T)"
done
echo "LOOP DONE"
