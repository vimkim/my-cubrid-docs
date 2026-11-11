#!/usr/bin/env python3
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import time


JAR_SHA256 = "936a262061c914694dfd669a543be24573c45d5aa0ff20a8b96b23d01e050e88"
INVARIANTS = ["TypeOK", "NoWritesUnderSelect", "NoWritesToAncestorTables",
              "DecisionsMatchRules", "FramesFollowExecution"]
DEFAULTS = dict(GuardMode="all", MetadataMode="complete", LifetimeMode="execute",
                Classifier="semantic", MaxDepth=3)
CASES = [
    ("complete", {}, None),
    ("no-select-check", dict(GuardMode="no-select-check"), "NoWritesUnderSelect"),
    ("no-overlap-check", dict(GuardMode="no-overlap-check"), "NoWritesToAncestorTables"),
    ("top-only", dict(GuardMode="top"), "NoWritesToAncestorTables"),
    ("cache-empty", dict(MetadataMode="cache-empty"), "NoWritesToAncestorTables"),
    ("xasl-type-only", dict(Classifier="xasl"), "NoWritesUnderSelect"),
    ("prepare-only", dict(LifetimeMode="prepare-only"), "NoWritesToAncestorTables"),
    ("error-frame-leak", dict(LifetimeMode="leak-on-error"), "FramesFollowExecution"),
    ("deny-all-writes", dict(GuardMode="deny-all-writes"), "DecisionsMatchRules"),
]


def main():
    parser = argparse.ArgumentParser(description="Check the proposed SP DML guard and its broken variants.")
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    started = time.monotonic()
    deadline = started + 300
    output = args.out.resolve() if args.out else Path(tempfile.mkdtemp(prefix="sp-dml-tlc-"))
    if args.out:
        output.mkdir(parents=True, exist_ok=False)
    jar = Path(os.environ.get("TLA2TOOLS", Path.home() / ".cache/tlaplus/tla2tools-1.7.4.jar"))
    if not jar.is_file():
        parser.error("Set TLA2TOOLS to the TLC 1.7.4 jar. See README.md for installation.")
    if hashlib.sha256(jar.read_bytes()).hexdigest() != JAR_SHA256:
        parser.error("TLA2TOOLS does not match the pinned TLC 1.7.4 SHA-256.")
    java = os.environ.get("JAVA", "java")
    source = Path(__file__).resolve().parent
    shutil.copyfile(source / "SpDmlGuard.tla", output / "SpDmlGuard.tla")
    results = []
    for name, changes, expected in CASES:
        settings = DEFAULTS | changes
        config = ["SPECIFICATION Spec", "CONSTANTS"]
        config.extend(f"  {key} = {json.dumps(value)}" for key, value in settings.items())
        config.append("INVARIANTS " + " ".join(INVARIANTS))
        if expected:
            config[-1] = "INVARIANTS TypeOK " + expected
        (output / f"{name}.cfg").write_text("\n".join(config) + "\n")
        command = [java, "-XX:+UseParallelGC", "-Xmx1g", "-cp", str(jar), "tlc2.TLC",
                   "-workers", "1", "-seed", "1", "-fp", "0",
                   "-metadir", str(output / f"states-{name}"),
                   "-config", f"{name}.cfg", "SpDmlGuard.tla"]
        case_started = time.monotonic()
        remaining = deadline - case_started
        if remaining <= 0:
            raise SystemExit("FAIL: the 300-second suite budget expired")
        try:
            with (output / f"{name}.log").open("w") as log:
                run = subprocess.run(command, cwd=output, stdout=log, stderr=subprocess.STDOUT,
                                     timeout=remaining, check=False)
        except subprocess.TimeoutExpired:
            raise SystemExit(f"FAIL: {name} exceeded the remaining 300-second suite budget")
        text = (output / f"{name}.log").read_text()
        violation = re.search(r"Invariant (\w+) is violated", text)
        found = violation.group(1) if violation else None
        passed = (run.returncode == 0 and "Model checking completed. No error has been found." in text
                  if expected is None else run.returncode == 12 and found == expected)
        counts = re.search(r"([\d,]+) states generated, ([\d,]+) distinct states found", text)
        row = dict(case=name, result="PASS" if passed else "FAIL", expected_violation=expected,
                   found_violation=found, seconds=round(time.monotonic() - case_started, 3),
                   exit_code=run.returncode, settings=settings,
                   generated=int(counts[1].replace(",", "")) if counts else None,
                   distinct=int(counts[2].replace(",", "")) if counts else None)
        results.append(row)
        detail = found or ("all invariants hold" if passed else f"no expected result, exit {run.returncode}")
        print(f"{row['result']} {name}: {detail} ({row['seconds']}s)", flush=True)
    summary = dict(jar_sha256=JAR_SHA256,
                   model_sha256=hashlib.sha256((output / "SpDmlGuard.tla").read_bytes()).hexdigest(),
                   checker_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                   seconds=round(time.monotonic() - started, 3),
                   budget_seconds=300, cases=results)
    (output / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(f"Evidence: {output}")
    if not all(row["result"] == "PASS" for row in results):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
