-- CBRD-27057 desired physical target repro, excluded from Ticket03 passing manifest.
-- Source fb567a629,16KiB I/O/log pages,MVCC-enabled CS connection.
-- One fixed INT:4B + fixed boundbits4B + MVCC insert header16B + VOT4B.
-- Reserve16B for future MVCC delete/previous-version fields.
-- Gate estimate =44 + serialized VARBIT length. Accepted target4060B.
-- VARBIT N4011 -> ALIGN_UP(N+5,4)=4016 -> estimate4060: stays inline.
-- VARBIT N4012 -> serialized4020 -> estimate4064: desired demotion.
-- Expected SHOW gate_at: Has_oos_file0, Oos_num_recs0, Oos_recs_sumlen0.
-- Expected SHOW gate_above: Has_oos_file1, Oos_num_recs1, Oos_recs_sumlen4044.
-- Current raw DB_PAGESIZE/4=4086 fails the gate_above expected physical state.
-- Do not change the desired result to zero and do not fix the engine in this ticket.
create table gate_at (id int primary key, payload bit varying);
create table gate_above (id int primary key, payload bit varying);
insert into gate_at values (1,cast(repeat('a1',4011) as bit varying));
insert into gate_above values (2,cast(repeat('b2',4012) as bit varying));
commit;
show heap oos of gate_at;
show heap oos of gate_above;
-- An attempt owns database/server/files and deletes its fixture after observation.
