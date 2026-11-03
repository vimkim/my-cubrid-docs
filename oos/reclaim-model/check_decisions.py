#!/usr/bin/env python3
"""Check each OOS reclaim design decision with TLC and compare the results with EXPECTED.

Decisions 1-4 have one model each; decision 5 checks the chosen combination in OosReclaimDesign.

Usage: python3 check_decisions.py --out NEW_DIR [--jar tla2tools.jar] [--java java] [--jobs N]

Each check runs one model with one setting and one invariant. A "reason" check runs the state
invariant that explains why a passing option passes. Exit status: 0 when every result matches,
1 on a mismatch, 2 on a TLC or tool error.
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
DEFAULT_JAR = os.path.expanduser("~/.cache/tlaplus/tla2tools-1.7.4.jar")

P, F = "PASS", "FAIL"

# Decision 1 and 4: OosSpaceProtect. Columns follow SPACE_PROPS.
SPACE_PROPS = ["UndoFindsEmptySlot", "UndoFindsRoom", "OtherRecordIntact", "ReclaimedWhenDone",
               "NoLatchWaitCycle"]
SPACE = {
    "none": [F, F, F, P, P],
    "latch": [P, P, P, P, F],
    "slot_only": [P, F, P, P, P],
    "slot_and_bytes": [P, P, P, P, P],
    "page_exclude": [P, P, P, P, P],
    "no_undo": [P, P, P, P, P],
}
# UndoFindsPage without the LSA gate. With the gate every option passes.
NO_GATE_PAGE = {"none": F, "latch": P, "slot_only": F, "slot_and_bytes": F, "page_exclude": P,
                "no_undo": P}
SPACE_REASONS = {
    "none": [("UndoSlotsStayEmpty", F), ("UndoBytesStayFree", F)],
    "latch": [("LatchCoversUndo", P), ("UndoSlotsStayEmpty", P), ("UndoBytesStayFree", P)],
    "slot_only": [("MarkCoversUndo", P), ("UndoSlotsStayEmpty", P), ("UndoBytesStayFree", F)],
    "slot_and_bytes": [("MarkCoversUndo", P), ("ReserveCoversUndo", P), ("UndoSlotsStayEmpty", P),
                       ("UndoBytesStayFree", P)],
    "page_exclude": [("ExcludeCoversUndo", P), ("UndoSlotsStayEmpty", P), ("UndoBytesStayFree", P),
                     ("UndoPagesStayAllocated", P)],
    "no_undo": [("NothingToUndo", P), ("UndoSlotsStayEmpty", P), ("UndoBytesStayFree", P),
                ("UndoPagesStayAllocated", P)],
}

# Decision 2: OosDropDecision.
DROP_PROPS = ["RowChainIntact", "DroppedChainReclaimed"]
DROP = {
    "undo_image": [F, P],
    "commit_filter": [F, P],
    "commit_hook": [F, P],
    "postpone": [P, P],
}
DROP_REASONS = {
    "commit_hook": [("NotifyDurableOnlyWithCommit", F), ("NotifyOnlyForSurvivingUpdate", P)],
    "postpone": [("NotifyDurableOnlyWithCommit", P), ("NotifyOnlyForSurvivingUpdate", P)],
}

# Decision 3: OosReclaimRetry. Key (Order, LinkStamp, OnError).
RETRY_PROPS = ["OtherRecordIntact", "ReclaimedWhenDone"]


def retry_expected(order, link, on_error):
    other = F if (order == "tail_first" and not link) else P
    reclaimed = P if (order == "tail_first" and on_error == "rerun") else F
    return [other, reclaimed]


# Decision 5: OosReclaimDesign, the chosen combination and one variant per undone decision.
DESIGN_CONFIGS = {
    "design": {"Horizon": True, "Notify": "postpone", "LinkStamp": True},
    "no_horizon": {"Horizon": False, "Notify": "postpone", "LinkStamp": True},
    "undo_image": {"Horizon": True, "Notify": "undo_image", "LinkStamp": True},
    "no_link_stamp": {"Horizon": True, "Notify": "postpone", "LinkStamp": False},
}
DESIGN_PROPS = ["NeededChainsIntact", "ReuseKeepsChain", "ReaderSeesIntactChain", "OtherRecordIntact",
                "NoOrphanWhenQuiescent"]
DESIGN_REASONS = ["ReclaimOnlyUnreachable", "NotifyOnlyForCommittedDrop", "RemainingIsPrefix",
                  "ListStillNamesChain"]
DESIGN_EXPECTED = {
    "design": ([P, P, P, P, P], [P, P, P, P]),
    "no_horizon": ([P, P, F, P, P], [F, P, P, P]),
    "undo_image": ([F, F, F, P, P], [F, P, P, P]),
    "no_link_stamp": ([P, P, P, F, P], [P, P, P, F]),
}
# Each witness must fail in the design: TLC then shows a path that reaches the situation.
DESIGN_WITNESSES = ["WitnessBothChainsReclaimed", "WitnessReusedChainReclaimed", "WitnessVacuumWaitsForSnapshot",
                    "WitnessRerunStopsAtReusedSlot", "WitnessDeallocDuringReclaim"]

RETRY_REASONS = {
    ("head_first", True, "rerun"): [("RemainingIsPrefix", F)],
    ("tail_first", False, "rerun"): [("RemainingIsPrefix", P), ("ListStillNamesChain", F)],
    ("tail_first", True, "rerun"): [("RemainingIsPrefix", P), ("ListStillNamesChain", P)],
}


def tla_value(v):
    if isinstance(v, bool):
        return "TRUE" if v else "FALSE"
    return '"{}"'.format(v)


def checks():
    out = []
    for protect, row in SPACE.items():
        for prop, exp in zip(SPACE_PROPS, row):
            out.append(("1", "OosSpaceProtect", {"Protect": protect, "Gate": "lsa"}, prop, exp, "property"))
        out.append(("4", "OosSpaceProtect", {"Protect": protect, "Gate": "lsa"}, "UndoFindsPage", P, "property"))
        out.append(("4", "OosSpaceProtect", {"Protect": protect, "Gate": "none"}, "UndoFindsPage",
                    NO_GATE_PAGE[protect], "property"))
        for reason, exp in SPACE_REASONS[protect]:
            out.append(("1", "OosSpaceProtect", {"Protect": protect, "Gate": "lsa"}, reason, exp, "reason"))
    out.append(("4", "OosSpaceProtect", {"Protect": "no_undo", "Gate": "none"}, "NothingToUndo", P, "reason"))
    for notify, row in DROP.items():
        for prop, exp in zip(DROP_PROPS, row):
            out.append(("2", "OosDropDecision", {"Notify": notify}, prop, exp, "property"))
        for reason, exp in DROP_REASONS.get(notify, []):
            out.append(("2", "OosDropDecision", {"Notify": notify}, reason, exp, "reason"))
    for order in ["head_first", "tail_first"]:
        for link in [False, True]:
            for on_error in ["discard", "rerun"]:
                settings = {"Order": order, "LinkStamp": link, "OnError": on_error}
                for prop, exp in zip(RETRY_PROPS, retry_expected(order, link, on_error)):
                    out.append(("3", "OosReclaimRetry", settings, prop, exp, "property"))
                for reason, exp in RETRY_REASONS.get((order, link, on_error), []):
                    out.append(("3", "OosReclaimRetry", settings, reason, exp, "reason"))
    for config, settings in DESIGN_CONFIGS.items():
        props, reasons = DESIGN_EXPECTED[config]
        for prop, exp in zip(DESIGN_PROPS, props):
            out.append(("5", "OosReclaimDesign", settings, prop, exp, "property"))
        for reason, exp in zip(DESIGN_REASONS, reasons):
            out.append(("5", "OosReclaimDesign", settings, reason, exp, "reason"))
    for witness in DESIGN_WITNESSES:
        out.append(("5", "OosReclaimDesign", DESIGN_CONFIGS["design"], witness, F, "witness"))
    return out


def run(check, out, jar, java):
    decision, module, settings, inv, exp, kind = check
    name = "{}-{}-{}-{}".format(decision, module, "-".join(str(v) for v in settings.values()), inv)
    work = os.path.join(out, name)
    os.makedirs(work)
    shutil.copy(os.path.join(HERE, module + ".tla"), work)
    cfg = os.path.join(work, "MC.cfg")
    with open(cfg, "w") as f:
        f.write("CONSTANTS\n")
        for k, v in settings.items():
            f.write("    {} = {}\n".format(k, tla_value(v)))
        f.write("SPECIFICATION Spec\nINVARIANT {}\nVIEW view\n".format(inv))
    # TLC unpacks its standard modules into java.io.tmpdir; parallel runs must not share it.
    cmd = [java, "-XX:+UseParallelGC", "-Djava.io.tmpdir=" + work, "-cp", jar, "tlc2.TLC",
           "-workers", "1", "-cleanup", "-metadir", os.path.join(work, "states"), "-config", cfg, module]
    if settings.get("Protect") == "latch":
        # D1 reaches the latch cycle that NoLatchWaitCycle reports; let the other invariants run past it.
        cmd.insert(cmd.index("-cleanup"), "-deadlock")
    proc = subprocess.run(cmd, cwd=work, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                          universal_newlines=True)
    text = proc.stdout
    with open(os.path.join(work, "tlc.out"), "w") as f:
        f.write(text)
    if "Model checking completed. No error has been found." in text:
        result = P
    elif re.search(r"Invariant \w+ is violated", text):
        result = F
    elif "Deadlock reached" in text:
        result = "DEADLOCK"
    else:
        result = "ERROR"
    distinct = re.search(r"(\d+) distinct states found", text)
    trace = re.findall(r'^/\\ last = "(.*)"$', text, re.M) if result != P else []
    return {"decision": decision, "module": module, "settings": settings, "invariant": inv,
            "kind": kind, "expected": exp, "result": result, "name": name,
            "distinct": int(distinct.group(1)) if distinct else None, "trace": trace}


def label(settings):
    return ", ".join("{}={}".format(k, tla_value(v).strip('"')) for k, v in settings.items())


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

    shas = {}
    for module in ["OosSpaceProtect", "OosDropDecision", "OosReclaimRetry", "OosReclaimDesign"]:
        with open(os.path.join(HERE, module + ".tla"), "rb") as f:
            shas[module] = hashlib.sha256(f.read()).hexdigest()
    with open(args.jar, "rb") as f:
        shas["tla2tools"] = hashlib.sha256(f.read()).hexdigest()

    todo = checks()
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.jobs) as pool:
        results = list(pool.map(lambda c: run(c, args.out, args.jar, args.java), todo))

    lines = ["# OOS reclaim decision checks", ""]
    lines += ["- {} sha256 `{}`".format(k, v) for k, v in shas.items()]
    lines += ["", "| Decision | Setting | Invariant | Kind | Result | Expected | Distinct states |",
              "| --- | --- | --- | --- | --- | --- | --- |"]
    for r in results:
        lines.append("| {} | {} | {} | {} | {} | {} | {} |".format(
            r["decision"], label(r["settings"]), r["invariant"], r["kind"], r["result"], r["expected"],
            r["distinct"]))
    lines += ["", "## Counterexamples", ""]
    for r in results:
        if r["result"] != P:
            verb = "reaches" if r["kind"] == "witness" else "breaks"
            lines.append("### Decision {}: {} {} {}".format(r["decision"], label(r["settings"]), verb, r["invariant"]))
            lines.append("")
            lines += ["{}. {}".format(i, s) for i, s in enumerate(r["trace"][1:], 1)]
            lines.append("")
    summary = "\n".join(lines) + "\n"
    with open(os.path.join(args.out, "summary.md"), "w") as f:
        f.write(summary)
    with open(os.path.join(args.out, "results.json"), "w") as f:
        json.dump({"sha256": shas, "results": results}, f, indent=1)
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
