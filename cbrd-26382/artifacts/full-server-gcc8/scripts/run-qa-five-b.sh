#!/usr/bin/env bash
set -euo pipefail

container=cbrd26382-single
results=/home/vimkim/gh/cb/cbrd-26382-results/bench
raw=$results/raw
csv=$results/timings.csv
expected=282475249

exec_b ()
{
  podman exec \
    -e CUBRID=/opt/B \
    -e CUBRID_DATABASES=/bench/registry \
    -e PATH=/opt/B/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin \
    -e LD_LIBRARY_PATH=/opt/B/lib:/opt/B/cci/lib \
    "$container" "$@"
}

guard_host_quiet ()
{
  local phase=$1 compiler_count runnable
  compiler_count=$(pgrep -cx cc1plus || true)
  runnable=$(awk '{split($4, tasks, "/"); print tasks[1]}' /proc/loadavg)
  if [ "$compiler_count" -ne 0 ] || [ "$runnable" -gt 24 ]; then
    echo "host contention detected ($phase): cc1plus=$compiler_count runnable=$runnable" >&2
    exit 1
  fi
}

for run in 1 2 3 4 5; do
  stem=qa-five-0-$run-0-B
  log=$raw/$stem.log
  lifecycle=$raw/$stem.lifecycle.log
  stamp=$(date --iso-8601=seconds)
  guard_host_quiet "$stem/pre"
  exec_b bash -lc 'cubrid server start c26382' >"$lifecycle" 2>&1
  server_pid=$(podman exec "$container" pgrep -o cub_server)
  podman exec "$container" taskset -apc 3,4 "$server_pid" >>"$lifecycle" 2>&1

  set +e
  exec_b bash -lc 'taskset -c 5 csql -C -u dba -i /bench/query.sql c26382' >"$log" 2>&1
  query_status=$?
  set -e

  exec_b timeout 30 cubrid server stop c26382 >>"$lifecycle" 2>&1
  exec_b timeout 15 cub_commdb -A >>"$lifecycle" 2>&1
  guard_host_quiet "$stem/post"
  seconds=$(sed -n 's/^1 row selected\. (\([0-9.]*\) sec).*/\1/p' "$log")
  result=$(awk '/^[[:space:]]+[0-9]+[[:space:]]*$/ {gsub(/[[:space:]]/, ""); print; exit}' "$log")
  if [ "$query_status" -ne 0 ] || [ -z "$seconds" ] || [ "$result" != "$expected" ]; then
    echo "invalid B QA-view run $run: status=$query_status seconds=$seconds result=$result" >&2
    exit 1
  fi
  printf 'qa-five,0,%s,0,B,%s,%s,%s\n' "$run" "$seconds" "$result" "$stamp" >>"$csv"
  echo "qa-five B run=$run $seconds sec"
done
