set pagination off
set breakpoint pending on
break heap_attrinfo_determine_disk_layout
run
printf "v0 st=%d fixed=%d id=%d\n", attr_info->values[0].last_attrepr->oos_storage, attr_info->values[0].last_attrepr->is_fixed, attr_info->values[0].last_attrepr->id
printf "v1 st=%d fixed=%d id=%d\n", attr_info->values[1].last_attrepr->oos_storage, attr_info->values[1].last_attrepr->is_fixed, attr_info->values[1].last_attrepr->id
printf "v2 st=%d fixed=%d id=%d\n", attr_info->values[2].last_attrepr->oos_storage, attr_info->values[2].last_attrepr->is_fixed, attr_info->values[2].last_attrepr->id
p pr_data_writeval_disk_size(&attr_info->values[0].dbvalue)
p pr_data_writeval_disk_size(&attr_info->values[1].dbvalue)
p pr_data_writeval_disk_size(&attr_info->values[2].dbvalue)
p attr_info->values[1].dbvalue.data.ch.medium.size
p attr_info->values[2].dbvalue.data.ch.medium.size
p attr_info->values[1].last_attrepr->domain->type->id
