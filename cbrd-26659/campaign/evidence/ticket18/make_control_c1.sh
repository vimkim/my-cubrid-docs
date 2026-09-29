#!/usr/bin/env bash
# CBRD-26659 ticket 18 -- build negative control C1's scenario, with two defects planted.
#
#   make_control_c1.sh [scenario-dir]        default: $CAMPAIGN_TICKET_ROOT/controls/c1
#
# The control proves two checking mechanisms detect a defect they are supposed to detect:
#   (a) the CTP comparison -- one hex digit of the eighteen-column record's LAST column digest
#       is changed in a COPY of the promoted answer.  The last column is deliberate: it is one
#       of the six that stay INLINE, so a comparison that only looked at demoted values would
#       pass;
#   (b) the spec-driven activation checker -- the expected chunk count for that record is 11
#       instead of 12 in evidence/ticket18/controls/<case>.spec, which is checked in.
# Both must fail.  Neither defect is ever written into the testcase repository: this script only
# ever reads from it.
set -eu
CASE=cbrd_26659_oos_rep10_many_stubs
SRC=${SRC:-/home/vimkim/gh/tc/cubrid-testcases-cbrd-26659/sql/_36_guava/cbrd_26659}
OUT=${1:-${CAMPAIGN_TICKET_ROOT:-/home/vimkim/.cub/campaign/cbrd-26659/ticket18}/controls/c1}

rm -rf "$OUT"
mkdir -p "$OUT/cases" "$OUT/answers"
cp "$SRC/cases/$CASE.sql" "$OUT/cases/"
cp "$SRC/answers/$CASE.answer" "$OUT/answers/"

# The digest of the last column of the wide record, with its last hex digit changed.  Located by
# the `name` column beside it rather than by a literal, so a re-promotion that changes the digest
# does not silently turn this into a no-op.
python3 - "$OUT/answers/$CASE.answer" <<'PY'
import pathlib, re, sys
p = pathlib.Path(sys.argv[1]); lines = p.read_text().splitlines()
target = None
for i, line in enumerate(lines):
    cells = line.split()
    if len(cells) < 5 or cells[0] != "col" or "name" not in cells or "digest" not in cells:
        continue
    name_col, digest_col = cells.index("name"), cells.index("digest")
    for j in range(i + 1, len(lines)):
        row = lines[j].split()
        if len(row) <= digest_col:
            break
        if row[name_col].strip("'") == "v18":
            target = (j, row[digest_col])
            break
    if target:
        break
if not target:
    raise SystemExit("no v18 digest row found; the answer format changed")
j, digest = target
assert re.fullmatch(r"[0-9a-f]{32}", digest), digest
flipped = digest[:-1] + ("0" if digest[-1] != "0" else "1")
lines[j] = lines[j].replace(digest, flipped, 1)
p.write_text("\n".join(lines) + "\n")
print(f"planted: v18 digest {digest} -> {flipped} (an INLINE column of the wide record)")
PY
echo "control scenario at $OUT"
