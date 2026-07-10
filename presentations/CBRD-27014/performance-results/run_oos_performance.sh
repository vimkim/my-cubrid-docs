#!/usr/bin/env bash
# Controlled CBRD-27014 OOS benchmark runner. It owns only the perf27014 DB.
set -Eeuo pipefail
shopt -s inherit_errexit

readonly ROOT="/home/vimkim/gh/my-cubrid-docs/presentations/CBRD-27014"
readonly RESULTS_ROOT="$ROOT/performance-results"
readonly SETUP_SQL="$ROOT/oos-performance-setup.sql"
readonly DB_NAME="perf27014"
readonly ROWS=100000
readonly PAYLOAD_BITS=32768
readonly PORT=15230
readonly RUNS=5

usage ()
{
  echo "usage: $0 develop|oos [all|s5]"
}

[[ $# -ge 1 && $# -le 2 ]] || { usage >&2; exit 2; }
BRANCH="$1"
MODE="${2:-all}"
[[ "$MODE" == "all" || "$MODE" == "s5" ]] || { usage >&2; exit 2; }
case "$BRANCH" in
  develop)
    WORKTREE="/home/vimkim/gh/cb/develop"
    CUBRID="/home/vimkim/.cub/install/develop/release_gcc"
    ;;
  oos)
    WORKTREE="/home/vimkim/gh/cb/CBRD-27006-oos-recdes-locality"
    CUBRID="/home/vimkim/.cub/install/CBRD-27006-oos-recdes-locality/release_gcc"
    ;;
  *)
    usage >&2
    exit 2
    ;;
esac

export CUBRID
export CUBRID_DATABASES="$RESULTS_ROOT/database-files/$BRANCH"
export PATH="$CUBRID/bin:$PATH"
export LD_LIBRARY_PATH="$CUBRID/lib:$CUBRID/cci/lib:${LD_LIBRARY_PATH:-}"

readonly CSQL="$CUBRID/bin/csql"
readonly CUBRID_BIN="$CUBRID/bin/cubrid"
readonly BRANCH_RESULTS="$RESULTS_ROOT/$BRANCH"
readonly DB_DIR="$CUBRID_DATABASES/$DB_NAME"
readonly CONF="$CUBRID/conf/cubrid.conf"
readonly ORIGINAL_CONF="$BRANCH_RESULTS/environment/cubrid.conf.before"

mkdir -p "$BRANCH_RESULTS/environment" "$BRANCH_RESULTS/sql" "$CUBRID_DATABASES"
exec > >(tee -a "$BRANCH_RESULTS/runner.log") 2>&1
set -x

cleanup ()
{
  local rc=$?
  "$CUBRID_BIN" server stop "$DB_NAME" || true
  if [[ -f "$ORIGINAL_CONF" ]]; then
    cp "$ORIGINAL_CONF" "$CONF"
  fi
  exit "$rc"
}
trap cleanup EXIT

record_environment ()
{
  git -C "$WORKTREE" rev-parse HEAD > "$BRANCH_RESULTS/environment/git-commit.txt"
  git -C "$WORKTREE" status --short --branch > "$BRANCH_RESULTS/environment/git-status.txt"
  "$CSQL" --version > "$BRANCH_RESULTS/environment/csql-version.txt"
  uname -a > "$BRANCH_RESULTS/environment/uname.txt"
  lscpu > "$BRANCH_RESULTS/environment/lscpu.txt"
  free -h > "$BRANCH_RESULTS/environment/free-h.txt"
  df -h "$RESULTS_ROOT" > "$BRANCH_RESULTS/environment/df-h.txt"
  findmnt -T "$RESULTS_ROOT" > "$BRANCH_RESULTS/environment/findmnt.txt"
  lsblk -o NAME,TYPE,SIZE,MOUNTPOINT,FSTYPE,MODEL > "$BRANCH_RESULTS/environment/lsblk.txt"
  cp "$SETUP_SQL" "$BRANCH_RESULTS/sql/oos-performance-setup.sql"
  cp "$CONF" "$ORIGINAL_CONF"
}

configure_isolated_server ()
{
  # The two branches run sequentially, but a private port prevents accidental
  # attachment to an unrelated local CUBRID master owned by another user.
  sed -Ei \
    -e 's/^cubrid_port_id=.*/cubrid_port_id=15230/' \
    -e 's/^data_buffer_size=.*/data_buffer_size=512M/' \
    "$CONF"
  cp "$CONF" "$BRANCH_RESULTS/environment/cubrid.conf.active-s1-s4"
}

enable_small_vacuum_log_blocks ()
{
  # This database-specific parameter is frozen at createdb time. It affects
  # only S5 and makes the delete record visible to vacuum promptly.
  printf '\n[@%s]\nvacuum_log_block_pages=4\n' "$DB_NAME" >> "$CONF"
  cp "$CONF" "$BRANCH_RESULTS/environment/cubrid.conf.active-s5"
}

capture_server_state ()
{
  local out="$1"
  "$CUBRID_BIN" server status > "$out" 2>&1 || true
}

create_database ()
{
  local phase="$1"
  mkdir -p "$BRANCH_RESULTS/$phase"
  mkdir -p "$DB_DIR"
  "$CUBRID_BIN" server stop "$DB_NAME" || true
  "$CUBRID_BIN" createdb --db-volume-size=2G --log-volume-size=2G --db-page-size=16K \
    --replace -F "$DB_DIR" "$DB_NAME" en_US.utf8 > "$BRANCH_RESULTS/$phase/createdb.out" 2>&1
  "$CUBRID_BIN" server start "$DB_NAME" > "$BRANCH_RESULTS/$phase/server-start.out" 2>&1
  capture_server_state "$BRANCH_RESULTS/$phase/server-status.out"
}

stop_database ()
{
  "$CUBRID_BIN" server stop "$DB_NAME" > "$BRANCH_RESULTS/server-stop.out" 2>&1 || true
}

setup_full_data ()
{
  local phase="$1"
  "$CSQL" -C -u dba -p '' "$DB_NAME" -i "$SETUP_SQL" -o "$BRANCH_RESULTS/$phase/setup.out"
  "$CSQL" -C -u dba -p '' "$DB_NAME" -t -N -c \
    "SELECT COUNT(*), MIN(BIT_LENGTH(payload)), MAX(BIT_LENGTH(payload)), SUM(hot_col) FROM perf_oos;" \
    > "$BRANCH_RESULTS/$phase/setup-validation.out"
}

create_empty_schema ()
{
  local phase="$1"
  "$CSQL" -C -u dba -p '' "$DB_NAME" -c \
    "CREATE TABLE perf_oos (id INT PRIMARY KEY, hot_col INT NOT NULL, payload BIT VARYING);" \
    > "$BRANCH_RESULTS/$phase/create-schema.out"
}

capture_stats ()
{
  local out="$1"
  "$CUBRID_BIN" statdump -c "$DB_NAME" > "$out"
}

capture_space ()
{
  local out="$1"
  "$CUBRID_BIN" spacedb -C --size-unit=M "$DB_NAME" > "$out"
  find "$DB_DIR" -maxdepth 1 -type f -printf '%f %s bytes\n' | sort > "${out%.txt}.files.txt"
}

run_sql ()
{
  local case_name="$1"
  local run="$2"
  local sql="$3"
  local dir="$BRANCH_RESULTS/$case_name/run-$run"
  mkdir -p "$dir"
  capture_stats "$dir/stat-before.txt"
  /usr/bin/time -f 'elapsed_s=%e\nmax_rss_kb=%M\nuser_cpu_s=%U\nsys_cpu_s=%S' -o "$dir/time.txt" \
    "$CSQL" -C -u dba -p '' "$DB_NAME" -t -N -c "$sql" > "$dir/csql.out" 2> "$dir/csql.err"
  capture_stats "$dir/stat-after.txt"
}

run_s1_s2 ()
{
  create_database "reads"
  setup_full_data "reads"

  mkdir -p "$BRANCH_RESULTS/s1" "$BRANCH_RESULTS/s2"
  "$CSQL" -C -u dba -p '' "$DB_NAME" -t -N -c 'SELECT SUM(hot_col) FROM perf_oos;' \
    > "$BRANCH_RESULTS/s1/warmup.out"
  for run in $(seq 1 "$RUNS"); do
    run_sql "s1-narrow-scan-warm" "$run" 'SELECT SUM(hot_col) FROM perf_oos;'
  done

  "$CSQL" -C -u dba -p '' "$DB_NAME" -t -N -c \
    "SELECT COUNT(*) FROM perf_oos WHERE payload = CAST (REPEAT (X'0123456789ABCDEF', 512) AS BIT VARYING);" \
    > "$BRANCH_RESULTS/s2/warmup.out"
  for run in $(seq 1 "$RUNS"); do
    run_sql "s2-payload-access-warm" "$run" \
      "SELECT COUNT(*) FROM perf_oos WHERE payload = CAST (REPEAT (X'0123456789ABCDEF', 512) AS BIT VARYING);"
  done
  stop_database
}

run_s3 ()
{
  local run
  local sql="INSERT INTO perf_oos SELECT LEVEL, MOD (LEVEL, 1000), REPEAT (X'0123456789ABCDEF', 512) FROM db_root CONNECT BY LEVEL <= $ROWS; COMMIT;"
  for run in $(seq 1 "$RUNS"); do
    local phase="s3-bulk-insert/run-$run"
    create_database "$phase"
    create_empty_schema "$phase"
    capture_space "$BRANCH_RESULTS/$phase/space-before.txt"
    run_sql "s3-bulk-insert" "$run" "$sql"
    capture_space "$BRANCH_RESULTS/$phase/space-after.txt"
    "$CSQL" -C -u dba -p '' "$DB_NAME" -t -N -c \
      'SELECT COUNT(*), MIN(BIT_LENGTH(payload)), MAX(BIT_LENGTH(payload)) FROM perf_oos;' \
      > "$BRANCH_RESULTS/$phase/validation.out"
    stop_database
  done
}

run_s4 ()
{
  local run
  for run in $(seq 1 "$RUNS"); do
    local phase="s4-small-column-update/run-$run"
    create_database "$phase"
    setup_full_data "$phase"
    capture_space "$BRANCH_RESULTS/$phase/space-before.txt"
    run_sql "s4-small-column-update" "$run" 'UPDATE perf_oos SET hot_col = hot_col + 1; COMMIT;'
    capture_space "$BRANCH_RESULTS/$phase/space-after.txt"
    "$CSQL" -C -u dba -p '' "$DB_NAME" -t -N -c \
      'SELECT COUNT(*), SUM(hot_col), MIN(BIT_LENGTH(payload)), MAX(BIT_LENGTH(payload)) FROM perf_oos;' \
      > "$BRANCH_RESULTS/$phase/validation.out"
    stop_database
  done
}

run_s5 ()
{
  [[ "$BRANCH" == "oos" ]] || return 0
  enable_small_vacuum_log_blocks
  create_database "s5-delete-vacuum-reinsert"
  setup_full_data "s5-delete-vacuum-reinsert"
  local phase="$BRANCH_RESULTS/s5-delete-vacuum-reinsert"
  capture_space "$phase/space-before-delete.txt"
  printf ';oos_stats perf_oos\n' | "$CSQL" -C -u dba -p '' "$DB_NAME" > "$phase/oos-stats-before-delete.out"
  run_sql "s5-delete-vacuum-reinsert/delete" 1 'DELETE FROM perf_oos; COMMIT;'
  capture_space "$phase/space-after-delete.txt"
  "$CSQL" -C -u dba -p '' "$DB_NAME" -t -N -c 'SELECT COUNT(*) FROM perf_oos;' > "$phase/delete-validation.out"
  "$CUBRID_BIN" vacuumdb -C --dump "$DB_NAME" > "$phase/vacuum-before-wakeup.out"
  printf ';vacuum\n' | "$CSQL" -C -u dba -p '' "$DB_NAME" > "$phase/vacuum-wakeup.out"

  # Ensure the delete-containing vacuum log blocks are no longer at the log head.
  "$CSQL" -C -u dba -p '' "$DB_NAME" -c \
    "CREATE TABLE vacuum_filler (id INT PRIMARY KEY, v VARCHAR(100)); INSERT INTO vacuum_filler SELECT LEVEL, REPEAT ('x', 100) FROM db_root CONNECT BY LEVEL <= 5000; COMMIT;" \
    > "$phase/vacuum-filler.out"
  for poll in $(seq 1 60); do
    "$CUBRID_BIN" vacuumdb -C --dump "$DB_NAME" > "$phase/vacuum-poll-$poll.out"
    printf ';vacuum\n' | "$CSQL" -C -u dba -p '' "$DB_NAME" > "$phase/vacuum-wakeup-$poll.out"
    sleep 1
  done
  capture_space "$phase/space-after-vacuum.txt"
  printf ';oos_stats perf_oos\n' | "$CSQL" -C -u dba -p '' "$DB_NAME" > "$phase/oos-stats-after-vacuum.out"
  run_sql "s5-delete-vacuum-reinsert/reinsert" 1 \
    "INSERT INTO perf_oos SELECT LEVEL, MOD (LEVEL, 1000), REPEAT (X'0123456789ABCDEF', 512) FROM db_root CONNECT BY LEVEL <= $ROWS; COMMIT;"
  capture_space "$phase/space-after-reinsert.txt"
  "$CSQL" -C -u dba -p '' "$DB_NAME" -t -N -c \
    'SELECT COUNT(*), MIN(BIT_LENGTH(payload)), MAX(BIT_LENGTH(payload)) FROM perf_oos;' \
    > "$phase/reinsert-validation.out"
  printf ';oos_stats perf_oos\n' | "$CSQL" -C -u dba -p '' "$DB_NAME" > "$phase/oos-stats-after-reinsert.out"
  "$CUBRID_BIN" vacuumdb -C --dump "$DB_NAME" > "$phase/vacuum-final.out"
  stop_database
}

record_environment
configure_isolated_server
if [[ "$MODE" == "all" ]]; then
  run_s1_s2
  run_s3
  run_s4
fi
run_s5
printf 'completed_at=%s\n' "$(date --iso-8601=seconds)" > "$BRANCH_RESULTS/completed.txt"
