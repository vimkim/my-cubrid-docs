#!/usr/bin/env python3
"""Paired comparison of two builds in growth_cost.py results.csv.

One server run (round) is the independent unit: samples inside a run share its noise. For each
item/metric the script takes the median of each run and then compares the runs of the two builds,
pairing run k of one build with the next run of the other (rounds alternate, so a pair is the two
runs closest in time). It prints the difference of run medians, how many pairs favour each side, and
the spread of the run medians. A Mann-Whitney U test on the pooled samples is not used: samples of
one run are not independent.

With several `results.csv base new` triples the run pairs of all triples are pooled in a second table,
with a two-sided sign test on the paired differences.

usage: paired_rounds.py results.csv base_label new_label [results2.csv base2 new2 ...]
"""
import csv
import math
import statistics
import sys
from collections import defaultdict

METRICS = (
    ("restart", "first_ms"), ("restart", "second_ms"),
    ("delete_empties", "after_delete_ms"), ("delete_empties", "no_delete_ms"),
    ("delete_keeps", "after_delete_ms"), ("delete_keeps", "no_delete_ms"),
    ("plain", "ms"),
    ("concurrent", "conc_max_ms"), ("concurrent", "conc_ms"),
)


def sign_test_p(slower, total):
    """Two-sided exact binomial test of slower ~ Binomial(total, 1/2)."""
    if total == 0:
        return float("nan")
    k = min(slower, total - slower)
    tail = sum(math.comb(total, i) for i in range(k + 1)) / 2 ** total
    return min(1.0, 2 * tail)


def main(path, base, new):
    pooled = {}
    runs = defaultdict(lambda: defaultdict(list))
    conc_iter = defaultdict(list)
    order = {}
    with open(path) as fh:
        for n, row in enumerate(csv.DictReader(fh)):
            lab = row["label"]
            if lab not in (base, new):
                continue
            order.setdefault((lab, row["round"]), n)
            item, metric, v = row["item"], row["metric"], float(row["value"])
            if item == "concurrent" and metric.startswith("w") and metric.endswith("_ms"):
                runs[(lab, "concurrent", "conc_ms")][row["round"]].append(v)
                conc_iter[(lab, row["round"], row["iter"])].append(v)
                continue
            runs[(lab, item, metric)][row["round"]].append(v)
    for (lab, rnd, it), xs in conc_iter.items():
        runs[(lab, "concurrent", "conc_max_ms")][rnd].append(max(xs))
    spread = defaultdict(list)
    for (lab, rnd, it), xs in conc_iter.items():
        spread[lab].append((max(xs) - min(xs)) / (len(xs) - 1))
    print(f"| item | metric | runs {base}/{new} | run-median spread {base} | run-median spread {new} | "
          f"median of paired diffs ({new} - {base}) | pairs {new} slower / total |")
    print("| --- | --- | --- | --- | --- | --- | --- |")
    for item, metric in METRICS:
        a, b = runs.get((base, item, metric)), runs.get((new, item, metric))
        if not a or not b:
            continue
        ma = {r: statistics.median(v) for r, v in a.items()}
        mb = {r: statistics.median(v) for r, v in b.items()}
        seq = sorted([(order[(base, r)], base, r) for r in ma] + [(order[(new, r)], new, r) for r in mb])
        diffs = []
        pending = {}
        for _, lab, r in seq:
            other = new if lab == base else base
            if other in pending:
                o = pending.pop(other)
                x, y = (ma[o], mb[r]) if lab == new else (ma[r], mb[o])
                diffs.append(y - x)
            else:
                pending[lab] = r
        va, vb = sorted(ma.values()), sorted(mb.values())
        slower = sum(1 for d in diffs if d > 0)
        pooled[(item, metric)] = diffs
        print(f"| {item} | {metric} | {len(ma)}/{len(mb)} | {va[0]:.3g}-{va[-1]:.3g} | {vb[0]:.3g}-{vb[-1]:.3g} | "
              f"{statistics.median(diffs):+.3g} | {slower}/{len(diffs)} |" if diffs else
              f"| {item} | {metric} | {len(ma)}/{len(mb)} | | | | |")
    tail_notes(spread)
    return pooled


def tail_notes(spread_by_label):
    for lab, xs in spread_by_label.items():
        xs = sorted(xs)
        print(f"\n{lab}: (slowest - fastest session) / 7 per concurrent iteration, upper bound of one serialized step: "
              f"median {statistics.median(xs):.2f} ms, range {xs[0]:.2f}-{xs[-1]:.2f} ms, n={len(xs)}")


if __name__ == "__main__":
    args = sys.argv[1:]
    all_diffs = defaultdict(list)
    for i in range(0, len(args), 3):
        for key, diffs in main(*args[i:i + 3]).items():
            all_diffs[key].extend(diffs)
        print()
    if len(args) > 3:
        print("| item | metric | pooled pairs | median of paired diffs | slower / total | sign test p |")
        print("| --- | --- | --- | --- | --- | --- |")
        for (item, metric), d in all_diffs.items():
            slower = sum(1 for x in d if x > 0)
            print(f"| {item} | {metric} | {len(d)} | {statistics.median(d):+.3g} | {slower}/{len(d)} | "
                  f"{sign_test_p(slower, len(d)):.2f} |")
