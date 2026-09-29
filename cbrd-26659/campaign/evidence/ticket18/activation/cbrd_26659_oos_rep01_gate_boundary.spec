# CBRD-26659 ticket 18 activation spec for cbrd_26659_oos_rep01_gate_boundary.
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

PHASE inline t_cbrd_26659_rep01_chk_inline 0 0 0
DROP TABLE IF EXISTS t_cbrd_26659_rep01_chk_inline;
CREATE TABLE t_cbrd_26659_rep01_chk_inline (id INT PRIMARY KEY, payload BIT VARYING, tag BIT VARYING);
INSERT INTO t_cbrd_26659_rep01_chk_inline VALUES (1, CAST(REPEAT('a', 7398) AS BIT VARYING), CAST(REPEAT('b', 600) AS BIT VARYING));
PHASE oosbacked t_cbrd_26659_rep01_chk_oos 1 1 3748
DROP TABLE IF EXISTS t_cbrd_26659_rep01_chk_oos;
CREATE TABLE t_cbrd_26659_rep01_chk_oos (id INT PRIMARY KEY, payload BIT VARYING, tag BIT VARYING);
INSERT INTO t_cbrd_26659_rep01_chk_oos VALUES (1, CAST(REPEAT('c', 7448) AS BIT VARYING), CAST(REPEAT('d', 600) AS BIT VARYING));
# The two band rows.  The four-record physical target accepted in CBRD-27057 puts the gate at
# 4060 B and would demote both of these; the pinned engine compares against DB_PAGESIZE/4 = 4086 B
# and keeps them inline, which is the conformance gap OOS-REP-03 records.  The pinned engine's
# answer must not become the expectation, and the accepted design's must not be asserted at an
# engine that does not implement it, so both are OBSERVED.  Expected under the accepted target:
# Has_oos_file 1, Oos_num_recs 1, Oos_recs_sumlen 3724 and 3744 respectively.
PHASE band_low t_cbrd_26659_rep01_chk_band_lo - - -
DROP TABLE IF EXISTS t_cbrd_26659_rep01_chk_band_lo;
CREATE TABLE t_cbrd_26659_rep01_chk_band_lo (id INT PRIMARY KEY, payload BIT VARYING, tag BIT VARYING);
INSERT INTO t_cbrd_26659_rep01_chk_band_lo VALUES (1, CAST(REPEAT('e', 7400) AS BIT VARYING), CAST(REPEAT('f', 600) AS BIT VARYING));
PHASE band_high t_cbrd_26659_rep01_chk_band_hi - - -
DROP TABLE IF EXISTS t_cbrd_26659_rep01_chk_band_hi;
CREATE TABLE t_cbrd_26659_rep01_chk_band_hi (id INT PRIMARY KEY, payload BIT VARYING, tag BIT VARYING);
INSERT INTO t_cbrd_26659_rep01_chk_band_hi VALUES (1, CAST(REPEAT('9', 7446) AS BIT VARYING), CAST(REPEAT('8', 600) AS BIT VARYING));
