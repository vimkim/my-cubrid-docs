insert into t1 values (2, repeat('a',9000), repeat('b',9000), repeat('c',9000));
select id, length(a) from t1 order by id;
commit;
