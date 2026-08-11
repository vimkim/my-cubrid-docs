;set communication_histogram=yes
;.hist on

DROP TABLE IF EXISTS sx_aio_exp_flush_t;

CREATE TABLE sx_aio_exp_flush_t
(
  id INTEGER PRIMARY KEY,
  payload VARCHAR (400)
);

INSERT INTO sx_aio_exp_flush_t
SELECT LEVEL, REPEAT (CHR (120), 320)
  FROM db_root
CONNECT BY LEVEL <= 20000;

COMMIT;

SELECT COUNT (*) AS inserted_rows
  FROM sx_aio_exp_flush_t;

;.dump_hist
