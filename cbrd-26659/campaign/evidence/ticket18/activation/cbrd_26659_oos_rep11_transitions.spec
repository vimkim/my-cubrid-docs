# CBRD-26659 ticket 18 activation spec for cbrd_26659_oos_rep11_transitions.
# Generated with the case itself; run by tools/activation_check_spec.sh, client-server, under
# campaign_ns.sh (user decision O2, ticket 35).  PHASE <tag> <table> <has_oos> <num_recs>
# <sumlen>; `-` observes instead of asserting.  Every asserted figure is derived, never
# measured.  Every phase owns its own table, so a chunk count is that phase's own and not a
# running total over the ones before it.
#
# Where a figure is observed rather than asserted, the line above it says what the accepted
# design would require and what the pinned engine is known to do.  Observation is what the
# authority policy requires of a quantity whose value is not settled at this revision; it is
# not leniency, and the difference between the two is the campaign's finding, not its oracle.

PHASE vot_inline t_cbrd_26659_rep11_chk_vot 0 0 0
DROP TABLE IF EXISTS t_cbrd_26659_rep11_chk_vot;
CREATE TABLE t_cbrd_26659_rep11_chk_vot (id INT PRIMARY KEY, a BIT VARYING, b BIT VARYING);
INSERT INTO t_cbrd_26659_rep11_chk_vot VALUES (1, CAST(REPEAT('1', 80) AS BIT VARYING), CAST(REPEAT('2', 80) AS BIT VARYING));
INSERT INTO t_cbrd_26659_rep11_chk_vot VALUES (2, CAST(REPEAT('3', 80) AS BIT VARYING), CAST(REPEAT('4', 88) AS BIT VARYING));
PHASE vot_narrowed t_cbrd_26659_rep11_chk_narrow 1 1 4224
DROP TABLE IF EXISTS t_cbrd_26659_rep11_chk_narrow;
CREATE TABLE t_cbrd_26659_rep11_chk_narrow (id INT PRIMARY KEY, payload BIT VARYING, tag BIT VARYING);
INSERT INTO t_cbrd_26659_rep11_chk_narrow VALUES (1, CAST(REPEAT('a', 8400) AS BIT VARYING), CAST(REPEAT('b', 60) AS BIT VARYING));
PHASE inline_before t_cbrd_26659_rep11_chk_trans 0 0 0
DROP TABLE IF EXISTS t_cbrd_26659_rep11_chk_trans;
CREATE TABLE t_cbrd_26659_rep11_chk_trans (id INT PRIMARY KEY, payload BIT VARYING, tag BIT VARYING);
INSERT INTO t_cbrd_26659_rep11_chk_trans VALUES (1, CAST(REPEAT('c', 6000) AS BIT VARYING), CAST(REPEAT('d', 600) AS BIT VARYING));
# Crossing the gate upward really does create a chain: this is the one transition assertion of
# the case, and it is assertable because the row was inline before and both accountings agree
# that 4200 B is above the gate.
PHASE crossed_up t_cbrd_26659_rep11_chk_trans 1 1 4224
UPDATE t_cbrd_26659_rep11_chk_trans SET payload = CAST(REPEAT('e', 8400) AS BIT VARYING) WHERE id = 1;
# Crossing back down.  The value goes inline again, but at this revision the chain the previous
# UPDATE created is not reclaimed synchronously (OOS-SQL-03, observation-only, superseded on
# paper by CBRD-27230), so the count after this statement is current behaviour and a moving
# target for vacuum.  Observed.
PHASE crossed_down t_cbrd_26659_rep11_chk_trans - - -
UPDATE t_cbrd_26659_rep11_chk_trans SET payload = CAST(REPEAT('f', 6000) AS BIT VARYING) WHERE id = 1;
