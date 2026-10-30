#!/usr/bin/env python3
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import xml.etree.ElementTree as ET

parser = argparse.ArgumentParser(description="Verify retained SQL3 NOK artifacts and error-number drift. Does not run or modify tests.")
parser.add_argument("--artifacts", type=Path, required=True)
parser.add_argument("--testcases", type=Path, required=True)
parser.add_argument("--engine", type=Path, required=True)
parser.add_argument("--producer", type=Path, required=True)
args = parser.parse_args()
if sys.flags.optimize:
    parser.error("Run without -O; this evidence check uses assertions.")

engine = "e3589ae42d42b04eb020e1ae43e165b01d31b12a"
old_engine = "fb567a629cdb390fff920542173fa36f454c74a0"
tc = "45e21ad799d82ebadc04a93c7d2f69517d53bf39"
cases = [
    ("rb05", "cbrd_26659_oos_record_boundaries", 1, 93),
    ("b03", "cbrd_26659_oos_sql05_bigone", 2, 122),
    ("l01", "cbrd_26659_oos_sql09_lob_maxcols", 1, 1079),
]
jars = {
    "sql/lib/cubridqa-cqt.jar": "926a1a6c3d73f91344a3e4a2446b51c7fe7329be5de413d90979ba8209052f0f",
    "sql/lib/cubrid_jdbc.jar": "17e2e0ee4c0756b4b0a7cd679f1fea4630124f5704bc69db0c2107235190ff98",
}
runtime_files = ["bin/cub_master", "bin/cub_server", "bin/csql", "bin/cubrid", "bin/cubrid_rel", "lib/libcubrid.so.11.5"]
for revision, number in [(old_engine, -1384), (engine, -1388)]:
    header = subprocess.check_output(["git", "-C", str(args.engine), "show", f"{revision}:src/base/error_code.h"], text=True)
    assert re.search(rf"^#define\s+ER_HEAP_OOS_OVERPASS_MAXOBJ_SIZE\s+{number}\s*$", header, re.M), revision

records = []
for attempt, name, differences, milliseconds in cases:
    root = args.artifacts.resolve() / attempt
    identity = json.loads((root / "identity.json").read_text())
    observation = json.loads((root / "observation.json").read_text())
    assert (identity["engine"], identity["testcases"], identity["case"], identity["preflight_exit"]) == (engine, tc, name, 0), attempt
    assert observation["runner_exit"] == 0 and observation["verify_exit"] == 1, attempt
    assert observation["watchdog"] is None and 0 < observation["wall_seconds"] < 120, attempt
    original = {}
    assert len(identity["input_files"]) == 2, attempt
    for folder, suffix, disabled in [("cases", ".sql", ".disabled"), ("answers", ".answer", "")]:
        source = f"disabled/failing/sql/_36_guava/cbrd_26659/{folder}/{name}{suffix}{disabled}"
        copied = root / "testcases/sql/_36_guava/cbrd_26659" / folder / (name + suffix)
        data = subprocess.check_output(["git", "-C", str(args.testcases), "show", f"{tc}:{source}"])
        entry, = [f for f in identity["input_files"] if f["source"] == source]
        assert Path(entry["copy"]) == copied and copied.read_bytes() == data, source
        assert hashlib.sha256(data).hexdigest() == entry["sha256"], source
        assert (args.testcases / source).read_bytes() == data, source
        original[folder] = data
    for relative, expected_hash in jars.items():
        assert hashlib.sha256((root / "CTP" / relative).read_bytes()).hexdigest() == expected_hash, relative
        assert identity[relative + "_sha256"] == expected_hash, relative
    for relative in runtime_files:
        assert hashlib.sha256((root / "cubrid" / relative).read_bytes()).digest() == hashlib.sha256((args.producer / relative).read_bytes()).digest(), (attempt, relative)

    case = root / "testcases/sql/_36_guava/cbrd_26659/cases" / (name + ".sql")
    assert (root / "expected-cases.txt").read_text().splitlines() == [str(case)], attempt
    run_log = (root / "run.log").read_text()
    result = Path(observation["result_root"])
    assert result.is_relative_to(root / "CTP/sql/result"), result
    assert re.findall(r"^Result Root Dir:(.+)$", run_log, re.M) == [str(result)], attempt
    completed = re.findall(r"^\[\d\d:\d\d:\d\d\] Testing (.+?) \(1/1 100\.00%\) \[([^]]+)\]$", run_log, re.M)
    assert completed == [(str(case), "NOK")], (attempt, completed)
    counts = {}
    for filename in ["main.info", "summary_info"]:
        values = dict(line.partition(":")[::2] for line in (result / filename).read_text().splitlines() if ":" in line)
        for key, value in [("total", "1"), ("success", "0"), ("fail", "1")]:
            assert values[key] == value, (attempt, filename, key)
        assert values["totalTime"] == str(milliseconds) + ("ms" if filename == "summary_info" else ""), filename
        counts[filename] = values
    assert counts["main.info"]["execute_case"] == "1", attempt
    assert counts["main.info"]["build"] == "11.5.0.2793-e3589ae", attempt
    assert counts["main.info"]["result_path"] == str(result), attempt
    xml = ET.parse(result / "linux_sql_64bit.xml")
    suite, = xml.findall(".//testsuite")
    element, = xml.findall(".//testcase")
    assert suite.get("tests") == "1" and suite.get("failures") == "1", attempt
    assert element.get("name") == str(case) and element.get("file") == str(case), attempt
    assert float(element.get("time")) == milliseconds / 1000, attempt
    assert len(element.findall("failure")) == 1 and not element.findall("skipped") and not element.findall("error"), attempt
    actual = case.with_suffix(".result").read_bytes()
    answer = original["answers"]
    assert answer != actual and answer.count(b"Error:-1384") == differences, attempt
    assert answer.replace(b"Error:-1384", b"Error:-1388") == actual, attempt
    changed_lines = [i for i, (a, b) in enumerate(zip(answer.splitlines(), actual.splitlines()), 1) if a != b]
    assert len(changed_lines) == differences, attempt
    records.append({"attempt": attempt, "case": name, "original_verdict": "NOK", "case_seconds": milliseconds / 1000,
                    "whole_command_seconds": observation["wall_seconds"], "changed_answer_lines": changed_lines,
                    "answer_sha256": hashlib.sha256(answer).hexdigest(), "result_sha256": hashlib.sha256(actual).hexdigest()})

print(json.dumps({"diagnosis_verified": True, "original_pass": 0, "original_nok": 3, "error_number_differences": 4,
                  "timeout_limit_enforcement_verified": False, "all_whole_commands_under_120_seconds": True,
                  "scope": "Retained artifacts only. Offline substitution does not grant PASS or reactivate a testcase.", "cases": records}, indent=2))
