#!/bin/bash
# CBRD-26659 campaign ticket 16 -- corruption-detection procedure on COPIED database, page and log images.
#
# Never touches a live database: two source images are built once in standalone mode under their own
# CUBRID_DATABASES, hashed, and then only raw COPIES (own directory, own databases.txt, rewritten _vinf
# paths) are corrupted and read. The sources are re-hashed at the end to prove they were not modified.
#
# Experiments (each on its own copy):
#   E0  clean copy            checkdb and whole-value reads pass -> the copy procedure itself is sound
#   E1  payload bytes         XOR 32 bytes inside a chunk payload of row 1
#   E2  chunk header          overwrite the head chunk's length field of row 2 (multi-chunk value)
#   E3  slotted-page header   XOR the num_slots/num_records fields of an OOS data page
#   E4c clean crash image     the kill -9 image recovers on open (control for E4)
#   E4  log page bytes        XOR 64 bytes in the last written active-log page of the crash image, then open
#
# Judged against: no OOS-specific detection or recovery guarantee is documented (catalogue OOS-DUR-07,
# Specification gap); the general claim is the manual's "cubrid checkdb ... checks the consistency of a
# database" (admin_utils.rst, checkdb section). Results are recorded as observations, nothing is asserted.
set -u
# shellcheck disable=SC1091
source /home/vimkim/.cub/campaign/cbrd-26659/ticket16/tools/t16env.sh
C=$T16/corruption
TOOLS=$T16/tools
OUT=$C/out
SRCDBS=$C/dbs
rm -rf "$OUT" "$C/copies"; mkdir -p "$OUT" "$C/copies" "$T16/cores"
J=$OUT/journal.txt
log () { printf '%s %s\n' "$(date +%H:%M:%S)" "$*" | tee -a "$J"; }
PS=16384
V1="CAST(REPEAT('AA', 8000) AS BIT VARYING)"
V2="CAST(REPEAT('BB', 20000) AS BIT VARYING)"
V3="CAST(REPEAT('CC', 8000) AS BIT VARYING)"
READS="SELECT id, (v = $V1) AS eq1, (v = $V2) AS eq2, (v = $V3) AS eq3 FROM t ORDER BY id; SHOW HEAP OOS OF t;"

sa_errlogs () {   # copy standalone error logs written since marker $1 into $2
  find "$CUBRID/log" -maxdepth 1 -name '*.err' -newer "$1" -exec cp {} "$2/" \; 2>/dev/null
}

# ---- 1. source images (built once, standalone mode) -----------------------------------------------------
build_sources () {
  export CUBRID_DATABASES=$SRCDBS
  rm -rf "$SRCDBS"; mkdir -p "$SRCDBS/c16k" "$SRCDBS/c16kcr"; : > "$SRCDBS/databases.txt"
  for db in c16k c16kcr; do
    cubrid createdb --db-volume-size=32M --log-volume-size=32M -F "$SRCDBS/$db" -L "$SRCDBS/$db" "$db" en_US > "$OUT/createdb-$db.out" 2>&1
    log "createdb $db rc=$?"
  done
  # clean image: inserts, whole-value reads, clean shutdown of the standalone process
  csql -S -u dba c16k -c "CREATE TABLE t (id INT, v BIT VARYING); INSERT INTO t VALUES (1, $V1); INSERT INTO t VALUES (2, $V2); INSERT INTO t VALUES (3, $V3); $READS" > "$OUT/source-c16k-build.out" 2>&1
  log "c16k build csql rc=$?"
  # crash image: same inserts committed, then the standalone process is killed before it flushes data pages
  csql -S -u dba c16kcr -c "CREATE TABLE t (id INT, v BIT VARYING);" > "$OUT/source-c16kcr-build-1.out" 2>&1
  csql -S -u dba c16kcr -c "INSERT INTO t VALUES (1, $V1); INSERT INTO t VALUES (2, $V2); INSERT INTO t VALUES (3, $V3); COMMIT; SELECT SLEEP(30);" > "$OUT/source-c16kcr-build-2.out" 2>&1 &
  # (stdout of the killed process is lost; the crash image is proven by the E4c recovery reading all three rows)
  local cpid=$!
  sleep 6
  kill -9 "$cpid"; wait "$cpid" 2>/dev/null
  log "c16kcr: csql -S pid $cpid killed with SIGKILL after the committed inserts (crash image)"
  ( cd "$SRCDBS" && sha256sum c16k/c16k c16k/c16k_lgat c16k/c16k_x001 c16kcr/c16kcr c16kcr/c16kcr_lgat c16kcr/c16kcr_x001 2>/dev/null ) > "$OUT/SHA256SUMS.sources.before"
  log "source hashes recorded"
}

# ---- 2. raw copy into a separate registry -----------------------------------------------------------------
make_copy () {   # make_copy <exp> <srcdb>  -> copy at $C/copies/<exp>/<srcdb>, registry $C/copies/<exp>/databases.txt
  local exp=$1 db=$2 dst=$C/copies/$1
  mkdir -p "$dst"
  cp -a "$SRCDBS/$db" "$dst/$db"
  sed -i "s|$SRCDBS/$db/|$dst/$db/|g" "$dst/$db/${db}_vinf"
  printf '#db-name\tvol-path\tdb-host\tlog-path\tlob-base-path\n%s\t%s\tlocalhost\t%s\tfile:%s/lob\n' "$db" "$dst/$db" "$dst/$db" "$dst/$db" > "$dst/databases.txt"
  log "[$exp] raw copy of $db -> $dst/$db (own databases.txt; _vinf paths rewritten)"
}
probe_copy () {   # probe_copy <exp> <db> : checkdb and whole-value reads on the copy, under its own registry
  local exp=$1 db=$2 dst=$C/copies/$1 mark=$OUT/.mark.$1
  touch "$mark"; sleep 1
  ( export CUBRID_DATABASES=$dst; cd "$T16/cores" && cubrid checkdb -S "$db" ) > "$OUT/$exp-checkdb.out" 2>&1
  log "[$exp] checkdb -S rc=$?"
  ( export CUBRID_DATABASES=$dst; cd "$T16/cores" && csql -S -u dba "$db" -c "$READS" ) > "$OUT/$exp-read.out" 2>&1
  log "[$exp] csql -S read rc=$? ; eq columns: $(grep -E '^ +[0-9]+ +[01] ' "$OUT/$exp-read.out" | tr -s ' ' | tr '\n' ';')"
  grep -iE "error|corrupt" "$OUT/$exp-read.out" "$OUT/$exp-checkdb.out" | head -5 | sed 's/^/    /' | tee -a "$J"
  mkdir -p "$OUT/$exp-errlogs"; sa_errlogs "$mark" "$OUT/$exp-errlogs"
  ls "$T16/cores" | grep -c core > "$OUT/$exp-cores.count" 2>/dev/null || true
}

build_sources

# ---- E0: clean copy -------------------------------------------------------------------------------------
make_copy E0 c16k
python3 "$TOOLS/oos_pages.py" scan "$C/copies/E0/c16k/c16k" $PS > "$OUT/E0-oos-pages.json"
log "[E0] PAGE_OOS pages in the primary volume: $(python3 -c "import json;d=json.load(open('$OUT/E0-oos-pages.json'));print([(p['pageid'],p['first_record']['length'],p['first_record']['chunk_index']) for p in d])")"
python3 "$TOOLS/oos_pages.py" scan "$C/copies/E0/c16k/c16k_x001" $PS > "$OUT/E0-oos-pages-x001.json"
log "[E0] PAGE_OOS pages in volume x001: $(python3 -c "import json;d=json.load(open('$OUT/E0-oos-pages-x001.json'));print([(p['pageid'],p['first_record']['length'],p['first_record']['chunk_index']) for p in d])")"
probe_copy E0 c16k

# choose target pages from the scan of the same image (the copies are byte-identical to E0's)
pick () {   # pick <json> <length> <index> -> "volfile pageid"
  python3 - "$1" "$2" "$3" <<'EOF'
import json, sys
d = json.load(open(sys.argv[1])); L = int(sys.argv[2]); I = int(sys.argv[3])
for p in d:
    if p["first_record"]["length"] == L and p["first_record"]["chunk_index"] == I:
        print(p["pageid"]); break
EOF
}
VOL=c16k; SCAN=$OUT/E0-oos-pages.json
if [ ! -s "$SCAN" ] || [ "$(python3 -c "import json;print(len(json.load(open('$SCAN'))))")" = 0 ]; then VOL=c16k_x001; SCAN=$OUT/E0-oos-pages-x001.json; fi
# the chunk header's length field is the serialized value length: ALIGN(5 + N, 4) for BIT VARYING of N >= 32 bytes
P_ROW1=$(pick "$SCAN" 8008 0)
P_HEAD2=$(pick "$SCAN" 20008 0)
if [ -z "$P_ROW1" ] || [ -z "$P_HEAD2" ]; then log "could not locate target pages; abort"; exit 9; fi
log "target pages in volume $VOL: row-1 chunk page=$P_ROW1, row-2 head chunk page=$P_HEAD2"

# ---- E1: payload bytes of row 1 -------------------------------------------------------------------------
make_copy E1 c16k
python3 "$TOOLS/oos_pages.py" xor "$C/copies/E1/c16k/$VOL" $(( P_ROW1 * PS + 64 + 16 + 4000 )) 32 | tee "$OUT/E1-mutation.json" | sed 's/^/    /' >> "$J"
probe_copy E1 c16k

# ---- E2: head chunk header length of row 2 --------------------------------------------------------------
make_copy E2 c16k
python3 "$TOOLS/oos_pages.py" set4 "$C/copies/E2/c16k/$VOL" $(( P_HEAD2 * PS + 64 )) 4660 | tee "$OUT/E2-mutation.json" | sed 's/^/    /' >> "$J"
probe_copy E2 c16k

# ---- E3: slotted-page header of the row-1 page ----------------------------------------------------------
make_copy E3 c16k
python3 "$TOOLS/oos_pages.py" xor "$C/copies/E3/c16k/$VOL" $(( P_ROW1 * PS + 32 )) 4 | tee "$OUT/E3-mutation.json" | sed 's/^/    /' >> "$J"
probe_copy E3 c16k

# ---- E4c: clean crash image recovers --------------------------------------------------------------------
make_copy E4c c16kcr
probe_copy E4c c16kcr

# ---- E4: log page bytes of the crash image --------------------------------------------------------------
make_copy E4 c16kcr
LASTPG=$(python3 "$TOOLS/oos_pages.py" lastpage "$C/copies/E4/c16kcr/c16kcr_lgat" $PS)
log "[E4] last non-zero active log page: $LASTPG"
python3 "$TOOLS/oos_pages.py" xor "$C/copies/E4/c16kcr/c16kcr_lgat" $(( LASTPG * PS + 4096 )) 64 | tee "$OUT/E4-mutation.json" | sed 's/^/    /' >> "$J"
probe_copy E4 c16kcr

# ---- sources untouched -----------------------------------------------------------------------------------
( cd "$SRCDBS" && sha256sum c16k/c16k c16k/c16k_lgat c16k/c16k_x001 c16kcr/c16kcr c16kcr/c16kcr_lgat c16kcr/c16kcr_x001 2>/dev/null ) > "$OUT/SHA256SUMS.sources.after"
if cmp -s "$OUT/SHA256SUMS.sources.before" "$OUT/SHA256SUMS.sources.after"; then log "source images unchanged (hashes identical before and after)"; else log "SOURCE IMAGES CHANGED"; fi
ls -la "$T16/cores" > "$OUT/cores-listing.txt"
log "done"
