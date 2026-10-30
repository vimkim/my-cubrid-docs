#!/usr/bin/env python3
"""Repeat the original SQL in fresh ISO-8859-1 DBs after the UTF-8 campaign."""

import argparse
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--primary-root", type=Path, required=True)
    args = parser.parse_args()
    primary = args.primary_root.resolve()
    first = json.loads((primary / "results.json").read_text())
    assert first["complete"] and len(first["samples"]) == 320
    root = primary / "iso88591"
    root.mkdir(exist_ok=False)
    spec = importlib.util.spec_from_file_location("reproduction", primary / "harness.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    m.DATABASE = "rvxi31"
    protocol = copy.deepcopy(json.loads((primary / "protocol.json").read_text()))
    protocol["created"] = m.stamp()
    protocol["database"] = m.DATABASE
    protocol["locale"] = "en_US.iso88591"
    protocol["parent_campaign"] = str(primary)
    protocol["locale_launcher_sha256"] = m.digest(__file__)
    protocol["purpose"] = "Test the missing locale condition; matching numbers do not identify the reviewer's locale"
    protocol["known_gaps"].append("ISO-8859-1 is a separate local hypothesis, not a confirmed reviewer input")
    for name in ["original-ddl.sql", "original-queries.sql", "original-cubrid.conf", "queries.json"]:
        shutil.copy2(primary / name, root / name)
    shutil.copytree(primary / "sized-workenv", root / "sized-workenv",
                    ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    database_module = root / "sized-workenv/cubrid_workenv/database.py"
    old = database_module.read_text()
    assert old.count("'en_US.utf8'") == 1
    database_module.write_text(old.replace("'en_US.utf8'", "'en_US.iso88591'"))
    assert database_module.read_text().replace("'en_US.iso88591'", "'en_US.utf8'") == old
    protocol["locale_tool_change"] = {"before_sha256": hashlib.sha256(old.encode()).hexdigest(),
                                      "after_sha256": m.digest(database_module),
                                      "replacement": ["en_US.utf8", "en_US.iso88591"]}
    for name, meta in protocol["variants"].items():
        env = m.environment(Path(meta["worktree"]))
        assert not m.owned_processes(env)
        registry = Path(env["CUBRID_DATABASES"]) / "databases.txt"
        before = registry.read_bytes()
        assert {line.split()[0] for line in before.decode().splitlines() if line.strip()} == {"rvx31"}
        out = root / name
        out.mkdir()
        create_env = os.environ.copy()
        create_env["PYTHONPATH"] = str(root / "sized-workenv")
        m.command([sys.executable, str(root / "sized-workenv/cub-workenv.py"), "create-db", "--worktree", meta["worktree"],
                   "--path", str(out / "database"), m.DATABASE], out / "createdb", create_env, timeout=180)
        assert registry.read_bytes().startswith(before), "Existing DB registration changed"
        assert {line.split()[0] for line in registry.read_text().splitlines() if line.strip()} == {"rvx31", m.DATABASE}
        meta["registry"] = registry.read_text()
        meta["locale"] = protocol["locale"]
        assert (out / "database/data" / m.DATABASE).stat().st_size == meta["physical_data_bytes"]
        assert (out / "database/log" / (m.DATABASE + "_lgat")).stat().st_size == meta["physical_log_bytes"]
        assert m.binary_identity(Path(env["CUBRID"])) == meta["binary_identity"]
        m.save(out / "build.json", meta)
    m.save(root / "protocol.json", protocol)
    m.run(root, 0, 4)


if __name__ == "__main__":
    main()
