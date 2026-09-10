#!/bin/bash
# CBRD-27064 [CDC]: when an overflow (REC_BIGONE) log record's header lands on a 4KB log-page
# boundary, cdc_get_overflow_recdes() read a stale log page, so CDC extraction of that record
# aborted with rc=-10 and the server logged "logical log page <neg> may be corrupted".
# Fixed in 11.4 P5 hotfix-3 (mechanism: see the JIRA issue).
#
# All cases extract with all_in_cond=1 so CDC reconstructs the FULL before-image (the 16-20KB
# overflow payload), which is what drives the cdc_get_overflow_recdes() path the defect lives in.
# The fault only fires when a record header hits the ~60-byte page-end window, so the payload SIZE
# is swept across a span wider than one 4KB log page to drive the header offset through that
# window; every payload is far larger than one page, so every row is an overflow record.
#
#   -1 insert regression : overflow INSERTs extracted in full  -> OK on every build
#   -2 delete regression : overflow DELETEs extracted in full  -> OK on every build
#   -3 update bug repro  : overflow UPDATEs                    -> NOK on a buggy build, OK when fixed
#
# The JIRA repro, the fix verification and the regression requirements are all UPDATE-based, and
# only UPDATE reproduces the defect here. INSERT/DELETE are carried as regression coverage because
# the fix guards the cdc_get_overflow_recdes() entry for every overflow path (undo, redo and the
# other overflow recovery indexes), so those paths must keep extracting cleanly.
#
# The UPDATE corruption is statistical (the stale page must resolve to an invalid page id), so that
# case repeats the extraction for several ROUNDS and is NOK if ANY round reproduces it.
#   Case OK  : all rows of the case's DML type extracted, extractor rc=0, no page corruption.
#       NOK  : rows lost / extract error / ER_LOG_PAGE_CORRUPTED / extraction timeout.

. $init_path/init.sh
init test

dbname=tc_cbrd27064
file=cdc_extract

rounds=3                    # UPDATE extraction attempts (bug caught if ANY round hits).
                            # Keeps the fixed-build run well inside the regression timeout.
n=2400                      # UPDATEs (hence overflow redo records) extracted per round
n_id=${REPRO_ROWS:-700}                    # INSERTs / DELETEs extracted by the regression cases. Smaller than $n
                            # because each one stores a distinct ~16KB row, not a new version of
                            # the same row.
nsize=${REPRO_SIZES:-1}                   # distinct payload sizes cycled through
base_bytes=16000            # smallest payload (~16KB, far over one 4KB page)
step_bytes=20               # size step per k; nsize*step (4400B) > 4KB page -> full sweep.
                            # Largest payload is 20380B, which must stay under the
                            # BIT VARYING(168192) = 21024 byte column limit: an oversized literal
                            # fails to coerce, leaving holes in cdc_src that would silently
                            # short-commit the INSERT/DELETE workloads.

srcfile="$cur_path/cbrd_27064_src.sql"
updsetup="$cur_path/cbrd_27064_upd_setup.sql"
updwl="$cur_path/cbrd_27064_upd_wl.sql"
inssetup="$cur_path/cbrd_27064_ins_setup.sql"
inswl="$cur_path/cbrd_27064_ins_wl.sql"
delsetup="$cur_path/cbrd_27064_del_setup.sql"
delwl="$cur_path/cbrd_27064_del_wl.sql"
goflag="$cur_path/cbrd_27064_go.flag"
evfile="$cur_path/cbrd_27064_evidence.txt"   # concise per-case diagnostics dumped on NOK
dbglog="$cur_path/cbrd_27064_dbg.log"        # verbose csql/setup output (kept out of the result)
: > "$evfile"
: > "$dbglog"
rm -f "$goflag"

# --- clean any leftover instance --------------------------------------------
cubrid server stop $dbname > /dev/null 2>&1
cubrid deletedb $dbname > /dev/null 2>&1
# drop stale server error logs so the per-case corruption count starts from zero
rm -f $CUBRID/log/server/${dbname}*.err

# CDC prerequisites (restored by finish via cubrid.conf.org). log_compress=no keeps record sizes
# stable; the large archive limit keeps logs available.
change_db_parameter "supplemental_log=1"
change_db_parameter "log_compress=no"
change_db_parameter "vacuum_disable=${REPRO_VACUUM_DISABLE:-no}"
change_db_parameter "log_max_archives=2147483647"

# 4KB db/log pages raise how often a log-record header falls on a page boundary.
# (cubrid_createdb appends $CUBRID_CHARSET; page-size/volume flags pass straight through.)
cubrid_createdb --db-volume-size=64M --log-volume-size=64M \
  --db-page-size=4K --log-page-size=4K $dbname >> "$dbglog" 2>&1

cubrid server start $dbname >> "$dbglog" 2>&1
cubrid broker start >> "$dbglog" 2>&1

hostip=127.0.0.1
port=`get_cubrid_port_id`

xgcc -lcubridcs -o $file ${file}.c >> "$dbglog" 2>&1

# --- swept-size incompressible source payloads (built once, reused by every case) --------------
csql -u dba $dbname >> "$dbglog" 2>&1 <<'EOF'
CREATE TABLE cdc_src (k INT PRIMARY KEY, payload BIT VARYING(168192));
COMMIT;
EOF
: > "$srcfile"
k=1
while [ $k -le $nsize ]; do
    sz=`expr $base_bytes + \( $k - 1 \) \* $step_bytes`
    hex=`head -c $sz /dev/urandom | od -An -v -tx1 | tr -d ' \n'`
    echo "INSERT INTO cdc_src VALUES ($k, X'$hex');" >> "$srcfile"
    k=`expr $k + 1`
done
echo "COMMIT;" >> "$srcfile"
csql -u dba $dbname -i "$srcfile" >> "$dbglog" 2>&1

# Every workload feeds off cdc_src, so a short load would silently shrink the committed row count
# and make the extractor wait for rows that were never written. Fail loudly instead.
src_rows=`csql -u dba $dbname -c "SELECT COUNT(*) FROM cdc_src" 2>> "$dbglog" \
          | awk '/^=+$/{getline; gsub(/[^0-9]/,""); print; exit}'`
if [ "$src_rows" != "$nsize" ]; then
    echo "SOURCE_LOAD_FAILED: cdc_src has ${src_rows} of ${nsize} rows (payload > column limit?)" >> "$evfile"
    write_nok "$evfile"
    write_nok "$evfile"
    write_nok "$evfile"
    cubrid server stop $dbname > /dev/null 2>&1
    cubrid broker stop > /dev/null 2>&1
    cubrid deletedb $dbname > /dev/null 2>&1
    # retain artifacts: rm -f $file ${file}.log "$cur_path"/cbrd_27064_*.sql "$goflag" "$evfile" "$dbglog" csql.* *.err *.class core*
    finish
    exit 0
fi

# --- per-case setup + workload scripts --------------------------------------------------------
# DELETE: the same $n_id overflow rows, loaded BEFORE find_lsa so only the deletes are extracted.
cat > "$delsetup" <<EOF
DROP TABLE IF EXISTS t_del;
CREATE TABLE t_del (id INT PRIMARY KEY, payload BIT VARYING(168192));
EOF
: > "$delwl"
i=1
while [ $i -le $n_id ]; do
    kk=`expr \( \( $i - 1 \) % $nsize \) + 1`
    echo "INSERT INTO t_del SELECT $i, payload FROM cdc_src WHERE k = $kk;" >> "$delsetup"
    echo "DELETE FROM t_del WHERE id = $i;" >> "$delwl"
    i=`expr $i + 1`
done
echo "COMMIT;" >> "$delsetup"
echo "COMMIT;" >> "$delwl"

# running total of server-logged page-corruption entries (delta per extraction)
corr_base=0
corr_now()   # total "may be corrupted" entries so far (timestamped file only, not the symlink)
{
    grep -h "may be corrupted\|ER_LOG_PAGE_CORRUPTED" $CUBRID/log/server/${dbname}_2*.err 2>/dev/null | wc -l
}

ext_timeout=300   # seconds for the EXTRACTION phase only (after the workload commits); a fixed
                  # build drains 2400 overflow rows within this even on a slow debug build

# run_extract <target_type 0=ins/1=upd/2=del> <expected> <setup.sql> <workload.sql> <label>
#   -> sets $extract_ok (1/0) and appends concise evidence
run_extract()
{
    tgt=$1; exp=$2; setupf=$3; wlf=$4; label=$5
    rm -f "$goflag"
    echo "===== $label (type=$tgt expected=$exp) =====" >> "$evfile"

    # pre-stime setup: NOT extracted, find_lsa is captured just after it commits
    csql -u dba $dbname -i "$setupf" >> "$dbglog" 2>&1

    stime=`date +%s`
    sleep 1

    # launch extractor (find_lsa now -> it sees only this case's workload)
    ./$file "$hostip" "$port" "$dbname" "$stime" "$exp" "$goflag" "$tgt" > ${file}.log 2>&1 &
    extractor_pid=$!
    sleep 2

    csql -u dba $dbname -i "$wlf" >> "$dbglog" 2>&1

    # release the extractor to drain the backlog, then time ONLY the extraction phase
    touch "$goflag"
    waited=0
    timed_out=0
    while kill -0 $extractor_pid 2>/dev/null; do
        if [ $waited -ge $ext_timeout ]; then
            timed_out=1
            xkill_pid $extractor_pid 2>/dev/null
            break
        fi
        sleep 3
        waited=`expr $waited + 3`
    done
    if [ $timed_out -eq 1 ]; then
        extractor_rc=124
        wait $extractor_pid 2>/dev/null
    else
        wait $extractor_pid
        extractor_rc=$?
    fi

    cat ${file}.log >> "$evfile"
    echo "EXTRACTOR_RC=${extractor_rc} (124=hang/timeout)" >> "$evfile"

    # target_count = rows of THIS case's DML type (immune to a stray pre-stime row in the window)
    target_count=`grep -oE "TARGET_COUNT: [0-9]+" ${file}.log | tail -1 | awk '{print $2}'`
    [ -z "$target_count" ] && target_count=-1

    c2=`corr_now`
    corr_case=`expr $c2 - $corr_base`
    corr_base=$c2
    echo "CORRUPTION=${corr_case}  TARGET_COUNT=${target_count}/${exp}" >> "$evfile"

    # clean iff extraction finished, returned success, drained every row of the target type, and
    # logged no page corruption.
    if [ "$timed_out" -eq 0 ] && [ "$extractor_rc" -eq 0 ] \
       && [ "$target_count" -ge "$exp" ] && [ "$corr_case" -eq 0 ]; then
        extract_ok=1
    else
        extract_ok=0
    fi

    # settle: drop any stray extractor and let its CDC session close before the next extraction
    xkill -f "$file .* $dbname " > /dev/null 2>&1
    sleep 3
}

# --- case 2: overflow DELETE (regression -- must stay clean on every build) --------------------
: > "$evfile"
run_extract 2 $n_id "$delsetup" "$delwl" "delete overflow"
if [ "$extract_ok" -eq 1 ]; then write_ok "delete overflow regression"; else write_nok "$evfile"; fi

# Namespace teardown stops all private processes; retain DB and logs.
cat "$evfile"
[ "$extract_ok" -eq 1 ]
