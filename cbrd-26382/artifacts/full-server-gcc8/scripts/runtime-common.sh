#!/usr/bin/env bash

runtime_script_dir=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
artifact_root=$(realpath "$runtime_script_dir/..")

if [ -n "${RUNTIME_CONFIG:-}" ]; then
  if [ ! -f "$RUNTIME_CONFIG" ]; then
    echo "runtime config does not exist: $RUNTIME_CONFIG" >&2
    exit 2
  fi
  # The config is a user-owned shell fragment containing exported topology values.
  # shellcheck source=/dev/null
  source "$RUNTIME_CONFIG"
fi

require_setting ()
{
  local name=$1
  if [ -z "${!name:-}" ]; then
    echo "required setting is empty: $name" >&2
    exit 2
  fi
}

load_results_root ()
{
  require_setting RESULTS_ROOT
  results_root=$(realpath -m "$RESULTS_ROOT")
}

load_runtime_topology ()
{
  load_results_root
  require_setting CONTAINER_NAME
  require_setting SERVER_CPUS
  require_setting CLIENT_CPU

  container=$CONTAINER_NAME
  server_cpus=$SERVER_CPUS
  client_cpu=$CLIENT_CPU
  max_runnable=${MAX_RUNNABLE:-24}
  container_bench_root=${CONTAINER_BENCH_ROOT:-/bench}
  container_install_root=${CONTAINER_INSTALL_ROOT:-/opt}
  database_name=${DATABASE_NAME:-c26382}
  expected_result=${EXPECTED_RESULT:-282475249}
  container_registry=$container_bench_root/registry
  container_query=$container_bench_root/query.sql
  container_query_plan=$container_bench_root/query-plan.sql

  if ! [[ "$max_runnable" =~ ^[1-9][0-9]*$ ]]; then
    echo "MAX_RUNNABLE must be a positive integer: $max_runnable" >&2
    exit 2
  fi
  if ! [[ "$server_cpus" =~ ^[0-9]+([,-][0-9]+)*$ ]]; then
    echo "invalid taskset CPU list in SERVER_CPUS: $server_cpus" >&2
    exit 2
  fi
  if ! [[ "$client_cpu" =~ ^[0-9]+$ ]]; then
    echo "CLIENT_CPU must name exactly one logical CPU: $client_cpu" >&2
    exit 2
  fi
}

validate_runtime_topology ()
{
  podman container inspect "$container" >/dev/null
  podman exec "$container" taskset -c "$server_cpus" true
  podman exec "$container" taskset -c "$client_cpu" true
  podman exec "$container" test -d "$container_bench_root"
  podman exec "$container" test -d "$container_registry"
  podman exec "$container" test -f "$container_registry/databases.txt"
  for variant in ${RUNTIME_VARIANTS:-qa-2029 A B C}; do
    podman exec "$container" test -d "$container_install_root/$variant"
  done
}

stage_query_file ()
{
  local source=$1 destination=$2
  test -f "$source"
  podman cp "$source" "$container:$destination"
}

exec_variant ()
{
  local variant=$1 install
  shift
  install=$container_install_root/$variant
  podman exec \
    -e "CUBRID=$install" \
    -e "CUBRID_DATABASES=$container_registry" \
    -e "PATH=$install/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin" \
    -e "LD_LIBRARY_PATH=$install/lib:$install/cci/lib" \
    "$container" "$@"
}

guard_host_quiet ()
{
  local phase=$1 compiler_count runnable
  compiler_count=$(pgrep -cx cc1plus || true)
  runnable=$(awk '{split($4, tasks, "/"); print tasks[1]}' /proc/loadavg)
  if [ "$compiler_count" -ne 0 ] || [ "$runnable" -gt "$max_runnable" ]; then
    echo "host contention detected ($phase): cc1plus=$compiler_count runnable=$runnable limit=$max_runnable" >&2
    exit 1
  fi
}
