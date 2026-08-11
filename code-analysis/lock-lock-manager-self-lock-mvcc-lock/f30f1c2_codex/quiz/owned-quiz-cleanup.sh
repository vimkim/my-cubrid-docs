#!/usr/bin/env bash
set -euo pipefail
[[ $# -eq 1 && $1 =~ ^[1-4]$ ]] || { echo "usage: owned-quiz-cleanup.sh QUIZ_NUMBER" >&2; exit 64; }
quiz_number="$1"
quiz_id="quiz-$quiz_number"
db_name="qalockq${quiz_number}f30"
report_dir=/home/vimkim/gh/my-cubrid-docs/code-analysis/lock-lock-manager-self-lock-mvcc-lock/f30f1c2_codex
source_revision=f30f1c26003e5aa8e93182648e06cad76fc77064
expected_dir="$report_dir/quiz/$quiz_id"
registry=/home/vimkim/.cub/db/cubrid-analysis/commondb/databases.txt
cubrid_bin=/home/vimkim/.cub/install/cubrid-analysis/debug_gcc/bin/cubrid
marker=.quiz-owner
runtime_dir="$expected_dir/runtime-owned"
volume_path="$runtime_dir/db"
log_path="$runtime_dir/log"
[[ $(pwd -P) == "$expected_dir" && -f "$marker" ]] || { echo "Quiz ownership marker missing" >&2; exit 78; }
state_value="$(awk -F= '$1 == "state" { print $2 }' "$marker")"
[[ "$state_value" == reserved || "$state_value" == created || "$state_value" == running ]] || { echo "Invalid Quiz owner state" >&2; exit 79; }
grep -Fxq "quiz_id=$quiz_id" "$marker"
grep -Fxq "db_name=$db_name" "$marker"
grep -Fxq "report_dir=$report_dir" "$marker"
grep -Fxq "source_revision=$source_revision" "$marker"
grep -Fxq "registry=$registry" "$marker"
grep -Fxq "volume_path=$volume_path" "$marker"
grep -Fxq "log_path=$log_path" "$marker"
if awk -v name="$db_name" -v volume="$volume_path" -v logdir="$log_path" '$1 == name && $2 == volume && $4 == logdir { found = 1 } END { exit !found }' "$registry"
then
  if [[ "$state_value" == running ]]
  then
    "$cubrid_bin" server stop "$db_name"
  fi
  "$cubrid_bin" deletedb "$db_name"
elif awk -v name="$db_name" '$1 == name { found = 1 } END { exit !found }' "$registry"
then
  echo "Database name exists at a foreign path" >&2
  exit 80
elif [[ "$state_value" != reserved ]]
then
  echo "Owned registry row unexpectedly absent" >&2
  exit 81
fi
if awk -v name="$db_name" '$1 == name { found = 1 } END { exit !found }' "$registry"
then
  echo "Registry row survived cleanup" >&2
  exit 82
fi
for owned_dir in "$volume_path/lob" "$volume_path" "$log_path" "$runtime_dir"
do
  if [[ -d "$owned_dir" ]]
  then
    rmdir "$owned_dir"
  fi
done
rm -f "$marker"
echo "QUIZ_CLEANUP_OK quiz=$quiz_id db=$db_name prior_state=$state_value registry_absent=true"
