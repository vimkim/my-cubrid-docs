#!/usr/bin/env python3
import csv
import json
import math
import random
import statistics
import sys
from collections import defaultdict


def load(path):
    with open(path, newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    for row in rows:
        row["seconds"] = float(row["seconds"])
        for name in ("server_migrations", "server_context_switches", "migrations", "switches",
                     "read_bytes", "majflt", "minflt", "utime_ticks", "stime_ticks"):
            if name in row:
                row[name] = float(row[name])
    return rows


def summarize(values):
    return {
        "n": len(values),
        "mean": statistics.fmean(values),
        "median": statistics.median(values),
        "stdev": statistics.stdev(values) if len(values) > 1 else 0.0,
        "min": min(values),
        "max": max(values),
    }


def bootstrap_mean_ratio(left, right, samples=100_000, seed=26382):
    rng = random.Random(seed)
    ratios = []
    for _ in range(samples):
        left_mean = statistics.fmean(left[rng.randrange(len(left))] for _ in left)
        right_mean = statistics.fmean(right[rng.randrange(len(right))] for _ in right)
        ratios.append(right_mean / left_mean)
    ratios.sort()
    observed = statistics.fmean(right) / statistics.fmean(left)
    return {
        "right_over_left": observed,
        "percent": (observed - 1.0) * 100.0,
        "ci95": [ratios[math.floor(samples * 0.025)], ratios[math.ceil(samples * 0.975) - 1]],
        "bootstrap_samples": samples,
    }


def correlation(left, right):
    left_mean = statistics.fmean(left)
    right_mean = statistics.fmean(right)
    numerator = sum((x - left_mean) * (y - right_mean) for x, y in zip(left, right))
    left_sum = sum((x - left_mean) ** 2 for x in left)
    right_sum = sum((y - right_mean) ** 2 for y in right)
    if not left_sum or not right_sum:
        return None
    return numerator / math.sqrt(left_sum * right_sum)


def main(qa_path, io_path):
    qa_rows = load(qa_path)
    io_rows = load(io_path)
    output = {"inputs": [qa_path, io_path], "qa_b_combined": {}, "io_matrix": {}}

    combined = [row for row in qa_rows + io_rows if row["variant"] in ("qa-2029", "B")]
    grouped = defaultdict(list)
    for row in combined:
        grouped[row["variant"]].append(row["seconds"])
    output["qa_b_combined"]["summary"] = {
        variant: summarize(values) for variant, values in sorted(grouped.items())
    }
    output["qa_b_combined"]["B_over_qa-2029"] = bootstrap_mean_ratio(
        grouped["qa-2029"], grouped["B"]
    )

    io_grouped = defaultdict(list)
    for row in io_rows:
        io_grouped[row["variant"]].append(row["seconds"])
    output["io_matrix"]["summary"] = {
        variant: summarize(values) for variant, values in sorted(io_grouped.items())
    }
    output["io_matrix"]["median_ratios"] = {
        f"{right}_over_{left}": statistics.median(io_grouped[right]) / statistics.median(io_grouped[left])
        for left, right in (("qa-2029", "A"), ("A", "B"), ("B", "C"), ("A", "C"))
    }
    seconds = [row["seconds"] for row in io_rows]
    output["io_matrix"]["correlations"] = {
        name: correlation(seconds, [row[name] for row in io_rows])
        for name in ("migrations", "switches", "minflt", "read_bytes")
    }
    output["io_matrix"]["physical_io"] = {
        "read_bytes_unique": sorted({row["read_bytes"] for row in io_rows}),
        "major_faults_unique": sorted({row["majflt"] for row in io_rows}),
    }
    print(json.dumps(output, indent=2, sort_keys=True))


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit(f"usage: {sys.argv[0]} QA_PCORES.csv PCORES_IO.csv")
    main(sys.argv[1], sys.argv[2])
