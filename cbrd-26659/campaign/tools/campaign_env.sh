#!/bin/bash
# CBRD-26659 campaign ticket 15 -- shared environment for the CTP wrappers.
#
# Sourced by run_ctp_sql.sh, run_ctp_shell.sh and activation_check_cs.sh. Everything here is
# a fact established by an earlier ticket, cited beside it:
#
#   pinned installs and library hashes      ticket 11, section 2 (binary identity)
#   campaign ports 26659/33120/33121/33122   ticket 14, section 2 (ports are allocated, not
#                                            isolated: an unprivileged namespace cannot bring
#                                            up loopback); ticket 16 uses 26671/33140-33142;
#                                            port 1523 belongs to other installs and is never
#                                            touched
#   namespace containment                    ticket 14, campaign_ns.sh (unshare --user
#                                            --map-current-user --pid --fork --mount-proc --ipc)
#   storage under /home                      decision ticket 08; spec "Execution tiers"
set -u

CAMPAIGN_STORAGE_ROOT=${CAMPAIGN_STORAGE_ROOT:-/home/vimkim/.cub/campaign/cbrd-26659}
CAMPAIGN_TICKET_ROOT=${CAMPAIGN_TICKET_ROOT:-${CAMPAIGN_STORAGE_ROOT}/ticket15}
CAMPAIGN_NS=${CAMPAIGN_NS:-/home/vimkim/.cub/campaign/cbrd-26659/ticket14/tools/campaign_ns.sh}
CAMPAIGN_INSTALL_ROOT=/home/vimkim/.cub/install/oos-baseline-f4299ac0c
CAMPAIGN_ENGINE_COMMIT=f4299ac0cd777a2a964c1f197ae5ebf9841a4936
CAMPAIGN_PORTS="26659 33120 33121 33122"
CAMPAIGN_PORT_ID=26659
CAMPAIGN_BROKER1_PORT=33120
CAMPAIGN_BROKER2_PORT=33121
CAMPAIGN_HA_PORT=33122
CTP_HOME=${CTP_HOME:-/home/vimkim/CTP}
export CTP_HOME
export JAVA_HOME="${JAVA_HOME:-/home/vimkim/.local/share/mise/installs/java/temurin-8.0.462+8}"
TOOLS_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
DOCS_CAMPAIGN_DIR=$(cd "${TOOLS_DIR}/.." && pwd)

die() { echo "[FATAL] $*" >&2; exit 1; }
log() { echo "[$(date +%H:%M:%S)] $*" >&2; }
manifest_of() { find "$1" -type f 2>/dev/null | LC_ALL=C sort | xargs -r sha256sum 2>/dev/null; }

# campaign_build_dir release|debug -> release_gcc|debug_gcc
campaign_build_dir() {
    case "$1" in
        release) echo release_gcc ;;
        debug) echo debug_gcc ;;
        *) die "build mode must be release or debug, got '$1'" ;;
    esac
}

# campaign_expected_hash release|debug libcubrid.so|libcubridsa.so   (ticket 11, section 2)
campaign_expected_hash() {
    case "$1/$2" in
        release/libcubrid.so)   echo a3256a7a40748752165e65a395b8aebcf8d85e00b87ee62e68bf75e1a5c85444 ;;
        release/libcubridsa.so) echo 8009c322633055df41af045fe560a86f1f8171648863d11f2e44d949e3cdd76e ;;
        debug/libcubrid.so)     echo 27399fae11a5ef134ba303e5ac6d672748b224bdf593504a2d4fae533a357253 ;;
        debug/libcubridsa.so)   echo 9a3db918bc01738666bbb1ede762da973a714090c15e6709c78b7dc9c825ba69 ;;
        *) die "no ticket 11 hash for $1/$2" ;;
    esac
}

# campaign_check_ports -- every campaign port must be free before a launcher starts
campaign_check_ports() {
    local port
    for port in ${CAMPAIGN_PORTS}; do
        if ss -ltn 2>/dev/null | awk '{print $4}' | grep -q ":${port}\$"; then
            die "port ${port} is in use; the campaign owns it and cannot share it (ticket 14 section 2)"
        fi
    done
}

# campaign_check_namespace -- unprivileged user namespaces must work, or nothing runs
campaign_check_namespace() {
    [ -x "${CAMPAIGN_NS}" ] || die "campaign_ns.sh not found at ${CAMPAIGN_NS}"
    "${CAMPAIGN_NS}" true >/dev/null 2>&1 || die "unshare --user --pid --ipc is not available; refusing to run CTP unconfined"
}

# campaign_set_engine release|debug -- point CUBRID/PATH/LD_LIBRARY_PATH at the pinned install
# and verify the two library hashes against ticket 11 before anything starts.
campaign_set_engine() {
    local mode=$1 lib got want
    CAMPAIGN_INSTALL="${CAMPAIGN_INSTALL_ROOT}/$(campaign_build_dir "${mode}")"
    [ -d "${CAMPAIGN_INSTALL}" ] || die "no install at ${CAMPAIGN_INSTALL}"
    export CUBRID="${CAMPAIGN_INSTALL}"
    export PATH="${CUBRID}/bin:${PATH}"
    export LD_LIBRARY_PATH="${CUBRID}/lib:${CUBRID}/cci/lib"
    for lib in libcubrid.so libcubridsa.so; do
        got=$(sha256sum "${CUBRID}/lib/${lib}" | cut -d' ' -f1)
        want=$(campaign_expected_hash "${mode}" "${lib}")
        [ "${got}" = "${want}" ] || die "${CUBRID}/lib/${lib} hashes ${got}, not ticket 11's ${mode} build ${want}"
    done
    CAMPAIGN_CUBRID_REL=$(cubrid_rel | tr -d '\r' | tr -s '[:space:]' ' ' | sed 's/^ //; s/ $//')
    case "${CAMPAIGN_CUBRID_REL}" in
        *f4299ac*) ;;
        *) die "cubrid_rel reports '${CAMPAIGN_CUBRID_REL}', not the pinned build" ;;
    esac
}

# campaign_admit BYTES -- refuse when the campaign storage would exceed its limit
campaign_admit() {
    python3 "${TOOLS_DIR}/retention.py" admit --bytes "$1" || die "admission refused by retention.py: storage limit reached; nothing was run and nothing was deleted (decision ticket 08)"
}
