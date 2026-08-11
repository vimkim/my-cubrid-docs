;set communication_histogram=yes
;.hist on

CREATE TABLE sx_aio_quiz_1_t
(
  id INTEGER PRIMARY KEY,
  payload VARCHAR (200)
);

INSERT INTO sx_aio_quiz_1_t
SELECT LEVEL, REPEAT (CHR (113), 160)
  FROM db_root
CONNECT BY LEVEL <= 2000;

COMMIT;

SELECT COUNT (*) AS quiz_rows
  FROM sx_aio_quiz_1_t;

;.dump_hist

DROP TABLE sx_aio_quiz_1_t;
COMMIT;
