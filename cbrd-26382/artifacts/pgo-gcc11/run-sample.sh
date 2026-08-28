#!/usr/bin/env bash
# usage: run-sample.sh <preset> <queries_per_session> [outfile]
# Starts the server pinned to SERVER_CPUS, runs the QA query N times in one
# pinned csql session, appends per-query elapsed seconds to outfile, stops the
# server. Prints the elapsed values to stdout as well.
set -euo pipefail
script_dir=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
preset=${1:?usage: run-sample.sh <preset> <queries> [outfile]}
queries=${2:?usage: run-sample.sh <preset> <queries> [outfile]}
outfile=${3:-}

# Default to socket 1: other users' workloads were observed on socket 0.
SERVER_CPUS=${SERVER_CPUS:-22-29}
CLIENT_CPU=${CLIENT_CPU:-32}
db=pgobench

# shellcheck source=/dev/null
source "$script_dir/env.sh" "$preset"

session_sql=$(mktemp)
trap 'rm -f "$session_sql"' EXIT
{
  echo ";time on"
  echo "SET TRACE OFF;"
  for _ in $(seq "$queries"); do
    echo "SELECT COUNT(*) FROM qa49 a, qa49 b, qa49 c, qa49 d, qa49 e;"
  done
} > "$session_sql"

# This experiment's installs use a private cubrid_port_id so our cub_master
# never collides with other users' masters on this shared host.
cleanup_runtime ()
{
  cubrid server stop "$db" >/dev/null 2>&1 || true
  cubrid service stop >/dev/null 2>&1 || true
}
trap 'rm -f "$session_sql"; cleanup_runtime' EXIT

taskset -c "$SERVER_CPUS" cubrid server start "$db" >/dev/null

csql_out=$(timeout "${CSQL_TIMEOUT:-900}" taskset -c "$CLIENT_CPU" csql -u dba "$db" -i "$session_sql")

cubrid server stop "$db" >/dev/null
cubrid service stop >/dev/null 2>&1 || true

# csql prints per-statement timing as: "1 row selected. (39.384686 sec) ..."
elapsed=$(printf '%s\n' "$csql_out" | sed -n 's/.*row[s]* selected\. (\([0-9.]*\) sec).*/\1/p')
count_result=$(printf '%s\n' "$csql_out" | grep -Eo '^[[:space:]]*[0-9]{6,}' | head -1 | tr -d ' ')

if [ -z "$elapsed" ]; then
  echo "failed to parse elapsed time; raw csql output follows" >&2
  printf '%s\n' "$csql_out" >&2
  exit 1
fi

for value in $elapsed; do
  line="$preset,$value,$count_result,$(date -Is)"
  echo "$line"
  if [ -n "$outfile" ]; then
    echo "$line" >> "$outfile"
  fi
done
