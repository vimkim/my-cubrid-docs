#!/usr/bin/env python3
"""Run PR7990 comment 6461744209 without changing its DDL or query SQL."""

import argparse
import configparser
import csv
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import statistics
import subprocess
import sys
import time
from datetime import datetime, timezone


CASES = ["w_small", "w_length", "w_substr", "w_update_small",
         "w_update_big", "n_scan", "n_pred", "n_update"]
REVISIONS = {"base": "4781495f01523a3ecc5891e3377ad62cf876a1cd",
             "feature": "4408135c0833ec959da3590f12c14efa69610c7e"}
DATABASE = "rvx31"
PRESET = "release_gcc_nounit"


def stamp():
    return datetime.now(timezone.utc).isoformat()


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save(path, data):
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
    temporary.replace(path)


def capture(command, environment=None, cwd=None):
    return subprocess.check_output(command, env=environment, cwd=cwd, text=True)


def command(argv, prefix, environment=None, cwd=None, timeout=600, session=False):
    prefix.parent.mkdir(parents=True, exist_ok=True)
    save(Path(str(prefix) + ".command.json"), {"argv": argv, "cwd": str(cwd), "started": stamp()})
    start = time.monotonic()
    with Path(str(prefix) + ".stdout").open("w") as out, Path(str(prefix) + ".stderr").open("w") as err:
        process = subprocess.Popen(argv, env=environment, cwd=cwd, stdin=subprocess.DEVNULL,
                                   stdout=out, stderr=err, start_new_session=session, close_fds=True)
        try:
            code = process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            # Leave storage and a potentially active server intact for inspection.
            save(Path(str(prefix) + ".timeout.json"), {"pid": process.pid, "at": stamp(), "argv": argv})
            raise
    elapsed = time.monotonic() - start
    save(Path(str(prefix) + ".exit.json"), {"returncode": code, "elapsed_seconds": elapsed, "ended": stamp()})
    errors = Path(str(prefix) + ".stderr").read_text()
    if code or re.search(r"\b(?:ERROR|Error):", errors):
        raise RuntimeError(f"Command failed ({code}): {prefix}")
    return elapsed


def environment(worktree):
    shell = capture(["cub-workenv", "env", "--worktree", str(worktree), "--preset", PRESET])
    payload = capture(["bash", "--noprofile", "--norc", "-c", shell +
                       "\nexec python3 -c 'import os,json;print(json.dumps(dict(os.environ)))'"])
    return json.loads(payload)


def tuples(path):
    return [tuple(map(int, line.split())) for line in path.read_text().splitlines()
            if re.fullmatch(r"\s*-?\d+(?:\s+-?\d+)*\s*", line)]


def csql(env, path):
    return [str(Path(env["CUBRID"]) / "bin/csql"), "-C", "-u", "dba", "--no-pager", "-t", "-N",
            "-i", str(path), DATABASE]


def sql(env, text, prefix):
    path = Path(str(prefix) + ".sql")
    path.write_text(text)
    command(csql(env, path), prefix, env)
    return tuples(Path(str(prefix) + ".stdout"))


def identity(pid):
    proc = Path("/proc") / str(pid)
    return {"pid": pid, "executable": str((proc / "exe").resolve()),
            "start_ticks": int((proc / "stat").read_text().rsplit(")", 1)[1].split()[19])}


def owned_processes(env, server_only=False):
    found = []
    for p in Path("/proc").iterdir():
        if not p.name.isdigit():
            continue
        try:
            binary = (p / "exe").resolve()
            pairs = dict(x.split(b"=", 1) for x in (p / "environ").read_bytes().split(b"\0") if b"=" in x)
            if pairs.get(b"CUBRID_CONF_FILE", b"").decode() != env["CUBRID_CONF_FILE"]:
                continue
            if server_only and (binary != (Path(env["CUBRID"]) / "bin/cub_server").resolve()
                                or DATABASE not in (p / "cmdline").read_bytes().replace(b"\0", b" ").decode().split()):
                continue
            if binary.name in {"cub_server", "cub_master", "cub_pl", "java", "cub_broker"}:
                found.append(identity(int(p.name)))
        except (OSError, ValueError, ProcessLookupError):
            continue
    return found


def binary_identity(install):
    result = {}
    for relative in ["bin/cub_server", "bin/csql", "lib/libcubrid.so.11.5"]:
        path = install / relative
        notes = capture(["readelf", "-n", str(path)])
        result[relative] = {"sha256": digest(path),
                            "build_id": re.search(r"Build ID: (\S+)", notes).group(1)}
    return result


def prepare(root, base, feature, tooling):
    if (root / "protocol.json").exists():
        raise RuntimeError("Protocol already exists; preserve the original preparation")
    comment = json.loads((root / "comment-6461744209.json").read_text())
    blocks = re.findall(r"```sql\s*\n(.*?)```", comment["body"].replace("\r", ""), re.S)
    assert len(blocks) == 2
    ddl, query_block = blocks
    queries = [line.strip() for line in query_block.splitlines() if line.strip() and not line.lstrip().startswith("--")]
    assert len(queries) == 8 and all(q.endswith(";") for q in queries)
    assert not re.search(r"ORDER\s+BY|UPDATE\s+STATISTICS|COMMIT", ddl, re.I)
    (root / "original-ddl.sql").write_text(ddl)
    (root / "original-queries.sql").write_text(query_block)
    save(root / "queries.json", dict(zip(CASES, queries)))

    # The host tool hardcodes 64M/32M. Keep its registration and ownership logic,
    # changing only the two native createdb arguments required by the comment.
    copy = root / "sized-workenv"
    shutil.copytree(tooling / "cubrid_workenv", copy / "cubrid_workenv",
                    ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    module = copy / "cubrid_workenv/database.py"
    original = module.read_text()
    old = "'--db-volume-size=64M', '--log-volume-size=32M'"
    new = "'--db-volume-size=2G', '--log-volume-size=1G'"
    assert original.count(old) == 1
    module.write_text(original.replace(old, new))
    assert module.read_text().replace(new, old) == original
    launcher = copy / "cub-workenv.py"
    launcher.write_text("from cubrid_workenv.cli import main\nraise SystemExit(main())\n")

    protocol = {"created": stamp(), "source": comment["url"], "comment_sha256": digest(root / "comment-6461744209.json"),
                "ddl_sha256": digest(root / "original-ddl.sql"), "queries_sha256": digest(root / "original-queries.sql"),
                "harness_sha256": digest(__file__), "revisions": REVISIONS, "variants": {},
                "database": DATABASE, "rounds": 4, "runs_per_case_per_round": 5, "discard_first": True,
                "case_order": CASES, "update_state": "same original tables, consecutive autocommitted UPDATEs; no reset between samples or rounds",
                "user_selected_assumptions": ["Use first comment feature 4408135 and consecutive UPDATEs because no extra information is available",
                                              "Run all four rounds today and disclose the original two-day spacing difference"],
                "round_order": [["base", "feature"], ["feature", "base"], ["base", "feature"], ["feature", "base"]],
                "known_gaps": ["Later comment omits feature SHA; use 4408135 named in first comment",
                               "Original compiler, full flags, locale, client options and UPDATE/reset cadence are not supplied",
                               "Four rounds collected in one session unless separately resumed; original spans two days",
                               "Host workenv allocates distinct master ports instead of shared port 1523",
                               "Variant order and server restart cadence are explicit local assumptions"],
                "tooling_source": {"commit": capture(["git", "rev-parse", "HEAD"], cwd=tooling).strip(),
                                   "database_py_sha256": hashlib.sha256(original.encode()).hexdigest(),
                                   "patched_sha256": digest(module), "only_change": [old, new]}}
    conf = re.search(r"```\s*\n(\[common\].*?)```", comment["body"].replace("\r", ""), re.S).group(1)
    settings = configparser.ConfigParser()
    settings.read_string(conf)
    (root / "original-cubrid.conf").write_text(conf)
    for name, worktree in [("base", base), ("feature", feature)]:
        out = root / name
        out.mkdir()
        assert capture(["git", "rev-parse", "HEAD"], cwd=worktree).strip() == REVISIONS[name]
        assert not capture(["git", "status", "--porcelain", "--untracked-files=no"], cwd=worktree).strip()
        install = Path.home() / ".cub/install" / worktree.name / PRESET
        command(["cub-workenv", "init", "--worktree", str(worktree), "--install", str(install),
                 "--preset", PRESET, "--no-db"], out / "init", timeout=120)
        env = environment(worktree)
        config = Path(env["CUBRID_CONF_FILE"])
        cfg = configparser.ConfigParser()
        cfg.read(config)
        for key, value in settings["common"].items():
            if key != "cubrid_port_id":
                cfg["common"][key] = value
        with config.open("w") as f:
            cfg.write(f)
        create_env = os.environ.copy()
        create_env["PYTHONPATH"] = str(copy)
        command([sys.executable, str(launcher), "create-db", "--worktree", str(worktree),
                 "--path", str(out / "database"), DATABASE], out / "createdb", create_env, timeout=180)
        state = json.loads((worktree / ".cub-workenv/state.json").read_text())
        build_dir = worktree / ("build_preset_" + PRESET)
        shutil.copy2(build_dir / "CMakeCache.txt", out / "CMakeCache.txt")
        cache = {}
        for line in (out / "CMakeCache.txt").read_text().splitlines():
            if "=" in line and not line.startswith(("#", "//")):
                key, value = line.split("=", 1)
                cache[key.split(":", 1)[0]] = value
        units = {k: v for k, v in cache.items() if k.startswith("UNIT_TEST")}
        assert units and set(units.values()) == {"OFF"}
        assert cache["CMAKE_BUILD_TYPE"] == "RelWithDebInfo"
        compiles = json.loads((build_dir / "compile_commands.json").read_text())
        selected = [e for e in compiles if e["file"].endswith("/heap_file.c")]
        assert selected
        for entry in selected:
            line = entry["command"]
            assert "-O2" in line and "-DNDEBUG" in line and "CUBRID_UNIT_TEST_ENABLED" not in line
        save(out / "compile-commands.json", selected)
        primary = out / "database/data" / DATABASE
        active_log = out / "database/log" / (DATABASE + "_lgat")
        assert primary.stat().st_size == 2 * 1024 ** 3
        assert active_log.stat().st_size == 1024 ** 3
        registry = Path(env["CUBRID_DATABASES"]) / "databases.txt"
        assert [line.split()[0] for line in registry.read_text().splitlines() if line.strip()] == [DATABASE]
        info = {"worktree": str(worktree), "revision": REVISIONS[name], "install": str(install),
                "preset": PRESET, "unit_options": units, "compiler": capture([cache["CMAKE_CXX_COMPILER"], "--version"]).splitlines()[0],
                "binary_identity": binary_identity(install), "configuration": config.read_text(),
                "physical_data_bytes": primary.stat().st_size, "physical_log_bytes": active_log.stat().st_size,
                "allocation": state["allocation"], "registry": registry.read_text(),
                "environment": {k: v for k, v in env.items() if k in {"CUBRID", "CUBRID_CONF_FILE", "CUBRID_DATABASES", "CUBRID_TMP", "TMPDIR", "JAVA_HOME", "LD_LIBRARY_PATH"}}}
        save(out / "build.json", info)
        protocol["variants"][name] = info
    save(root / "protocol.json", protocol)
    print("Prepared original DDL/SQL and isolated release installations", root, flush=True)


def expected(case, round_index, insensitive):
    if case == "w_small":
        return (20000, 990000 + round_index * 5 * 20000)
    if case == "w_length":
        return (120320000,)
    if case == "n_scan":
        return (200000, 9900000 + round_index * 5 * 200000)
    if case == "n_pred":
        return (sum(hashlib.sha256(str(i).encode()).hexdigest().upper()[29] == "A" for i in range(1, 200001)) if insensitive else 0,)
    if case == "w_substr":
        position = (4999 + round_index * 5) % 6016
        chunk, offset = divmod(position, 128)
        return (sum(hashlib.sha512(f"{i}_{chunk}".encode()).hexdigest().upper()[offset] == "A" for i in range(1, 20001)) if insensitive else 0,)
    return None


def instructions(path):
    rows = [r for r in csv.reader(path.read_text().splitlines(), delimiter=";")
            if len(r) > 4 and r[2] == "instructions:u"]
    assert len(rows) == 1, path
    row = rows[0]
    count, running = int(row[0].strip()), float(row[4])
    assert count > 0 and running >= 95, row
    return {"value": count, "running_percent": running, "event_runtime_ns": int(row[3])}


def check_state(env, prefix, update_count):
    text = (f"SELECT COUNT(*),SUM(CASE WHEN a=MOD(id,100)+{update_count} THEN 1 ELSE 0 END),SUM(LENGTH(big)) FROM w;\n"
            f"SELECT COUNT(*),SUM(CASE WHEN a=MOD(id,100)+{update_count} THEN 1 ELSE 0 END),SUM(LENGTH(s)) FROM n;\n")
    expected_rows = [(20000, 20000, 120320000), (200000, 200000, 12800000)]
    for i in [1, 17, 5000, 5001, 20000]:
        value = "".join(hashlib.sha512(f"{i}_{j}".encode()).hexdigest().upper() for j in range(47))
        shift = update_count % len(value) if i <= 5000 else 0
        value = value[shift:] + value[:shift]
        h = hashlib.sha256(value.encode()).hexdigest().upper()
        text += f"SELECT COUNT(*) FROM w WHERE id={i} AND SHA2(big,256)='{h}';\n"
        expected_rows.append((1,))
    actual = sql(env, text, prefix)
    assert actual == expected_rows, (prefix, actual, expected_rows)
    return {"update_count": update_count, "results": actual}


def summarize(data):
    result = {}
    for variant in REVISIONS:
        result[variant] = {}
        for case in CASES:
            kept = [s for s in data["samples"] if s["variant"] == variant and s["case"] == case and not s["warmup"]]
            if not kept:
                continue
            values = [s["instructions"]["value"] for s in kept]
            result[variant][case] = {"n": len(values), "median": statistics.median(values), "min": min(values), "max": max(values),
                                     "round_medians": {str(r): statistics.median(s["instructions"]["value"] for s in kept if s["round"] == r)
                                                       for r in sorted({s["round"] for s in kept})}}
    return result


def run(root, first_round, rounds):
    protocol = json.loads((root / "protocol.json").read_text())
    assert protocol["harness_sha256"] == digest(__file__), "Harness changed after preparation"
    assert protocol["ddl_sha256"] == digest(root / "original-ddl.sql")
    assert protocol["queries_sha256"] == digest(root / "original-queries.sql")
    queries = json.loads((root / "queries.json").read_text())
    path = root / "results.json"
    data = json.loads(path.read_text()) if path.exists() else {"protocol": str(root / "protocol.json"), "samples": [], "completed_pairs": [], "complete": False}
    assert 0 <= first_round < first_round + rounds <= 4
    envs = {k: environment(Path(v["worktree"])) for k, v in protocol["variants"].items()}
    for env in envs.values():
        assert not owned_processes(env), "Unexpected pre-existing owned instance"
    for r in range(first_round, first_round + rounds):
        for name in protocol["round_order"][r]:
            assert [name, r] not in data["completed_pairs"]
            assert not any(s["variant"] == name and s["round"] == r for s in data["samples"]), "Partial round retained; inspect instead of overwriting"
            out = root / name / f"round-{r}"
            out.mkdir()
            env = envs[name]
            meta = protocol["variants"][name]
            assert binary_identity(Path(env["CUBRID"])) == meta["binary_identity"]
            assert not any(owned_processes(e, True) for e in envs.values())
            print(stamp(), name, "round", r, "starting", flush=True)
            try:
                command([str(Path(env["CUBRID"]) / "bin/cubrid"), "server", "start", DATABASE], out / "start", env,
                        cwd=out, timeout=90, session=True)
                servers = owned_processes(env, True)
                assert len(servers) == 1, servers
                server = servers[0]
                pid = server["pid"]
                save(out / "server.json", server)
                (out / "maps.txt").write_text((Path("/proc") / str(pid) / "maps").read_text())
                assert str((Path(env["CUBRID"]) / "lib/libcubrid.so.11.5").resolve()) in (out / "maps.txt").read_text()
                command([str(Path(env["CUBRID"]) / "bin/cubrid"), "paramdump", "-C", "-b", DATABASE], out / "parameters", env)
                parameters = Path(str(out / "parameters") + ".stdout").read_text()
                for key, value in {"data_buffer_size": "4.0G", "log_buffer_size": "256.0M",
                                   "sort_buffer_size": "16.0M", "max_clients": "50",
                                   "db_volume_size": "2.0G", "log_volume_size": "1.0G",
                                   "csql_auto_commit": "y"}.items():
                    assert re.search(r"\b" + key + "=" + re.escape(value) + r"\s", parameters), (key, value)
                if r == 0:
                    command(csql(env, root / "original-ddl.sql"), out / "fixture", env)
                    check_state(env, out / "initial-state", 0)
                insensitive = sql(env, "SELECT CASE WHEN 'A'='a' THEN 1 ELSE 0 END;\n", out / "collation")[0][0]
                for case in CASES:
                    for sample in range(5):
                        prefix = out / f"{case}-{sample}"
                        query = queries[case]
                        query_path = Path(str(prefix) + ".sql")
                        query_path.write_text(query + "\n")
                        io_before = (Path("/proc") / str(pid) / "io").read_text()
                        argv = ["perf", "stat", "-x", ";", "-e", "instructions:u", "-p", str(pid), "-o", str(prefix) + ".perf", "--"] + csql(env, query_path)
                        elapsed = command(argv, prefix, env, timeout=1200)
                        assert identity(pid) == server
                        result = tuples(Path(str(prefix) + ".stdout"))
                        want = expected(case, r, insensitive)
                        if want is not None:
                            assert result == [want], (case, result, want)
                        else:
                            assert not result
                        record = {"variant": name, "round": r, "case": case, "run": sample,
                                  "warmup": sample == 0, "sql": query, "instructions": instructions(Path(str(prefix) + ".perf")),
                                  "elapsed_seconds": elapsed, "results": result, "at": stamp(),
                                  "loadavg": Path("/proc/loadavg").read_text().strip(),
                                  "io_before": io_before, "io_after": (Path("/proc") / str(pid) / "io").read_text()}
                        data["samples"].append(record)
                        data["summary"] = summarize(data)
                        save(path, data)
                    median = data["summary"][name][case]["round_medians"][str(r)]
                    print(stamp(), name, r, case, "median instructions", median, flush=True)
                save(out / "verified-state.json", check_state(env, out / "final-state", (r + 1) * 5))
                data["completed_pairs"].append([name, r])
                save(path, data)
            finally:
                command([str(Path(env["CUBRID"]) / "bin/cubrid"), "server", "stop", DATABASE], out / "stop", env, timeout=180, session=True)
                command([str(Path(env["CUBRID"]) / "bin/cubrid"), "service", "stop"], out / "service-stop", env, timeout=90, session=True)
                time.sleep(1)
                assert not owned_processes(env), "Owned runtime remains; inspect before continuing"
    data["summary"] = summarize(data)
    data["complete"] = len(data["completed_pairs"]) == 8
    save(path, data)
    print("Campaign complete:", data["complete"], "samples:", len(data["samples"]), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)
    prep = sub.add_parser("prepare")
    prep.add_argument("--root", type=Path, required=True)
    prep.add_argument("--base-worktree", type=Path, required=True)
    prep.add_argument("--feature-worktree", type=Path, required=True)
    prep.add_argument("--tooling", type=Path, required=True)
    execute = sub.add_parser("run")
    execute.add_argument("--root", type=Path, required=True)
    execute.add_argument("--first-round", type=int, default=0)
    execute.add_argument("--rounds", type=int, default=4)
    args = parser.parse_args()
    if args.action == "prepare":
        prepare(args.root.resolve(), args.base_worktree.resolve(), args.feature_worktree.resolve(), args.tooling.resolve())
    else:
        run(args.root.resolve(), args.first_round, args.rounds)


if __name__ == "__main__":
    main()
