drop table if exists t1;
create table t1 (id int primary key, v varchar(10));
insert into t1 values (1,'a'),(2,'b'),(3,'c');
alter table t1 add column c varchar(5000) default repeat('x', 4200);
create index i_c_id on t1 (c, id);
select id, length(c) from t1 using index i_c_id where c > '' order by id;
update t1 set v = 'z' where id = 1;
delete from t1 where id = 2;
select count(*) from t1;
