#!/usr/bin/env python3
"""CBRD-27872 / CBRD-27925 stage 2: is the churn drain limited by time or by log volume?

After each UPDATE of the churn workload, one large filler INSERT (6,000 rows of 1,500 bytes, about 9 MB of
data) pushes the log, then Oos_num_recs of c is polled every 50 ms until vacuum has removed the old chunks.
The harness drain pushes the log in steps of one 200-row filler (about 5 log pages); a build that finishes at
once after the large filler needed log volume, not time, in the harness drain.

usage: drain_probe.py --dbs DIR --build label=INSTALL=SHA ... [--reps 2] [--cycles 4]
"""
import argparse
import pathlib
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import growth_cost as g  # noqa: E402

BIG = "INSERT INTO f SELECT id, REPEAT('f', 1500) FROM nums WHERE id <= 6000"


def probe(b, rows, nbytes, cycles):
    b.csql("DROP TABLE IF EXISTS c;\nCREATE TABLE c (id INT PRIMARY KEY, v BIT VARYING);\n"
           f"INSERT INTO c SELECT id, {g.value_expr('id', nbytes)} FROM nums WHERE id <= {rows};\n", "probe-init")
    res = []
    for cy in range(1, cycles + 1):
        b.csql(f"UPDATE c SET v = {g.value_expr(f'id + {100000 * cy}', nbytes)};\n", f"probe-update-{cy}")
        t0 = time.time()
        b.run(["csql", "-C", "-u", "dba", "-c", BIG, b.db], "probe-bigfiller")
        polls = 0
        while b.oos("c").get("Oos_num_recs") != rows:
            polls += 1
            time.sleep(0.05)
            if time.time() - t0 > 60:
                raise RuntimeError(f"{b.label}: vacuum did not drain after the large filler")
        res.append((cy, polls, round(time.time() - t0, 2)))
        b.csql("DELETE FROM c WHERE MOD(id, 10) < 3;\n", f"probe-delete-{cy}")
        for _ in range(60):
            if b.oos("c").get("Oos_num_recs") == rows - rows * 3 // 10:
                break
            b.run(["csql", "-C", "-u", "dba", "-c", BIG, b.db], "probe-bigfiller")
            time.sleep(0.05)
        b.csql(f"INSERT INTO c SELECT id, {g.value_expr(f'id + {100000 * cy} + 7', nbytes)} FROM nums "
               f"WHERE id <= {rows} AND MOD(id, 10) < 3;\n", f"probe-reinsert-{cy}")
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dbs", required=True)
    ap.add_argument("--build", action="append", required=True)
    ap.add_argument("--reps", type=int, default=2)
    ap.add_argument("--cycles", type=int, default=4)
    a = ap.parse_args()
    builds = []
    for i, spec in enumerate(a.build):
        label, install, sha = spec.split("=", 2)
        builds.append(g.Build(label, install, sha, pathlib.Path(a.dbs) / label, 35100 + 10 * i))
    print("label rep [(cycle, polls after the large filler, seconds from UPDATE end to drained)]")
    for rep in range(a.reps):
        for b in (builds if rep % 2 == 0 else builds[::-1]):
            b.start()
            try:
                print(b.label, rep, probe(b, g.CFG["c_rows"], g.CFG["c_bytes"], a.cycles), flush=True)
            finally:
                b.stop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
