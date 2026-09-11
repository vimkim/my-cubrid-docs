#!/bin/bash
# CBRD-26659 campaign ticket 14 -- checker validation for the third checking mechanism:
# the SHOW HEAP OOS output classifier and the field extraction that follows it.
#
# Why it has twelve shapes. The classifier has been wrong three times, and each time the
# defect passed every green run:
#   1. two outcomes and a catch-all, so any non-syntax failure was reported as a missing
#      capability -- a SKIP, which passes the case with no activation evidence.
#   2. matching the bare class name, which also matches `ERROR: Unknown class
#      "dba.oos_dur01".`, so an error was read as an answer and fields came out of the
#      error text. Shape 5 caught this before it shipped.
#   3. hardcoded column positions: a row wide enough is not a row whose field 11 is still
#      Oos_num_recs. Shape 9 is the reordering that used to yield chunks=16344 silently.
#      Found by the Standards confirmation pass.
# A fourth was caught by shape 1 while fixing the third: a shell-quoting error made the
# class-name match look for `'"dba.oos_dur01"'` and no real row matched at all.
#
# Shape 8, a class with no OOS file, is the one shape no run of this case has produced.
# It is constructed from the engine source rather than observed: heap_oos.cpp makes only
# Oos_volume_id and Oos_file_id null when has_oos_file is 0, and csql renders a NULL as
# the literal token NULL (csql_result.c, csql_result_format.c), so the row keeps its full
# width. That is the shape where a wrong field count would have turned a real finding
# into a capability gap.
#
# The function bodies below are extracted verbatim from the case, so the test cannot
# drift away from what it validates. Exit status 0 only when every shape is correct.
oos_data_row()
{
    echo "$1" | awk -v cls="'dba.oos_dur01'" '
        /Table_name/ && /Has_oos_file/ { cols = NF; next }
        cols && index($0, cls) && NF >= cols { print; exit }'
}
oos_column_index()
{
    # oos_column_index <show output> <column name>
    echo "$1" | awk -v want="$2" '
        /Table_name/ && /Has_oos_file/ {
            for (i = 1; i <= NF; i++) { if ($i == want) { print i; exit } }
            exit
        }'
}
oos_required_columns="Has_oos_file Oos_num_recs Oos_recs_sumlen Oos_num_user_pages Oos_page_size"
classify_oos_output()
{
    local col
    # Order does not matter here because the two tests are mutually exclusive: a single
    # csql -c statement either parses or it does not, and no successful output can contain
    # "syntax error" when the only string columns are a class name and an OID. If they
    # ever did overlap, 2 would be the conservative answer, not 1: a 1 is a SKIP, which
    # carries no NOK, passes the case and leaves activation_observed at 0 -- the exact
    # failure mode this classification exists to remove.
    echo "$1" | grep -qi "syntax error" && return 1
    [ -n "`oos_data_row "$1"`" ] || return 2
    for col in ${oos_required_columns}; do
        [ -n "`oos_column_index "$1" "${col}"`" ] || return 2
    done
    return 0
}
oos_field()
{
    # oos_field <show output> <column name>. oos_data_row returns at most one line -- awk's
    # exit with no END block stops after the first match -- so the result is a single
    # value: a multi-line value would turn the numeric comparisons below into a shell error
    # instead of a failed assertion.
    local idx
    idx=`oos_column_index "$1" "$2"`
    [ -n "${idx}" ] || return 1
    oos_data_row "$1" | awk -v f="${idx}" '{print $f}'
}

fails=0
chk() { classify_oos_output "$2"; got=$?; if [ "$got" = "$3" ]; then echo "ok   $1 -> $got"; else echo "FAIL $1 -> $got, want $3"; fails=$((fails+1)); fi; }
val() { if [ "$2" = "$3" ]; then echo "ok   $1 = $2"; else echo "FAIL $1 = $2, want $3"; fails=$((fails+1)); fi; }

HDR="  Table_name            Class_oid             Heap_volume_id  Heap_file_id  Heap_header_page_id  Has_oos_file  Oos_volume_id  Oos_file_id  Oos_num_user_pages  Oos_page_size  Oos_num_recs       Oos_recs_sumlen    Oos_physical_bytes      Oos_unused_bytes
============"
ROW="
$HDR
  'dba.oos_dur01'       '(0|209|2)'                        1           576                  577             1              1          640                   4          16344             4                 24444                 65376                 40932

1 row selected. (0.000000 sec) Committed."

chk "1 a real answer row" "$ROW" 0
chk "2 a parser lacking the statement" "
In line 1, column 6,
ERROR: syntax error, unexpected HEAP
" 1
chk "3 a connection failure" "
ERROR: Failed to connect to database server, 't26659dur01', on the following host(s): localhost
" 2
chk "4 an authorization error" "
ERROR: Semantic: SHOW HEAP OOS requires DBA authorization.
" 2
chk "5 unknown class naming this very class" '
In line 1, column 33,
ERROR: Unknown class "dba.oos_dur01".
' 2
chk "6 a truncated row" "
$HDR
  'dba.oos_dur01'  '(0|209|2)'  1  576
" 2
chk "7 empty output" "" 2

# 8: a class with no OOS file. Only Oos_volume_id and Oos_file_id are db_make_null
# (heap_oos.cpp), and csql renders a NULL as the literal token NULL (csql_result.c,
# csql_result_format.c), so the row is still full width. This is the shape no run of this
# case has produced, and the one where a wrong field count would have turned a real
# finding into a capability gap.
NOOOS="
$HDR
  'dba.oos_dur01'       '(0|209|2)'                        1           576                  577             0           NULL         NULL                   0          16344             0                     0                     0                     0

1 row selected."
chk "8 a class with no OOS file" "$NOOOS" 0
val "8 has_oos on that row" "$(oos_field "$NOOOS" Has_oos_file)" 0
val "8 chunks on that row"  "$(oos_field "$NOOOS" Oos_num_recs)" 0

# 9: the columns reordered. Position 11 is no longer Oos_num_recs. Reading by name must
# still return the right values; reading by position would have returned 16344 chunks.
REORD="
  Table_name            Class_oid             Has_oos_file  Oos_num_recs  Heap_volume_id  Heap_file_id  Heap_header_page_id  Oos_volume_id  Oos_file_id  Oos_num_user_pages  Oos_page_size  Oos_recs_sumlen    Oos_physical_bytes      Oos_unused_bytes
============
  'dba.oos_dur01'       '(0|209|2)'                      1             4               1           576                  577              1          640                   4          16344             24444                 65376                 40932
"
chk "9 the columns reordered" "$REORD" 0
val "9 has_oos read by name" "$(oos_field "$REORD" Has_oos_file)" 1
val "9 chunks read by name"  "$(oos_field "$REORD" Oos_num_recs)" 4

# 10: a renamed column. Not a capability gap -- the output is not the shape this case knows
# how to read, so it must fail rather than skip.
RENAMED="
  Table_name            Class_oid             Heap_volume_id  Heap_file_id  Heap_header_page_id  Has_oos_file  Oos_volume_id  Oos_file_id  Oos_num_user_pages  Oos_page_size  Oos_chunk_count    Oos_recs_sumlen    Oos_physical_bytes      Oos_unused_bytes
============
  'dba.oos_dur01'       '(0|209|2)'                        1           576                  577             1              1          640                   4          16344             4                 24444                 65376                 40932
"
chk "10 Oos_num_recs renamed" "$RENAMED" 2

# 11: a row with no header before it cannot be a row.
chk "11 a row with no header" "
  'dba.oos_dur01'       '(0|209|2)'                        1           576                  577             1              1          640                   4          16344             4                 24444                 65376                 40932
" 2

# 12: a near-miss class name. index() is literal, so the dots are not a regex.
chk "12 a near-miss class name" "
$HDR
  'dbaXoos_dur01'       '(0|209|2)'                        1           576                  577             1              1          640                   4          16344             4                 24444                 65376                 40932
" 2

echo
val "field extraction from the real row (has_oos)" "$(oos_field "$ROW" Has_oos_file)" 1
val "field extraction from the real row (chunks)"  "$(oos_field "$ROW" Oos_num_recs)" 4
val "field extraction from the real row (sumlen)"  "$(oos_field "$ROW" Oos_recs_sumlen)" 24444
val "field extraction from an error"               "$(oos_field '
ERROR: Unknown class "dba.oos_dur01".
' Has_oos_file)" ""
echo "failures=$fails"; [ $fails -eq 0 ]
