#!/usr/bin/env python3
"""Statement times of every churn in DBS/<label>/logs, in run order, with the row count of each churn given by
--rows (repeated in the order churn_scale.py ran them). Prints median and range per rows/label/statement/cycle.
usage: scale_times.py DBS --rows 2000 6000 [--labels a b c]
"""
import argparse
import pathlib
import re
import statistics
from collections import defaultdict

STMT = re.compile(r"row(?:s)? affected\. \((\d+\.\d+) sec\)")
NAME = re.compile(r"^\d+-churn-(init|update|delete|reinsert)(?:-(\d+))?\.out$")

ap = argparse.ArgumentParser()
ap.add_argument("dbs")
ap.add_argument("--rows", type=int, nargs="+", required=True)
ap.add_argument("--labels", nargs="+")
a = ap.parse_args()
times = defaultdict(list)
for d in sorted(pathlib.Path(a.dbs).iterdir()):
    if not (d / "logs").is_dir() or (a.labels and d.name not in a.labels):
        continue
    n = -1
    for p in sorted((d / "logs").iterdir()):
        m = NAME.match(p.name)
        if not m:
            continue
        if m.group(1) == "init":
            n += 1
            continue
        v = STMT.findall(p.read_text(errors="replace"))
        if len(v) == 1:
            rows = a.rows[n % len(a.rows)]
            times[(rows, d.name, m.group(1), "c1" if m.group(2) == "1" else "c2+")].append(float(v[0]) * 1000)
print("| rows | build | statement | cycle | n | median ms | range ms |")
print("| --- | --- | --- | --- | --- | --- | --- |")
for k in sorted(times):
    v = times[k]
    print(f"| {k[0]} | {k[1]} | {k[2]} | {k[3]} | {len(v)} | {statistics.median(v):.1f} | {min(v):.1f}-{max(v):.1f} |")
