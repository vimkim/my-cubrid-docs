#!/bin/bash
# CBRD-26659 ticket 16 -- run every site scenario in fault and control mode, sequentially, then stop the
# campaign master (port 26671) that the runs started. Only pids recorded by the runs are signalled.
set -u
T16=/home/vimkim/.cub/campaign/cbrd-26659/ticket16
LOG=$T16/sites/run-all.log
mkdir -p "$T16/sites"
: > "$LOG"
for site in a1 b1 c1 d1 e1 f1 g1 h1 i1 j1 k1 l1; do
  for mode in fault control; do
    echo "##### $(date -Is) $site $mode" >> "$LOG"
    bash "$T16/tools/t16_run.sh" "$site" "$mode" >> "$LOG" 2>&1
    echo "##### rc=$?" >> "$LOG"
  done
done
# stop the campaign master started by the runs: it must be a cub_master listening on 26671 and one of our recorded pids
MP=$(ss -ltnp 'sport = :26671' | grep -o 'pid=[0-9]*' | head -1 | cut -d= -f2)
if [ -n "$MP" ] && grep -qs "master_pid=$MP" "$T16"/sites/*/*/pids.txt && [ "$(ps -o comm= -p "$MP")" = cub_master ]; then
  kill -TERM "$MP" && echo "master pid $MP (port 26671) stopped" >> "$LOG"
else
  echo "no campaign master to stop (port 26671 holder: ${MP:-none})" >> "$LOG"
fi
echo "##### ALL DONE $(date -Is)" >> "$LOG"
