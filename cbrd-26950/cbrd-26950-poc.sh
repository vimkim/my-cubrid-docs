#!/usr/bin/env bash
#
# CBRD-26950 PoC — vacuum deletes live data in a reused OOS slot.
#
# Reproduces the defect on a stock debug build, with NO source modification and
# no fault-injection hook.
#
# The three preconditions from the ticket, each one forced rather than raced:
#
#   1. identity-less probe  oos_chunk_exists() answers "is the slot occupied?",
#                           never "is this still my chunk?" — OOS_RECORD_HEADER
#                           carries no owner OID and no generation.
#   2. slot reuse           OOS pages are ANCHORED, so a freed slotid goes right
#                           back to the next oos_insert, and oos_delete_chain
#                           re-registers the page in bestspace immediately.
#   3. block retry          A vacuum block that does not run to completion keeps
#                           its start_lsa, so the whole block is re-walked from
#                           the immutable undo image.
#
#   phase 1  Insert R1 (gen 1), 5000-byte OOS-backed payloads.
#
#   phase 2  UPDATE all of R1 in ONE transaction, so vacuum cannot reclaim any of
#            it until COMMIT returns and the whole backlog goes eligible at once.
#            UPDATE, not DELETE: DELETE reclaims inside the heap sysop and is
#            idempotent through the MVCC check, so DELETE is not this bug. After
#            UPDATE the old chain survives only in the undo image.
#
#            Then, while vacuum is reclaiming, insert R3 (gen 3) at exactly the
#            same payload size from a second session. Their oos_insert calls take
#            the slots vacuum is freeing, out of the live bestspace cache. -> (2)
#            This has to happen in the same server session as the deletes: after
#            a restart the bestspace cache is cold and new inserts go to fresh
#            pages instead.
#
#            Finally `cubrid server stop`. That takes ~1.5 s to reach the vacuum
#            worker and vacuum reclaims ~2400 chains/s, so ROWS has to be big
#            enough that a backlog survives; otherwise vacuum simply finishes
#            every block and abandons none. With a backlog left, the worker
#            abandons its block at the next log entry.                     -> (3)
#
#   phase 3  Restart. Vacuum re-walks the abandoned block, re-derives the old OOS
#            OIDs from the undo image, the probe says "occupied", and oos_delete
#            removes R3's live chunk.                                      -> (1)
#
#   phase 4  Verdict.
#
# Evidence, in order of strength:
#
#   A. Decisive — gen-3 rows that were inserted and committed AFTER their slot
#      was freed, were never updated afterwards, and can no longer be read.
#      Nothing but the second vacuum pass touched them. gen-1 rows are the
#      control: their post-UPDATE chains were allocated before any delete, so no
#      reused slot can hold them, and they must stay clean.
#
#   B. Corroborating — OOS OIDs that appear in "deleted chunk at oid=" in both
#      vacuum passes. A chunk can only be deleted if its slot is occupied, so
#      each of these slots had been handed out again between the two deletes.
#      Read this as a count of re-deleted slots, not as a per-row victim list:
#      a delete whose sysop was aborted during the shutdown would be restored
#      and then legitimately deleted again, which lands in the same list.
#
# Requires a debug build ($CUBRID/log/oos.log is debug-only) with $CUBRID and
# $CUBRID_DATABASES pointing at it. Creates its own database and its own
# cubrid.conf, so no other database in the installation is touched.
#
# Runtime is a few minutes at the default size, most of it inserting R1.
#
set -uo pipefail

DB=${DB:-oos26950}
ROWS=${ROWS:-20000}                     # R1 rows. The vacuum backlog they create
                                        # must outlast the ~1.5 s a graceful stop
                                        # takes to reach the vacuum worker.
R3_ROWS=${R3_ROWS:-20000}               # upper bound per writer; the shutdown
                                        # cuts the clients off, so fewer land
R3_WRITERS=${R3_WRITERS:-6}             # parallel inserters. Live inserts have to
                                        # keep up with vacuum, or the slots it frees
                                        # last are still empty at the retry
STOP_AT_PCT=${STOP_AT_PCT:-30}          # stop once vacuum has freed this % of
                                        # the chains. Vacuum keeps going for the
                                        # ~1.5 s the stop takes, so this has to
                                        # leave room; a fixed sleep is unreliable
                                        # because the reclaim rate swings with
                                        # buffer-pool warmth
BLOCK_PAGES=${BLOCK_PAGES:-128}         # log pages per vacuum block (2 MB, so a
                                        # block lasts long enough to be caught
                                        # mid-walk)
PAYLOAD_UNITS=${PAYLOAD_UNITS:-4996}    # 8 + 2*4996 hex chars = 5000 bytes
VERIFY_CHUNK=${VERIFY_CHUNK:-250}       # ids per verification statement
PORT=${PORT:-21950}
ER_LOG_VACUUM=${ER_LOG_VACUUM:-4163}    # ERROR|WARNING|VACUUM_DATA|JOBS
WORK=${WORK:-$(mktemp -d "${TMPDIR:-/tmp}/cbrd26950.XXXXXX")}
mkdir -p "$WORK"

CONF="$WORK/cubrid.conf"
export CUBRID_CONF_FILE="$CONF"
OOSLOG="$CUBRID/log/oos.log"
SRVLOG="$CUBRID/log/server/${DB}_latest.err"

say()  { printf '\n=== %s\n' "$*"; }
note() { printf '    %s\n' "$*"; }
die()  { printf '\nFATAL: %s\n' "$*" >&2; exit 2; }

[ -n "${CUBRID:-}" ]           || die 'CUBRID is not set'
[ -n "${CUBRID_DATABASES:-}" ] || die 'CUBRID_DATABASES is not set'
command -v csql >/dev/null     || die 'csql is not on PATH'

# ---------------------------------------------------------------- primitives

write_conf() {
    cat > "$CONF" <<EOF
[service]
service=server
[common]
cubrid_port_id=$PORT
data_buffer_size=256M
log_buffer_size=64M
max_clients=20
enable_string_compression=no
vacuum_worker_count=1
vacuum_master_interval_in_msecs=10
vacuum_log_block_pages=$BLOCK_PAGES
er_log_vacuum=$ER_LOG_VACUUM
EOF
}

# `cubrid server start` leaves its daemons holding our stdout, so piping it here
# would block forever waiting for EOF. Always redirect to a file.
srv() { local tag=$1; shift; cubrid "$@" > "$WORK/cubrid-$tag.log" 2>&1 < /dev/null; }
server_start() {
    srv "start-$1" server start "$DB" || die "server start ($1) failed"
    grep -q success "$WORK/cubrid-start-$1.log" \
        || die "server did not start ($1): $(cat "$WORK/cubrid-start-$1.log")"
}
server_stop() { srv "stop-$1" server stop "$DB" || die "server stop ($1) failed"; }

sql() { csql -u dba -C "$DB" -c "$1" > "$WORK/sql.out" 2>&1 < /dev/null; }
sql_file() { csql -u dba -C "$DB" -i "$1" > "$2" 2>&1 < /dev/null; }
scalar() { sed -n 's/^ *\([0-9][0-9]*\) *$/\1/p' "$WORK/sql.out" | head -1; }
count_in_log() { local c; c=$(grep -ac "$1" "$SRVLOG" 2>/dev/null); echo "${c:-0}"; }

ooslog_offset() { stat -c%s "$OOSLOG" 2>/dev/null || echo 0; }

# OOS OIDs deleted since byte offset $1, as "vol|page|slot".
deleted_oids_since() {
    tail -c "+$(( $1 + 1 ))" "$OOSLOG" 2>/dev/null |
        sed -n 's/.*deleted chunk at oid={vol=\([0-9-]*\),page=\([0-9-]*\),slot=\([0-9-]*\)}.*/\1|\2|\3/p'
}
deleted_count_since() { deleted_oids_since "$1" | wc -l; }

payload_expr() { # $1 = hex unit
    printf "CAST(CONCAT(LPAD(HEX(id),8,'0'), REPEAT('%s',%s)) AS BIT VARYING)" "$1" "$PAYLOAD_UNITS"
}

gen_inserts() { # $1 first id, $2 count, $3 gen marker, $4 hex unit, $5 out file
    awk -v first="$1" -v n="$2" -v g="$3" -v unit="$4" -v units="$PAYLOAD_UNITS" '
      BEGIN {
        for (i = 0; i < n; i++) {
          id = first + i
          printf "INSERT INTO t VALUES (%d, %d, CAST(CONCAT(\x27%08X\x27, REPEAT(\x27%s\x27,%d)) AS BIT VARYING));\n",
                 id, g, id, unit, units
        }
      }' > "$5"
}

# ================================================================== phase 0
say "phase 0 — recreate $DB with a 16K page size"
note "work dir : $WORK"
write_conf
srv stop-pre server stop "$DB" || true
cubrid deletedb "$DB" > "$WORK/deletedb.log" 2>&1 < /dev/null || true
rm -rf "$CUBRID_DATABASES/$DB"
mkdir -p "$CUBRID_DATABASES/$DB"
cubrid createdb --db-page-size=16K --db-volume-size=512M --log-volume-size=512M \
    "$DB" en_US.utf8 -F "$CUBRID_DATABASES/$DB" > "$WORK/createdb.log" 2>&1 < /dev/null \
    || die "createdb failed, see $WORK/createdb.log"
server_start initial
sql "CREATE TABLE t (id INT PRIMARY KEY, gen INT, payload BIT VARYING); COMMIT;"
grep -q 'Execute OK' "$WORK/sql.out" || die "CREATE TABLE failed: $(cat "$WORK/sql.out")"

# ================================================================== phase 1
say "phase 1 — insert R1, OOS-backed"
gen_inserts 1 "$ROWS" 1 AA "$WORK/insert_r1.sql"
for w in $(seq 1 "$R3_WRITERS"); do
    gen_inserts $(( ROWS + 1 + (w - 1) * R3_ROWS )) "$R3_ROWS" 3 DD "$WORK/insert_r3_$w.sql"
done
sql_file "$WORK/insert_r1.sql" "$WORK/insert_r1.out"
R1_OK=$(grep -c 'row affected' "$WORK/insert_r1.out")
[ "$R1_OK" -eq "$ROWS" ] || die "R1 inserted $R1_OK of $ROWS rows, see $WORK/insert_r1.out"
note "R1: $R1_OK rows, payload 5000 B each"

# ================================================================== phase 2
say "phase 2 — UPDATE, let live inserts take the freed slots, then stop mid-block"
OFF_A=$(ooslog_offset)
sql "UPDATE t SET payload = CAST(CONCAT(LPAD(HEX(id),8,'0'), REPEAT('BB',$PAYLOAD_UNITS)) AS BIT VARYING); COMMIT;"
grep -q 'rows affected' "$WORK/sql.out" || die "UPDATE failed: $(cat "$WORK/sql.out")"
note "R1 updated to 'BB' — $ROWS 'AA' chains now live only in the undo image"

R3_PIDS=()
for w in $(seq 1 "$R3_WRITERS"); do
    sql_file "$WORK/insert_r3_$w.sql" "$WORK/insert_r3_$w.out" &
    R3_PIDS+=("$!")
done
TARGET=$(( ROWS * STOP_AT_PCT / 100 ))
note "$R3_WRITERS R3 writers inserting; stopping once vacuum has freed $TARGET chains"
for _ in $(seq 1 2000); do
    [ "$(deleted_count_since "$OFF_A")" -ge "$TARGET" ] && break
    sleep 0.05
done

server_stop mid
kill "${R3_PIDS[@]}" 2>/dev/null; wait "${R3_PIDS[@]}" 2>/dev/null

deleted_oids_since "$OFF_A" | sort -u > "$WORK/deleted_A.txt"
FREED=$(wc -l < "$WORK/deleted_A.txt")
INTR=$(count_in_log 'is interrupted!')
note "pass 1 freed $FREED of $ROWS chains, leaving $(( ROWS - FREED )) unreclaimed"
note "R3 rows committed before the stop: $(cat "$WORK"/insert_r3_*.out | grep -c 'row affected')"
note "vacuum blocks abandoned mid-walk: $INTR"
[ "$FREED" -eq 0 ] && die "vacuum freed nothing (server log: $SRVLOG)"
if [ "$INTR" -eq 0 ]; then
    note "(no block logged 'interrupted'. That message only appears when the"
    note " master processes the finished-job queue before going down; a block"
    note " left IN_PROGRESS on the vacuum data page is converted to interrupted"
    note " at load time instead, and re-walked just the same.)"
fi

# ================================================================== phase 3
say "phase 3 — restart, and let vacuum re-walk the abandoned block"
OFF_C=$(ooslog_offset)
server_start retry

note "waiting for vacuum to go quiet..."
last=-1; stable=0
for _ in $(seq 1 900); do
    n=$(deleted_count_since "$OFF_C")
    if [ "$n" -eq "$last" ]; then
        stable=$(( stable + 1 )); [ "$stable" -ge 10 ] && break
    else
        stable=0; last=$n
    fi
    sleep 0.5
done
note "the retry deleted $last chunks"

deleted_oids_since "$OFF_C" | sort -u > "$WORK/deleted_C.txt"
comm -12 "$WORK/deleted_A.txt" "$WORK/deleted_C.txt" > "$WORK/double_deleted.txt"
DOUBLE=$(wc -l < "$WORK/double_deleted.txt")

# ================================================================== phase 4
say "phase 4 — verdict"

# Verify in id ranges rather than one statement over the table: the first
# unreadable row aborts its statement, and a single statement would then hide
# every other row behind it.
verify_range() { # $1 lo, $2 hi, $3 hex unit, $4 label -> "unreadable_ranges mismatched_rows"
    local lo=$1 hi=$2 unit=$3 label=$4 err=0 bad=0 i j n
    : > "$WORK/verify_$label.log"
    for (( i = lo; i <= hi; i += VERIFY_CHUNK )); do
        j=$(( i + VERIFY_CHUNK - 1 )); [ "$j" -gt "$hi" ] && j=$hi
        csql -u dba -C "$DB" -c \
            "SELECT COUNT(*) FROM t WHERE id BETWEEN $i AND $j AND payload <> $(payload_expr "$unit");" \
            > "$WORK/vchunk.out" 2>&1 < /dev/null
        if grep -q 'ERROR' "$WORK/vchunk.out"; then
            err=$(( err + 1 ))
            { printf -- '--- ids %d..%d\n' "$i" "$j"; cat "$WORK/vchunk.out"; } >> "$WORK/verify_$label.log"
        else
            n=$(sed -n 's/^ *\([0-9][0-9]*\) *$/\1/p' "$WORK/vchunk.out" | head -1)
            bad=$(( bad + ${n:-0} ))
        fi
    done
    echo "$err $bad"
}

sql "SELECT COUNT(*) FROM t WHERE gen = 3;"
GEN3=$(scalar)
GEN3_HI=$(( ROWS + R3_WRITERS * R3_ROWS ))

note "verifying gen-1 (ids 1..$ROWS) — the control..."
read -r CTRL_ERR CTRL_BAD <<< "$(verify_range 1 "$ROWS" BB gen1)"
note "verifying gen-3 (ids $(( ROWS + 1 ))..$GEN3_HI) — the victims..."
read -r VIC_ERR VIC_BAD <<< "$(verify_range $(( ROWS + 1 )) "$GEN3_HI" DD gen3)"

printf '    committed gen-3 rows                   : %s\n' "${GEN3:-?}"
printf '    OOS OIDs deleted in both vacuum passes : %s\n' "$DOUBLE"
printf '    gen-1 control (chains predate any free): %s unreadable ranges, %s rows wrong\n' \
    "$CTRL_ERR" "$CTRL_BAD"
printf '    gen-3 victims                          : %s unreadable ranges, %s rows wrong\n' \
    "$VIC_ERR" "$VIC_BAD"

REPRO=no
if [ "$DOUBLE" -gt 0 ]; then
    REPRO=yes
    say "CORROBORATING — $DOUBLE OOS OIDs were deleted by both vacuum passes"
    head -6 "$WORK/double_deleted.txt" | sed 's/^/    vol|page|slot  /'
    [ "$DOUBLE" -gt 6 ] && note "... and $(( DOUBLE - 6 )) more, in $WORK/double_deleted.txt"
    note "a chunk is only deleted when its slot is occupied, so every one of"
    note "these slots had been handed out again between the two deletes"
fi
if [ "$VIC_ERR" -gt 0 ] || [ "$VIC_BAD" -gt 0 ]; then
    REPRO=yes
    say "REPRODUCED — committed gen-3 rows lost their OOS values"
    note "these rows were inserted and committed after their slot was freed, and"
    note "were never touched again, yet their payload can no longer be read:"
    : > "$WORK/damaged_ids.txt"
    while read -r lo hi; do
        for (( k = lo; k <= hi; k++ )); do
            csql -u dba -C "$DB" -c "SELECT COUNT(*) FROM t WHERE id = $k AND payload <> $(payload_expr DD);" \
                > "$WORK/vrow.out" 2>&1 < /dev/null
            grep -q 'ERROR' "$WORK/vrow.out" && echo "$k" >> "$WORK/damaged_ids.txt"
        done
    done < <(sed -n 's/^--- ids \([0-9]*\)\.\.\([0-9]*\)$/\1 \2/p' "$WORK/verify_gen3.log")
    DAMAGED=$(wc -l < "$WORK/damaged_ids.txt")
    note "$DAMAGED gen-3 rows are unreadable, for example ids: $(head -6 "$WORK/damaged_ids.txt" | tr '\n' ' ')"
    note "full list: $WORK/damaged_ids.txt"
    printf '    the server reports, for one of them:\n'
    grep -a -m1 'ERROR' "$WORK/verify_gen3.log" | sed 's/^/    /'
fi
if [ "$CTRL_ERR" -gt 0 ] || [ "$CTRL_BAD" -gt 0 ]; then
    note "NOTE: the gen-1 control is also damaged ($WORK/verify_gen1.log)."
    note "      Expected clean — their chains were written before any delete."
fi

say "artifacts"
note "work dir   : $WORK"
note "oos.log    : $OOSLOG"
note "server log : $SRVLOG"
note "database   : $DB (still running; 'cubrid server stop $DB' to stop)"

if [ "$REPRO" = no ]; then
    say "NOT reproduced in this run"
    note "if pass 1 freed everything, lower STOP_AT_PCT or raise ROWS so a"
    note "backlog survives the stop; if it left a backlog but nothing was"
    note "double-deleted, raise R3_WRITERS so live inserts keep up with the"
    note "slots vacuum is freeing."
    exit 1
fi
exit 0
