# CBRD-26659 ticket 19 activation spec for cbrd_26659_oos_rep06_lob_neighbours.
# Generated with the case itself by evidence/ticket19/gen_ticket19_cases.py; run by
# tools/activation_check_spec.sh, client-server, under campaign_ns.sh (user decision O2,
# ticket 35).  PHASE <tag> <table> <has_oos> <num_recs> <sumlen>; `-` observes instead of
# asserting.  Every asserted figure is derived, never measured: see derivation-output.txt.

PHASE create t_cbrd_26659_rep06_lob 0 0 0
DROP TABLE IF EXISTS t_cbrd_26659_rep06_lob;
CREATE TABLE t_cbrd_26659_rep06_lob (id INT PRIMARY KEY, payload BIT VARYING, tag BIT VARYING,
                  b1 BLOB, b2 BLOB, b3 BLOB, b4 BLOB, c1 CLOB);
# One chunk holding the 4200 B payload: the five locator strings are eligible but far too short
# to be the largest candidate, so the largest-first loop stops after `payload` (ADR-0002).
PHASE oosbacked t_cbrd_26659_rep06_lob 1 1 4224
INSERT INTO t_cbrd_26659_rep06_lob VALUES (1, CAST(REPEAT('a', 8400) AS BIT VARYING), CAST(REPEAT('b', 600) AS BIT VARYING),
                        BIT_TO_BLOB(CAST(REPEAT('a1', 64) AS BIT VARYING)), BIT_TO_BLOB(CAST(REPEAT('b2', 64) AS BIT VARYING)), BIT_TO_BLOB(CAST(REPEAT('c3', 64) AS BIT VARYING)), BIT_TO_BLOB(CAST(REPEAT('d4', 64) AS BIT VARYING)), CHAR_TO_CLOB('cbrd-26659-oos-clob-neighbour-1'));
INSERT INTO t_cbrd_26659_rep06_lob VALUES (2, CAST(REPEAT('c', 6000) AS BIT VARYING), CAST(REPEAT('d', 600) AS BIT VARYING),
                        BIT_TO_BLOB(CAST(REPEAT('a1', 64) AS BIT VARYING)), BIT_TO_BLOB(CAST(REPEAT('b2', 64) AS BIT VARYING)), BIT_TO_BLOB(CAST(REPEAT('c3', 64) AS BIT VARYING)), BIT_TO_BLOB(CAST(REPEAT('d4', 64) AS BIT VARYING)), CHAR_TO_CLOB('cbrd-26659-oos-clob-neighbour-2'));
# The copy, on the INSERT ... SELECT path, carrying five locators with it.  One chunk, because
# only row 1 is above the gate; the locators are eligible but far too short to be the largest
# candidate beside a 4200 B payload.
PHASE copy t_cbrd_26659_rep06_lob_copy 1 1 4224
DROP TABLE IF EXISTS t_cbrd_26659_rep06_lob_copy;
CREATE TABLE t_cbrd_26659_rep06_lob_copy (id INT PRIMARY KEY, payload BIT VARYING, tag BIT VARYING,
                   b1 BLOB, b2 BLOB, b3 BLOB, b4 BLOB, c1 CLOB);
INSERT INTO t_cbrd_26659_rep06_lob_copy SELECT id, payload, tag, b1, b2, b3, b4, c1 FROM t_cbrd_26659_rep06_lob;
