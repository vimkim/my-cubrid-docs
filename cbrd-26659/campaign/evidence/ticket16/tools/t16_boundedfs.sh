#!/bin/bash
# CBRD-26659 campaign ticket 16 -- bounded test filesystem for space-exhaustion experiments (no root).
#
# Mechanism: an unprivileged user namespace with the current user mapped to root inside
# (unshare --user --map-root-user), a private mount namespace, and a size-bounded tmpfs mounted on a
# directory under this ticket's home. A private PID namespace makes the whole run collapse when the
# namespace leader exits, so nothing can be left running on the disposable filesystem.
#
# Variant A (tmpfs, 256 MiB): a standalone-mode database whose volumes and log live on the tmpfs is filled
#   with OOS rows until the filesystem is exhausted. Writes are confined: the tmpfs vanishes with the
#   namespace, the mount point is empty outside, and /home usage is unchanged.
# Variant B (CUBRID-level bound, on disk): a database created with a 16 MiB primary volume is filled the
#   same way to show what the engine itself bounds (nothing: permanent data volumes auto-extend).
#
# Both variants run in standalone mode (csql -S), so no port and no cub_master is involved.
set -u
# shellcheck disable=SC1091
source /home/vimkim/.cub/campaign/cbrd-26659/ticket16/tools/t16env.sh
B=$T16/boundedfs
OUT=$B/out
MNT=$B/mnt
mkdir -p "$OUT" "$MNT" "$B/dbs_tmpfs" "$B/dbs_disk"
J=$OUT/journal.txt
log () { printf '%s %s\n' "$(date +%H:%M:%S)" "$*" | tee -a "$J"; }

log "=== variant A: tmpfs in an unprivileged user+mount+pid namespace"
df -B1 --output=source,size,used,avail,target /home > "$OUT/A-home-df-before.txt"
ls -la "$MNT" > "$OUT/A-mnt-before.txt"
: > "$B/dbs_tmpfs/databases.txt"

cat > "$B/inner_A.sh" <<'EOF'
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
EOF
unshare --user --map-root-user --mount --pid --fork --mount-proc --ipc -- bash "$B/inner_A.sh" "$MNT" "$OUT" 256m > "$OUT/A-inner.txt" 2>&1
log "variant A namespace exited rc=$? ; inner log: $OUT/A-inner.txt"
sed 's/^/    /' "$OUT/A-inner.txt" | tee -a "$J"
ls -la "$MNT" > "$OUT/A-mnt-after.txt"
df -B1 --output=source,size,used,avail,target /home > "$OUT/A-home-df-after.txt"
log "outside after: mnt entries=$(find "$MNT" -mindepth 1 | wc -l) ; /home used before=$(awk 'NR==2{print $3}' "$OUT/A-home-df-before.txt") after=$(awk 'NR==2{print $3}' "$OUT/A-home-df-after.txt")"
mount | grep -c "$MNT" > "$OUT/A-mount-visible-outside.txt"; log "tmpfs visible outside the namespace: $(cat "$OUT/A-mount-visible-outside.txt") mount(s)"

log "=== variant B: CUBRID-level bound (16 MiB primary volume on disk, no filesystem bound)"
export CUBRID_DATABASES=$B/dbs_disk
: > "$CUBRID_DATABASES/databases.txt"; rm -rf "$B/dbs_disk/bdisk"; mkdir -p "$B/dbs_disk/bdisk"
cubrid createdb --db-volume-size=16M --log-volume-size=20M -F "$B/dbs_disk/bdisk" -L "$B/dbs_disk/bdisk" bdisk en_US > "$OUT/B-createdb.out" 2>&1
log "createdb bdisk rc=$?"
ls -la "$B/dbs_disk/bdisk" > "$OUT/B-volumes-before.txt"
csql -S -u dba bdisk -c "CREATE TABLE t (id INT, v BIT VARYING); INSERT INTO t SELECT ROWNUM, CAST(REPEAT('EE', 12000) AS BIT VARYING) FROM db_class a, db_class b LIMIT 1500; SELECT COUNT(*) FROM t; SHOW HEAP OOS OF t;" > "$OUT/B-fill.out" 2>&1
log "variant B fill rc=$? ; $(grep -E '^ +[0-9]+$' "$OUT/B-fill.out" | head -1 | tr -d ' ') rows"
ls -la "$B/dbs_disk/bdisk" > "$OUT/B-volumes-after.txt"
log "volumes after: $(grep -E 'bdisk(_x[0-9]+)?$' "$OUT/B-volumes-after.txt" | awk '{print $NF" "$5}' | tr '\n' ';')"
cat "$B/dbs_disk/bdisk/bdisk_vinf" > "$OUT/B-vinf-after.txt"
log "done"
