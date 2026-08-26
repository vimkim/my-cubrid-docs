#!/usr/bin/env python3
"""Analyze A/B/D padding-control timings without discarding raw observations."""

import csv
import json
import math
import random
import statistics
import sys
from collections import defaultdict


COMPARISONS = (("A", "B"), ("B", "D"), ("A", "D"))


def percentile(values, fraction):
    ordered = sorted(values)
    index = min(len(ordered) - 1, math.floor(fraction * len(ordered)))
    return ordered[index]


def summarize(values):
    median = statistics.median(values)
    deviations = [abs(value - median) for value in values]
    mad = statistics.median(deviations)
    robust_limit = median + 3.0 * 1.4826 * mad
    return {
        "n": len(values),
        "mean": statistics.fmean(values),
        "median": median,
        "stdev": statistics.stdev(values) if len(values) > 1 else 0.0,
        "min": min(values),
        "max": max(values),
        "mad": mad,
        "robust_high_outliers": [value for value in values if mad and value > robust_limit],
    }


def unpaired_bootstrap(left, right, rng, samples=100_000):
    observed = statistics.median(right) / statistics.median(left)
    ratios = []
    for _ in range(samples):
        left_draw = [left[rng.randrange(len(left))] for _ in left]
        right_draw = [right[rng.randrange(len(right))] for _ in right]
        ratios.append(statistics.median(right_draw) / statistics.median(left_draw))
    return {
        "estimator": "ratio of independently resampled medians",
        "right_over_left": observed,
        "percent": (observed - 1.0) * 100.0,
        "ci95": [percentile(ratios, 0.025), percentile(ratios, 0.975)],
        "bootstrap_samples": samples,
    }


def paired_round_bootstrap(rounds, left, right, rng, samples=100_000):
    pairs = [(values[left], values[right]) for _, values in sorted(rounds.items())]
    observed = statistics.median([right_value / left_value for left_value, right_value in pairs])
    ratios = []
    for _ in range(samples):
        draw = [pairs[rng.randrange(len(pairs))] for _ in pairs]
        ratios.append(statistics.median([right_value / left_value for left_value, right_value in draw]))
    return {
        "estimator": "median ratio of per-round variant means",
        "right_over_left": observed,
        "percent": (observed - 1.0) * 100.0,
        "ci95": [percentile(ratios, 0.025), percentile(ratios, 0.975)],
        "bootstrap_samples": samples,
        "rounds": len(pairs),
        "right_slower_rounds": sum(right_value > left_value for left_value, right_value in pairs),
        "right_faster_rounds": sum(right_value < left_value for left_value, right_value in pairs),
    }


def main(path):
    rows = []
    with open(path, newline="", encoding="utf-8") as stream:
        for row in csv.DictReader(stream):
            row["run"] = int(row["run"])
            row["position"] = int(row["position"])
            row["seconds"] = float(row["seconds"])
            for field in ("read_bytes", "write_bytes", "minflt", "majflt", "utime_ticks", "stime_ticks"):
                row[field] = int(row[field])
            rows.append(row)

    variants = defaultdict(list)
    positions = defaultdict(list)
    round_values = defaultdict(lambda: defaultdict(list))
    for row in rows:
        variants[row["variant"]].append(row["seconds"])
        positions[(row["variant"], row["position"])].append(row["seconds"])
        round_values[row["run"]][row["variant"]].append(row["seconds"])

    if set(variants) != {"A", "B", "D"}:
        raise SystemExit(f"incomplete variant set: {sorted(variants)}")

    balanced_rounds = {}
    for run, values in sorted(round_values.items()):
        if set(values) != {"A", "B", "D"}:
            raise SystemExit(f"incomplete run {run}: {sorted(values)}")
        counts = {variant: len(items) for variant, items in values.items()}
        if len(set(counts.values())) != 1:
            raise SystemExit(f"unbalanced run {run}: {counts}")
        balanced_rounds[run] = {
            variant: statistics.fmean(items) for variant, items in values.items()
        }

    rng = random.Random(26382)
    output = {
        "input": path,
        "rows": len(rows),
        "summary": {variant: summarize(values) for variant, values in sorted(variants.items())},
        "by_position": {
            f"{variant}/position-{position}": summarize(values)
            for (variant, position), values in sorted(positions.items())
        },
        "physical_io": {
            field: sorted({row[field] for row in rows})
            for field in ("read_bytes", "write_bytes", "majflt")
        },
        "unpaired_bootstrap": {},
        "paired_round_bootstrap": {},
        "per_round_means": balanced_rounds,
    }
    for left, right in COMPARISONS:
        key = f"{right}_over_{left}"
        output["unpaired_bootstrap"][key] = unpaired_bootstrap(
            variants[left], variants[right], rng
        )
        output["paired_round_bootstrap"][key] = paired_round_bootstrap(
            balanced_rounds, left, right, rng
        )
    print(json.dumps(output, indent=2, sort_keys=True))


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit(f"usage: {sys.argv[0]} PADDING.csv")
    main(sys.argv[1])
