#!/usr/bin/env bash
set -euo pipefail
[[ $# -eq 1 && $1 =~ ^[1-4]$ ]] || { echo "usage: owned-quiz-runner.sh QUIZ_NUMBER" >&2; exit 64; }
quiz_number="$1"
quiz_id="quiz-$quiz_number"
db_name="qalockq${quiz_number}f30"
report_dir=/home/vimkim/gh/my-cubrid-docs/code-analysis/lock-lock-manager-self-lock-mvcc-lock/f30f1c2_codex
source_revision=f30f1c26003e5aa8e93182648e06cad76fc77064
expected_dir="$report_dir/quiz/$quiz_id"
registry=/home/vimkim/.cub/db/cubrid-analysis/commondb/databases.txt
cubrid_bin=/home/vimkim/.cub/install/cubrid-analysis/debug_gcc/bin/cubrid
csql_bin=/home/vimkim/.cub/install/cubrid-analysis/debug_gcc/bin/csql
marker=.quiz-owner
runtime_dir="$expected_dir/runtime-owned"
volume_path="$runtime_dir/db"
log_path="$runtime_dir/log"
[[ $(pwd -P) == "$expected_dir" ]] || { echo "Run from $expected_dir" >&2; exit 72; }
[[ $(sha256sum "$csql_bin" | awk '{print $1}') == beb90bf72abab0334bf096d783bfef58608dbd21031daa4913cf93f137fdf722 ]] || { echo "Unexpected csql binary" >&2; exit 70; }
[[ $(sha256sum "$cubrid_bin" | awk '{print $1}') == 56ddaca924ecb6229a8f1c22b5322457a21a45a458e478c12a402f372ef53179 ]] || { echo "Unexpected cubrid binary" >&2; exit 71; }
if awk -v name="$db_name" '$1 == name { found = 1 } END { exit !found }' "$registry"
then
  echo "Refusing pre-existing database: $db_name" >&2
  exit 73
fi
[[ ! -e "$marker" && ! -e "$runtime_dir" ]] || { echo "Stale owned Quiz state" >&2; exit 74; }
mkdir -p raw-output
run_dir="$(mktemp -d "$expected_dir/raw-output/run.XXXXXX")"
mkdir -p "$volume_path" "$log_path"
nonce="$(date -u +%Y%m%dT%H%M%SZ)-$$"
write_marker ()
{
  local state_value="$1"
  {
    echo "state=$state_value"
    echo "quiz_id=$quiz_id"
    echo "db_name=$db_name"
    echo "report_dir=$report_dir"
    echo "source_revision=$source_revision"
    echo "registry=$registry"
    echo "volume_path=$volume_path"
    echo "log_path=$log_path"
    echo "run_dir=$run_dir"
    echo "nonce=$nonce"
  } >"$marker"
}
cleaned=0
session_a_pid=
session_b_pid=
validate_live_actor ()
{
  local actor_pid="$1"
  local actor_file="$2"
  local actor_cmdline
  [[ -n "$actor_pid" ]] || return 0
  if kill -0 "$actor_pid" 2>/dev/null
  then
    actor_cmdline="$(tr '\0' ' ' <"/proc/$actor_pid/cmdline")"
    [[ "$actor_cmdline" == *"$csql_bin"* && "$actor_cmdline" == *"-i $actor_file"* && "$actor_cmdline" == *"-t $db_name"* ]] || { echo "Refusing cleanup with unverified child PID $actor_pid" >&2; return 1; }
  fi
}
finish ()
{
  local exit_status="$?"
  if [[ "$cleaned" -eq 0 && -f "$marker" ]]
  then
    validate_live_actor "$session_a_pid" session-a.sql || exit 84
    validate_live_actor "$session_b_pid" session-b.sql || exit 84
    if ! bash cleanup.sh >>"$run_dir/emergency-cleanup.out" 2>>"$run_dir/emergency-cleanup.err"
    then
      echo "Emergency cleanup failed; ownership marker preserved" >&2
      exit 83
    fi
  fi
  exit "$exit_status"
}
trap finish EXIT
trap 'exit 130' INT
trap 'exit 143' TERM
write_marker reserved
"$cubrid_bin" createdb -F "$volume_path" -L "$log_path" --db-volume-size=64M --log-volume-size=64M "$db_name" en_US.utf8 >"$run_dir/createdb.out" 2>"$run_dir/createdb.err"
awk -v name="$db_name" -v volume="$volume_path" -v logdir="$log_path" '$1 == name && $2 == volume && $4 == logdir { found = 1 } END { exit !found }' "$registry" || { echo "Registry ownership mismatch" >&2; exit 75; }
write_marker created
"$cubrid_bin" server start "$db_name" >"$run_dir/server-start.out" 2>"$run_dir/server-start.err"
write_marker running
"$csql_bin" -C -u dba --no-auto-commit -i setup.sql -t "$db_name" >"$run_dir/setup.out" 2>"$run_dir/setup.err"
"$csql_bin" -C -u dba --no-auto-commit -i session-a.sql -t "$db_name" >"$run_dir/session-a.out" 2>"$run_dir/session-a.err" &
session_a_pid="$!"
readiness_raw="$run_dir/readiness.lockdb.txt"
sleep 2
kill -0 "$session_a_pid" 2>/dev/null || { echo "Session A ended before capture window" >&2; wait "$session_a_pid"; exit 76; }
"$cubrid_bin" lockdb "$db_name" >"$readiness_raw"
if [[ "$quiz_number" -ne 1 ]]
then
  "$csql_bin" -C -u dba --no-auto-commit -i session-b.sql -t "$db_name" >"$run_dir/session-b.out" 2>"$run_dir/session-b.err" &
  session_b_pid="$!"
  contention_raw="$run_dir/contention.lockdb.txt"
  sleep 2
  kill -0 "$session_a_pid" 2>/dev/null || { echo "Session A ended before contention capture" >&2; wait "$session_a_pid"; exit 77; }
  kill -0 "$session_b_pid" 2>/dev/null || { echo "Session B ended before contention capture" >&2; wait "$session_b_pid"; exit 77; }
  "$cubrid_bin" lockdb -c "$db_name" >"$contention_raw"
fi
wait "$session_a_pid"
if [[ "$quiz_number" -ne 1 ]]
then
  wait "$session_b_pid"
fi
"$cubrid_bin" lockdb -c "$db_name" >"$run_dir/post-release.lockdb.txt"
bash cleanup.sh >"$run_dir/cleanup.out" 2>"$run_dir/cleanup.err"
cleaned=1
echo "QUIZ_RUN_OK quiz=$quiz_id db=$db_name raw_output=$run_dir cleanup_verified=true"
