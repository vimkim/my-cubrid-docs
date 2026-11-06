select id, length(a), length(b) from t3 where id in (204,205) order by 1;
alter table t3 modify a varchar(30000) storage force_inline;
show create table t3;
select id, length(a), length(b) from t3 where id in (204,205) order by 1;
update t3 set id=904 where id=204;
update t3 set id=905 where id=205;
select id, length(a), length(b) from t3 where id>=900 or id in (204,205) order by 1;
update t3 set a='kASAOsE1nYEZ9GlGHpYaax7LBejYWo6oScBVX4ANCc9vIFShP88xbjV0fhZ7bDkJUvzFjlQcE30peXmnRZ5QW8W5LUehJEJ0ymv7' where id=205;
select id, length(a), length(b) from t3 order by 1;
