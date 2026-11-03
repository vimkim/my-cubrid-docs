#!/usr/bin/env python3
"""Check OosReclaim.tla for every setting and compare the results with the U1 expectations.

Usage: python3 run.py --out NEW_DIR [--jar tla2tools.jar] [--java java] [--jobs N]

Exit status: 0 when every result matches EXPECTED, 1 on a mismatch, 2 on a TLC or tool error.
"""

import argparse
import concurrent.futures
import hashlib
import itertools
import json
import os
import re
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SPEC = os.path.join(HERE, "OosReclaim.tla")
DEFAULT_JAR = os.path.expanduser("~/.cache/tlaplus/tla2tools-1.7.4.jar")

SETTINGS = {
    "Op": ["del", "upd"],
    "ReuseAt": ["immediate", "final"],
    "DecideFrom": ["ended", "committed"],
    "HeadIdentity": ["stamp", "none"],
}
CODE = {"ReuseAt": "immediate", "DecideFrom": "ended", "HeadIdentity": "stamp"}
SAFE = {"ReuseAt": "final", "DecideFrom": "committed", "HeadIdentity": "stamp"}
PROPERTIES = [
    "ForwardUndoFindsEmptySlot",
    "ChunkUndoFindsEmptySlot",
    "RowChainIntact",
    "OtherRecordIntact",
    "ReclaimedWhenDone",
]

# The defects that the model must reproduce, each with the one setting that isolates it.
GATE = [
    ("CBRD-27858", "del", CODE, "ForwardUndoFindsEmptySlot"),
    ("CBRD-27781", "del", CODE, "ChunkUndoFindsEmptySlot"),
    ("CBRD-27237", "upd", CODE, "RowChainIntact"),
    ("CBRD-26950", "upd", {"ReuseAt": "final", "DecideFrom": "committed", "HeadIdentity": "none"},
     "OtherRecordIntact"),
]


def expected(op, reuse, decide, ident, prop):
    if prop == "ForwardUndoFindsEmptySlot":
        return "FAIL" if op == "del" and reuse == "immediate" else "PASS"
    if prop == "ChunkUndoFindsEmptySlot":
        return "FAIL" if reuse == "immediate" else "PASS"
    if prop == "RowChainIntact":
        return "FAIL" if op == "upd" and decide == "ended" else "PASS"
    if prop == "OtherRecordIntact":
        if reuse == "immediate":
            return "FAIL"
        return "FAIL" if op == "upd" and ident == "none" else "PASS"
    if prop == "ReclaimedWhenDone":
        return "FAIL" if op == "upd" else "PASS"
    raise ValueError(prop)


def run_case(case, out, jar, java):
    name = "{Op}-{ReuseAt}-{DecideFrom}-{HeadIdentity}-{prop}".format(**case)
    work = os.path.join(out, name)
    os.makedirs(work)
    shutil.copy(SPEC, work)
    cfg = os.path.join(work, "MC.cfg")
    with open(cfg, "w") as f:
        f.write("CONSTANTS\n")
        for key in SETTINGS:
            f.write('    {} = "{}"\n'.format(key, case[key]))
        f.write("SPECIFICATION Spec\nINVARIANT {}\nVIEW view\n".format(case["prop"]))
    # TLC unpacks its standard modules into java.io.tmpdir; parallel runs must not share it.
    cmd = [java, "-XX:+UseParallelGC", "-Djava.io.tmpdir=" + work, "-cp", jar, "tlc2.TLC",
           "-workers", "1", "-cleanup",
           "-metadir", os.path.join(work, "states"), "-config", cfg, "OosReclaim"]
    proc = subprocess.run(cmd, cwd=work, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                          universal_newlines=True)
    text = proc.stdout
    with open(os.path.join(work, "tlc.out"), "w") as f:
        f.write(text)
    if "Model checking completed. No error has been found." in text:
        result = "PASS"
    elif re.search(r"Invariant \w+ is violated", text):
        result = "FAIL"
    elif "Deadlock reached" in text:
        result = "DEADLOCK"
    else:
        result = "ERROR"
    distinct = re.search(r"(\d+) distinct states found", text)
    trace = re.findall(r'^/\\ last = "(.*)"$', text, re.M) if result == "FAIL" else []
    return dict(case, name=name, result=result, trace=trace,
                distinct=int(distinct.group(1)) if distinct else None,
                expected=expected(case["Op"], case["ReuseAt"], case["DecideFrom"],
                                  case["HeadIdentity"], case["prop"]))


def find(results, op, settings, prop):
    for r in results:
        if r["Op"] == op and r["prop"] == prop and all(r[k] == v for k, v in settings.items()):
            return r
    raise KeyError((op, settings, prop))


def depends_on(results, op, prop, start=CODE):
    """Settings whose single change from start changes this property's result."""
    base = find(results, op, start, prop)["result"]
    flips = []
    for key, value in start.items():
        other = [v for v in SETTINGS[key] if v != value][0]
        changed = find(results, op, dict(start, **{key: other}), prop)["result"]
        if changed != base:
            flips.append("{}={}".format(key, other))
    return base, flips


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--jar", default=os.environ.get("TLA2TOOLS_JAR", DEFAULT_JAR))
    ap.add_argument("--java", default=os.environ.get("JAVA", "java"))
    ap.add_argument("--jobs", type=int, default=os.cpu_count() or 4)
    args = ap.parse_args()

    if os.path.exists(args.out) and os.listdir(args.out):
        sys.exit("--out must be a new or empty directory: " + args.out)
    os.makedirs(args.out, exist_ok=True)
    with open(args.jar, "rb") as f:
        jar_sha = hashlib.sha256(f.read()).hexdigest()
    with open(SPEC, "rb") as f:
        spec_sha = hashlib.sha256(f.read()).hexdigest()

    cases = [dict(zip(list(SETTINGS) + ["prop"], values))
             for values in itertools.product(*SETTINGS.values(), PROPERTIES)]
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.jobs) as pool:
        results = list(pool.map(lambda c: run_case(c, args.out, args.jar, args.java), cases))

    errors = [r for r in results if r["result"] not in ("PASS", "FAIL")]
    mismatches = [r for r in results if r["result"] in ("PASS", "FAIL") and r["result"] != r["expected"]]

    lines = ["# OosReclaim U1 results", "",
             "spec sha256 `{}`, tla2tools sha256 `{}`, {} runs".format(spec_sha, jar_sha, len(results)), "",
             "## Known defects at the code's settings", "",
             "| Defect | Workload | Settings | Property | Result | Steps |", "| --- | --- | --- | --- | --- | --- |"]
    for ticket, op, settings, prop in GATE:
        r = find(results, op, settings, prop)
        shown = ", ".join("{}={}".format(k, v) for k, v in settings.items())
        lines.append("| {} | {} | {} | {} | {} | {} |".format(ticket, op, shown, prop, r["result"], len(r["trace"])))
    lines += ["", "## Which setting each result depends on", "",
              "| Workload | Property | At the code's settings | Changed by one setting |", "| --- | --- | --- | --- |"]
    for op in SETTINGS["Op"]:
        for prop in PROPERTIES:
            base, flips = depends_on(results, op, prop)
            lines.append("| {} | {} | {} | {} |".format(op, prop, base, ", ".join(flips) or "none"))
    lines += ["", "## Which assumption, put back alone, breaks each property", "",
              "Start: " + ", ".join("{}={}".format(k, v) for k, v in SAFE.items()), "",
              "| Workload | Property | At the start | Broken by one setting |", "| --- | --- | --- | --- |"]
    for op in SETTINGS["Op"]:
        for prop in PROPERTIES:
            base, flips = depends_on(results, op, prop, SAFE)
            lines.append("| {} | {} | {} | {} |".format(op, prop, base, ", ".join(flips) or "none"))
    lines += ["", "## Counterexamples for the known defects", ""]
    for ticket, op, settings, prop in GATE:
        r = find(results, op, settings, prop)
        lines.append("### {} ({})".format(ticket, r["name"]))
        lines.append("")
        lines += ["{}. {}".format(i, step) for i, step in enumerate(r["trace"][1:], 1)]
        lines.append("")
    lines += ["## All runs", "", "| Run | Result | Expected | Distinct states |", "| --- | --- | --- | --- |"]
    lines += ["| {name} | {result} | {expected} | {distinct} |".format(**r) for r in results]

    summary = "\n".join(lines) + "\n"
    with open(os.path.join(args.out, "summary.md"), "w") as f:
        f.write(summary)
    with open(os.path.join(args.out, "results.json"), "w") as f:
        json.dump({"spec_sha256": spec_sha, "jar_sha256": jar_sha, "results": results}, f, indent=1)
    print(summary)

    if errors:
        print("TLC OR TOOL ERROR: " + ", ".join(r["name"] + "=" + r["result"] for r in errors))
        return 2
    if mismatches:
        print("MISMATCH: " + ", ".join(r["name"] + " got " + r["result"] for r in mismatches))
        return 1
    print("ALL RESULTS MATCH THE U1 EXPECTATIONS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
