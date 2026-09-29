# CBRD-26659 ticket 18 activation spec for cbrd_26659_oos_rep13_placement_hints.
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

# Every figure in this spec is OBSERVED.  Whether STORAGE PREFER_INLINE ordering and the
# STORAGE FORCE_OUTLINE gate bypass are required behaviour is undecided (OOS-REP-13, BLOCKED),
# so there is no expectation to assert and the engine's answer must not become one.  What the
# observation is for is that a merge reviewer can see what this revision does.
#
# At this revision, from the source: FORCE_OUTLINE demotes any non-NULL variable value larger
# than the inline stub before the record gate is consulted at all, so the 40 B value below is
# expected to be moved out of a record far under the gate; PREFER_INLINE sinks its column to the
# tail of the candidate list, so the 2000 B hinted column is expected to stay inline while the
# 1900 B one moves; and PREFER_OUTLINE is an alias of DEFAULT in the parse tree, so the third
# table is expected to behave exactly like an unhinted one.
PHASE force_outline t_cbrd_26659_rep13_chk_force - - -
DROP TABLE IF EXISTS t_cbrd_26659_rep13_chk_force;
CREATE TABLE t_cbrd_26659_rep13_chk_force (id INT PRIMARY KEY, hinted BIT VARYING STORAGE FORCE_OUTLINE, tag BIT VARYING);
INSERT INTO t_cbrd_26659_rep13_chk_force VALUES (1, CAST(REPEAT('a', 80) AS BIT VARYING), CAST(REPEAT('b', 600) AS BIT VARYING));
PHASE prefer_inline t_cbrd_26659_rep13_chk_prefer - - -
DROP TABLE IF EXISTS t_cbrd_26659_rep13_chk_prefer;
CREATE TABLE t_cbrd_26659_rep13_chk_prefer (id INT PRIMARY KEY, hinted BIT VARYING STORAGE PREFER_INLINE, other BIT VARYING, tag BIT VARYING);
INSERT INTO t_cbrd_26659_rep13_chk_prefer VALUES (1, CAST(REPEAT('c', 4000) AS BIT VARYING), CAST(REPEAT('d', 3800) AS BIT VARYING), CAST(REPEAT('e', 600) AS BIT VARYING));
PHASE prefer_outline t_cbrd_26659_rep13_chk_alias - - -
DROP TABLE IF EXISTS t_cbrd_26659_rep13_chk_alias;
CREATE TABLE t_cbrd_26659_rep13_chk_alias (id INT PRIMARY KEY, hinted BIT VARYING STORAGE PREFER_OUTLINE, other BIT VARYING, tag BIT VARYING);
INSERT INTO t_cbrd_26659_rep13_chk_alias VALUES (1, CAST(REPEAT('f', 4000) AS BIT VARYING), CAST(REPEAT('9', 3800) AS BIT VARYING), CAST(REPEAT('8', 600) AS BIT VARYING));
PHASE default_control t_cbrd_26659_rep13_chk_default - - -
DROP TABLE IF EXISTS t_cbrd_26659_rep13_chk_default;
CREATE TABLE t_cbrd_26659_rep13_chk_default (id INT PRIMARY KEY, hinted BIT VARYING, other BIT VARYING, tag BIT VARYING);
INSERT INTO t_cbrd_26659_rep13_chk_default VALUES (1, CAST(REPEAT('7', 4000) AS BIT VARYING), CAST(REPEAT('6', 3800) AS BIT VARYING), CAST(REPEAT('5', 600) AS BIT VARYING));
