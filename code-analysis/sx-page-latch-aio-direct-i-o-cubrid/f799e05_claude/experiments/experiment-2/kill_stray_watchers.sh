#!/bin/bash
# experiment-2 corrective cleanup: `cubrid statdump`는 wrapper가 실제 statdump를
# 자식으로 띄우므로 start_watcher.sh 의 watcher.pid 가 wrapper PID를 기록해
# stop_watcher.sh 가 자식을 놓칠 수 있다. 이 스크립트는 이 실험이 만든
# watcher만 — cmdline에 sx_latch_lab 과 우리의 출력 파일 이름(watch.out /
# watch_dry3.out)이 정확히 포함된 statdump 프로세스만 — 종료한다.
set -u
found=0
for pid in $(pgrep -f "statdump -i 60 -o .*watch(_dry3)?\.out sx_latch_lab" || true); do
  cmdline="$(tr '\0' ' ' < /proc/$pid/cmdline 2>/dev/null || true)"
  case "$cmdline" in
    *"statdump -i 60 -o "*"watch.out sx_latch_lab"*|*"statdump -i 60 -o "*"watch_dry3.out sx_latch_lab"*)
      echo "killing experiment-owned watcher pid=$pid cmd=$cmdline"
      kill "$pid" 2>/dev/null || true
      found=1
      ;;
  esac
done
sleep 2
remaining="$(pgrep -f "statdump -i 60 -o .*watch(_dry3)?\.out sx_latch_lab" | wc -l || true)"
echo "remaining=$remaining found_any=$found"
[ "$remaining" -eq 0 ]
