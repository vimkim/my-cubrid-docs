;set communication_histogram=yes
;.hist on

DROP TABLE IF EXISTS sx_quiz2_t;

CREATE TABLE sx_quiz2_t (id INT PRIMARY KEY, v VARCHAR(200));

INSERT INTO sx_quiz2_t
SELECT LEVEL, REPEAT(CHR(121), 150) FROM db_root CONNECT BY LEVEL <= 10000;

COMMIT;

SELECT COUNT(*) FROM sx_quiz2_t;

;.dump_hist

DROP TABLE sx_quiz2_t;

COMMIT;
