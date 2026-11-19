#!/usr/bin/env python3
"""Commit latency of INSERT-then-COMMIT clients, with the server's fsyncs per commit.

    python3 latency.py DBNAME COMMIT_LAT_BINARY --label L [--clients 1] [--n 3000] [--warmup 50]

Prints one JSON line: commit-call latency percentiles in microseconds over all clients (warm-up transactions of
each client dropped), mean transaction time, throughput, and the cub_server statdump deltas per commit.
"""

import argparse
import json
import os
import subprocess
import tempfile
import time
from pathlib import Path

KEYS = ("Num_file_iosynches", "Num_log_wals", "Num_tran_commits", "Num_log_page_iowrites")


def csql(db, sql):
    subprocess.run(["csql", "-C", "-u", "dba", "-c", sql, db], stdin=subprocess.DEVNULL, capture_output=True,
                   check=True, timeout=120)


def statdump(db):
    r = subprocess.run(["cubrid", "statdump", "-c", db], stdin=subprocess.DEVNULL, capture_output=True, text=True,
                       check=True, timeout=120)
    stats = {}
    for line in r.stdout.splitlines():
        name, _, value = line.partition("=")
        if name.strip() in KEYS and value.strip().isdigit():
            stats[name.strip()] = int(value)
    return stats


def start_watcher(db):
    """Global stats accumulate only while some client watches them."""
    w = subprocess.Popen(["cubrid", "statdump", "-i", "3600", "-c", db], stdin=subprocess.DEVNULL,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(0.5)
    return w


def pct(sorted_xs, q):
    return sorted_xs[min(len(sorted_xs) - 1, int(q * len(sorted_xs)))]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("db")
    ap.add_argument("binary")
    ap.add_argument("--label", required=True)
    ap.add_argument("--clients", type=int, default=1)
    ap.add_argument("--n", type=int, default=3000)
    ap.add_argument("--warmup", type=int, default=50)
    args = ap.parse_args()
    csql(args.db, "drop table if exists lat; create table lat (c int, i int);")
    outdir = Path(tempfile.mkdtemp(prefix="commit_lat_"))
    watcher = start_watcher(args.db)
    before = statdump(args.db)
    load_before = os.getloadavg()[0]
    start = time.monotonic()
    procs = []
    for c in range(args.clients):
        out = (outdir / f"c{c}.out").open("w")
        procs.append(subprocess.Popen([args.binary, args.db, str(args.n), str(c)], stdin=subprocess.DEVNULL,
                                      stdout=out, stderr=subprocess.STDOUT))
    for p in procs:
        if p.wait() != 0:
            raise RuntimeError((outdir / f"c{procs.index(p)}.out").read_text()[-2000:])
    wall = time.monotonic() - start
    after = statdump(args.db)
    watcher.kill()
    watcher.wait()
    commit, txn = [], []
    for c in range(args.clients):
        rows = [line.split() for line in (outdir / f"c{c}.out").read_text().splitlines()]
        for row in rows[args.warmup:]:
            commit.append(int(row[0]))
            txn.append(int(row[1]))
    commit.sort()
    total_commits = args.clients * args.n
    delta = {k: after.get(k, 0) - before.get(k, 0) for k in KEYS}
    print(json.dumps({
        "label": args.label, "clients": args.clients, "n": args.n, "samples": len(commit),
        "commit_us": {"mean": round(sum(commit) / len(commit), 1), "p50": pct(commit, 0.5),
                      "p90": pct(commit, 0.9), "p99": pct(commit, 0.99), "max": commit[-1]},
        "txn_mean_us": round(sum(txn) / len(txn), 1),
        "commits_per_s": round(total_commits / wall, 1),
        "fsyncs_per_commit": round(delta["Num_file_iosynches"] / max(1, delta["Num_tran_commits"]), 3),
        "statdump_delta": delta,
        "loadavg_1m": [round(load_before, 1), round(os.getloadavg()[0], 1)],
    }), flush=True)


if __name__ == "__main__":
    main()
