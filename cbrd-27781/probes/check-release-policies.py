#!/usr/bin/env python3
"""Compare current and hypothetical chunk-release policies in the bounded model."""

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--rev", required=True)
    parser.add_argument("--checker", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    toolchain = json.loads(Path(__file__).with_name("release-policy-toolchain.json").read_text())
    checker_root = args.checker.resolve().parent.parent
    for relative, expected in toolchain["checker_file_sha256"].items():
        dependency = args.checker.resolve() if relative == "scripts/check.py" else checker_root / relative
        if not dependency.is_file() or hashlib.sha256(dependency.read_bytes()).hexdigest() != expected:
            parser.error("Checker dependency differs from the reviewed toolchain: " + str(dependency))
    revision = subprocess.check_output(
        ["git", "-C", str(args.repo), "rev-parse", "--verify", "--end-of-options", args.rev + "^{commit}"],
        text=True,
    ).strip()
    args.out.mkdir(parents=True, exist_ok=False)
    results = []
    for name, overrides in [
        ("current", []),
        ("hypothetical_chunk_exclusion_until_sysop_end", ["--set", "oos_chunk_release=after_sysop_end"]),
    ]:
        command = [
            sys.executable,
            str(args.checker.resolve()),
            "--repo", str(args.repo.resolve()),
            "--rev", revision,
            "--out", str((args.out / name).resolve()),
            *overrides,
        ]
        log = args.out / (name + ".log")
        with log.open("w") as stream:
            completed = subprocess.run(command, stdout=stream, stderr=subprocess.STDOUT, check=False)
        properties = [
            line.strip() for line in log.read_text().splitlines()
            if any(line.lstrip().startswith(prop) for prop in [
                "HomeSlotUndoFindsEmptySlot ",
                "ForwardSlotUndoFindsEmptySlot ",
                "OosChunkUndoFindsEmptySlot ",
            ])
        ]
        results.append({
            "case": name,
            "revision": revision,
            "hypothetical": bool(overrides),
            "command": command,
            "exit_code": completed.returncode,
            "property_results": properties,
            "log": str(log.resolve()),
        })
        (args.out / "results.json").write_text(json.dumps(results, indent=2) + "\n")
        print(json.dumps(results[-1], indent=2), flush=True)
        if completed.returncode not in (0, 1, 3):
            return completed.returncode
    print("These model results do not implement a CUBRID fix or verify a latch graph, guard registry, or byte reservation.")
    if any(result["exit_code"] == 1 for result in results):
        return 1
    if any(result["exit_code"] == 3 for result in results):
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
