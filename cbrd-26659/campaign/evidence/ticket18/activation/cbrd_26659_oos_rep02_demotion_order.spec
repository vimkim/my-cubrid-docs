# CBRD-26659 ticket 18 activation spec for cbrd_26659_oos_rep02_demotion_order.
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

PHASE comparator t_cbrd_26659_rep02ord_chk_cmp 0 0 0
DROP TABLE IF EXISTS t_cbrd_26659_rep02ord_chk_cmp;
CREATE TABLE t_cbrd_26659_rep02ord_chk_cmp (id INT PRIMARY KEY, big1 BIT VARYING, big2 BIT VARYING, tag BIT VARYING);
INSERT INTO t_cbrd_26659_rep02ord_chk_cmp VALUES (1, CAST(REPEAT('1', 1800) AS BIT VARYING), CAST(REPEAT('2', 1600) AS BIT VARYING), CAST(REPEAT('3', 600) AS BIT VARYING));
# The payload sum is what makes this a largest-first observation rather than a count: 2024 is
# `big1` moved and 1924 would be `big2`, so an engine that demoted the smaller candidate
# would fail here even though both produce one chunk.
PHASE unequal t_cbrd_26659_rep02ord_chk_uneq 1 1 2024
DROP TABLE IF EXISTS t_cbrd_26659_rep02ord_chk_uneq;
CREATE TABLE t_cbrd_26659_rep02ord_chk_uneq (id INT PRIMARY KEY, big1 BIT VARYING, big2 BIT VARYING, tag BIT VARYING);
INSERT INTO t_cbrd_26659_rep02ord_chk_uneq VALUES (1, CAST(REPEAT('a', 4000) AS BIT VARYING), CAST(REPEAT('b', 3800) AS BIT VARYING), CAST(REPEAT('c', 600) AS BIT VARYING));
# The two candidates are the same size, so the payload sum is 2024 whichever of them the
# tie-break took.  That is exactly why it may be asserted: it carries the count and the size
# without carrying the tie-break, which the normative text does not fix.
PHASE tie t_cbrd_26659_rep02ord_chk_tie 1 1 2024
DROP TABLE IF EXISTS t_cbrd_26659_rep02ord_chk_tie;
CREATE TABLE t_cbrd_26659_rep02ord_chk_tie (id INT PRIMARY KEY, big1 BIT VARYING, big2 BIT VARYING, tag BIT VARYING);
INSERT INTO t_cbrd_26659_rep02ord_chk_tie VALUES (1, CAST(REPEAT('d', 4000) AS BIT VARYING), CAST(REPEAT('e', 4000) AS BIT VARYING), CAST(REPEAT('f', 600) AS BIT VARYING));
PHASE cascade t_cbrd_26659_rep02ord_chk_casc 1 2 4348
DROP TABLE IF EXISTS t_cbrd_26659_rep02ord_chk_casc;
CREATE TABLE t_cbrd_26659_rep02ord_chk_casc (id INT PRIMARY KEY, big1 BIT VARYING, big2 BIT VARYING, big3 BIT VARYING, tag BIT VARYING);
INSERT INTO t_cbrd_26659_rep02ord_chk_casc VALUES (1, CAST(REPEAT('6', 4400) AS BIT VARYING), CAST(REPEAT('7', 4200) AS BIT VARYING), CAST(REPEAT('8', 4000) AS BIT VARYING), CAST(REPEAT('9', 600) AS BIT VARYING));
