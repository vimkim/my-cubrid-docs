#!/usr/bin/env python3
"""Adopt the authoritative hand-set scoping onto ticket 17's matrix rows.

    scope_matrix.py --matrix FILE --authoritative FILE [FILE ...] [--check]

`matrix_merge.py` writes `gap_kind: none` for a new row whose latest outcome is a PASS with
proven OOS-path evidence, and prints "SCOPE TO BE CONFIRMED BY THE AUTHOR" in the summary,
because whether a clause of the requirement is evidenced only by a checker outside every
executed suite is a judgement about the requirement's text that tooling cannot make (ticket 13
report section 8, the qualified rule).

Ticket 17 re-ran cases that tickets 19 and 41 had already scoped by hand, into a matrix of its
own. Left alone, eight of its seventeen rows would read `none` where the authoritative matrices
read `Delivery gap` -- ticket 17 would be claiming, for the same requirement, case and
configuration, coverage that the ticket which wrote the case had explicitly qualified. The
qualification is a property of the requirement and the case, not of the invocation, so this
script copies it rather than letting a re-measurement quietly widen a coverage claim.

It only ever makes a row's claim narrower or equal: a row whose authoritative gap kind is
`none` is left as it is, and a row absent from every authoritative matrix is reported, never
guessed. `--check` exits 1 when any row still disagrees, so the adoption is verifiable after
the fact and not only at the moment it ran.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

NOTE = ("SCOPE ADOPTED by evidence/ticket17/scope_matrix.py from {src} row {row}, which the ticket that "
        "wrote the case set by hand under the qualified rule; ticket 17 re-measured the case and must not "
        "widen its coverage claim. ")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--matrix", required=True)
    ap.add_argument("--authoritative", nargs="+", required=True)
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args(argv)

    auth = {}
    for path in args.authoritative:
        for row in json.loads(Path(path).read_text())["rows"]:
            auth.setdefault(row["row_id"], (path, row))

    matrix = json.loads(Path(args.matrix).read_text())
    changed, missing, disagree = [], [], []
    for row in matrix["rows"]:
        entry = auth.get(row["row_id"])
        if entry is None:
            missing.append(row["row_id"])
            continue
        src, ref = entry
        want = ref["finding"]["gap_kind"]
        if row["finding"]["gap_kind"] == want:
            continue
        if args.check:
            disagree.append(f"{row['row_id']}: {row['finding']['gap_kind']!r} here, {want!r} in {src}")
            continue
        row["finding"]["gap_kind"] = want
        if ref.get("attribution", {}).get("target") not in (None, "unknown"):
            row["attribution"] = json.loads(json.dumps(ref["attribution"]))
        row["finding"]["summary"] = NOTE.format(src=src, row=ref["row_id"]) + row["finding"]["summary"]
        changed.append(f"{row['row_id']} -> {want} (from {src})")

    for r in missing:
        print(f"UNSCOPED: {r} appears in no authoritative matrix; its gap kind is the merge's own", file=sys.stderr)
    if args.check:
        for d in disagree:
            print("DISAGREES: " + d)
        print(f"[scope_matrix] {len(matrix['rows'])} row(s), {len(disagree)} disagreement(s), {len(missing)} unscoped")
        return 1 if disagree else 0

    Path(args.matrix).write_text(json.dumps(matrix, indent=2) + "\n")
    for c in changed:
        print("  " + c)
    print(f"[scope_matrix] {len(changed)} row(s) narrowed, {len(missing)} unscoped, {len(matrix['rows'])} total")
    return 0


if __name__ == "__main__":
    sys.exit(main())
