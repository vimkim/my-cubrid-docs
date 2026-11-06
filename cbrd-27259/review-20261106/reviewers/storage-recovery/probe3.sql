show create table t1;
show create table t4;
select class_name, attr_name, storage from _db_attribute where class_name in ('t1');
