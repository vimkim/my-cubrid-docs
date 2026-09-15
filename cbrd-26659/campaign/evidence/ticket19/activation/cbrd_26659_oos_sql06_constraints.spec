# CBRD-26659 ticket 19 activation spec for cbrd_26659_oos_sql06_constraints.
# Generated with the case itself by evidence/ticket19/gen_ticket19_cases.py; run by
# tools/activation_check_spec.sh, client-server, under campaign_ns.sh (user decision O2,
# ticket 35).  PHASE <tag> <table> <has_oos> <num_recs> <sumlen>; `-` observes instead of
# asserting.  Every asserted figure is derived, never measured: see derivation-output.txt.

PHASE create t_cbrd_26659_sql06c 0 0 0
DROP TABLE IF EXISTS t_cbrd_26659_sql06c;
CREATE TABLE t_cbrd_26659_sql06c (id INT PRIMARY KEY, payload BIT VARYING, tag BIT VARYING, uniq INT UNIQUE);
PHASE fixture t_cbrd_26659_sql06c 1 1 4224
INSERT INTO t_cbrd_26659_sql06c VALUES (1, CAST(REPEAT('a', 8400) AS BIT VARYING), CAST(REPEAT('b', 600) AS BIT VARYING), 100);
INSERT INTO t_cbrd_26659_sql06c VALUES (2, CAST(REPEAT('c', 6000) AS BIT VARYING), CAST(REPEAT('d', 600) AS BIT VARYING), 200);
# The rejected INSERT may or may not have written chunks before the unique check refused it,
# and any it wrote are dead and awaiting vacuum, so the count is observed.  What IS asserted at
# the SQL seam is that no VALUE is stored -- see the case.
PHASE after_pk_violation t_cbrd_26659_sql06c 1 - -
INSERT INTO t_cbrd_26659_sql06c VALUES (1, CAST(REPEAT('e', 8600) AS BIT VARYING), CAST(REPEAT('5', 600) AS BIT VARYING), 300);
