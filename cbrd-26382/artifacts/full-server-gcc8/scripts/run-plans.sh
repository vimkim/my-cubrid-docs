#!/usr/bin/env bash
set -euo pipefail

script_dir=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
# shellcheck source=runtime-common.sh
source "$script_dir/runtime-common.sh"
load_runtime_topology
validate_runtime_topology

root=$results_root/bench/plans
query_plan=$artifact_root/query-plan.sql
mkdir -p "$root"
stage_query_file "$query_plan" "$container_query_plan"

for variant in qa-2029 A B C; do
  lifecycle=$root/$variant.lifecycle.log
  exec_variant "$variant" cubrid server start "$database_name" >"$lifecycle" 2>&1
  server_pid=$(podman exec "$container" pgrep -o cub_server)
  podman exec "$container" taskset -apc "$server_cpus" "$server_pid" >>"$lifecycle" 2>&1

  set +e
  exec_variant "$variant" taskset -c "$client_cpu" \
    csql -C -u dba -i "$container_query_plan" "$database_name" >"$root/$variant.plan.log" 2>&1
  status=$?
  set -e

  exec_variant "$variant" timeout 30 cubrid server stop "$database_name" >>"$lifecycle" 2>&1
  exec_variant "$variant" timeout 15 cub_commdb -A >>"$lifecycle" 2>&1
  result=$(awk '/^[[:space:]]+[0-9]+[[:space:]]*$/ {gsub(/[[:space:]]/, ""); print; exit}' \
    "$root/$variant.plan.log")
  if [ "$status" -ne 0 ] || [ "$result" != "$expected_result" ]; then
    echo "plan capture failed: $variant status=$status result=$result" >&2
    exit 1
  fi
  echo "captured $variant"
done
