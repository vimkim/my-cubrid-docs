#!/bin/bash
set -eu

db_name="sxaio_codex"
watch_output="watch-statdump.out"
watch_log="watch-statdump.log"
pid_file="watch-statdump.pid"

if test -e "$pid_file"; then
  echo "refusing to replace existing $pid_file" >&2
  exit 1
fi

setsid cubrid statdump -i 60 -o "$watch_output" "$db_name" >"$watch_log" 2>&1 &
watch_pid=$!
sleep 2

if ! kill -0 "$watch_pid" 2>/dev/null; then
  echo "statdump watcher failed to start" >&2
  exit 1
fi

watch_pgid=$(ps -o pgid= -p "$watch_pid" | tr -d ' ')
watch_start=$(awk '{ print $22 }' "/proc/$watch_pid/stat")
if test "$watch_pgid" != "$watch_pid"; then
  echo "statdump watcher did not become a process-group leader" >&2
  exit 1
fi

echo "$watch_pid $watch_start" >"$pid_file"

echo "watcher_started=$watch_pid"
