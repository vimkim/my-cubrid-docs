#!/bin/bash
set -eu

db_name="sxaio_codex"
watch_output="watch-statdump.out"
pid_file="watch-statdump.pid"

if test -f "$pid_file"; then
  read -r watch_pid expected_start <"$pid_file"
  case "$watch_pid" in
    ''|*[!0-9]*)
      echo "invalid watcher ownership receipt" >&2
      exit 1
      ;;
  esac
  case "$expected_start" in
    ''|*[!0-9]*)
      echo "invalid watcher start-time receipt" >&2
      exit 1
      ;;
  esac
  if test -r "/proc/$watch_pid/stat"; then
    current_start=$(awk '{ print $22 }' "/proc/$watch_pid/stat")
    if test "$current_start" != "$expected_start"; then
      echo "watcher pid was reused; refusing to signal it" >&2
      exit 1
    fi
    kill -TERM -- "-$watch_pid" 2>/dev/null || true
  fi
fi

: "${watch_pid:?missing report-owned watcher receipt}"

attempt=0
while ps -eo pgid= | awk -v owned_pgid="$watch_pid" '$1 == owned_pgid { found = 1 } END { exit found ? 0 : 1 }'
do
  if test "$attempt" -ge 20; then
    break
  fi
  sleep 0.1
  attempt=$((attempt + 1))
done

if ps -eo pgid= | awk -v owned_pgid="$watch_pid" '$1 == owned_pgid { found = 1 } END { exit found ? 0 : 1 }'; then
  echo "report-owned statdump process group remains" >&2
  exit 1
fi

rm -f "$pid_file"
echo "watcher_stopped=1"
