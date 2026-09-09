# Ticket03 only: shrink one INCR and one DECR first-pass buffer after layout/OOS preparation.
# Locations are pinned to the source diff captured by the isolated runner, not a production test hook.
set pagination off
set confirm off
set breakpoint pending on
set $injected = 0
set $injected_pos = 0
set $injected_neg = 0
set $retried = 0
break heap_file.c:13557
commands
  silent
  set $idx = 0
  while $idx < attr_info->num_values
    if ((attr_info->values[$idx].do_increment == 1 && $injected_pos == 0) || (attr_info->values[$idx].do_increment == -1 && $injected_neg == 0)) && increments_already_applied == false && old_recdes != 0
      set $injected = $injected + 1
      if attr_info->values[$idx].do_increment == 1
        set $injected_pos = 1
      else
        set $injected_neg = 1
      end
      set $saved_cache = attr_info
      set $pending_index = $idx
      # Enough for the UPDATE header; too little for its complete columns.
      set inline_size_after_oos = header_size
      printf "TICKET03_RETRY injected: increment=%d header=%lu\n", attr_info->values[$idx].do_increment, header_size
    end
    set $idx = $idx + 1
  end
  continue
end
break heap_file.c:13578
commands
  silent
  if $injected > 0 && attr_info == $saved_cache
    set $retried = $retried + 1
    printf "TICKET03_RETRY columns retry: value=%d pending=%d\n", attr_info->values[$pending_index].dbvalue.data.i, attr_info->values[$pending_index].do_increment
    if attr_info->values[$pending_index].dbvalue.data.i != 10 + attr_info->values[$pending_index].do_increment
      echo TICKET03_RETRY did not fail after the first real mutation\n
      quit 1
    end
  end
  continue
end
run
if $injected != 2 || $retried != 2
  echo TICKET03_RETRY missing expected injection/retry\n
  quit 1
end
if $_exitcode != 0
  quit 1
end
echo TICKET03_RETRY PASS: INCR and DECR each retried after mutation; final behavioral assertions passed\n
quit 0
