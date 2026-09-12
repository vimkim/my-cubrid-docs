SET SYSTEM PARAMETERS 'fault_injection_ids=700010; fault_injection_fire_at_occurrence=0';
INSERT INTO t SELECT ROWNUM + 1000, CAST(REPEAT('CC', 40000) AS BIT VARYING) FROM db_class a, db_class b LIMIT 12;
COMMIT;
SHOW HEAP OOS OF t;
