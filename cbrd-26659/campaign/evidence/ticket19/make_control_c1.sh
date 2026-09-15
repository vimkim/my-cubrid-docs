#!/usr/bin/env bash
# CBRD-26659 ticket 19 -- build negative control C1's scenario, with two defects planted.
#
#   make_control_c1.sh [scenario-dir]        default: $CAMPAIGN_TICKET_ROOT/controls/c1
#
# The control proves two checking mechanisms detect a defect they are supposed to detect:
#   (a) the CTP comparison -- one hex digit of the multi-chunk value's digest is changed in a
#       COPY of the promoted answer;
#   (b) the spec-driven activation checker -- the expected chunk-payload sum for row 1 is one
#       byte wrong in evidence/ticket19/controls/<case>.spec, which is checked in.
# Both must fail.  Neither defect is ever written into the testcase repository: this script only
# ever reads from it.
set -eu
CASE=cbrd_26659_oos_sql02_mixed_chunks
SRC=${SRC:-/home/vimkim/gh/tc/cubrid-testcases-cbrd-26659/sql/_36_guava/cbrd_26659}
OUT=${1:-${CAMPAIGN_TICKET_ROOT:-/home/vimkim/.cub/campaign/cbrd-26659/ticket19}/controls/c1}

rm -rf "$OUT"
mkdir -p "$OUT/cases" "$OUT/answers"
cp "$SRC/cases/$CASE.sql" "$OUT/cases/"
cp "$SRC/answers/$CASE.answer" "$OUT/answers/"

# The digest of the 20000 B value, with its last hex digit changed.  Located by the length
# column beside it rather than by a literal, so a re-promotion that changes the digest does not
# silently turn this into a no-op.
python3 - "$OUT/answers/$CASE.answer" <<'PY'
import pathlib, re, sys
p = pathlib.Path(sys.argv[1]); lines = p.read_text().splitlines()
for i, line in enumerate(lines):
    if "multi1_md5" not in line:
        continue
    header = line.split()
    col = header.index("multi1_md5")
    row = lines[i + 1].split()
    digest = row[col]
    assert re.fullmatch(r"[0-9a-f]{32}", digest), digest
    flipped = digest[:-1] + ("0" if digest[-1] != "0" else "1")
    lines[i + 1] = lines[i + 1].replace(digest, flipped, 1)
    p.write_text("\n".join(lines) + "\n")
    print(f"planted: multi1_md5 {digest} -> {flipped} in the first result row")
    break
else:
    raise SystemExit("no multi1_md5 column found; the answer format changed")
PY
echo "control scenario at $OUT"
