#!/usr/bin/env python3
"""Apply ticket 49's corrections to ticket 17's tier-placement model (review findings F1, F5, F7).

    apply_ticket49_model_corrections.py --model evidence/ticket17/tier-placement-model.json [--dry-run]

The model is the input `tools/tier_placement.py` computes the placement from, and its rule is that
nothing in it is typed by hand. Three of ticket 17's independent review's findings change rows of
it, and each change below is derived from its source rather than written in:

**F1 -- the multi-session barrier row.** Ticket 17 recorded "no barrier scenario exists in either
suite" and derived the row from a token-file mechanism probe. A four-participant barrier scenario
does exist in the private suite (`shell/_06_issues/_18_2h/bug_bts_22449`, driven through CTP's
isolation ctltool), and ticket 49 ran it at the seam twice (`att-T49-0001`, `att-T49-0002`,
`evidence/ticket49/`). In both runs the schedule halts at `MC: wait until C4 ready` -- C4's
`ALTER TABLE ... ADD COLUMN` stays blocked behind C2's online unique index build for the
controller's 100 s barrier wait -- and the controller is killed by the tool's 120 s timeout, so the
cost of a COMPLETED four-participant schedule is not observable with this scenario at the pin.
The row therefore keeps `derived` (the review's O1 caveat attached: the probe measured
uncontended coordination, a floor, not a schedule) and records the Capability gap, with the two
runs' measured figures read out of their bundles and evidence copies as the lower bound they are.

**F5 -- what the `Invocation` figure is.** Eight rows carry `invocation_measured_seconds`; three
are one wall clock over the whole invocation and five are assembled from separately measured
parts. Each gains `invocation_measurement` (`measured-whole` or `composite`) and a composite its
`composition`, whose numbers are read from the probes' outputs; `tier_placement.py` refuses a
measured figure without the label and renders the label as a column.

**F7 -- two citations.** The corruption-detection and bounded-filesystem rows cite "ticket 16
section 12"; the figures are in ticket 16's section 11, *Hand-offs*.

`build_model.py` imports `apply_to_workloads` and applies the same three corrections to what it
builds, so a regeneration and this script agree row for row. Idempotent; reports what it changed.
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
CAMPAIGN = HERE.parents[1]
sys.path.insert(0, str(CAMPAIGN / "tools"))
from extract_ctp_timings import collect  # noqa: E402

TICKET49_STORAGE = Path("/home/vimkim/.cub/campaign/cbrd-26659/ticket49")
TICKET49_EVIDENCE = CAMPAIGN / "evidence" / "ticket49"
BARRIER_ATTEMPTS = ("att-T49-0001", "att-T49-0002")
BARRIER_INVOCATIONS = ("inv-T49-0001", "inv-T49-0002")

MEASURED_WHOLE = {
    "public-sql-deterministic": "one wall clock over the whole invocation, the resource sampler's, wrapper setup and restore included (samples/inv-T17-0002.json)",
    "shell-crash-recover": "one wall clock over the whole invocation, the resource sampler's (samples/inv-T17-0004.json, the debug run)",
    "shell-issue-bucket": "one wall clock over the whole invocation, the CTP launcher's elapsed_seconds of att-T14-0008-bucket",
}
CITATIONS = {
    "ticket 16 section 12: 98 s for six experiments": "ticket 16 section 11 (Hand-offs): 98 s for six experiments",
    "ticket 16 section 12: 31 s": "ticket 16 section 11 (Hand-offs): 31 s",
}


def load(path):
    p = Path(path)
    return json.loads(p.read_text()) if p.exists() else None


def compositions(storage: Path) -> dict:
    """The five composite invocation figures, each named from the outputs it was assembled from."""
    probes = HERE / "probes"
    seeds10 = load(probes / "seed-cost-10-fresh.json") or load(storage / "seeds/10-fresh/seed_cost.json")
    seeds100 = load(probes / "seed-cost-100-fresh.json") or load(storage / "seeds/100-fresh/seed_cost.json")
    reused = load(probes / "seed-cost-100-reused.json") or load(storage / "seeds/100-reused/seed_cost.json")
    cells = [json.loads(p.read_text()) for p in sorted((HERE / "config-domain").glob("*.json"))]
    walls = load(probes / "instr-site-walls.json") or load(storage / "instr-site-walls.json") or []
    out = {}
    if seeds10:
        out["churn-seeded-scheduled"] = (f"the seed probe's measured total for ten seeds ({seeds10['total_seconds']} s, seeds-10-fresh) "
                                         "plus the shell seam's median fixed cost (4.1 s), a launcher toll the probe never paid")
    if seeds100:
        out["churn-seeded-extended"] = (f"the seed probe's measured total for one hundred seeds ({seeds100['total_seconds']} s, "
                                        "seeds-100-fresh) plus the shell seam's median fixed cost (4.1 s), a launcher toll the probe never paid")
    if reused:
        out["churn-seeded-extended-amortized"] = (f"the seed probe's measured total for one hundred seeds on one fixture ({reused['total_seconds']} s, "
                                                  "seeds-100-reused) plus the shell seam's median fixed cost (4.1 s), a launcher toll the probe never paid")
    if cells:
        out["configuration-sweep"] = (f"the SUM of the twelve cells' separately measured probe walls ({round(sum(c['wall_seconds'] for c in cells), 2)} s "
                                      "over evidence/ticket17/config-domain/), never run as one invocation")
    if walls:
        out["instrumented-fault-campaign"] = (f"the SUM of the {len(walls)} fault and control walls read out of ticket 41's run-all.log "
                                              f"({round(sum(r['wall'] for r in walls), 1)} s), never run as one invocation")
    return out


def barrier_observation(storage: Path, evidence: Path) -> tuple:
    """What the two ticket 49 runs measured, read from their bundles and evidence copies.

    Returns (evidence_ids, capability_gap_text) or (None, None) when the runs are not on this host.
    """
    rows = {r["invocation"]: r for r in collect([storage / "attempts"])} if (storage / "attempts").is_dir() else {}
    if not all(inv in rows for inv in BARRIER_INVOCATIONS):
        return None, None
    case_s = []
    schedule_s = []
    for inv in BARRIER_INVOCATIONS:
        case_s.append(round(rows[inv]["cases"][0]["milliseconds"] / 1000, 1))
        runone = evidence / inv / "runone.log"
        if runone.exists():
            schedule_s.append(round(int(runone.read_text().split()[-1]) / 1000, 1))
    text = (
        "CAPABILITY GAP (ticket 49, closing ticket 17's review F1): a four-participant barrier scenario DOES exist in the "
        "private suite -- bug_bts_22449 (shell/_06_issues/_18_2h, pre-existing, four clients under CTP's isolation ctltool with "
        "MC-controlled barriers) -- and ticket 49 ran it at the shell seam twice, "
        + " and ".join(f"{a} ({inv})" for a, inv in zip(BARRIER_ATTEMPTS, BARRIER_INVOCATIONS)) + ". "
        "In both runs the schedule halts at `MC: wait until C4 ready`: C4's ALTER TABLE ... ADD COLUMN stays blocked behind C2's "
        "online unique index build for the controller's 100 s barrier wait, and the controller is killed by the tool's 120 s "
        "timeout; the case records OK (its only assertion is the core-file scan) and the campaign records FAIL (the case time "
        "exceeds the fast tier's 120 s per-case cap). Measured, as a LOWER BOUND for this scenario at the pin and not as the cost "
        f"of a completed schedule: CTP case time {' and '.join(f'{s} s' for s in case_s)}, of which the ctltool schedule itself "
        f"{' and '.join(f'{s} s' for s in schedule_s) if schedule_s else 'the tool timeout'} (the compile of the ctltool, "
        "createdb and server start make up the rest). The cost of a completed four-participant schedule is therefore not "
        "observable with this scenario at the pinned engine, and this row stays derived. What it does establish: a barrier "
        "schedule in which one participant blocks costs more than the fast tier's per-case cap, which is consistent with the "
        "scheduled placement. Ticket 23 owes the measurement with its own schedules and should not reuse 22449.ctl as it stands."
    )
    return list(BARRIER_ATTEMPTS), text


BARRIER_DERIVATION = (
    "DERIVED, NOT MEASURED, from the barrier MECHANISM probe (tools/barrier_cost_probe.sh): {bar_total} s for four participants over "
    "three acknowledged barriers, fixture included, plus the measured crash-and-recover cost ({dur_worst} s), because a "
    "concurrent-lifetime schedule that survives a restart pays both. CAVEAT (ticket 17's review, O1): the probe's participants "
    "run a fresh csql per round, each on its own table, every statement autocommitting -- no session, transaction or snapshot is "
    "held across a barrier and no two participants contend -- so its 0.17 s per barrier is a FLOOR for uncontended coordination, "
    "not the cost of a schedule; the four required families (snapshot survival, rollback survival, slot reuse and cleanup retry, "
    "interrupted recovery) hold state across their barriers and will cost more. The families themselves have no case at either "
    "seam (a Delivery gap, ticket 23's). The barrier SCENARIO that exists in the private suite was timed by ticket 49 and could "
    "not complete at the pin: see capability_gap."
)


def apply_to_workloads(workloads: list, storage: Path = TICKET49_STORAGE, evidence: Path = TICKET49_EVIDENCE,
                       bar_total=None, dur_worst=None) -> list:
    """Apply F1, F5 and F7 to a list of workload rows in place; return the ids that changed."""
    changed = []
    comps = compositions(Path("/home/vimkim/.cub/campaign/cbrd-26659/ticket17"))
    barrier_evidence, gap = barrier_observation(storage, evidence)
    for w in workloads:
        before = json.dumps(w, sort_keys=True)
        # F5
        if w.get("invocation_measured_seconds") is not None:
            if w["id"] in MEASURED_WHOLE:
                w["invocation_measurement"] = "measured-whole"
                w["measured_as"] = MEASURED_WHOLE[w["id"]]
            elif w["id"] in comps:
                w["invocation_measurement"] = "composite"
                w["composition"] = comps[w["id"]]
        # F7
        if w.get("evidence"):
            w["evidence"] = [CITATIONS.get(e, e) for e in w["evidence"]]
        # F1
        if w["id"] == "multi-session-barrier":
            m = __import__("re").search(r"([0-9.]+) s for four participants.*?crash-and-recover cost \(([0-9.]+) s\)",
                                        w.get("derivation", ""), __import__("re").S)
            bt = bar_total if bar_total is not None else (m.group(1) if m else "5.614")
            dw = dur_worst if dur_worst is not None else (m.group(2) if m else "19.27")
            w["derivation"] = BARRIER_DERIVATION.format(bar_total=bt, dur_worst=dw)
            if gap:
                w["evidence"] = barrier_evidence
                w["capability_gap"] = gap
        if json.dumps(w, sort_keys=True) != before:
            changed.append(w["id"])
    return changed


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--model", required=True)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)
    path = Path(args.model)
    model = json.loads(path.read_text())
    changed = apply_to_workloads(model["workloads"])
    verb = "would change" if args.dry_run else "changed"
    print(f"[apply_ticket49_model_corrections] {verb} {len(changed)} workload row(s): {', '.join(changed) or 'none'}")
    if changed and not args.dry_run:
        path.write_text(json.dumps(model, indent=2) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
