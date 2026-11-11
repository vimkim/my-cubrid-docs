#!/usr/bin/env python3
"""CBRD-27872 / CBRD-27925 stage 2: flat CPU profile of cub_server during the churn workload.

Runs growth_cost.Runner.churn unchanged on the databases growth_cost.py created. A Runner subclass starts
`perf record -p <cub_server>` when churn() records pages_initial and stops it after the last cycle's
re-INSERT, so the profile covers the UPDATE, DELETE, vacuum drain and re-INSERT of all cycles and nothing
else. Cycle 1 allocates new pages in every build; from cycle 2 on stage 2 reuses emptied pages, so use at
least 3 cycles. The profile is flat (no call graph): it answers which symbols carry the CPU, not who called.

Output: OUT/<label>-rep<N>.perf.data and OUT/<label>-rep<N>.report.txt (perf report --no-children, by symbol).
"""
import argparse
import os
import pathlib
import signal
import subprocess
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import growth_cost as g  # noqa: E402


def server_pid(b):
    out = subprocess.run(["pgrep", "-u", str(os.getuid()), "-f", f"cub_server {b.db}"],
                         capture_output=True, text=True, env=b.env).stdout.split()
    if len(out) != 1:
        raise RuntimeError(f"{b.label}: expected one cub_server for {b.db}, found {out}")
    return out[0]


class PerfRunner(g.Runner):
    def __init__(self, out, cycles):
        super().__init__(out)
        self.cycles, self.out_dir, self.perf = cycles, pathlib.Path(out), {}

    def emit(self, b, rnd, item, it, metric, value):
        super().emit(b, rnd, item, it, metric, value)
        if item != "churn":
            return
        data = self.out_dir / f"{b.label}-rep{rnd}.perf.data"
        if metric == "pages_initial":
            self.perf[b.label] = subprocess.Popen(
                ["perf", "record", "-F", "4000", "-p", server_pid(b), "-o", str(data)],
                stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            time.sleep(1)
        elif metric == "pages_after_reinsert" and it == self.cycles:
            proc = self.perf.pop(b.label)
            proc.send_signal(signal.SIGINT)
            proc.wait(timeout=60)
            rep = subprocess.run(["perf", "report", "-i", str(data), "--stdio", "--no-children", "--sort", "dso,symbol",
                                  "--percent-limit", "0.3"], capture_output=True, text=True).stdout
            (self.out_dir / f"{b.label}-rep{rnd}.report.txt").write_text(rep)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dbs", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--build", action="append", required=True)
    ap.add_argument("--reps", type=int, default=2)
    ap.add_argument("--cycles", type=int, default=4)
    ap.add_argument("--rows", type=int, default=g.CFG["c_rows"], help="rows of the churn table c")
    a = ap.parse_args()
    g.CFG["c_rows"] = a.rows
    pathlib.Path(a.out).mkdir(parents=True, exist_ok=True)
    builds = []
    for i, spec in enumerate(a.build):
        label, install, sha = spec.split("=", 2)
        builds.append(g.Build(label, install, sha, pathlib.Path(a.dbs) / label, 35100 + 10 * i))
    r = PerfRunner(a.out, a.cycles)
    for rep in range(a.reps):
        for b in (builds if rep % 2 == 0 else builds[::-1]):
            print(f"== perf rep {rep} {b.label} {time.strftime('%T')}", flush=True)
            r.churn(b, rep, a.cycles)
    return 0


if __name__ == "__main__":
    sys.exit(main())
