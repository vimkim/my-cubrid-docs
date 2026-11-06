set pagination off
set breakpoint pending on
break heap_attrinfo_determine_disk_layout
commands
silent
printf "LAYOUT nvalues=%d class=%d|%d|%d\n", attr_info->num_values, attr_info->class_oid.volid, attr_info->class_oid.pageid, attr_info->class_oid.slotid
bt 4
continue
end
run
