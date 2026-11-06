set pagination off
set breakpoint pending on
break heap_file.c:14271
commands
silent
printf "GUARD has_oos=%d inline_after=%d max=%d offs=%d\n", has_oos, inline_size_after_oos, heap_Maxslotted_reclength, offset_size
continue
end
run
