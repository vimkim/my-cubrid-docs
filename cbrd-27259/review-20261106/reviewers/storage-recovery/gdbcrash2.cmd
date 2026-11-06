set pagination off
set breakpoint pending on
break locator_attribute_info_force
run
finish
printf "AFTER force\n"
kill
