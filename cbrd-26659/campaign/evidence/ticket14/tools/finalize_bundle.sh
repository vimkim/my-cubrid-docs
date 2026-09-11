#!/bin/bash
# CBRD-26659 campaign ticket 14 -- complete one attempt's replay bundle.
#
#   finalize_bundle.sh <attempt-id> <case-path> <release_gcc|debug_gcc> <scenario-root>
#
# run_attempt.sh collects what the launcher produced. This adds the three things the
# specification's replay-bundle list needs that the launcher does not produce: the exact
# workload as executed, the expected-versus-actual comparison, and a replay command with
# its prerequisites. It then prints the per-item paths, sizes and hashes that the bundle
# index is filled in from.
set -u

if [ "$#" -ne 4 ]; then
    echo "usage: finalize_bundle.sh <attempt-id> <case-path> <build-mode> <scenario-root>" >&2
    exit 2
fi

attempt_id=$1
case_path=$2
mode=$3
scenario=$4

root=/home/vimkim/.cub/campaign/cbrd-26659/ticket14
bundle=${root}/attempts/${attempt_id}
name=$(basename "${case_path}" .sh)
[ -d "${bundle}" ] || { echo "no bundle at ${bundle}" >&2; exit 1; }

cp "${case_path}" "${bundle}/workload.sh"

# Expected versus actual. The case is its own comparator -- every assertion names itself
# and prints the mismatch on failure -- so the comparison is the ordered assertion list
# from the pre-run oracle set against the result file the run produced.
{
    echo "# expected versus actual -- ${attempt_id}"
    echo "# expected: the 17 assertions of expected-oracle.md section 5, in order,"
    echo "#           each OK, with #17 skipped on a release build."
    echo "# actual  : ${name}.result as written by the case."
    echo
    echo "## actual"
    cat "${bundle}/${name}.result"
    echo
    echo "## tally"
    echo "executed(OK|NOK) = $(grep -cE "^${name}-[0-9]+ : (OK|NOK)" "${bundle}/${name}.result")"
    echo "OK               = $(grep -cE "^${name}-[0-9]+ : OK" "${bundle}/${name}.result")"
    echo "NOK              = $(grep -cE "^${name}-[0-9]+ : NOK" "${bundle}/${name}.result")"
    echo "SKIP             = $(grep -c ' : SKIP ' "${bundle}/${name}.result")"
    echo
    echo "## assertion names in the order the oracle lists them"
    grep -oE '^'"${name}"'-(([0-9]+ : (OK|NOK))|skip : SKIP) *[a-z_]*' "${bundle}/${name}.result"
} > "${bundle}/expected_vs_actual.txt"

cat > "${bundle}/replay.sh" <<EOF
#!/bin/bash
# Replay of ${attempt_id}.
#
# Prerequisites, none of which this script creates:
#   * the pinned engine installed at
#       /home/vimkim/.cub/install/oos-baseline-f4299ac0c/${mode}
#     built from /home/vimkim/gh/cb/oos-baseline-f4299ac0c at
#     f4299ac0cd777a2a964c1f197ae5ebf9841a4936. identity.txt holds the library hashes
#     run_attempt.sh checks before it will start.
#   * CTP installed at /home/vimkim/CTP (jar hashes in identity.txt).
#   * the testcase worktree on branch CBRD-26659-oos-testcases-handover, with the case at
#       ${case_path}
#   * TCP ports 26659, 33120, 33121 and 33122 free.
#   * util-linux unshare with unprivileged user namespaces enabled, which is what
#     contains the CTP helpers' unscoped process and IPC cleanup.
#
# No service needs to be running: the case creates, starts, crashes, restarts and drops
# its own database.
exec bash ${root}/tools/run_attempt.sh <new-attempt-id> ${mode} ${scenario}
EOF
chmod +x "${bundle}/replay.sh"

echo "root_path=${bundle}"
echo "total_bytes=$(du -sb "${bundle}" | cut -f1)"
echo "bundle_sha256=$(find "${bundle}" -type f | sort | xargs sha256sum | sha256sum | cut -d' ' -f1)"
echo
for f in workload.sh identity.txt shell_cbrd26659.conf expected_vs_actual.txt replay.sh \
         case-evidence/operations.journal case-evidence/skipped.journal \
         case-evidence/show_heap_oos_after_insert.out case-evidence/show_heap_oos_after_recovery.out \
         case-evidence/paramdump.out case-evidence/createdb.out case-evidence/checkdb.out \
         case-evidence/oos.log "${name}.result" ctp_runtime_logs/feedback.log \
         ctp_runtime_logs/test_status.data ctp_runtime_logs/dispatch_tc_ALL.txt; do
    if [ -f "${bundle}/${f}" ]; then
        echo "$(sha256sum "${bundle}/${f}" | cut -d' ' -f1)  ${f}"
    else
        echo "ABSENT                                                            ${f}"
    fi
done
echo
echo "core files in the bundle and the install: $(find "${bundle}" /home/vimkim/.cub/install/oos-baseline-f4299ac0c/${mode} -name 'core*' -type f 2>/dev/null | wc -l)"
