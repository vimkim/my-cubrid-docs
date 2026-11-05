#!/usr/bin/env python3
"""Check OosGrowthBound.tla for each growth-side reclaim design and print the comparison table.

For every design and crash setting it reports:
  safety   TypeOK and FreeHoldsNothing
  strong   NoGrowthPastStaleEmpty (the current specification)
  max_R    the worst file size in pages: the smallest Bound for which SizeWithinBound holds,
           or "cap" when the file reaches MaxPages (NoOverflow fails), i.e. unbounded growth
  max_cost the most pages one grow examines: the smallest passing CostBound

Usage: python3 run.py --out NEW_DIR [--jar tla2tools.jar] [--java java] [--jobs N]
       [--max-pages 7,9] [--cap 2] [--live 2]

Exit status: 0 when every result matches EXPECTED, 1 on a mismatch, 2 on a TLC or tool error.
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
SPEC = os.path.join(HERE, "OosGrowthBound.tla")
DEFAULT_JAR = os.path.expanduser("~/.cache/tlaplus/tla2tools-1.7.4.jar")

# name -> (Design, N, FallbackFull)
DESIGNS = {
    "none": ("none", 1, True),
    "full_skip": ("full_skip", 1, True),
    "full_defer": ("full_defer", 1, True),
    "full_retry": ("full_retry", 1, True),
    "budget_N1": ("budget", 1, True),
    "budget_N2": ("budget", 2, True),
    "cand_fullboot": ("cand", 1, True),
    "cand_budgetboot_N2": ("cand", 2, False),
}

# Expected verdicts (strong holds, growth bounded) per (design, crashes, writes during a grow).
# These lock the results recorded in growth-bound-design.md; a key that is absent is not checked.
def _expected():
    table = {}
    for crashes in (False, True):
        for writes in (False, True):
            table[("none", crashes, writes)] = (False, False)
            table[("full_skip", crashes, writes)] = (False, not writes)
            table[("full_defer", crashes, writes)] = (True, not writes)
            table[("full_retry", crashes, writes)] = (True, not writes)
            table[("budget_N1", crashes, writes)] = (False, False)
            table[("budget_N2", crashes, writes)] = (False, False)
            table[("cand_fullboot", crashes, writes)] = (True, not (crashes and writes))
            table[("cand_budgetboot_N2", crashes, writes)] = (not crashes, not crashes)
    return table


EXPECTED = _expected()

# Larger caps separate "bounded above the small cap" from "unbounded": (design, crashes, writes,
# MaxPages) -> expected NoOverflow verdict.
CAP_CHECKS = {
    ("cand_fullboot", False, True, 8): "PASS",
    ("cand_fullboot", False, True, 10): "PASS",
    ("budget_N2", False, False, 8): "FAIL",
    ("budget_N2", False, False, 10): "FAIL",
    ("full_defer", False, True, 8): "FAIL",
    ("full_skip", False, True, 8): "FAIL",
}
# NoFutileWork (no page examined by a grow during which no page was empty), quiet grows.
EXPECTED_FUTILE = {
    (name, crashes): "PASS" if name == "none" or (name.startswith("cand") and not crashes) else "FAIL"
    for name in ("none", "full_skip", "full_defer", "full_retry", "budget_N1", "budget_N2",
                 "cand_fullboot", "cand_budgetboot_N2")
    for crashes in (False, True)
}


def write_cfg(path, design, n, fallback, crashes, writes, max_pages, cap, live, bound, cost, invariants):
    tla_bool = lambda b: "TRUE" if b else "FALSE"
    with open(path, "w") as f:
        f.write("CONSTANTS\n")
        f.write(f'  Design = "{design}"\n  MaxPages = {max_pages}\n  Cap = {cap}\n  L = {live}\n')
        f.write(f"  N = {n}\n  FallbackFull = {tla_bool(fallback)}\n  Crashes = {tla_bool(crashes)}\n")
        f.write(f"  WritesDuringGrow = {tla_bool(writes)}\n")
        f.write(f"  Bound = {bound}\n  CostBound = {cost}\n")
        f.write("SPECIFICATION Spec\n")
        f.write("INVARIANTS " + " ".join(invariants) + "\n")


def verdict_of(out, cfg_name):
    violated = re.search(r"Invariant (\w+) is violated", out)
    if violated:
        return "FAIL", violated.group(1), out
    if "Model checking completed. No error has been found." in out:
        states = re.search(r"(\d+) distinct states found", out)
        return "PASS", states.group(1) if states else "?", out
    return None


def tlc(args, workdir, cfg_name):
    log = os.path.join(workdir, cfg_name + ".log")
    if args.resume and os.path.exists(log):
        with open(log) as f:
            cached = verdict_of(f.read(), cfg_name)
        if cached:
            return cached
    # Concurrent TLC processes extract the standard modules into java.io.tmpdir; give each its own.
    tmpdir = os.path.join(workdir, "tmp-" + cfg_name)
    os.makedirs(tmpdir, exist_ok=True)
    cmd = [args.java, "-XX:+UseParallelGC", f"-Djava.io.tmpdir={tmpdir}", "-cp", args.jar,
           "tlc2.TLC", "-workers", "4",
           "-deadlock", "-metadir", os.path.join(workdir, "states-" + cfg_name),
           "-config", cfg_name + ".cfg", "OosGrowthBound.tla"]
    proc = subprocess.run(cmd, cwd=workdir, capture_output=True, text=True)
    out = proc.stdout + proc.stderr
    with open(os.path.join(workdir, cfg_name + ".log"), "w") as f:
        f.write(out)
    shutil.rmtree(os.path.join(workdir, "states-" + cfg_name), ignore_errors=True)
    shutil.rmtree(tmpdir, ignore_errors=True)
    verdict = verdict_of(out, cfg_name)
    if verdict:
        return verdict
    raise RuntimeError(f"TLC error for {cfg_name}:\n{out[-3000:]}")


def check_one(args, workdir, name, crashes, writes, max_pages):
    design, n, fallback = DESIGNS[name]
    tag = f"{name}-{'crash' if crashes else 'nocrash'}-{'writes' if writes else 'quiet'}-P{max_pages}"
    common = dict(design=design, n=n, fallback=fallback, crashes=crashes, writes=writes,
                  max_pages=max_pages,
                  cap=args.cap, live=args.live)

    def run(suffix, bound, cost, invariants):
        cfg = f"{tag}-{suffix}"
        write_cfg(os.path.join(workdir, cfg + ".cfg"), bound=bound, cost=cost,
                  invariants=invariants, **common)
        return tlc(args, workdir, cfg)

    big = 10 * max_pages

    def least_passing(prefix, lo, hi, make):
        # Smallest value in [lo, hi] whose run passes; hi is known to pass.
        while lo < hi:
            mid = (lo + hi) // 2
            verdict, _, _ = run(f"{prefix}{mid}", *make(mid))
            if verdict == "PASS":
                hi = mid
            else:
                lo = mid + 1
        return hi

    # Safety and cost come from the smallest cap, and cost only from quiet grows: the larger cap
    # only confirms that a bounded size is stable.
    smallest = max_pages == args.caps[0]
    safety, safety_info = "-", "-"
    if smallest:
        safety, safety_info, _ = run("safety", max_pages, big, ["TypeOK", "FreeHoldsNothing"])
    strong, strong_info, _ = run("strong", max_pages, big, ["NoGrowthPastStaleEmpty"])
    overflow, _, _ = run("overflow", max_pages, big, ["NoOverflow"])
    if overflow == "FAIL":
        max_r = "cap"
    else:
        max_r = least_passing("size", 0, max_pages, lambda b: (b, big, ["SizeWithinBound"]))
    max_cost, futile = "-", "-"
    if smallest and not writes:
        futile, _, _ = run("futile", max_pages, big, ["NoFutileWork"])
        cost_hi = 2 * max_pages + 1
        verdict, _, _ = run(f"cost{cost_hi}", max_pages, cost_hi, ["CostWithinBound"])
        if verdict != "PASS":
            raise RuntimeError(f"{tag}: a grow examined more than {cost_hi} pages")
        max_cost = least_passing("cost", 0, cost_hi, lambda c: (max_pages, c, ["CostWithinBound"]))
    return {
        "design": name, "crashes": crashes, "writes": writes, "max_pages": max_pages,
        "safety": safety, "safety_states": safety_info,
        "strong": strong, "max_R": max_r, "max_cost": max_cost, "futile": futile,
    }


def check_cap(args, workdir, name, crashes, writes, max_pages):
    design, n, fallback = DESIGNS[name]
    cfg = f"cap-{name}-{'crash' if crashes else 'nocrash'}-{'writes' if writes else 'quiet'}-P{max_pages}"
    write_cfg(os.path.join(workdir, cfg + ".cfg"), design=design, n=n, fallback=fallback,
              crashes=crashes, writes=writes, max_pages=max_pages, cap=args.cap, live=args.live,
              bound=max_pages, cost=10 * max_pages, invariants=["NoOverflow"])
    verdict, info, _ = tlc(args, workdir, cfg)
    return (name, crashes, writes, max_pages), verdict, info


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out", required=True)
    parser.add_argument("--jar", default=DEFAULT_JAR)
    parser.add_argument("--java", default="java")
    parser.add_argument("--jobs", type=int, default=16)
    parser.add_argument("--max-pages", default="5,6")
    parser.add_argument("--cap", type=int, default=2)
    parser.add_argument("--live", type=int, default=2)
    parser.add_argument("--resume", action="store_true",
                        help="reuse verdicts in existing .log files of --out (same spec only)")
    args = parser.parse_args()
    args.caps = sorted(int(x) for x in args.max_pages.split(","))

    if os.path.exists(args.out) and not args.resume:
        print(f"--out {args.out} exists; choose a new directory", file=sys.stderr)
        return 2
    os.makedirs(args.out, exist_ok=True)
    copied = os.path.join(args.out, "OosGrowthBound.tla")
    if args.resume and os.path.exists(copied):
        with open(copied, "rb") as a, open(SPEC, "rb") as b:
            if a.read() != b.read():
                print("--resume: the spec in --out differs from OosGrowthBound.tla", file=sys.stderr)
                return 2
    shutil.copy(SPEC, args.out)
    with open(SPEC, "rb") as f:
        spec_sha = hashlib.sha256(f.read()).hexdigest()

    caps = args.caps
    jobs = [(name, crashes, writes, mp) for name in DESIGNS for crashes in (False, True)
            for writes in (False, True) for mp in caps]
    results = []
    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=args.jobs) as pool:
            futures = [pool.submit(check_one, args, args.out, *job) for job in jobs]
            cap_futures = [pool.submit(check_cap, args, args.out, *key) for key in CAP_CHECKS]
            for fut in futures:
                results.append(fut.result())
            cap_results = [fut.result() for fut in cap_futures]
    except RuntimeError as exc:
        print(exc, file=sys.stderr)
        return 2

    mismatches = []
    print(f"spec sha256 {spec_sha}  Cap={args.cap} L={args.live} MaxPages={caps}")
    print("| design | crashes | writes in grow | MaxPages | safety | strong | max R | max cost/grow "
          "| no futile work |")
    print("| --- | --- | --- | --- | --- | --- | --- | --- | --- |")
    for r in results:
        print(f"| {r['design']} | {r['crashes']} | {r['writes']} | {r['max_pages']} | {r['safety']} | {r['strong']} "
              f"| {r['max_R']} | {r['max_cost']} | {r['futile']} |")
        got = (r["strong"] == "PASS", r["max_R"] != "cap")
        want = EXPECTED.get((r["design"], r["crashes"], r["writes"]), got)
        futile_ok = r["futile"] == "-" or r["futile"] == EXPECTED_FUTILE[(r["design"], r["crashes"])]
        if r["safety"] not in ("PASS", "-") or got != want or not futile_ok:
            mismatches.append(r)

    # A bounded design must report the same worst size under both caps.
    for name in DESIGNS:
        for crashes in (False, True):
            for writes in (False, True):
                sizes = {r["max_R"] for r in results
                         if r["design"] == name and r["crashes"] == crashes and r["writes"] == writes}
                if "cap" not in sizes and len(sizes) > 1:
                    mismatches.append({"design": name, "crashes": crashes, "writes": writes,
                                       "unstable_max_R": sorted(sizes)})

    print()
    print("| larger cap: design | crashes | writes in grow | MaxPages | NoOverflow | distinct states |")
    print("| --- | --- | --- | --- | --- | --- |")
    for key, verdict, info in cap_results:
        name, crashes, writes, mp = key
        print(f"| {name} | {crashes} | {writes} | {mp} | {verdict} | {info if verdict == 'PASS' else '-'} |")
        if verdict != CAP_CHECKS[key]:
            mismatches.append({"cap_check": list(key), "verdict": verdict})

    with open(os.path.join(args.out, "results.json"), "w") as f:
        json.dump({"spec_sha256": spec_sha, "cap": args.cap, "live": args.live, "max_pages": caps,
                   "results": results, "mismatches": mismatches}, f, indent=2)
    if mismatches:
        print("MISMATCH:", json.dumps(mismatches, indent=2))
        return 1
    print("all results match EXPECTED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
