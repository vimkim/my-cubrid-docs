# CBRD-26659 ticket 19 activation spec for cbrd_26659_oos_sql02_mixed_chunks.
# Generated with the case itself by evidence/ticket19/gen_ticket19_cases.py; run by
# tools/activation_check_spec.sh, client-server, under campaign_ns.sh (user decision O2,
# ticket 35).  PHASE <tag> <table> <has_oos> <num_recs> <sumlen>; `-` observes instead of
# asserting.  Every asserted figure is derived, never measured: see derivation-output.txt.

PHASE create t_cbrd_26659_sql02_mixed 0 0 0
DROP TABLE IF EXISTS t_cbrd_26659_sql02_mixed;
CREATE TABLE t_cbrd_26659_sql02_mixed
  (id INT PRIMARY KEY, single1 BIT VARYING, multi1 BIT VARYING, single2 BIT VARYING);
# Three chunk records for row 1: two for the 20000 B value and one for the 3500 B one.  This is
# where the reused CBRD-27006 workload's chunk topology stops being an inference.  The
# equal-size tie between single1 and single2 does not reach these figures: the two columns
# being the same size, the count and the sum are identical whichever one moved.
PHASE row1 t_cbrd_26659_sql02_mixed 1 3 23565
INSERT INTO t_cbrd_26659_sql02_mixed VALUES (1, CAST(REPEAT('1', 7000) AS BIT VARYING), CAST(REPEAT('2', 40000) AS BIT VARYING), CAST(REPEAT('3', 7000) AS BIT VARYING));
PHASE row2 t_cbrd_26659_sql02_mixed 1 6 48228
INSERT INTO t_cbrd_26659_sql02_mixed VALUES (2, CAST(REPEAT('4', 7200) AS BIT VARYING), CAST(REPEAT('5', 42000) AS BIT VARYING), CAST(REPEAT('6', 6800) AS BIT VARYING));
