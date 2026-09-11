#!/bin/bash
# CBRD-26659 campaign ticket 14 -- run one CTP shell invocation against a pinned install
# and assemble its replay bundle.
#
#   run_attempt.sh <attempt-id> <release_gcc|debug_gcc> <scenario-root>
#
# What it takes care of, beyond invoking the launcher:
#
#   isolation    the whole invocation runs under campaign_ns.sh, so the CTP helpers'
#                `pkill cub` and their `ipcrm` sweep cannot reach anything this
#                invocation did not start (isolation_check.sh is the demonstration).
#
#   ports        an unprivileged network namespace cannot bring up loopback, so ports are
#                allocated to the campaign instead and verified free before the run.
#
#   $CUBRID/conf CTP resets the install's configuration from ~/.CUBRID_SHELL_FM before
#                every case (Test.resetCUBRID_linux: `rm -rf ${CUBRID}/conf/*` then
#                `cp -rf ~/.CUBRID_SHELL_FM/conf/*`, and the same for databases/). The
#                user's own snapshot is a whole foreign install carrying
#                cubrid_port_id = 1523, so left alone this would overwrite the pinned
#                install's configuration. HOME is therefore redirected to a
#                campaign-owned directory whose .CUBRID_SHELL_FM is seeded from the
#                pinned install itself: the reset then restores the pinned configuration,
#                and the user's snapshot is neither read nor written. Both claims are
#                checked by hashing before and after rather than assumed.
#
#   identity     the engine is verified against ticket 11's recorded library hashes
#                before the launcher starts. A CUBRID binary reports whichever library
#                the loader resolves, so the environment is set first and the hashes are
#                checked, not just the version string.
#
#   outcome      CTP has only PASS and FAIL per case, so the case states its own campaign
#                outcome in <evidence>/case_outcome and this script surfaces it. A run that
#                proved durability but could not observe the out-of-row path reports SKIP
#                there, and the manifest takes its case outcome from it rather than from
#                CTP's success count.
#
#   proof        a launcher exit status is not execution proof. The discovered case list,
#                the executed/success/fail/skip counts and the per-assertion OK, NOK and
#                SKIP lines are extracted from CTP's own runtime logs and from the case's
#                result file, and printed as the summary the manifest is filled in from.
set -u

if [ "$#" -ne 3 ]; then
    echo "usage: run_attempt.sh <attempt-id> <release_gcc|debug_gcc> <scenario-root>" >&2
    exit 2
fi

attempt_id=$1
mode=$2
scenario=$3

root=/home/vimkim/.cub/campaign/cbrd-26659/ticket14
tools=${root}/tools
bundle=${root}/attempts/${attempt_id}
install=/home/vimkim/.cub/install/oos-baseline-f4299ac0c/${mode}
ctp_home=/home/vimkim/CTP
fake_home=${root}/home/${attempt_id}
real_home=${HOME}

# ticket 11, section 2
case "${mode}" in
    release_gcc)
        want_libcubrid=a3256a7a40748752165e65a395b8aebcf8d85e00b87ee62e68bf75e1a5c85444
        want_libcubridsa=8009c322633055df41af045fe560a86f1f8171648863d11f2e44d949e3cdd76e
        ;;
    debug_gcc)
        want_libcubrid=27399fae11a5ef134ba303e5ac6d672748b224bdf593504a2d4fae533a357253
        want_libcubridsa=9a3db918bc01738666bbb1ede762da973a714090c15e6709c78b7dc9c825ba69
        ;;
    *) echo "unknown build mode ${mode}" >&2; exit 2 ;;
esac

rm -rf "${bundle}" "${fake_home}"
mkdir -p "${bundle}" "${fake_home}/.CUBRID_SHELL_FM"

die() { echo "[FATAL] $*" >&2; exit 1; }
manifest_of() { find "$1" -type f | sort | xargs sha256sum 2>/dev/null; }

# --- ports ----------------------------------------------------------------------------
for port in 26659 33120 33121 33122; do
    if ss -ltn 2>/dev/null | awk '{print $4}' | grep -q ":${port}\$"; then
        die "port ${port} is already in use; the campaign owns it and cannot share it"
    fi
done

# --- engine identity --------------------------------------------------------------------
export CUBRID="${install}"
export PATH="${CUBRID}/bin:${PATH}"
export LD_LIBRARY_PATH="${CUBRID}/lib:${LD_LIBRARY_PATH:-}"

got_libcubrid=$(sha256sum "${CUBRID}/lib/libcubrid.so" | cut -d' ' -f1)
got_libcubridsa=$(sha256sum "${CUBRID}/lib/libcubridsa.so" | cut -d' ' -f1)
[ "${got_libcubrid}" = "${want_libcubrid}" ] || die "libcubrid.so is not ticket 11's ${mode} build"
[ "${got_libcubridsa}" = "${want_libcubridsa}" ] || die "libcubridsa.so is not ticket 11's ${mode} build"

{
    echo "attempt_id=${attempt_id}"
    echo "build_mode=${mode}"
    echo "install=${install}"
    echo "cubrid_rel=$(cubrid_rel | tr -d '\r' | tr '\n' ' ')"
    echo "sha256 lib/libcubrid.so=${got_libcubrid}"
    echo "sha256 lib/libcubridsa.so=${got_libcubridsa}"
    echo "sha256 bin/cub_server=$(sha256sum "${CUBRID}/bin/cub_server" | cut -d' ' -f1)"
    echo "sha256 bin/csql=$(sha256sum "${CUBRID}/bin/csql" | cut -d' ' -f1)"
    echo "ctp_home=${ctp_home}"
    echo "sha256 CTP/shell/lib/cubridqa-shell.jar=$(sha256sum "${ctp_home}/shell/lib/cubridqa-shell.jar" | cut -d' ' -f1)"
    echo "sha256 CTP/common/lib/cubridqa-common.jar=$(sha256sum "${ctp_home}/common/lib/cubridqa-common.jar" | cut -d' ' -f1)"
    echo "sha256 CTP/shell/init_path/init.sh=$(sha256sum "${ctp_home}/shell/init_path/init.sh" | cut -d' ' -f1)"
    echo "scenario=${scenario}"
    echo "started_at=$(date -Is)"
} > "${bundle}/identity.txt"

# --- redirect CTP's configuration reset away from the user's own snapshot ---------------
cp -rf "${CUBRID}/conf" "${fake_home}/.CUBRID_SHELL_FM/conf"
mkdir -p "${fake_home}/.CUBRID_SHELL_FM/databases"
cp -rf "${CUBRID}/databases/." "${fake_home}/.CUBRID_SHELL_FM/databases/" 2>/dev/null

manifest_of "${CUBRID}/conf" > "${bundle}/install_conf.before"
manifest_of "${CUBRID}/databases" > "${bundle}/install_databases.before"
manifest_of "${real_home}/.CUBRID_SHELL_FM" > "${bundle}/user_shell_fm.before"

# Redirecting HOME keeps CTP's reset from installing a foreign configuration, but CTP
# then writes this invocation's ports into the install's cubrid.conf, cubrid_broker.conf
# and cubrid_ha.conf and never puts them back. The pinned install is shared with every
# other campaign ticket, so the configuration is copied away here and restored verbatim
# after the run; the manifests taken above and below are the check that it worked.
cp -a "${CUBRID}/conf" "${bundle}/install_conf_backup"
cp -a "${CUBRID}/databases" "${bundle}/install_databases_backup"

# --- configuration -----------------------------------------------------------------------
conf=${bundle}/shell_cbrd26659.conf
sed -e "s|^scenario=.*|scenario=${scenario}|" \
    -e "s|^testcase_update_yn=.*|testcase_update_yn=false|" \
    -e "s|^testcase_exclude_from_file=.*|#&|" \
    -e "s|^testcase_retry_num=.*|testcase_retry_num=0|" \
    -e "s|^testcase_timeout_in_secs=.*|testcase_timeout_in_secs=900|" \
    -e "s|^default.cubrid.cubrid_port_id=.*|default.cubrid.cubrid_port_id=26659|" \
    -e "s|^default.broker1.BROKER_PORT=.*|default.broker1.BROKER_PORT=33121|" \
    -e "s|^default.broker1.APPL_SERVER_SHM_ID=.*|default.broker1.APPL_SERVER_SHM_ID=33121|" \
    -e "s|^default.broker2.BROKER_PORT=.*|default.broker2.BROKER_PORT=33120|" \
    -e "s|^default.broker2.APPL_SERVER_SHM_ID=.*|default.broker2.APPL_SERVER_SHM_ID=33120|" \
    -e "s|^default.ha.ha_port_id=.*|default.ha.ha_port_id=33122|" \
    "${ctp_home}/conf/shell_ci.conf" > "${conf}"

# --- the case list CTP's own discovery rule produces --------------------------------------
find "${scenario}" -name "*.sh" -type f -print \
    | xargs -i echo {} \
    | awk -F "/" '{ if ($(NF-2)".sh" == $NF) print }' \
    | sort > "${bundle}/case-list.txt"
expected_cases=$(wc -l < "${bundle}/case-list.txt")
[ "${expected_cases}" -gt 0 ] || die "no case under ${scenario} matches CTP's discovery rule"

# --- run -----------------------------------------------------------------------------------
export HOME="${fake_home}"
export OOS_CAMPAIGN_EVIDENCE_DIR="${bundle}/case-evidence"
export JAVA_HOME="${JAVA_HOME:-/home/vimkim/.local/share/mise/installs/java/temurin-8.0.462+8}"

started=$(date +%s)
script -qefc "${tools}/campaign_ns.sh ${ctp_home}/bin/ctp.sh shell -c ${conf}" "${bundle}/transcript.raw" >/dev/null 2>&1
launcher_status=$?
ended=$(date +%s)
tr -d '\r' < "${bundle}/transcript.raw" > "${bundle}/transcript.log"
rm -f "${bundle}/transcript.raw"
export HOME="${real_home}"

# --- collect ----------------------------------------------------------------------------------
cp -r "${ctp_home}/result/shell/current_runtime_logs" "${bundle}/ctp_runtime_logs" 2>/dev/null
while read -r f; do
    d=$(dirname "${f}")
    n=$(basename "${f}" .sh)
    [ -f "${d}/${n}.result" ] && cp "${d}/${n}.result" "${bundle}/${n}.result"
done < "${bundle}/case-list.txt"

# The case's own artifacts must not be left in the testcase repository.
while read -r f; do
    d=$(dirname "${f}")
    n=$(basename "${f}" .sh)
    rm -f "${d}/${n}.result"
done < "${bundle}/case-list.txt"
# Put the pinned install's configuration back exactly as it was found. This also removes
# the .org copies change_db_parameter leaves behind, which restore_all_conf reads but
# never deletes.
[ -d "${bundle}/install_conf_backup" ] || die "the configuration backup is missing; refusing to touch ${CUBRID}/conf"
rm -rf "${CUBRID:?}/conf" "${CUBRID:?}/databases"
cp -a "${bundle}/install_conf_backup" "${CUBRID}/conf"
cp -a "${bundle}/install_databases_backup" "${CUBRID}/databases"

manifest_of "${CUBRID}/conf" > "${bundle}/install_conf.after"
manifest_of "${CUBRID}/databases" > "${bundle}/install_databases.after"
manifest_of "${real_home}/.CUBRID_SHELL_FM" > "${bundle}/user_shell_fm.after"

conf_drift=$(diff "${bundle}/install_conf.before" "${bundle}/install_conf.after" | grep -c '^[<>]')
db_drift=$(diff "${bundle}/install_databases.before" "${bundle}/install_databases.after" | grep -c '^[<>]')
fm_drift=$(diff "${bundle}/user_shell_fm.before" "${bundle}/user_shell_fm.after" | grep -c '^[<>]')

status=${bundle}/ctp_runtime_logs/test_status.data
discovered=$(wc -l < "${bundle}/ctp_runtime_logs/dispatch_tc_ALL.txt" 2>/dev/null || echo 0)
get() { grep "^$1=" "${status}" 2>/dev/null | cut -d= -f2; }

{
    echo "attempt_id=${attempt_id}"
    echo "build_mode=${mode}"
    echo "launcher_exit_status=${launcher_status}"
    echo "elapsed_seconds=$((ended - started))"
    echo "expected_case_count=${expected_cases}"
    echo "discovered_case_count=${discovered}"
    echo "total_case_count=$(get total_case_count)"
    echo "executed_case_count=$(get total_executed_case_count)"
    echo "success_case_count=$(get total_success_case_count)"
    echo "fail_case_count=$(get total_fail_case_count)"
    echo "skip_case_count=$(get total_skip_case_count)"
    if [ -f "${bundle}/case-evidence/case_outcome" ]; then
        echo "case_outcome=$(cut -d'|' -f1 "${bundle}/case-evidence/case_outcome")"
        echo "case_outcome_reason=$(cut -d'|' -f2- "${bundle}/case-evidence/case_outcome")"
    else
        echo "case_outcome=MISSING"
        echo "case_outcome_reason=the case wrote no case_outcome file; treat the run as unproven"
    fi
    for r in "${bundle}"/*.result; do
        [ -f "${r}" ] || continue
        n=$(basename "${r}" .result)
        echo "assertions_executed[${n}]=$(grep -cE "^${n}-[0-9]+ : (OK|NOK)" "${r}")"
        echo "assertions_ok[${n}]=$(grep -cE "^${n}-[0-9]+ : OK" "${r}")"
        echo "assertions_nok[${n}]=$(grep -cE "^${n}-[0-9]+ : NOK" "${r}")"
        echo "assertions_skipped[${n}]=$(grep -c ' : SKIP ' "${r}")"
    done
    echo "install_conf_drift_lines=${conf_drift}"
    echo "install_databases_drift_lines=${db_drift}"
    echo "user_shell_fm_drift_lines=${fm_drift}"
    echo "ended_at=$(date -Is)"
} | tee "${bundle}/summary.txt"

echo
echo "bundle: ${bundle}"
