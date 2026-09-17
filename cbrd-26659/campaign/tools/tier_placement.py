#!/usr/bin/env python3
"""Compute the campaign's tier-placement table from measured inputs (campaign ticket 17).

    tier_placement.py place --model FILE [--format md|json]
    tier_placement.py check --model FILE

Decision ticket 08 fixed three tiers and their caps and then said: "Tier placement of specific
workloads is finalized only after the feasibility tickets measure representative cases." This
module is that finalization. It takes the caps and the measured per-case and per-invocation
costs as INPUTS and derives the placement, so that a table which would not survive a change of
cap cannot be written by hand and called a placement.

What it computes for each workload:

  * `invocation_seconds` = fixed cost of the seam's invocation + cases x per-case cost. The
    fixed cost is a measured property of the seam (the CTP SQL launcher costs the same 43-44 s
    for one case and for nine), so a placement that ignores it understates every invocation.
  * `smallest_fitting_tier`: the first tier whose per-case AND invocation caps both hold. None
    when no tier holds -- which is recorded, never squeezed: "Any workload that cannot fit is
    recorded, not squeezed" (ticket 17 criterion 3).
  * for a seeded workload, the cost under BOTH readings of decision ticket 08's "N seeds per
    selected randomized workload", because the decision does not say whether the seeds of one
    workload are one case or N cases, and the two readings differ by a factor of N against the
    per-case cap. The ambiguity is reported rather than resolved here: settling it is a map
    decision, not an implementation ticket's (spec, Reopening rule).

`problems()` is what `selftest_tier_placement.py` plants mistakes against. Standard library only.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

TIER_ORDER = ("fast", "scheduled", "extended")


def _fits(caps, per_case, invocation):
    return per_case <= caps["per_case_seconds"] and invocation <= caps["invocation_seconds"]


def place(model: dict) -> dict:
    caps = model["caps"]
    problems, risks, rows = [], [], []
    for w in model["workloads"]:
        row = dict(w)
        seeds = w.get("seeds")
        if seeds:
            per_seed = w["per_seed_seconds"]
            row["seeds_all_in_one_case"] = {"per_case_seconds": round(seeds * per_seed, 3), "cases": 1}
            row["seed_per_case"] = {"per_case_seconds": round(per_seed, 3), "cases": seeds}
            per_case = seeds * per_seed
            cases = w.get("cases_per_invocation", 1)
        else:
            per_case = w["per_case_seconds"]
            cases = w.get("cases_per_invocation", 1)
        row["per_case_seconds"] = round(per_case, 3)
        # Two different questions, both worth an answer. The worst-case-uniform figure asks what the
        # invocation would cost if every case were as slow as the slowest; a heterogeneous suite (the
        # eleven-case private bucket runs cases of 1.4 s and 112 s) is placed by what it was measured
        # to cost, and the worst-case figure is carried beside it as a recorded risk, never instead of it.
        row["invocation_worst_case_seconds"] = round(w.get("invocation_fixed_seconds", 0) + cases * per_case, 3)
        measured = w.get("invocation_measured_seconds")
        row["invocation_seconds"] = round(measured, 3) if measured is not None else row["invocation_worst_case_seconds"]

        smallest = None
        for tier in TIER_ORDER:
            if _fits(caps[tier], row["per_case_seconds"], row["invocation_seconds"]):
                smallest = tier
                break
        row["smallest_fitting_tier"] = smallest

        proposed = w.get("proposed_tier")
        if smallest is None:
            problems.append(
                f"{w['id']}: fits no tier -- {row['per_case_seconds']} s per case and "
                f"{row['invocation_seconds']} s per invocation exceed every cap. Record it as outstanding; "
                f"changing a cap is a recorded decision, not a table edit (decision ticket 08)")
            row["headroom"] = None
        elif proposed:
            cap = caps.get(proposed)
            if cap is None:
                problems.append(f"{w['id']}: proposed tier {proposed!r} is not one of {TIER_ORDER}")
            else:
                if row["per_case_seconds"] > cap["per_case_seconds"]:
                    problems.append(
                        f"{w['id']}: proposed for the {proposed} tier, whose per-case cap is "
                        f"{cap['per_case_seconds']} s, but the case costs {row['per_case_seconds']} s")
                if row["invocation_seconds"] > cap["invocation_seconds"]:
                    problems.append(
                        f"{w['id']}: proposed for the {proposed} tier, whose invocation cap is "
                        f"{cap['invocation_seconds']} s, but the invocation costs {row['invocation_seconds']} s")
                if row["invocation_worst_case_seconds"] > cap["invocation_seconds"] >= row["invocation_seconds"]:
                    risks.append(
                        f"{w['id']}: placed in the {proposed} tier on its measured invocation time "
                        f"({row['invocation_seconds']} s), but if every one of its {cases} cases cost as much as its "
                        f"slowest ({row['per_case_seconds']} s) the worst case would be "
                        f"{row['invocation_worst_case_seconds']} s, over the {cap['invocation_seconds']} s cap. The "
                        f"margin is the suite's composition, so adding slow cases consumes it")
                row["headroom"] = {
                    "per_case_percent": round(100 * (1 - row["per_case_seconds"] / cap["per_case_seconds"]), 1),
                    "invocation_percent": round(100 * (1 - row["invocation_seconds"] / cap["invocation_seconds"]), 1),
                }
        if w.get("basis") not in ("measured", "derived"):
            problems.append(f"{w['id']}: basis {w.get('basis')!r} is neither 'measured' nor 'derived'")
        elif w["basis"] == "derived" and not w.get("derivation"):
            problems.append(
                f"{w['id']}: recorded as derived with no derivation; a derived figure that does not say "
                f"how it was derived reads as a measured one")
        elif w["basis"] == "measured" and not w.get("evidence"):
            problems.append(f"{w['id']}: recorded as measured but names no attempt or probe as evidence")
        rows.append(row)
    return {"caps": caps, "workloads": rows, "problems": problems, "risks": risks}


def table_markdown(result: dict) -> str:
    lines = [
        "| Workload | Coverage family | Seam | Per case | Cases / invocation | Invocation | Tier | Headroom (case / invocation) | Basis |",
        "|---|---|---|---:|---:|---:|---|---|---|",
    ]
    for w in result["workloads"]:
        tier = w.get("proposed_tier") or w["smallest_fitting_tier"] or "**fits no tier**"
        hr = w.get("headroom")
        hrs = f"{hr['per_case_percent']}% / {hr['invocation_percent']}%" if hr else "—"
        basis = w["basis"]
        if basis == "measured":
            basis += f" ({', '.join(w.get('evidence', []))})"
        lines.append(
            f"| {w['name']} | {w['family']} | {w['seam']} | {w['per_case_seconds']} s | "
            f"{w.get('cases_per_invocation', 1)} | {w['invocation_seconds']} s | {tier} | {hrs} | {basis} |")
    return "\n".join(lines)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("place", "check"):
        p = sub.add_parser(name)
        p.add_argument("--model", required=True)
        if name == "place":
            p.add_argument("--format", choices=("md", "json"), default="md")
    args = ap.parse_args(argv)
    result = place(json.loads(Path(args.model).read_text()))
    if args.cmd == "check":
        for p in result["problems"]:
            print("PROBLEM: " + p)
        for r in result["risks"]:
            print("RISK: " + r)
        print(f"[tier_placement] {len(result['workloads'])} workload(s), {len(result['problems'])} problem(s), "
              f"{len(result['risks'])} recorded risk(s)")
        return 1 if result["problems"] else 0
    print(json.dumps(result, indent=2) if args.format == "json" else table_markdown(result))
    return 0


if __name__ == "__main__":
    sys.exit(main())
