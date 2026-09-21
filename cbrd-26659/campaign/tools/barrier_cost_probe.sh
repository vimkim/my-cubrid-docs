#!/usr/bin/env bash
# CBRD-26659 campaign ticket 17 -- what a multi-session barrier schedule costs, measured.
#
#   barrier_cost_probe.sh --build release|debug --page-size N --participants P --rounds R --out DIR
#
# Ticket 17 criterion 1 asks for a timed "multi-session barrier scenario". The campaign's four
# required schedule families have no case at either seam (a Delivery gap, ticket 23's), and this
# header used to add that no barrier scenario existed anywhere; that was wrong (the independent
# review of ticket 17, F1): the private suite's shell/_06_issues/_18_2h/bug_bts_22449 is a
# four-participant, coordinator-released barrier scenario driven through CTP's isolation ctltool,
# and ticket 49 ran it at the seam twice -- it does not complete at the pinned engine (its fourth
# participant stays blocked for the tool's whole barrier wait), so its cost is a Capability gap
# (ticket 17 record, section 5.6). What this probe measures is the MECHANISM such a scenario is
# built from -- and only its uncontended floor: each participant runs a fresh csql per round on its
# own table with every statement autocommitting, so nothing is held across a barrier and no two
# participants contend (review O1). The placement table's row for the families is derived from it
# with that caveat, and ticket 23 owes the measurement with real schedules.
#
# The mechanism is the one decision ticket 05 requires: "Every participant acknowledges an explicit
# barrier after establishing its state; the coordinator releases the next participant... Sleeps pace
# polling and never prove ordering." So: each participant opens its own csql session, establishes
# state with a real database operation (an out-of-row INSERT), acknowledges by creating a token, and
# blocks until the coordinator creates its release token. Sleep is the poll interval only; the
# ordering is proven by the tokens. Every wait carries a deadline, as decision 05 also requires, and
# a timeout ends the probe with its evidence rather than reporting a time.
#
# This is a timing probe, not a testcase: it asserts nothing about the engine beyond the round trip
# it measures, writes into neither testcase repository, and produces no campaign record of its own.
#
# MUST run under campaign_ns.sh: it starts a cub_master and a cub_server.
set -u
here=$(cd "$(dirname "$0")" && pwd)
. "${here}/campaign_env.sh"

build=release page_size=16384 participants=4 rounds=3 out="" deadline=60 poll=0.05
while [ $# -gt 0 ]; do
    case "$1" in
        --build) build=$2; shift 2 ;;
        --page-size) page_size=$2; shift 2 ;;
        --participants) participants=$2; shift 2 ;;
        --rounds) rounds=$2; shift 2 ;;
        --deadline) deadline=$2; shift 2 ;;
        --out) out=$2; shift 2 ;;
        *) die "unknown argument $1" ;;
    esac
done
[ -n "${out}" ] || die "usage: barrier_cost_probe.sh [--build B] [--page-size N] [--participants P] [--rounds R] --out DIR"
mkdir -p "${out}"
tokens="${out}/tokens"; rm -rf "${tokens}"; mkdir -p "${tokens}"

campaign_check_namespace
campaign_set_engine "${build}"
export CUBRID_DATABASES=${CAMPAIGN_TICKET_ROOT:-/home/vimkim/.cub/campaign/cbrd-26659/ticket17}/barrier-db
mkdir -p "${CUBRID_DATABASES}"; cd "${CUBRID_DATABASES}" || exit 1
[ -f databases.txt ] || printf '#db-name\tvol-path\t\tdb-host\t\tlog-path\t\tlob-base-path\n' > databases.txt
db=t17barrier

conf=${CUBRID}/conf/cubrid.conf
conf_before=$(sha256sum "${conf}" | cut -d' ' -f1)
cp -p "${conf}" "${out}/cubrid.conf.backup"
sed -i "s/^cubrid_port_id=.*/cubrid_port_id=${CAMPAIGN_PORT_ID}/" "${conf}"
restore() {
    cubrid server stop "${db}" >> "${out}/teardown.log" 2>&1 || true
    cubrid service stop >> "${out}/teardown.log" 2>&1 || true
    cp -p "${out}/cubrid.conf.backup" "${conf}"
    if [ "$(sha256sum "${conf}" | cut -d' ' -f1)" = "${conf_before}" ]; then
        echo "install_conf_restored=verbatim" >> "${out}/journal.txt"
    else
        echo "install_conf_restored=DRIFTED" >> "${out}/journal.txt"
    fi
}
trap restore EXIT

now () { date +%s.%N; }
elapsed () { python3 -c "print(round($2 - $1, 3))"; }
log () { printf '%s %s\n' "$(date +%H:%M:%S.%N | cut -c1-12)" "$*" | tee -a "${out}/journal.txt"; }

{
    echo "install=${CUBRID}"
    echo "cubrid_rel=${CAMPAIGN_CUBRID_REL}"
    echo "engine_commit=${CAMPAIGN_ENGINE_COMMIT}"
    echo "participants=${participants} rounds=${rounds} page_size=${page_size} build=${build}"
    echo "deadline_seconds=${deadline} poll_seconds=${poll}"
    sha256sum "${CUBRID}/lib/libcubrid.so" "${CUBRID}/bin/csql"
} > "${out}/identity.txt"

t_fixture0=$(now)
cubrid deletedb "${db}" > /dev/null 2>&1 || true
cubrid createdb --db-volume-size=64M --log-volume-size=32M \
    --db-page-size="${page_size}" --log-page-size="${page_size}" "${db}" en_US.utf8 > "${out}/createdb.log" 2>&1 \
    || { log "createdb FAILED"; exit 2; }
t_created=$(now)
cubrid server start "${db}" > "${out}/server_start.log" 2>&1
grep -q "success\|already running" "${out}/server_start.log" || { log "server start FAILED"; exit 2; }
t_fixture1=$(now)
log "fixture ready: createdb $(elapsed "${t_fixture0}" "${t_created}") s, server start $(elapsed "${t_created}" "${t_fixture1}") s"

# --- a participant: establish state, acknowledge, wait for release, act, acknowledge -------------
participant () {
    local i=$1 r
    local sql="${out}/p${i}.sql"
    cat > "${sql}" <<SQL
DROP TABLE IF EXISTS t_t17_bar_${i};
CREATE TABLE t_t17_bar_${i} (id INT PRIMARY KEY, payload BIT VARYING);
INSERT INTO t_t17_bar_${i} VALUES (1, CAST(REPEAT('AB', 4000) AS BIT VARYING));
SELECT OCTET_LENGTH(payload) FROM t_t17_bar_${i};
SQL
    csql -u dba "${db}" -i "${sql}" > "${out}/p${i}.out" 2>&1
    echo "$(now)" > "${tokens}/ready.${i}"
    for r in $(seq 1 "${rounds}"); do
        local waited=0
        while [ ! -e "${tokens}/go.${i}.${r}" ]; do
            sleep "${poll}"
            waited=$(python3 -c "print(round(${waited} + ${poll}, 3))")
            if python3 -c "import sys; sys.exit(0 if ${waited} > ${deadline} else 1)"; then
                echo "DEADLINE participant ${i} round ${r}" > "${tokens}/timeout.${i}.${r}"
                return 1
            fi
        done
        cat > "${out}/p${i}_r${r}.sql" <<SQL
UPDATE t_t17_bar_${i} SET payload = CAST(REPEAT('CD', $((4000 + i * 100 + r * 10))) AS BIT VARYING) WHERE id = 1;
SELECT OCTET_LENGTH(payload) FROM t_t17_bar_${i};
SQL
        csql -u dba "${db}" -i "${out}/p${i}_r${r}.sql" >> "${out}/p${i}.out" 2>&1
        echo "$(now)" > "${tokens}/done.${i}.${r}"
    done
    return 0
}

wait_for () {                      # wait_for <glob> <count> <label>; deadline-bounded
    local pattern=$1 want=$2 label=$3 waited=0
    while [ "$(find "${tokens}" -maxdepth 1 -name "${pattern}" | wc -l)" -lt "${want}" ]; do
        sleep "${poll}"
        waited=$(python3 -c "print(round(${waited} + ${poll}, 3))")
        if python3 -c "import sys; sys.exit(0 if ${waited} > ${deadline} else 1)"; then
            log "DEADLINE reached waiting for ${label} (${pattern}); capturing evidence and stopping"
            ls -la "${tokens}" > "${out}/tokens_at_timeout.txt"
            cubrid server status > "${out}/server_status_at_timeout.txt" 2>&1 || true
            return 1
        fi
    done
    return 0
}

t_sessions0=$(now)
for i in $(seq 1 "${participants}"); do participant "${i}" & done
wait_for 'ready.*' "${participants}" "every participant to establish state and acknowledge" || exit 3
t_sessions1=$(now)
log "all ${participants} participants established state and acknowledged: $(elapsed "${t_sessions0}" "${t_sessions1}") s"

round_times=()
for r in $(seq 1 "${rounds}"); do
    t0=$(now)
    for i in $(seq 1 "${participants}"); do : > "${tokens}/go.${i}.${r}"; done
    wait_for "done.*.${r}" "${participants}" "round ${r}" || exit 3
    t1=$(now)
    e=$(elapsed "${t0}" "${t1}")
    round_times+=("${e}")
    log "round ${r}: release to all-acknowledged ${e} s"
done
wait
t_end=$(now)

python3 - "${out}" "${participants}" "${rounds}" "${t_fixture0}" "${t_created}" "${t_fixture1}" \
         "${t_sessions0}" "${t_sessions1}" "${t_end}" "${round_times[@]}" <<'PY' > "${out}/barrier_cost.json"
import json, sys
out, participants, rounds = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
f0, created, f1, s0, s1, end = map(float, sys.argv[4:10])
rt = [float(x) for x in sys.argv[10:]]
print(json.dumps({
    "participants": participants,
    "rounds": rounds,
    "createdb_seconds": round(created - f0, 3),
    "server_start_seconds": round(f1 - created, 3),
    "fixture_seconds": round(f1 - f0, 3),
    "sessions_establish_and_acknowledge_seconds": round(s1 - s0, 3),
    "round_seconds": rt,
    "round_seconds_mean": round(sum(rt) / len(rt), 3) if rt else None,
    "round_seconds_max": max(rt) if rt else None,
    "total_seconds": round(end - f0, 3),
    "note": "release-to-all-acknowledged per round; the poll interval paces the wait and never proves ordering",
}, indent=2))
PY
cat "${out}/barrier_cost.json"
log "total $(elapsed "${t_fixture0}" "${t_end}") s"
cubrid deletedb "${db}" >> "${out}/teardown.log" 2>&1 || true
