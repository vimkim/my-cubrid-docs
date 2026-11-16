set confirm off
set breakpoint pending on
break client_support::css_receive_data_from_server_with_timeout
disable 1
commands 1
  silent
  printf "FORCE_TIMEOUT rid=%u: return ERROR_WHEN_READING_SIZE (7) without reading, as a poll timeout does\n", eid & 0xffff
  return (int) 7
  continue
end
break net_client_ping_server
ignore 2 42
commands 2
  silent
  printf "PING_43 reached\n"
  enable once 1
  disable 2
  continue
end
