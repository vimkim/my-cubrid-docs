#!/usr/bin/env python3
"""CBRD-27872 / CBRD-27925 stage 2: does more log traffic at the end of a churn phase change drain time,
per-cycle peak pages and reserved sectors?

Hypothesis under test: vacuum only processes complete log blocks; stage 2 writes about 40% fewer log
records, so the last block of a cycle fills later, the old chunks are vacuumed later, and the next
cycle's UPDATE needs about 100 more pages (2,101 instead of 2,001) and one more sector.

Runs growth_cost.Runner.churn unchanged, in two modes per build and repetition:
  small  the harness drain: one 200-row filler INSERT (about 5 log pages) per poll, as in every other run
  big    the same poll, but each filler INSERTs 6,000 rows of 1,500 bytes (about 9 MB), so the log block
         that holds the end of the UPDATE or DELETE is complete after one filler
If the hypothesis holds, `big` makes stage 2 drain as fast as stage 1 and removes the extra pages and the
extra sector. If it does not, the drain time may match but the peak and the sector count stay.

Output: OUT/results.csv, item `logtraffic`, round = repetition, iter = cycle,
  metric = <mode>_<name>, name in pages_peak_update, pages_after_update_drain, pages_after_delete_drain,
  pages_after_reinsert, update_drain_s, delete_drain_s, update_drain_fillers, delete_drain_fillers,
  sectors_c (iter = number of cycles).

usage: log_traffic_churn.py --out DIR --build label=INSTALL=SHA=DBROOT ... [--reps 3] [--cycles 6]
       [--rows 2000] [--modes small big]
"""
import argparse
import pathlib
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import growth_cost as g  # noqa: E402

BIG = "INSERT INTO f SELECT id, REPEAT('f', 1500) FROM nums WHERE id <= 6000"
PAGES = ("pages_peak_update", "pages_after_update_drain", "pages_after_delete_drain", "pages_after_reinsert")


class Bench(g.Build):
    big = False

    def run(self, args, name, timeout=600, check=True):
        if name == "filler" and self.big:
            args = list(args)
            args[5] = BIG
        return super().run(args, name, timeout, check)


class LogTrafficRunner(g.Runner):
    def __init__(self, out):
        super().__init__(out)
        self.mode, self.stamp, self.nfill = "small", {}, {}

    def fillers(self, b):
        return len(list(b.logs.glob("*-filler")))

    def emit(self, b, rnd, item, it, metric, value):
        if item != "churn":
            return super().emit(b, rnd, item, it, metric, value)
        if metric.startswith("sectors_"):
            if metric == "sectors_c":
                super().emit(b, rnd, "logtraffic", it, f"{self.mode}_sectors_c", value)
            return
        if metric == "pages_initial":
            self.stamp[b.label], self.nfill[b.label] = time.time(), self.fillers(b)
            return
        if metric not in PAGES:
            return
        now, nf = time.time(), self.fillers(b)
        super().emit(b, rnd, "logtraffic", it, f"{self.mode}_{metric}", value)
        if metric == "pages_after_update_drain":
            super().emit(b, rnd, "logtraffic", it, f"{self.mode}_update_drain_s", round(now - self.stamp[b.label], 2))
            super().emit(b, rnd, "logtraffic", it, f"{self.mode}_update_drain_fillers", nf - self.nfill[b.label])
        if metric == "pages_after_delete_drain":
            super().emit(b, rnd, "logtraffic", it, f"{self.mode}_delete_drain_s", round(now - self.stamp[b.label], 2))
            super().emit(b, rnd, "logtraffic", it, f"{self.mode}_delete_drain_fillers", nf - self.nfill[b.label])
        self.stamp[b.label], self.nfill[b.label] = time.time(), self.fillers(b)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--build", action="append", required=True, help="label=INSTALL=SHA=DBROOT")
    ap.add_argument("--reps", type=int, default=3)
    ap.add_argument("--cycles", type=int, default=6)
    ap.add_argument("--rows", type=int, default=g.CFG["c_rows"], help="rows of the churn table c")
    ap.add_argument("--modes", nargs="+", default=["small", "big"], choices=["small", "big"])
    a = ap.parse_args()
    g.CFG["c_rows"] = a.rows
    pathlib.Path(a.out).mkdir(parents=True, exist_ok=True)
    builds = []
    for i, spec in enumerate(a.build):
        label, install, sha, root = spec.split("=", 3)
        builds.append(Bench(label, install, sha, pathlib.Path(root), 35100 + 10 * i))
    r = LogTrafficRunner(a.out)
    rnd = 0
    for rep in range(a.reps):
        for mode in a.modes if rep % 2 == 0 else a.modes[::-1]:
            for b in (builds if (rep + (mode == "big")) % 2 == 0 else builds[::-1]):
                b.big, r.mode = mode == "big", mode
                print(f"== logtraffic rep {rep} {mode} {b.label} {time.strftime('%T')}", flush=True)
                r.churn(b, rep, a.cycles)
    return 0


if __name__ == "__main__":
    sys.exit(main())
