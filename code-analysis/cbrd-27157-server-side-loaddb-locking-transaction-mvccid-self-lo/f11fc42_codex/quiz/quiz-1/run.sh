#!/usr/bin/env bash
set -euo pipefail

db_name=ca27157q1buf11
registry=/home/vimkim/.cub/db/feat-oos-fix-regression/commondb/databases.txt
cubrid_bin=/home/vimkim/.cub/install/feat-oos-fix-regression/debug_gcc/bin/cubrid
csql_bin=/home/vimkim/.cub/install/feat-oos-fix-regression/debug_gcc/bin/csql
quiz_dir=$(cd "$(dirname "$0")" && pwd)
run_dir=$(mktemp -d "$quiz_dir/.runtime.XXXXXX")
owned=0
bg_pids=()

cleanup ()
{
  status=$?
  trap - EXIT INT TERM
  if (( owned == 1 ))
  then
    for pid in "${bg_pids[@]}"
    do
      kill "$pid" >/dev/null 2>&1 || true
    done
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
    if awk -v name="$db_name" '$1 == name { found = 1 } END { exit !found }' "$registry"
    then
      echo "CLEANUP_FAILED registry=$db_name" >&2
      status=1
    fi
    if ps -u "$(id -u)" -o comm=,args= | awk -v db="$db_name" '($1 == "cub_server" || $1 == "cub_pl") && $3 == db { found = 1 } END { exit !found }'
    then
      echo "CLEANUP_FAILED process=$db_name" >&2
      status=1
    fi
    (( status == 0 )) && echo "CLEANUP_VERIFIED db=$db_name"
  fi
  rm -rf -- "$run_dir"
  exit "$status"
}
trap cleanup EXIT INT TERM

if awk -v name="$db_name" '$1 == name { found = 1 } END { exit !found }' "$registry"
then
  echo "기존 DB를 보호하기 위해 중단합니다: $db_name" >&2
  exit 30
fi

cd "$run_dir"
"$cubrid_bin" createdb --db-volume-size=64M "$db_name" en_US.utf8 >/dev/null
owned=1
"$cubrid_bin" server start "$db_name" > server-start.out 2> server-start.err < /dev/null
"$csql_bin" -C -u dba -i "$quiz_dir/setup.sql" -t "$db_name" >/dev/null

mkfifo data.fifo
(
  exec 4>data.fifo
  exec 4>&-
  exec 3>data.fifo
  printf '%%class [dba].[bu_target] ([id] [payload])\n' >&3
  touch class-sent
  sleep 5
  exec 3>&-
) &
writer_pid=$!
bg_pids+=("$writer_pid")
"$cubrid_bin" loaddb -C -u dba -d data.fifo "$db_name" > loaddb.out 2> loaddb.err &
loader_pid=$!
bg_pids+=("$loader_pid")

for attempt in $(seq 1 100)
do
  [[ -f class-sent ]] || { sleep 0.1; continue; }
  "$cubrid_bin" lockdb "$db_name" > bu-ready.out
  grep -q 'Class = dba.bu_target' bu-ready.out && grep -q 'BU_LOCK' bu-ready.out && break
  sleep 0.1
done
grep -q 'BU_LOCK' bu-ready.out

"$csql_bin" -C -u dba -i "$quiz_dir/exercise.sql" -t "$db_name" > observer.out 2> observer.err &
observer_pid=$!
bg_pids+=("$observer_pid")
for attempt in $(seq 1 50)
do
  "$cubrid_bin" lockdb -c "$db_name" > contention.out
  if grep -q 'Class = dba.bu_target' contention.out && grep -q 'BU_LOCK' contention.out && grep -q 'SCH_M_LOCK' contention.out
  then
    break
  fi
  sleep 0.1
done
grep -q 'BU_LOCK' contention.out
grep -q 'SCH_M_LOCK' contention.out
wait "$writer_pid"
wait "$loader_pid"
wait "$observer_pid"
[[ ! -s loaddb.err && ! -s observer.err ]]
grep -q 'after_bu' observer.out
echo 'PREDICATE_OK unrelated_update=success target_holder=BU_LOCK target_waiter=SCH_M_LOCK alter_after_release=success'
