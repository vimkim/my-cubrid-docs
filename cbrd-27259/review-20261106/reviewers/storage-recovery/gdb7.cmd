set pagination off
set breakpoint pending on
break heap_attrinfo_get_record_payload_size
run
finish
p attr_info->num_values
p attr_info->values[1].last_attrepr->oos_storage
p attr_info->values[1].last_attrepr->is_fixed
p attr_info->values[1].dbvalue.domain.general_info.type
