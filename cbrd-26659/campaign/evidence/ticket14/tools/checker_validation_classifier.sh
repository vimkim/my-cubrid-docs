#!/bin/bash
# CBRD-26659 campaign ticket 14 -- checker validation for the third checking mechanism:
# the SHOW HEAP OOS output classifier and the field extraction that follows it.
#
# Why it has sixteen shapes. The classifier has been wrong three times, and each time the
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
#
# Shapes 13 to 16 pin interactions rather than defects. 13 is the only construction in
# which a column located by name could point past the row. 14 locks the name comparison to
# exact field equality, because a substring match would reintroduce by-name the
# wrong-column bug that was removed by-position. 15 is the header divergence: the position
# and the value must come from the SAME header, which is why the row selector and the index
# lookup were collapsed into one awk pass. 16 is the visible marker an observation gets
# when its column is outside oos_required_columns and the header does not carry it, since
# nothing inspects oos_field's status inside a command substitution.
oos_field()
{
    # oos_field <show output> <column name> -> the value, or nothing and status 1
    local v
    v=`echo "$1" | awk -v cls="'dba.oos_dur01'" -v want="$2" '
        /Table_name/ && /Has_oos_file/ {
            idx = 0
            for (i = 1; i <= NF; i++) { if ($i == want) { idx = i; break } }
            cols = NF
            next
        }
        cols && index($0, cls) && NF >= cols { if (idx) { print $idx }; exit }'`
    [ -n "${v}" ] || return 1
    echo "${v}"
}
oos_observed()
{
    oos_field "$1" "$2" || echo "UNRESOLVED($2)"
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
    # Deliberate word-split on a space-separated list of literal column names: none
    # contains a space or a glob character, and no IFS is set anywhere in this case or in
    # the CTP helpers it sources.
    for col in ${oos_required_columns}; do
        oos_field "$1" "${col}" > /dev/null || return 2
    done
    return 0
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

# 13: the header is wider than the data row, which is the only construction in which a
# column located by name could point past the row's last field. oos_data_row requires
# NF >= cols so the row is not selected at all and the classification is 2 -- it fails
# closed. Pinned rather than reasoned about, because this is the one place where "located
# by name" and "wide enough" have to agree: an index comes from the header (so idx <= cols)
# and a row is only selected when NF >= cols, therefore idx <= NF always, but that is an
# argument and this is a test.
chk "13 header wider than the row" "
$HDR
  'dba.oos_dur01'       '(0|209|2)'                        1           576                  577             1              1          640                   4          16344             4
" 2

# 14: column names must be compared by EXACT field equality, never by substring. This
# header carries both Heap_volume_id and Oos_volume_id, and Oos_num_recs shares fragments
# with Oos_recs_sumlen and Oos_num_user_pages. A substring or regex match on the name side
# would reintroduce by-name exactly the wrong-column bug that was just removed by-position,
# and every value below would come from the wrong field. Suggested by the Standards
# confirmation pass as a guess about code it had not read; the code was already exact, so
# this shape exists to keep it that way.
val "14 Oos_volume_id is not Heap_volume_id" "$(oos_field "$ROW" Oos_volume_id)" 1
val "14 Heap_volume_id is its own column"    "$(oos_field "$ROW" Heap_volume_id)" 1
val "14 Oos_num_recs is not Oos_recs_sumlen" "$(oos_field "$ROW" Oos_num_recs)" 4
val "14 Oos_recs_sumlen is its own column"   "$(oos_field "$ROW" Oos_recs_sumlen)" 24444
val "14 Oos_num_user_pages is its own column" "$(oos_field "$ROW" Oos_num_user_pages)" 4
val "14 a name that is only a fragment resolves to nothing" "$(oos_field "$ROW" volume_id)" ""
val "14 a name that is only a prefix resolves to nothing"    "$(oos_field "$ROW" Oos_num)" ""

# 15: two headers, the row belonging to the SECOND. The second header moves Oos_num_recs
# from position 11 to position 4. When the row selector and the index lookup were separate
# functions, the lookup exited on the first header and the row took its width from the
# nearest one above it, so this read position 11 of a row laid out in the second header's
# order. One awk pass makes the position and the value come from the same header.
TWOHDR="
$HDR
  'dba.nothing_here'    '(0|1|1)'                          1             1                    1             0           NULL         NULL                   0          16344             0                     0                     0                     0

  Table_name            Class_oid             Has_oos_file  Oos_num_recs  Heap_volume_id  Heap_file_id  Heap_header_page_id  Oos_volume_id  Oos_file_id  Oos_num_user_pages  Oos_page_size  Oos_recs_sumlen    Oos_physical_bytes      Oos_unused_bytes
============
  'dba.oos_dur01'       '(0|209|2)'                      1             4               1           576                  577              1          640                   4          16344             24444                 65376                 40932
"
chk "15 two headers, row under the second" "$TWOHDR" 0
val "15 chunks from the second header"  "$(oos_field "$TWOHDR" Oos_num_recs)" 4
val "15 has_oos from the second header" "$(oos_field "$TWOHDR" Has_oos_file)" 1

# 16: an observation whose column the header does not carry. oos_field signals it with
# status 1 and empty output, which no command substitution inspects, so oos_observed turns
# it into a marker the journal will show instead of an empty value.
val "16 a missing observation column is marked" "$(oos_observed "$ROW" Oos_no_such_column)" "UNRESOLVED(Oos_no_such_column)"
val "16 a present observation column is not"    "$(oos_observed "$ROW" Oos_recs_sumlen)" 24444

echo
val "field extraction from the real row (has_oos)" "$(oos_field "$ROW" Has_oos_file)" 1
val "field extraction from the real row (chunks)"  "$(oos_field "$ROW" Oos_num_recs)" 4
val "field extraction from the real row (sumlen)"  "$(oos_field "$ROW" Oos_recs_sumlen)" 24444
val "field extraction from an error"               "$(oos_field '
ERROR: Unknown class "dba.oos_dur01".
' Has_oos_file)" ""
echo "failures=$fails"; [ $fails -eq 0 ]
