#!/usr/bin/env bash
# Activation CHECKER for the ticket-13 tracer-bullet fixture.
#
#   activation_check.sh <install-dir> <out-dir> [db-name] [expected-sumlen]
#
# The public SQL case cannot detect a largest-first regression: no portable SQL exposes
# per-attribute placement, so an engine that moved out `small` instead of `big` would
# produce a byte-identical answer.  This script is the check that can tell them apart.
#
# It replays the public case's fixture in the public case's insert order under csql -S, with
# `SHOW HEAP OOS OF` interleaved, and ASSERTS three observations:
#
#   after CREATE            Has_oos_file 0, Oos_num_recs 0, Oos_recs_sumlen 0
#   after the comparator    Has_oos_file 0, Oos_num_recs 0, Oos_recs_sumlen 0
#   after the OOS-backed    Has_oos_file 1, Oos_num_recs 1, Oos_recs_sumlen <expected>
#
# The third sum is what discriminates: 3024 = 3008 payload + one 16-byte chunk header
# identifies the moved-out value as `big`.  Moving out `small` would give 1224.
#
# Exit status 0 only when every assertion holds; non-zero on any mismatch, so the script
# can fail.  The fourth argument exists so a negative control can pass a wrong expectation
# and demonstrate that this checker actually detects it.
#
# Standalone mode only: starts no cub_master and no cub_server, so it cannot disturb any
# other CUBRID process on the host.  It creates and owns one database and touches nothing
# else.
set -u

INSTALL=${1:?install dir}
OUT=$(mkdir -p "${2:?output dir}" && cd "$2" && pwd)
DB=${3:-t13chk16k}
EXPECT_SUMLEN=${4:-3024}
PAGE=16384

export CUBRID="$INSTALL"
export CUBRID_DATABASES="$HOME/.cub/campaign/cbrd-26659/db"
export PATH="$CUBRID/bin:$PATH"
export LD_LIBRARY_PATH="$CUBRID/lib:$CUBRID/cci/lib:${LD_LIBRARY_PATH:-}"
mkdir -p "$CUBRID_DATABASES"
cd "$CUBRID_DATABASES" || exit 1

{
  echo "install=$CUBRID"
  echo "db=$DB  db_page_size=$PAGE  run_mode=standalone"
  echo "expected_sumlen=$EXPECT_SUMLEN"
  cubrid_rel
  sha256sum "$CUBRID/lib/libcubrid.so" "$CUBRID/lib/libcubridsa.so"
} > "$OUT/identity.txt" 2>&1

OOSLOG="$CUBRID/log/oos.log"
oos_lines () { if [ -f "$OOSLOG" ]; then wc -l < "$OOSLOG"; else echo 0; fi; }
{
  echo "oos.log path: $OOSLOG"
  echo "oos.log lines before: $(oos_lines)"
} > "$OUT/ooslog-summary.txt"

cubrid deletedb "$DB" >/dev/null 2>&1 || true
cubrid createdb --db-volume-size=64M --log-volume-size=32M \
  --db-page-size="$PAGE" --log-page-size="$PAGE" "$DB" en_US.utf8 > "$OUT/createdb.log" 2>&1 \
  || { echo "createdb $DB FAILED" | tee -a "$OUT/createdb.log"; exit 2; }

# One SHOW HEAP OOS per phase, each into its own file, so parsing cannot mix them up.
phase () {                       # phase <tag> <sql-before-the-show>
  local tag=$1 sql=$2
  cat > "$OUT/phase_${tag}.sql" <<EOF
${sql}
SHOW HEAP OOS OF t_cbrd_26659_rep02;
EOF
  csql -S -u dba "$DB" -i "$OUT/phase_${tag}.sql" > "$OUT/phase_${tag}.out" 2>&1
}

phase create "
DROP TABLE IF EXISTS t_cbrd_26659_rep02;
CREATE TABLE t_cbrd_26659_rep02 (id INT PRIMARY KEY, big BIT VARYING, small BIT VARYING);"

phase comparator "
INSERT INTO t_cbrd_26659_rep02
  VALUES (2, CAST(REPEAT('CC', 1000) AS BIT VARYING), CAST(REPEAT('DD', 500) AS BIT VARYING));"

phase oosbacked "
INSERT INTO t_cbrd_26659_rep02
  VALUES (1, CAST(REPEAT('AA', 3000) AS BIT VARYING), CAST(REPEAT('BB', 1200) AS BIT VARYING));"

# Pull the three numbers out of the SHOW HEAP OOS row.  The row is the line quoting the
# class name; Has_oos_file, Oos_num_recs and Oos_recs_sumlen are fields 6, 11 and 12 of it.
read_field () {                  # read_field <tag> <1-based field index>
  awk -v n="$2" "/'dba.t_cbrd_26659_rep02'/ { print \$n; exit }" "$OUT/phase_$1.out"
}

fails=0
check () {                       # check <label> <expected> <actual>
  if [ "$2" = "$3" ]; then
    printf 'PASS  %-44s expected %-6s got %s\n' "$1" "$2" "$3"
  else
    printf 'FAIL  %-44s expected %-6s got %s\n' "$1" "$2" "$3"
    fails=$((fails + 1))
  fi
}

{
  for tag in create comparator oosbacked; do
    if ! grep -q "'dba.t_cbrd_26659_rep02'" "$OUT/phase_${tag}.out"; then
      echo "FAIL  phase ${tag}: no SHOW HEAP OOS row found -- extraction failed"
      fails=$((fails + 1))
    fi
  done

  check "after CREATE: Has_oos_file"        0                "$(read_field create 6)"
  check "after CREATE: Oos_num_recs"        0                "$(read_field create 11)"
  check "after CREATE: Oos_recs_sumlen"     0                "$(read_field create 12)"

  check "after comparator: Has_oos_file"    0                "$(read_field comparator 6)"
  check "after comparator: Oos_num_recs"    0                "$(read_field comparator 11)"
  check "after comparator: Oos_recs_sumlen" 0                "$(read_field comparator 12)"

  check "after OOS-backed: Has_oos_file"    1                "$(read_field oosbacked 6)"
  check "after OOS-backed: Oos_num_recs"    1                "$(read_field oosbacked 11)"
  check "after OOS-backed: Oos_recs_sumlen" "$EXPECT_SUMLEN" "$(read_field oosbacked 12)"

  echo
  if [ "$fails" -eq 0 ]; then
    echo "RESULT: activation proven -- one chunk, and the payload sum identifies \`big\` as the moved-out value."
  else
    echo "RESULT: $fails assertion(s) failed -- activation NOT proven."
  fi
} > "$OUT/assertions.txt" 2>&1
cat "$OUT/assertions.txt"

{
  echo "oos.log lines after: $(oos_lines)"
  echo -n "insert-side oos_insert lines (expected 0 at this pin, the INSERT path writes none): "
  if [ -f "$OOSLOG" ]; then grep -c 'oos_insert' "$OOSLOG" || true; else echo 0; fi
} >> "$OUT/ooslog-summary.txt"
[ -f "$OOSLOG" ] && cp "$OOSLOG" "$OUT/oos.log"

cubrid checkdb -S "$DB" > "$OUT/checkdb.txt" 2>&1
echo "checkdb exit=$?" >> "$OUT/checkdb.txt"

exit $(( fails > 0 ? 1 : 0 ))
