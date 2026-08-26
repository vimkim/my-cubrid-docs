#!/usr/bin/env bash
set -euo pipefail

script_dir=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
# shellcheck source=runtime-common.sh
source "$script_dir/runtime-common.sh"
load_runtime_topology
validate_runtime_topology
require_setting P_CORE_CPUS

p_core_cpus=$P_CORE_CPUS
if ! [[ "$p_core_cpus" =~ ^[0-9]+([,-][0-9]+)*$ ]]; then
  echo "invalid taskset CPU list in P_CORE_CPUS: $p_core_cpus" >&2
  exit 2
fi
podman exec "$container" taskset -c "$p_core_cpus" true

results=$results_root/bench
raw=$results/raw-pcores-io
csv=$results/pcores-io.csv
mkdir -p "$raw"
stage_query_file "$artifact_root/query.sql" "$container_query"

if [ "${RESUME:-0}" != 1 ] || [ ! -f "$csv" ]; then
  printf '%s\n' 'series,run,position,variant,seconds,result,migrations,switches,rchar,wchar,read_bytes,write_bytes,minflt,majflt,utime_ticks,stime_ticks,timestamp' >"$csv"
fi

read_server_stats ()
{
  local server_pid=$1
  podman exec "$container" bash -lc '
    set -euo pipefail
    pid=$1
    read -r migrations switches < <(awk "
      /se.nr_migrations[[:space:]]*:/ { migrations += \$3 }
      /^nr_switches[[:space:]]*:/ { switches += \$3 }
      END { printf \"%d %d\\n\", migrations, switches }
    " /proc/"$pid"/task/*/sched)
    read -r rchar wchar read_bytes write_bytes < <(awk "
      /^rchar:/ { rchar = \$2 }
      /^wchar:/ { wchar = \$2 }
      /^read_bytes:/ { read_bytes = \$2 }
      /^write_bytes:/ { write_bytes = \$2 }
      END { printf \"%d %d %d %d\\n\", rchar, wchar, read_bytes, write_bytes }
    " /proc/"$pid"/io)
    read -r minflt majflt utime stime < <(awk "{ print \$10, \$12, \$14, \$15 }" /proc/"$pid"/stat)
    printf "%s %s %s %s %s %s %s %s %s %s\\n" \
      "$migrations" "$switches" "$rchar" "$wchar" "$read_bytes" "$write_bytes" \
      "$minflt" "$majflt" "$utime" "$stime"
  ' -- "$server_pid"
}

run_one ()
{
  local series=$1 run=$2 position=$3 variant=$4
  local stem log lifecycle stamp server_pid query_status seconds result
  local -a before after delta

  stem=pcores-io-${series}-${run}-${position}-${variant}
  log=$raw/$stem.log
  lifecycle=$raw/$stem.lifecycle.log
  stamp=$(date --iso-8601=seconds)

  if awk -F, -v s="$series" -v r="$run" -v p="$position" -v v="$variant" \
    'NR > 1 && $1 == s && $2 == r && $3 == p && $4 == v { found = 1 } END { exit !found }' "$csv"; then
    echo "skip completed $stem"
    return
  fi

  guard_host_quiet "$stem/pre"
  exec_variant "$variant" cubrid server start "$database_name" >"$lifecycle" 2>&1
  server_pid=$(podman exec "$container" pgrep -o cub_server)
  podman exec "$container" taskset -apc "$p_core_cpus" "$server_pid" >>"$lifecycle" 2>&1
  read -r -a before < <(read_server_stats "$server_pid")

  set +e
  exec_variant "$variant" taskset -c "$p_core_cpus" \
    csql -C -u dba -i "$container_query" "$database_name" >"$log" 2>&1
  query_status=$?
  set -e
  read -r -a after < <(read_server_stats "$server_pid")

  exec_variant "$variant" timeout 30 cubrid server stop "$database_name" >>"$lifecycle" 2>&1
  exec_variant "$variant" timeout 15 cub_commdb -A >>"$lifecycle" 2>&1
  ! podman exec "$container" pgrep cub_server >>"$lifecycle" 2>&1
  ! podman exec "$container" pgrep cub_master >>"$lifecycle" 2>&1
  guard_host_quiet "$stem/post"

  seconds=$(sed -n 's/^1 row selected\. (\([0-9.]*\) sec).*/\1/p' "$log")
  result=$(awk '/^[[:space:]]+[0-9]+[[:space:]]*$/ {gsub(/[[:space:]]/, ""); print; exit}' "$log")
  if [ "$query_status" -ne 0 ] || [ -z "$seconds" ] || [ "$result" != "$expected_result" ]; then
    echo "invalid P-core I/O run: variant=$variant run=$run status=$query_status seconds=$seconds result=$result" >&2
    exit 1
  fi

  for index in 0 1 2 3 4 5 6 7 8 9; do
    delta[$index]=$((after[index] - before[index]))
  done
  printf '%s,%s,%s,%s,%s,%s' "$series" "$run" "$position" "$variant" "$seconds" "$result" >>"$csv"
  printf ',%s' "${delta[@]}" >>"$csv"
  printf ',%s\n' "$stamp" >>"$csv"
  printf 'pcores-io series=%s run=%s pos=%s %s %s sec read_bytes=%s minflt=%s cpu_ticks=%s\n' \
    "$series" "$run" "$position" "$variant" "$seconds" \
    "${delta[4]}" "${delta[6]}" "$((delta[8] + delta[9]))"
}

for run in 1 2 3 4 5; do
  position=0
  for variant in qa-2029 A B C; do
    position=$((position + 1))
    run_one forward "$run" "$position" "$variant"
  done
  position=0
  for variant in C B A qa-2029; do
    position=$((position + 1))
    run_one reverse "$run" "$position" "$variant"
  done
done
