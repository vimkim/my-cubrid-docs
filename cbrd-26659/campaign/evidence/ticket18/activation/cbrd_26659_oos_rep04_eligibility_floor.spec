# CBRD-26659 ticket 18 activation spec for cbrd_26659_oos_rep04_eligibility_floor.
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

PHASE comparator t_cbrd_26659_rep04_chk_cmp 0 0 0
DROP TABLE IF EXISTS t_cbrd_26659_rep04_chk_cmp;
CREATE TABLE t_cbrd_26659_rep04_chk_cmp (id INT PRIMARY KEY, filler BIT(800), payload BIT VARYING, small BIT VARYING);
INSERT INTO t_cbrd_26659_rep04_chk_cmp VALUES (1, CAST(REPEAT('1', 200) AS BIT(800)), CAST(REPEAT('2', 1000) AS BIT VARYING), CAST(REPEAT('3', 30) AS BIT VARYING));
# One chunk, not two: `payload` moved and the 15 B `small` did not, although the record is still
# above the gate and the loop was still looking.  That is the eligibility floor and nothing else.
PHASE below_floor t_cbrd_26659_rep04_chk_below 1 1 4224
DROP TABLE IF EXISTS t_cbrd_26659_rep04_chk_below;
CREATE TABLE t_cbrd_26659_rep04_chk_below (id INT PRIMARY KEY, filler BIT(40000), payload BIT VARYING, small BIT VARYING);
INSERT INTO t_cbrd_26659_rep04_chk_below VALUES (1, CAST(REPEAT('a', 10000) AS BIT(40000)), CAST(REPEAT('b', 8400) AS BIT VARYING), CAST(REPEAT('c', 30) AS BIT VARYING));
# Two chunks: at 24 B `small` is a candidate under both accountings and the exhausted loop takes it.
PHASE above_floor t_cbrd_26659_rep04_chk_above 1 2 4268
DROP TABLE IF EXISTS t_cbrd_26659_rep04_chk_above;
CREATE TABLE t_cbrd_26659_rep04_chk_above (id INT PRIMARY KEY, filler BIT(40000), payload BIT VARYING, small BIT VARYING);
INSERT INTO t_cbrd_26659_rep04_chk_above VALUES (1, CAST(REPEAT('d', 10000) AS BIT(40000)), CAST(REPEAT('e', 8400) AS BIT VARYING), CAST(REPEAT('f', 48) AS BIT VARYING));
# The band.  At 20 B the value serializes to 24 B: above the pinned 16-byte floor and at the
# normative 24-byte one, so the pinned engine demotes it and the accepted identity layout of
# CBRD-26950 would not.  Expected under the accepted layout: Oos_num_recs 1, Oos_recs_sumlen
# 4224.  Observed, never asserted (OOS-REP-05, UNSUPPORTED at this revision).
PHASE floor_band t_cbrd_26659_rep04_chk_band - - -
DROP TABLE IF EXISTS t_cbrd_26659_rep04_chk_band;
CREATE TABLE t_cbrd_26659_rep04_chk_band (id INT PRIMARY KEY, filler BIT(40000), payload BIT VARYING, small BIT VARYING);
INSERT INTO t_cbrd_26659_rep04_chk_band VALUES (1, CAST(REPEAT('8', 10000) AS BIT(40000)), CAST(REPEAT('9', 8400) AS BIT VARYING), CAST(REPEAT('7', 40) AS BIT VARYING));
