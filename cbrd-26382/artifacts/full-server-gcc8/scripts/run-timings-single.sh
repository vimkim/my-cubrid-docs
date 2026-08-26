#!/usr/bin/env bash
set -euo pipefail

container=cbrd26382-single
results=/home/vimkim/gh/cb/cbrd-26382-results/bench
raw=$results/raw
csv=$results/timings.csv
expected=282475249
mkdir -p "$raw"

if [ "${RESUME:-0}" != 1 ] || [ ! -f "$csv" ]; then
  printf 'phase,series,round,position,variant,seconds,result,timestamp\n' >"$csv"
fi

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

run_one ()
{
  local phase=$1 series=$2 round=$3 position=$4 variant=$5
  local stem stamp log lifecycle server_pid seconds result query_status
  stamp=$(date --iso-8601=seconds)
  stem=${phase}-${series}-${round}-${position}-${variant}
  log=$raw/$stem.log
  lifecycle=$raw/$stem.lifecycle.log

  if awk -F, -v p="$phase" -v s="$series" -v r="$round" -v o="$position" -v v="$variant" \
    'NR > 1 && $1 == p && $2 == s && $3 == r && $4 == o && $5 == v {found = 1} END {exit !found}' "$csv"; then
    echo "skip completed $stem"
    return
  fi

  guard_host_quiet "$stem/pre"
  exec_variant "$variant" bash -lc 'cubrid server start c26382' >"$lifecycle" 2>&1
  server_pid=$(podman exec "$container" pgrep -o cub_server)
  podman exec "$container" taskset -apc 3,4 "$server_pid" >>"$lifecycle" 2>&1

  set +e
  exec_variant "$variant" bash -lc \
    'taskset -c 5 csql -C -u dba -i /bench/query.sql c26382' >"$log" 2>&1
  query_status=$?
  set -e

  exec_variant "$variant" timeout 30 cubrid server stop c26382 >>"$lifecycle" 2>&1
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
  if [ "$query_status" -ne 0 ]; then
    echo "query failed for $variant in $log (status $query_status)" >&2
    exit "$query_status"
  fi

  seconds=$(sed -n 's/^1 row selected\. (\([0-9.]*\) sec).*/\1/p' "$log")
  result=$(awk '/^[[:space:]]+[0-9]+[[:space:]]*$/ {gsub(/[[:space:]]/, ""); print; exit}' "$log")
  if [ -z "$seconds" ] || [ "$result" != "$expected" ]; then
    echo "invalid result for $variant in $log: seconds=$seconds result=$result" >&2
    exit 1
  fi
  printf '%s,%s,%s,%s,%s,%s,%s,%s\n' \
    "$phase" "$series" "$round" "$position" "$variant" "$seconds" "$result" "$stamp" >>"$csv"
  printf '%s series=%s round=%s position=%s %s %s sec\n' \
    "$phase" "$series" "$round" "$position" "$variant" "$seconds"
}

for warmup in 1 2; do
  for variant in A B C qa-2029; do
    run_one warmup 0 "$warmup" 0 "$variant"
  done
done

for run in 1 2 3 4 5; do
  run_one qa-five 0 "$run" 0 qa-2029
done

permutations=(ABC ACB BAC BCA CAB CBA CBA CAB BCA BAC ACB ABC)
for series in 1 2 3 4 5; do
  for index in "${!permutations[@]}"; do
    round=$((index + 1))
    order=${permutations[$(((index + series - 1) % 12))]}
    for position in 1 2 3; do
      variant=${order:$((position - 1)):1}
      run_one randomized "$series" "$round" "$position" "$variant"
    done
  done
done
