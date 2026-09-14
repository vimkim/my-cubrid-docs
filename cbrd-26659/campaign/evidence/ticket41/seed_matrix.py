#!/usr/bin/env python3
"""Seed the ticket 41 coverage matrix from the recorded ticket 13 and ticket 14 matrices.

    python3 evidence/ticket41/seed_matrix.py --out evidence/ticket41/matrix-seed.json

`matrix_merge.py` merges manifests into ONE existing matrix, and the campaign's recorded rows
live in two: ticket 13's seven (three case rows and four hand-maintained caseless ones) and
ticket 14's three (two case rows and the withdrawn `OOS-REP-07` claim). Re-merging ticket 14's
manifests into ticket 13's matrix would regenerate ticket 14's rows and drop its hand-written
caseless row, which is the erasure ticket 41 forbids. This takes the union instead: every row
verbatim, in order, with the two source matrices left untouched.

The one edit, and it is a hand act on hand-owned rows in a NEW record: each caseless row gains
`hand_maintained: true` (ticket 36 item 6), the field that replaced recognition by row id. The
recorded matrices keep their rows exactly as recorded; only this seed carries the field.

Refuses on a row-id collision, a differing catalogue or any accepted exclusion, none of which
the union could resolve mechanically.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

CAMPAIGN = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(CAMPAIGN / "tools"))
from campaign_records import load_json, now_iso, write_record  # noqa: E402

SOURCES = [CAMPAIGN / "evidence" / "ticket13" / "matrix.json",
           CAMPAIGN / "evidence" / "ticket14" / "matrix.json"]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", required=True)
    args = ap.parse_args(argv)

    matrices = [load_json(p) for p in SOURCES]
    catalogues = {m["catalogue"]["hash"] for m in matrices}
    if len(catalogues) != 1:
        print(f"[seed_matrix] REFUSED: the sources cite different catalogues: {catalogues}", file=sys.stderr)
        return 2
    rows, seen, hand = [], set(), 0
    for m, src in zip(matrices, SOURCES):
        if m.get("accepted_exclusions"):
            print(f"[seed_matrix] REFUSED: {src} carries accepted exclusions; only the user merges those", file=sys.stderr)
            return 2
        for row in m["rows"]:
            if row["row_id"] in seen:
                print(f"[seed_matrix] REFUSED: row id {row['row_id']} appears in both sources", file=sys.stderr)
                return 2
            seen.add(row["row_id"])
            row = dict(row)
            if row.get("case") is None or row.get("configuration") is None:
                row["hand_maintained"] = True
                hand += 1
            rows.append(row)
    seed = {"schema_version": 1, "generated_at": now_iso(), "catalogue": matrices[0]["catalogue"],
            "rows": rows, "accepted_exclusions": []}
    write_record(seed, "matrix", args.out)
    print(f"[seed_matrix] {len(rows)} row(s) from {len(SOURCES)} matrices ({hand} caseless rows given "
          f"hand_maintained: true); wrote {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
