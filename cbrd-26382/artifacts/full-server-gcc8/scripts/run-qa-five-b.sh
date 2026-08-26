#!/usr/bin/env bash
set -euo pipefail

script_dir=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
# shellcheck source=runtime-common.sh
source "$script_dir/runtime-common.sh"
load_runtime_topology
validate_runtime_topology

results=$results_root/bench
raw=$results/raw
csv=$results/timings.csv
mkdir -p "$raw"
stage_query_file "$artifact_root/query.sql" "$container_query"

exec_b ()
{
  exec_variant B "$@"
}

for run in 1 2 3 4 5; do
  stem=qa-five-0-$run-0-B
  log=$raw/$stem.log
  lifecycle=$raw/$stem.lifecycle.log
  stamp=$(date --iso-8601=seconds)
  guard_host_quiet "$stem/pre"
  exec_b cubrid server start "$database_name" >"$lifecycle" 2>&1
  server_pid=$(podman exec "$container" pgrep -o cub_server)
  podman exec "$container" taskset -apc "$server_cpus" "$server_pid" >>"$lifecycle" 2>&1

  set +e
  exec_b taskset -c "$client_cpu" \
    csql -C -u dba -i "$container_query" "$database_name" >"$log" 2>&1
  query_status=$?
  set -e

  exec_b timeout 30 cubrid server stop "$database_name" >>"$lifecycle" 2>&1
  exec_b timeout 15 cub_commdb -A >>"$lifecycle" 2>&1
  guard_host_quiet "$stem/post"
  seconds=$(sed -n 's/^1 row selected\. (\([0-9.]*\) sec).*/\1/p' "$log")
  result=$(awk '/^[[:space:]]+[0-9]+[[:space:]]*$/ {gsub(/[[:space:]]/, ""); print; exit}' "$log")
  if [ "$query_status" -ne 0 ] || [ -z "$seconds" ] || [ "$result" != "$expected_result" ]; then
    echo "invalid B QA-view run $run: status=$query_status seconds=$seconds result=$result" >&2
    exit 1
  fi
  printf 'qa-five,0,%s,0,B,%s,%s,%s\n' "$run" "$seconds" "$result" "$stamp" >>"$csv"
  echo "qa-five B run=$run $seconds sec"
done
