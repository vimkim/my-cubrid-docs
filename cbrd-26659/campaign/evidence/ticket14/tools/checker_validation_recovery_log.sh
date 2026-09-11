#!/bin/bash
# CBRD-26659 campaign ticket 14, revision 8 (ticket 34) -- checker validation for the fourth
# checking mechanism: the recovery-log reader behind assertion 10,
# recovery_redo_phase_replayed_log_records.
#
# Why it exists. The independent review of ticket 14 (finding F1) showed that the case
# proved a server came back up, not that recovery replayed anything: had every dirty page
# been flushed before the kill -9, every value assertion would pass on an engine that never
# logged an OOS operation. Revision 8 reads the engine's own recovery lines from
# $CUBRID/log/server/<db>_*.err. That is a new checking mechanism, so the specification's
# rule applies: a controlled failure example the checker must detect, shown to discriminate
# (recovery_log_discriminates.sh runs these shapes against revision 7's judgement).
#
# The function bodies below are extracted VERBATIM from the case, so this cannot drift away
# from what it validates. Exit status 0 only when every shape is judged correctly.
#
# Shapes:
#   1  the real five-line recovery sequence from a pinned release run (att-T14-0028's
#      preserved server log), before=0                      -> OK|pages=2|records=83
#   2  the analysis lines only, no REDO phase                  -> NOK (nothing added)
#   3  an empty log                                             -> NOK
#   4  a REDO phase with zero records to redo                   -> NOK (nothing to redo)
#   5  two REDO phases when none was there before               -> NOK (a stale phase must
#      not be read as the restart's, and two recoveries is not this schedule)
#   6  two REDO phases when one was there before                -> OK, with the LAST line's
#      counts (the restart's), not the first's
#   7  a REDO line whose counts do not parse                    -> NOK
#   8  the utility's unconditional banner, "This may take a long time depending on the
#      amount of recovery works to do", which server_restart.out carries on every start
#      and which the review found byte-identical to server_start.out -> NOK
#   9  the UNDO line parses to "<pages> <transactions>"; absent -> empty
#  10  before is not a number (a broken count before the crash) -> treated as 0, so one
#      phase after the restart is still OK rather than a shell error

is_number()
{
    echo "$1" | grep -qE '^[0-9]+$'
}
# The counts the engine printed on its LAST REDO-phase line: "<pages> <records>", or
# nothing when there is no such line or it does not carry both numbers.
recovery_redo_counts()
{
    echo "$1" | grep "Log recovery: REDO Phase is started" | tail -1 \
        | sed -n 's/.*Log pages to redo: \([0-9][0-9]*\), Log records to redo: \([0-9][0-9]*\).*/\1 \2/p'
}
# The counts on the LAST UNDO-phase line: "<pages> <transactions>", or nothing.
recovery_undo_counts()
{
    echo "$1" | grep "Log recovery: UNDO Phase is started" | tail -1 \
        | sed -n 's/.*Log pages to undo: \([0-9][0-9]*\), transactions to undo: \([0-9][0-9]*\).*/\1 \2/p'
}
judge_recovery_log()
{
    local before=$1 text=$2 after added counts pages records
    after=`echo "${text}" | grep -c "Log recovery: REDO Phase is started"`
    is_number "${before}" || before=0
    added=`expr ${after} - ${before}`
    if [ "${added}" -ne 1 ]; then
        echo "NOK|expected exactly one REDO phase added by the restart, found ${added} (before=${before}, after=${after})"
        return 1
    fi
    counts=`recovery_redo_counts "${text}"`
    if [ -z "${counts}" ]; then
        echo "NOK|the REDO line carries no parsable page and record counts"
        return 1
    fi
    pages=`echo "${counts}" | cut -d' ' -f1`
    records=`echo "${counts}" | cut -d' ' -f2`
    if [ "${records}" -lt 1 ]; then
        echo "NOK|recovery found nothing to redo (records=${records}): the values may have survived because the pages were already flushed, not because redo restored them"
        return 1
    fi
    echo "OK|pages=${pages}|records=${records}"
}

fails=0
chk()
{
    # chk <label> <before> <text> <expected verdict prefix, OK or NOK> [<expected full OK line>]
    local got rc
    got=`judge_recovery_log "$2" "$3"`; rc=$?
    case "$4" in
        OK)  if [ ${rc} -eq 0 ] && [ "${got}" = "$5" ]; then echo "ok   $1 -> ${got}"; else echo "FAIL $1 -> rc=${rc} ${got}, want $5"; fails=$((fails+1)); fi ;;
        NOK) if [ ${rc} -ne 0 ] && [ "${got#NOK|}" != "${got}" ]; then echo "ok   $1 -> ${got}"; else echo "FAIL $1 -> rc=${rc} ${got}, want NOK"; fails=$((fails+1)); fi ;;
    esac
}
val() { if [ "$2" = "$3" ]; then echo "ok   $1 = [$2]"; else echo "FAIL $1 = [$2], want [$3]"; fails=$((fails+1)); fi; }

REAL="
Time: 09/11/26 15:07:06.116 - NOTIFICATION *** file src/transaction/log_recovery.c, line 833  CODE = -1128, Tran = 0, CLIENT = :(0), EID = 1
Log recovery is started.

Time: 09/11/26 15:07:06.116 - NOTIFICATION *** file src/transaction/log_recovery.c, line 837  CODE = -1296, Tran = 0, CLIENT = :(0), EID = 2
Log recovery: ANALYSIS Phase is started.

Time: 09/11/26 15:07:06.116 - NOTIFICATION *** file src/transaction/log_recovery.c, line 842  CODE = -1300, Tran = 0, CLIENT = :(0), EID = 3
Log recovery: ANALYSIS Phase is finished.

Time: 09/11/26 15:07:06.116 - NOTIFICATION *** file src/transaction/log_recovery.c, line 878  CODE = -1297, Tran = 0, CLIENT = :(0), EID = 4
Log recovery: REDO Phase is started. Log pages to redo: 2, Log records to redo: 83.

Time: 09/11/26 15:07:06.145 - NOTIFICATION *** file src/transaction/log_recovery.c, line 4069  CODE = -1299, Tran = 0, CLIENT = :(0), EID = 5
Log recovery: REDO Phase is being finished up.

Time: 09/11/26 15:07:06.150 - NOTIFICATION *** file src/transaction/log_recovery.c, line 883  CODE = -1300, Tran = 0, CLIENT = :(0), EID = 6
Log recovery: REDO Phase is finished.

Time: 09/11/26 15:07:06.150 - NOTIFICATION *** file src/transaction/log_recovery.c, line 4675  CODE = -1298, Tran = 0, CLIENT = :(0), EID = 7
Log recovery: UNDO Phase is started. Log pages to undo: 0, transactions to undo: 0.

Time: 09/11/26 15:07:06.166 - NOTIFICATION *** file src/transaction/log_recovery.c, line 974  CODE = -1129, Tran = 0, CLIENT = :(0), EID = 12
Log recovery is finished.
"
ANALYSIS_ONLY="
Log recovery is started.
Log recovery: ANALYSIS Phase is started.
Log recovery: ANALYSIS Phase is finished.
Log recovery is finished.
"
ZERO="
Log recovery is started.
Log recovery: REDO Phase is started. Log pages to redo: 0, Log records to redo: 0.
Log recovery: UNDO Phase is started. Log pages to undo: 0, transactions to undo: 0.
Log recovery is finished.
"
TWO="
Log recovery: REDO Phase is started. Log pages to redo: 1, Log records to redo: 7.
Log recovery: UNDO Phase is started. Log pages to undo: 0, transactions to undo: 0.
Server status is UP.
Log recovery: REDO Phase is started. Log pages to redo: 2, Log records to redo: 83.
Log recovery: UNDO Phase is started. Log pages to undo: 0, transactions to undo: 0.
"
MALFORMED="
Log recovery: REDO Phase is started. Log pages to redo: two, Log records to redo: many.
"
BANNER="
This may take a long time depending on the amount of recovery works to do.
"

chk "1 the real recovery sequence, before=0" 0 "$REAL" OK "OK|pages=2|records=83"
chk "2 analysis lines only, no REDO phase"   0 "$ANALYSIS_ONLY" NOK
chk "3 an empty log"                          0 "" NOK
chk "4 a REDO phase with nothing to redo"     0 "$ZERO" NOK
chk "5 two REDO phases, none before"          0 "$TWO" NOK
chk "6 two REDO phases, one before"           1 "$TWO" OK "OK|pages=2|records=83"
chk "7 a REDO line whose counts do not parse" 0 "$MALFORMED" NOK
chk "8 the utility's unconditional banner"    0 "$BANNER" NOK
val "9 undo counts from the real sequence"    "$(recovery_undo_counts "$REAL")" "0 0"
val "9 undo counts when absent"               "$(recovery_undo_counts "$BANNER")" ""
chk "10 before is not a number"               "" "$REAL" OK "OK|pages=2|records=83"
val "redo counts from the real sequence"      "$(recovery_redo_counts "$REAL")" "2 83"
val "redo counts take the LAST line"          "$(recovery_redo_counts "$TWO")" "2 83"

echo "failures=$fails"; [ $fails -eq 0 ]
