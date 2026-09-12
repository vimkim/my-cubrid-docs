CREATE TABLE t (id INT, v BIT VARYING);
;autocommit off
INSERT INTO t VALUES (1, CAST(REPEAT('BB', 20000) AS BIT VARYING));
SET SYSTEM PARAMETERS 'fault_injection_ids=1; fault_injection_fire_at_occurrence=1';
ROLLBACK;
SELECT COUNT(*) FROM t;
COMMIT;
