create table rp2 (id int, c varchar storage force_inline, d varchar(10)) partition by range (id) (partition p0 values less than (10));
alter table rp2 add partition (partition p1 values less than (20));
alter table rp2 modify c varchar(500);
alter table rp2 modify d varchar(20) storage force_inline;
alter table rp2 reorganize partition p1 into (partition p1a values less than (15), partition p1b values less than (20));
