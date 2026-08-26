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
raw=$results/raw-pcores
csv=$results/qa-pcores-five.csv
mkdir -p "$raw"
stage_query_file "$artifact_root/query.sql" "$container_query"

if [ "${RESUME:-0}" != 1 ] || [ ! -f "$csv" ]; then
  printf 'series,run,variant,seconds,result,server_migrations,server_context_switches,timestamp\n' >"$csv"
fi

read_server_sched ()
{
  local server_pid=$1
  podman exec "$container" bash -lc '
    set -euo pipefail
    pid=$1
    awk "
      /se.nr_migrations[[:space:]]*:/ { migrations += \$3 }
      /^nr_switches[[:space:]]*:/ { switches += \$3 }
      END { printf \"%d %d\\n\", migrations, switches }
    " /proc/"$pid"/task/*/sched
  ' -- "$server_pid"
}

run_one ()
{
  local series=$1 run=$2 variant=$3
  local stem log lifecycle stamp server_pid query_status seconds result
  local migrations_before switches_before migrations_after switches_after

  stem=qa-pcores-${series}-${run}-${variant}
  log=$raw/$stem.log
  lifecycle=$raw/$stem.lifecycle.log
  stamp=$(date --iso-8601=seconds)

  if awk -F, -v s="$series" -v r="$run" -v v="$variant" \
    'NR > 1 && $1 == s && $2 == r && $3 == v { found = 1 } END { exit !found }' "$csv"; then
    echo "skip completed $stem"
    return
  fi

  guard_host_quiet "$stem/pre"
  exec_variant "$variant" cubrid server start "$database_name" >"$lifecycle" 2>&1
  server_pid=$(podman exec "$container" pgrep -o cub_server)
  podman exec "$container" taskset -apc "$p_core_cpus" "$server_pid" >>"$lifecycle" 2>&1
  read -r migrations_before switches_before < <(read_server_sched "$server_pid")

  set +e
  exec_variant "$variant" taskset -c "$p_core_cpus" \
    csql -C -u dba -i "$container_query" "$database_name" >"$log" 2>&1
  query_status=$?
  set -e
  read -r migrations_after switches_after < <(read_server_sched "$server_pid")

  exec_variant "$variant" timeout 30 cubrid server stop "$database_name" >>"$lifecycle" 2>&1
  exec_variant "$variant" timeout 15 cub_commdb -A >>"$lifecycle" 2>&1
  if podman exec "$container" pgrep cub_server >>"$lifecycle" 2>&1; then
    echo "server remains after stop for $variant" >&2
    exit 1
  fi
  if podman exec "$container" pgrep cub_master >>"$lifecycle" 2>&1; then
    echo "master remains after stop for $variant" >&2
    exit 1
  fi
  guard_host_quiet "$stem/post"

  seconds=$(sed -n 's/^1 row selected\. (\([0-9.]*\) sec).*/\1/p' "$log")
  result=$(awk '/^[[:space:]]+[0-9]+[[:space:]]*$/ {gsub(/[[:space:]]/, ""); print; exit}' "$log")
  if [ "$query_status" -ne 0 ] || [ -z "$seconds" ] || [ "$result" != "$expected_result" ]; then
    echo "invalid P-core run: variant=$variant run=$run status=$query_status seconds=$seconds result=$result" >&2
    exit 1
  fi

  printf '%s,%s,%s,%s,%s,%s,%s,%s\n' \
    "$series" "$run" "$variant" "$seconds" "$result" \
    "$((migrations_after - migrations_before))" "$((switches_after - switches_before))" "$stamp" >>"$csv"
  printf 'qa-pcores series=%s run=%s %s %s sec migrations=%s switches=%s\n' \
    "$series" "$run" "$variant" "$seconds" \
    "$((migrations_after - migrations_before))" "$((switches_after - switches_before))"
}

for run in 1 2 3 4 5; do
  run_one qa-first "$run" qa-2029
done
for run in 1 2 3 4 5; do
  run_one b-second "$run" B
done
for run in 1 2 3 4 5; do
  run_one b-first "$run" B
done
for run in 1 2 3 4 5; do
  run_one qa-second "$run" qa-2029
done
