# CBRD-26659 ticket 18 activation spec for cbrd_26659_oos_rep09_null_empty.
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

PHASE comparator t_cbrd_26659_rep09_chk_cmp 0 0 0
DROP TABLE IF EXISTS t_cbrd_26659_rep09_chk_cmp;
CREATE TABLE t_cbrd_26659_rep09_chk_cmp (id INT PRIMARY KEY, payload BIT VARYING, nullable BIT VARYING, empty BIT VARYING, tag BIT VARYING);
INSERT INTO t_cbrd_26659_rep09_chk_cmp VALUES (1, CAST(REPEAT('1', 6000) AS BIT VARYING), NULL, CAST('' AS BIT VARYING), CAST(REPEAT('2', 600) AS BIT VARYING));
# One chunk, not three: the NULL column and the zero-length column are not candidates, so only
# `payload` moved.  A count of two or three here would be the finding.
PHASE oosbacked t_cbrd_26659_rep09_chk_oos 1 1 4224
DROP TABLE IF EXISTS t_cbrd_26659_rep09_chk_oos;
CREATE TABLE t_cbrd_26659_rep09_chk_oos (id INT PRIMARY KEY, payload BIT VARYING, nullable BIT VARYING, empty BIT VARYING, tag BIT VARYING);
INSERT INTO t_cbrd_26659_rep09_chk_oos VALUES (1, CAST(REPEAT('a', 8400) AS BIT VARYING), NULL, CAST('' AS BIT VARYING), CAST(REPEAT('b', 600) AS BIT VARYING));
# After the OOS-backed column is set to NULL.  At this revision an UPDATE allocates fresh chains
# and the dead ones stay until vacuum (OOS-SQL-03, observation-only), and when the new value is
# NULL there is no new chain at all -- so what remains here is a background question, not a
# requirement.  Observed.
PHASE updated_to_null t_cbrd_26659_rep09_chk_oos - - -
UPDATE t_cbrd_26659_rep09_chk_oos SET payload = NULL WHERE id = 1;
