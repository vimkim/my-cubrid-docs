#!/usr/bin/env bash
# Paired activation-evidence run for the ticket-13 tracer-bullet SQL case.
#
#   activation_evidence.sh <install-dir> <out-dir>
#
# Replays the public case's fixture in the public case's insert order, under csql -S, with
# `SHOW HEAP OOS OF` interleaved at the three points the oracle predicts.  The public case
# stays portable and contains no diagnostic statement; this run is what proves its OOS path
# executed.
#
# Standalone mode only: it starts no cub_master and no cub_server, so it cannot disturb any
# other CUBRID process on the host.  It creates and owns one database under its own
# CUBRID_DATABASES and touches nothing else.
#
# The debug OOS log cannot supply insert-side evidence at this pin (ticket 11 §6: the SQL
# INSERT path calls oos_insert_many, which writes no debug line).  The run records the log's
# before/after line counts anyway, so that absence is evidence rather than an assumption.
set -u

INSTALL=${1:?install dir}
OUT=${2:?output dir}
DB=${3:-t13oos16k}
PAGE=16384

export CUBRID="$INSTALL"
export CUBRID_DATABASES="$HOME/.cub/campaign/cbrd-26659/db"
export PATH="$CUBRID/bin:$PATH"
export LD_LIBRARY_PATH="$CUBRID/lib:$CUBRID/cci/lib:${LD_LIBRARY_PATH:-}"
mkdir -p "$CUBRID_DATABASES" "$OUT"
cd "$CUBRID_DATABASES" || exit 1

{
  echo "install=$CUBRID"
  echo "databases=$CUBRID_DATABASES"
  echo "db=$DB"
  echo "db_page_size=$PAGE"
  echo "run_mode=standalone"
  cubrid_rel
  sha256sum "$CUBRID/lib/libcubrid.so" "$CUBRID/lib/libcubridsa.so"
} > "$OUT/identity.txt" 2>&1

OOSLOG="$CUBRID/log/oos.log"
echo "oos.log lines before: $(wc -l < "$OOSLOG" 2>/dev/null || echo 0)" > "$OUT/ooslog-summary.txt"

cubrid deletedb "$DB" >/dev/null 2>&1 || true
if ! cubrid createdb --db-volume-size=64M --log-volume-size=32M \
      --db-page-size="$PAGE" --log-page-size="$PAGE" "$DB" en_US.utf8 > "$OUT/createdb.log" 2>&1; then
  echo "createdb $DB FAILED" | tee -a "$OUT/createdb.log"
  exit 1
fi

cat > "$OUT/fixture.sql" <<'EOF'
-- Ticket 13 activation evidence, pinned engine f4299ac0c, 16 KiB pages.
-- Same fixture and same insert order as
-- sql/_36_guava/cbrd_26659/cases/cbrd_26659_oos_rep02_largest_first.sql,
-- with SHOW HEAP OOS interleaved.  Expected, per expected-oracle.md:
--   after CREATE            Has_oos_file 0, Oos_num_recs 0, Oos_recs_sumlen 0
--   after the comparator    Has_oos_file 0, Oos_num_recs 0, Oos_recs_sumlen 0   (OOS-REP-01)
--   after the OOS-backed    Has_oos_file 1, Oos_num_recs 1, Oos_recs_sumlen 3024 (OOS-REP-02)
DROP TABLE IF EXISTS t_cbrd_26659_rep02;
CREATE TABLE t_cbrd_26659_rep02 (id INT PRIMARY KEY, big BIT VARYING, small BIT VARYING);
SHOW HEAP OOS OF t_cbrd_26659_rep02;

INSERT INTO t_cbrd_26659_rep02
  VALUES (2, CAST(REPEAT('CC', 1000) AS BIT VARYING), CAST(REPEAT('DD', 500) AS BIT VARYING));
SHOW HEAP OOS OF t_cbrd_26659_rep02;

INSERT INTO t_cbrd_26659_rep02
  VALUES (1, CAST(REPEAT('AA', 3000) AS BIT VARYING), CAST(REPEAT('BB', 1200) AS BIT VARYING));
SHOW HEAP OOS OF t_cbrd_26659_rep02;

-- the public case's own assertions, re-run here so logical success and activation
-- evidence come from the same fixture state
SELECT id, DISK_SIZE(big) AS big_disk, DISK_SIZE(small) AS small_disk,
       big   = CAST(REPEAT('AA', 3000) AS BIT VARYING) AS big_ok,
       small = CAST(REPEAT('BB', 1200) AS BIT VARYING) AS small_ok
  FROM t_cbrd_26659_rep02 WHERE id = 1;
SELECT id, DISK_SIZE(big) AS big_disk, DISK_SIZE(small) AS small_disk,
       big   = CAST(REPEAT('CC', 1000) AS BIT VARYING) AS big_ok,
       small = CAST(REPEAT('DD',  500) AS BIT VARYING) AS small_ok
  FROM t_cbrd_26659_rep02 WHERE id = 2;

-- observation only, never asserted: what the size built-ins report for these values.
-- Ticket 11's probe labelled LENGTH(v)/8 as "bytes" and printed 1008 for a 4,035-byte
-- value, so LENGTH is not the byte length and not the bit length either.  Recorded here so
-- no later case mistakes it for a size oracle.
SELECT DISK_SIZE(big) AS disk_size, LENGTH(big) AS length_fn, BIT_LENGTH(big) AS bit_length_fn,
       OCTET_LENGTH(big) AS octet_length_fn
  FROM t_cbrd_26659_rep02 WHERE id = 1;
EOF

csql -S -u dba "$DB" -i "$OUT/fixture.sql" > "$OUT/fixture.out" 2>&1
echo "csql exit=$?" >> "$OUT/fixture.out"

{
  echo "oos.log lines after: $(wc -l < "$OOSLOG" 2>/dev/null || echo 0)"
  echo "--- insert-side oos_insert lines (expected: none at this pin) ---"
  grep -c 'oos_insert' "$OOSLOG" 2>/dev/null || echo 0
} >> "$OUT/ooslog-summary.txt"
[ -f "$OOSLOG" ] && cp "$OOSLOG" "$OUT/oos.log"

cubrid checkdb -S "$DB" > "$OUT/checkdb.txt" 2>&1
echo "checkdb exit=$?" >> "$OUT/checkdb.txt"
