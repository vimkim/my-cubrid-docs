set pagination off
set breakpoint pending on
break heap_attrinfo_determine_disk_layout
break heap_oos_warn_bigone_without_oos
run
bt 12
continue
bt 12
continue
