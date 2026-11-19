#!/usr/bin/env python3
"""CBRD-28062 sweep: INSERT/UPDATE of 4~16KB values and cold (restart-only) reads with I/O trace.

Companion of the CBRD-27788 harness (bench.py, sweep.py, ordinary.py, io_bench.py). The caller owns
database creation, server lifetime and CPU pinning. Needs PYTHONPATH=<harness dir> for bench and sweep.
Metric: server instructions:u from `perf stat -p <server pid>`, like the 27788 harness.
"""
import argparse, json, os, re, shutil, sys, time
from pathlib import Path

import bench
import sweep

ROWS = sweep.ROWS
SIZES = sweep.SIZES
COLS = "(id INT PRIMARY KEY, a INT, s VARCHAR(40), big VARCHAR(20000))"
PREFIX = {"insert": "ins", "update_small": "ups", "update_big": "upb"}
SUM_A = sum(n % 100 for n in range(1, ROWS + 1))
TRACE = re.compile(r"^\s*SELECT \(time: (\d+), fetch: (\d+), fetch_time: (\d+), ioread: (\d+)\)", re.M)


def source_sql(table, chunks):
    """One-row source table holding an incompressible value of the fixture size (LZ4 shrinks repeated text to ~nothing)."""
    big = ",".join(f"SHA2('src_{k}',512)" for k in range(chunks))
    return (f"DROP TABLE IF EXISTS src_{table};\nCREATE TABLE src_{table} (id INT PRIMARY KEY, big VARCHAR(20000));\n"
            f"INSERT INTO src_{table} SELECT 1, CONCAT({big}) FROM db_root;\nCOMMIT;\n")


def value(table):
    return f"(SELECT big FROM src_{table})"  # uncorrelated: evaluated once per statement


def clone(table, source):
    return (f"CREATE TABLE {table} {COLS};\nINSERT INTO {table} SELECT id, a, s, big FROM {source} ORDER BY id;\n"
            f"COMMIT;\nUPDATE STATISTICS ON {table};\n")


def check_sql(table, source_table):
    return (f"SELECT COUNT(*), SUM(a), SUM(LENGTH(big)), SUM(CASE WHEN big={value(source_table)} THEN 1 ELSE 0 END) "
            f"FROM {table};\n")


def wait_for_idle(pid, limit=180):
    def ticks():
        f = Path(f"/proc/{pid}/stat").read_text().rsplit(")", 1)[1].split()
        return int(f[11]) + int(f[12])
    seen, streak, end = [], 0, time.monotonic() + limit
    while time.monotonic() < end:
        before = ticks(); time.sleep(0.25)
        used = (ticks() - before) / os.sysconf("SC_CLK_TCK")
        seen.append(used); streak = streak + 1 if used <= 0.0101 else 0
        if streak >= 8:
            return len(seen) * 0.25
    raise ValueError(f"server did not become idle: {seen[-8:]}")


def proc_io(pid):
    return {k: int(v) for k, v in (l.split(":", 1) for l in Path(f"/proc/{pid}/io").read_text().splitlines())}


class Run:
    def __init__(self, args):
        self.args = args
        self.identity, self.client = bench.validate_server(args.server_pid, args.database)
        self.out = Path(args.output).resolve()
        self.out.mkdir(parents=True, exist_ok=False)
        self.manifest = {"schema": 1, "kind": args.action, "label": args.label, "source": args.source,
                         "database": args.database, "server": self.identity,
                         "server_sha256": bench.digest(self.identity["executable"]),
                         "client_sha256": bench.digest(self.client), "harness_sha256": bench.digest(__file__),
                         "samples": [], "complete": False}
        self.save()

    def save(self):
        (self.out / "summary.json").write_text(json.dumps(self.manifest, indent=2) + "\n")

    def sql(self, name, text):
        path = self.out / (name + ".sql"); path.write_text(text)
        bench.run(bench.csql_command(self.args.database, path, str(self.client)), self.out / name, self.args.timeout)
        return bench.results(self.out / (name + ".stdout"))

    def storage(self, name, table, length):
        """Capture SHOW HEAP CAPACITY/OOS and assert that every row stores the full value (nothing compressed away)."""
        text = f"SHOW HEAP CAPACITY OF {table};\n" + (f"SHOW HEAP OOS OF {table};\n" if self.args.show_oos else "")
        self.sql(name, text)
        rows = [l.split("\t") for l in (self.out / (name + ".stdout")).read_text().splitlines() if l.startswith("dba.")]
        placement = {"num_recs": int(rows[0][5]), "heap_pages": int(rows[0][8]), "avg_rec_len": int(rows[0][9]),
                     "oos_recs": int(rows[1][10]) if len(rows) > 1 else 0,
                     "oos_pages": int(rows[1][8]) if len(rows) > 1 else 0,
                     "oos_sumlen": int(rows[1][11]) if len(rows) > 1 else 0}
        stored = placement["avg_rec_len"] + placement["oos_sumlen"] / placement["num_recs"]
        if placement["num_recs"] != ROWS or stored < 0.98 * length:
            raise ValueError(f"value not stored in full ({stored:.0f} B per row < {length} B): {name}")
        return placement

    def counted(self, name, text, wide=False):
        """Run `text` through csql under perf stat on the server; return elapsed, counters and io delta."""
        path = self.out / (name + ".sql"); path.write_text(text)
        perf = self.out / (name + ".perf")
        client = bench.csql_command(self.args.database, path, str(self.client))
        if wide:  # keep the trace column whole
            at = client.index("--no-pager") + 1
            client[at:at] = ["--string-width", "1000000"]
        cmd = ["perf", "stat", "-x", ";", "-e", "instructions:u,cycles:u,task-clock", "-p", str(self.args.server_pid),
               "-o", str(perf), "--"] + client
        idle = wait_for_idle(self.args.server_pid)
        before = proc_io(self.args.server_pid)
        elapsed = bench.run(cmd, self.out / name, self.args.timeout)
        after = proc_io(self.args.server_pid)
        if bench.process_identity(self.args.server_pid) != self.identity:
            raise ValueError("server process changed during measurement")
        return {"elapsed_seconds": elapsed, "idle_wait_seconds": idle, "counters": bench.counters(perf),
                "server_io_delta": {k: after[k] - before[k] for k in before}, "load": os.getloadavg()}


def dml(args):
    r = Run(args)
    r.manifest["runs"] = args.runs
    r.manifest["cases"] = args.cases
    for table, chunks in SIZES.items():
        length = chunks * 128
        r.sql(f"source-{table}", source_sql(table, chunks))
        if r.sql(f"source-{table}-check", f"SELECT COUNT(*), SUM(LENGTH(big)) FROM src_{table};\n") != [(1, length)]:
            raise ValueError(f"bad source value {table}")
        for case in args.cases.split(","):
            for i in range(args.runs):
                name, t = f"{case}-{table}-{i}", f"{PREFIX[case]}_{table}_{i}"
                if case == "insert":
                    r.sql(name + "-setup", f"CREATE TABLE {t} {COLS};\n")
                    work = f"INSERT INTO {t} SELECT n, MOD(n,100), 's'||n, {value(table)} FROM seq;\nCOMMIT;\n"
                    want = (ROWS, SUM_A, ROWS * length, ROWS)
                else:
                    r.sql(name + "-setup", clone(t, table))
                    if r.sql(name + "-before", check_sql(t, table)) != [(ROWS, SUM_A, ROWS * length, 0)]:
                        raise ValueError(f"bad clone {name}")
                    if case == "update_small":
                        work, want = f"UPDATE {t} SET a=a+1;\nCOMMIT;\n", (ROWS, SUM_A + ROWS, ROWS * length, 0)
                    else:
                        work, want = f"UPDATE {t} SET big={value(table)};\nCOMMIT;\n", (ROWS, SUM_A, ROWS * length, ROWS)
                sample = r.counted(name, work)
                got = r.sql(name + "-after", check_sql(t, table))
                if got != [want]:
                    raise ValueError(f"unexpected contents {got} != {want}: {name}")
                placement = r.storage(name + "-storage", t, length)
                r.sql(name + "-drop", f"DROP TABLE {t};\nCOMMIT;\n")
                r.manifest["samples"].append({"table": table, "case": case, "run": i, "warmup": i == 0, "placement": placement, **sample})
                r.save()
        r.sql(f"source-{table}-drop", f"DROP TABLE src_{table};\nCOMMIT;\n")
    r.manifest["complete"] = True
    r.save()
    print(r.out / "summary.json")


def cold(args):
    """One sample right after a server start: the data buffer is cold, the OS file cache is warm."""
    r = Run(args)
    table, case = args.table, args.case
    text = "SET TRACE ON;\n" + sweep.CASES[case].format(t=table) + "\nSHOW TRACE;\nSET TRACE OFF;\n"
    sample = r.counted(f"{case}-{table}", text, wide=True)
    out = (r.out / f"{case}-{table}.stdout").read_text().replace(r"\n", "\n")
    got = bench.results(r.out / f"{case}-{table}.stdout")
    if got != [sweep.expected(table)[case]]:
        raise ValueError(f"unexpected result {got}")
    trace = TRACE.findall(out)
    if len(trace) != 1:
        raise ValueError("missing trace")
    sample["trace"] = dict(zip(("time_ms", "fetch", "fetch_time_ms", "ioread"), map(int, trace[0])))
    sample["parallel_scan"] = "parallel workers:" in out.lower()  # same default as the sweep queries (no hint)
    r.manifest["samples"].append({"table": table, "case": case, **sample})
    r.manifest["complete"] = True
    r.save()
    print(json.dumps(r.manifest["samples"][0]["trace"]))


def main():
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="action", required=True)
    for name in ("dml", "cold"):
        m = sub.add_parser(name)
        for flag in ("--database", "--label", "--source", "--output"):
            m.add_argument(flag, required=True)
        m.add_argument("--server-pid", type=int, required=True)
        m.add_argument("--timeout", type=int, default=1800)
        m.add_argument("--show-oos", action="store_true")
        if name == "dml":
            m.add_argument("--runs", type=int, default=5)
            m.add_argument("--cases", default="insert,update_small,update_big")
        else:
            m.add_argument("--table", choices=SIZES, required=True)
            m.add_argument("--case", choices=("narrow", "length"), required=True)
    args = p.parse_args()
    (dml if args.action == "dml" else cold)(args)


if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        sys.exit(2)
