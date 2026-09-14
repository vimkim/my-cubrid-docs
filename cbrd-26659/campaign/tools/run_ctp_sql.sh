#!/bin/bash
# CBRD-26659 campaign ticket 15 -- run one CTP SQL invocation and turn it into execution proof.
#
#   run_ctp_sql.sh --declarations FILE --build release|debug --manifest-id ID
#                  --attempt-ids a[,b,...] --evidence-dir DIR
#                  [--scenario-override DIR] [--kind original|checker-validation|coexistence]
#                  [--no-activation] [--tier fast|scheduled|extended] [--producer-version TEXT]
#                  [--promotions FILE] [--reserve-bytes N]
#
# After the launcher exits this script has produced, under <evidence-dir>: one manifest (kind
# original), one attempt record per executed case and one replay-bundle index per attempt,
# each validated against ticket 12's schemas before it is written; and, under the campaign
# storage, the packed replay bundle. The testcase repository is left exactly as found.
#
# What it takes care of, beyond invoking the launcher (sources in brackets):
#
#   containment  the launcher runs under campaign_ns.sh, so CTP's do_clean `pkill cub` and its
#                ipcrm sweep can only reach what this invocation started [ticket 14 section 2;
#                ticket 13 had to stop an unrelated master by hand instead].
#   ports        26659/33120/33121/33122 are verified free first [ticket 14 section 2].
#   identity     CUBRID/PATH/LD_LIBRARY_PATH point at the pinned install and both library
#                hashes are checked against the campaign's re-pinned build before anything starts,
#                and so are the CTP tree's jars and init.sh [ticket 41; ticket 37 item 1].
#   install      $CUBRID/conf and $CUBRID/databases are backed up, hashed before and after and
#                restored verbatim: CTP's run.sh writes the invocation's ports into cubrid.conf
#                and keeps .forFun copies [ticket 13 section 11]. CUBRID_DATABASES is the
#                campaign's own directory, so `basic` never lands in the install.
#   worktree     CTP writes <case>.result into the repository's cases/ directory on every run;
#                the files are copied into the bundle and the tree is restored to its pre-run
#                state, verified by hash.
#   proof        main.info and summary.info are read by ctp_sql_records.py; the launcher exit
#                status is recorded, never trusted [ticket 13 findings a, b, d].
#   activation   the declared checker runs client-server under campaign_ns.sh in the case's own
#                run mode, so its evidence can be `proven` [user decision O2, ticket 35].
#   cap          the invocation cap of the tier is enforced with `timeout`; a killed launcher
#                is recorded as invocation_cap_reached with everything captured so far.
#   admission    retention.py admit refuses to start at the storage limit [decision 08].
set -u
here=$(cd "$(dirname "$0")" && pwd)
. "${here}/campaign_env.sh"

declarations="" build="" manifest_id="" attempt_ids="" evidence_dir="" scenario_override="" kind=original
activation=yes tier=fast producer_version="" promotions="" reserve_bytes=$((2 * 1024 * 1024 * 1024)) cap_override=""
while [ $# -gt 0 ]; do
    case "$1" in
        --declarations) declarations=$2; shift 2 ;;
        --build) build=$2; shift 2 ;;
        --manifest-id) manifest_id=$2; shift 2 ;;
        --attempt-ids) attempt_ids=$2; shift 2 ;;
        --evidence-dir) evidence_dir=$2; shift 2 ;;
        --scenario-override) scenario_override=$2; shift 2 ;;
        --kind) kind=$2; shift 2 ;;
        --no-activation) activation=no; shift ;;
        --tier) tier=$2; shift 2 ;;
        --producer-version) producer_version=$2; shift 2 ;;
        --promotions) promotions=$2; shift 2 ;;
        --reserve-bytes) reserve_bytes=$2; shift 2 ;;
        --cap-override) cap_override=$2; shift 2 ;;
        *) die "unknown argument $1" ;;
    esac
done
[ -n "${declarations}" ] && [ -n "${build}" ] && [ -n "${manifest_id}" ] && [ -n "${attempt_ids}" ] && [ -n "${evidence_dir}" ] \
    || die "usage: run_ctp_sql.sh --declarations FILE --build release|debug --manifest-id ID --attempt-ids a,b --evidence-dir DIR [...]"

# --- declarations -> shell variables -------------------------------------------------------------
eval "$(python3 - "${declarations}" <<'EOF'
import json, sys, shlex
d = json.load(open(sys.argv[1]))
print("decl_repository=" + shlex.quote(d["repository"]))
print("decl_scenario=" + shlex.quote(d["scenario"]))
print("decl_page_size=" + shlex.quote(str(d.get("page_size", 16384))))
print("decl_cases=" + shlex.quote(" ".join(sorted(d["cases"]))))
act = {n: c["activation_check"] for n, c in d["cases"].items() if c.get("activation_check")}
print("decl_activation=" + shlex.quote(" ".join(f"{n}:{c['script']}:{':'.join(map(str, c.get('args', [])))}" for n, c in act.items())))
EOF
)"
case "${decl_repository}" in
    testcases) worktree=/home/vimkim/gh/tc/cubrid-testcases-cbrd-26659 ;;
    testcases-private-ex) worktree=/home/vimkim/gh/tc/cubrid-testcases-private-ex-cbrd-26659 ;;
    *) die "unknown repository ${decl_repository}" ;;
esac
scenario=${scenario_override:-${worktree}/${decl_scenario}}
[ -d "${scenario}" ] || die "scenario ${scenario} does not exist"
case_dir=$(find "${scenario}" -type d -name cases | head -1)
[ -n "${case_dir}" ] || die "no cases/ directory under ${scenario}"
answer_dir="$(dirname "${case_dir}")/answers"
[ "${tier}" = fast ] && inv_cap=900 || { [ "${tier}" = scheduled ] && inv_cap=7200 || inv_cap=28800; }
[ -n "${cap_override}" ] && inv_cap=${cap_override}   # cap-enforcement control only; recorded in the manifest

# --- preflight -----------------------------------------------------------------------------------
campaign_check_namespace
campaign_check_ports
campaign_check_ctp
campaign_set_engine "${build}"
[ -f "${CUBRID}/jdbc/cubrid_jdbc.jar" ] || die "${CUBRID}/jdbc/cubrid_jdbc.jar is missing; CTP needs the JDBC client artifact (ticket 13 finding c)"
campaign_admit "${reserve_bytes}"

bundle=${CAMPAIGN_TICKET_ROOT}/attempts/${manifest_id}
[ -e "${bundle}" ] && die "bundle ${bundle} already exists; attempts are never overwritten"
mkdir -p "${bundle}/ctp_result" "${evidence_dir}"
export CUBRID_DATABASES=${CAMPAIGN_TICKET_ROOT}/ctpdb
mkdir -p "${CUBRID_DATABASES}"
[ -f "${CUBRID_DATABASES}/databases.txt" ] || printf '#db-name\tvol-path\t\tdb-host\t\tlog-path\t\tlob-base-path\n' > "${CUBRID_DATABASES}/databases.txt"

# --- the CTP configuration used (recorded in the bundle) ------------------------------------------
conf=${bundle}/sql_${manifest_id}.conf
cat > "${conf}" <<EOF
# CBRD-26659 campaign ticket 15 -- CTP SQL configuration generated by run_ctp_sql.sh for ${manifest_id}.
# Derived from ticket 13's sql_cbrd26659.conf; the HA port and MASTER_SHM_ID use the campaign's
# ha port ${CAMPAIGN_HA_PORT} instead of ticket 13's 59901 so that every port a master could open is
# a campaign-allocated one.
[sql]
scenario = ${scenario}
enable_memory_leak = no
testcase_exclude_from_file = \${CTP_HOME}/conf/exclusions.txt
test_category = sql
jdbc_config_file = test_default.xml
db_charset = en_US
need_make_locale = no
cubrid_createdb_opts = --db-volume-size=128M --log-volume-size=64M --db-page-size=${decl_page_size} --log-page-size=${decl_page_size}

[sql/cubrid.conf]
java_stored_procedure = yes
test_mode = yes
max_plan_cache_entries = 1000
unicode_input_normalization = no
cubrid_port_id = ${CAMPAIGN_PORT_ID}
ha_mode = yes
lock_timeout = 10sec

[sql/cubrid_ha.conf]
ha_mode = yes
ha_apply_max_mem_size = 300
ha_port_id = ${CAMPAIGN_HA_PORT}

[sql/cubrid_broker.conf/%query_editor]
SERVICE = OFF

[sql/cubrid_broker.conf/%BROKER1]
BROKER_PORT = ${CAMPAIGN_BROKER1_PORT}
APPL_SERVER_SHM_ID = ${CAMPAIGN_BROKER1_PORT}
APPL_SERVER_MAX_SIZE = 100M

[sql/cubrid_broker.conf/broker]
MASTER_SHM_ID = ${CAMPAIGN_HA_PORT}
EOF

# --- snapshots before ----------------------------------------------------------------------------
manifest_of "${CUBRID}/conf" > "${bundle}/install_conf.before"
manifest_of "${CUBRID}/databases" > "${bundle}/install_databases.before"
manifest_of "${scenario}" > "${bundle}/scenario_tree.before"
cp -a "${CUBRID}/conf" "${bundle}/install_conf_backup"
cp -a "${CUBRID}/databases" "${bundle}/install_databases_backup"

# workload and expected answer, and the pre-existing .result files CTP would overwrite
single=0; [ "$(echo ${decl_cases} | wc -w)" -eq 1 ] && single=1
mkdir -p "${bundle}/preexisting"
for c in ${decl_cases}; do
    if [ ${single} -eq 1 ]; then w=${bundle}/workload.sql; a=${bundle}/expected.answer; else mkdir -p "${bundle}/workload" "${bundle}/expected"; w=${bundle}/workload/${c}.sql; a=${bundle}/expected/${c}.answer; fi
    [ -f "${case_dir}/${c}.sql" ] && cp "${case_dir}/${c}.sql" "${w}"
    [ -f "${answer_dir}/${c}.answer" ] && cp "${answer_dir}/${c}.answer" "${a}"
    [ -f "${case_dir}/${c}.result" ] && cp -p "${case_dir}/${c}.result" "${bundle}/preexisting/${c}.result"
done

tc_commit=$(git -C "${worktree}" rev-parse HEAD)
tc_base=$(git -C "${worktree}" merge-base HEAD origin/develop)
tc_branch=$(git -C "${worktree}" rev-parse --abbrev-ref HEAD)
started_at=$(date -Is)
{
    echo "# ticket 15 identity file (run_ctp_sql.sh)"
    echo "manifest_id=${manifest_id}"
    echo "engine_baseline_commit=${CAMPAIGN_ENGINE_COMMIT}"
    echo "engine_worktree=/home/vimkim/gh/cb/oos-baseline-f4299ac0c"
    echo "install_prefix=${CUBRID}"
    echo "build_mode=${build}"
    echo "run_mode=client-server"
    echo "page_size=${decl_page_size}"
    echo "cubrid_rel=${CAMPAIGN_CUBRID_REL}"
    sha256sum "${CUBRID}/lib/libcubrid.so" "${CUBRID}/lib/libcubridsa.so" "${CUBRID}/bin/cub_server" "${CUBRID}/bin/csql" "${CUBRID}/jdbc/cubrid_jdbc.jar"
    echo "ctp_home=${CTP_HOME}"
    echo "java_home=${JAVA_HOME}"
    sha256sum "${CTP_HOME}/sql/lib/cubridqa-cqt.jar" "${CTP_HOME}/common/lib/cubridqa-common.jar" "${CTP_HOME}/shell/init_path/init.sh"
    echo "testcase_repository=${decl_repository}"
    echo "testcase_branch=${tc_branch}"
    echo "testcase_commit=${tc_commit}"
    echo "testcase_base_commit=${tc_base}"
    echo "testcase_worktree=${worktree}"
    echo "testcase_worktree_dirty=$(git -C "${worktree}" status --short | grep -c . || true)"
    echo "scenario=${scenario}"
    echo "context_revision=f6543de680b91ae357466b72a983f982892859cd"
    echo "context_content_hash=sha256:c9daf3c4ed25e16356ebf3c79c55f6bb7391d76c5664675a9aaf55cd5ac11698"
    echo "cubrid_databases=${CUBRID_DATABASES}"
    echo "storage_root=${CAMPAIGN_STORAGE_ROOT}"
    echo "namespace=campaign_ns.sh"
    echo "command=timeout --foreground -k 20 ${inv_cap} ${CAMPAIGN_NS} ${CTP_HOME}/bin/ctp.sh sql -c ${conf}"
    echo "started_at=${started_at}"
} > "${bundle}/identity.txt"

# --- run --------------------------------------------------------------------------------------------
log "running CTP SQL for ${manifest_id} under campaign_ns.sh (cap ${inv_cap} s)"
t0=$(date +%s)
timeout --foreground -k 20 "${inv_cap}" script -qefc "${CAMPAIGN_NS} ${CTP_HOME}/bin/ctp.sh sql -c ${conf}" "${bundle}/transcript.raw" >/dev/null 2>&1
launcher_status=$?
t1=$(date +%s)
cap_reached=0; [ ${launcher_status} -eq 124 ] && cap_reached=1
tr -d '\r' < "${bundle}/transcript.raw" > "${bundle}/ctp.log"
rm -f "${bundle}/transcript.raw"

# --- collect --------------------------------------------------------------------------------------------
result_dir=$(grep -m1 '^Test Result Directory:' "${bundle}/ctp.log" | cut -d: -f2- | tr -d '[:space:]')
[ -z "${result_dir}" ] && result_dir=$(grep -m1 '^Result Root Dir:' "${bundle}/ctp.log" | cut -d: -f2- | tr -d '[:space:]')
if [ -n "${result_dir}" ] && [ -d "${result_dir}" ]; then
    cp -r "${result_dir}/." "${bundle}/ctp_result/"
else
    log "WARNING: no result directory found in the launcher log; the proof will fail"
fi
mkdir -p "${bundle}/actual"
for c in ${decl_cases}; do
    if [ -f "${case_dir}/${c}.result" ]; then
        if [ ${single} -eq 1 ]; then cp -p "${case_dir}/${c}.result" "${bundle}/actual.result"; else cp -p "${case_dir}/${c}.result" "${bundle}/actual/${c}.result"; fi
    fi
    # restore the worktree: put back the pre-existing .result or remove the new one
    if [ -f "${bundle}/preexisting/${c}.result" ]; then cp -p "${bundle}/preexisting/${c}.result" "${case_dir}/${c}.result"; else rm -f "${case_dir}/${c}.result"; fi
done
rmdir "${bundle}/actual" 2>/dev/null || true

# --- paired activation check, client-server, under the namespace ---------------------------------------
if [ "${activation}" = yes ] && [ -n "${decl_activation}" ] && [ ${cap_reached} -eq 0 ]; then
    # CTP's do_clean restored cubrid.conf from its .forFun copy; make sure the port the checker
    # will use is the campaign's (the whole conf directory is restored from the backup below).
    sed -i "s/^cubrid_port_id=.*/cubrid_port_id=${CAMPAIGN_PORT_ID}/" "${CUBRID}/conf/cubrid.conf"
    grep -q "^cubrid_port_id=${CAMPAIGN_PORT_ID}$" "${CUBRID}/conf/cubrid.conf" || echo "cubrid_port_id=${CAMPAIGN_PORT_ID}" >> "${CUBRID}/conf/cubrid.conf"
    campaign_check_ports
    for spec in ${decl_activation}; do
        c=${spec%%:*}; rest=${spec#*:}; script_name=${rest%%:*}; args=$(echo "${rest#*:}" | tr ':' ' ')
        script_path=${here}/${script_name}; [ -x "${script_path}" ] || script_path=${script_name}
        log "activation check for ${c}: ${script_name} ${args} (client-server, under campaign_ns.sh)"
        CAMPAIGN_TICKET_ROOT="${CAMPAIGN_TICKET_ROOT}" CAMPAIGN_PORT_ID="${CAMPAIGN_PORT_ID}" ACTIVATION_PAGE_SIZE="${decl_page_size}" \
            "${CAMPAIGN_NS}" "${script_path}" "${CUBRID}" "${bundle}/activation/${c}" ${args} > "${bundle}/activation_${c}.log" 2>&1
        echo "activation_exit[${c}]=$?" >> "${bundle}/identity.txt"
    done
fi
ended_at=$(date -Is)

# --- restore the install and verify by hash -----------------------------------------------------------
[ -d "${bundle}/install_conf_backup" ] || die "the configuration backup is missing; refusing to touch ${CUBRID}/conf"
rm -rf "${CUBRID:?}/conf" "${CUBRID:?}/databases"
cp -a "${bundle}/install_conf_backup" "${CUBRID}/conf"
cp -a "${bundle}/install_databases_backup" "${CUBRID}/databases"
manifest_of "${CUBRID}/conf" > "${bundle}/install_conf.after"
manifest_of "${CUBRID}/databases" > "${bundle}/install_databases.after"
manifest_of "${scenario}" > "${bundle}/scenario_tree.after"
conf_drift=$(diff "${bundle}/install_conf.before" "${bundle}/install_conf.after" | grep -c '^[<>]' || true)
db_drift=$(diff "${bundle}/install_databases.before" "${bundle}/install_databases.after" | grep -c '^[<>]' || true)
tree_drift=$(diff "${bundle}/scenario_tree.before" "${bundle}/scenario_tree.after" | grep -c '^[<>]' || true)
{
    echo "install_conf_drift_lines=${conf_drift}"
    echo "install_databases_drift_lines=${db_drift}"
    echo "worktree_drift_lines=${tree_drift}"
    echo "result_dir=${result_dir}"
    echo "ended_at=${ended_at}"
} >> "${bundle}/identity.txt"
{
    echo "started_at=${started_at}"
    echo "ctp_exit=${launcher_status}"
    echo "elapsed_seconds=$((t1 - t0))"
    echo "cap_reached=${cap_reached}"
    echo "ended_at=${ended_at}"
} > "${bundle}/timing.txt"

cat > "${bundle}/replay.sh" <<EOF
#!/bin/bash
# Replay of ${manifest_id} (CTP SQL, ${build} build, client-server, ${decl_page_size} B pages).
#
# Prerequisites, none of which this script creates:
#   * the pinned engine installed at ${CUBRID}, built from
#     /home/vimkim/gh/cb/oos-baseline-f4299ac0c at ${CAMPAIGN_ENGINE_COMMIT}, with the JDBC client
#     artifact under jdbc/ (identity.txt holds the hashes checked before the launcher started);
#   * CTP at ${CTP_HOME} (jar hashes in identity.txt) and a JDK 8 in JAVA_HOME;
#   * the testcase worktree ${worktree} at commit ${tc_commit} (branch ${tc_branch});
#   * TCP ports ${CAMPAIGN_PORTS} free; util-linux unshare with unprivileged user namespaces.
# No service needs to be running: CTP creates, starts and drops its own database inside the
# namespace. The declared case list is ${declarations}.
exec bash ${here}/run_ctp_sql.sh --declarations ${declarations} --build ${build} --manifest-id <new-manifest-id> --attempt-ids <new-attempt-ids> --evidence-dir <evidence-dir>${scenario_override:+ --scenario-override ${scenario_override}}
EOF
chmod +x "${bundle}/replay.sh"

# --- records ---------------------------------------------------------------------------------------------
act_args=()
for spec in ${decl_activation:-}; do c=${spec%%:*}; [ -d "${bundle}/activation/${c}" ] && act_args+=(--activation "${c}=${bundle}/activation/${c}"); done
extra=()
[ ${cap_reached} -eq 1 ] && extra+=(--cap-reached)
[ -n "${cap_override}" ] && extra+=(--cap-seconds "${cap_override}")
[ -n "${promotions}" ] && extra+=(--promotions "${promotions}")
[ -n "${producer_version}" ] && extra+=(--producer-version "${producer_version}")
log "launcher exit ${launcher_status} (recorded, not trusted); building records"
python3 "${here}/ctp_sql_records.py" build --bundle "${bundle}" --result-dir "${bundle}/ctp_result" \
    --declarations "${declarations}" --manifest-id "${manifest_id}" --attempt-ids "${attempt_ids}" \
    --evidence-dir "${evidence_dir}" --kind "${kind}" --tier "${tier}" --build-mode "${build}" \
    --launcher-exit "${launcher_status}" --activation-evidence-copy "${act_args[@]}" "${extra[@]}"
rc=$?
echo "bundle: ${bundle}"
echo "install drift: conf=${conf_drift} databases=${db_drift}; worktree drift: ${tree_drift}"
exit ${rc}
