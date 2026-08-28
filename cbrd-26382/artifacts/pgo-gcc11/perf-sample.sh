#!/usr/bin/env bash
# usage: perf-sample.sh <preset> <queries> <perf_out_file>
# Like run-sample.sh, but attaches perf stat to cub_server for the duration of
# the csql session. Appends one perf stat report per invocation.
set -euo pipefail
script_dir=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
preset=${1:?usage: perf-sample.sh <preset> <queries> <perf_out>}
queries=${2:?}
perf_out=${3:?}

SERVER_CPUS=${SERVER_CPUS:-22-29}
CLIENT_CPU=${CLIENT_CPU:-32}
db=pgobench
EVENTS=${EVENTS:-task-clock,cycles,instructions,branches,branch-misses,L1-icache-load-misses,iTLB-load-misses,idq.dsb_uops,idq.mite_uops}

# shellcheck source=/dev/null
source "$script_dir/env.sh" "$preset"

session_sql=$(mktemp)
cleanup ()
{
  rm -f "$session_sql"
  cubrid server stop "$db" >/dev/null 2>&1 || true
  cubrid service stop >/dev/null 2>&1 || true
}
trap cleanup EXIT

{
  echo ";time on"
  echo "SET TRACE OFF;"
  for _ in $(seq "$queries"); do
    echo "SELECT COUNT(*) FROM qa49 a, qa49 b, qa49 c, qa49 d, qa49 e;"
  done
} > "$session_sql"

taskset -c "$SERVER_CPUS" cubrid server start "$db" >/dev/null
server_pid=$(pgrep -f "[c]ub_server $db" | head -1)
[ -n "$server_pid" ] || { echo "no cub_server pid" >&2; exit 1; }

echo "## $preset $(date -Is) pid=$server_pid" >> "$perf_out"
perf stat -e "$EVENTS" -p "$server_pid" -o "$perf_out" --append -- \
  timeout "${CSQL_TIMEOUT:-900}" taskset -c "$CLIENT_CPU" csql -u dba "$db" -i "$session_sql" \
  | sed -n 's/.*row[s]* selected\. (\([0-9.]*\) sec).*/\1/p'

cubrid server stop "$db" >/dev/null
cubrid service stop >/dev/null 2>&1 || true
