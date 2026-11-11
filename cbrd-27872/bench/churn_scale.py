#!/usr/bin/env python3
"""CBRD-27872 / CBRD-27925 stage 2: does the cost of a growth statement depend on the emptied-page set size?

Runs growth_cost.Runner.churn with several row counts for the churn table c, on the databases growth_cost.py
created, and prints csql's own statement time of the UPDATE, DELETE and re-INSERT of each cycle (cycle 1 and
cycles 2+ separately). From cycle 2 on, stage 2 keeps every page vacuum emptied in the file's emptied-page
set, so the set holds about rows/2 pages. A cost that grows with the row count in cycles 2+ and is absent in
cycle 1 and in DELETE points at work per growth that is linear in the set size.

usage: churn_scale.py --dbs DIR --build label=INSTALL=SHA ... --rows 2000 6000 --reps 2 --cycles 3
"""
import argparse
import pathlib
import re
import statistics
import sys
import time
from collections import defaultdict

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import growth_cost as g  # noqa: E402

STMT = re.compile(r"row(?:s)? affected\. \((\d+\.\d+) sec\)")
NAME = re.compile(r"\d+-churn-(update|delete|reinsert)-(\d+)\.out$")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dbs", required=True)
    ap.add_argument("--build", action="append", required=True)
    ap.add_argument("--rows", type=int, nargs="+", default=[2000, 6000])
    ap.add_argument("--reps", type=int, default=2)
    ap.add_argument("--cycles", type=int, default=3)
    a = ap.parse_args()
    builds = []
    for i, spec in enumerate(a.build):
        label, install, sha = spec.split("=", 2)
        builds.append(g.Build(label, install, sha, pathlib.Path(a.dbs) / label, 35100 + 10 * i))
    scratch = pathlib.Path(a.dbs) / "scale-results"
    scratch.mkdir(exist_ok=True)
    r = g.Runner(scratch)
    times = defaultdict(list)
    for rep in range(a.reps):
        for rows in a.rows:
            g.CFG["c_rows"] = rows
            for b in (builds if rep % 2 == 0 else builds[::-1]):
                before = set(p.name for p in b.logs.iterdir())
                print(f"== scale rep {rep} rows {rows} {b.label} {time.strftime('%T')}", flush=True)
                r.churn(b, rep, a.cycles)
                for p in b.logs.iterdir():
                    m = NAME.search(p.name)
                    if p.name in before or not m:
                        continue
                    v = STMT.findall(p.read_text(errors="replace"))
                    if len(v) == 1:
                        times[(rows, b.label, m.group(1), "c1" if int(m.group(2)) == 1 else "c2+")].append(float(v[0]) * 1000)
    print("| rows | build | statement | cycle | n | median ms | range ms |")
    print("| --- | --- | --- | --- | --- | --- | --- |")
    for k in sorted(times):
        v = times[k]
        print(f"| {k[0]} | {k[1]} | {k[2]} | {k[3]} | {len(v)} | {statistics.median(v):.1f} | {min(v):.1f}-{max(v):.1f} |")
    return 0


if __name__ == "__main__":
    sys.exit(main())
