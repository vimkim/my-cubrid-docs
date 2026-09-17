#!/usr/bin/env bash
# CBRD-26659 campaign ticket 17 -- probe ONE cell of the configuration domain.
#
#   config_domain_probe.sh --build release|debug --page-size 4096|8192|16384 \
#                          --run-mode standalone|client-server --out DIR
#
# Criterion 2 asks that each of the twelve combinations of page size, build and run mode is
# "either proven runnable with a matching binary or recorded as a Capability gap", and the
# spec's Engine baseline section adds that "a build directory's presence is not proof of a
# matching binary". This script therefore proves the cell by running it: it creates a database
# at the declared page size with the pinned install whose library hashes campaign_env.sh has
# already verified, inserts one out-of-row value, reads it back and asks the engine for its own
# view of both facts (`cubrid spacedb` for the page size, `SHOW HEAP OOS` for the OOS path).
#
# What it decides is only what it observed. `config_domain.py` owns what counts as proven, so
# that this script cannot decide that about itself; it writes <out>/<cell>.json and that module
# reads it.
#
# Safety:
#   * MUST run under campaign_ns.sh: a client-server cell starts a cub_master and a cub_server,
#     and the namespace's exit tears them down (ticket 37 decision 2).
#   * client-server cells need $CUBRID/conf/cubrid.conf to carry the campaign's port, which the
#     install does not (it carries the 1523 default and port 1523 belongs to other installs).
#     The file is backed up, rewritten, restored verbatim and the restoration verified by hash,
#     the way ticket 14's runner treats CTP's rewrite of the same file. Drift is recorded.
#   * databases live under the ticket's own CUBRID_DATABASES, never the install's.
set -u
here=$(cd "$(dirname "$0")" && pwd)
. "${here}/campaign_env.sh"

build="" page_size="" run_mode="" out=""
while [ $# -gt 0 ]; do
    case "$1" in
        --build) build=$2; shift 2 ;;
        --page-size) page_size=$2; shift 2 ;;
        --run-mode) run_mode=$2; shift 2 ;;
        --out) out=$2; shift 2 ;;
        *) die "unknown argument $1" ;;
    esac
done
[ -n "${build}" ] && [ -n "${page_size}" ] && [ -n "${run_mode}" ] && [ -n "${out}" ] \
    || die "usage: config_domain_probe.sh --build B --page-size N --run-mode M --out DIR"
case "${run_mode}" in standalone) tag=sa ;; client-server) tag=cs ;; *) die "run mode must be standalone or client-server" ;; esac

cell="${page_size}-${build}-${tag}"
mkdir -p "${out}/${cell}"
work="${out}/${cell}"
db="t17cfg${page_size}${build:0:1}${tag}"

campaign_check_namespace
campaign_set_engine "${build}"                 # verifies both library hashes against ticket 41
export CUBRID_DATABASES=${CAMPAIGN_TICKET_ROOT:-/home/vimkim/.cub/campaign/cbrd-26659/ticket17}/config-domain-db
mkdir -p "${CUBRID_DATABASES}"
cd "${CUBRID_DATABASES}" || die "cannot enter ${CUBRID_DATABASES}"
[ -f databases.txt ] || printf '#db-name\tvol-path\t\tdb-host\t\tlog-path\t\tlob-base-path\n' > databases.txt

# --- identity, taken from the install that is about to run ---------------------------------------
sha_of() { sha256sum "$1" | cut -d' ' -f1; }
lib_sha=$(sha_of "${CUBRID}/lib/libcubrid.so")
libsa_sha=$(sha_of "${CUBRID}/lib/libcubridsa.so")
csql_sha=$(sha_of "${CUBRID}/bin/csql")
server_sha=$(sha_of "${CUBRID}/bin/cub_server")
{
    echo "cell=${cell}"
    echo "install=${CUBRID}"
    echo "cubrid_rel=${CAMPAIGN_CUBRID_REL}"
    echo "engine_commit=${CAMPAIGN_ENGINE_COMMIT}"
    echo "page_size_declared=${page_size}"
    echo "run_mode=${run_mode}"
    echo "database=${db}"
    echo "started_at=$(date -Is)"
} > "${work}/identity.txt"

conf=${CUBRID}/conf/cubrid.conf
conf_before=$(sha_of "${conf}")
conf_restored=not-applicable
cleanup() {
    if [ "${run_mode}" = client-server ]; then
        cubrid server stop "${db}" >> "${work}/teardown.log" 2>&1 || true
        cubrid service stop >> "${work}/teardown.log" 2>&1 || true
    fi
    if [ -f "${work}/cubrid.conf.backup" ]; then
        cp -p "${work}/cubrid.conf.backup" "${conf}"
        if [ "$(sha_of "${conf}")" = "${conf_before}" ]; then conf_restored=verbatim; else conf_restored=DRIFTED; fi
        echo "conf_restored=${conf_restored}" >> "${work}/identity.txt"
    fi
}
trap cleanup EXIT

if [ "${run_mode}" = client-server ]; then
    cp -p "${conf}" "${work}/cubrid.conf.backup"
    sed -i "s/^cubrid_port_id=.*/cubrid_port_id=${CAMPAIGN_PORT_ID}/" "${conf}"
    grep -q "^cubrid_port_id=${CAMPAIGN_PORT_ID}\$" "${conf}" || die "could not point ${conf} at the campaign port"
fi

verdict=runnable reason=null
started=$(date +%s.%N)

# --- create the database at the declared page size ------------------------------------------------
cubrid deletedb "${db}" > /dev/null 2>&1 || true
if ! cubrid createdb --db-volume-size=64M --log-volume-size=32M \
        --db-page-size="${page_size}" --log-page-size="${page_size}" "${db}" en_US.utf8 \
        > "${work}/createdb.log" 2>&1; then
    verdict=capability-gap
    reason="createdb refused at ${page_size} B pages on the ${build} build: $(tr '\n' ' ' < "${work}/createdb.log" | tail -c 400)"
fi

page_readback=null
if [ "${verdict}" = runnable ]; then
    cubrid spacedb -S "${db}" > "${work}/spacedb.txt" 2>&1 || true
    # "Space description for database 'x' with pagesize 4.0K. (log pagesize: 4.0K)"
    page_readback=$(awk '/with pagesize/ {
        for (i = 1; i <= NF; i++) if ($i == "pagesize") { v = $(i+1); sub(/\..*/, "", v); print v * 1024; exit }
    }' "${work}/spacedb.txt")
    [ -n "${page_readback}" ] || page_readback=null
fi

# --- the workload: one out-of-row value, written and read back ------------------------------------
cat > "${work}/workload.sql" <<'SQL'
DROP TABLE IF EXISTS t_t17_cfg;
CREATE TABLE t_t17_cfg (id INT PRIMARY KEY, payload BIT VARYING, tag BIT VARYING);
INSERT INTO t_t17_cfg VALUES (1, CAST(REPEAT('AB', 4000) AS BIT VARYING), CAST(REPEAT('7', 600) AS BIT VARYING));
SELECT OCTET_LENGTH(payload)                                          AS payload_octets,
       MD5(payload)                                                   AS payload_md5,
       payload = CAST(REPEAT('AB', 4000) AS BIT VARYING)              AS payload_ok,
       tag     = CAST(REPEAT('7', 600) AS BIT VARYING)                AS tag_ok
  FROM t_t17_cfg;
SHOW HEAP OOS OF t_t17_cfg;
SQL

if [ "${verdict}" = runnable ]; then
    if [ "${run_mode}" = client-server ]; then
        cubrid server start "${db}" > "${work}/server_start.log" 2>&1
        if ! grep -q "success\|already running" "${work}/server_start.log"; then
            verdict=capability-gap
            reason="cub_server refused to start for a ${page_size} B ${build} database: $(tr '\n' ' ' < "${work}/server_start.log" | tail -c 400)"
        else
            csql -u dba "${db}" -i "${work}/workload.sql" > "${work}/workload.out" 2>&1 || true
        fi
    else
        csql -S -u dba "${db}" -i "${work}/workload.sql" > "${work}/workload.out" 2>&1 || true
    fi
fi

# --- what the engine said about itself ------------------------------------------------------------
# Columns are located by NAME from the SHOW HEAP OOS header (ticket 14 finding i), never by position.
read_oos () {
    awk -v col="$1" '
      /Has_oos_file/ && !hdr { for (i = 1; i <= NF; i++) if ($i == col) idx = i; hdr = 1; next }
      hdr && index($0, "t_t17_cfg") { if (idx > 0 && NF >= idx) print $idx; exit }
    ' "${work}/workload.out" 2>/dev/null
}
has_oos=$(read_oos Has_oos_file); num_recs=$(read_oos Oos_num_recs); sumlen=$(read_oos Oos_recs_sumlen)
[ -n "${has_oos:-}" ] || has_oos=null
[ -n "${num_recs:-}" ] || num_recs=null
[ -n "${sumlen:-}" ] || sumlen=null

roundtrip=differs
if [ -f "${work}/workload.out" ] && grep -qE '^ +4000 +' "${work}/workload.out" \
   && [ "$(grep -cE "^ +4000 +'[0-9a-f]{32}' +1 +1" "${work}/workload.out")" -ge 1 ]; then
    roundtrip=byte-identical
fi
[ "${verdict}" = runnable ] || roundtrip=null

ended=$(date +%s.%N)
wall=$(python3 -c "print(round(${ended} - ${started}, 2))")
echo "ended_at=$(date -Is)" >> "${work}/identity.txt"

cleanup; trap - EXIT
cubrid deletedb "${db}" > "${work}/deletedb.log" 2>&1 || true

export T17_CELL="${cell}" T17_PAGE="${page_size}" T17_BUILD="${build}" T17_MODE="${run_mode}"
export T17_VERDICT="${verdict}" T17_COMMIT="${CAMPAIGN_ENGINE_COMMIT}" T17_REL="${CAMPAIGN_CUBRID_REL}"
export T17_INSTALL="${CUBRID}" T17_DB="${db}" T17_LIB="${lib_sha}" T17_LIBSA="${libsa_sha}"
export T17_CSQL="${csql_sha}" T17_SERVER="${server_sha}" T17_READBACK="${page_readback}"
export T17_HASOOS="${has_oos}" T17_NUMRECS="${num_recs}" T17_SUMLEN="${sumlen}"
export T17_ROUNDTRIP="${roundtrip}" T17_WALL="${wall}" T17_REASON="${reason}"
export T17_CONF="${conf_restored}" T17_WORK="${work}"
python3 "${here}/config_domain_cell.py" > "${out}/${cell}.json"
echo "[${cell}] ${verdict} (${wall}s, conf ${conf_restored})" >&2
