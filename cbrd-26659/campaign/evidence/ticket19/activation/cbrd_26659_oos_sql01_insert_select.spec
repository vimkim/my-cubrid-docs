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
