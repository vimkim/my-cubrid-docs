"""Reproduce the historical SQL report discrepancy; do not certify suite success."""

import argparse
import hashlib
import io
import json
from pathlib import Path
import re
import subprocess
import tarfile
import tempfile
import textwrap
import xml.etree.ElementTree as ET

parser = argparse.ArgumentParser(description=__doc__)
for name in ["bundle", "collector-result", "engine-git", "testcase-git", "ctp-git"]:
    parser.add_argument("--" + name, required=True, type=Path)
parser.add_argument("--schemas", type=Path, default=Path("/home/vimkim/gh/cubrid-ci/schema"))
args = parser.parse_args()
engine = "e3589ae42d42b04eb020e1ae43e165b01d31b12a"
workflow_sha = "4f1a68c1ebec12f29bc8ba98b5ce8cacb1fc8735"
testcase_sha = "45e21ad799d82ebadc04a93c7d2f69517d53bf39"
ctp_sha = "ef6712ab450a9c8a6b5bf41d605b1683bd60a3a2"
result = json.loads(args.collector_result.read_text())
manifest = json.loads((args.bundle / "manifest.json").read_text())
observations = [p for p in (args.bundle / "observations").glob("*/result.json")
                if json.loads(p.read_text()).get("command") == result]
assert len(observations) == 1, "Collector observation must match the historical result exactly"
observation_path = observations[0]
observation = json.loads(observation_path.read_text())
request_path = observation_path.parent / "request.json"
request = json.loads(request_path.read_text())
assert request["observation_id"] == observation["observation_id"]
for path, schema in [
    (args.collector_result, "command-result-v2.schema.json"),
    (args.bundle / "manifest.json", "manifest-v2.schema.json"),
    (observation_path, "collection-observation-result-v1.schema.json"),
    (request_path, "collection-observation-request-v1.schema.json"),
]:
    validation = subprocess.run(
        ["jsonschema", "-i", str(path), str(args.schemas / schema)],
        text=True, capture_output=True,
    )
    assert validation.returncode == 0, validation.stderr
assert result["repository"] == manifest["repository"] == "CUBRID/cubrid"
assert result["commit"] == manifest["commit"] == engine
assert result["pr"]["number"] == manifest["pr"]["number"] == 8128
assert result["suites"]["test_sql"]["execution"] == {"run_id": 40837919358, "attempt": 1}
assert result["suites"]["test_sql"]["state"] == "collection_failed"
raw = args.bundle / "providers/github-actions/runs/40837919358/attempts/1/test_sql/raw"
workflow = subprocess.check_output(
    ["git", "-C", str(args.engine_git), "show", workflow_sha + ":.github/workflows/gha-ci.yml"],
    text=True,
)
lines = workflow.splitlines()
start = lines.index("  COUNT_RESULTS: |") + 1
end = start
while end < len(lines) and (not lines[end].strip() or lines[end].startswith("    ")):
    end += 1
counter = textwrap.dedent("\n".join(lines[start:end]))
prefix = "sql/_05_plcsql/_01_testspec/_05_bug_fix/"
expected_missing = {prefix + "cbrd-27556/cases/" + name + ".sql" for name in [
    "33_static_sql_group_by_having_alias", "33_static_sql_group_by_having_alias_error",
]}
source_paths = set(subprocess.check_output(
    ["git", "-C", str(args.testcase_git), "ls-tree", "-r", "--name-only", testcase_sha, "--", prefix],
    text=True,
).splitlines())
assert expected_missing <= source_paths
assert any(p.startswith(prefix + "cases/") and p.endswith(".sql") for p in source_paths)
shards = []
receipts = 0
for shard in sorted((raw / "shards").iterdir()):
    if not shard.is_dir():
        continue
    assert observation["acquisition"]["test_sql"]["shards"][shard.name]["state"] == "retained"
    for receipt in (shard / ".cubrid-ci-receipts").glob("*.json"):
        record = json.loads(receipt.read_text())
        assert Path(record["file_name"]).name == record["file_name"]
        data = (shard / record["file_name"]).read_bytes()
        assert len(data) == record["size_bytes"]
        assert hashlib.sha256(data).hexdigest() == record["sha256"]
        receipts += 1
    assert testcase_sha in (shard / "tc.read").read_text()
    assert engine in (shard / "build.read").read_text()
    counted = dict(item.split("=", 1) for item in subprocess.check_output(
        ["bash", "-c", counter + '\ncount "$1"', "count-replay", str(shard)], text=True,
    ).split())
    xml_cases = list(ET.parse(shard / "linux_sql_64bit.xml").getroot().iter("testcase"))
    xml_names = {case.attrib["name"] for case in xml_cases}
    text_rows = {}
    for number, line in enumerate((shard / "summary_info").read_text().splitlines(), 1):
        match = re.search(r":(nok|ok)\s+[0-9]+ms$", line)
        if match:
            name = line[:match.start()].removeprefix("/home/cubrid-testcases/")
            assert name not in text_rows, "Duplicate text case result"
            text_rows[name] = number
    missing = sorted(text_rows.keys() - xml_names)
    assert not (xml_names - text_rows.keys())
    assert len(xml_names) == len(xml_cases)
    assert int(counted["exec"]) == len(text_rows)
    assert set(missing) == (expected_missing if shard.name == "01" else set())
    shards.append({"shard": shard.name, "workflow_run": int(counted["exec"]),
                   "xml_cases": len(xml_cases), "text_only": missing})
assert len(shards) == 10 and receipts == 50
fixture = Path(__file__).with_name("NestedSummaryProbe.java")
with tempfile.TemporaryDirectory(prefix="sql-count-proof-") as directory:
    scratch = Path(directory)
    archive = subprocess.check_output(
        ["git", "-C", str(args.ctp_git), "archive", ctp_sha, "--", "CTP"],
    )
    with tarfile.open(fileobj=io.BytesIO(archive)) as source:
        source.extractall(scratch, filter="data")
    ctp = scratch / "CTP"
    compiled = subprocess.run(["ant", "-q", "compile"], cwd=ctp, text=True, capture_output=True)
    assert compiled.returncode == 0, compiled.stdout + compiled.stderr
    jars = [str(p) for folder in ["common/lib", "common/lib/mail", "sql/lib", "common/sched/lib", "jdbc/lib"]
            for p in (ctp / folder).glob("*.jar")]
    classpath = ":".join([str(ctp / "build")] + jars)
    subprocess.run(["javac", "-cp", classpath, "-d", str(scratch), str(fixture)],
                   check=True, text=True, capture_output=True)
    probes = []
    for layout in ["mixed", "separate"]:
        for outcome in ["pass", "fail"]:
            probe = subprocess.run(
                ["java", "-cp", str(scratch) + ":" + classpath, "NestedSummaryProbe", layout, outcome],
                text=True, capture_output=True,
            )
            assert not probe.stderr, probe.stderr
            data = json.loads(probe.stdout.splitlines()[0])
            expected_count = 1 if layout == "mixed" else 3
            expected_failures = 2 if layout == "separate" and outcome == "fail" else 0
            assert data["aggregate"] == data["junit_cases"] == expected_count
            assert data["aggregate_failures"] == data["junit_failures"] == expected_failures
            assert probe.returncode == (1 if layout == "mixed" else 0)
            probes.append(data)
print(json.dumps({
    "run_id": 40837919358, "attempt": 1, "engine": engine,
    "workflow_sha": workflow_sha, "testcase_sha": testcase_sha, "ctp_sha": ctp_sha,
    "observation_id": observation["observation_id"], "receipt_files_checked": receipts,
    "collector_sql_state": "collection_failed", "suite_success_certified": False,
    "shards": shards, "actual_ctp_probes": probes,
    "conclusion": "Nested categories are omitted from aggregate/JUnit traversal; no repair applied.",
}, indent=2))
