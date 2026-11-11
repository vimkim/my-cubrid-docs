#!/usr/bin/env python3
"""Per-cycle peak pages and sectors of churn_scale.py runs, which write several row counts under one round.

Splits each (label, round) at its pages_initial rows, in file order, and labels the churns with --rows in the
order churn_scale.py ran them. The peak of a cycle is its largest snapshot (pages after the UPDATE, the UPDATE
drain, the DELETE drain and the re-INSERT).
usage: scale_peaks.py results.csv --rows 2000 6000
"""
import argparse
import csv
from collections import defaultdict

SNAP = ("pages_peak_update", "pages_after_update_drain", "pages_after_delete_drain", "pages_after_reinsert")

ap = argparse.ArgumentParser()
ap.add_argument("csv")
ap.add_argument("--rows", type=int, nargs="+", required=True)
a = ap.parse_args()
runs = defaultdict(list)
with open(a.csv) as fh:
    for r in csv.DictReader(fh):
        if r["item"] != "churn":
            continue
        key = (r["label"], int(r["round"]))
        if r["metric"] == "pages_initial":
            runs[key].append({"initial": int(r["value"]), "peak": defaultdict(int), "sectors": None})
            continue
        cur = runs[key][-1]
        if r["metric"] in SNAP:
            cy = int(r["iter"])
            cur["peak"][cy] = max(cur["peak"][cy], int(float(r["value"])))
        elif r["metric"] == "sectors_c":
            cur["sectors"] = int(r["value"])
print("| rows | build | round | initial | peak per cycle | sectors c |")
print("| --- | --- | --- | --- | --- | --- |")
for (label, rnd), lst in sorted(runs.items()):
    for rows, run in zip(a.rows, lst):
        peaks = " / ".join(str(run["peak"][c]) for c in sorted(run["peak"]))
        print(f"| {rows} | {label} | {rnd} | {run['initial']} | {peaks} | {run['sectors']} |")
