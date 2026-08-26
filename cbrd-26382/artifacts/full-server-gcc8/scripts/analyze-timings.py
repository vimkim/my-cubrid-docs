#!/usr/bin/env python3
import csv
import json
import math
import random
import statistics
import sys
from collections import defaultdict


def summarize(values):
    mean = statistics.fmean(values)
    stdev = statistics.stdev(values) if len(values) > 1 else 0.0
    ordered = sorted(values)
    trim = math.floor(len(ordered) * 0.1)
    trimmed = ordered[trim : len(ordered) - trim] if trim else ordered
    return {
        "n": len(values),
        "mean": mean,
        "trimmed_mean_10_percent": statistics.fmean(trimmed),
        "median": statistics.median(values),
        "stdev": stdev,
        "cv_percent": stdev / mean * 100.0,
        "min": min(values),
        "max": max(values),
    }


def paired_bootstrap(pairs, seed=26382, samples=100_000):
    rng = random.Random(seed)
    observed = statistics.median([right for _, right in pairs]) / statistics.median([left for left, _ in pairs])
    ratios = []
    count = len(pairs)
    for _ in range(samples):
        draw = [pairs[rng.randrange(count)] for _ in range(count)]
        ratios.append(
            statistics.median([right for _, right in draw])
            / statistics.median([left for left, _ in draw])
        )
    ratios.sort()
    lo = ratios[math.floor(0.025 * samples)]
    hi = ratios[math.ceil(0.975 * samples) - 1]
    return {
        "right_over_left": observed,
        "percent": (observed - 1.0) * 100.0,
        "ci95": [lo, hi],
        "bootstrap_samples": samples,
        "right_slower_pairs": sum(right > left for left, right in pairs),
        "right_faster_pairs": sum(right < left for left, right in pairs),
        "ties": sum(right == left for left, right in pairs),
    }


def main(path):
    rows = []
    with open(path, newline="", encoding="utf-8") as stream:
        for row in csv.DictReader(stream):
            row["seconds"] = float(row["seconds"])
            row["series"] = int(row["series"])
            row["round"] = int(row["round"])
            rows.append(row)

    output = {"input": path}
    for phase in ("warmup", "qa-five", "randomized"):
        grouped = defaultdict(list)
        for row in rows:
            if row["phase"] == phase:
                grouped[row["variant"]].append(row["seconds"])
        output[phase] = {variant: summarize(values) for variant, values in sorted(grouped.items())}

    triplets = defaultdict(dict)
    for row in rows:
        if row["phase"] == "randomized":
            triplets[(row["series"], row["round"])][row["variant"]] = row["seconds"]
    if len(triplets) != 60 or any(set(values) != {"A", "B", "C"} for values in triplets.values()):
        raise SystemExit(f"incomplete randomized matrix: {len(triplets)} triplets")

    output["paired"] = {}
    for left, right in (("A", "B"), ("B", "C"), ("A", "C")):
        pairs = [(values[left], values[right]) for _, values in sorted(triplets.items())]
        output["paired"][f"{right}_over_{left}"] = paired_bootstrap(pairs)

    series = defaultdict(lambda: defaultdict(list))
    for row in rows:
        if row["phase"] == "randomized":
            series[row["series"]][row["variant"]].append(row["seconds"])
    output["series"] = {
        str(number): {variant: summarize(values) for variant, values in sorted(groups.items())}
        for number, groups in sorted(series.items())
    }
    print(json.dumps(output, indent=2, sort_keys=True))


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit(f"usage: {sys.argv[0]} TIMINGS.csv")
    main(sys.argv[1])
