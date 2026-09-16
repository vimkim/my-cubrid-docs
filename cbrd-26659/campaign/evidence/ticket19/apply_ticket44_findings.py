#!/usr/bin/env python3
"""Apply ticket 44's two hand-owned matrix changes to ticket 19's coverage matrix.

    apply_ticket44_findings.py --matrix evidence/ticket19/matrix.json

Everything mechanical about `inv-T19-0008` is `matrix_merge.py`'s: which rows gain an attempt,
that `cbrd_26659_oos_sql02_update` on release becomes `ever_failed` with one failure in four,
and that `latest_outcome` stays `PASS` because `inv-T19-0009` is later.  Run that first:

    python3 tools/matrix_merge.py --manifest evidence/ticket19/inv-T19-0008.json \\
        --existing evidence/ticket19/matrix.json --attempt-records-dir evidence/ticket19 \\
        --out evidence/ticket19/matrix.json

Two things the merge deliberately does not write, and this script does:

**F1's attribution.**  `matrix_merge.py` never touches `attribution` -- a cause is a judgement
with evidence behind it, not a count.  The FAIL of `att-T19-0075` is understood: revision 2 of
the ticket 19 report lower-cased the cases and relabelled the update case's third step, and
`inv-T19-0008` ran the relabelled case against the answer promoted from `inv-T19-0003`, which
still carried the old label.  The values were byte-identical; the label was not.  So the target
is `harness`, the repository precedent for "the engine behaved correctly and the test apparatus
is what differed" (ticket 13's two caseless rows), and the note says so in as many words.  This
is bookkeeping, not a retraction: nothing about the delivery changes, and `flakiness.failures`
already records the count.

**F4's accepted exclusion.**  The three bootstrap invocations `inv-T19-0001..0003` executed all
27 of their attempts and their outcomes were never merged, which the specification allows only
as an accepted exclusion: "Only the user converts incomplete coverage into an accepted
exclusion, as a dated entry in the coverage matrix naming the requirement and reason.  Agents
propose; they never accept."  The proposal stood in prose in three places and `matrix_merge.py`
refuses to write the list at all.  The user accepted it on 2026-09-16, which is what lets this
script write the entries; the entries themselves are derived from the three manifests rather
than typed, so the attempt ids they name cannot drift from the records they exclude.

This script is idempotent, writes through `write_record`, and refuses to run before the merge.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))
from campaign_records import RecordError, write_record  # noqa: E402

HERE = Path(__file__).resolve().parent

# --- F1 -------------------------------------------------------------------------------------
MERGED_INVOCATION = "inv-T19-0008"
FAILED_ATTEMPT = "att-T19-0075"
FAILED_ROW = "OOS-SQL-02/cbrd_26659_oos_sql02_update/16384-release-cs"
ATTRIBUTION = {
    "target": "harness",
    "evidence": ("cbrd-26659/campaign/evidence/ticket19/att-T19-0075.json and its expected-versus-actual diff "
                 "under the inv-T19-0008 replay bundle; the eight other cases of the same invocation came back "
                 "byte-identical against the same promoted answers, which is what separates a testcase-side "
                 "difference from an engine one. The answer was re-promoted from this invocation in testcase "
                 "commit 35c815943 and inv-T19-0009 then PASSed."),
    "note": ("NOT an Engine defect. Revision 2 of the ticket 19 report lower-cased the cases and relabelled this "
             "case's third step (finding T5/S4); inv-T19-0008 ran the relabelled case against the answer promoted "
             "from inv-T19-0003, which still carried the old label, so the whole-result comparison differed by the "
             "label and by nothing else. Every value read back exactly. Recorded here because a later pass never "
             "erases an earlier failure, not because the delivery is in doubt: latest_outcome stays PASS and "
             "flakiness.failures records the one failure in four attempts. Merged by ticket 44 F1."),
}

# --- F4 -------------------------------------------------------------------------------------
BOOTSTRAP_MANIFESTS = ["inv-T19-0001.json", "inv-T19-0002.json", "inv-T19-0003.json"]
EXCLUSION_DATE = "2026-09-16"
EXCLUSION_REASON = (
    "The three bootstrap invocations inv-T19-0001, inv-T19-0002 and inv-T19-0003 executed every case with a "
    "deliberately empty .answer, which is how CTP is made to run a new case and emit a candidate instead of "
    "skipping it and still exiting 0 (ticket 13 finding a). Their FAIL outcomes are the mechanism by which the "
    "answers under review were produced, not findings about the engine: every case of the family PASSed against "
    "the promoted answers in inv-T19-0004, -0005, -0006, -0009 and -0010, and merging the bootstraps would set "
    "ever_failed and three failures in five attempts on every row of the family for a reason that is not a "
    "finding. The manifests, the 27 attempt records and the 27 replay bundles are retained in full. This is the "
    "campaign's only exclusion of an executed `original` attempt from the matrix: inv-T19-0008, whose answers "
    "were NOT empty, is merged (ticket 44 F1)."
)
EXCLUSION_PROPOSED_IN = (
    "Proposed in campaign ticket 19's Outcome, in section 12 of CBRD-26659-sql-operations_f4299ac_claude.md, and "
    "in finding F4 of CBRD-26659-ticket19-independent-review_f4299ac_claude.md; carried to a decision by ticket 44."
)


def bootstrap_attempts_by_requirement():
    """Which attempt of the three bootstrap invocations belongs to which requirement.

    Derived from the manifests rather than typed, so an entry cannot name an attempt that is not
    excluded, or miss one that is.
    """
    by_req: dict[str, list[str]] = {}
    for name in BOOTSTRAP_MANIFESTS:
        manifest = json.loads((HERE / name).read_text(encoding="utf-8"))
        for case in manifest["cases"]:
            for attempt in case["attempts"]:
                for rid in case["requirements"]:
                    by_req.setdefault(rid, []).append(attempt["attempt_id"])
    return {rid: sorted(set(ids)) for rid, ids in sorted(by_req.items())}


def exclusion_entries():
    entries = []
    for rid, attempts in bootstrap_attempts_by_requirement().items():
        entries.append({
            "requirement": rid,
            "date": EXCLUSION_DATE,
            "reason": EXCLUSION_REASON,
            "accepted_by": "user",
            "scope": ("Excludes from the coverage matrix only the bootstrap attempts "
                      + ", ".join(attempts)
                      + " of invocations inv-T19-0001, inv-T19-0002 and inv-T19-0003. No case, configuration or "
                        "later attempt of this requirement is excluded."),
            "proposed_in": EXCLUSION_PROPOSED_IN,
        })
    return entries


def apply_attribution(matrix) -> bool:
    rows = {row["row_id"]: row for row in matrix["rows"]}
    row = rows.get(FAILED_ROW)
    if row is None:
        raise RecordError(f"{FAILED_ROW} is not in the matrix")
    if not any(h["attempt_id"] == FAILED_ATTEMPT for h in row["finding"]["history"]):
        raise RecordError(
            f"{FAILED_ROW} does not carry {FAILED_ATTEMPT}: merge {MERGED_INVOCATION} with matrix_merge.py first "
            "(this script attributes a failure the matrix does not yet know about)")
    if row["attribution"] == ATTRIBUTION:
        return False
    row["attribution"] = dict(ATTRIBUTION)
    return True


def apply_exclusions(matrix) -> bool:
    wanted = exclusion_entries()
    if matrix.get("accepted_exclusions") == wanted:
        return False
    if matrix.get("accepted_exclusions"):
        raise RecordError(
            "accepted_exclusions already carries entries this script did not write; only the user writes them, "
            "so nothing is overwritten. Reconcile by hand.")
    matrix["accepted_exclusions"] = wanted
    return True


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--matrix", required=True)
    args = ap.parse_args(argv)
    try:
        return apply_findings(args)
    except RecordError as exc:
        print(f"[apply_ticket44_findings] REFUSED: {exc}", file=sys.stderr)
        return 2


def apply_findings(args) -> int:
    path = Path(args.matrix)
    matrix = json.loads(path.read_text(encoding="utf-8"))

    changed_attribution = apply_attribution(matrix)
    changed_exclusions = apply_exclusions(matrix)
    if not (changed_attribution or changed_exclusions):
        print("[apply_ticket44_findings] already applied; nothing to write")
        return 0
    write_record(matrix, "matrix", path)
    print(f"[apply_ticket44_findings] attribution {'set' if changed_attribution else 'unchanged'}; "
          f"{len(matrix['accepted_exclusions'])} accepted exclusion(s) "
          f"{'written' if changed_exclusions else 'unchanged'}; wrote {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
