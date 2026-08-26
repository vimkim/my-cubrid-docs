#!/usr/bin/env bash
set -euo pipefail

script_dir=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
# shellcheck source=runtime-common.sh
source "$script_dir/runtime-common.sh"
load_runtime_topology
validate_runtime_topology

root=$results_root/bench/pmu
mkdir -p "$root"
stage_query_file "$artifact_root/query.sql" "$container_query"

start_server ()
{
  local variant=$1 lifecycle=$2 server_pid
  exec_variant "$variant" cubrid server start "$database_name" >"$lifecycle" 2>&1
  server_pid=$(podman exec "$container" pgrep -o cub_server)
  podman exec "$container" taskset -apc "$server_cpus" "$server_pid" >>"$lifecycle" 2>&1
  podman top "$container" hpid pid comm \
    | awk -v pid="$server_pid" '$2 == pid && $3 == "cub_server" {print $1; exit}'
}

stop_server ()
{
  local variant=$1 lifecycle=$2
  exec_variant "$variant" timeout 30 cubrid server stop "$database_name" >>"$lifecycle" 2>&1
  exec_variant "$variant" timeout 15 cub_commdb -A >>"$lifecycle" 2>&1
  ! podman exec "$container" pgrep cub_server >>"$lifecycle" 2>&1
  ! podman exec "$container" pgrep cub_master >>"$lifecycle" 2>&1
}

run_stat ()
{
  local variant=$1 group=$2 repetition=$3 events=$4
  local stem lifecycle hpid status result install
  install=$container_install_root/$variant
  stem=$variant-$group-$repetition
  lifecycle=$root/$stem.lifecycle.log
  if [ -s "$root/$stem.perf.csv" ] && [ -s "$root/$stem.query.log" ]; then
    result=$(awk '/^[[:space:]]+[0-9]+[[:space:]]*$/ {gsub(/[[:space:]]/, ""); print; exit}' \
      "$root/$stem.query.log")
    if [ "$result" = "$expected_result" ]; then
      echo "skip completed $stem"
      return
    fi
  fi
  guard_host_quiet "$stem/pre"
  hpid=$(start_server "$variant" "$lifecycle")

  set +e
  perf stat -x, -o "$root/$stem.perf.csv" -e "$events" -p "$hpid" -- \
    podman exec \
      -e "CUBRID=$install" \
      -e "CUBRID_DATABASES=$container_registry" \
      -e "PATH=$install/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin" \
      -e "LD_LIBRARY_PATH=$install/lib:$install/cci/lib" \
      "$container" taskset -c "$client_cpu" \
      csql -C -u dba -i "$container_query" "$database_name" \
      >"$root/$stem.query.log" 2>&1
  status=$?
  set -e

  stop_server "$variant" "$lifecycle"
  guard_host_quiet "$stem/post"
  result=$(awk '/^[[:space:]]+[0-9]+[[:space:]]*$/ {gsub(/[[:space:]]/, ""); print; exit}' \
    "$root/$stem.query.log")
  if [ "$status" -ne 0 ] || [ "$result" != "$expected_result" ]; then
    echo "PMU run failed: $stem status=$status result=$result" >&2
    exit 1
  fi
  echo "completed $stem"
}

run_profile ()
{
  local variant=$1 lifecycle hpid status result install
  install=$container_install_root/$variant
  lifecycle=$root/$variant-profile.lifecycle.log
  if [ -s "$root/$variant-profile.perf.data" ] && [ -s "$root/$variant-profile.query.log" ]; then
    result=$(awk '/^[[:space:]]+[0-9]+[[:space:]]*$/ {gsub(/[[:space:]]/, ""); print; exit}' \
      "$root/$variant-profile.query.log")
    if [ "$result" = "$expected_result" ]; then
      echo "skip completed $variant-profile"
      return
    fi
  fi
  guard_host_quiet "$variant-profile/pre"
  hpid=$(start_server "$variant" "$lifecycle")
  cp "/proc/$hpid/maps" "$root/$variant-profile.maps"

  set +e
  perf record -F 999 --call-graph fp -p "$hpid" \
    -o "$root/$variant-profile.perf.data" -- \
    podman exec \
      -e "CUBRID=$install" \
      -e "CUBRID_DATABASES=$container_registry" \
      -e "PATH=$install/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin" \
      -e "LD_LIBRARY_PATH=$install/lib:$install/cci/lib" \
      "$container" taskset -c "$client_cpu" \
      csql -C -u dba -i "$container_query" "$database_name" \
      >"$root/$variant-profile.query.log" 2>&1
  status=$?
  set -e

  stop_server "$variant" "$lifecycle"
  guard_host_quiet "$variant-profile/post"
  result=$(awk '/^[[:space:]]+[0-9]+[[:space:]]*$/ {gsub(/[[:space:]]/, ""); print; exit}' \
    "$root/$variant-profile.query.log")
  if [ "$status" -ne 0 ] || [ "$result" != "$expected_result" ]; then
    echo "profile run failed: $variant status=$status result=$result" >&2
    exit 1
  fi
  echo "completed $variant-profile"
}

core_events='task-clock,context-switches,cpu-migrations,page-faults,cycles,instructions,ref-cycles'
branch_events='branch-instructions,branch-misses'
cache_events='cache-references,cache-misses'
l1d_events='L1-dcache-loads,L1-dcache-load-misses'
llc_events='LLC-loads,LLC-load-misses'
itlb_events='iTLB-loads,iTLB-load-misses'
l1i_events='L1-icache-load-misses'
frontend_events='idq_uops_not_delivered.core,icache_64b.iftag_miss,icache_64b.iftag_stall'
uopcache_events='idq.dsb_uops,idq.mite_uops,dsb2mite_switches.penalty_cycles,machine_clears.count'
frontendret_events='frontend_retired.l1i_miss,frontend_retired.dsb_miss'

for repetition in 1 2; do
  for variant in A B C qa-2029; do
    run_stat "$variant" core "$repetition" "$core_events"
    run_stat "$variant" branch "$repetition" "$branch_events"
    run_stat "$variant" cache "$repetition" "$cache_events"
    run_stat "$variant" l1d "$repetition" "$l1d_events"
    run_stat "$variant" llc "$repetition" "$llc_events"
    run_stat "$variant" itlb "$repetition" "$itlb_events"
    run_stat "$variant" l1i "$repetition" "$l1i_events"
    run_stat "$variant" frontend "$repetition" "$frontend_events"
    run_stat "$variant" uopcache "$repetition" "$uopcache_events"
    run_stat "$variant" frontendret "$repetition" "$frontendret_events"
  done
done

for variant in A B C qa-2029; do
  run_profile "$variant"
done
