# CBRD-26659 ticket 19 activation spec for cbrd_26659_oos_sql02_update.
# Generated with the case itself by evidence/ticket19/gen_ticket19_cases.py; run by
# tools/activation_check_spec.sh, client-server, under campaign_ns.sh (user decision O2,
# ticket 35).  PHASE <tag> <table> <has_oos> <num_recs> <sumlen>; `-` observes instead of
# asserting.  Every asserted figure is derived, never measured: see derivation-output.txt.

PHASE create t_cbrd_26659_sql02 0 0 0
DROP TABLE IF EXISTS t_cbrd_26659_sql02;
CREATE TABLE t_cbrd_26659_sql02 (id INT PRIMARY KEY, payload BIT VARYING, tag BIT VARYING);
PHASE oosbacked t_cbrd_26659_sql02 1 1 4224
INSERT INTO t_cbrd_26659_sql02 VALUES (1, CAST(REPEAT('a', 8400) AS BIT VARYING), CAST(REPEAT('b', 600) AS BIT VARYING));
PHASE comparator t_cbrd_26659_sql02 1 1 4224
INSERT INTO t_cbrd_26659_sql02 VALUES (2, CAST(REPEAT('c', 6000) AS BIT VARYING), CAST(REPEAT('d', 600) AS BIT VARYING));
# From here the counts are current behaviour, not a requirement: at the pin every UPDATE
# allocates fresh value chains, and the dead ones stay until vacuum (OOS-SQL-03,
# observation-only, superseded on paper by CBRD-27230).  Observed, never asserted.
PHASE update_payload t_cbrd_26659_sql02 1 - -
UPDATE t_cbrd_26659_sql02 SET payload = CAST(REPEAT('e', 10000) AS BIT VARYING) WHERE id = 1;
PHASE update_tag_only t_cbrd_26659_sql02 1 - -
UPDATE t_cbrd_26659_sql02 SET tag = CAST(REPEAT('7', 600) AS BIT VARYING) WHERE id = 1;
PHASE update_multichunk t_cbrd_26659_sql02 1 - -
UPDATE t_cbrd_26659_sql02 SET payload = CAST(REPEAT('f', 40000) AS BIT VARYING) WHERE id = 1;
# The last two steps of the case write through two further execution paths: an UPDATE whose
# value comes from a subquery, and a multi-table UPDATE.  Finding T19-F1 is exactly a path that
# silently skips the record gate, so neither is inherited from the phases above; each runs on
# its own fresh table, starting from an inline row, so the count after it is unambiguous.
PHASE subquery_update t_cbrd_26659_sql02_chk_sub 1 1 4624
DROP TABLE IF EXISTS t_cbrd_26659_sql02_chk_sub;
DROP TABLE IF EXISTS t_cbrd_26659_sql02_chk_src;
CREATE TABLE t_cbrd_26659_sql02_chk_sub (id INT PRIMARY KEY, payload BIT VARYING, tag BIT VARYING);
CREATE TABLE t_cbrd_26659_sql02_chk_src (id INT PRIMARY KEY, payload BIT VARYING, tag BIT VARYING);
INSERT INTO t_cbrd_26659_sql02_chk_src VALUES (1, CAST(REPEAT('d', 9200) AS BIT VARYING), CAST(REPEAT('5', 600) AS BIT VARYING));
INSERT INTO t_cbrd_26659_sql02_chk_sub VALUES (1, CAST(REPEAT('c', 6000) AS BIT VARYING), CAST(REPEAT('d', 600) AS BIT VARYING));
UPDATE t_cbrd_26659_sql02_chk_sub SET payload = (SELECT payload FROM t_cbrd_26659_sql02_chk_src WHERE id = 1) WHERE id = 1;
PHASE join_update t_cbrd_26659_sql02_chk_join 1 1 4624
DROP TABLE IF EXISTS t_cbrd_26659_sql02_chk_join;
CREATE TABLE t_cbrd_26659_sql02_chk_join (id INT PRIMARY KEY, payload BIT VARYING, tag BIT VARYING);
INSERT INTO t_cbrd_26659_sql02_chk_join VALUES (1, CAST(REPEAT('c', 6000) AS BIT VARYING), CAST(REPEAT('d', 600) AS BIT VARYING));
UPDATE t_cbrd_26659_sql02_chk_join a, t_cbrd_26659_sql02_chk_src b SET a.payload = b.payload, a.tag = b.tag WHERE a.id = 1 AND b.id = 1;
