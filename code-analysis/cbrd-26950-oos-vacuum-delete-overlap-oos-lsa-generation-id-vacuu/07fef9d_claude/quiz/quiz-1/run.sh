#!/usr/bin/env bash
#
# quiz-1 — normal forward-walk reclaim, self-contained observation.
# Creates/uses ONLY its own database (oos26950q1). Debug build required (oos.log).
# Usage: bash run.sh          (full run + auto-cleanup)
#        bash run.sh cleanup  (cleanup only)
set -uo pipefail
DB=oos26950q1
ROWS=2000
UNITS=4996                       # 8 + 2*4996 hex = 5000 B payload
HERE="$(cd "$(dirname "$0")" && pwd)"
WORK="$HERE/work"
mkdir -p "$WORK"
CONF="$WORK/cubrid.conf"
export CUBRID_CONF_FILE="$CONF"
OOSLOG="$CUBRID/log/oos.log"

die() { printf 'FAIL: %s\n' "$*" >&2; exit 2; }
[ -n "${CUBRID:-}" ] || die 'CUBRID not set'
command -v csql >/dev/null || die 'csql not on PATH'

cleanup() {
    cubrid server stop "$DB" > /dev/null 2>&1 < /dev/null || true
    cubrid deletedb "$DB" > /dev/null 2>&1 < /dev/null || true
    rm -rf "${CUBRID_DATABASES:?}/$DB"
    echo "cleanup: $DB removed"
}
[ "${1:-}" = cleanup ] && { cleanup; exit 0; }

cat > "$CONF" <<EOF
[service]
service=server
[common]
cubrid_port_id=1523
data_buffer_size=256M
log_buffer_size=64M
max_clients=20
enable_string_compression=no
vacuum_worker_count=1
vacuum_master_interval_in_msecs=10
stored_procedure=no
EOF

echo "== setup: recreate $DB"
cleanup > /dev/null
mkdir -p "$CUBRID_DATABASES/$DB"
cubrid createdb --db-page-size=16K --db-volume-size=512M --log-volume-size=512M \
    "$DB" en_US.utf8 -F "$CUBRID_DATABASES/$DB" > "$WORK/createdb.log" 2>&1 < /dev/null \
    || die "createdb failed ($WORK/createdb.log)"
cubrid server start "$DB" > "$WORK/start.log" 2>&1 < /dev/null
grep -q success "$WORK/start.log" || die "server start failed ($WORK/start.log)"
csql -u dba -C "$DB" -c "CREATE TABLE t (id INT PRIMARY KEY, gen INT, payload BIT VARYING); COMMIT;" \
    > /dev/null 2>&1 < /dev/null

echo "== insert $ROWS OOS-backed rows (5000 B each)"
awk -v n="$ROWS" -v u="$UNITS" 'BEGIN{for(i=1;i<=n;i++)
  printf "INSERT INTO t VALUES (%d, 1, CAST(CONCAT(\x27%08X\x27, REPEAT(\x27AA\x27,%d)) AS BIT VARYING));\n", i, i, u}' \
  > "$WORK/insert.sql"
csql -u dba -C "$DB" -i "$WORK/insert.sql" > "$WORK/insert.out" 2>&1 < /dev/null
[ "$(grep -c 'row affected' "$WORK/insert.out")" -eq "$ROWS" ] || die "insert incomplete"

OFF=$(stat -c%s "$OOSLOG" 2>/dev/null || echo 0)
echo "== update all rows in one transaction (old chains -> undo images only)"
csql -u dba -C "$DB" -c \
  "UPDATE t SET payload = CAST(CONCAT(LPAD(HEX(id),8,'0'), REPEAT('BB',$UNITS)) AS BIT VARYING); COMMIT;" \
  > /dev/null 2>&1 < /dev/null

echo "== wait for vacuum to reclaim $ROWS old chains (pushing filler log traffic)"
deleted() { tail -c "+$(( OFF + 1 ))" "$OOSLOG" 2>/dev/null | grep -ac 'deleted chunk at oid=' || true; }
inserted() { tail -c "+$(( OFF + 1 ))" "$OOSLOG" 2>/dev/null | grep -ac 'inserted to oid=' || true; }
ok=0
for i in $(seq 1 300); do
    [ "$(deleted)" -ge "$ROWS" ] && { ok=1; break; }
    awk -v it="$i" -v u="$UNITS" 'BEGIN{for(k=1;k<=40;k++)
      printf "INSERT INTO t VALUES (%d, 0, CAST(REPEAT(\x27FF\x27,%d) AS BIT VARYING));\n", -(it*1000+k), u; print "COMMIT;"}' \
      > "$WORK/filler.sql"
    csql -u dba -C "$DB" -i "$WORK/filler.sql" > /dev/null 2>&1 < /dev/null
    sleep 0.5
done
[ "$ok" -eq 1 ] || { cleanup; die "vacuum did not reclaim in time (deleted=$(deleted))"; }
csql -u dba -C "$DB" -c "DELETE FROM t WHERE gen = 0; COMMIT;" > /dev/null 2>&1 < /dev/null

echo "== verify live values after reclamation"
csql -u dba -C "$DB" -c \
  "SELECT COUNT(*), SUM(CASE WHEN payload <> CAST(CONCAT(LPAD(HEX(id),8,'0'), REPEAT('BB',$UNITS)) AS BIT VARYING) THEN 1 ELSE 0 END) FROM t WHERE gen = 1;" \
  > "$WORK/verify.out" 2>&1 < /dev/null
TOTAL=$(sed -n 's/^ *\([0-9][0-9]*\)  *\([0-9][0-9]*\) *$/\1/p' "$WORK/verify.out" | head -1)
BAD=$(sed -n 's/^ *\([0-9][0-9]*\)  *\([0-9][0-9]*\) *$/\2/p' "$WORK/verify.out" | head -1)
printf '\n   verify: total=%s mismatch=%s   (expected: 2000 / 0)\n' "${TOTAL:-?}" "${BAD:-?}"
printf '   oos.log deletes since update: %s   (expected: >= 2000)\n' "$(deleted)"
printf '   oos.log inserts since update: %s   <-- P3 의 답과 비교하라\n\n' "$(inserted)"
cleanup
[ "${TOTAL:-0}" -eq "$ROWS" ] && [ "${BAD:-1}" -eq 0 ] || die "verification failed"
echo "quiz-1 run complete"
