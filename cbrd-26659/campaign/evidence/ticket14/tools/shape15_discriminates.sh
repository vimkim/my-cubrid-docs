#!/bin/bash
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

HDR="  Table_name            Class_oid             Heap_volume_id  Heap_file_id  Heap_header_page_id  Has_oos_file  Oos_volume_id  Oos_file_id  Oos_num_user_pages  Oos_page_size  Oos_num_recs       Oos_recs_sumlen    Oos_physical_bytes      Oos_unused_bytes
============"
TWOHDR="
$HDR
  'dba.nothing_here'    '(0|1|1)'                          1             1                    1             0           NULL         NULL                   0          16344             0                     0                     0                     0

  Table_name            Class_oid             Has_oos_file  Oos_num_recs  Heap_volume_id  Heap_file_id  Heap_header_page_id  Oos_volume_id  Oos_file_id  Oos_num_user_pages  Oos_page_size  Oos_recs_sumlen    Oos_physical_bytes      Oos_unused_bytes
============
  'dba.oos_dur01'       '(0|209|2)'                      1             4               1           576                  577              1          640                   4          16344             24444                 65376                 40932
"
echo "REVISION 6 (split functions), shape 15:"
echo "  index from the FIRST header : Oos_num_recs -> $(oos_column_index "$TWOHDR" Oos_num_recs)"
echo "  oos_field Oos_num_recs      : $(oos_field "$TWOHDR" Oos_num_recs)   <- wrong, that is Oos_page_size's slot"
echo "  correct value               : 4"
