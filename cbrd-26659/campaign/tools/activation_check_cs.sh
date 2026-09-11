#!/usr/bin/env bash
# CBRD-26659 campaign ticket 15 -- client-server activation CHECKER for the ticket 13 fixture.
#
#   activation_check_cs.sh <install-dir> <out-dir> [db-name] [expected-sumlen]
#
# A client-server counterpart of evidence/ticket13/activation_check.sh, which is standalone
# (csql -S). The user's decision O2 (ticket 35) asks that public SQL activation checks run in
# the case's own run mode -- CTP runs the case client-server -- so that the evidence can be
# `proven` rather than `reused`. This script replays the public case's fixture in the public
# case's insert order against a cub_server it starts itself, with SHOW HEAP OOS interleaved,
# and ASSERTS the same nine observations as the standalone checker:
#
#   after CREATE            Has_oos_file 0, Oos_num_recs 0, Oos_recs_sumlen 0
#   after the comparator    Has_oos_file 0, Oos_num_recs 0, Oos_recs_sumlen 0
#   after the OOS-backed    Has_oos_file 1, Oos_num_recs 1, Oos_recs_sumlen <expected>
#
# 3024 = 3008 payload + one 16-byte chunk header identifies the moved-out value as `big`;
# moving out `small` would give 1224. The fourth argument lets a negative control pass a wrong
# expectation and demonstrate that the checker detects it.
#
# Safety:
#   * MUST run under campaign_ns.sh (the wrapper does this): it starts a cub_master and a
#     cub_server, and the namespace's exit tears them down.
#   * refuses to start unless $CUBRID/conf/cubrid.conf carries the campaign's cubrid_port_id
#     (26659); it never touches port 1523.
#   * databases live under the campaign's own CUBRID_DATABASES, never the install's.
#
# Exit 0 only when every assertion holds. assertions.txt ends in a RESULT line; identity.txt
# carries run_mode=client-server, which is what ctp_sql_records.py reads to decide `proven`.
set -u

INSTALL=${1:?install dir}
OUT=$(mkdir -p "${2:?output dir}" && cd "$2" && pwd)
DB=${3:-t15chk16k}
EXPECT_SUMLEN=${4:-3024}
PAGE=${ACTIVATION_PAGE_SIZE:-16384}
PORT=${CAMPAIGN_PORT_ID:-26659}
CAMPAIGN_TICKET_ROOT=${CAMPAIGN_TICKET_ROOT:-/home/vimkim/.cub/campaign/cbrd-26659/ticket15}

export CUBRID="$INSTALL"
export CUBRID_DATABASES="${CAMPAIGN_TICKET_ROOT}/db"
export PATH="$CUBRID/bin:$PATH"
export LD_LIBRARY_PATH="$CUBRID/lib:$CUBRID/cci/lib"
mkdir -p "$CUBRID_DATABASES"
cd "$CUBRID_DATABASES" || exit 1

conf_port=$(sed -n 's/^cubrid_port_id=\([0-9]*\).*/\1/p' "$CUBRID/conf/cubrid.conf" | head -1)
if [ "${conf_port}" != "${PORT}" ]; then
  echo "REFUSED: $CUBRID/conf/cubrid.conf carries cubrid_port_id=${conf_port:-<unset>}, not the campaign port ${PORT}; not starting a master" | tee "$OUT/assertions.txt"
  echo "RESULT: activation NOT proven -- checker refused to start" >> "$OUT/assertions.txt"
  exit 3
fi
if [ "$(readlink /proc/1/exe 2>/dev/null)" = "$(readlink /proc/self/exe 2>/dev/null)" ] || [ "$$" -le 3 ]; then
  : # inside a fresh PID namespace (we are near PID 1); fine
fi

{
  echo "install=$CUBRID"
  echo "db=$DB"
  echo "db_page_size=$PAGE"
  echo "run_mode=client-server"
  echo "cubrid_port_id=$PORT"
  echo "expected_sumlen=$EXPECT_SUMLEN"
  echo "cubrid_rel=$(cubrid_rel | tr -d '\r' | tr -s '[:space:]' ' ')"
  sha256sum "$CUBRID/lib/libcubrid.so" "$CUBRID/lib/libcubridsa.so"
  echo "started_at=$(date -Is)"
} > "$OUT/identity.txt" 2>&1

cubrid deletedb "$DB" >/dev/null 2>&1 || true
cubrid createdb --db-volume-size=64M --log-volume-size=32M \
  --db-page-size="$PAGE" --log-page-size="$PAGE" "$DB" en_US.utf8 > "$OUT/createdb.log" 2>&1 \
  || { echo "createdb $DB FAILED" | tee -a "$OUT/createdb.log"; echo "RESULT: activation NOT proven -- createdb failed" > "$OUT/assertions.txt"; exit 2; }

cubrid server start "$DB" > "$OUT/server_start.log" 2>&1
if ! grep -q "success\|already running" "$OUT/server_start.log"; then
  echo "server start FAILED" >> "$OUT/server_start.log"
  echo "RESULT: activation NOT proven -- server start failed" > "$OUT/assertions.txt"
  cubrid service stop >/dev/null 2>&1
  exit 2
fi

phase () {                       # phase <tag> <sql-before-the-show>
  local tag=$1 sql=$2
  cat > "$OUT/phase_${tag}.sql" <<EOF
${sql}
SHOW HEAP OOS OF t_cbrd_26659_rep02;
EOF
  csql -u dba "$DB" -i "$OUT/phase_${tag}.sql" > "$OUT/phase_${tag}.out" 2>&1
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

# Columns are located by NAME from the SHOW HEAP OOS header (ticket 14 finding i), never by
# position: the header line carries the column names, the row is the line quoting the class.
read_field () {                  # read_field <tag> <column name>
  awk -v col="$2" '
    /Has_oos_file/ && !hdr { for (i = 1; i <= NF; i++) if ($i == col) idx = i; hdr = 1; next }
    hdr && index($0, "'"'"'dba.t_cbrd_26659_rep02'"'"'") { if (idx > 0 && NF >= idx) print $idx; else print "UNRESOLVED(" col ")"; exit }
  ' "$OUT/phase_$1.out"
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
  check "after CREATE: Has_oos_file"        0                "$(read_field create Has_oos_file)"
  check "after CREATE: Oos_num_recs"        0                "$(read_field create Oos_num_recs)"
  check "after CREATE: Oos_recs_sumlen"     0                "$(read_field create Oos_recs_sumlen)"
  check "after comparator: Has_oos_file"    0                "$(read_field comparator Has_oos_file)"
  check "after comparator: Oos_num_recs"    0                "$(read_field comparator Oos_num_recs)"
  check "after comparator: Oos_recs_sumlen" 0                "$(read_field comparator Oos_recs_sumlen)"
  check "after OOS-backed: Has_oos_file"    1                "$(read_field oosbacked Has_oos_file)"
  check "after OOS-backed: Oos_num_recs"    1                "$(read_field oosbacked Oos_num_recs)"
  check "after OOS-backed: Oos_recs_sumlen" "$EXPECT_SUMLEN" "$(read_field oosbacked Oos_recs_sumlen)"
  echo
  echo "run_mode: client-server (csql over the cub_master on port $PORT, cub_server $DB)"
  if [ "$fails" -eq 0 ]; then
    echo "RESULT: activation proven -- one chunk, and the payload sum identifies \`big\` as the moved-out value."
  else
    echo "RESULT: activation NOT proven -- $fails assertion(s) failed."
  fi
} > "$OUT/assertions.txt" 2>&1
cat "$OUT/assertions.txt"

cubrid server stop "$DB" > "$OUT/server_stop.log" 2>&1
cubrid service stop >> "$OUT/server_stop.log" 2>&1
cubrid checkdb -S "$DB" > "$OUT/checkdb.txt" 2>&1
echo "checkdb exit=$?" >> "$OUT/checkdb.txt"
echo "ended_at=$(date -Is)" >> "$OUT/identity.txt"

exit $(( fails > 0 ? 1 : 0 ))
