info registers rip rsp rbp
set $c = *(struct css_conn_entry **)($rbp-0x50)
printf "conn=%p request_id=%u status=%d\n", $c, $c->request_id, $c->status
printf "css_receive_data locals: req_id=%u rid=%u type=%d buf=%p buf_size=%d\n", *(unsigned short *)($rbp-0x54), *(unsigned int *)($rbp-0xc), *(int *)($rbp-0x10), *(char **)($rbp-0x8), *(int *)($rbp-0x3c)
set $q = $c->buffer_queue
set $n = 0
while ($q != 0 && $n < 64)
  printf "buffer_queue[%d] key=%u buffer=%p size=%d\n", $n, $q->key, $q->buffer, $q->size
  set $q = $q->next
  set $n = $n + 1
end
printf "buffer_queue entries=%d\n", $n
set $q = $c->data_queue
set $n = 0
while ($q != 0 && $n < 64)
  printf "data_queue[%d] key=%u size=%d rc=%d\n", $n, $q->key, $q->size, $q->rc
  set $q = $q->next
  set $n = $n + 1
end
x/40ga $sp
