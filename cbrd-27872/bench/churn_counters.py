#!/usr/bin/env python3
"""CBRD-27872 / CBRD-27925 stage 2: server counters during the churn workload, per build.

Runs growth_cost.Runner.churn unchanged on the databases growth_cost.py created. The Runner subclass
takes a `cubrid statdump` snapshot at every point where churn() records a page count, so the counter
deltas are split into the four phases of a cycle: update, update_drain (vacuum of the old chunks),
delete (DML plus drain) and reinsert. The drain loop pushes the log with filler INSERTs whose number
depends on vacuum timing, so a calibration of the cost of one filler is measured once per run and
subtracted (the *_net metrics).

The server counts only while some client watches statistics, so a `cubrid statdump -i 1` process runs for
the duration of each churn (a csql session with @collect_exec_stats would hold a transaction snapshot and
block vacuum). Without it every counter reads 0; the script stops when the calibration reads 0.

Output: OUT/results.csv (a separate directory from the databases, columns as in growth_cost.py).
Item `churn_counters`, iter = cycle, metric = <phase>_<counter>[_net|_fillers], and cycle_<counter>_net.
"""
import argparse
import pathlib
import re
import signal
import subprocess
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import growth_cost as g  # noqa: E402

COUNTERS = ("Num_log_append_records", "Num_log_page_iowrites", "Num_file_page_allocs", "Num_file_page_deallocs")
STAT_LINE = re.compile(r"^(Num_\w+)\s*=\s*(\d+)", re.M)
PHASE_OF = {
    "pages_peak_update": "update",
    "pages_after_update_drain": "update_drain",
    "pages_after_delete_drain": "delete",
    "pages_after_reinsert": "reinsert",
}
CALIBRATION_FILLERS = 5


def statdump(b):
    out = b.run(["cubrid", "statdump", b.db], "statdump")
    found = {k: int(v) for k, v in STAT_LINE.findall(out)}
    missing = [c for c in COUNTERS if c not in found]
    if missing:
        raise RuntimeError(f"{b.label}: statdump has no {missing}")
    return found


def fillers_so_far(b):
    return len(list(b.logs.glob("*-filler")))


class CounterRunner(g.Runner):
    def __init__(self, out, cycles):
        super().__init__(out)
        self.cycles = cycles
        self.watch = {}
        self.snap = {}
        self.nfill = {}
        self.per_filler = {}
        self.cycle_net = {}

    def emit(self, b, rnd, item, it, metric, value):
        super().emit(b, rnd, item, it, metric, value)
        if item != "churn" or not metric.startswith("pages_"):
            return
        if metric == "pages_initial":
            fh = open(b._log("statdump-watcher"), "wb")
            proc = subprocess.Popen(["cubrid", "statdump", "-i", "1", b.db], stdin=subprocess.DEVNULL, stdout=fh,
                                    stderr=subprocess.STDOUT, env=b.env, cwd=b.root)
            self.watch[b.label] = (proc, fh)
            time.sleep(2)
            before = statdump(b)
            for _ in range(CALIBRATION_FILLERS):
                b.run(["csql", "-C", "-u", "dba", "-c",
                       "INSERT INTO f SELECT id, REPEAT('f', 1500) FROM nums WHERE id <= 200", b.db], "filler")
                time.sleep(0.1)
            time.sleep(1)
            after = statdump(b)
            if after["Num_log_append_records"] == before["Num_log_append_records"]:
                self.stop_watcher(b)
                raise RuntimeError(f"{b.label}: statdump counters did not move during the calibration fillers")
            self.per_filler[b.label] = {c: (after[c] - before[c]) / CALIBRATION_FILLERS for c in COUNTERS}
            for c in COUNTERS:
                self.emit(b, rnd, "churn_counters", 0, f"filler_{c}", round(self.per_filler[b.label][c], 1))
            self.snap[b.label] = after
            self.nfill[b.label] = fillers_so_far(b)
            self.cycle_net[b.label] = {c: 0.0 for c in COUNTERS}
            return
        phase = PHASE_OF.get(metric)
        if phase is None:
            return
        now = statdump(b)
        nf = fillers_so_far(b)
        fillers = nf - self.nfill[b.label]
        self.emit(b, rnd, "churn_counters", it, f"{phase}_fillers", fillers)
        for c in COUNTERS:
            raw = now[c] - self.snap[b.label][c]
            net = raw - fillers * self.per_filler[b.label][c]
            self.emit(b, rnd, "churn_counters", it, f"{phase}_{c}", raw)
            self.emit(b, rnd, "churn_counters", it, f"{phase}_{c}_net", round(net, 1))
            self.cycle_net[b.label][c] += net
        self.snap[b.label], self.nfill[b.label] = now, nf
        if phase == "reinsert":
            for c in COUNTERS:
                self.emit(b, rnd, "churn_counters", it, f"cycle_{c}_net", round(self.cycle_net[b.label][c], 1))
                self.cycle_net[b.label][c] = 0.0
            if it == self.cycles:
                self.stop_watcher(b)

    def stop_watcher(self, b):
        proc, fh = self.watch.pop(b.label)
        proc.send_signal(signal.SIGINT)
        try:
            proc.wait(timeout=30)
        except subprocess.TimeoutExpired:
            proc.kill()
        fh.close()
        pathlib.Path(fh.name).unlink()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dbs", required=True, help="the --out directory growth_cost.py created (holds <label>/)")
    ap.add_argument("--out", required=True, help="directory for this script's results.csv")
    ap.add_argument("--build", action="append", required=True,
                    help="label=INSTALL=SHA, in the order given to growth_cost.py (the ports follow the order)")
    ap.add_argument("--reps", type=int, default=4)
    ap.add_argument("--cycles", type=int, default=6)
    a = ap.parse_args()
    pathlib.Path(a.out).mkdir(parents=True, exist_ok=True)
    builds = []
    for i, spec in enumerate(a.build):
        label, install, sha = spec.split("=", 2)
        builds.append(g.Build(label, install, sha, pathlib.Path(a.dbs) / label, 35100 + 10 * i))
    r = CounterRunner(a.out, a.cycles)
    for rep in range(a.reps):
        for b in (builds if rep % 2 == 0 else builds[::-1]):
            print(f"== counters rep {rep} {b.label} {time.strftime('%T')}", flush=True)
            r.churn(b, rep, a.cycles)
    return 0


if __name__ == "__main__":
    sys.exit(main())
