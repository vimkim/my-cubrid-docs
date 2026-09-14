#!/usr/bin/env python3
"""Self-test of the answer-promotion contract (ticket 36 item 8, applied by ticket 40).

    selftest_promotions.py [--keep DIR]

A `promoted` entry claims the reviewed answer is the retained candidate renamed. The proof --
the two files hashing equal -- is mechanical, so `ctp_sql_records.verified_promotions` checks it
and the human supplies only what is not mechanical: the review note and the flag. These checks
are the refusals that contract owes.

Every identifier carries SELFTEST so nothing here can be mistaken for campaign evidence.

  1. a promoted entry whose answer and candidate hash equal is written, and the tool appends
     the rename proof to the hand-supplied review note;
  2. the same entry without a review note is refused;
  3. the same entry without an explicit flagged_for_user is refused;
  4. an entry whose answer and candidate differ is refused: the rename is unproven;
  5. an entry whose candidate is not in the bundle is refused;
  6. a candidate or retained-as-failure-evidence entry passes through untouched.

Exit 0 when every check holds.
"""
from __future__ import annotations

import argparse
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from campaign_records import RecordError  # noqa: E402
import ctp_sql_records  # noqa: E402

CASE = "SELFTEST_case"
NOTE = "SELFTEST: reviewed against OOS-REP-02 and promoted"


def bundle_with(tmp: Path, name: str, answer: str, candidate) -> Path:
    b = tmp / name
    b.mkdir(parents=True, exist_ok=True)
    (b / "expected.answer").write_text(answer)
    if candidate is not None:
        (b / "candidate.result").write_text(candidate)
    return b


def refused(entry, bundle) -> str:
    """Return the refusal message, or '' when the call was accepted."""
    try:
        ctp_sql_records.verified_promotions([entry], bundle, {CASE})
    except RecordError as exc:
        return str(exc)
    return ""


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--keep", help="directory to keep the synthetic files in (default: a temporary directory)")
    args = ap.parse_args(argv)
    tmp = Path(args.keep) if args.keep else Path(tempfile.mkdtemp(prefix="selftest-promotions-"))
    tmp.mkdir(parents=True, exist_ok=True)
    fails = []

    def check(label, cond):
        print(("PASS  " if cond else "FAIL  ") + label)
        if not cond:
            fails.append(label)

    matching = bundle_with(tmp, "matching", "SELFTEST rows\n", "SELFTEST rows\n")
    differing = bundle_with(tmp, "differing", "SELFTEST rows\n", "SELFTEST other rows\n")
    no_candidate = bundle_with(tmp, "no-candidate", "SELFTEST rows\n", None)
    promoted = {"case": CASE, "action": "promoted", "flagged_for_user": False, "review_note": NOTE, "reviewer": "SELFTEST reviewer"}

    # 1. accepted, with the proof written by the tool
    out = ctp_sql_records.verified_promotions([dict(promoted)], matching, {CASE})
    check("1a a proven rename is written", len(out) == 1 and out[0]["action"] == "promoted")
    check("1b the hand-supplied review note is kept", out[0]["review_note"].startswith(NOTE))
    check("1c the tool appends the rename proof", "RENAME VERIFIED" in out[0]["review_note"]
          and "expected.answer" in out[0]["review_note"] and "candidate.result" in out[0]["review_note"])
    check("1d the flag is left as the reviewer set it", out[0]["flagged_for_user"] is False)

    # 2..5. the refusals
    no_note = dict(promoted, review_note="   ")
    check("2  refused without a review note", "review note" in refused(no_note, matching))
    no_flag = {k: v for k, v in promoted.items() if k != "flagged_for_user"}
    check("3  refused without an explicit flagged_for_user", "flagged_for_user" in refused(no_flag, matching))
    check("4  refused when the answer and the candidate differ", "unproven" in refused(dict(promoted), differing))
    check("5  refused when the candidate is not in the bundle", "cannot be verified" in refused(dict(promoted), no_candidate))

    # 6. the tool only gates `promoted`
    others = [{"case": CASE, "action": "candidate", "flagged_for_user": False, "review_note": None, "reviewer": None},
              {"case": CASE, "action": "retained-as-failure-evidence", "flagged_for_user": False, "review_note": None, "reviewer": None}]
    check("6  candidate and retained entries pass through untouched",
          ctp_sql_records.verified_promotions([dict(e) for e in others], no_candidate, {CASE}) == others)

    print(f"[selftest_promotions] {len(fails)} failing check(s); files under {tmp}")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
