#!/usr/bin/env python3
"""Run every TLC configuration in cfg/ and print one line per run.

Usage: python3 run.py [--only SUBSTRING] [--out DIR] [--workers N] [--jobs N]

Each cfg names its spec and the expected result in its first lines
(\\* spec: ..., \\* expect: PASS|FAIL).  TLC output goes to a scratch
directory outside this repository (printed at the start).  For a FAIL the
counterexample is printed as its steps, taken from the spec's `last`
variable.  Exit status: 0 when every run matches its expectation, 1 when
one does not, 2 when TLC could not run.
"""
import argparse
import concurrent.futures
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
JAR = os.environ.get("TLA2TOOLS_JAR",
                     os.path.expanduser("~/.cache/tlaplus/tla2tools-1.7.4.jar"))
JAVA = os.environ.get("JAVA", "java")


def read_header(path):
    meta = {}
    with open(path, encoding="utf-8") as f:
        for line in f:
            m = re.match(r"\\\*\s*(\w+):\s*(.*)", line)
            if not m:
                break
            meta[m.group(1)] = m.group(2).strip()
    return meta


def run_one(cfg, out_root, workers):
    name = os.path.splitext(os.path.basename(cfg))[0]
    meta = read_header(cfg)
    spec = meta["spec"]
    work = os.path.join(out_root, name)
    os.makedirs(work, exist_ok=True)
    shutil.copy(os.path.join(HERE, spec + ".tla"), work)
    shutil.copy(cfg, work)
    cmd = [JAVA, "-XX:+UseParallelGC", "-XX:ParallelGCThreads=2", "-Djava.io.tmpdir=" + work, "-cp", JAR,
           "tlc2.TLC", "-config", os.path.basename(cfg), "-workers", str(workers),
           "-metadir", os.path.join(work, "states"), "-cleanup", spec + ".tla"]
    start = time.time()
    with open(os.path.join(work, name + ".out"), "w", encoding="utf-8") as log:
        subprocess.run(cmd, cwd=work, stdout=log, stderr=subprocess.STDOUT, check=False)
    seconds = time.time() - start
    with open(os.path.join(work, name + ".out"), encoding="utf-8") as f:
        text = f.read()
    found = re.findall(r"([\d,]+) distinct states found", text)
    states = found[-1].replace(",", "") if found else "?"
    if "No error has been found" in text:
        result, why = "PASS", ""
    elif re.search(r"Invariant \w+ is violated", text):
        result, why = "FAIL", re.search(r"Invariant (\w+) is violated", text).group(1)
    elif "Deadlock reached" in text:
        result, why = "FAIL", "TLC deadlock"
    else:
        result, why = "ERROR", "see " + os.path.join(work, name + ".out")
    steps = []
    if result == "FAIL":
        steps = re.findall(r'^/\\ last = "(.*)"$', text, re.M)
    return dict(name=name, expect=meta.get("expect", "?"), result=result, why=why,
                states=states, seconds=seconds, steps=steps, about=meta.get("about", ""))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default="", help="run only cfgs whose name contains this")
    ap.add_argument("--out", default=None, help="scratch directory for TLC output")
    ap.add_argument("--workers", type=int, default=8, help="TLC workers per run")
    ap.add_argument("--jobs", type=int, default=max(1, (os.cpu_count() or 8) // 8),
                    help="runs at the same time")
    ap.add_argument("--quiet", action="store_true", help="do not print counterexample steps")
    args = ap.parse_args()
    if not os.path.isfile(JAR):
        print("tla2tools jar not found: %s (set TLA2TOOLS_JAR)" % JAR)
        return 2
    out_root = args.out or tempfile.mkdtemp(prefix="sidecar-recovery-model-")
    os.makedirs(out_root, exist_ok=True)
    cfgs = sorted(os.path.join(HERE, "cfg", c) for c in os.listdir(os.path.join(HERE, "cfg"))
                  if c.endswith(".cfg") and args.only in c)
    print("TLC output: %s" % out_root)
    start = time.time()
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.jobs) as pool:
        results = list(pool.map(lambda c: run_one(c, out_root, args.workers), cfgs))
    status = 0
    for r in results:
        ok = r["result"] == r["expect"]
        if r["result"] == "ERROR":
            status = 2
        elif not ok and status == 0:
            status = 1
        print("%-5s %10s states %6.1fs  %-52s expect %s%s%s" % (
            r["result"], r["states"], r["seconds"], r["name"], r["expect"],
            "" if ok else "  <-- UNEXPECTED",
            ("  (" + r["why"] + ")") if r["why"] else ""))
    if not args.quiet:
        for r in results:
            if r["steps"]:
                print("\n%s: %s" % (r["name"], r["about"]))
                for i, s in enumerate(r["steps"][1:], 1):
                    print("  %2d. %s" % (i, s))
    print("\n%d runs in %.0fs wall time" % (len(results), time.time() - start))
    return status


if __name__ == "__main__":
    sys.exit(main())
