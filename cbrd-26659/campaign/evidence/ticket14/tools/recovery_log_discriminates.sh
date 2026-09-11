#!/bin/bash
# CBRD-26659 campaign ticket 14, revision 8 (ticket 34) -- shows that the recovery-log shapes
# DISCRIMINATE: run against the code they were written to catch, they are not caught.
#
# Revision 7 (testcase commit adbd8b745) judged the restart by two things only: `cubrid
# server start` exited 0 and a probe query answered within the deadline. It never opened
# $CUBRID/log/server. So every shape the revision-8 reader rejects -- a log with no REDO
# phase, an empty log, a REDO phase with nothing to redo, the utility's unconditional banner
# -- passes revision 7's judgement unchanged, which is exactly the gap the independent review
# named (F1). The specification asks that a controlled failure example be shown to
# discriminate by running it against code that lacks the check; this is that run.
set -u
worktree=/home/vimkim/gh/tc/cubrid-testcases-private-ex-cbrd-26659
case_rel=shell/_06_issues/_26_2h/cbrd_26659_oos_dur01/cases/cbrd_26659_oos_dur01.sh
tools=$(cd "$(dirname "$0")" && pwd)

rev7=$(git -C "${worktree}" show adbd8b745:${case_rel})
echo "revision 7 (adbd8b745) lines that read the recovery messages: $(echo "${rev7}" | grep -c 'REDO Phase\|Log recovery')   <- none: the check did not exist"
echo "revision 7 lines that mention log/server at all: $(echo "${rev7}" | grep -c 'log/server')   <- only the failure-preservation COPY of the directory, never a read"
echo "revision 7 post-restart judgement, verbatim:"
echo "${rev7}" | grep -n 'restart_rc} -eq 0 \] && wait_for' | sed 's/^/    /'
echo

# Revision 7's judgement, as the case applied it: exit status 0 and a probe query answered.
# It takes no log text at all, which is the point.
rev7_judge()
{
    # rev7_judge <restart_rc> <probe output> <server log text, IGNORED by revision 7>
    if [ "$1" -eq 0 ] && echo "$2" | grep -q 'row selected'; then echo OK; else echo NOK; fi
}
# Revision 8's judgement is the reader under test, extracted verbatim into the checker.
. "${tools}/checker_validation_recovery_log.sh" >/dev/null 2>&1 || true

PROBE="
            1
  1 row selected. (0.000000 sec) Committed."
ANALYSIS_ONLY="
Log recovery is started.
Log recovery: ANALYSIS Phase is started.
Log recovery: ANALYSIS Phase is finished.
Log recovery is finished.
"
ZERO="
Log recovery: REDO Phase is started. Log pages to redo: 0, Log records to redo: 0.
"
BANNER="
This may take a long time depending on the amount of recovery works to do.
"

n=0; disc=0
show()
{
    local label=$1 text=$2 r7 r8
    r7=$(rev7_judge 0 "${PROBE}" "${text}")
    r8=$(judge_recovery_log 0 "${text}" | cut -d'|' -f1)
    n=$((n+1))
    if [ "${r7}" = "OK" ] && [ "${r8}" = "NOK" ]; then disc=$((disc+1)); mark="discriminates"; else mark="DOES NOT DISCRIMINATE"; fi
    printf '  %-45s revision 7: %-3s  revision 8: %-3s  %s\n' "${label}" "${r7}" "${r8}" "${mark}"
}
echo "shape                                          judged by a successful restart (rc=0, probe answered)"
show "no REDO phase (analysis lines only)" "${ANALYSIS_ONLY}"
show "empty server log"                    ""
show "REDO phase with nothing to redo"     "${ZERO}"
show "the utility's unconditional banner"  "${BANNER}"
echo
echo "shapes=${n} discriminating=${disc}"
[ ${disc} -eq ${n} ]
