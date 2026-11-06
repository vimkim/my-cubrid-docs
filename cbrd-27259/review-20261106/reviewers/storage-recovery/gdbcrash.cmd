set pagination off
set breakpoint pending on
break heap_oos_warn_bigone_without_oos
run
printf "HIT warn\n"
kill
