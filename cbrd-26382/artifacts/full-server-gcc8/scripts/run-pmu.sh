#!/usr/bin/env bash
set -euo pipefail

container=cbrd26382-single
root=/home/vimkim/gh/cb/cbrd-26382-results/bench/pmu
mkdir -p "$root"

guard_host_quiet ()
{
  local phase=$1 compiler_count runnable
  compiler_count=$(pgrep -cx cc1plus || true)
  runnable=$(awk '{split($4, tasks, "/"); print tasks[1]}' /proc/loadavg)
  if [ "$compiler_count" -ne 0 ] || [ "$runnable" -gt 80 ]; then
    echo "host contention detected ($phase): cc1plus=$compiler_count runnable=$runnable" >&2
    exit 1
  fi
}

exec_variant ()
{
  local variant=$1
  shift
  podman exec \
    -e "CUBRID=/opt/$variant" \
    -e CUBRID_DATABASES=/bench/registry \
    -e "PATH=/opt/$variant/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin" \
    -e "LD_LIBRARY_PATH=/opt/$variant/lib:/opt/$variant/cci/lib" \
    "$container" "$@"
}

start_server ()
{
  local variant=$1 lifecycle=$2 server_pid
  exec_variant "$variant" bash -lc 'cubrid server start c26382' >"$lifecycle" 2>&1
  server_pid=$(podman exec "$container" pgrep -o cub_server)
  podman exec "$container" taskset -apc 3,4 "$server_pid" >>"$lifecycle" 2>&1
  podman top "$container" hpid pid comm \
    | awk -v pid="$server_pid" '$2 == pid && $3 == "cub_server" {print $1; exit}'
}

stop_server ()
{
  local variant=$1 lifecycle=$2
  exec_variant "$variant" timeout 30 cubrid server stop c26382 >>"$lifecycle" 2>&1
  exec_variant "$variant" timeout 15 cub_commdb -A >>"$lifecycle" 2>&1
  ! podman exec "$container" pgrep cub_server >>"$lifecycle" 2>&1
  ! podman exec "$container" pgrep cub_master >>"$lifecycle" 2>&1
}

run_stat ()
{
  local variant=$1 group=$2 repetition=$3 events=$4
  local stem lifecycle hpid status result
  stem=$variant-$group-$repetition
  lifecycle=$root/$stem.lifecycle.log
  if [ -s "$root/$stem.perf.csv" ] && [ -s "$root/$stem.query.log" ]; then
    result=$(awk '/^[[:space:]]+[0-9]+[[:space:]]*$/ {gsub(/[[:space:]]/, ""); print; exit}' \
      "$root/$stem.query.log")
    if [ "$result" = 282475249 ]; then
      echo "skip completed $stem"
      return
    fi
  fi
  guard_host_quiet "$stem/pre"
  hpid=$(start_server "$variant" "$lifecycle")

  set +e
  perf stat -x, -o "$root/$stem.perf.csv" -e "$events" -p "$hpid" -- \
    podman exec \
      -e "CUBRID=/opt/$variant" \
      -e CUBRID_DATABASES=/bench/registry \
      -e "PATH=/opt/$variant/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin" \
      -e "LD_LIBRARY_PATH=/opt/$variant/lib:/opt/$variant/cci/lib" \
      "$container" bash -lc \
      'taskset -c 5 csql -C -u dba -i /bench/query.sql c26382' \
      >"$root/$stem.query.log" 2>&1
  status=$?
  set -e

  stop_server "$variant" "$lifecycle"
  guard_host_quiet "$stem/post"
  result=$(awk '/^[[:space:]]+[0-9]+[[:space:]]*$/ {gsub(/[[:space:]]/, ""); print; exit}' \
    "$root/$stem.query.log")
  if [ "$status" -ne 0 ] || [ "$result" != 282475249 ]; then
    echo "PMU run failed: $stem status=$status result=$result" >&2
    exit 1
  fi
  echo "completed $stem"
}

run_profile ()
{
  local variant=$1 lifecycle hpid status result
  lifecycle=$root/$variant-profile.lifecycle.log
  if [ -s "$root/$variant-profile.perf.data" ] && [ -s "$root/$variant-profile.query.log" ]; then
    result=$(awk '/^[[:space:]]+[0-9]+[[:space:]]*$/ {gsub(/[[:space:]]/, ""); print; exit}' \
      "$root/$variant-profile.query.log")
    if [ "$result" = 282475249 ]; then
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
      -e "CUBRID=/opt/$variant" \
      -e CUBRID_DATABASES=/bench/registry \
      -e "PATH=/opt/$variant/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin" \
      -e "LD_LIBRARY_PATH=/opt/$variant/lib:/opt/$variant/cci/lib" \
      "$container" bash -lc \
      'taskset -c 5 csql -C -u dba -i /bench/query.sql c26382' \
      >"$root/$variant-profile.query.log" 2>&1
  status=$?
  set -e

  stop_server "$variant" "$lifecycle"
  guard_host_quiet "$variant-profile/post"
  result=$(awk '/^[[:space:]]+[0-9]+[[:space:]]*$/ {gsub(/[[:space:]]/, ""); print; exit}' \
    "$root/$variant-profile.query.log")
  if [ "$status" -ne 0 ] || [ "$result" != 282475249 ]; then
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
