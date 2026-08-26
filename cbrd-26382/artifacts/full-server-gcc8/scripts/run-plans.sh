#!/usr/bin/env bash
set -euo pipefail

container=cbrd26382-single
root=/home/vimkim/gh/cb/cbrd-26382-results/bench/plans
mkdir -p "$root"
podman cp /home/vimkim/gh/cb/CBRD-26382-scope-exit/.scratch/cbrd-26382-gcc8-follow-up/query-plan.sql \
  "$container:/bench/query-plan.sql"

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

for variant in qa-2029 A B C; do
  lifecycle=$root/$variant.lifecycle.log
  exec_variant "$variant" bash -lc 'cubrid server start c26382' >"$lifecycle" 2>&1
  server_pid=$(podman exec "$container" pgrep -o cub_server)
  podman exec "$container" taskset -apc 3,4 "$server_pid" >>"$lifecycle" 2>&1

  set +e
  exec_variant "$variant" bash -lc \
    'taskset -c 5 csql -C -u dba -i /bench/query-plan.sql c26382' >"$root/$variant.plan.log" 2>&1
  status=$?
  set -e

  exec_variant "$variant" timeout 30 cubrid server stop c26382 >>"$lifecycle" 2>&1
  exec_variant "$variant" timeout 15 cub_commdb -A >>"$lifecycle" 2>&1
  result=$(awk '/^[[:space:]]+[0-9]+[[:space:]]*$/ {gsub(/[[:space:]]/, ""); print; exit}' \
    "$root/$variant.plan.log")
  if [ "$status" -ne 0 ] || [ "$result" != 282475249 ]; then
    echo "plan capture failed: $variant status=$status result=$result" >&2
    exit 1
  fi
  echo "captured $variant"
done
