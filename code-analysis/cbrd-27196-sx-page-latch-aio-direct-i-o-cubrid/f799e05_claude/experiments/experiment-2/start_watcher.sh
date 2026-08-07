#!/bin/bash
# experiment-2 setup: 통계 수집 watcher를 시작한다.
# CUBRID perfmon은 watcher(예: cubrid statdump)가 붙어 있는 동안에만 전역 카운터를
# 누적하므로(stats_on=no 기본값), flush 관측 전에 interval statdump를 붙여 둔다.
# watcher는 이 실험이 소유하며 stop_watcher.sh 가 정확히 이 PID만 종료한다.
set -eu
cd "$(dirname "$0")"
nohup cubrid statdump -i 60 -o watch.out sx_latch_lab > watch.log 2>&1 &
echo $! > watcher.pid
sleep 2
kill -0 "$(cat watcher.pid)"
echo "watcher started: pid=$(cat watcher.pid)"
