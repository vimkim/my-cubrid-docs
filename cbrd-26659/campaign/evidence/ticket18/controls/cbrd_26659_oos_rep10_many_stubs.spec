# CBRD-26659 ticket 18 activation spec for cbrd_26659_oos_rep10_many_stubs.
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

PHASE comparator t_cbrd_26659_rep10_chk_cmp 0 0 0
DROP TABLE IF EXISTS t_cbrd_26659_rep10_chk_cmp;
CREATE TABLE t_cbrd_26659_rep10_chk_cmp (id INT PRIMARY KEY, v01 BIT VARYING, v02 BIT VARYING, v03 BIT VARYING, v04 BIT VARYING, v05 BIT VARYING, v06 BIT VARYING, v07 BIT VARYING, v08 BIT VARYING, v09 BIT VARYING, v10 BIT VARYING, v11 BIT VARYING, v12 BIT VARYING, v13 BIT VARYING, v14 BIT VARYING, v15 BIT VARYING, v16 BIT VARYING, v17 BIT VARYING, v18 BIT VARYING);
INSERT INTO t_cbrd_26659_rep10_chk_cmp VALUES (1, CAST(REPEAT('4', 60) AS BIT VARYING), CAST(REPEAT('5', 60) AS BIT VARYING), CAST(REPEAT('6', 60) AS BIT VARYING), CAST(REPEAT('7', 60) AS BIT VARYING), CAST(REPEAT('8', 60) AS BIT VARYING), CAST(REPEAT('9', 60) AS BIT VARYING), CAST(REPEAT('a', 60) AS BIT VARYING), CAST(REPEAT('b', 60) AS BIT VARYING), CAST(REPEAT('c', 60) AS BIT VARYING), CAST(REPEAT('d', 60) AS BIT VARYING), CAST(REPEAT('e', 60) AS BIT VARYING), CAST(REPEAT('f', 60) AS BIT VARYING), CAST(REPEAT('1', 60) AS BIT VARYING), CAST(REPEAT('2', 60) AS BIT VARYING), CAST(REPEAT('3', 60) AS BIT VARYING), CAST(REPEAT('4', 60) AS BIT VARYING), CAST(REPEAT('5', 60) AS BIT VARYING), CAST(REPEAT('6', 60) AS BIT VARYING));
# 12 chunks from one record.  The sizes are all different, so the payload sum names WHICH
# 12 of the 18 columns moved and not only how many: a loop that took them in any other
# order would reach a different sum.
PHASE wide t_cbrd_26659_rep10_chk_wide 1 11 8016
DROP TABLE IF EXISTS t_cbrd_26659_rep10_chk_wide;
CREATE TABLE t_cbrd_26659_rep10_chk_wide (id INT PRIMARY KEY, v01 BIT VARYING, v02 BIT VARYING, v03 BIT VARYING, v04 BIT VARYING, v05 BIT VARYING, v06 BIT VARYING, v07 BIT VARYING, v08 BIT VARYING, v09 BIT VARYING, v10 BIT VARYING, v11 BIT VARYING, v12 BIT VARYING, v13 BIT VARYING, v14 BIT VARYING, v15 BIT VARYING, v16 BIT VARYING, v17 BIT VARYING, v18 BIT VARYING);
INSERT INTO t_cbrd_26659_rep10_chk_wide VALUES (1, CAST(REPEAT('1', 1400) AS BIT VARYING), CAST(REPEAT('2', 1380) AS BIT VARYING), CAST(REPEAT('3', 1360) AS BIT VARYING), CAST(REPEAT('4', 1340) AS BIT VARYING), CAST(REPEAT('5', 1320) AS BIT VARYING), CAST(REPEAT('6', 1300) AS BIT VARYING), CAST(REPEAT('7', 1280) AS BIT VARYING), CAST(REPEAT('8', 1260) AS BIT VARYING), CAST(REPEAT('9', 1240) AS BIT VARYING), CAST(REPEAT('a', 1220) AS BIT VARYING), CAST(REPEAT('b', 1200) AS BIT VARYING), CAST(REPEAT('c', 1180) AS BIT VARYING), CAST(REPEAT('d', 1160) AS BIT VARYING), CAST(REPEAT('e', 1140) AS BIT VARYING), CAST(REPEAT('f', 1120) AS BIT VARYING), CAST(REPEAT('1', 1100) AS BIT VARYING), CAST(REPEAT('2', 1080) AS BIT VARYING), CAST(REPEAT('3', 1060) AS BIT VARYING));
