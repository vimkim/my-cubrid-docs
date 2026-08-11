#!/usr/bin/env bash
set -euo pipefail

db_name=ca27157q3dstf11
registry=/home/vimkim/.cub/db/feat-oos-fix-regression/commondb/databases.txt
cubrid_bin=/home/vimkim/.cub/install/feat-oos-fix-regression/debug_gcc/bin/cubrid
quiz_dir=$(cd "$(dirname "$0")" && pwd)
run_dir=$(mktemp -d "$quiz_dir/.collision.XXXXXX")
owned=0

cleanup_collision ()
{
  status=$?
  trap - EXIT INT TERM
  if (( owned == 1 ))
  then
    "$cubrid_bin" server stop "$db_name" >/dev/null 2>&1 || true
    for pid in $(ps -u "$(id -u)" -o pid=,comm=,args= | awk -v db="$db_name" '($2 == "cub_server" || $2 == "cub_pl") && $4 == db { print $1 }')
    do
      kill -KILL "$pid" >/dev/null 2>&1 || true
    done
    for attempt in $(seq 1 50)
    do
      if ! ps -u "$(id -u)" -o comm=,args= | awk -v db="$db_name" '($1 == "cub_server" || $1 == "cub_pl") && $3 == db { found = 1 } END { exit !found }'
      then
        break
      fi
      sleep 0.1
    done
    "$cubrid_bin" deletedb "$db_name" >/dev/null 2>&1 || status=1
  fi
  rm -rf -- "$run_dir"
  if (( owned == 1 ))
  then
    ! awk -v name="$db_name" '$1 == name { found = 1 } END { exit !found }' "$registry" || status=1
    ! ps -u "$(id -u)" -o comm=,args= | awk -v db="$db_name" '($1 == "cub_server" || $1 == "cub_pl") && $3 == db { found = 1 } END { exit !found }' || status=1
    (( status == 0 )) && echo "COLLISION_TEST_CLEANUP_VERIFIED db=$db_name"
  fi
  exit "$status"
}
trap cleanup_collision EXIT INT TERM

if awk -v name="$db_name" '$1 == name { found = 1 } END { exit !found }' "$registry"
then
  echo "Collision test refuses an already pre-existing database: $db_name" >&2
  exit 71
fi

cd "$run_dir"
"$cubrid_bin" createdb --db-volume-size=64M "$db_name" en_US.utf8 >/dev/null
owned=1
"$cubrid_bin" server start "$db_name" > server-start.out 2> server-start.err < /dev/null
server_pid=
for attempt in $(seq 1 100)
do
  server_pid=$(ps -u "$(id -u)" -o pid=,comm=,args= | awk -v db="$db_name" '$2 == "cub_server" && $4 == db { print $1; exit }')
  [[ -n "$server_pid" ]] && break
  sleep 0.1
done
[[ -n "$server_pid" ]]
before_registry=$(awk -v name="$db_name" '$1 == name { print; exit }' "$registry")
[[ -n "$before_registry" ]]

set +e
"$quiz_dir/run.sh" > launcher.out 2> launcher.err
launcher_status=$?
set -e
[[ "$launcher_status" == 30 ]]
grep -q "기존 DB를 보호하기 위해 중단합니다: $db_name" launcher.err
after_registry=$(awk -v name="$db_name" '$1 == name { print; exit }' "$registry")
[[ "$after_registry" == "$before_registry" ]]
kill -0 "$server_pid"
cmdline=$(tr '\0' ' ' < "/proc/$server_pid/cmdline")
[[ "$cmdline" == "cub_server $db_name " ]]
echo "COLLISION_PRESERVED db=$db_name server_pid=$server_pid launcher_exit=$launcher_status registry_unchanged=yes"

