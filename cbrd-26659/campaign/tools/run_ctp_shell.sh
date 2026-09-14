#!/bin/bash
# CBRD-26659 campaign ticket 15 -- run one CTP shell invocation and turn it into execution proof.
#
#   run_ctp_shell.sh --declarations FILE --build release|debug --manifest-id ID
#                    --attempt-ids a[,b,...] --evidence-dir DIR
#                    [--scenario-override DIR] [--kind original|checker-validation|coexistence]
#                    [--oracle FILE] [--planted CASE:ASSERTION=NOK ...] [--tier fast|scheduled|extended]
#                    [--producer-version TEXT] [--reserve-bytes N]
#
# Successor of ticket 14's run_attempt.sh (whose containment, HOME redirection, identity check,
# before/after hashing and proof extraction it keeps) that also writes the campaign records
# through ctp_shell_records.py. What it takes care of (sources in brackets):
#
#   containment  the whole invocation runs under campaign_ns.sh: the CTP shell helpers'
#                `cubrid service stop`, `pkill cub` and ipcrm sweep reach only this
#                invocation's processes and segments [ticket 14 section 2].
#   ports        26659/33120/33121/33122 verified free first [ticket 14 section 2].
#   identity     pinned install, library hashes verified against ticket 11 [ticket 11 s2].
#   $CUBRID/conf CTP resets the install's conf and databases from ~/.CUBRID_SHELL_FM before every
#                case; HOME is redirected to a campaign-owned directory seeded from the pinned
#                install, and conf and databases are restored verbatim afterwards, both checked
#                by hash [ticket 14 finding c].
#   evidence     single-case invocations get OOS_CAMPAIGN_EVIDENCE_DIR=<bundle>/case-evidence;
#                multi-case invocations leave it unset and collect each case's *_evidence
#                directory from the repository into <bundle>/case-evidence/<case>/ afterwards
#                (decision request in the ticket 15 record: a root-plus-case-name convention).
#   worktree     .result files and evidence directories are copied out and the scenario tree is
#                restored to its pre-run state, verified by hash.
#   proof        test_status.data, dispatch_tc_ALL.txt and the .result files are read by
#                ctp_shell_records.py; the launcher exit status is recorded, never trusted
#                [ticket 14 finding b].
#   cap          the tier's invocation cap is enforced with `timeout`; CTP's own per-case
#                timeout is set to the invocation cap so that CTP never kills a crash case
#                mid-restart and destroys its evidence [ticket 14 section 5]; the per-case cap
#                is judged from the measured case time by the post-processor.
#   admission    retention.py admit refuses to start at the storage limit [decision 08].
set -u
here=$(cd "$(dirname "$0")" && pwd)
. "${here}/campaign_env.sh"

declarations="" build="" manifest_id="" attempt_ids="" evidence_dir="" scenario_override="" kind=original
oracle="" planted=() tier=fast producer_version="" reserve_bytes=$((2 * 1024 * 1024 * 1024)) cap_override=""
while [ $# -gt 0 ]; do
    case "$1" in
        --declarations) declarations=$2; shift 2 ;;
        --build) build=$2; shift 2 ;;
        --manifest-id) manifest_id=$2; shift 2 ;;
        --attempt-ids) attempt_ids=$2; shift 2 ;;
        --evidence-dir) evidence_dir=$2; shift 2 ;;
        --scenario-override) scenario_override=$2; shift 2 ;;
        --kind) kind=$2; shift 2 ;;
        --oracle) oracle=$2; shift 2 ;;
        --planted) planted+=(--planted "$2"); shift 2 ;;
        --tier) tier=$2; shift 2 ;;
        --producer-version) producer_version=$2; shift 2 ;;
        --reserve-bytes) reserve_bytes=$2; shift 2 ;;
        --cap-override) cap_override=$2; shift 2 ;;
        *) die "unknown argument $1" ;;
    esac
done
[ -n "${declarations}" ] && [ -n "${build}" ] && [ -n "${manifest_id}" ] && [ -n "${attempt_ids}" ] && [ -n "${evidence_dir}" ] \
    || die "usage: run_ctp_shell.sh --declarations FILE --build release|debug --manifest-id ID --attempt-ids a,b --evidence-dir DIR [...]"

eval "$(python3 - "${declarations}" <<'EOF'
import json, sys, shlex
d = json.load(open(sys.argv[1]))
print("decl_repository=" + shlex.quote(d["repository"]))
print("decl_scenario=" + shlex.quote(d["scenario"]))
print("decl_cases=" + shlex.quote(" ".join(sorted(d["cases"]))))
EOF
)"
case "${decl_repository}" in
    testcases) worktree=/home/vimkim/gh/tc/cubrid-testcases-cbrd-26659 ;;
    testcases-private-ex) worktree=/home/vimkim/gh/tc/cubrid-testcases-private-ex-cbrd-26659 ;;
    *) die "unknown repository ${decl_repository}" ;;
esac
scenario=${scenario_override:-${worktree}/${decl_scenario}}
[ -d "${scenario}" ] || die "scenario ${scenario} does not exist"
[ "${tier}" = fast ] && inv_cap=900 || { [ "${tier}" = scheduled ] && inv_cap=7200 || inv_cap=28800; }
[ -n "${cap_override}" ] && inv_cap=${cap_override}   # cap-enforcement control only; recorded in the manifest

campaign_check_namespace
campaign_check_ports
campaign_check_ctp
campaign_set_engine "${build}"
campaign_admit "${reserve_bytes}"

bundle=${CAMPAIGN_TICKET_ROOT}/attempts/${manifest_id}
fake_home=${CAMPAIGN_TICKET_ROOT}/home/${manifest_id}
real_home=${HOME}
[ -e "${bundle}" ] && die "bundle ${bundle} already exists; attempts are never overwritten"
mkdir -p "${bundle}" "${fake_home}/.CUBRID_SHELL_FM" "${evidence_dir}"

# --- redirect CTP's configuration reset away from the user's own snapshot ------------------------
cp -rf "${CUBRID}/conf" "${fake_home}/.CUBRID_SHELL_FM/conf"
mkdir -p "${fake_home}/.CUBRID_SHELL_FM/databases"
cp -rf "${CUBRID}/databases/." "${fake_home}/.CUBRID_SHELL_FM/databases/" 2>/dev/null
manifest_of "${CUBRID}/conf" > "${bundle}/install_conf.before"
manifest_of "${CUBRID}/databases" > "${bundle}/install_databases.before"
manifest_of "${real_home}/.CUBRID_SHELL_FM" > "${bundle}/user_shell_fm.before"
manifest_of "${scenario}" > "${bundle}/scenario_tree.before"
cp -a "${CUBRID}/conf" "${bundle}/install_conf_backup"
cp -a "${CUBRID}/databases" "${bundle}/install_databases_backup"

# --- configuration ---------------------------------------------------------------------------------
conf=${bundle}/shell_${manifest_id}.conf
sed -e "s|^scenario=.*|scenario=${scenario}|" \
    -e "s|^testcase_update_yn=.*|testcase_update_yn=false|" \
    -e "s|^testcase_exclude_from_file=.*|#&|" \
    -e "s|^testcase_retry_num=.*|testcase_retry_num=0|" \
    -e "s|^testcase_timeout_in_secs=.*|testcase_timeout_in_secs=${inv_cap}|" \
    -e "s|^default.cubrid.cubrid_port_id=.*|default.cubrid.cubrid_port_id=${CAMPAIGN_PORT_ID}|" \
    -e "s|^default.broker1.BROKER_PORT=.*|default.broker1.BROKER_PORT=${CAMPAIGN_BROKER2_PORT}|" \
    -e "s|^default.broker1.APPL_SERVER_SHM_ID=.*|default.broker1.APPL_SERVER_SHM_ID=${CAMPAIGN_BROKER2_PORT}|" \
    -e "s|^default.broker2.BROKER_PORT=.*|default.broker2.BROKER_PORT=${CAMPAIGN_BROKER1_PORT}|" \
    -e "s|^default.broker2.APPL_SERVER_SHM_ID=.*|default.broker2.APPL_SERVER_SHM_ID=${CAMPAIGN_BROKER1_PORT}|" \
    -e "s|^default.ha.ha_port_id=.*|default.ha.ha_port_id=${CAMPAIGN_HA_PORT}|" \
    "${CTP_HOME}/conf/shell_ci.conf" > "${conf}"

# --- the case list CTP's own discovery rule produces (ticket 14 finding h) -------------------------
find "${scenario}" -name "*.sh" -type f -print | awk -F "/" '{ if ($(NF-2)".sh" == $NF) print }' | LC_ALL=C sort > "${bundle}/case-list.txt"
discovered_by_rule=$(wc -l < "${bundle}/case-list.txt")
[ "${discovered_by_rule}" -gt 0 ] || die "no case under ${scenario} matches CTP's discovery rule"
single=0; [ "${discovered_by_rule}" -eq 1 ] && [ "$(echo ${decl_cases} | wc -w)" -eq 1 ] && single=1
# workloads and pre-existing .result files
mkdir -p "${bundle}/preexisting"
while read -r f; do
    d=$(dirname "${f}"); n=$(basename "${f}" .sh)
    if [ ${single} -eq 1 ]; then cp "${f}" "${bundle}/workload.sh"; else mkdir -p "${bundle}/workload"; cp "${f}" "${bundle}/workload/${n}.sh"; fi
    [ -f "${d}/${n}.result" ] && cp -p "${d}/${n}.result" "${bundle}/preexisting/${n}.result"
done < "${bundle}/case-list.txt"

tc_commit=$(git -C "${worktree}" rev-parse HEAD)
tc_base=$(git -C "${worktree}" merge-base HEAD origin/develop)
tc_branch=$(git -C "${worktree}" rev-parse --abbrev-ref HEAD)
started_at=$(date -Is)
{
    echo "# ticket 15 identity file (run_ctp_shell.sh)"
    echo "manifest_id=${manifest_id}"
    echo "engine_baseline_commit=${CAMPAIGN_ENGINE_COMMIT}"
    echo "engine_worktree=/home/vimkim/gh/cb/oos-baseline-f4299ac0c"
    echo "install_prefix=${CUBRID}"
    echo "build_mode=${build}"
    echo "run_mode=client-server"
    echo "cubrid_rel=${CAMPAIGN_CUBRID_REL}"
    sha256sum "${CUBRID}/lib/libcubrid.so" "${CUBRID}/lib/libcubridsa.so" "${CUBRID}/bin/cub_server" "${CUBRID}/bin/csql"
    echo "ctp_home=${CTP_HOME}"
    echo "java_home=${JAVA_HOME}"
    sha256sum "${CTP_HOME}/shell/lib/cubridqa-shell.jar" "${CTP_HOME}/common/lib/cubridqa-common.jar" "${CTP_HOME}/shell/init_path/init.sh"
    echo "testcase_repository=${decl_repository}"
    echo "testcase_branch=${tc_branch}"
    echo "testcase_commit=${tc_commit}"
    echo "testcase_base_commit=${tc_base}"
    echo "testcase_worktree=${worktree}"
    echo "testcase_worktree_dirty=$(git -C "${worktree}" status --short | grep -c . || true)"
    echo "scenario=${scenario}"
    echo "context_revision=f6543de680b91ae357466b72a983f982892859cd"
    echo "context_content_hash=sha256:c9daf3c4ed25e16356ebf3c79c55f6bb7391d76c5664675a9aaf55cd5ac11698"
    echo "storage_root=${CAMPAIGN_STORAGE_ROOT}"
    echo "namespace=campaign_ns.sh"
    echo "home_redirected_to=${fake_home}"
    echo "command=timeout --foreground -k 30 ${inv_cap} ${CAMPAIGN_NS} ${CTP_HOME}/bin/ctp.sh shell -c ${conf}"
    echo "started_at=${started_at}"
} > "${bundle}/identity.txt"

# --- run ----------------------------------------------------------------------------------------------
export HOME="${fake_home}"
if [ ${single} -eq 1 ]; then export OOS_CAMPAIGN_EVIDENCE_DIR="${bundle}/case-evidence"; else unset OOS_CAMPAIGN_EVIDENCE_DIR; fi
log "running CTP shell for ${manifest_id} under campaign_ns.sh (cap ${inv_cap} s)"
t0=$(date +%s)
timeout --foreground -k 30 "${inv_cap}" script -qefc "${CAMPAIGN_NS} ${CTP_HOME}/bin/ctp.sh shell -c ${conf}" "${bundle}/transcript.raw" >/dev/null 2>&1
launcher_status=$?
t1=$(date +%s)
cap_reached=0; [ ${launcher_status} -eq 124 ] && cap_reached=1
tr -d '\r' < "${bundle}/transcript.raw" > "${bundle}/ctp.log"
rm -f "${bundle}/transcript.raw"
export HOME="${real_home}"
unset OOS_CAMPAIGN_EVIDENCE_DIR

# --- collect ----------------------------------------------------------------------------------------------
cp -r "${CTP_HOME}/result/shell/current_runtime_logs" "${bundle}/ctp_runtime_logs" 2>/dev/null
while read -r f; do
    d=$(dirname "${f}"); n=$(basename "${f}" .sh)
    [ -f "${d}/${n}.result" ] && cp -p "${d}/${n}.result" "${bundle}/${n}.result"
    if [ ${single} -eq 0 ]; then
        for ev in "${d}"/*_evidence; do
            [ -d "${ev}" ] || continue
            mkdir -p "${bundle}/case-evidence/${n}"
            cp -a "${ev}/." "${bundle}/case-evidence/${n}/"
            rm -rf "${ev}"
        done
    fi
    if [ -f "${bundle}/preexisting/${n}.result" ]; then cp -p "${bundle}/preexisting/${n}.result" "${d}/${n}.result"; else rm -f "${d}/${n}.result"; fi
done < "${bundle}/case-list.txt"
ended_at=$(date -Is)

# --- restore the install and verify --------------------------------------------------------------------------
[ -d "${bundle}/install_conf_backup" ] || die "the configuration backup is missing; refusing to touch ${CUBRID}/conf"
rm -rf "${CUBRID:?}/conf" "${CUBRID:?}/databases"
cp -a "${bundle}/install_conf_backup" "${CUBRID}/conf"
cp -a "${bundle}/install_databases_backup" "${CUBRID}/databases"
manifest_of "${CUBRID}/conf" > "${bundle}/install_conf.after"
manifest_of "${CUBRID}/databases" > "${bundle}/install_databases.after"
manifest_of "${real_home}/.CUBRID_SHELL_FM" > "${bundle}/user_shell_fm.after"
manifest_of "${scenario}" > "${bundle}/scenario_tree.after"
conf_drift=$(diff "${bundle}/install_conf.before" "${bundle}/install_conf.after" | grep -c '^[<>]' || true)
db_drift=$(diff "${bundle}/install_databases.before" "${bundle}/install_databases.after" | grep -c '^[<>]' || true)
fm_drift=$(diff "${bundle}/user_shell_fm.before" "${bundle}/user_shell_fm.after" | grep -c '^[<>]' || true)
tree_drift=$(diff "${bundle}/scenario_tree.before" "${bundle}/scenario_tree.after" | grep -c '^[<>]' || true)
status=${bundle}/ctp_runtime_logs/test_status.data
get() { grep "^$1=" "${status}" 2>/dev/null | cut -d= -f2; }
{
    echo "manifest_id=${manifest_id}"
    echo "build_mode=${build}"
    echo "launcher_exit_status=${launcher_status}"
    echo "cap_reached=${cap_reached}"
    echo "elapsed_seconds=$((t1 - t0))"
    echo "expected_case_count=$(echo ${decl_cases} | wc -w)"
    echo "discovered_by_rule_count=${discovered_by_rule}"
    echo "discovered_case_count=$(wc -l < "${bundle}/ctp_runtime_logs/dispatch_tc_ALL.txt" 2>/dev/null || echo 0)"
    echo "total_case_count=$(get total_case_count)"
    echo "executed_case_count=$(get total_executed_case_count)"
    echo "success_case_count=$(get total_success_case_count)"
    echo "fail_case_count=$(get total_fail_case_count)"
    echo "skip_case_count=$(get total_skip_case_count)"
    for r in "${bundle}"/*.result; do
        [ -f "${r}" ] || continue; n=$(basename "${r}" .result)
        echo "assertions_executed[${n}]=$(grep -cE "^${n}-[0-9]+ : (OK|NOK)" "${r}")"
        echo "assertions_ok[${n}]=$(grep -cE "^${n}-[0-9]+ : OK" "${r}")"
        echo "assertions_nok[${n}]=$(grep -cE "^${n}-[0-9]+ : NOK" "${r}")"
        echo "assertions_skipped[${n}]=$(grep -cE "^${n}-[0-9]+ : SKIP" "${r}")"
        ev=${bundle}/case-evidence; [ ${single} -eq 0 ] && ev=${bundle}/case-evidence/${n}
        if [ -f "${ev}/case_outcome" ]; then echo "case_outcome[${n}]=$(cat "${ev}/case_outcome")"; else echo "case_outcome[${n}]=MISSING"; fi
    done
    echo "install_conf_drift_lines=${conf_drift}"
    echo "install_databases_drift_lines=${db_drift}"
    echo "user_shell_fm_drift_lines=${fm_drift}"
    echo "worktree_drift_lines=${tree_drift}"
    echo "ended_at=${ended_at}"
} | tee "${bundle}/summary.txt"

cat > "${bundle}/replay.sh" <<EOF
#!/bin/bash
# Replay of ${manifest_id} (CTP shell, ${build} build).
#
# Prerequisites, none of which this script creates:
#   * the pinned engine installed at ${CUBRID}, built from
#     /home/vimkim/gh/cb/oos-baseline-f4299ac0c at ${CAMPAIGN_ENGINE_COMMIT} (identity.txt holds
#     the library hashes checked before the launcher started);
#   * CTP at ${CTP_HOME} (jar hashes in identity.txt) and a JDK 8 in JAVA_HOME;
#   * the testcase worktree ${worktree} at commit ${tc_commit} (branch ${tc_branch});
#   * TCP ports ${CAMPAIGN_PORTS} free; util-linux unshare with unprivileged user namespaces,
#     which is what contains the CTP helpers' unscoped process and IPC cleanup.
# No service needs to be running: the case creates, starts, crashes, restarts and drops its own
# database. The declared case list is ${declarations}.
exec bash ${here}/run_ctp_shell.sh --declarations ${declarations} --build ${build} --manifest-id <new-manifest-id> --attempt-ids <new-attempt-ids> --evidence-dir <evidence-dir>${scenario_override:+ --scenario-override ${scenario_override}}${oracle:+ --oracle ${oracle}}
EOF
chmod +x "${bundle}/replay.sh"

extra=()
[ ${cap_reached} -eq 1 ] && extra+=(--cap-reached)
[ -n "${cap_override}" ] && extra+=(--cap-seconds "${cap_override}")
[ -n "${oracle}" ] && extra+=(--oracle "${oracle}")
[ -n "${producer_version}" ] && extra+=(--producer-version "${producer_version}")
log "launcher exit ${launcher_status} (recorded, not trusted); building records"
python3 "${here}/ctp_shell_records.py" build --bundle "${bundle}" --declarations "${declarations}" \
    --manifest-id "${manifest_id}" --attempt-ids "${attempt_ids}" --evidence-dir "${evidence_dir}" \
    --kind "${kind}" --tier "${tier}" "${planted[@]}" "${extra[@]}"
rc=$?
# CTP snapshots the whole install into $HOME/.CUBRID_SHELL_FM on the first case (about 430 MiB per
# run). The redirected HOME is not evidence -- the before/after hashes above are -- so it is removed.
rm -rf "${fake_home}"
echo "bundle: ${bundle}"
echo "install drift: conf=${conf_drift} databases=${db_drift} user_shell_fm=${fm_drift}; worktree drift: ${tree_drift}"
exit ${rc}
