#!/usr/bin/env bash
# Exercise the derived OOS boundaries against one installed build of the pinned engine.
#
#   probe_boundaries.sh <install-dir> <db-prefix> <out-dir> [cs]
#
# Creates three disposable databases (<db-prefix>16k/8k/4k) under a dedicated CUBRID_DATABASES,
# runs the boundary SQL in standalone mode, dumps SHOW HEAP OOS, oos.log, diagdb and spacedb
# evidence, and optionally starts one client-server instance (16 KiB) on a private port.
# It never touches databases or processes outside its own CUBRID_DATABASES / port.
set -u

INSTALL=${1:?install dir}
PREFIX=${2:?db name prefix}
OUT=${3:?output dir}
DO_CS=${4:-}
PORT=26659

export CUBRID="$INSTALL"
export CUBRID_DATABASES="$HOME/.cub/db/oos-baseline-f4299ac0c/commondb"
export PATH="$CUBRID/bin:$PATH"
export LD_LIBRARY_PATH="$CUBRID/lib:$CUBRID/cci/lib:${LD_LIBRARY_PATH:-}"
mkdir -p "$CUBRID_DATABASES" "$OUT"
cd "$CUBRID_DATABASES" || exit 1

# private port so this install's master never collides with other installs
if command -v crudini >/dev/null 2>&1; then
  crudini --set "$CUBRID/conf/cubrid.conf" common cubrid_port_id "$PORT"
else
  sed -i "s/^#\?cubrid_port_id=.*/cubrid_port_id=$PORT/" "$CUBRID/conf/cubrid.conf"
fi

{
  echo "install=$CUBRID"
  echo "databases=$CUBRID_DATABASES"
  echo "port=$(grep '^cubrid_port_id' "$CUBRID/conf/cubrid.conf")"
  cubrid_rel
} > "$OUT/identity.txt" 2>&1

# tag  io  gate_in gate_out norm  ch1   ch2   fok   frej  kfloor
BOUNDS=(
  "16k 16K 4035 4036 4012 16283 16284 16176 16177 4086"
  "8k   8K 1987 1988 1964  8091  8092  7984  7985 2038"
  "4k   4K  963  964  940  3995  3996  3888  3889 1014"
)

OOSLOG="$CUBRID/log/oos.log"
echo "oos.log lines before: $(wc -l < "$OOSLOG" 2>/dev/null || echo 0)" > "$OUT/ooslog-summary.txt"

for row in "${BOUNDS[@]}"; do
  read -r tag io gin gout norm ch1 ch2 fok frej kfloor <<<"$row"
  db="${PREFIX}${tag}"
  sql="$OUT/probe_${tag}.sql"
  out="$OUT/probe_${tag}.out"

  cubrid deletedb "$db" >/dev/null 2>&1 || true
  if ! cubrid createdb --db-volume-size=64M --log-volume-size=32M \
        --db-page-size="$io" --log-page-size="$io" "$db" en_US.utf8 > "$OUT/createdb_${tag}.log" 2>&1; then
    echo "createdb $db FAILED" | tee -a "$OUT/createdb_${tag}.log"
    continue
  fi

  cat > "$sql" <<EOF
-- pinned engine f4299ac0c, ${io} pages, database ${db}
-- 1. record gate (schema A: id INT, v BIT VARYING)
CREATE TABLE a_in   (id INT, v BIT VARYING);
CREATE TABLE a_out  (id INT, v BIT VARYING);
CREATE TABLE a_norm (id INT, v BIT VARYING);
INSERT INTO a_in   VALUES (1, CAST(REPEAT('AA', ${gin})  AS BIT VARYING));
INSERT INTO a_out  VALUES (1, CAST(REPEAT('BB', ${gout}) AS BIT VARYING));
INSERT INTO a_norm VALUES (1, CAST(REPEAT('CC', ${norm}) AS BIT VARYING));
SELECT 'a_in ${gin}'   AS probe, (v = CAST(REPEAT('AA', ${gin})  AS BIT VARYING)) AS whole_value_eq, LENGTH(v)/8 AS bytes, DISK_SIZE(v) AS disk_size FROM a_in;
SELECT 'a_out ${gout}' AS probe, (v = CAST(REPEAT('BB', ${gout}) AS BIT VARYING)) AS whole_value_eq, LENGTH(v)/8 AS bytes, DISK_SIZE(v) AS disk_size FROM a_out;
SELECT 'a_norm ${norm}' AS probe, (v = CAST(REPEAT('CC', ${norm}) AS BIT VARYING)) AS whole_value_eq, LENGTH(v)/8 AS bytes, DISK_SIZE(v) AS disk_size FROM a_norm;
SHOW HEAP OOS OF a_in;
SHOW HEAP OOS OF a_out;
SHOW HEAP OOS OF a_norm;
-- 2. single-to-multi chunk boundary
CREATE TABLE c1 (id INT, v BIT VARYING);
CREATE TABLE c2 (id INT, v BIT VARYING);
INSERT INTO c1 VALUES (1, CAST(REPEAT('AB', ${ch1}) AS BIT VARYING));
INSERT INTO c2 VALUES (1, CAST(REPEAT('CD', ${ch2}) AS BIT VARYING));
SELECT 'c1 ${ch1}' AS probe, (v = CAST(REPEAT('AB', ${ch1}) AS BIT VARYING)) AS whole_value_eq, LENGTH(v)/8 AS bytes FROM c1;
SELECT 'c2 ${ch2}' AS probe, (v = CAST(REPEAT('CD', ${ch2}) AS BIT VARYING)) AS whole_value_eq, LENGTH(v)/8 AS bytes FROM c2;
SHOW HEAP OOS OF c1;
SHOW HEAP OOS OF c2;
-- 3. eligibility floor: fixed BIT pushes the record over the gate; s is the only candidate
CREATE TABLE e15 (id INT, f BIT($((kfloor*8))), s BIT VARYING);
CREATE TABLE e16 (id INT, f BIT($((kfloor*8))), s BIT VARYING);
CREATE TABLE e23 (id INT, f BIT($((kfloor*8))), s BIT VARYING);
CREATE TABLE e24 (id INT, f BIT($((kfloor*8))), s BIT VARYING);
INSERT INTO e15 VALUES (1, CAST(REPEAT('AA', ${kfloor}) AS BIT($((kfloor*8)))), CAST(REPEAT('D1', 15) AS BIT VARYING));
INSERT INTO e16 VALUES (1, CAST(REPEAT('AA', ${kfloor}) AS BIT($((kfloor*8)))), CAST(REPEAT('D2', 16) AS BIT VARYING));
INSERT INTO e23 VALUES (1, CAST(REPEAT('AA', ${kfloor}) AS BIT($((kfloor*8)))), CAST(REPEAT('D3', 23) AS BIT VARYING));
INSERT INTO e24 VALUES (1, CAST(REPEAT('AA', ${kfloor}) AS BIT($((kfloor*8)))), CAST(REPEAT('D4', 24) AS BIT VARYING));
SHOW HEAP OOS OF e15;
SHOW HEAP OOS OF e16;
SHOW HEAP OOS OF e23;
SHOW HEAP OOS OF e24;
SELECT 'e16' AS probe, (s = CAST(REPEAT('D2', 16) AS BIT VARYING)) AS whole_value_eq FROM e16;
SELECT 'e24' AS probe, (s = CAST(REPEAT('D4', 24) AS BIT VARYING)) AS whole_value_eq FROM e24;
-- 4. OOS + bigone rejection
CREATE TABLE b_ok  (id INT, f BIT($((fok*8))),  v BIT VARYING);
CREATE TABLE b_rej (id INT, f BIT($((frej*8))), v BIT VARYING);
INSERT INTO b_ok  VALUES (1, CAST(REPEAT('AA', ${fok})  AS BIT($((fok*8)))),  CAST(REPEAT('EE', 64) AS BIT VARYING));
INSERT INTO b_rej VALUES (1, CAST(REPEAT('AA', ${frej}) AS BIT($((frej*8)))), CAST(REPEAT('EE', 64) AS BIT VARYING));
SELECT 'b_ok rows' AS probe, COUNT(*) FROM b_ok;
SELECT 'b_rej rows' AS probe, COUNT(*) FROM b_rej;
SHOW HEAP OOS OF b_ok;
SHOW HEAP OOS OF b_rej;
-- 5. placement hints present at the pin (syntax only)
CREATE TABLE h (id INT, p BIT VARYING STORAGE PREFER_INLINE, q BIT VARYING STORAGE FORCE_OUTLINE);
INSERT INTO h VALUES (1, CAST(REPEAT('AA', 40) AS BIT VARYING), CAST(REPEAT('BB', 40) AS BIT VARYING));
SHOW HEAP OOS OF h;
EOF

  csql -S -u dba "$db" -i "$sql" > "$out" 2>&1
  echo "csql exit=$? for $db" >> "$out"

  # release-build diagnostics
  cubrid diagdb -d 1 "$db" > "$OUT/diagdb_d1_${tag}.txt" 2>&1
  cubrid diagdb -d 2 "$db" > "$OUT/diagdb_d2_${tag}.txt" 2>&1
  cubrid spacedb -S -p "$db" > "$OUT/spacedb_p_${tag}.txt" 2>&1
  cubrid spacedb -S "$db" > "$OUT/spacedb_${tag}.txt" 2>&1
  cubrid checkdb -S "$db" > "$OUT/checkdb_${tag}.txt" 2>&1
  echo "checkdb exit=$?" >> "$OUT/checkdb_${tag}.txt"
done

{
  echo "oos.log lines after: $(wc -l < "$OOSLOG" 2>/dev/null || echo 0)"
  echo "oos_insert lines: $(grep -c 'oos_insert' "$OOSLOG" 2>/dev/null || echo 0)"
  echo "--- last 12 lines ---"
  tail -12 "$OOSLOG" 2>/dev/null
} >> "$OUT/ooslog-summary.txt"

if [ "$DO_CS" = "cs" ]; then
  db="${PREFIX}16k"
  {
    cubrid server start "$db"
    for _ in $(seq 1 60); do
      if cubrid server status 2>/dev/null | grep -q "$db"; then break; fi
      sleep 1
    done
    cubrid server status
    csql -u dba "$db" -c "SHOW HEAP OOS OF a_out; SELECT 'cs a_out' AS probe, LENGTH(v)/8 AS bytes FROM a_out;"
    echo "csql cs exit=$?"
    cubrid server stop "$db"
    cubrid service stop
    pgrep -a -f "$CUBRID/bin/cub_" || echo "no cub_ processes from $CUBRID remain"
  } > "$OUT/cs_mode_16k.txt" 2>&1
fi

echo "done: $OUT"
