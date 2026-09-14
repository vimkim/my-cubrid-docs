#!/bin/bash
# CBRD-26659 campaign ticket 15 -- shared environment for the CTP wrappers.
#
# Sourced by run_ctp_sql.sh, run_ctp_shell.sh and activation_check_cs.sh. Everything here is
# a fact established by an earlier ticket, cited beside it:
#
#   pinned installs and library hashes      ticket 41 (re-pin without the unit-test seams,
#                                            carrying out ticket 39 item 1); ticket 11
#                                            section 2 holds the superseded build, kept only
#                                            for replaying the bundles that cite it
#   CTP jar and init.sh hashes               ticket 37 item 1 (a swapped tree is caught the
#                                            way a swapped library is)
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
# The campaign's CTP tree is PINNED, never inherited: the login environment on this host carries
# CTP_HOME=/home/vimkim/gh/ctp/run-sql/CTP (a different CTP checkout with different jars), and the
# manifest's runner fingerprint must name the tree that actually ran. Tickets 13 and 14 ran
# /home/vimkim/CTP (cubridqa-cqt.jar 456cabff…, cubridqa-shell.jar e7c8ef04…). Override only
# through CAMPAIGN_CTP_HOME, which is then recorded in identity.txt and fingerprinted.
CTP_HOME=${CAMPAIGN_CTP_HOME:-/home/vimkim/CTP}
export CTP_HOME
export JAVA_HOME="${CAMPAIGN_JAVA_HOME:-/home/vimkim/.local/share/mise/installs/java/temurin-8.0.462+8}"
TOOLS_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
DOCS_CAMPAIGN_DIR=$(cd "${TOOLS_DIR}/.." && pwd)

die() { echo "[FATAL] $*" >&2; exit 1; }
log() { echo "[$(date +%H:%M:%S)] $*" >&2; }
manifest_of() { find "$1" -type f 2>/dev/null | LC_ALL=C sort | xargs -r sha256sum 2>/dev/null; }

# campaign_build_dir release|debug -> release_gcc_nounit|debug_gcc_nounit  (ticket 41)
campaign_build_dir() {
    case "$1" in
        release) echo release_gcc_nounit ;;
        debug) echo debug_gcc_nounit ;;
        *) die "build mode must be release or debug, got '$1'" ;;
    esac
}

# campaign_expected_hash release|debug libcubrid.so|libcubridsa.so   (ticket 41, re-pinned build)
# These four hashes and campaign_build_dir above are also in campaign_records.py
# (LIBRARY_HASHES, BUILD_DIRS): the shell gates a run before any Python runs, so both need
# them. A re-pin must change BOTH files; the baseline record's revision is the authority.
campaign_expected_hash() {
    case "$1/$2" in
        release/libcubrid.so)   echo 1bbbe44663c79d069181b0d812df95c7f7d793b7f16f2850ab4e8af899986b7c ;;
        release/libcubridsa.so) echo 559a955ea2c46ae3de15efc572fd6a8dbaef7751e38b6c418656437d7a158179 ;;
        debug/libcubrid.so)     echo 30c520623ea5ab4661a1e1151e41922698e149f71f84a3dce669e24ffb34661f ;;
        debug/libcubridsa.so)   echo bc0de923e72f2c0464a69df20de9a58715d370382bc58274f85a2cf9e31a1931 ;;
        *) die "no ticket 41 hash for $1/$2" ;;
    esac
}

# campaign_legacy_hash release|debug libcubrid.so|libcubridsa.so   (ticket 11, superseded)
# Recognised only so a run pointed at the old install is refused by name rather than by an
# anonymous mismatch; a new run never uses it. Unlike campaign_expected_hash this one echoes
# an empty string instead of calling die on an unknown argument: it is a probe asking "is this
# the old build?", and "no" is an answer, not an error.
campaign_legacy_hash() {
    case "$1/$2" in
        release/libcubrid.so)   echo a3256a7a40748752165e65a395b8aebcf8d85e00b87ee62e68bf75e1a5c85444 ;;
        release/libcubridsa.so) echo 8009c322633055df41af045fe560a86f1f8171648863d11f2e44d949e3cdd76e ;;
        debug/libcubrid.so)     echo 27399fae11a5ef134ba303e5ac6d672748b224bdf593504a2d4fae533a357253 ;;
        debug/libcubridsa.so)   echo 9a3db918bc01738666bbb1ede762da973a714090c15e6709c78b7dc9c825ba69 ;;
        *) echo "" ;;
    esac
}

# campaign_check_ctp -- the CTP tree must be the campaign's (ticket 37 item 1)
campaign_check_ctp() {
    local rel got want
    while read -r want rel; do
        [ -n "${rel}" ] || continue
        [ -f "${CTP_HOME}/${rel}" ] || die "${CTP_HOME}/${rel} is missing; this is not the campaign's CTP tree"
        got=$(sha256sum "${CTP_HOME}/${rel}" | cut -d' ' -f1)
        [ "${got}" = "${want}" ] || die "${CTP_HOME}/${rel} hashes ${got}, not the campaign's ${want} (ticket 37 item 1)"
    done <<'EOF'
456cabffff33abe4c5cd4695d40b33a713b8e53d86b6158fd87f94148e17f078 sql/lib/cubridqa-cqt.jar
e7c8ef04ee377d5fd33d82ad237210ee0c0c509c7b643787ba5f2137d69e6347 shell/lib/cubridqa-shell.jar
2d89d3a03b48675c8dfea4d312a01953b90c2f9a04750e65a9e53655b8ff7074 common/lib/cubridqa-common.jar
14fcc2aa5d707569b855a40081b13e9cc21dd35794791fc57accb06c663470c9 shell/init_path/init.sh
EOF
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
# and verify the two library hashes against the campaign's build (ticket 41) before anything
# starts. An install holding the superseded ticket 11 build is named as such in the refusal.
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
        if [ "${got}" != "${want}" ]; then
            if [ "${got}" = "$(campaign_legacy_hash "${mode}" "${lib}")" ]; then
                die "${CUBRID}/lib/${lib} is the superseded ticket 11 ${mode} build, which carries the unit-test seams; the campaign's build is ${want} (ticket 41)"
            fi
            die "${CUBRID}/lib/${lib} hashes ${got}, not the campaign's ${mode} build ${want} (ticket 41)"
        fi
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
