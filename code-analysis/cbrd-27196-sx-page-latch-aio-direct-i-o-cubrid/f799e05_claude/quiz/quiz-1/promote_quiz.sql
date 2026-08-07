;set communication_histogram=yes
;.hist on

DROP TABLE IF EXISTS sx_quiz1_t;

CREATE TABLE sx_quiz1_t (id INT PRIMARY KEY, v VARCHAR(100));

INSERT INTO sx_quiz1_t
SELECT LEVEL, REPEAT(CHR(120), 80) FROM db_root CONNECT BY LEVEL <= 20000;

COMMIT;

SELECT COUNT(*) FROM sx_quiz1_t;

;.dump_hist

DROP TABLE sx_quiz1_t;

COMMIT;
