# CBRD-26659 ticket 19 activation spec for cbrd_26659_oos_sql06_rollback.
# Generated with the case itself by evidence/ticket19/gen_ticket19_cases.py; run by
# tools/activation_check_spec.sh, client-server, under campaign_ns.sh (user decision O2,
# ticket 35).  PHASE <tag> <table> <has_oos> <num_recs> <sumlen>; `-` observes instead of
# asserting.  Every asserted figure is derived, never measured: see derivation-output.txt.

# Only the committed fixture is replayed: what makes this case OOS coverage is that the rows
# the transactions write and undo are OOS-backed.  The undo semantics themselves are asserted
# by the case at the SQL seam, which is where they are observable, and csql's own autocommit
# control is a session command rather than SQL, so replaying the transactions here would test
# the checker's driver rather than the engine.
PHASE create t_cbrd_26659_sql06r 0 0 0
DROP TABLE IF EXISTS t_cbrd_26659_sql06r;
CREATE TABLE t_cbrd_26659_sql06r (id INT PRIMARY KEY, payload BIT VARYING, tag BIT VARYING);
PHASE fixture t_cbrd_26659_sql06r 1 1 4224
INSERT INTO t_cbrd_26659_sql06r VALUES (1, CAST(REPEAT('a', 8400) AS BIT VARYING), CAST(REPEAT('b', 600) AS BIT VARYING));
INSERT INTO t_cbrd_26659_sql06r VALUES (2, CAST(REPEAT('c', 6000) AS BIT VARYING), CAST(REPEAT('d', 600) AS BIT VARYING));
