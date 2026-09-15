# CBRD-26659 ticket 19 activation spec for cbrd_26659_oos_sql01_insert_select.
# Generated with the case itself by evidence/ticket19/gen_ticket19_cases.py; run by
# tools/activation_check_spec.sh, client-server, under campaign_ns.sh (user decision O2,
# ticket 35).  PHASE <tag> <table> <has_oos> <num_recs> <sumlen>; `-` observes instead of
# asserting.  Every asserted figure is derived, never measured: see derivation-output.txt.

PHASE create t_cbrd_26659_sql01 0 0 0
DROP TABLE IF EXISTS t_cbrd_26659_sql01;
CREATE TABLE t_cbrd_26659_sql01 (id INT PRIMARY KEY, payload BIT VARYING, tag BIT VARYING);
PHASE comparator t_cbrd_26659_sql01 0 0 0
INSERT INTO t_cbrd_26659_sql01 VALUES (2, CAST(REPEAT('c', 6000) AS BIT VARYING), CAST(REPEAT('d', 600) AS BIT VARYING));
PHASE oosbacked t_cbrd_26659_sql01 1 1 4224
INSERT INTO t_cbrd_26659_sql01 VALUES (1, CAST(REPEAT('a', 8400) AS BIT VARYING), CAST(REPEAT('b', 600) AS BIT VARYING));
PHASE bulk100 t_cbrd_26659_sql01_b100 1 100 457600
DROP TABLE IF EXISTS t_cbrd_26659_sql01_b1000;
DROP TABLE IF EXISTS t_cbrd_26659_sql01_b100;
DROP TABLE IF EXISTS n1000_cbrd_26659_sql01;
DROP TABLE IF EXISTS n10_cbrd_26659_sql01;
CREATE TABLE n10_cbrd_26659_sql01 (i INT);
INSERT INTO n10_cbrd_26659_sql01 VALUES (0), (1), (2), (3), (4), (5), (6), (7), (8), (9);
CREATE TABLE n1000_cbrd_26659_sql01 (i INT PRIMARY KEY);
INSERT INTO n1000_cbrd_26659_sql01 SELECT a.i * 100 + b.i * 10 + c.i + 1 FROM n10_cbrd_26659_sql01 a, n10_cbrd_26659_sql01 b, n10_cbrd_26659_sql01 c;
CREATE TABLE t_cbrd_26659_sql01_b100 (id INT PRIMARY KEY, payload BIT VARYING, tag BIT VARYING);
INSERT INTO t_cbrd_26659_sql01_b100
  SELECT i, CAST(REPEAT(SUBSTR('123456789abcdef', MOD(i, 15) + 1, 1), 2 * (4200 + 7 * i)) AS BIT VARYING), CAST(REPEAT('7', 600) AS BIT VARYING) FROM n1000_cbrd_26659_sql01 WHERE i <= 100;
# The thousand-row group too: without this phase its OOS-backed premise would be derived and
# never observed, while the case's answer asserts all thousand values read back exactly.
PHASE bulk1000 t_cbrd_26659_sql01_b1000 1 1000 4169540
CREATE TABLE t_cbrd_26659_sql01_b1000 (id INT PRIMARY KEY, payload BIT VARYING, tag BIT VARYING);
INSERT INTO t_cbrd_26659_sql01_b1000
  SELECT i, CAST(REPEAT(SUBSTR('123456789abcdef', MOD(i, 15) + 1, 1), 2 * (4100 + MOD(i, 97))) AS BIT VARYING), CAST(REPEAT('7', 600) AS BIT VARYING) FROM n1000_cbrd_26659_sql01;
# INSERT ... SELECT is a different execution path from INSERT ... VALUES -- CUBRID decides them
# separately (execute_statement.c, INSERT_SELECT versus INSERT_VALUES) -- and finding T19-F1
# proves the path, not the size, decides whether the record gate runs at all.  So the copy the
# case makes is observed on its own table rather than inherited from the group it copies.
PHASE copy t_cbrd_26659_sql01_copy 1 100 457600
DROP TABLE IF EXISTS t_cbrd_26659_sql01_copy;
CREATE TABLE t_cbrd_26659_sql01_copy (id INT PRIMARY KEY, payload BIT VARYING, tag BIT VARYING);
INSERT INTO t_cbrd_26659_sql01_copy SELECT id, payload, tag FROM t_cbrd_26659_sql01_b100;
