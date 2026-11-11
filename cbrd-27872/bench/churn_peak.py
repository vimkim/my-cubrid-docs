#!/usr/bin/env python3
"""ADR-0009 decision 4 on growth_cost.py churn rows: per-cycle peak pages and reserved sectors.

Per (build, rep) the peak of cycle k is the largest page count among the four snapshots of that cycle
(after UPDATE, after the UPDATE drain, after the DELETE drain, after the re-INSERT). The cycle passes when
its peak <= first cycle's peak + max(2, ceil(10%)). The sector check compares the file's reserved sectors
after the last cycle with the sectors the first cycle's peak needs (64 pages per sector).

usage: churn_peak.py results.csv [label ...]
"""
import csv
import math
import statistics
import sys
from collections import defaultdict

SNAPSHOTS = ("pages_peak_update", "pages_after_update_drain", "pages_after_delete_drain", "pages_after_reinsert")
SECTOR_PAGES = 64


def main(path, labels):
    pages = defaultdict(dict)
    sectors = {}
    with open(path) as fh:
        for row in csv.DictReader(fh):
            if row["item"] != "churn" or (labels and row["label"] not in labels):
                continue
            key = (row["label"], int(row["round"]))
            m, v, cy = row["metric"], int(float(row["value"])), int(row["iter"])
            if m in SNAPSHOTS:
                pages[key].setdefault(cy, {})[m] = v
            elif m == "sectors_c":
                sectors[key] = v
    print("| build | rep | cycle 1 peak | cycle peaks 1..N | worst cycle vs first | allowance | passes | sectors c | sectors needed by first peak |")
    print("| --- | --- | --- | --- | --- | --- | --- | --- | --- |")
    summary = defaultdict(list)
    for key in sorted(pages):
        per = pages[key]
        peaks = [max(per[cy].values()) for cy in sorted(per)]
        first = peaks[0]
        allow = max(2, math.ceil(first * 0.10))
        worst = max(p - first for p in peaks)
        ok = worst <= allow
        need = math.ceil(first / SECTOR_PAGES)
        sec = sectors.get(key)
        summary[key[0]].append((ok, worst, sec, need, first, peaks))
        print(f"| {key[0]} | {key[1]} | {first} | {', '.join(map(str, peaks))} | {worst:+d} | {allow} | "
              f"{'yes' if ok else 'NO'} | {sec} | {need} |")
    print()
    for lab, rows in summary.items():
        firsts = [r[4] for r in rows]
        worsts = [r[1] for r in rows]
        allp = [p for r in rows for p in r[5]]
        print(f"{lab}: reps={len(rows)}, all pass={all(r[0] for r in rows)}, first-cycle peak median={statistics.median(firsts)} "
              f"range={min(firsts)}-{max(firsts)}, worst cycle minus first: median={statistics.median(worsts):+g} "
              f"range={min(worsts):+d}..{max(worsts):+d}, all cycle peaks range={min(allp)}-{max(allp)}, "
              f"sectors c={sorted(set(r[2] for r in rows))}, sectors needed by first peak={sorted(set(r[3] for r in rows))}")


if __name__ == "__main__":
    main(sys.argv[1], set(sys.argv[2:]) or None)
