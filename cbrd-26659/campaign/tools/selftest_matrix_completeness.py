#!/usr/bin/env python3
"""Negative control for the coverage-completeness check (ticket 44 O1).

    selftest_matrix_completeness.py [--keep DIR]

`check_campaign_records.check_matrix_completeness` exists because ticket 19's `inv-T19-0008`
executed nine cases, one of them FAILed, and none of its attempt records reached any matrix --
and every shape check passed anyway. A check that passes on the repaired tree proves nothing
about whether it would have caught that, so this plants the defect back and requires the check
to report it.

Every identifier carries SELFTEST so nothing here can be mistaken for campaign evidence.

  1. an `original` attempt carried by a matrix row's `finding.history` is accounted for;
  2. the same attempt with the history entry removed is reported -- the planted defect;
  3. a dated `accepted_exclusions` entry naming the attempt in `scope` accounts for it instead;
  4. an exclusion that names only the invocation, not the attempt, does NOT account for it;
  5. `checker-validation` and `coexistence` attempts are never asked for;
  6. an id that appears only in the free-form `reason` does NOT account for the attempt;
  7. an exclusion that is undated, or not accepted by the user, is itself reported;
  8. an attempt record in a `controls/` subdirectory is examined, not skipped;
  9. two `original` records sharing one id but naming different attempts are reported, because
     pooling every matrix's history is only sound while an id names one attempt.

Exit 0 when every check holds.
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import check_campaign_records as ccr  # noqa: E402

ATTEMPT = "att-SELFTEST-0001"
MANIFEST = "inv-SELFTEST-0001"


def attempt_record(kind: str, manifest: str = MANIFEST, case: str = "SELFTEST_case") -> dict:
    return {"attempt_id": ATTEMPT, "kind": kind, "manifest_id": manifest, "outcome": "FAIL",
            "case": {"name": case}}


def matrix(history_ids, exclusions) -> dict:
    return {
        "rows": [{"row_id": "SELFTEST/row", "finding": {"history": [{"attempt_id": a} for a in history_ids]}}],
        "accepted_exclusions": exclusions,
    }


def run(tmp: Path, label: str, record: dict, matrix_doc: dict, subdir: str = "", also: dict = None) -> list:
    """Run the check against a synthetic evidence tree; return its failure messages.

    The evidence root and the campaign root are arguments, so only the accumulator the whole
    module writes into has to be swapped.
    """
    root = tmp / label
    ticket = root / "evidence" / "selftest"
    (ticket / subdir).mkdir(parents=True, exist_ok=True)
    (ticket / "matrix.json").write_text(json.dumps(matrix_doc), encoding="utf-8")
    (ticket / subdir / f"{record['attempt_id']}.json").write_text(json.dumps(record), encoding="utf-8")
    if also is not None:
        (ticket / "regenerated").mkdir(parents=True, exist_ok=True)
        (ticket / "regenerated" / f"{also['attempt_id']}.json").write_text(json.dumps(also), encoding="utf-8")
    saved_failures = ccr.failures
    ccr.failures = []
    try:
        ccr.check_matrix_completeness(evidence=root / "evidence", campaign=root)
        return list(ccr.failures)
    finally:
        ccr.failures = saved_failures


def exclusion(scope: str, **overrides) -> dict:
    entry = {"requirement": "OOS-SQL-01", "date": "2026-09-16", "accepted_by": "user",
             "reason": "SELFTEST bootstrap exclusion", "scope": scope, "proposed_in": "SELFTEST"}
    entry.update(overrides)
    return entry


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--keep", help="directory to keep the synthetic tree in (default: a temporary directory)")
    args = ap.parse_args(argv)
    tmp = Path(args.keep) if args.keep else Path(tempfile.mkdtemp(prefix="selftest-completeness-"))
    tmp.mkdir(parents=True, exist_ok=True)
    fails = []

    def check(label, cond):
        print(("PASS  " if cond else "FAIL  ") + label)
        if not cond:
            fails.append(label)

    check("1  a merged original attempt is accounted for",
          run(tmp, "merged", attempt_record("original"), matrix([ATTEMPT], [])) == [])

    planted = run(tmp, "planted", attempt_record("original"), matrix([], []))
    check("2  THE PLANTED DEFECT: an unmerged original attempt is reported",
          len(planted) == 1 and ATTEMPT in planted[0])

    check("3  a dated exclusion naming the attempt accounts for it",
          run(tmp, "excluded", attempt_record("original"),
              matrix([], [exclusion(f"the bootstrap attempt {ATTEMPT}")])) == [])

    check("4  an exclusion naming only the invocation does not account for it",
          len(run(tmp, "invocation-only", attempt_record("original"),
                  matrix([], [exclusion(f"the whole of {MANIFEST}")]))) == 1)

    for kind in ("checker-validation", "coexistence"):
        check(f"5  a {kind} attempt is never asked for",
              run(tmp, kind, attempt_record(kind), matrix([], [])) == [])

    check("6  an id named only in the free-form reason does not account for it",
          len(run(tmp, "reason-only", attempt_record("original"),
                  matrix([], [exclusion("no attempt named here",
                                        reason=f"prose that happens to mention {ATTEMPT}")]))) == 1)

    for label, slug, override in (("an undated exclusion", "undated", {"date": None}),
                                  ("an exclusion the user did not accept", "not-user", {"accepted_by": "agent"})):
        failures = run(tmp, f"exclusion-{slug}", attempt_record("original"),
                       matrix([], [exclusion(f"the bootstrap attempt {ATTEMPT}", **override)]))
        check(f"7  {label} is itself reported, and accounts for nothing", len(failures) == 2)

    check("8  an attempt record under controls/ is examined, not skipped",
          len(run(tmp, "controls", attempt_record("original"), matrix([], []), subdir="controls")) == 1)

    merged_matrix = matrix([ATTEMPT], [])
    check("9a a regenerated copy of the same attempt is not a collision",
          run(tmp, "same-id-same-attempt", attempt_record("original"), merged_matrix,
              also=attempt_record("original")) == [])
    collision = run(tmp, "same-id-other-attempt", attempt_record("original"), merged_matrix,
                    also=attempt_record("original", manifest="inv-SELFTEST-0002", case="SELFTEST_other"))
    check("9b two different attempts sharing one id are reported",
          len(collision) == 1 and "different attempt" in collision[0])

    print(f"[selftest_matrix_completeness] {len(fails)} failing check(s); files under {tmp}")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
