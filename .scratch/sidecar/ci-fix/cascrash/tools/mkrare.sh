#!/usr/bin/env bash
# mkrare.sh WORKTREE OUT: gdb breakpoints on the rare client paths of the ping-timeout chain (no per-request stops).
WT=${1:?}; OUT=${2:?}
L=$(awk '/^net_client_ping_server \(/{f=1} f && /error = ER_NET_SERVER_DATA_RECEIVE;/{print NR; exit}' "$WT/src/communication/network_cl.c")
cat > "$OUT" <<G
set breakpoint pending on
break network_cl.c:$L
commands
  silent
  printf "PING_TIMEOUT eid=%d rid=%u\n", eid, eid & 0xffff
  bt 8
  continue
end
break connection_list_cl::css_queue_unexpected_data_packet
commands
  silent
  printf "UNEXPECTED_DATA rid=%u buffer=%p size=%d rc=%d\n", request_id, buffer, size, rc
  bt 10
  continue
end
break connection_cl::css_remove_all_unexpected_packets
commands
  silent
  printf "REMOVE_ALL_UNEXPECTED\n"
  bt 8
  continue
end
break connection_list_cl::css_process_abort_packet
commands
  silent
  printf "ABORT_PACKET rid=%u\n", request_id
  continue
end
G
echo "$OUT (ping timeout line $L)"
