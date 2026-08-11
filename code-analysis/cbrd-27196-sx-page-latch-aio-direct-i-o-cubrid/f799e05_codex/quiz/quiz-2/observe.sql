;set communication_histogram=yes
;.hist on

CREATE TABLE sx_aio_quiz_2_t
(
  id INTEGER PRIMARY KEY,
  payload VARCHAR (200)
);

INSERT INTO sx_aio_quiz_2_t
SELECT LEVEL, REPEAT (CHR (114), 120)
  FROM db_root
CONNECT BY LEVEL <= 1000;

UPDATE sx_aio_quiz_2_t
   SET payload = REPEAT (CHR (115), 180)
 WHERE MOD (id, 2) = 0;

COMMIT;

SELECT COUNT (*) AS quiz_rows,
       SUM (CASE WHEN LENGTH (payload) = 180 THEN 1 ELSE 0 END) AS updated_rows
  FROM sx_aio_quiz_2_t;

;.dump_hist

DROP TABLE sx_aio_quiz_2_t;
COMMIT;
