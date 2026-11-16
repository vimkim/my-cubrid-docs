set breakpoint pending on
set confirm off
break client_support::css_receive_data_from_server_with_timeout if (eid & 0xffff) == 6840 && timeout > 0
commands
  silent
  printf "FORCE_TIMEOUT rid=%u: return ERROR_WHEN_READING_SIZE (7) without reading, as a poll timeout does\n", eid & 0xffff
  return (int) 7
  continue
end
break connection_list_cl::css_get_data_buffer if request_id == 6840
commands
  silent
  set $bq = conn->buffer_queue
  if $bq != 0
    printf "GET_DATA_BUFFER rid=%u head=%p key=%u size=%d next=%p\n", request_id, $bq->buffer, $bq->key, $bq->size, $bq->next
  else
    printf "GET_DATA_BUFFER rid=%u buffer_queue empty\n", request_id
  end
  bt 10
  continue
end
break connection_list_cl::css_queue_unexpected_data_packet if request_id == 6840
commands
  silent
  printf "UNEXPECTED_DATA rid=%u buffer=%p size=%d\n", request_id, buffer, size
  continue
end
