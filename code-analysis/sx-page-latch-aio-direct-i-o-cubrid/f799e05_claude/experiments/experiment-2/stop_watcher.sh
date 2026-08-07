#!/bin/bash
# experiment-2 cleanup: start_watcher.sh 가 기록한 PID의 statdump watcher만 종료한다.
set -eu
cd "$(dirname "$0")"
PID="$(cat watcher.pid)"
kill "$PID" 2>/dev/null || true
for i in 1 2 3 4 5; do
  if ! kill -0 "$PID" 2>/dev/null; then
    echo "watcher stopped: pid=$PID"
    exit 0
  fi
  sleep 1
done
echo "watcher still alive: pid=$PID" >&2
exit 1
