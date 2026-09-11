#!/bin/bash
# CBRD-26659 campaign ticket 14 -- complete one attempt's replay bundle.
#
#   finalize_bundle.sh <attempt-id> <case-path> <release_gcc|debug_gcc> <scenario-root> [<assertion>=NOK ...]
#
# run_attempt.sh collects what the launcher produced. This adds the three things the
# specification's replay-bundle list needs that the launcher does not produce: the exact
# workload as executed, the expected-versus-actual comparison, and a replay command with
# its prerequisites. It then prints the per-item paths, sizes and hashes that the bundle
# index is filled in from.
#
# Revision 8 (ticket 34, independent review finding F3). The EXPECTED side is read from
# expected-oracle.md section 5 -- the pre-derived, ordered assertion table -- and never from
# the result file: the previous version re-grepped the actual result, truncated every
# assertion name at its first digit, matched a SKIP shape the case never emits, and gave the
# negative control a header claiming "each OK". The expected status per row is OK, or SKIP
# where the oracle's "skips when" column names the build under test, or whatever the trailing
# <assertion>=NOK arguments say -- the negative control passes the assertion it plants a
# defect in, so its header states that run's real expectation. Each oracle row is then set
# against the actual line with the same number, by full name, and the verdict is MATCH only
# when every row matches and no unexpected numbered line exists.
# Known limit (delta review of ticket 34): expected_status recognises only the "release build" and
# "debug build" skip conditions of the oracle's "skips when" column. On a build without SHOW HEAP OOS
# the oracle's assertions 5 and 16 would compare as expected OK against actual SKIP, and the case-level
# "SKIP case_outcome" line would be listed as a numbered line the oracle does not know, so the verdict
# would be MISMATCH: conservative, never a false MATCH. A MISMATCH on a capability-gap run is therefore
# not a defect in the comparison; ticket 15's tooling should either keep and document this or extend
# the skip-condition matching.
set -u

if [ "$#" -lt 4 ]; then
    echo "usage: finalize_bundle.sh <attempt-id> <case-path> <build-mode> <scenario-root> [<assertion>=NOK ...]" >&2
    exit 2
fi

attempt_id=$1
case_path=$2
mode=$3
scenario=$4
shift 4
overrides="$*"

root=/home/vimkim/.cub/campaign/cbrd-26659/ticket14
oracle=${ORACLE:-/home/vimkim/gh/my-cubrid-docs/cbrd-26659/campaign/evidence/ticket14/expected-oracle.md}
bundle=${root}/attempts/${attempt_id}
name=$(basename "${case_path}" .sh)
[ -d "${bundle}" ] || { echo "no bundle at ${bundle}" >&2; exit 1; }
[ -f "${oracle}" ] || { echo "no oracle at ${oracle}" >&2; exit 1; }
result=${bundle}/${name}.result
[ -f "${result}" ] || { echo "no result file at ${result}" >&2; exit 1; }

cp "${case_path}" "${bundle}/workload.sh"

# --- expected side: the oracle's section-5 table --------------------------------------------
# Rows look like "| 10 | `recovery_redo_phase_replayed_log_records` | <expectation> | <skips when> |".
# Field 2 is the number, field 3 the backticked name, the last non-empty field the skip condition.
expected_rows=$(awk -F'|' '
    /^\| *[0-9]+ *\| *`[a-z0-9_]+` *\|/ {
        n=$2; gsub(/ /,"",n)
        nm=$3; gsub(/[` ]/,"",nm)
        sw=$(NF-1); gsub(/^ +| +$/,"",sw)
        print n "\t" nm "\t" sw
    }' "${oracle}")
expected_count=$(echo "${expected_rows}" | grep -c .)

expected_status()
{
    # expected_status <name> <skips when>  -> OK | SKIP | NOK
    local nm=$1 sw=$2 o
    for o in ${overrides}; do
        [ "${o}" = "${nm}=NOK" ] && { echo NOK; return; }
    done
    case "${mode}" in
        release_gcc) echo "${sw}" | grep -qi "release build" && { echo SKIP; return; } ;;
        debug_gcc)   echo "${sw}" | grep -qi "debug build" && { echo SKIP; return; } ;;
    esac
    echo OK
}

# --- actual side: one line per assertion, by number -------------------------------------------
actual_line()
{
    # actual_line <number> -> "<status> <name>" from the result file, or nothing
    sed -n "s/^${name}-$1 : \(OK\|NOK\|SKIP\) *\([A-Za-z0-9_]*\).*/\1 \2/p" "${result}" | head -1
}

mismatches=0
comparison=""
skips_expected=""
noks_expected=""
while IFS="$(printf '\t')" read -r n nm sw; do
    [ -n "${n}" ] || continue
    want=$(expected_status "${nm}" "${sw}")
    [ "${want}" = "SKIP" ] && skips_expected="${skips_expected}#${n} "
    [ "${want}" = "NOK" ] && noks_expected="${noks_expected}#${n} ${nm} "
    got=$(actual_line "${n}")
    got_status=${got%% *}
    got_name=${got#* }
    if [ -z "${got}" ]; then
        verdict="MISSING"; mismatches=$((mismatches+1))
    elif [ "${got_status}" = "${want}" ] && [ "${got_name}" = "${nm}" ]; then
        verdict="match"
    else
        verdict="MISMATCH"; mismatches=$((mismatches+1))
    fi
    comparison="${comparison}${n} | ${nm} | ${want} | ${got_status:--} | ${got_name:--} | ${verdict}
"
done <<EOF
${expected_rows}
EOF

# numbered lines the oracle does not list (the case-level SKIP outcome line takes the next number)
extra=$(sed -n "s/^${name}-\([0-9]*\) : .*/\1/p" "${result}" | while read -r n; do
    echo "${expected_rows}" | awk -F'\t' -v n="${n}" '$1==n{f=1} END{exit !f}' || grep "^${name}-${n} : " "${result}"
done)
[ -n "${extra}" ] && mismatches=$((mismatches+1))

if [ ${mismatches} -eq 0 ]; then verdict_all="MATCH"; else verdict_all="MISMATCH (${mismatches})"; fi

{
    echo "# expected versus actual -- ${attempt_id}"
    echo "# expected: the ${expected_count} assertions of expected-oracle.md section 5, in order, each OK,"
    echo "#           except: skipped on this ${mode} build: ${skips_expected:-none};"
    if [ -n "${noks_expected}" ]; then
        echo "#           planted defect, expected NOK: ${noks_expected}(a checker-validation run: the case as a whole must FAIL)"
    else
        echo "#           no planted defect (a regression run: the case as a whole must PASS)"
    fi
    echo "# actual  : ${name}.result as written by the case; each oracle row is set against the actual"
    echo "#           line with the same number, compared by status and by full assertion name."
    echo "# oracle  : $(sha256sum "${oracle}" | cut -d' ' -f1)  $(basename "${oracle}")"
    echo
    echo "## comparison"
    echo "n | oracle name | expected | actual status | actual name | verdict"
    printf '%s' "${comparison}"
    echo
    echo "## numbered actual lines the oracle does not list"
    echo "${extra:-(none)}"
    echo
    echo "## tally"
    echo "expected rows    = ${expected_count}"
    echo "executed(OK|NOK) = $(grep -cE "^${name}-[0-9]+ : (OK|NOK)" "${result}")"
    echo "OK               = $(grep -cE "^${name}-[0-9]+ : OK" "${result}")"
    echo "NOK              = $(grep -cE "^${name}-[0-9]+ : NOK" "${result}")"
    echo "SKIP             = $(grep -cE "^${name}-[0-9]+ : SKIP" "${result}")"
    echo
    echo "## verdict"
    echo "expected_vs_actual=${verdict_all}"
    echo
    echo "## actual (verbatim)"
    cat "${result}"
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
echo "expected_vs_actual=${verdict_all}"
echo
for f in workload.sh identity.txt shell_cbrd26659.conf expected_vs_actual.txt replay.sh \
         case-evidence/operations.journal case-evidence/skipped.journal \
         case-evidence/show_heap_oos_after_insert.out case-evidence/show_heap_oos_after_recovery.out \
         case-evidence/recovery_log_excerpt.txt \
         case-evidence/paramdump.out case-evidence/createdb.out case-evidence/checkdb.out \
         case-evidence/oos.log "${name}.result" ctp_runtime_logs/feedback.log \
         ctp_runtime_logs/test_status.data ctp_runtime_logs/dispatch_tc_ALL.txt; do
    if [ -f "${bundle}/${f}" ]; then
        echo "$(sha256sum "${bundle}/${f}" | cut -d' ' -f1)  ${f}"
    else
        echo "ABSENT                                                            ${f}"
    fi
done
for f in "${bundle}"/case-evidence/server_log/*.err; do
    [ -f "${f}" ] && echo "$(sha256sum "${f}" | cut -d' ' -f1)  case-evidence/server_log/$(basename "${f}")"
done
echo
echo "core files in the bundle and the install: $(find "${bundle}" /home/vimkim/.cub/install/oos-baseline-f4299ac0c/${mode} -name 'core*' -type f 2>/dev/null | wc -l)"
