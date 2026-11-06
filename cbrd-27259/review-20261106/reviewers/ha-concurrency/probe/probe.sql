create table t1 (id int storage default, a varchar(20000) storage force_inline, b varchar(20000) storage force_inline, c varchar(20000) storage force_inline);
create table t2 (id int, a varchar(20000), b varchar(20000), c varchar(20000));
;schema t1
insert into t1 values (1, repeat('a',7000), repeat('b',7000), repeat('c',7000));
select id, length(a)+length(b)+length(c) from t1;
insert into t2 values (1, repeat('a',7000), repeat('b',7000), repeat('c',7000));
select id, length(a)+length(b)+length(c) from t2;
commit;
