#!/bin/bash
# CBRD-26659 campaign ticket 14 -- checker validation for the third checking mechanism.
#
# The whole-value oracle has its control in cases/make_negative_control.sh and the
# acknowledgement parser has checker_validation_journal.sh. This is the control for the
# SHOW HEAP OOS output classifier, which decides whether an activation check asserts,
# skips as a capability gap, or fails.
#
# It exists because the first version of that classifier had two outcomes and a catch-all,
# so any non-syntax failure -- a disconnect, an authorization error, a renamed column --
# was reported as "this build does not answer SHOW HEAP OOS": a real failure recorded as a
# capability gap, which passes the case. The second version matched the bare class name,
# which ALSO matches `ERROR: Unknown class "dba.oos_dur01".`, so an error was read as an
# answer and fields were extracted from the error text. This test caught that before it
# shipped. The shipped version requires the quoted class name and the full column count.
#
# The function bodies below are extracted verbatim from the case, so the test cannot drift
# away from what it validates.
# Exit status 0 only when every case classifies correctly.
oos_data_row()
{
    echo "$1" | awk "/'dba.oos_dur01'/ && NF >= 14 { print; exit }"
}
classify_oos_output()
{
    echo "$1" | grep -qi "syntax error" && return 1
    [ -n "`oos_data_row "$1"`" ] && return 0
    return 2
}
oos_field()
{
    # oos_field <show output> <awk field number>. oos_data_row returns at most one line, so
    # the result is a single value: a multi-line value would turn the numeric comparisons
    # below into a shell error instead of a failed assertion.
    oos_data_row "$1" | awk -v f=$2 '{print $f}'
}

fails=0
chk() { classify_oos_output "$2"; got=$?; if [ "$got" = "$3" ]; then echo "ok   $1 -> $got"; else echo "FAIL $1 -> $got, want $3"; fails=$((fails+1)); fi; }
ROW="
  Table_name            Class_oid             Heap_volume_id  Heap_file_id  Heap_header_page_id  Has_oos_file  Oos_volume_id  Oos_file_id  Oos_num_user_pages  Oos_page_size  Oos_num_recs       Oos_recs_sumlen    Oos_physical_bytes      Oos_unused_bytes
============
  'dba.oos_dur01'       '(0|209|2)'                        1           576                  577             1              1          640                   4          16344             4                 24444                 65376                 40932

1 row selected. (0.000000 sec) Committed."
chk "a real answer row" "$ROW" 0
chk "a parser lacking the statement" "
In line 1, column 6,
ERROR: syntax error, unexpected HEAP
" 1
chk "a connection failure" "
ERROR: Failed to connect to database server, 't26659dur01', on the following host(s): localhost
" 2
chk "an authorization error" "
ERROR: Semantic: SHOW HEAP OOS requires DBA authorization.
" 2
chk "unknown class naming this very class" '
In line 1, column 33,
ERROR: Unknown class "dba.oos_dur01".
' 2
chk "a truncated row (fewer columns)" "
  'dba.oos_dur01'  '(0|209|2)'  1  576
" 2
chk "empty output" "" 2
echo
echo "field extraction from the real row: has_oos=$(oos_field "$ROW" 6) chunks=$(oos_field "$ROW" 11) sumlen=$(oos_field "$ROW" 12)"
echo "field extraction from an error:     [$(oos_field '
ERROR: Unknown class "dba.oos_dur01".
' 6)]"
echo "failures=$fails"; [ $fails -eq 0 ]
