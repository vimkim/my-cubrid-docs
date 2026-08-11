#!/usr/bin/env bash
set -euo pipefail

src_db=ca27157q3srcf11
dst_db=ca27157q3dstf11
registry=/home/vimkim/.cub/db/feat-oos-fix-regression/commondb/databases.txt
cubrid_bin=/home/vimkim/.cub/install/feat-oos-fix-regression/debug_gcc/bin/cubrid
csql_bin=/home/vimkim/.cub/install/feat-oos-fix-regression/debug_gcc/bin/csql
quiz_dir=$(cd "$(dirname "$0")" && pwd)
run_dir=$(mktemp -d "$quiz_dir/.runtime.XXXXXX")
owned_src=0
owned_dst=0

stop_owned_db ()
{
  db_name=$1
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
}

cleanup ()
{
  status=$?
  trap - EXIT INT TERM
  if (( owned_dst == 1 ))
  then
    stop_owned_db "$dst_db"
    "$cubrid_bin" deletedb "$dst_db" >/dev/null 2>&1 || status=1
  fi
  if (( owned_src == 1 ))
  then
    stop_owned_db "$src_db"
    "$cubrid_bin" deletedb "$src_db" >/dev/null 2>&1 || status=1
  fi
  rm -rf -- "$run_dir"
  if (( owned_src == 1 ))
  then
    if awk -v name="$src_db" '$1 == name { found = 1 } END { exit !found }' "$registry" || ps -u "$(id -u)" -o comm=,args= | awk -v db="$src_db" '($1 == "cub_server" || $1 == "cub_pl") && $3 == db { found = 1 } END { exit !found }'
    then
      echo "CLEANUP_FAILED owned_db=$src_db" >&2
      status=1
    fi
  fi
  if (( owned_dst == 1 ))
  then
    if awk -v name="$dst_db" '$1 == name { found = 1 } END { exit !found }' "$registry" || ps -u "$(id -u)" -o comm=,args= | awk -v db="$dst_db" '($1 == "cub_server" || $1 == "cub_pl") && $3 == db { found = 1 } END { exit !found }'
    then
      echo "CLEANUP_FAILED owned_db=$dst_db" >&2
      status=1
    fi
  fi
  (( status == 0 && (owned_src == 1 || owned_dst == 1) )) && echo "CLEANUP_VERIFIED dbs=$src_db,$dst_db"
  exit "$status"
}
trap cleanup EXIT INT TERM

for db_name in "$src_db" "$dst_db"
do
  if awk -v name="$db_name" '$1 == name { found = 1 } END { exit !found }' "$registry"
  then
    echo "기존 DB를 보호하기 위해 중단합니다: $db_name" >&2
    exit 30
  fi
done

cd "$run_dir"
"$cubrid_bin" createdb --db-volume-size=64M "$src_db" en_US.utf8 >/dev/null
owned_src=1
"$cubrid_bin" server start "$src_db" > src-server-start.out 2> src-server-start.err < /dev/null
"$csql_bin" -C -u dba -i "$quiz_dir/source-data.sql" -t "$src_db" >/dev/null
"$cubrid_bin" unloaddb -u dba --CS-mode "$src_db" >/dev/null
"$cubrid_bin" server stop "$src_db" >/dev/null
test -s "${src_db}_schema"
test -s "${src_db}_objects"

"$cubrid_bin" createdb --db-volume-size=64M "$dst_db" en_US.utf8 >/dev/null
owned_dst=1
"$cubrid_bin" server start "$dst_db" > dst-server-start.out 2> dst-server-start.err < /dev/null
"$cubrid_bin" loaddb -C -u dba -s "${src_db}_schema" -d "${src_db}_objects" "$dst_db" > loaddb.out
cat loaddb.out "${dst_db}_loaddb.log" > loaddb-combined.out
grep -Eq 'Total 2 object\(s\) inserted, 0 object\(s\) failed' loaddb-combined.out
"$csql_bin" -C -u dba -i "$quiz_dir/exercise.sql" -t "$dst_db" > observer.out 2> observer.err
[[ ! -s observer.err ]]
grep -q 'small.*1' observer.out
grep -q 'large.*1' observer.out
grep -q "Class 'dba.small_inline' has no OOS file" observer.out
grep -q "OOS statistics for class 'dba.large_oos'" observer.out
grep -Eq 'Live OOS records[[:space:]]*:[[:space:]]*[1-9]' observer.out
echo 'PREDICATE_OK loaddb=2_inserted_0_failed small=no_oos_file large=oos_vfid_and_live_record values=match'
