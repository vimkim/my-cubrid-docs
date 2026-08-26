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
raw=$results/raw-padding-freshdb
csv=$results/padding-freshdb.csv
container_fresh_root=$container_bench_root/freshdb-work
repetitions=${FRESHDB_REPETITIONS:-3}
mkdir -p "$raw"
podman exec "$container" mkdir -p "$container_fresh_root"
stage_query_file "$artifact_root/query.sql" "$container_query"

if ! [[ "$repetitions" =~ ^[1-9][0-9]*$ ]]; then
  echo "FRESHDB_REPETITIONS must be a positive integer: $repetitions" >&2
  exit 2
fi

if [ "${RESUME:-0}" != 1 ] || [ ! -f "$csv" ]; then
  printf '%s\n' \
    'series,run,position,variant,seconds,result,migrations,switches,rchar,wchar,read_bytes,write_bytes,minflt,majflt,utime_ticks,stime_ticks,timestamp' \
    >"$csv"
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
  local variant_lower db_name db_dir stem log lifecycle stamp server_pid query_status service_stop_status seconds result index
  local -a before after delta

  variant_lower=${variant,,}
  db_name=f${run}${series##*-}${position}${variant_lower}
  db_dir=$container_fresh_root/$db_name
  stem=freshdb-${series}-${run}-${position}-${variant}
  log=$raw/$stem.log
  lifecycle=$raw/$stem.lifecycle.log
  stamp=$(date --iso-8601=seconds)

  if awk -F, -v s="$series" -v r="$run" -v p="$position" -v v="$variant" \
    'NR > 1 && $1 == s && $2 == r && $3 == p && $4 == v { found = 1 } END { exit !found }' "$csv"; then
    echo "skip completed $stem"
    return
  fi

  if podman exec "$container" test -e "$db_dir"; then
    echo "refusing to reuse existing fresh-DB directory: $db_dir" >&2
    exit 1
  fi

  guard_host_quiet "$stem/pre-create"
  podman exec "$container" mkdir "$db_dir"
  exec_variant "$variant" cubrid createdb -r "$db_name" en_US.utf8 \
    --db-volume-size=20m --log-volume-size=20m -F "$db_dir" -L "$db_dir" >"$lifecycle" 2>&1
  guard_host_quiet "$stem/pre-query"
  exec_variant "$variant" cubrid server start "$db_name" >>"$lifecycle" 2>&1
  server_pid=$(podman exec "$container" pgrep -o cub_server)
  podman exec "$container" taskset -apc "$p_core_cpus" "$server_pid" >>"$lifecycle" 2>&1
  read -r -a before < <(read_server_stats "$server_pid")

  set +e
  exec_variant "$variant" taskset -c "$p_core_cpus" \
    csql -C -u dba -i "$container_query" "$db_name" >"$log" 2>&1
  query_status=$?
  set -e
  read -r -a after < <(read_server_stats "$server_pid")

  set +e
  exec_variant "$variant" timeout 30 cubrid service stop >>"$lifecycle" 2>&1
  service_stop_status=$?
  set -e
  printf 'cubrid service stop status=%s (process-exit check is authoritative)\n' \
    "$service_stop_status" >>"$lifecycle"
  podman exec "$container" bash -lc '
    for attempt in $(seq 1 30); do
      if ! pgrep cub_server >/dev/null && ! pgrep cub_master >/dev/null; then
        exit 0
      fi
      sleep 0.5
    done
    exit 1
  ' >>"$lifecycle" 2>&1

  seconds=$(sed -n 's/^1 row selected\. (\([0-9.]*\) sec).*/\1/p' "$log")
  result=$(awk '/^[[:space:]]+[0-9]+[[:space:]]*$/ {gsub(/[[:space:]]/, ""); print; exit}' "$log")
  if [ "$query_status" -ne 0 ] || [ -z "$seconds" ] || [ "$result" != "$expected_result" ]; then
    echo "invalid fresh-DB run; preserving $db_dir: variant=$variant run=$run status=$query_status seconds=$seconds result=$result" >&2
    exit 1
  fi

  exec_variant "$variant" cubrid deletedb "$db_name" >>"$lifecycle" 2>&1
  podman exec "$container" rmdir "$db_dir/lob" "$db_dir"
  guard_host_quiet "$stem/post"

  for index in 0 1 2 3 4 5 6 7 8 9; do
    delta[$index]=$((after[index] - before[index]))
  done
  printf '%s,%s,%s,%s,%s,%s' "$series" "$run" "$position" "$variant" "$seconds" "$result" >>"$csv"
  printf ',%s' "${delta[@]}" >>"$csv"
  printf ',%s\n' "$stamp" >>"$csv"
  printf 'freshdb series=%s run=%s pos=%s %s %s sec read_bytes=%s majflt=%s\n' \
    "$series" "$run" "$position" "$variant" "$seconds" "${delta[4]}" "${delta[7]}"
}

for run in $(seq 1 "$repetitions"); do
  if [ $((run % 2)) -eq 1 ]; then
    orders=('A B D' 'B D A' 'D A B')
  else
    orders=('A D B' 'D B A' 'B A D')
  fi
  series=0
  for order in "${orders[@]}"; do
    series=$((series + 1))
    position=0
    for variant in $order; do
      position=$((position + 1))
      run_one "balanced-$series" "$run" "$position" "$variant"
    done
  done
done
