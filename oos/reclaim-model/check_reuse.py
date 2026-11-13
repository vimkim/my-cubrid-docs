#!/usr/bin/env python3
"""Check OosChainReuse.tla (CBRD-27230 chain reuse) with TLC and compare the results with EXPECTED.

The design setting must pass every safety invariant and the liveness property. Each negative
control undoes one decision and must fail the property it protects. Each witness must fail in the
design setting, which shows that the situation it names is reachable.

Usage: python3 check_reuse.py --out NEW_DIR [--jar tla2tools.jar] [--java java] [--jobs N]
       [--workers N] [--only NAME_SUBSTRING]

Exit status: 0 when every result matches, 1 on a mismatch, 2 on a TLC or tool error.
"""

import argparse
import concurrent.futures
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
MODULE = "OosChainReuse"
DEFAULT_JAR = os.path.expanduser("~/.cache/tlaplus/tla2tools-1.7.4.jar")
P, F = "PASS", "FAIL"

# Safety runs use the larger bounds; liveness runs keep the trace variable in the state (no VIEW), so
# they use one statement per transaction and three slots.
BOUNDS = {
    "safety": {"Txns": '{"T1", "T2"}', "Readers": '{"R1"}', "Slots": "{1, 2, 3, 4}", "MaxStmts": "2",
               "MaxStamp": "6", "MaxNotes": "8"},
    "liveness": {"Txns": '{"T1", "T2"}', "Readers": '{"R1"}', "Slots": "{1, 2, 3}", "MaxStmts": "1",
                 "MaxStamp": "5", "MaxNotes": "4"},
}
DESIGN = {"Reuse": "copy", "Source": "latest", "Drop": "set_diff", "Publish": "postpone", "Cancel": True, "Horizon": True,
          "Identity": True, "Rerun": True, "UndoFrees": "created"}

SAFETY = ["NeededChainsLive", "NoWrongDelete", "NotifyOnlyForCommittedDrop"]
LIVENESS = ["GarbageReclaimed"]
PROPS = SAFETY + LIVENESS

# name -> (setting overrides, expected result per PROPS; None skips the check)
CONFIGS = {
    "design": ({}, [P, P, P, P]),
    "publish_before_commit": ({"Publish": "before_commit"}, [F, P, F, P]),
    "no_horizon": ({"Horizon": False}, [F, P, P, P]),
    # A postpone that survives its rollback lets vacuum free live chains, and the freed slots feed
    # further allocations: the safety bounds give over 25 GB of TLC state. This control runs at the
    # liveness bounds and checks no liveness.
    "no_cancel": ({"Cancel": False}, [F, P, F, None]),
    "undo_image_drop": ({"Drop": "undo_image"}, [F, P, F, P]),
    "no_identity": ({"Identity": False}, [F, F, P, P]),
    "no_rerun": ({"Rerun": False}, [P, P, P, F]),
    # A restamped head is not restored by a rollback, so the restamped chain also leaks.
    "restamp": ({"Reuse": "restamp"}, [F, P, P, F]),
    # A stub copied from an older version resurrects a chain that an earlier statement dropped.
    "snapshot_source": ({"Source": "snapshot"}, [F, P, F, P]),
    "undo_frees_reused": ({"UndoFrees": "new_record"}, [F, P, P, P]),
}
WITNESSES = ["WitnessSharedChainReclaimed", "WitnessSnapshotHoldsReclaim", "WitnessDuplicateNotify",
             "WitnessCrashInPostponeThenReclaim", "WitnessPartialRollbackThenCommit"]


def tla_value(v):
    if isinstance(v, bool):
        return "TRUE" if v else "FALSE"
    return '"{}"'.format(v)


def checks():
    out = []
    for name, (over, row) in CONFIGS.items():
        settings = dict(DESIGN, **over)
        bounds = "liveness" if None in row else "safety"
        for prop, exp in zip(PROPS, row):
            if exp is None:
                continue
            kind = "liveness" if prop in LIVENESS else "safety"
            out.append((name, settings, prop, exp, kind, "liveness" if kind == "liveness" else bounds))
    for w in WITNESSES:
        out.append(("design", dict(DESIGN), w, F, "witness", "safety"))
    return out


def run(check, out, jar, java, workers):
    config, settings, prop, exp, kind, bounds = check
    name = "{}-{}".format(config, prop)
    work = os.path.join(out, name)
    os.makedirs(work)
    shutil.copy(os.path.join(HERE, MODULE + ".tla"), work)
    cfg = os.path.join(work, "MC.cfg")
    with open(cfg, "w") as f:
        f.write("CONSTANTS\n")
        for k, v in BOUNDS[bounds].items():
            f.write("    {} = {}\n".format(k, v))
        for k, v in settings.items():
            f.write("    {} = {}\n".format(k, tla_value(v)))
        if kind == "liveness":
            # TLC cannot check liveness under VIEW; the trace variable last stays in the state.
            f.write("SPECIFICATION LiveSpec\nPROPERTY {}\n".format(prop))
        else:
            f.write("SPECIFICATION Spec\nINVARIANT {}\nVIEW view\n".format(prop))
    # TLC unpacks its standard modules into java.io.tmpdir; parallel runs must not share it.
    cmd = [java, "-XX:+UseParallelGC", "-Xmx10g", "-Djava.io.tmpdir=" + work, "-cp", jar, "tlc2.TLC",
           "-workers", str(workers), "-deadlock", "-cleanup", "-metadir", os.path.join(work, "states"),
           "-config", cfg, MODULE]
    proc = subprocess.run(cmd, cwd=work, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                          universal_newlines=True)
    text = proc.stdout
    with open(os.path.join(work, "tlc.out"), "w") as f:
        f.write(text)
    if "Model checking completed. No error has been found." in text:
        result = P
    elif re.search(r"Invariant \w+ is violated", text) or re.search(r"Temporal properties were violated", text):
        result = F
    else:
        result = "ERROR"
    distinct = re.search(r"^\d+ states generated, (\d+) distinct states found", text, re.M)
    trace = re.findall(r'^/\\ last = "(.*)"$', text, re.M) if result != P else []
    return {"config": config, "settings": settings, "property": prop, "kind": kind, "bounds": bounds,
            "expected": exp,
            "result": result, "name": name, "distinct": int(distinct.group(1)) if distinct else None,
            "trace": trace}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--jar", default=os.environ.get("TLA2TOOLS_JAR", DEFAULT_JAR))
    ap.add_argument("--java", default=os.environ.get("JAVA", "java"))
    ap.add_argument("--jobs", type=int, default=4)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--only", default=None)
    args = ap.parse_args()
    if os.path.exists(args.out) and os.listdir(args.out):
        sys.exit("--out must be a new or empty directory: " + args.out)
    os.makedirs(args.out, exist_ok=True)

    shas = {}
    with open(os.path.join(HERE, MODULE + ".tla"), "rb") as f:
        shas[MODULE] = hashlib.sha256(f.read()).hexdigest()
    with open(args.jar, "rb") as f:
        shas["tla2tools"] = hashlib.sha256(f.read()).hexdigest()

    todo = [c for c in checks() if args.only is None or args.only in "{}-{}".format(c[0], c[2])]
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.jobs) as pool:
        results = list(pool.map(lambda c: run(c, args.out, args.jar, args.java, args.workers), todo))

    lines = ["# OOS chain reuse checks (CBRD-27230)", ""]
    lines += ["- {} sha256 `{}`".format(k, v) for k, v in shas.items()]
    for k, b in BOUNDS.items():
        lines.append("- {} bounds: ".format(k) + ", ".join("{}={}".format(x, v) for x, v in b.items()))
    lines.append("")
    lines += ["| Setting | Property | Kind | Bounds | Result | Expected | Distinct states |",
              "| --- | --- | --- | --- | --- | --- | --- |"]
    for r in results:
        lines.append("| {} | {} | {} | {} | {} | {} | {} |".format(
            r["config"], r["property"], r["kind"], r["bounds"], r["result"], r["expected"], r["distinct"]))
    lines += ["", "## Counterexamples", ""]
    for r in results:
        if r["result"] != P:
            verb = "reaches" if r["kind"] == "witness" else "breaks"
            lines.append("### {} {} {}".format(r["config"], verb, r["property"]))
            lines.append("")
            lines += ["{}. {}".format(i, s) for i, s in enumerate(r["trace"][1:], 1)]
            lines.append("")
    summary = "\n".join(lines) + "\n"
    with open(os.path.join(args.out, "summary.md"), "w") as f:
        f.write(summary)
    with open(os.path.join(args.out, "results.json"), "w") as f:
        json.dump({"sha256": shas, "bounds": BOUNDS, "results": results}, f, indent=1)
    print(summary)

    errors = [r for r in results if r["result"] not in (P, F)]
    mismatches = [r for r in results if r["result"] in (P, F) and r["result"] != r["expected"]]
    if errors:
        print("TLC OR TOOL ERROR: " + ", ".join(r["name"] + "=" + r["result"] for r in errors))
        return 2
    if mismatches:
        print("MISMATCH: " + ", ".join(r["name"] + " got " + r["result"] for r in mismatches))
        return 1
    print("ALL {} RESULTS MATCH THE EXPECTATIONS".format(len(results)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
