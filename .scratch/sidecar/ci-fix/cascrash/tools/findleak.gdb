set breakpoint pending on
break connection_list_cl::css_queue_user_data_buffer if request_id == 6840
commands
  silent
  printf "QUEUE rid=%u size=%d buffer=%p conn->request_id=%u\n", request_id, size, buffer, conn->request_id
  bt 30
  continue
end
break connection_list_cl::css_get_data_buffer if request_id == 6840
commands
  silent
  printf "TAKE rid=%u\n", request_id
  bt 12
  continue
end
