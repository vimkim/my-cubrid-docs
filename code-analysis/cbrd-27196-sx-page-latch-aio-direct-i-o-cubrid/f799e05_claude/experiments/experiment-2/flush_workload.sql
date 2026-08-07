-- experiment-2 runner (관측 내장형)
-- 목적: 대량 insert가 data page를 dirty로 만드는 것을 같은 csql 실행 안에서
--       per-transaction histogram으로 관측한다 (Num_data_page_dirties > 0).
--       flush 자체(디스크 물리 쓰기)는 이후 backupdb가 강제하는 checkpoint 동안
--       전역 카운터 Num_data_page_iowrites 증가로 별도 기록(exp2-statdump-after)에서 관측한다.

;set communication_histogram=yes
;.hist on

DROP TABLE IF EXISTS sx_flush_t;

CREATE TABLE sx_flush_t (id INT PRIMARY KEY, v VARCHAR(200));

INSERT INTO sx_flush_t
SELECT LEVEL, REPEAT(CHR(121), 150) FROM db_root CONNECT BY LEVEL <= 10000;

COMMIT;

SELECT COUNT(*) FROM sx_flush_t;

;.dump_hist
