set -u
# runs INSIDE the namespace as (mapped) root; $CUBRID etc. inherited from t16env.sh
MNT=$1; OUT=$2; SIZE=$3
mount -t tmpfs -o size=$SIZE tmpfs "$MNT" || { echo "mount failed rc=$?"; exit 97; }
echo "inside: uid=$(id -u) pid=$$"; df -B1 --output=source,size,used,avail,target "$MNT"
export CUBRID_DATABASES=/home/vimkim/.cub/campaign/cbrd-26659/ticket16/boundedfs/dbs_tmpfs
mkdir -p "$MNT/db"
cubrid createdb --db-volume-size=16M --log-volume-size=20M -F "$MNT/db" -L "$MNT/db" bfs en_US > "$OUT/A-createdb.out" 2>&1
echo "createdb rc=$?"; df -B1 --output=size,used,avail "$MNT" | tail -1; ls -la "$MNT/db"
# fill: 12 KiB OOS values, one statement per row (autocommit) so the first failing statement is visible
python3 - > "$OUT/A-fill.sql" <<'PY'
print("CREATE TABLE t (id INT, v BIT VARYING);")
for i in range(1, 12001):
    print(f"INSERT INTO t VALUES ({i}, CAST(REPEAT('EE', 12000) AS BIT VARYING));")
print("SELECT COUNT(*) FROM t; SHOW HEAP OOS OF t;")
PY
mkdir -p "$OUT/A-cores" && cd "$OUT/A-cores"
csql -S -u dba bfs -i "$OUT/A-fill.sql" > "$OUT/A-fill.out" 2>&1
echo "fill csql rc=$?"
echo "--- fill outcome (first error and tail):"; grep -n -m3 -B2 -A2 "ERROR" "$OUT/A-fill.out"; tail -5 "$OUT/A-fill.out"
echo "--- rows inserted: $(grep -c '1 row affected' "$OUT/A-fill.out")"
df -B1 --output=size,used,avail "$MNT" | tail -1; ls -la "$MNT/db"
cp "$CUBRID"/log/*bfs*.err "$OUT/" 2>/dev/null
# read back what survived (the standalone process may have died; a fresh open recovers)
csql -S -u dba bfs -c "SELECT COUNT(*) FROM t; SHOW HEAP OOS OF t;" > "$OUT/A-readback.out" 2>&1
echo "readback rc=$?"; tail -12 "$OUT/A-readback.out"
echo "inside-done"
