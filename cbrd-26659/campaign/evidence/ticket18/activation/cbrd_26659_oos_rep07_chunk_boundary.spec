# CBRD-26659 ticket 18 activation spec for cbrd_26659_oos_rep07_chunk_boundary.
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

PHASE comparator t_cbrd_26659_rep07_chk_cmp 0 0 0
DROP TABLE IF EXISTS t_cbrd_26659_rep07_chk_cmp;
CREATE TABLE t_cbrd_26659_rep07_chk_cmp (id INT PRIMARY KEY, payload BIT VARYING, tag BIT VARYING);
INSERT INTO t_cbrd_26659_rep07_chk_cmp VALUES (1, CAST(REPEAT('1', 6000) AS BIT VARYING), CAST(REPEAT('2', 600) AS BIT VARYING));
PHASE one_chunk t_cbrd_26659_rep07_chk_one 1 1 16296
DROP TABLE IF EXISTS t_cbrd_26659_rep07_chk_one;
CREATE TABLE t_cbrd_26659_rep07_chk_one (id INT PRIMARY KEY, payload BIT VARYING, tag BIT VARYING);
INSERT INTO t_cbrd_26659_rep07_chk_one VALUES (1, CAST(REPEAT('a', 32550) AS BIT VARYING), CAST(REPEAT('b', 600) AS BIT VARYING));
PHASE two_chunks t_cbrd_26659_rep07_chk_two 1 2 16324
DROP TABLE IF EXISTS t_cbrd_26659_rep07_chk_two;
CREATE TABLE t_cbrd_26659_rep07_chk_two (id INT PRIMARY KEY, payload BIT VARYING, tag BIT VARYING);
INSERT INTO t_cbrd_26659_rep07_chk_two VALUES (1, CAST(REPEAT('c', 32568) AS BIT VARYING), CAST(REPEAT('d', 600) AS BIT VARYING));
PHASE three_chunks t_cbrd_26659_rep07_chk_three 1 3 32632
DROP TABLE IF EXISTS t_cbrd_26659_rep07_chk_three;
CREATE TABLE t_cbrd_26659_rep07_chk_three (id INT PRIMARY KEY, payload BIT VARYING, tag BIT VARYING);
INSERT INTO t_cbrd_26659_rep07_chk_three VALUES (1, CAST(REPEAT('e', 65152) AS BIT VARYING), CAST(REPEAT('f', 600) AS BIT VARYING));
