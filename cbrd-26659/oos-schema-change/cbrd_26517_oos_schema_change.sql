-- OOS 스키마 변경 회귀 테스트
-- 목적: OOS 대상 레코드가 있는 테이블에서 컬럼 위치 변경, 추가/삭제, 타입 변경 후에도
--       OOS 컬럼 값이 정확히 읽히고 기존 레코드가 깨지지 않는지 확인한다.
-- 참고: BIT VARYING 은 문자열 압축 영향을 받지 않으므로 OOS 크기 테스트에 적합하다.
--       CAST(REPEAT('AA', 5000) AS BIT VARYING) 은 5000 byte payload 를 만든다.
--       DISK_SIZE 결과에는 VARBIT 저장 overhead 가 포함되어 5008 로 보인다.

drop table if exists oos_schema_change_test;

create table oos_schema_change_test (
  id int primary key,
  oos_data_a bit varying,
  oos_data_b bit varying,
  note varchar(20),
  keep_col int
);

-- 5000 byte + 4600 byte payload 로 record > DB_PAGESIZE/4 조건을 넘겨 OOS demotion 을 유도한다.
-- a/b 는 hot/cold 의미가 아니라, 서로 다른 OOS 값을 구분하기 위한 이름이다.
insert into oos_schema_change_test values (
  1,
  cast(repeat('AA', 5000) as bit varying),
  cast(repeat('BB', 4600) as bit varying),
  'base',
  10
);

evaluate '0. 초기 OOS 대상 레코드 확인';
select
  'initial' as step,
  count(*) as row_count,
  min(disk_size(oos_data_a)) as oos_a_bytes,
  min(disk_size(oos_data_b)) as oos_b_bytes,
  min(case when oos_data_a = cast(repeat('AA', 5000) as bit varying) then 1 else 0 end) as oos_a_ok,
  min(case when oos_data_b = cast(repeat('BB', 4600) as bit varying) then 1 else 0 end) as oos_b_ok,
  min(case when note = 'base' then 1 else 0 end) as note_ok,
  min(case when keep_col = 10 then 1 else 0 end) as keep_ok
from oos_schema_change_test;

select attr_name, def_order, data_type, prec, is_nullable
from db_attribute
where class_name = 'oos_schema_change_test'
order by def_order;

-- 1) 컬럼 위치 변경: OOS 컬럼을 앞/뒤로 이동해도 값이 동일하게 resolve 되는지 확인한다.
alter table oos_schema_change_test change column oos_data_b oos_data_b bit varying first;
alter table oos_schema_change_test change column oos_data_a oos_data_a bit varying after note;

evaluate '1. 컬럼 위치 변경 후 확인';
select
  'after_order_change' as step,
  count(*) as row_count,
  min(disk_size(oos_data_a)) as oos_a_bytes,
  min(disk_size(oos_data_b)) as oos_b_bytes,
  min(case when oos_data_a = cast(repeat('AA', 5000) as bit varying) then 1 else 0 end) as oos_a_ok,
  min(case when oos_data_b = cast(repeat('BB', 4600) as bit varying) then 1 else 0 end) as oos_b_ok,
  min(case when note = 'base' then 1 else 0 end) as note_ok,
  min(case when keep_col = 10 then 1 else 0 end) as keep_ok
from oos_schema_change_test;

select attr_name, def_order
from db_attribute
where class_name = 'oos_schema_change_test'
order by def_order;

-- 2) 컬럼만 추가/삭제: 기존 row 를 직접 변경하지 않는 metadata 성격의 ADD/DROP 이 OOS 에 영향 없는지 확인한다.
alter table oos_schema_change_test add column meta_only varchar(20) after id;

evaluate '2-1. nullable 컬럼만 추가 후 확인';
select
  'after_add_nullable' as step,
  count(*) as row_count,
  min(disk_size(oos_data_a)) as oos_a_bytes,
  min(disk_size(oos_data_b)) as oos_b_bytes,
  min(case when oos_data_a = cast(repeat('AA', 5000) as bit varying) then 1 else 0 end) as oos_a_ok,
  min(case when oos_data_b = cast(repeat('BB', 4600) as bit varying) then 1 else 0 end) as oos_b_ok,
  min(case when meta_only is null then 1 else 0 end) as new_col_null_ok
from oos_schema_change_test;

alter table oos_schema_change_test drop column meta_only;

evaluate '2-2. nullable 컬럼만 삭제 후 확인';
select
  'after_drop_nullable' as step,
  count(*) as row_count,
  min(disk_size(oos_data_a)) as oos_a_bytes,
  min(disk_size(oos_data_b)) as oos_b_bytes,
  min(case when oos_data_a = cast(repeat('AA', 5000) as bit varying) then 1 else 0 end) as oos_a_ok,
  min(case when oos_data_b = cast(repeat('BB', 4600) as bit varying) then 1 else 0 end) as oos_b_ok
from oos_schema_change_test;

-- 3) 컬럼 추가/삭제와 함께 레코드가 실제로 바뀌는 경우:
--    새 컬럼에 값을 채운 뒤 삭제해도 기존 OOS 컬럼이 계속 정상인지 확인한다.
alter table oos_schema_change_test add column rewrite_data bit varying after oos_data_b;
update oos_schema_change_test
set rewrite_data = cast(repeat('CC', 1200) as bit varying),
    note = 'rewrite'
where id = 1;

evaluate '3-1. 컬럼 추가 후 레코드 변경 확인';
select
  'after_add_and_update' as step,
  count(*) as row_count,
  min(disk_size(oos_data_a)) as oos_a_bytes,
  min(disk_size(oos_data_b)) as oos_b_bytes,
  min(disk_size(rewrite_data)) as rewrite_bytes,
  min(case when oos_data_a = cast(repeat('AA', 5000) as bit varying) then 1 else 0 end) as oos_a_ok,
  min(case when oos_data_b = cast(repeat('BB', 4600) as bit varying) then 1 else 0 end) as oos_b_ok,
  min(case when rewrite_data = cast(repeat('CC', 1200) as bit varying) then 1 else 0 end) as rewrite_ok,
  min(case when note = 'rewrite' then 1 else 0 end) as note_ok
from oos_schema_change_test;

alter table oos_schema_change_test drop column rewrite_data;

evaluate '3-2. 값이 있던 컬럼 삭제 후 확인';
select
  'after_drop_rewritten' as step,
  count(*) as row_count,
  min(disk_size(oos_data_a)) as oos_a_bytes,
  min(disk_size(oos_data_b)) as oos_b_bytes,
  min(case when oos_data_a = cast(repeat('AA', 5000) as bit varying) then 1 else 0 end) as oos_a_ok,
  min(case when oos_data_b = cast(repeat('BB', 4600) as bit varying) then 1 else 0 end) as oos_b_ok,
  min(case when note = 'rewrite' then 1 else 0 end) as note_ok
from oos_schema_change_test;

-- 4) OOS 컬럼 자신의 타입/속성이 바뀌는 경우:
--    OOS 컬럼의 VARBIT precision 과 nullable 속성을 바꾼 뒤에도 값이 유지되는지 확인한다.
alter table oos_schema_change_test modify column oos_data_a bit varying(50000) not null;

evaluate '4. 컬럼 타입/속성 변경 후 확인';
select
  'after_type_change' as step,
  count(*) as row_count,
  min(disk_size(oos_data_a)) as oos_a_bytes,
  min(disk_size(oos_data_b)) as oos_b_bytes,
  min(case when oos_data_a = cast(repeat('AA', 5000) as bit varying) then 1 else 0 end) as oos_a_ok,
  min(case when oos_data_b = cast(repeat('BB', 4600) as bit varying) then 1 else 0 end) as oos_b_ok,
  min(case when note = 'rewrite' then 1 else 0 end) as note_ok,
  min(case when keep_col = 10 then 1 else 0 end) as keep_ok
from oos_schema_change_test;

select attr_name, data_type, prec, is_nullable
from db_attribute
where class_name = 'oos_schema_change_test'
  and attr_name in ('oos_data_a', 'oos_data_b')
order by attr_name;

-- 5) DEFAULT 값을 가진 컬럼 추가로 기존 record 를 rewrite 하는 경우:
--    hard default 를 실제 row 에 채워 넣어도 기존 OOS 컬럼 값이 유지되는지 확인한다.
set system parameters 'add_column_update_hard_default=yes';

alter table oos_schema_change_test add column default_col int not null default 77 after keep_col;

evaluate '5. default value 컬럼 추가로 record rewrite 후 확인';
select
  'after_default_rewrite' as step,
  count(*) as row_count,
  min(disk_size(oos_data_a)) as oos_a_bytes,
  min(disk_size(oos_data_b)) as oos_b_bytes,
  min(case when oos_data_a = cast(repeat('AA', 5000) as bit varying) then 1 else 0 end) as oos_a_ok,
  min(case when oos_data_b = cast(repeat('BB', 4600) as bit varying) then 1 else 0 end) as oos_b_ok,
  min(case when default_col = 77 then 1 else 0 end) as default_ok
from oos_schema_change_test;

-- 6) OOS 를 포함한 컬럼 자체가 사라지는 경우:
--    한 OOS 컬럼을 DROP 해도 남은 OOS 컬럼과 row 가 정상인지 확인한다.
alter table oos_schema_change_test drop column oos_data_b;

evaluate '6. OOS 컬럼 삭제 후 남은 OOS 컬럼 확인';
select
  'after_drop_oos_column' as step,
  count(*) as row_count,
  min(disk_size(oos_data_a)) as oos_a_bytes,
  min(case when oos_data_a = cast(repeat('AA', 5000) as bit varying) then 1 else 0 end) as oos_a_ok,
  min(case when note = 'rewrite' then 1 else 0 end) as note_ok,
  min(case when default_col = 77 then 1 else 0 end) as default_ok
from oos_schema_change_test;

select attr_name, def_order
from db_attribute
where class_name = 'oos_schema_change_test'
order by def_order;

drop table oos_schema_change_test;

-- 7) OOS 가 아니었던 컬럼이 OOS 로 가는 경우:
--    3000 byte 컬럼 하나만 있을 때는 record 가 DB_PAGESIZE/4 이하라 OOS 대상이 아니다.
--    이후 DEFAULT 값을 가진 컬럼을 hard rewrite 로 추가해서 record 를 키우면,
--    기존 inline 컬럼이 가장 큰 variable column 이 되어 OOS demotion 대상이 된다.
drop table if exists oos_inline_to_oos_test;

create table oos_inline_to_oos_test (
  id int primary key,
  inline_then_oos bit varying
);

insert into oos_inline_to_oos_test values (
  1,
  cast(repeat('AA', 3000) as bit varying)
);

evaluate '7-1. OOS 전환 전 inline 컬럼 확인';
select
  'before_inline_to_oos' as step,
  count(*) as row_count,
  min(disk_size(inline_then_oos)) as inline_bytes,
  min(case when inline_then_oos = cast(repeat('AA', 3000) as bit varying) then 1 else 0 end) as inline_ok
from oos_inline_to_oos_test;

alter table oos_inline_to_oos_test
  add column grow_data bit varying not null default cast(repeat('DD', 2500) as bit varying);

evaluate '7-2. default value rewrite 후 inline 컬럼의 OOS 전환 확인';
select
  'after_inline_to_oos' as step,
  count(*) as row_count,
  min(disk_size(inline_then_oos)) as inline_bytes,
  min(disk_size(grow_data)) as grow_bytes,
  min(case when inline_then_oos = cast(repeat('AA', 3000) as bit varying) then 1 else 0 end) as inline_ok,
  min(case when grow_data = cast(repeat('DD', 2500) as bit varying) then 1 else 0 end) as grow_ok
from oos_inline_to_oos_test;

set system parameters 'add_column_update_hard_default=no';

drop table oos_inline_to_oos_test;
