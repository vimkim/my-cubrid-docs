#!/usr/bin/env bash
# CBRD-26659 campaign ticket 19 -- spec-driven client-server activation CHECKER.
#
#   activation_check_spec.sh <install-dir> <out-dir> <spec-file> [db-name]
#
# Ticket 13's activation_check_cs.sh replays one hard-coded fixture.  Ticket 19 has eight
# cases with eight different fixtures, so this checker takes the fixture from a spec file
# instead, and is otherwise the same instrument: it starts its own cub_server, replays the
# case's own statements in the case's own order, interleaves SHOW HEAP OOS, and exits non-zero
# unless every asserted observation holds.  The user's decision O2 (ticket 35) asks that public
# SQL activation checks run in the case's own run mode -- CTP runs the cases client-server --
# so that the evidence can be `proven` rather than `reused`.
#
# SPEC FORMAT (see evidence/ticket19/activation/*.spec, generated with the cases themselves)
#
#   # comment, ignored
#   PHASE <tag> <table> <has_oos> <num_recs> <sumlen>
#   <SQL statements, one or more lines, run BEFORE this phase's SHOW HEAP OOS>
#   ...
#
# Each of the three expected fields is either an integer, which is ASSERTED, or `-`, which is
# OBSERVED: printed with its context and never able to fail the run.  Observation is not
# leniency -- it is what the campaign's authority policy requires for a quantity whose value is
# not settled at the pin.  Two kinds appear here:
#
#   * chunk growth after an UPDATE.  At the pin every UPDATE allocates fresh value chains even
#     for attributes the statement did not assign (OOS-SQL-03, `observation-only`, superseded on
#     paper by CBRD-27230), so the count that follows an UPDATE is current behaviour, never a
#     requirement.
#   * chunk survival after a DELETE.  OOS-SQL-05 says the chains are not removed at delete time
#     in MVCC mode, and they are not -- but the moment vacuum reclaims them is a background
#     event, so asserting a count right after a DELETE would be asserting a race.  The expected
#     value is printed beside the observed one so a reviewer sees the deferral.
#
# Safety, unchanged from activation_check_cs.sh:
#   * MUST run under campaign_ns.sh (the wrapper does this): it starts a cub_master and a
#     cub_server, and the namespace's exit tears them down.
#   * refuses to start unless $CUBRID/conf/cubrid.conf carries the campaign's cubrid_port_id;
#     it never touches port 1523.
#   * databases live under the campaign's own CUBRID_DATABASES, never the install's.
#
# Exit 0 only when every asserted observation holds.  assertions.txt ends in a RESULT line;
# identity.txt carries run_mode=client-server, which is what ctp_sql_records.py reads.
set -u

INSTALL=${1:?install dir}
OUT=$(mkdir -p "${2:?output dir}" && cd "$2" && pwd)
SPEC=${3:?spec file}
DB=${4:-t19chk}
PAGE=${ACTIVATION_PAGE_SIZE:-16384}
PORT=${CAMPAIGN_PORT_ID:-26659}
CAMPAIGN_TICKET_ROOT=${CAMPAIGN_TICKET_ROOT:-/home/vimkim/.cub/campaign/cbrd-26659/ticket19}

[ -r "$SPEC" ] || { echo "spec $SPEC is not readable" >&2; exit 2; }

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

{
  echo "install=$CUBRID"
  echo "db=$DB"
  echo "db_page_size=$PAGE"
  echo "run_mode=client-server"
  echo "cubrid_port_id=$PORT"
  echo "spec=$SPEC"
  echo "spec_sha256=$(sha256sum "$SPEC" | cut -d' ' -f1)"
  echo "cubrid_rel=$(cubrid_rel | tr -d '\r' | tr -s '[:space:]' ' ')"
  sha256sum "$CUBRID/lib/libcubrid.so" "$CUBRID/lib/libcubridsa.so"
  echo "started_at=$(date -Is)"
} > "$OUT/identity.txt" 2>&1

cubrid deletedb "$DB" >/dev/null 2>&1 || true
cubrid createdb --db-volume-size=256M --log-volume-size=64M \
  --db-page-size="$PAGE" --log-page-size="$PAGE" "$DB" en_US.utf8 > "$OUT/createdb.log" 2>&1 \
  || { echo "createdb $DB FAILED" | tee -a "$OUT/createdb.log"; echo "RESULT: activation NOT proven -- createdb failed" > "$OUT/assertions.txt"; exit 2; }

cubrid server start "$DB" > "$OUT/server_start.log" 2>&1
if ! grep -q "success\|already running" "$OUT/server_start.log"; then
  echo "server start FAILED" >> "$OUT/server_start.log"
  echo "RESULT: activation NOT proven -- server start failed" > "$OUT/assertions.txt"
  cubrid service stop >/dev/null 2>&1
  exit 2
fi

# --- split the spec into one SQL file per phase, plus a table of expectations ------------------
mkdir -p "$OUT/phases"
awk -v out="$OUT/phases" '
  /^[[:space:]]*#/ { next }
  /^PHASE[[:space:]]/ {
    n++
    tag[n] = $2; tbl[n] = $3; e_has[n] = $4; e_num[n] = $5; e_sum[n] = $6
    file = sprintf("%s/%02d_%s.sql", out, n, $2)
    next
  }
  n > 0 { print > file }
  END {
    for (i = 1; i <= n; i++)
      printf "%d\t%s\t%s\t%s\t%s\t%s\n", i, tag[i], tbl[i], e_has[i], e_num[i], e_sum[i] > (out "/index.tsv")
  }
' "$SPEC"

# Columns are located by NAME from the SHOW HEAP OOS header (ticket 14 finding i), never by
# position: the header line carries the column names, the row is the line quoting the class.
read_field () {                  # read_field <phase out file> <table> <column name>
  awk -v col="$3" -v tbl="'dba.$2'" '
    /Has_oos_file/ && !hdr { for (i = 1; i <= NF; i++) if ($i == col) idx = i; hdr = 1; next }
    hdr && index($0, tbl) { if (idx > 0 && NF >= idx) print $idx; else print "UNRESOLVED(" col ")"; exit }
  ' "$1"
}

fails=0
observations=0
{
  while IFS=$'\t' read -r idx tag tbl e_has e_num e_sum; do
    sqlfile=$(printf '%s/phases/%02d_%s.sql' "$OUT" "$idx" "$tag")
    outfile="$OUT/phases/$(printf '%02d_%s' "$idx" "$tag").out"
    printf 'SHOW HEAP OOS OF %s;\n' "$tbl" >> "$sqlfile"
    csql -u dba "$DB" -i "$sqlfile" > "$outfile" 2>&1
    if ! grep -q "'dba.$tbl'" "$outfile"; then
      echo "FAIL  phase ${tag}: no SHOW HEAP OOS row for ${tbl} -- extraction failed"
      fails=$((fails + 1))
      continue
    fi
    for pair in "Has_oos_file:$e_has" "Oos_num_recs:$e_num" "Oos_recs_sumlen:$e_sum"; do
      col=${pair%%:*}; want=${pair#*:}
      got=$(read_field "$outfile" "$tbl" "$col")
      label="${tag}/${tbl}: ${col}"
      if [ "$want" = "-" ]; then
        printf 'OBSERVE  %-52s %s\n' "$label" "$got"
        observations=$((observations + 1))
      elif [ "$want" = "$got" ]; then
        printf 'PASS     %-52s expected %-8s got %s\n' "$label" "$want" "$got"
      else
        printf 'FAIL     %-52s expected %-8s got %s\n' "$label" "$want" "$got"
        fails=$((fails + 1))
      fi
    done
  done < "$OUT/phases/index.tsv"
  echo
  echo "run_mode: client-server (csql over the cub_master on port $PORT, cub_server $DB)"
  echo "observations (not assertions): $observations"
  if [ "$fails" -eq 0 ]; then
    echo "RESULT: activation proven -- every asserted SHOW HEAP OOS observation holds."
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
