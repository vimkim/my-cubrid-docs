-- Shared OOS performance dataset.
-- Execute unchanged through csql on both develop and the OOS branch.

DROP TABLE IF EXISTS perf_oos;

CREATE TABLE perf_oos (
  id       INT PRIMARY KEY,
  hot_col  INT NOT NULL,
  payload  BIT VARYING
);

INSERT INTO perf_oos
SELECT LEVEL,
       MOD (LEVEL, 1000),
       REPEAT (X'0123456789ABCDEF', 512)
  FROM db_root
CONNECT BY LEVEL <= 100000;
COMMIT;

SELECT COUNT(*) AS rows_loaded,
       MIN (BIT_LENGTH (payload)) AS min_payload_bits,
       MAX (BIT_LENGTH (payload)) AS max_payload_bits
  FROM perf_oos;
