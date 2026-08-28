#!/usr/bin/env python3
"""Summarize pgo-bench results: per-variant stats + pairwise comparison."""
import csv
import math
import statistics
import sys
from collections import defaultdict


def mann_whitney_u(xs, ys):
    """Two-sided Mann-Whitney U with normal approximation (ties averaged)."""
    combined = [(v, 0) for v in xs] + [(v, 1) for v in ys]
    combined.sort()
    ranks = {}
    i = 0
    while i < len(combined):
        j = i
        while j + 1 < len(combined) and combined[j + 1][0] == combined[i][0]:
            j += 1
        avg_rank = (i + j) / 2 + 1
        for k in range(i, j + 1):
            ranks[k] = avg_rank
        i = j + 1
    r1 = sum(ranks[k] for k, (_, g) in enumerate(combined) if g == 0)
    n1, n2 = len(xs), len(ys)
    u1 = r1 - n1 * (n1 + 1) / 2
    mu = n1 * n2 / 2
    sigma = math.sqrt(n1 * n2 * (n1 + n2 + 1) / 12)
    if sigma == 0:
        return u1, float("nan")
    z = (u1 - mu) / sigma
    p = 2 * (1 - 0.5 * (1 + math.erf(abs(z) / math.sqrt(2))))
    return u1, p


def main(path):
    data = defaultdict(list)
    with open(path) as f:
        for row in csv.reader(f):
            if not row or row[0] == "variant":
                continue
            data[row[0]].append(float(row[1]))

    variants = sorted(data)
    for v in variants:
        xs = data[v]
        print(
            f"{v}: n={len(xs)} mean={statistics.mean(xs):.4f} "
            f"median={statistics.median(xs):.4f} "
            f"stdev={statistics.stdev(xs) if len(xs) > 1 else 0:.4f} "
            f"min={min(xs):.4f} max={max(xs):.4f}"
        )

    if len(variants) == 2:
        a, b = variants
        med_a, med_b = statistics.median(data[a]), statistics.median(data[b])
        mean_a, mean_b = statistics.mean(data[a]), statistics.mean(data[b])
        print(f"\n{b} vs {a}:")
        print(f"  median delta: {100 * (med_b - med_a) / med_a:+.3f}%")
        print(f"  mean   delta: {100 * (mean_b - mean_a) / mean_a:+.3f}%")
        u, p = mann_whitney_u(data[a], data[b])
        print(f"  Mann-Whitney U={u:.1f} two-sided p={p:.5f}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "results.csv")
