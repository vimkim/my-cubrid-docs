#!/bin/sh

set -eu

DB_NAME=testdb
DB_DIR="$CUBRID_DATABASES/$DB_NAME"
BASE_VOLUME="$DB_DIR/$DB_NAME"
OFF_TRACE=/tmp/cbrd-27093.dwb-off.trace
ON_TRACE=/tmp/cbrd-27093.dwb-on.trace
TRACE_PID=
CASE_SYNC_COUNT=0

stop_trace()
{
  if [ -n "$TRACE_PID" ]; then
    if kill -0 "$TRACE_PID" 2>/dev/null; then
      kill -TERM "$TRACE_PID"
    fi
    wait "$TRACE_PID" 2>/dev/null || true
    TRACE_PID=
  fi
}

cleanup()
{
  stop_trace
  cubrid server stop "$DB_NAME" >/dev/null 2>&1 || true
}

trap cleanup 0
trap 'exit 129' 1
trap 'exit 130' 2
trap 'exit 143' 15

wait_for_strace_attach()
{
  server_pid=$1
  attempts=0

  while [ "$attempts" -lt 100 ]; do
    if ! kill -0 "$TRACE_PID" 2>/dev/null; then
      echo "strace exited before attaching to cub_server" >&2
      return 1
    fi

    tracer_pid=$(awk '/^TracerPid:/ { print $2 }' "/proc/$server_pid/status")
    if [ "$tracer_pid" = "$TRACE_PID" ]; then
      return 0
    fi

    attempts=$((attempts + 1))
    sleep 0.05
  done

  echo "timed out waiting for strace to attach to cub_server PID $server_pid" >&2
  return 1
}

recreate_database()
{
  cubrid server stop "$DB_NAME" >/dev/null 2>&1 || true
  cubrid deletedb "$DB_NAME" >/dev/null 2>&1 || true
  mkdir -p "$DB_DIR"
  cubrid createdb --db-volume-size=20M --log-volume-size=20M \
    "$DB_NAME" en_US.utf8 -F "$DB_DIR"
}

load_workload()
{
  csql -u dba "$DB_NAME" -c "
DROP TABLE IF EXISTS t1;
CREATE TABLE t1 (a INT, b VARCHAR(200));
INSERT INTO t1
  SELECT ROWNUM, REPEAT('x', 200)
  FROM db_class x1, db_class x2, db_class x3
  LIMIT 100000;"
}

find_server_pid()
{
  server_pids=$(pgrep -f "cub_server $DB_NAME\$" || true)

  # Intentionally split pgrep's whitespace-separated PID list.
  set -- $server_pids
  if [ "$#" -ne 1 ]; then
    echo "expected one cub_server process for $DB_NAME, found $#" >&2
    return 1
  fi

  printf '%s\n' "$1"
}

run_case()
{
  label=$1
  dwb_size=$2
  trace_file=$3
  attach_log="${trace_file}.attach.log"

  echo
  echo "=== DWB $label (double_write_buffer_size=$dwb_size) ==="

  stop_trace
  cubrid server stop "$DB_NAME" >/dev/null 2>&1 || true
  ini.sh -s common "$CUBRID/conf/cubrid.conf" double_write_buffer_size "$dwb_size"
  cubrid server start "$DB_NAME"

  effective_dwb_size=$(
    cubrid paramdump -C "$DB_NAME" |
      sed -n 's/.*double_write_buffer_size=\([0-9][0-9]*\).*/\1/p'
  )
  if [ "$effective_dwb_size" != "$dwb_size" ]; then
    echo "expected double_write_buffer_size=$dwb_size, got ${effective_dwb_size:-unknown}" >&2
    return 1
  fi

  : > "$trace_file"
  : > "$attach_log"
  server_pid=$(find_server_pid)
  strace -f -y -e trace=fsync,fdatasync -p "$server_pid" \
    -o "$trace_file" 2>"$attach_log" &
  TRACE_PID=$!

  if ! wait_for_strace_attach "$server_pid"; then
    stop_trace
    sed -n '1,120p' "$attach_log" >&2
    return 1
  fi

  # DWB synchronizes data volumes while flushing this workload. Trace both the
  # workload and the explicit checkpoint so the enabled case is a valid control.
  load_workload
  echo ";checkpoint" | csql --sysadm -u dba "$DB_NAME"
  sleep 1
  stop_trace

  echo "--- sync calls by path ---"
  awk -F '[<>]' '
    NF >= 3 && $2 != "" { count[$2]++ }
    END {
      for (path in count) {
        print count[path], path
      }
    }
  ' "$trace_file" | sort -nr

  CASE_SYNC_COUNT=$(
    awk -F '[<>]' -v path="$BASE_VOLUME" '
      $2 == path { count++ }
      END { print count + 0 }
    ' "$trace_file"
  )
  echo "permanent base volume sync count: $CASE_SYNC_COUNT"

  cubrid server stop "$DB_NAME"
}

# A fresh database is needed only once. Both cases below reuse it and restart
# the server after changing the DWB setting.
ini.sh -s common "$CUBRID/conf/cubrid.conf" double_write_buffer_size 0
recreate_database

run_case off 0 "$OFF_TRACE"
off_sync_count=$CASE_SYNC_COUNT

run_case on 2097152 "$ON_TRACE"
on_sync_count=$CASE_SYNC_COUNT

echo
echo "=== CBRD-27093 result ==="
echo "DWB off permanent base volume sync count: $off_sync_count"
echo "DWB on  permanent base volume sync count: $on_sync_count"
echo "DWB off trace: $OFF_TRACE"
echo "DWB on  trace: $ON_TRACE"

if [ "$on_sync_count" -eq 0 ]; then
  echo "INVALID: the DWB-on control did not synchronize the permanent base volume" >&2
  exit 1
fi

if [ "$off_sync_count" -eq 0 ]; then
  echo "REPRODUCED: DWB-off checkpoint did not synchronize the permanent base volume"
else
  echo "NOT REPRODUCED: DWB-off checkpoint synchronized the permanent base volume"
fi
