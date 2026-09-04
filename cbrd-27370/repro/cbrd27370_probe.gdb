set pagination off
set confirm off
set breakpoint pending on
break probe_point
commands
  silent
  set $iop = (pgbuf_iopage_buffer *) ((char *) page - (long) &((pgbuf_iopage_buffer *) 0)->iopage.page)
  set $holder = pgbuf_find_thrd_holder (thread_p, $iop->bcb)
  if $holder == 0
    printf "GDB %s: holder=NULL\n", label
  else
    printf "GDB %s: holder_fix_count=%d\n", label, $holder->fix_count
  end
  continue
end
run
bt 8
quit
