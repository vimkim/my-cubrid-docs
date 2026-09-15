# CBRD-26659 ticket 19 activation spec for cbrd_26659_oos_sql05_delete.
# Generated with the case itself by evidence/ticket19/gen_ticket19_cases.py; run by
# tools/activation_check_spec.sh, client-server, under campaign_ns.sh (user decision O2,
# ticket 35).  PHASE <tag> <table> <has_oos> <num_recs> <sumlen>; `-` observes instead of
# asserting.  Every asserted figure is derived, never measured: see derivation-output.txt.

PHASE create t_cbrd_26659_sql05 0 0 0
DROP TABLE IF EXISTS t_cbrd_26659_sql05;
CREATE TABLE t_cbrd_26659_sql05 (id INT PRIMARY KEY, payload BIT VARYING, tag BIT VARYING);
PHASE fixture t_cbrd_26659_sql05 1 3 13272
INSERT INTO t_cbrd_26659_sql05 VALUES (1, CAST(REPEAT('a', 8400) AS BIT VARYING), CAST(REPEAT('b', 600) AS BIT VARYING));
INSERT INTO t_cbrd_26659_sql05 VALUES (2, CAST(REPEAT('c', 6000) AS BIT VARYING), CAST(REPEAT('d', 600) AS BIT VARYING));
INSERT INTO t_cbrd_26659_sql05 VALUES (3, CAST(REPEAT('e', 8800) AS BIT VARYING), CAST(REPEAT('5', 600) AS BIT VARYING));
INSERT INTO t_cbrd_26659_sql05 VALUES (4, CAST(REPEAT('f', 9200) AS BIT VARYING), CAST(REPEAT('6', 600) AS BIT VARYING));
# OOS-SQL-05 says the value chains are not removed at delete time in MVCC mode, and they are
# not -- but the moment vacuum reclaims them is a background event, so the count here is
# OBSERVED with its expected value beside it rather than asserted against a race.
# Expected while the deletes are still undo sources: 13272 unchanged after one DELETE,
# and unchanged again after DELETE of the rest.
PHASE delete_one t_cbrd_26659_sql05 1 - -
DELETE FROM t_cbrd_26659_sql05 WHERE id = 1;
PHASE delete_rest t_cbrd_26659_sql05 1 - -
DELETE FROM t_cbrd_26659_sql05;
