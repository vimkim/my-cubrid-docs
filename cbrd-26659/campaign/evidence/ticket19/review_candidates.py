#!/usr/bin/env python3
"""Review ticket 19's candidate .result files against the pre-run oracle, before promotion.

    review_candidates.py --bundle <bundle dir> [--strict]

The campaign forbids promoting a CTP first-run result because it exists: "The first `.result`
is a candidate; review it against the requirement, then promote by rename."  This is that
review, done against values derived without the engine rather than by eye:

  1. every `*_ok` boolean equality flag in every result table is 1 -- a 0 is a failure;
  2. every (OCTET_LENGTH, MD5) pair the results print is a pair the derivation predicts.  The
     digest table comes from `gen_ticket19_cases.py --oracle`, which computes md5 of the
     literal's own hexadecimal form in Python; a digest the engine produced that is not in that
     table means the engine returned a value the case did not write;
  3. every length column agrees with the digest beside it, so a truncated value whose digest
     happened to collide with another literal's would still be caught;
  4. the specific scalars the oracle names -- aggregate totals, row counts, error identities --
     appear exactly as expected;
  5. no unexpected `Error:` line appears anywhere.

Exit 0 only when every case passes every check.  Nothing here writes into the bundle or the
testcase repository.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gen_ticket19_cases as g  # noqa: E402
import derive_ticket19_sizes as d  # noqa: E402

MD5_RE = re.compile(r"\b[0-9a-f]{32}\b")
ERROR_RE = re.compile(r"^Error:(-?\d+)\s*$")

# The oracle's named scalars, section by section.  Each entry is a substring that must occur in
# the case's result text, with the section of expected-oracle.md that justifies it.
EXPECTED_SCALARS = {
    "cbrd_26659_oos_sql01_insert_select": [
        ("1000     1     1000", "S3 TEST 4: helper is exactly 1..1000"),
        ("100     100     100     100     455350     4207     4900     100",
         "S3 TEST 5: bulk-100 aggregate"),
        ("1000     1000     1000     1000     4147025     4100     4196     1000",
         "S3 TEST 6: bulk-1000 aggregate"),
        ("100     100     100     100", "S3 TEST 7: INSERT ... SELECT copied all 100 rows"),
        ("2     2     0", "S3 TEST 3: two rows, both exact, none aliased"),
    ],
    "cbrd_26659_oos_sql02_update": [
        ("2     2     0     2", "S4 TEST 10: two rows carrying the source value, none aliased"),
    ],
    "cbrd_26659_oos_sql05_delete": [
        ("4     4     4     0", "S5 TEST 7: four re-inserted rows, all exact and distinct"),
    ],
    "cbrd_26659_oos_sql06_constraints": [
        ("2     2     2", "S7 TEST 6: the table is exactly the fixture after every failure"),
    ],
    "cbrd_26659_oos_sql06_triggers": [
        ("2     2", "S8 TEST 5: two rows, two distinct payloads, after the rejected UPDATE"),
    ],
    "cbrd_26659_oos_sql02_mixed_chunks": [
        ("2     0     2", "S10 TEST 4: two rows, no aliasing, two distinct multi-chunk values"),
    ],
}

# Error identities the oracle derived from the pinned engine before it was run.
EXPECTED_ERRORS = {
    "cbrd_26659_oos_sql06_constraints": [-670, -670, -631, -670],
    "cbrd_26659_oos_sql06_triggers": [-517],
}


# Ticket 13's tracer-bullet case shares the scenario directory, so this invocation executes it
# too.  Its literals are not ticket 19's, and its answer was promoted and independently
# reviewed long ago; they are listed here so the review covers every result the run produced
# rather than skipping the one case it does not own.
TICKET13_LITERALS = [("a", 3000), ("b", 1200), ("c", 1000), ("d", 500)]


def literal_table():
    """(octet_length, md5) -> the literal that produces it, from the derivation alone.

    Covers the explicit literals the cases write, the values the two generated bulk groups
    produce (which are SQL expressions, not literals, and so never pass through `val()`), and
    ticket 13's four literals.
    """
    for fn in g.CASES:
        fn()
    for fn in g.SPECS:
        fn()
    table = {}
    for char, n in list(g._values) + TICKET13_LITERALS:
        table[(n, d.md5_of(char, n))] = f"REPEAT('{char}', {2 * n})"
    for group in (d.BULK_100, d.BULK_1000):
        for i in group.ids():
            char, n = group.char(i), group.size(i)
            table[(n, d.md5_of(char, n))] = f"{group.name} row {i}"
    return table


def parse_tables(text):
    """Yield (header_cells, [row_cells]) for every result table in a CTP .result file."""
    blocks = text.split("=" * 51)
    for b in blocks:
        lines = [l for l in b.splitlines() if l.strip()]
        if not lines:
            continue
        header = lines[0].split()
        if not any(h.endswith("_ok") or h.endswith("_md5") or h.endswith("_octets")
                   or h.endswith("_len") or h.startswith("n_") or h == "id" for h in header):
            continue
        rows = [l.split() for l in lines[1:]]
        yield header, rows


def review(case, text, table):
    problems = []

    # 1 + 3: every equality flag is 1, and every (length, digest) pair is one we predicted
    for header, rows in parse_tables(text):
        idx = {h: i for i, h in enumerate(header)}
        for row in rows:
            if len(row) < len(header):
                continue
            for h, i in idx.items():
                if h.endswith("_ok") and row[i] != "1":
                    problems.append(f"{case}: column {h} is {row[i]}, not 1 (row {row[:1]})")
            for h, i in idx.items():
                if not h.endswith("_md5"):
                    continue
                digest = row[i]
                if not MD5_RE.fullmatch(digest):
                    continue
                # Pair the digest with ITS OWN length column when the table has one.  Falling
                # back to any other length column would compare a tag's digest against a
                # payload's length and report a difference that is not there.
                prefix = h[: -len("_md5")]
                len_col = next((c for c in (f"{prefix}_octets", f"{prefix}_len")
                                if c in idx), None)
                if len_col is None:
                    if not any(k[1] == digest for k in table):
                        problems.append(f"{case}: digest {digest} in {h} is not produced by any "
                                        "value the derivation predicts")
                    continue
                n = int(row[idx[len_col]])
                if (n, digest) not in table:
                    problems.append(f"{case}: ({n} B, {digest}) in {h} is not a "
                                    "(length, digest) pair the derivation predicts")

    # 2: no unexpected errors; 4: the expected ones, in order
    got_errors = [int(m.group(1)) for line in text.splitlines()
                  if (m := ERROR_RE.match(line.strip()))]
    want_errors = EXPECTED_ERRORS.get(case, [])
    if got_errors != want_errors:
        problems.append(f"{case}: error identities {got_errors}, expected {want_errors}")

    # 5: the oracle's named scalars
    for needle, why in EXPECTED_SCALARS.get(case, []):
        if needle not in text:
            problems.append(f"{case}: expected scalars not found ({why}): '{needle}'")

    return problems


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bundle", type=Path, required=True)
    args = ap.parse_args()

    table = literal_table()
    results = sorted((args.bundle / "actual").glob("*.result"))
    if not results:
        one = args.bundle / "actual.result"
        results = [one] if one.exists() else []
    if not results:
        print(f"no candidate .result under {args.bundle}")
        return 2

    print(f"# Candidate review against the pre-run oracle ({len(table)} predicted "
          f"(length, digest) pairs)\n")
    total = 0
    for r in results:
        case = r.stem
        problems = review(case, r.read_text(errors="replace"), table)
        total += len(problems)
        flags = sum(1 for _h, rows in parse_tables(r.read_text(errors="replace")) for _r in rows)
        print(f"{'OK  ' if not problems else 'FAIL'}  {case:<44} "
              f"{len(r.read_text().splitlines()):>5} lines, {flags:>4} result rows")
        for p in problems:
            print(f"        {p}")
    print(f"\nRESULT: {'every candidate matches the oracle' if total == 0 else f'{total} problem(s)'}")
    return 0 if total == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
