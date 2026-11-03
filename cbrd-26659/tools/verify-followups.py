#!/usr/bin/env python3
"""Verify retained Work715 repair and diagnosis evidence without native DB runs."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--root", required=True, type=Path)
parser.add_argument("--testcases", required=True, type=Path)
args = parser.parse_args()
root = args.root.resolve()
engine = "e3589ae42d42b04eb020e1ae43e165b01d31b12a"
base = "01df2600ac75180812451462b5c044cfa56b732a"
checks = json.loads((root / "tc-integration.json").read_text())
assert checks["base"] == base and checks["exact_tested_candidate_blobs"]
assert len(checks["changed_paths"]) == 7
publication = json.loads((root / "tc-publication.json").read_text())
assert publication["remote"] == checks["tip"] == publication["local"]
assert publication["push_exit"] == 0
for lane, script, expected in [('b-repartition', 'verify-evidence.py', 'd9200e8b4d2a2f81822389fb2c6d140577ad1e7169f22ee7a59f01eac3419833'), ('c-fail14', 'analyze.py', 'e16197f2d8f129b22c58759dcddb1312c2ad1be7a244373fa20c35bd43343de5'), ('d-timeout', 'verify-result.py', '642c9e627302b1e85b3ed0b11de3707675684ed67dd85a237082cdd2073c2f8c')]:
    path = root / lane / script
    assert hashlib.sha256(path.read_bytes()).hexdigest() == expected, path
    result = subprocess.run([sys.executable, str(path)], cwd=path.parent, capture_output=True, text=True)
    assert result.returncode == 0, (lane, result.stdout, result.stderr)

focused = Path("/home/vimkim/.agents/skills/cubrid-common/scripts/testkit-focused.py")
a = json.loads((root / "a-tde/result.json").read_text())
assert a["engine"] == engine and a["tc_base"] == base
assert len(a["cases"]) == 2
for case in a["cases"]:
    assert case["verdict"] == "PASS" and case["runner_exit"] == case["verifier_exit"] == 0
    assert case["cleanup_clear"] and case["containment_observed"]
    assert case["aes_acknowledgements"] == [["baseline", "AES"], ["recovered", "AES"]]
    attempt = Path(case["attempt"])
    result = subprocess.run([sys.executable, str(focused), "verify", "--suite", "shell", "--result-dir", case["result_dir"], "--expected-list", str(attempt / "expected-cases.txt"), "--run-log", str(attempt / "run.log"), "--runner-exit", "0"], capture_output=True, text=True)
    assert result.returncode == 0, (case["case"], result.stdout, result.stderr)
    observed = json.loads((attempt / "observation.json").read_text())
    assert not observed["remaining_owned_processes"] and not observed["remaining_observed_namespace_holders"]
    assert not observed["remaining_host_mounts"] and not observed["remaining_sockets"]

b = json.loads((root / "b-repartition/result.json").read_text())
assert b["engine_sha"] == engine and b["tc_base_sha"] == base
assert b["status"] == "PASS" and len(b["attempts"]) == 1
assert set(b["attempts"][0]["policies"]) == {"default", "force_outline"}
c = json.loads((root / "c-fail14/result.json").read_text())
assert c["engine_sha"] == engine and c["tc_sha"] == base
assert len(c["cases"]) == len({x["case"] for x in c["cases"]}) == 14
assert all(x["verdict"] == "FAIL" for x in c["cases"])
unknown = [x for x in c["cases"] if x["attribution"].startswith("Unknown:")]
assert len(unknown) == 6 and not c["attempts"]
d = json.loads((root / "d-timeout/result.json").read_text())
assert d["engine_sha"] == engine and d["tc_sha"] == base
assert d["prior_attempt"]["runner_exit"] == 124
assert d["replay"]["runner_exit"] == d["replay"]["verifier_exit"] == 0
assert d["replay"]["native_timeout_seconds"] == 750
assert d["replay"]["outer_timeout_seconds"] == 780
assert len(d["replay"]["phases"]) == 18
for file in checks["changed_paths"]:
    candidate = b["tc_commit"] if file.endswith("oos08_partitions.sh") else a["tc_commit"]
    blobs = []
    for commit in (checks["tip"], candidate):
        blobs.append(subprocess.check_output(["git", "-C", str(args.testcases), "rev-parse", commit + ":" + file], text=True).strip())
    assert blobs[0] == blobs[1], file
receipt = json.loads((root / "ci-trigger-receipt.json").read_text())
assert receipt["engine"] == engine and receipt["tc_private"] == checks["tip"]
print(json.dumps({"verified": True, "engine": engine, "tc_published": checks["tip"], "tde_pass": 2, "repartition_pass": 1, "repartition_policies": 2, "retained_failures": 14, "supported_engine_findings": 8, "unknown_causes": 6, "schema_extended_diagnostic_pass": 1, "original_schema_timeout_retained": True, "ci_terminal_present": (root / "ci-terminal.json").exists()}, indent=2))
