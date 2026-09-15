# CBRD-26659 ticket 19 activation spec for cbrd_26659_oos_sql06_triggers.
# Generated with the case itself by evidence/ticket19/gen_ticket19_cases.py; run by
# tools/activation_check_spec.sh, client-server, under campaign_ns.sh (user decision O2,
# ticket 35).  PHASE <tag> <table> <has_oos> <num_recs> <sumlen>; `-` observes instead of
# asserting.  Every asserted figure is derived, never measured: see derivation-output.txt.

PHASE create t_cbrd_26659_sql06t 0 0 0
DROP TABLE IF EXISTS t_cbrd_26659_sql06t_inslog;
DROP TABLE IF EXISTS t_cbrd_26659_sql06t_ins;
DROP TABLE IF EXISTS t_cbrd_26659_sql06t_mirror;
DROP TABLE IF EXISTS t_cbrd_26659_sql06t_log;
DROP TABLE IF EXISTS t_cbrd_26659_sql06t;
CREATE TABLE t_cbrd_26659_sql06t (id INT PRIMARY KEY, payload BIT VARYING, tag BIT VARYING);
CREATE TABLE t_cbrd_26659_sql06t_log (seq INT AUTO_INCREMENT PRIMARY KEY, id INT, payload_octets INT,
                    payload_md5 VARCHAR(32));
CREATE TABLE t_cbrd_26659_sql06t_mirror (id INT PRIMARY KEY, payload BIT VARYING, tag BIT VARYING);
# The fixture is built while the table still has no trigger, so these rows really are
# OOS-backed.  This is the phase that makes the case OOS coverage at all.
PHASE pre_trigger_inserts t_cbrd_26659_sql06t 1 1 4224
INSERT INTO t_cbrd_26659_sql06t VALUES (1, CAST(REPEAT('a', 8400) AS BIT VARYING), CAST(REPEAT('b', 600) AS BIT VARYING));
INSERT INTO t_cbrd_26659_sql06t VALUES (2, CAST(REPEAT('c', 6000) AS BIT VARYING), CAST(REPEAT('d', 600) AS BIT VARYING));
# FINDING (campaign report, ticket 19): the OOS record gate is applied only on the server-side
# DML path.  Once the table carries a trigger, the UPDATE below is routed to the client-side
# object-template path (execute_statement.c:12445) and never reaches
# heap_attrinfo_determine_disk_layout, so it rewrites the record fully inline and drops the
# chain.  Were the gate path-independent this phase would still read 1 / 4224.
# OBSERVED, not asserted: asserting either number would bless one side of the defect.
PHASE after_triggered_update t_cbrd_26659_sql06t 1 - -
CREATE TRIGGER tr_t_cbrd_26659_sql06t_log AFTER UPDATE ON t_cbrd_26659_sql06t
  EXECUTE INSERT INTO t_cbrd_26659_sql06t_log (id, payload_octets, payload_md5)
          VALUES (obj.id, OCTET_LENGTH(obj.payload), MD5(obj.payload));
UPDATE t_cbrd_26659_sql06t SET tag = CAST(REPEAT('7', 600) AS BIT VARYING) WHERE id = 1;
# Same finding on the INSERT side: a fresh table whose first INSERT carries a trigger.  Were
# the gate path-independent this phase would read 1 / 1 / 4224.  All three observed.
PHASE insert_trigger_table t_cbrd_26659_sql06t_ins - - -
CREATE TABLE t_cbrd_26659_sql06t_ins (id INT PRIMARY KEY, payload BIT VARYING, tag BIT VARYING);
CREATE TABLE t_cbrd_26659_sql06t_inslog (id INT PRIMARY KEY, payload_octets INT, payload_md5 VARCHAR(32));
CREATE TRIGGER tr_t_cbrd_26659_sql06t_ins AFTER INSERT ON t_cbrd_26659_sql06t_ins
  EXECUTE INSERT INTO t_cbrd_26659_sql06t_inslog VALUES (obj.id, OCTET_LENGTH(obj.payload), MD5(obj.payload));
INSERT INTO t_cbrd_26659_sql06t_ins VALUES (1, CAST(REPEAT('a', 8400) AS BIT VARYING), CAST(REPEAT('b', 600) AS BIT VARYING));
