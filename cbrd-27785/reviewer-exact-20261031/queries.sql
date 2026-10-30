-- 좁은 컬럼 스캔
select count(*), sum(a) from w;
-- 큰 컬럼을 읽는 스캔
select sum(length(big)) from w;
select count(*) from w where substr(big, 5000, 1) = 'a';
-- 작은 컬럼 UPDATE
update w set a=a+1;
-- 큰 컬럼 UPDATE
update w set big=concat(substr(big,2),substr(big,1,1)) where id<=5000;
-- OOS 값이 없는 일반 테이블
select count(*), sum(a) from n;
select count(*) from n where substr(s, 30, 1) = 'a';
update n set a=a+1;
