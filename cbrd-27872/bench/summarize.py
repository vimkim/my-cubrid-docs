#!/usr/bin/env python3
"""Summarize growth_cost.py results.csv: per build, item and metric, n / median / p95 / min / max.

Concurrent workers are pooled into conc_ms / conc_fetches (all workers) and conc_max_ms (slowest per iteration).
"""
import csv
import statistics
import sys
from collections import defaultdict


def pct(xs, q):
    xs = sorted(xs)
    return xs[min(len(xs) - 1, max(0, round(q * (len(xs) - 1))))]


def main(path, labels=None):
    data = defaultdict(list)
    conc_iter = defaultdict(list)
    shas = {}
    with open(path) as fh:
        for row in csv.DictReader(fh):
            lab, item, metric = row["label"], row["item"], row["metric"]
            if labels and lab not in labels:
                continue
            shas[lab] = row["sha"]
            v = float(row["value"])
            if item == "concurrent" and metric.startswith("w"):
                kind = "ms" if metric.endswith("_ms") else "fetches"
                data[(lab, item, f"conc_{kind}")].append(v)
                if kind == "ms":
                    conc_iter[(lab, row["round"], row["iter"])].append(v)
                continue
            data[(lab, item, metric)].append(v)
    for (lab, rnd, it), xs in conc_iter.items():
        data[(lab, "concurrent", "conc_max_ms")].append(max(xs))
    print("| build | item | metric | n | median | p95 | min | max |")
    print("| --- | --- | --- | --- | --- | --- | --- | --- |")
    for key in sorted(data, key=lambda k: (k[1], k[2], k[0])):
        lab, item, metric = key
        xs = data[key]
        print(f"| {lab} ({shas[lab][:9]}) | {item} | {metric} | {len(xs)} | {statistics.median(xs):g} | "
              f"{pct(xs, 0.95):g} | {min(xs):g} | {max(xs):g} |")


if __name__ == "__main__":
    main(sys.argv[1], set(sys.argv[2:]) or None)
