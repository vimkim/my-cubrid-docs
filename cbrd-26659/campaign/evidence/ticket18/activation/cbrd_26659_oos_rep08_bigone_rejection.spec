# CBRD-26659 ticket 18 activation spec for cbrd_26659_oos_rep08_bigone_rejection.
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

PHASE comparator t_cbrd_26659_rep08_chk_cmp 0 0 0
DROP TABLE IF EXISTS t_cbrd_26659_rep08_chk_cmp;
CREATE TABLE t_cbrd_26659_rep08_chk_cmp (id INT PRIMARY KEY, filler BIT(800), v BIT VARYING);
INSERT INTO t_cbrd_26659_rep08_chk_cmp VALUES (1, CAST(REPEAT('1', 200) AS BIT(800)), CAST(REPEAT('2', 128) AS BIT VARYING));
PHASE accepted t_cbrd_26659_rep08_chk_ok 1 1 88
DROP TABLE IF EXISTS t_cbrd_26659_rep08_chk_ok;
CREATE TABLE t_cbrd_26659_rep08_chk_ok (id INT PRIMARY KEY, filler BIT(129344), v BIT VARYING);
INSERT INTO t_cbrd_26659_rep08_chk_ok VALUES (1, CAST(REPEAT('a', 32336) AS BIT(129344)), CAST(REPEAT('b', 128) AS BIT VARYING));
# The rejected INSERT.  OOS-REP-08 says the rejection happens BEFORE any chunk is written, so
# the assertion is that the class still has no OOS file at all -- not merely that the row is
# absent, which the case itself shows.  csql continues past the error, which is what lets the
# SHOW HEAP OOS after it run.
PHASE rejected t_cbrd_26659_rep08_chk_rej 0 0 0
DROP TABLE IF EXISTS t_cbrd_26659_rep08_chk_rej;
CREATE TABLE t_cbrd_26659_rep08_chk_rej (id INT PRIMARY KEY, filler BIT(129416), v BIT VARYING);
INSERT INTO t_cbrd_26659_rep08_chk_rej VALUES (1, CAST(REPEAT('c', 32354) AS BIT(129416)), CAST(REPEAT('d', 128) AS BIT VARYING));
# The non-OOS neighbour: a record above the same threshold whose only variable value is below
# both eligibility floors.  Nothing is demoted, so nothing is rejected and no OOS file exists.
PHASE nonoos_bigone t_cbrd_26659_rep08_chk_big 0 0 0
DROP TABLE IF EXISTS t_cbrd_26659_rep08_chk_big;
CREATE TABLE t_cbrd_26659_rep08_chk_big (id INT PRIMARY KEY, filler BIT(160000), s BIT VARYING);
INSERT INTO t_cbrd_26659_rep08_chk_big VALUES (1, CAST(REPEAT('e', 40000) AS BIT(160000)), CAST(REPEAT('f', 20) AS BIT VARYING));
