"""CBRD-27788 AC-P2 size sweep: full reads of 4~16KB values, server instructions per query."""
import argparse, json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import bench
import ordinary

ROWS = 20000
CHUNK = 128
SIZES = {"w36": 36, "w47": 47, "w78": 78, "w110": 110}
CASES = {
    "narrow": "SELECT COUNT(*), SUM(a) FROM {t};",
    "length": "SELECT SUM(LENGTH(big)) FROM {t};",
    "substr": "SELECT COUNT(*) FROM {t} WHERE SUBSTR(big, 4000, 1) = 'a';",
    "fullscan": "SELECT COUNT(*) FROM {t} WHERE big LIKE '%G%';",
}


def expected(table):
    chunks = SIZES[table]
    return {"narrow": (ROWS, sum(n % 100 for n in range(1, ROWS + 1))),
            "length": (ROWS * chunks * CHUNK,), "substr": (0,), "fullscan": (0,)}


def fixture():
    out = [f"CREATE TABLE seq (n INT PRIMARY KEY);",
           f"INSERT INTO seq SELECT ROWNUM FROM db_attribute a, db_attribute b, db_attribute c LIMIT {ROWS};"]
    for table, chunks in SIZES.items():
        big = ",".join(f"SHA2(n||'_{k}',512)" for k in range(chunks))
        out.append(f"CREATE TABLE {table} (id INT PRIMARY KEY, a INT, s VARCHAR(40), big VARCHAR(20000));")
        out.append(f"INSERT INTO {table} SELECT n, MOD(n,100), 's'||n, CONCAT({big}) FROM seq;")
    out += ["COMMIT;"] + [f"UPDATE STATISTICS ON {t};" for t in SIZES]
    return "\n".join(out) + "\n"


def measure(args):
    identity, client = bench.validate_server(args.server_pid, args.database)
    output = Path(args.output).resolve()
    output.mkdir(parents=True, exist_ok=False)
    manifest = {"schema": 1, "label": args.label, "source": args.source, "database": args.database,
                "server": identity, "server_sha256": bench.digest(identity["executable"]),
                "client_sha256": bench.digest(client), "harness_sha256": bench.digest(__file__),
                "runs": args.runs, "cases": CASES, "sizes": SIZES, "samples": [], "complete": False}
    save = lambda: (output / "summary.json").write_text(json.dumps(manifest, indent=2) + "\n")
    save()
    for table in SIZES:
        storage = output / f"{table}-storage.sql"
        storage.write_text(f"SHOW HEAP CAPACITY OF {table};\n" + (f"SHOW HEAP OOS OF {table};\n" if args.show_oos else ""))
        bench.run(bench.csql_command(args.database, storage, str(client)), output / f"{table}-storage", args.timeout)
        for case, text in CASES.items():
            for index in range(args.runs):
                name = f"{table}-{case}-{index}"
                path = output / (name + ".sql")
                path.write_text(text.format(t=table) + "\n")
                perf = output / (name + ".perf")
                command = ["perf", "stat", "-x", ";", "-e", "instructions:u,cycles:u,task-clock",
                           "-p", str(args.server_pid), "-o", str(perf), "--"]
                command += bench.csql_command(args.database, path, str(client))
                idle = ordinary.wait_for_idle(args.server_pid)
                elapsed = bench.run(command, output / name, args.timeout)
                if bench.process_identity(args.server_pid) != identity:
                    raise ValueError("server process changed during measurement")
                got = bench.results(output / (name + ".stdout"))
                if got != [expected(table)[case]]:
                    raise ValueError(f"unexpected result {got}: {name}.stdout")
                manifest["samples"].append({"table": table, "case": case, "run": index, "warmup": index == 0,
                                            "elapsed_seconds": elapsed, "pre_count_idle_cpu_seconds": idle,
                                            "counters": bench.counters(perf)})
                save()
    manifest["complete"] = True
    save()
    print(output / "summary.json")


def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="action", required=True)
    sub.add_parser("fixture")
    m = sub.add_parser("measure")
    for flag in ("--database", "--label", "--source", "--output"):
        m.add_argument(flag, required=True)
    m.add_argument("--server-pid", type=int, required=True)
    m.add_argument("--runs", type=int, default=6)
    m.add_argument("--timeout", type=int, default=600)
    m.add_argument("--show-oos", action="store_true")
    args = parser.parse_args()
    if args.action == "fixture":
        sys.stdout.write(fixture())
    else:
        measure(args)


if __name__ == "__main__":
    main()
