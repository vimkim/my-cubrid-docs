-- P1: CREATE semantics, identifiers, errors
create table t1 (a varchar(100) storage force_inline, b int storage default, c int storage force_inline, d varchar storage prefer_inline, e varchar storage force_outline, f varchar storage default, g varchar storage prefer_outline, h char(10) storage force_inline, i bit(80) storage force_inline);
show create table t1;
create table force_inline (force_inline int, force_inline2 varchar storage force_inline);
show create table force_inline;
select force_inline from force_inline;
create table e1 (a int storage force_outline);
create table e2 (a int storage prefer_outline);
create table e3 (a int storage prefer_inline);
create table e4 (a varchar, class attribute ca varchar storage force_inline);
create table e5 (a varchar, b varchar shared 'x' storage force_inline);
create table e6 (a varchar, b varchar shared 'x' storage default);
create table e7 (a varchar, class attribute ca int storage default);
create view v1 (a varchar storage force_inline) as select 'x';
create view v2 (a int storage default) as select 1;
show create table e4;
show create table e5;
show create table e6;
show create table e7;
