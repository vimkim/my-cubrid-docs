#!/usr/bin/env python3
"""Checker for the tier-placement table (campaign ticket 17).

`tier_placement.py` derives the placement table from measured inputs and the caps decision
ticket 08 fixed. This selftest plants the mistakes a hand-written table makes -- a workload
placed in a tier whose cap it exceeds, a workload squeezed into a tier instead of being
recorded as fitting none, a derived figure presented as measured, a seed count whose arithmetic
was never done -- and requires the tool to report each one.

The point is that the caps are INPUTS. A table that stays the same when a cap changes is prose
about the caps, not a computation against them; check 10 is the regression test for that.

Standard library only. Writes nothing outside a temporary directory.
"""
from __future__ import annotations

import copy
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import tier_placement  # noqa: E402

FAILS = []


def check(n, label, ok):
    print(("PASS  " if ok else "FAIL  ") + f"{n:<4}{label}")
    if not ok:
        FAILS.append(f"{n} {label}")


CAPS = {
    "fast": {"invocation_seconds": 900, "per_case_seconds": 120},
    "scheduled": {"invocation_seconds": 7200, "per_case_seconds": 900},
    "extended": {"invocation_seconds": 28800, "per_case_seconds": 3600},
}


def model():
    return {
        "caps": copy.deepcopy(CAPS),
        "workloads": [
            {
                "id": "sql-fixed", "name": "fixed deterministic public SQL", "family": "SQL operations",
                "seam": "public SQL", "basis": "measured", "evidence": ["inv-T17-0002"],
                "per_case_seconds": 7.5, "cases_per_invocation": 9,
                "invocation_fixed_seconds": 44, "proposed_tier": "fast",
            },
            {
                "id": "shell-crash", "name": "crash and recover", "family": "Durability",
                "seam": "private shell", "basis": "measured", "evidence": ["inv-T17-0003"],
                "per_case_seconds": 11.7, "cases_per_invocation": 1,
                "invocation_fixed_seconds": 6, "proposed_tier": "fast",
            },
            {
                "id": "churn-10", "name": "randomized churn, ten seeds", "family": "Durability",
                "seam": "private shell", "basis": "measured", "evidence": ["seeds-10-fresh"],
                "seeds": 10, "per_seed_seconds": 5.8, "cases_per_invocation": 1,
                "invocation_fixed_seconds": 17, "proposed_tier": "scheduled",
            },
        ],
    }


def placed(m):
    return {w["id"]: w for w in tier_placement.place(m)["workloads"]}


def main():
    with tempfile.TemporaryDirectory(prefix="selftest-tier-"):
        m = model()
        out = tier_placement.place(m)
        check(1, "a table whose every workload fits its proposed tier reports no problem",
              out["problems"] == [])

        rows = placed(m)
        check(2, "a nine-case public SQL invocation is computed, not asserted: 44 + 9 x 7.5 = 111.5 s",
              abs(rows["sql-fixed"]["invocation_seconds"] - 111.5) < 0.01)
        check(3, "the smallest fitting tier is named beside the proposal",
              rows["sql-fixed"]["smallest_fitting_tier"] == "fast")

        m2 = model()
        m2["workloads"][1]["per_case_seconds"] = 130.0          # over the fast per-case cap
        probs = tier_placement.place(m2)["problems"]
        check(4, "a workload whose per-case time exceeds its proposed tier's per-case cap is reported",
              len(probs) == 1 and "shell-crash" in probs[0] and "per-case cap" in probs[0])

        m3 = model()
        m3["workloads"][0]["cases_per_invocation"] = 200         # 44 + 200 x 7.5 = 1544 s > 900
        probs = tier_placement.place(m3)["problems"]
        check(5, "a workload whose invocation time exceeds its proposed tier's invocation cap is reported",
              len(probs) == 1 and "sql-fixed" in probs[0] and "invocation cap" in probs[0])

        m4 = model()
        m4["workloads"][1]["per_case_seconds"] = 4000.0          # over every per-case cap
        out4 = tier_placement.place(m4)
        row = {w["id"]: w for w in out4["workloads"]}["shell-crash"]
        check(6, "a workload that fits no tier is recorded as fitting none, never squeezed into one",
              row["smallest_fitting_tier"] is None
              and any("shell-crash" in p and "fits no tier" in p for p in out4["problems"]))

        m5 = model()
        m5["workloads"][0]["basis"] = "derived"
        probs = tier_placement.place(m5)["problems"]
        check(7, "a derived figure with no derivation recorded is reported",
              len(probs) == 1 and "sql-fixed" in probs[0] and "derivation" in probs[0])

        m6 = model()
        m6["workloads"][0]["basis"] = "derived"
        m6["workloads"][0]["derivation"] = "scaled from the nine-case invocation"
        m6["workloads"][0]["evidence"] = []
        check(8, "a derived figure that records its derivation is accepted without an attempt id",
              tier_placement.place(m6)["problems"] == [])

        rows = placed(model())
        churn = rows["churn-10"]
        check(9, "a seeded workload is costed under BOTH readings of 'seeds per workload': "
                 "10 x 5.8 = 58 s in one case, and 5.8 s per case across ten cases",
              abs(churn["seeds_all_in_one_case"]["per_case_seconds"] - 58.0) < 0.01
              and abs(churn["seed_per_case"]["per_case_seconds"] - 5.8) < 0.01)

        m7 = model()
        m7["caps"]["fast"]["per_case_seconds"] = 5              # the cap, not the table, changes
        out7 = tier_placement.place(m7)
        rows7 = {w["id"]: w for w in out7["workloads"]}
        check(10, "the caps are inputs: lowering the fast per-case cap moves the placement",
              rows7["sql-fixed"]["smallest_fitting_tier"] == "scheduled"
              and any("sql-fixed" in p for p in out7["problems"]))

        m8 = model()
        m8["workloads"][2]["proposed_tier"] = "fast"           # 17 + 58 = 75 s, but 58 s > ... fits fast
        out8 = tier_placement.place(m8)
        check(11, "a proposal larger than necessary is allowed; a proposal the workload does not fit is not",
              out8["problems"] == [])

        m10 = model()
        m10["workloads"][0]["cases_per_invocation"] = 11
        m10["workloads"][0]["invocation_measured_seconds"] = 432.0
        out10 = tier_placement.place(m10)
        rows10 = {w["id"]: w for w in out10["workloads"]}
        check(13, "a workload whose whole invocation was measured uses the measurement, and carries the "
                  "worst-case-uniform figure beside it rather than instead of it",
              rows10["sql-fixed"]["invocation_seconds"] == 432.0
              and abs(rows10["sql-fixed"]["invocation_worst_case_seconds"] - (44 + 11 * 7.5)) < 0.01
              and out10["problems"] == [])

        m11 = model()
        m11["workloads"][0]["cases_per_invocation"] = 11
        m11["workloads"][0]["per_case_seconds"] = 112.0        # 44 + 11 x 112 = 1276 s, over the fast cap
        m11["workloads"][0]["invocation_measured_seconds"] = 432.0
        out11 = tier_placement.place(m11)
        rows11 = {w["id"]: w for w in out11["workloads"]}
        check(14, "a measured invocation that fits while its worst-case-uniform figure does not is a recorded "
                  "risk, not a problem: the measurement places it, the risk is not hidden",
              out11["problems"] == []
              and any("sql-fixed" in r and "worst" in r for r in out11["risks"])
              and rows11["sql-fixed"]["smallest_fitting_tier"] == "fast")

        m12 = model()
        m12["workloads"][0]["invocation_measured_seconds"] = 5000.0   # measured, and over the fast cap
        out12 = tier_placement.place(m12)
        check(15, "a measured invocation over the proposed tier's cap is still a problem",
              any("sql-fixed" in p and "invocation cap" in p for p in out12["problems"]))

        m9 = model()
        m9["workloads"][2]["seeds"] = 100
        rows9 = {w["id"]: w for w in tier_placement.place(m9)["workloads"]}
        check(12, "the extended tier's hundred seeds are costed from the measured per-seed time: 580 s",
              abs(rows9["churn-10"]["seeds_all_in_one_case"]["per_case_seconds"] - 580.0) < 0.01)

    print(f"[selftest_tier_placement] {len(FAILS)} failing check(s)")
    for f in FAILS:
        print("  " + f)
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
