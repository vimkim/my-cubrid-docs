#!/usr/bin/env python3
"""Review ticket 18's candidate .result files against the pre-run oracle, before promotion.

    review_candidates.py --bundle <bundle dir> [--only-ticket18]

The campaign forbids promoting a CTP first-run result because it exists: "The first `.result`
is a candidate; review it against the requirement, then promote by rename."  This is that
review, done against values derived without the engine rather than by eye.  It follows ticket
19's `review_candidates.py` and differs from it in three ways, each forced by ticket 18's cases:

  * ticket 18 prints most of its checks one row per COLUMN (`col`, `name`, `octets`, `digest`,
    `ok`) rather than one wide row per record, because its widest record carries eighteen
    columns and fifty-four scalars.  Both table shapes are understood here;
  * a NULL length beside a NULL value is expected, not a parse failure (OOS-REP-09);
  * two cases are expected to produce an error, and one of them is expected to produce it from
    a DDL statement, so the error identities are per case and ordered.

The checks:

  1. every equality flag -- `ok` or `*_ok` -- is 1, and every `*_is_null` is the value the
     oracle names;
  2. every (OCTET_LENGTH, MD5) pair the results print is a pair the derivation predicts, in
     Python, without the engine.  A digest the engine produced that is not in that table means
     the engine returned a value no case wrote;
  3. each digest is paired with ITS OWN length column, so a truncation whose digest happened to
     collide with another literal's would still be caught;
  4. the specific scalars the oracle names -- aggregate totals, row counts, the refused DDL's
     class count -- appear exactly as expected;
  5. the error identities are exactly the ones the oracle derived from the pinned engine's
     message catalogue before it ran, in order, and no others appear anywhere;
  6. every case yields at least one equality flag, so a rename in the generator that stopped the
     flags being recognised would fail here instead of passing silently.

Exit 0 only when every case passes every check.  Nothing here writes into the bundle or the
testcase repository.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "ticket19"))
import gen_ticket19_cases as g  # noqa: E402
import derive_ticket19_sizes as d  # noqa: E402

MD5_RE = re.compile(r"\b[0-9a-f]{32}\b")
ERROR_RE = re.compile(r"^Error:(-?\d+)\s*$")

TICKET18_CASES = ["cbrd_26659_oos_rep01_gate_boundary", "cbrd_26659_oos_rep02_demotion_order",
                  "cbrd_26659_oos_rep04_eligibility_floor", "cbrd_26659_oos_rep07_chunk_boundary",
                  "cbrd_26659_oos_rep08_bigone_rejection", "cbrd_26659_oos_rep09_null_empty",
                  "cbrd_26659_oos_rep10_many_stubs", "cbrd_26659_oos_rep11_transitions",
                  "cbrd_26659_oos_rep13_placement_hints"]

# The oracle's named scalars, section by section.  Each entry is a substring that must occur in
# the case's result text, with the section of expected-oracle.md that justifies it.
EXPECTED_SCALARS = {
    "cbrd_26659_oos_rep01_gate_boundary": [
        ("4     4     4     0", "S3 TEST 5: four rows, four exact, four distinct, none aliased"),
    ],
    "cbrd_26659_oos_rep02_demotion_order": [
        ("1     0     1", "S4 TEST 4: the two equal-size values are different values"),
        ("3     3     0", "S4 TEST 6: three rows, three distinct big1, none aliased"),
    ],
    "cbrd_26659_oos_rep04_eligibility_floor": [
        ("3     3     3     3     3", "S5 TEST 5: three rows, distinct in every column"),
    ],
    "cbrd_26659_oos_rep07_chunk_boundary": [
        ("4     4     68135     3000     32576     0", "S6 TEST 5: the four-row aggregate"),
    ],
    "cbrd_26659_oos_rep08_bigone_rejection": [],
    "cbrd_26659_oos_rep09_null_empty": [],
    "cbrd_26659_oos_rep10_many_stubs": [
        ("18     18", "S9 TEST 3: eighteen distinct digests over eighteen columns"),
        ("2     0     0     730     560", "S9 TEST 4: the two-row aggregate"),
    ],
    "cbrd_26659_oos_rep11_transitions": [
        ("2     2     0", "S10 TEST 8: two rows, two distinct payloads, none aliased"),
    ],
    "cbrd_26659_oos_rep13_placement_hints": [],
}

# Error identities the oracle derived from the pinned engine before it was run.
EXPECTED_ERRORS = {
    "cbrd_26659_oos_rep08_bigone_rejection": [-1382],   # ER_HEAP_OOS_OVERPASS_MAXOBJ_SIZE
    "cbrd_26659_oos_rep13_placement_hints": [-495],     # ER_PT_EXECUTE
}

# The scenario runs as a whole (campaign ticket 48 item 48.3), so this review sees ticket 13's
# and ticket 19's candidates too.  Their expectations are IMPORTED from ticket 19's reviewer
# rather than re-typed, so the two cannot drift: a case that changes its error identity has one
# place to change it.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "ticket19"))
import review_candidates as t19  # noqa: E402

for _case, _errors in t19.EXPECTED_ERRORS.items():
    EXPECTED_ERRORS.setdefault(_case, _errors)
for _case, _scalars in t19.EXPECTED_SCALARS.items():
    EXPECTED_SCALARS.setdefault(_case, _scalars)

# Ticket 13's and ticket 19's cases share the scenario directory, so this invocation executes
# them too.  Their literals are listed so the review covers every result the run produced rather
# than skipping the nine cases it does not own.
TICKET13_LITERALS = [("a", 3000), ("b", 1200), ("c", 1000), ("d", 500)]


def literal_table():
    """(octet_length, md5) -> the literal that produces it, from the derivation alone."""
    for fn in g.CASES:
        fn()
    for _spec_dir, specs in g.SPEC_GROUPS:
        for fn in specs:
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
    for b in text.split("=" * 51):
        lines = [l for l in b.splitlines() if l.strip()]
        if not lines:
            continue
        header = lines[0].split()
        if not any(h.endswith(("_ok", "_md5", "_octets", "_len", "_is_null")) or h.startswith("n_")
                   or h in ("id", "col", "name", "octets", "digest", "ok") for h in header):
            continue
        yield header, [l.split() for l in lines[1:]]


def pairs_in(header, row):
    """Yield (length column, digest column, length, digest) for every digest in one row.

    Ticket 19's tables name their columns `<prefix>_octets` and `<prefix>_md5`; ticket 18's
    per-column tables name them `octets` and `digest`.  Either way the digest is paired with the
    length beside it and never with some other column's.
    """
    idx = {h: i for i, h in enumerate(header)}
    for h, i in idx.items():
        if i >= len(row):
            continue
        digest = row[i]
        if not MD5_RE.fullmatch(digest):
            continue
        if h == "digest":
            len_col = "octets" if "octets" in idx else None
        elif h.endswith("_md5"):
            prefix = h[: -len("_md5")]
            len_col = next((c for c in (f"{prefix}_octets", f"{prefix}_len") if c in idx), None)
        else:
            len_col = None
        if len_col is None or idx[len_col] >= len(row):
            yield None, h, None, digest
        else:
            yield len_col, h, row[idx[len_col]], digest


def review(case, text, table):
    problems = []
    flags = 0
    for header, rows in parse_tables(text):
        idx = {h: i for i, h in enumerate(header)}
        for row in rows:
            if len(row) < len(header):
                continue
            for h, i in idx.items():
                if h == "ok" or h.endswith("_ok"):
                    flags += 1
                    if row[i] != "1":
                        problems.append(f"{case}: column {h} is {row[i]}, not 1 (row {row[:2]})")
            for len_col, dig_col, n, digest in pairs_in(header, row):
                if len_col is None:
                    if not any(k[1] == digest for k in table):
                        problems.append(f"{case}: digest {digest} in {dig_col} is not produced "
                                        "by any value the derivation predicts")
                    continue
                if (int(n), digest) not in table:
                    problems.append(f"{case}: ({n} B, {digest}) in {dig_col} is not a "
                                    "(length, digest) pair the derivation predicts")
    if flags == 0:
        problems.append(f"{case}: no equality flag was recognised in any result table; either "
                        "the case stopped asserting whole-value equality or this reviewer no "
                        "longer understands the result format")

    got_errors = [int(m.group(1)) for line in text.splitlines()
                  if (m := ERROR_RE.match(line.strip()))]
    want_errors = EXPECTED_ERRORS.get(case, [])
    if got_errors != want_errors:
        problems.append(f"{case}: error identities {got_errors}, expected {want_errors}")

    for needle, why in EXPECTED_SCALARS.get(case, []):
        if needle not in text:
            problems.append(f"{case}: expected scalars not found ({why}): '{needle}'")
    return problems


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bundle", type=Path, required=True)
    ap.add_argument("--only-ticket18", action="store_true",
                    help="review only the nine cases this ticket owns")
    args = ap.parse_args()

    table = literal_table()
    results = sorted((args.bundle / "actual").glob("*.result"))
    if not results:
        one = args.bundle / "actual.result"
        results = [one] if one.exists() else []
    if args.only_ticket18:
        results = [r for r in results if r.stem in TICKET18_CASES]
    if not results:
        print(f"no candidate .result under {args.bundle}")
        return 2

    print(f"# Candidate review against the pre-run oracle ({len(table)} predicted "
          f"(length, digest) pairs)\n")
    total = 0
    for r in results:
        text = r.read_text(errors="replace")
        problems = review(r.stem, text, table)
        total += len(problems)
        rows = sum(len(rws) for _h, rws in parse_tables(text))
        mine = "ticket 18" if r.stem in TICKET18_CASES else "earlier"
        print(f"{'OK  ' if not problems else 'FAIL'}  {r.stem:<46} {mine:<9} "
              f"{len(text.splitlines()):>5} lines, {rows:>4} result rows")
        for p in problems:
            print(f"        {p}")
    print(f"\nRESULT: {'every candidate matches the oracle' if total == 0 else f'{total} problem(s)'}")
    return 0 if total == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
