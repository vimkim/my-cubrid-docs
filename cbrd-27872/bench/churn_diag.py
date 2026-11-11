#!/usr/bin/env python3
"""Churn (growth_cost.Runner.churn unchanged) with per-phase OOS occupancy from a diag build.

A diag build appends one DIAG line per SHOW HEAP OOS to $OOS_DIAG_FILE; non-diag builds ignore it.
usage: churn_diag.py --out DIR --build label=INSTALL=SHA[=ENV=VAL,...] ... [--rows 2000] [--cycles 3] [--reps 1]
"""
import argparse
import os
import pathlib
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import growth_cost as g  # noqa: E402

for k in [k for k in os.environ if k.startswith("CUBRID")]:
    del os.environ[k]


class DiagBuild(g.Build):
    def create_small(self):
        for d in (self.root, self.logs, self.root / "tmp"):
            d.mkdir(parents=True, exist_ok=True)
        (self.root / "cubrid.conf").write_text(
            "[service]\nservice=server\n[common]\n"
            f"cubrid_port_id={self.port}\ndata_buffer_size={g.CFG['buffer']}\n"
            "log_buffer_size=64M\nerror_log_level=error\n")
        (self.root / "databases.txt").touch()
        self.run(["cubrid", "createdb", "--db-volume-size=2G", "--log-volume-size=1G", "-F", str(self.root),
                  self.db, "en_US.utf8"], "createdb")
        self.start()
        self.csql("CREATE TABLE nums (id INT);\n"
                  "INSERT INTO nums SELECT ROWNUM FROM db_class a, db_class b, db_class c WHERE ROWNUM <= 60000;\n"
                  "CREATE TABLE f (id INT, s VARCHAR(2000));\n", "schema")
        self.stop()


class DiagRunner(g.Runner):
    def emit(self, b, rnd, item, it, metric, value):
        super().emit(b, rnd, item, it, metric, value)
        diag = b.root / "diag.txt"
        line = ""
        if diag.exists():
            lines = diag.read_text().splitlines()
            line = lines[-1] if lines else ""
        with open(self.out / "diag.log", "a") as fh:
            fh.write(f"{b.label} rep={rnd} cy={it} {metric}={value} load={os.getloadavg()[0]:.0f} :: {line}\n")
        print(f"{b.label} rep={rnd} cy={it} {metric}={value} :: {line[:400]}", flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--build", action="append", required=True)
    ap.add_argument("--rows", type=int, default=2000)
    ap.add_argument("--cycles", type=int, default=3)
    ap.add_argument("--reps", type=int, default=1)
    ap.add_argument("--port", type=int, default=35400)
    a = ap.parse_args()
    g.CFG["c_rows"] = a.rows
    out = pathlib.Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    builds = []
    for i, spec in enumerate(a.build):
        parts = spec.split("=", 3)
        label, install, sha = parts[:3]
        b = DiagBuild(label, install, sha, out / label, a.port + 10 * i)
        b.env["OOS_DIAG_FILE"] = str(b.root / "diag.txt")
        if len(parts) > 3:
            for kv in parts[3].split(","):
                k, v = kv.split(":", 1)
                b.env[k] = v
        if not (b.root / "databases.txt").exists():
            b.create_small()
        builds.append(b)
    r = DiagRunner(out)
    for rep in range(a.reps):
        for b in (builds if rep % 2 == 0 else builds[::-1]):
            print(f"== churn {rep} {b.label} {time.strftime('%T')} load={os.getloadavg()[0]:.0f}", flush=True)
            r.churn(b, rep, a.cycles)
    return 0


if __name__ == "__main__":
    sys.exit(main())
