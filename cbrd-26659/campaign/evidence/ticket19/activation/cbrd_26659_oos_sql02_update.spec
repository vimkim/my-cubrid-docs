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
