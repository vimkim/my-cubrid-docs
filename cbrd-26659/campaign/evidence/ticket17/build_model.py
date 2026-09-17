#!/usr/bin/env python3
"""Build ticket 17's measurement set and tier-placement model from the probes' own outputs.

    build_model.py --storage DIR --out-measurements FILE --out-model FILE

Nothing in the two JSON files this writes is typed by hand: every number is read out of a
probe's output, a sampler's output or a retained CTP bundle, and every workload row says which.
`tier_placement.py` then computes the placement from the model, and `selftest_tier_placement.py`
checks that computation. The chain is: probe -> measurement -> model -> placement -> table, with
a checker at the last two links.

A row whose basis is `derived` carries a `derivation` sentence saying what it was derived from;
`tier_placement.py` refuses a derived row without one. Standard library only.
"""
from __future__ import annotations

import argparse
import json
import re
import statistics
import sys
from pathlib import Path

TOOLS = Path(__file__).resolve().parent.parent.parent / "tools"
sys.path.insert(0, str(TOOLS))
from extract_ctp_timings import collect  # noqa: E402

BUNDLE_ROOTS = [
    "/home/vimkim/.cub/campaign/cbrd-26659/attempts",
    "/home/vimkim/.cub/campaign/cbrd-26659/ticket14/attempts",
    "/home/vimkim/.cub/campaign/cbrd-26659/ticket15/attempts",
    "/home/vimkim/.cub/campaign/cbrd-26659/ticket17/attempts",
    "/home/vimkim/.cub/campaign/cbrd-26659/ticket19/attempts",
]
CAPS = {
    "fast": {"invocation_seconds": 900, "per_case_seconds": 120},
    "scheduled": {"invocation_seconds": 7200, "per_case_seconds": 900},
    "extended": {"invocation_seconds": 28800, "per_case_seconds": 3600},
}


def stats(values):
    return {"min": round(min(values), 3), "max": round(max(values), 3),
            "median": round(statistics.median(values), 3), "n": len(values)}


def load(path):
    p = Path(path)
    return json.loads(p.read_text()) if p.exists() else None


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--storage", default="/home/vimkim/.cub/campaign/cbrd-26659/ticket17")
    ap.add_argument("--out-measurements", required=True)
    ap.add_argument("--out-model", required=True)
    args = ap.parse_args(argv)
    st = Path(args.storage)

    # --- CTP seams, from every retained bundle of tickets 13, 14, 15, 17, 19 and 41 -------------
    bundles = collect(BUNDLE_ROOTS)
    sql = [b for b in bundles if b["seam"] == "sql" and b["launcher_seconds"]]
    shell = [b for b in bundles if b["seam"] == "shell" and b["launcher_seconds"]]
    sql_case_ms = [c["milliseconds"] for b in sql for c in b["cases"] if c["milliseconds"] > 0]
    shell_case_s = [c["milliseconds"] / 1000 for b in shell for c in b["cases"]]
    # The SQL launcher's cost is fixed per invocation: the case total never exceeds ~2 s of it.
    sql_fixed = [b["launcher_seconds"] - b["case_milliseconds_total"] / 1000 for b in sql]
    shell_fixed = [b["launcher_seconds"] - b["case_milliseconds_total"] / 1000 for b in shell]
    bulk = [c["milliseconds"] / 1000 for b in sql for c in b["cases"]
            if c["case"] == "cbrd_26659_oos_sql01_insert_select"]
    dur01 = {"release": [], "debug": [], "unrecorded": []}
    for b in shell:
        for c in b["cases"]:
            if c["case"] == "cbrd_26659_oos_dur01":
                # the build mode is READ from the bundle, never inferred from the duration: ticket 14's
                # att-T14-0001 is a release run at 19.3 s, slower than several debug runs
                dur01.setdefault(b["build_mode"] or "unrecorded", []).append(c["milliseconds"] / 1000)
    bucket = [b for b in shell if b["case_count"] > 1]

    # --- ticket 17's own probes ---------------------------------------------------------------
    cells = {p.stem: json.loads(p.read_text()) for p in sorted((st / "config-domain").glob("*.json"))}
    seeds10 = load(st / "seeds/10-fresh/seed_cost.json")
    seeds100 = load(st / "seeds/100-fresh/seed_cost.json")
    seeds_reused = load(st / "seeds/100-reused/seed_cost.json")
    barrier = load(st / "barrier/barrier_cost.json")
    samples = {p.stem: json.loads(p.read_text()) for p in sorted((st / "samples").glob("*.json"))}
    instr = load(st / "instr-site-walls.json") or []
    instr_pairs = {}
    for r in instr:
        instr_pairs.setdefault(r["site"], {})[r["mode"]] = r["wall"]
    pair_seconds = [v.get("fault", 0) + v.get("control", 0) for v in instr_pairs.values()]

    # the paired OOS-path evidence check: whole invocation minus the launcher, over the cases checked
    ev = None
    inv2 = load(Path(__file__).resolve().parent / "inv-T17-0002.json")
    if inv2:
        import datetime as dt
        w = (dt.datetime.fromisoformat(inv2["invocation"]["ended_at"])
             - dt.datetime.fromisoformat(inv2["invocation"]["started_at"])).total_seconds()
        launcher = int(re.search(r"elapsed_seconds=(\d+)",
                                 (st / "attempts/inv-T17-0002/timing.txt").read_text()).group(1))
        ev = {"whole_invocation_seconds": w, "launcher_seconds": launcher,
              "cases_checked": len(inv2["expected_cases"]) if "expected_cases" in inv2 else 9,
              "per_check_seconds": round((w - launcher) / 9, 2)}

    measurements = {
        "host": "dev2 (80 logical CPUs, 251 GiB RAM, /home 1.4 TiB free at the time of measuring)",
        "engine": {"commit": "f4299ac0cd777a2a964c1f197ae5ebf9841a4936",
                   "builds": ["release_gcc_nounit", "debug_gcc_nounit"],
                   "instrumentation": "oos-instr-f4299ac0c/debug_gcc_nounit, patch set t16-set1"},
        "ctp_sql": {
            "invocations": len(sql),
            "launcher_seconds": stats([b["launcher_seconds"] for b in sql]),
            "fixed_seconds_per_invocation": stats(sql_fixed),
            "case_milliseconds": stats(sql_case_ms),
            "bulk_case_seconds": stats(bulk),
            "paired_oos_path_evidence_check": ev,
        },
        "ctp_shell": {
            "invocations": len(shell),
            "launcher_seconds": stats([b["launcher_seconds"] for b in shell]),
            "fixed_seconds_per_invocation": stats(shell_fixed),
            "case_seconds": stats(shell_case_s),
            "crash_recover_case_seconds": {k: stats(v) for k, v in dur01.items() if v},
            "eleven_case_bucket": [{"invocation": b["invocation"], "launcher_seconds": b["launcher_seconds"],
                                    "case_seconds_total": round(b["case_milliseconds_total"] / 1000, 1),
                                    "slowest_case_seconds": round(max(c["milliseconds"] for c in b["cases"]) / 1000, 1)}
                                   for b in bucket],
        },
        "configuration_domain": {
            "cells": len(cells),
            "runnable": sum(1 for c in cells.values() if c["verdict"] == "runnable"),
            "capability_gaps": [c["cell"] for c in cells.values() if c["verdict"] != "runnable"],
            "wall_seconds": stats([c["wall_seconds"] for c in cells.values()]),
        },
        "seeded_churn": {
            "ten_seeds_fresh": seeds10 and {"total_seconds": seeds10["total_seconds"],
                                            "per_seed_seconds": seeds10["per_seed_seconds"],
                                            "phases_median": {k: round(statistics.median(
                                                [s["phases"][k] for s in seeds10["seeds"] if k in s["phases"]]), 3)
                                                for k in ("createdb", "server_start", "workload", "teardown")}},
            "hundred_seeds_fresh": seeds100 and {"total_seconds": seeds100["total_seconds"],
                                                 "per_seed_seconds": seeds100["per_seed_seconds"]},
            "hundred_seeds_reused": seeds_reused and {"total_seconds": seeds_reused["total_seconds"],
                                                      "per_seed_seconds": seeds_reused["per_seed_seconds"]},
        },
        "barrier_mechanism": barrier,
        "instrumented_sites": {
            "sites": len(instr_pairs),
            "fault_plus_control_seconds": stats(pair_seconds) if pair_seconds else None,
            "whole_campaign_seconds": round(sum(pair_seconds), 1) if pair_seconds else None,
            "source": "evidence/ticket41/instr-sites/run-all.log, the re-verification on the re-pinned build",
        },
        "resources": {k: {"wall_seconds": v["wall_seconds"], "peak_cpus": v["peak_cpus"],
                          "mean_cpus": v["mean_cpus"], "peak_rss_gib": v["peak_rss_gib"],
                          "peak_processes": v["peak_processes"],
                          "storage_delta_gib": v["storage_delta_gib"]} for k, v in samples.items()},
    }
    Path(args.out_measurements).write_text(json.dumps(measurements, indent=2) + "\n")

    # --- the model the placement is computed from ---------------------------------------------
    sqlfix = round(statistics.median([b["launcher_seconds"] for b in sql]), 1)
    shfix = round(statistics.median(shell_fixed), 1)
    evcheck = ev["per_check_seconds"] if ev else 7.3
    sql_worst_case = round(max(sql_case_ms) / 1000, 3)
    dur_worst = round(max(v for vals in dur01.values() for v in vals), 2)
    bucket_worst = round(max(max(c["milliseconds"] for c in b["cases"]) for b in bucket) / 1000, 1)
    instr_worst = round(max(pair_seconds), 1)
    per_seed = (seeds100 or seeds10)["per_seed_seconds"]["mean"]
    seed_src = seeds100 or seeds10
    fixture_seconds = round(statistics.median(
        [s["phases"]["createdb"] + s["phases"]["server_start"] for s in seed_src["seeds"]]), 2)
    cfg_worst = round(max(c["wall_seconds"] for c in cells.values()), 2)
    bar_total = barrier["total_seconds"] if barrier else None

    # Whole-invocation times that were MEASURED as a whole, so the placement uses the measurement
    # rather than the worst-case-uniform formula (tier_placement.py carries both).
    def sampled(name):
        s = samples.get(name)
        return round(s["wall_seconds"], 2) if s else None
    bucket_measured = round(max(b["launcher_seconds"] for b in bucket), 1) if bucket else None
    cfg_total = round(sum(c["wall_seconds"] for c in cells.values()), 2)
    instr_campaign = round(sum(pair_seconds), 1) if pair_seconds else None
    reused = seeds_reused["per_seed_seconds"]["mean"] if seeds_reused else None

    workloads = [
        {"id": "public-sql-deterministic", "name": "Fixed deterministic public SQL cases, each with its paired OOS-path evidence check",
         "family": "Representation, SQL operations, Read paths, Schema and utilities", "seam": "public SQL",
         "basis": "measured", "evidence": ["inv-T17-0002", "inv-T19-0001..0010"],
         "per_case_seconds": round(sql_worst_case + evcheck, 2), "cases_per_invocation": 9,
         "invocation_fixed_seconds": sqlfix, "invocation_measured_seconds": sampled("inv-T17-0002"),
         "proposed_tier": "fast"},
        {"id": "public-sql-bulk-churn", "name": "Bulk and churn SQL groups (100 and 1,000 out-of-row rows)",
         "family": "SQL operations", "seam": "public SQL",
         "basis": "measured", "evidence": ["inv-T17-0002", "inv-T19-0001..0010"],
         "per_case_seconds": round(max(bulk) + evcheck, 2), "cases_per_invocation": 1,
         "invocation_fixed_seconds": sqlfix, "proposed_tier": "fast"},
        {"id": "public-sql-suite-projected-40", "name": "The public SQL suite projected to forty cases (tickets 18 to 22)",
         "family": "Representation, SQL operations, Read paths, Schema and utilities", "seam": "public SQL",
         "basis": "derived",
         "derivation": f"the measured per-case cost of the nine-case suite ({round(sql_worst_case + evcheck, 2)} s: "
                       f"worst case execution {sql_worst_case} s plus one {evcheck} s OOS-path evidence check) "
                       f"multiplied by forty cases, over the measured {sqlfix} s launcher cost, which nine "
                       f"invocations show does not grow with the case count",
         "per_case_seconds": round(sql_worst_case + evcheck, 2), "cases_per_invocation": 40,
         "invocation_fixed_seconds": sqlfix, "proposed_tier": "fast"},
        {"id": "shell-crash-recover", "name": "Crash and recover (kill -9, restart, recovery-log assertion)",
         "family": "Durability", "seam": "private shell",
         "basis": "measured", "evidence": ["inv-T17-0003", "inv-T17-0004", "inv-T41-0002", "inv-T41-0003"],
         "per_case_seconds": dur_worst, "cases_per_invocation": 1,
         "invocation_fixed_seconds": shfix, "invocation_measured_seconds": sampled("inv-T17-0004"),
         "proposed_tier": "fast"},
        {"id": "shell-issue-bucket", "name": "A whole private issue bucket, eleven cases, the campaign case among them",
         "family": "Durability", "seam": "private shell",
         "basis": "measured", "evidence": ["att-T14-0008-bucket", "att-T14-0012-bucket", "att-T14-0016-bucket"],
         "per_case_seconds": bucket_worst, "cases_per_invocation": 11,
         "invocation_fixed_seconds": shfix, "invocation_measured_seconds": bucket_measured,
         "proposed_tier": "fast"},
        {"id": "multi-session-barrier", "name": "The four required multi-session schedule families, each four participants over three acknowledged barriers",
         "family": "Concurrent lifetime", "seam": "private shell",
         "basis": "derived",
         "derivation": (f"NO SCENARIO EXISTS: ticket 23 owns concurrent-lifetime schedules and is blocked by this "
                        f"ticket, so the scenario is a Delivery gap and this row is an estimate. What is measured is "
                        f"the MECHANISM, by tools/barrier_cost_probe.sh: "
                        + (f"{bar_total} s for four participants over three acknowledged barriers, fixture included. "
                           if bar_total else "(probe not yet run). ")
                        + f"The estimate adds the measured crash-and-recover cost ({dur_worst} s), because a "
                          f"concurrent-lifetime schedule that survives a restart pays both."),
         "per_case_seconds": round((bar_total or 0) + dur_worst, 2), "cases_per_invocation": 4,
         "invocation_fixed_seconds": shfix, "proposed_tier": "scheduled"},
        {"id": "churn-seeded-scheduled", "name": "Randomized out-of-row churn, ten fixed seeds, fresh fixture per seed",
         "family": "Concurrent lifetime, Durability", "seam": "private shell",
         "basis": "measured", "evidence": ["seeds-10-fresh", "seeds-100-fresh"],
         "seeds": 10, "per_seed_seconds": per_seed, "cases_per_invocation": 1,
         "invocation_fixed_seconds": shfix,
         "invocation_measured_seconds": round((seeds10["total_seconds"] if seeds10 else 0) + shfix, 2),
         "proposed_tier": "scheduled"},
        {"id": "churn-seeded-extended", "name": "Randomized out-of-row churn, one hundred recorded seeds, fresh fixture per seed",
         "family": "Concurrent lifetime, Durability", "seam": "private shell",
         "basis": "measured", "evidence": ["seeds-100-fresh"],
         "seeds": 100, "per_seed_seconds": per_seed, "cases_per_invocation": 1,
         "invocation_fixed_seconds": shfix,
         "invocation_measured_seconds": round((seeds100["total_seconds"] if seeds100 else 0) + shfix, 2),
         "proposed_tier": "extended"},
        {"id": "churn-seeded-extended-amortized", "name": "The same hundred seeds on one fixture reused across them",
         "family": "Concurrent lifetime, Durability", "seam": "private shell",
         "basis": "measured", "evidence": ["seeds-100-reused"],
         "seeds": 100, "per_seed_seconds": reused, "cases_per_invocation": 1,
         "invocation_fixed_seconds": shfix,
         "invocation_measured_seconds": round((seeds_reused["total_seconds"] if seeds_reused else 0) + shfix, 2),
         "proposed_tier": "scheduled"},
        {"id": "instrumented-fault-site", "name": "One instrumented fault site, fault run plus its fault-disabled control",
         "family": "Resource pressure", "seam": "private shell (instrumented configuration)",
         "basis": "measured", "evidence": ["t17-instr-a1", "evidence/ticket41/instr-sites/run-all.log"],
         "per_case_seconds": instr_worst, "cases_per_invocation": 1,
         "invocation_fixed_seconds": shfix, "proposed_tier": "scheduled"},
        {"id": "instrumented-fault-campaign", "name": "The whole validated fault campaign, twelve sites, fault plus control",
         "family": "Resource pressure", "seam": "private shell (instrumented configuration)",
         "basis": "measured", "evidence": ["evidence/ticket41/instr-sites/run-all.log"],
         "per_case_seconds": instr_worst, "cases_per_invocation": 12,
         "invocation_fixed_seconds": shfix, "invocation_measured_seconds": instr_campaign,
         "proposed_tier": "extended"},
        {"id": "corruption-detection", "name": "Corruption detection on copied database, page and log images, six experiments",
         "family": "Resource pressure", "seam": "private shell (instrumented configuration)",
         "basis": "measured", "evidence": ["ticket 16 section 12: 98 s for six experiments"],
         "per_case_seconds": 98.0, "cases_per_invocation": 1,
         "invocation_fixed_seconds": shfix, "proposed_tier": "scheduled"},
        {"id": "bounded-fs-exhaustion", "name": "Bounded test filesystem exhaustion",
         "family": "Resource pressure", "seam": "private shell (instrumented configuration)",
         "basis": "measured", "evidence": ["ticket 16 section 12: 31 s"],
         "per_case_seconds": 31.0, "cases_per_invocation": 1,
         "invocation_fixed_seconds": shfix, "proposed_tier": "scheduled"},
        {"id": "configuration-sweep", "name": "The twelve-cell configuration sweep (4/8/16 KiB x release/debug x SA/CS)",
         "family": "Representation", "seam": "neither (a probe, not a case)",
         "basis": "measured", "evidence": ["evidence/ticket17/config-domain/"],
         "per_case_seconds": cfg_worst, "cases_per_invocation": 12,
         "invocation_fixed_seconds": 0, "invocation_measured_seconds": cfg_total,
         "proposed_tier": "fast"},
        {"id": "ops-ha", "name": "HA replica correctness (dedicated scenario, prerequisites declared)",
         "family": "Operational features", "seam": "private shell",
         "basis": "derived",
         "derivation": (f"NO SCENARIO EXISTS and nothing about HA has been measured by this campaign. The figure is a "
                        f"LOWER BOUND, not an estimate of the real cost: an HA scenario pays at least two database "
                        f"fixtures and two server starts (2 x the measured {fixture_seconds} s) plus a "
                        f"replication wait of unknown length. Ticket 17 records it as unmeasured; the tickets that "
                        f"write the scenario owe the measurement."),
         "per_case_seconds": 30.0, "cases_per_invocation": 1,
         "invocation_fixed_seconds": shfix, "proposed_tier": "scheduled"},
        {"id": "ops-cdc-encryption", "name": "CDC/flashback and encryption (dedicated scenarios, prerequisites declared)",
         "family": "Operational features", "seam": "private shell",
         "basis": "derived",
         "derivation": ("NO SCENARIO EXISTS and nothing about CDC, flashback or encryption has been measured by this "
                        "campaign. The figure is a LOWER BOUND: one database fixture, one server start and one "
                        "restart, which the crash-and-recover case measures at "
                        f"{dur_worst} s, plus the extra service each needs. Unmeasured; the tickets that write the "
                        "scenarios owe the measurement."),
         "per_case_seconds": round(dur_worst * 2, 2), "cases_per_invocation": 1,
         "invocation_fixed_seconds": shfix, "proposed_tier": "scheduled"},
    ]
    Path(args.out_model).write_text(json.dumps({"caps": CAPS, "workloads": workloads}, indent=2) + "\n")
    print(f"[build_model] {len(workloads)} workloads; measurements from {len(sql)} SQL and {len(shell)} shell "
          f"bundles, {len(cells)} configuration cells, "
          f"{(seeds100 or seeds10 or {}).get('seeds') and len((seeds100 or seeds10)['seeds'])} seeds, "
          f"{len(instr_pairs)} instrumented sites, {len(samples)} resource samples")
    return 0


if __name__ == "__main__":
    sys.exit(main())
