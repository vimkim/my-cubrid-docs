-- experiment-1 runner (관측 내장형)
-- 목적: B-tree insert 20,000건이 page latch 승격(promote)을 실제로 수행하는지,
--       csql 세션 histogram(;.hist)으로 같은 실행 안에서 관측한다.
-- 오라클: ;.dump_hist 출력의 Data_page_total_promote_success > 0
--         그리고 Data_page_total_promote_fail == 0 (단일 세션이라 경쟁 없음).

;set communication_histogram=yes
;.hist on

DROP TABLE IF EXISTS sx_promote_t;

CREATE TABLE sx_promote_t (id INT PRIMARY KEY, v VARCHAR(100));

INSERT INTO sx_promote_t
SELECT LEVEL, REPEAT(CHR(120), 80) FROM db_root CONNECT BY LEVEL <= 20000;

COMMIT;

SELECT COUNT(*) FROM sx_promote_t;

;.dump_hist

DROP TABLE sx_promote_t;

COMMIT;
