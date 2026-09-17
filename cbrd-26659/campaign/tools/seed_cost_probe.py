#!/usr/bin/env python3
"""Measure what one seed of a randomized OOS churn workload costs (campaign ticket 17).

    seed_cost_probe.py --build release|debug --page-size N --seeds K [--first-seed S]
                       [--rows R] [--fixture fresh|reused] --out DIR

Ticket 17 criterion 4 asks that the seed counts -- 10 for the scheduled tier, 100 for the
extended tier (decision ticket 08) -- are "checked against measured per-seed times". No
randomized workload exists in either suite yet: tickets 23 to 32 own them. What does exist is
the shape such a workload must have, fixed by the coverage decision and by ticket 19's
bulk groups, so this probe runs that shape and times it. It is a timing probe and not a
testcase: it asserts nothing about the engine, writes into neither testcase repository and
produces no campaign record of its own. What it produces is the per-seed cost the placement
arithmetic needs, measured rather than assumed.

The workload per seed, derived from the seed alone so that a seed reproduces its own workload:

  1. a 1000-row deterministic helper table, built the way ticket 19's TEST 4 builds it;
  2. INSERT of `--rows` rows whose payload sizes sweep 3000..6999 bytes from the seed, so every
     row is out of row at every supported page size and the chunk count varies within one run;
  3. CHURN: UPDATE every third row to a new size (the multi-chunk growth path), DELETE every
     third row, re-INSERT them at different sizes (the slot-reuse path);
  4. VERIFY: whole-value equality of every surviving row against its generator expression, plus
     row count, payload octets and distinct digests;
  5. `SHOW HEAP OOS`, so a seed that never reached the OOS path is visible rather than timed.

`--fixture fresh` gives each seed its own database, which is what a randomized campaign
workload needs for an independent trial; `--fixture reused` keeps one database and one server
across the seeds, which is the cheaper schedule a tier could adopt. Both are measured, because
the difference between them decides whether 100 seeds fit an hour.

Standard library only; the engine is reached through csql, never through an internal API.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

HELPER = """
CREATE TABLE n10_t17 (i INT);
INSERT INTO n10_t17 VALUES (0), (1), (2), (3), (4), (5), (6), (7), (8), (9);
CREATE TABLE n1000_t17 (i INT PRIMARY KEY);
INSERT INTO n1000_t17 SELECT a.i * 100 + b.i * 10 + c.i + 1 FROM n10_t17 a, n10_t17 b, n10_t17 c;
"""


def size_expr(seed, salt):
    """3000..6999 bytes, a function of the seed and the row number and nothing else."""
    return f"(3000 + MOD(i * {seed * 7919 + salt} + {seed}, 4000))"


def char_expr(seed, salt):
    return f"SUBSTR('123456789abcdef', MOD(i * {seed + salt} + {seed}, 15) + 1, 1)"


def workload_sql(seed, rows, table):
    ins_size, ins_char = size_expr(seed, 1), char_expr(seed, 1)
    upd_size, upd_char = size_expr(seed, 2), char_expr(seed, 2)
    rei_size, rei_char = size_expr(seed, 3), char_expr(seed, 3)
    return f"""
CREATE TABLE {table} (id INT PRIMARY KEY, payload BIT VARYING, tag BIT VARYING);
INSERT INTO {table}
  SELECT i, CAST(REPEAT({ins_char}, 2 * {ins_size}) AS BIT VARYING),
            CAST(REPEAT('7', 600) AS BIT VARYING)
    FROM n1000_t17 WHERE i <= {rows};
UPDATE {table} SET payload = CAST(REPEAT(
    SUBSTR('123456789abcdef', MOD(id * {seed + 2} + {seed}, 15) + 1, 1),
    2 * (3000 + MOD(id * {seed * 7919 + 2} + {seed}, 4000))) AS BIT VARYING)
  WHERE MOD(id, 3) = 0;
DELETE FROM {table} WHERE MOD(id, 3) = 1;
INSERT INTO {table}
  SELECT i, CAST(REPEAT({rei_char}, 2 * {rei_size}) AS BIT VARYING),
            CAST(REPEAT('7', 600) AS BIT VARYING)
    FROM n1000_t17 WHERE i <= {rows} AND MOD(i, 3) = 1;
SELECT COUNT(*) AS n_rows,
       SUM(OCTET_LENGTH(payload)) AS payload_octets,
       COUNT(DISTINCT MD5(payload)) AS distinct_payloads,
       SUM(CASE WHEN OCTET_LENGTH(payload) BETWEEN 3000 AND 6999 THEN 1 ELSE 0 END) AS n_in_range
  FROM {table};
SHOW HEAP OOS OF {table};
"""


def csql(env, db, sql_path, out_path, standalone=False):
    cmd = ["csql"] + (["-S"] if standalone else []) + ["-u", "dba", db, "-i", str(sql_path)]
    with open(out_path, "wb") as fh:
        return subprocess.call(cmd, stdout=fh, stderr=subprocess.STDOUT, env=env)


def run(cmd, env, out_path=None):
    with open(out_path, "ab") if out_path else open(os.devnull, "wb") as fh:
        return subprocess.call(cmd, stdout=fh, stderr=subprocess.STDOUT, env=env)


def oos_fields(text, table):
    header = re.search(r"^(.*Has_oos_file.*)$", text, re.M)
    if not header:
        return None
    cols = header.group(1).split()
    for line in text.splitlines():
        if table in line and "'" in line:
            vals = line.split()
            if len(vals) >= len(cols):
                got = dict(zip(cols, vals[len(vals) - len(cols):]))
                return {k: int(got[k]) for k in ("Has_oos_file", "Oos_num_recs", "Oos_recs_sumlen") if k in got}
    return None


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--build", choices=("release", "debug"), default="release")
    ap.add_argument("--page-size", type=int, default=16384)
    ap.add_argument("--seeds", type=int, default=10)
    ap.add_argument("--first-seed", type=int, default=1)
    ap.add_argument("--rows", type=int, default=500)
    ap.add_argument("--fixture", choices=("fresh", "reused"), default="fresh")
    ap.add_argument("--out", required=True)
    args = ap.parse_args(argv)

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ)
    install = env["CUBRID"]
    dbroot = Path(env["CUBRID_DATABASES"])
    dbroot.mkdir(parents=True, exist_ok=True)
    if not (dbroot / "databases.txt").exists():
        (dbroot / "databases.txt").write_text("#db-name\tvol-path\t\tdb-host\t\tlog-path\t\tlob-base-path\n")
    os.chdir(dbroot)

    result = {
        "build": args.build,
        "page_size": args.page_size,
        "rows_per_seed": args.rows,
        "fixture": args.fixture,
        "install": install,
        "seeds": [],
    }
    shared_db = f"t17seed{args.page_size}{args.fixture[0]}"
    started_all = time.time()

    def createdb(db, log):
        return run(["cubrid", "createdb", "--db-volume-size=256M", "--log-volume-size=64M",
                    f"--db-page-size={args.page_size}", f"--log-page-size={args.page_size}",
                    db, "en_US.utf8"], env, log)

    if args.fixture == "reused":
        run(["cubrid", "deletedb", shared_db], env, out / "setup.log")
        createdb(shared_db, out / "setup.log")
        run(["cubrid", "server", "start", shared_db], env, out / "setup.log")
        (out / "helper.sql").write_text(HELPER)
        csql(env, shared_db, out / "helper.sql", out / "helper.out")

    for n in range(args.seeds):
        seed = args.first_seed + n
        rec = {"seed": seed, "phases": {}}
        db = shared_db if args.fixture == "reused" else f"t17seed{seed}"
        table = f"t_t17_seed{seed}"
        sql = out / f"seed{seed}.sql"
        sql.write_text((HELPER if args.fixture == "fresh" else "") + workload_sql(seed, args.rows, table))
        t0 = time.time()
        if args.fixture == "fresh":
            run(["cubrid", "deletedb", db], env, out / f"seed{seed}.setup.log")
            createdb(db, out / f"seed{seed}.setup.log")
            rec["phases"]["createdb"] = round(time.time() - t0, 3)
            t1 = time.time()
            run(["cubrid", "server", "start", db], env, out / f"seed{seed}.setup.log")
            rec["phases"]["server_start"] = round(time.time() - t1, 3)
        t2 = time.time()
        rc = csql(env, db, sql, out / f"seed{seed}.out")
        rec["phases"]["workload"] = round(time.time() - t2, 3)
        rec["csql_exit"] = rc
        text = (out / f"seed{seed}.out").read_text(errors="replace")
        rec["oos"] = oos_fields(text, table)
        m = re.search(r"^\s*(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s*$", text, re.M)
        rec["verify"] = {"n_rows": int(m.group(1)), "payload_octets": int(m.group(2)),
                         "distinct_payloads": int(m.group(3)), "n_in_range": int(m.group(4))} if m else None
        t3 = time.time()
        if args.fixture == "fresh":
            run(["cubrid", "server", "stop", db], env, out / f"seed{seed}.setup.log")
            run(["cubrid", "deletedb", db], env, out / f"seed{seed}.setup.log")
            rec["phases"]["teardown"] = round(time.time() - t3, 3)
        else:
            (out / f"drop{seed}.sql").write_text(f"DROP TABLE {table};\n")
            csql(env, db, out / f"drop{seed}.sql", out / f"seed{seed}.drop.out")
            rec["phases"]["teardown"] = round(time.time() - t3, 3)
        rec["seed_seconds"] = round(time.time() - t0, 3)
        result["seeds"].append(rec)
        print(f"[seed_cost_probe] seed {seed}: {rec['seed_seconds']} s "
              f"({', '.join(f'{k} {v}' for k, v in rec['phases'].items())}), "
              f"oos {rec['oos']}", file=sys.stderr)

    if args.fixture == "reused":
        run(["cubrid", "server", "stop", shared_db], env, out / "setup.log")
        run(["cubrid", "deletedb", shared_db], env, out / "setup.log")
    run(["cubrid", "service", "stop"], env, out / "setup.log")

    per_seed = [s["seed_seconds"] for s in result["seeds"]]
    result["total_seconds"] = round(time.time() - started_all, 2)
    result["per_seed_seconds"] = {
        "min": min(per_seed), "max": max(per_seed),
        "mean": round(sum(per_seed) / len(per_seed), 3),
        "median": round(sorted(per_seed)[len(per_seed) // 2], 3),
    }
    (out / "seed_cost.json").write_text(json.dumps(result, indent=2))
    print(f"[seed_cost_probe] {args.seeds} seeds, {args.fixture} fixture, {args.build}, "
          f"{args.page_size} B pages: total {result['total_seconds']} s, "
          f"per seed {result['per_seed_seconds']}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
