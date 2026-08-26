#!/usr/bin/env python3
"""Summarize CBRD-26382 perf-stat CSV files without mutating the raw evidence."""

import csv
import json
import math
import os
import pathlib
import re
import statistics
import sys
from collections import defaultdict


QUERY_TIME_RE = re.compile(r"1 row selected\. \(([0-9.]+) sec\)")


def parse_number(value):
    value = value.strip().replace(" ", "")
    if not value or value.startswith("<"):
        return None
    try:
        return float(value)
    except ValueError:
        return None


def parse_perf_csv(path):
    events = {}
    unsupported = []
    with path.open(newline="", encoding="utf-8", errors="replace") as stream:
        for row in csv.reader(stream):
            if len(row) < 3 or row[0].startswith("#"):
                continue
            value = parse_number(row[0])
            event = row[2].strip()
            if not event:
                continue
            if value is None:
                unsupported.append({"event": event, "raw": row})
                continue
            runtime_ns = parse_number(row[3]) if len(row) > 3 else None
            running_percent = parse_number(row[4].rstrip("%")) if len(row) > 4 else None
            events[event] = {
                "value": value,
                "unit": row[1].strip(),
                "runtime_ns": runtime_ns,
                "running_percent": running_percent,
            }
    return events, unsupported


def query_seconds(path):
    match = QUERY_TIME_RE.search(path.read_text(encoding="utf-8", errors="replace"))
    if not match:
        raise RuntimeError(f"query time not found: {path}")
    return float(match.group(1))


def safe_ratio(numerator, denominator):
    if numerator is None or denominator in (None, 0):
        return None
    return numerator / denominator


def value(events, name):
    item = events.get(name)
    if item is not None:
        return item["value"]
    for event, candidate in events.items():
        if not event.startswith("cpu_core/"):
            continue
        inner = event.removeprefix("cpu_core/")
        if inner.endswith("/u"):
            inner = inner[:-2]
        if inner == name:
            return candidate["value"]
    return None


def derived_metrics(group, events, seconds):
    metrics = {"query_seconds": seconds}
    if group == "core":
        metrics.update(
            ipc=safe_ratio(value(events, "instructions"), value(events, "cycles")),
            ghz=safe_ratio(value(events, "cycles"), seconds * 1e9),
            instructions_per_second=safe_ratio(value(events, "instructions"), seconds),
        )
    elif group == "branch":
        metrics["miss_percent"] = 100 * safe_ratio(
            value(events, "branch-misses"), value(events, "branch-instructions")
        )
    elif group == "cache":
        metrics["miss_percent"] = 100 * safe_ratio(
            value(events, "cache-misses"), value(events, "cache-references")
        )
    elif group == "l1d":
        metrics["miss_percent"] = 100 * safe_ratio(
            value(events, "L1-dcache-load-misses"), value(events, "L1-dcache-loads")
        )
    elif group == "llc":
        metrics["miss_percent"] = 100 * safe_ratio(
            value(events, "LLC-load-misses"), value(events, "LLC-loads")
        )
    elif group == "uopcache":
        dsb = value(events, "idq.dsb_uops")
        mite = value(events, "idq.mite_uops")
        metrics["mite_percent_of_dsb_plus_mite"] = 100 * safe_ratio(mite, None if dsb is None or mite is None else dsb + mite)
        for event, item in events.items():
            metrics[f"{event}_per_second"] = item["value"] / seconds
    elif group in ("itlb", "l1i", "frontend", "frontendret"):
        for event, item in events.items():
            metrics[f"{event}_per_second"] = item["value"] / seconds
    elif group == "topdown":
        slots = value(events, "slots")
        for name in ("topdown-retiring", "topdown-bad-spec", "topdown-fe-bound", "topdown-be-bound"):
            metrics[f"{name}_percent"] = 100 * safe_ratio(value(events, name), slots)
    elif group == "topdown2":
        slots = value(events, "slots")
        backend = value(events, "topdown-be-bound")
        memory = value(events, "topdown-mem-bound")
        metrics["topdown-mem-bound_percent"] = 100 * safe_ratio(memory, slots)
        metrics["topdown-core-bound_percent"] = 100 * safe_ratio(
            None if backend is None or memory is None else backend - memory, slots
        )
        for name in ("topdown-fetch-lat", "topdown-br-mispredict", "topdown-heavy-ops"):
            metrics[f"{name}_percent"] = 100 * safe_ratio(value(events, name), slots)
    return metrics


def summarize(values):
    clean = [value for value in values if value is not None and math.isfinite(value)]
    if not clean:
        return None
    return {
        "n": len(clean),
        "mean": statistics.fmean(clean),
        "median": statistics.median(clean),
        "min": min(clean),
        "max": max(clean),
    }


def main(root_arg):
    root = pathlib.Path(root_arg)
    runs = []
    unsupported = []
    for path in sorted(root.glob("*.perf.csv")):
        match = re.fullmatch(r"(A|B|C|qa-2029)-([a-z0-9]+)-([1-9][0-9]*)\.perf\.csv", path.name)
        if not match:
            continue
        variant, group, repetition = match.groups()
        events, missing = parse_perf_csv(path)
        seconds = query_seconds(path.with_name(path.name.replace(".perf.csv", ".query.log")))
        run = {
            "variant": variant,
            "group": group,
            "repetition": int(repetition),
            "query_seconds": seconds,
            "events": events,
            "derived": derived_metrics(group, events, seconds),
        }
        runs.append(run)
        for item in missing:
            unsupported.append({"file": path.name, **item})

    expected = int(os.environ.get("PMU_EXPECTED_RUNS", 4 * 10 * 2))
    if len(runs) != expected:
        raise SystemExit(f"incomplete PMU matrix: found {len(runs)}, expected {expected}")

    grouped = defaultdict(lambda: defaultdict(list))
    running_percentages = []
    for run in runs:
        key = f"{run['variant']}/{run['group']}"
        for metric, metric_value in run["derived"].items():
            grouped[key][metric].append(metric_value)
        for item in run["events"].values():
            if item["running_percent"] is not None:
                running_percentages.append(item["running_percent"])

    output = {
        "input_root": str(root),
        "run_count": len(runs),
        "unsupported_unique": sorted({item["event"] for item in unsupported}),
        "running_percent": summarize(running_percentages),
        "summary": {
            key: {metric: summarize(values) for metric, values in sorted(metrics.items())}
            for key, metrics in sorted(grouped.items())
        },
        "runs": runs,
    }
    print(json.dumps(output, indent=2, sort_keys=True))


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit(f"usage: {sys.argv[0]} PMU_ROOT")
    main(sys.argv[1])
