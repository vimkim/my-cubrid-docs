set pagination off
set breakpoint pending on
break heap_oos_warn_bigone_without_oos
commands
silent
printf "WARN size=%d max=%d\n", record_size, max_size
continue
end
break er_set if err_id == -1388
commands
silent
printf "ER1388\n"
continue
end
run
info breakpoints
