#!/usr/bin/env python3
"""Check OosRestartGrowth.tla for each restart-durability design and print the result table.

Per (design, crashes, writes during a grow, K, MaxPages) it reports:
  safety    TypeOK and FreeHoldsNothing
  strict    NoGrowthPastStaleEmpty: the strict rule at every grow
  outside   StrictOutsideWindow: the strict rule at grows that start with the set known complete
  complete  SetCompleteWhenKnown
  max_R     smallest passing Bound, or "cap" when NoOverflow fails
  max_cost  smallest passing CostBound (pages examined by one grow)
  Both bounds come from one loop: a violated bound is raised by one and the run repeated,
  so every run but the last stops at its first violation.
  futile    NoFutileWork (quiet grows only)
  states    distinct states of the full (all-pass) run
  secs      wall time of all TLC runs of the row

Usage: python3 -I -B run.py --out NEW_DIR [--jobs 3] [--workers 4] [--max-pages 4]
Exit 0 when every verdict matches EXPECTED, 1 on a mismatch, 2 on a TLC error.
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
import time

HERE = os.path.dirname(os.path.abspath(__file__))
SPEC = os.path.join(HERE, "OosRestartGrowth.tla")
JAR = os.path.expanduser("~/.cache/tlaplus/tla2tools-1.7.4.jar")

DESIGNS = ["cand_fullboot", "hdr_count", "redofn_only", "redo_bg_slack",
           "ckpt_redo", "ckpt_early", "hdr_list", "hdr_late", "hdr_lazy"]
SLACK = 1
FULL_K = "full"            # K = MaxPages: the set never overflows
OVERFLOW_DESIGNS = ["cand_fullboot", "ckpt_redo", "hdr_list"]


# (design, crashes, writes, K) -> (strict, outside, complete, bounded); K is FULL_K or 1.
def _expected():
    t = {}
    for d in DESIGNS:
        for w in (False, True):
            # Without crashes every design is the run-time candidate set.
            t[(d, False, w, FULL_K)] = (True, True, True, True)
    # A lazy list lets writes refill a listed page before the grower looks and empty it after.
    t[("hdr_lazy", False, True, FULL_K)] = (True, True, True, False)
    for w in (False, True):
        t[("cand_fullboot", True, w, FULL_K)] = (True, True, True, not w)
        t[("hdr_count", True, w, FULL_K)] = (True, True, True, not w)
        t[("redofn_only", True, w, FULL_K)] = (False, False, False, False)
        t[("redo_bg_slack", True, w, FULL_K)] = (False, True, True, False)
        t[("ckpt_redo", True, w, FULL_K)] = (True, True, True, True)
        t[("ckpt_early", True, w, FULL_K)] = (False, False, False, False)
        t[("hdr_list", True, w, FULL_K)] = (True, True, True, True)
        t[("hdr_late", True, w, FULL_K)] = (False, False, False, False)
        t[("hdr_lazy", True, w, FULL_K)] = (True, True, True, not w)
    return t


EXPECTED = _expected()
CONTROLS = ["ckpt_early", "hdr_late"]   # wrong-order controls: they already fail without writes
ROWS = [(d, c, w, FULL_K) for d in DESIGNS for c in (False, True) for w in (False, True)
        if not (d in CONTROLS and w)]
ROWS += [(d, c, w, 1) for d in OVERFLOW_DESIGNS for c in (False, True) for w in (False, True)]


def b(x):
    return "TRUE" if x else "FALSE"


def final_states(out):
    # The final summary line, not a progress line: progress lines also say "distinct states found".
    s = re.search(r"([\d,]+) distinct states found, 0 states left on queue", out)
    return s.group(1).replace(",", "") if s else "?"


def run_tlc(args, tag, design, crashes, writes, k, mp, bound, cost, invs):
    cfg = os.path.join(args.out, tag + ".cfg")
    with open(cfg, "w") as f:
        f.write("CONSTANTS\n")
        f.write(f'  Design = "{design}"\n  MaxPages = {mp}\n  Cap = {args.cap}\n  L = {args.live}\n')
        f.write(f"  K = {k}\n  Slack = {SLACK}\n  Crashes = {b(crashes)}\n  WritesDuringGrow = {b(writes)}\n")
        f.write(f"  Bound = {bound}\n  CostBound = {cost}\n")
        f.write("SPECIFICATION Spec\nINVARIANTS " + " ".join(invs) + "\n")
    log = os.path.join(args.out, tag + ".log")
    tmp = os.path.join(args.out, "tmp-" + tag)
    meta = os.path.join(args.out, "states-" + tag)
    os.makedirs(tmp, exist_ok=True)
    cmd = ["java", "-XX:+UseParallelGC", f"-Djava.io.tmpdir={tmp}", "-cp", JAR, "tlc2.TLC",
           "-workers", str(args.workers), "-deadlock", "-metadir", meta,
           "-config", cfg, os.path.join(args.out, "OosRestartGrowth.tla")]
    t0 = time.time()
    try:
        p = subprocess.run(cmd, cwd=args.out, capture_output=True, text=True, timeout=args.timeout)
        out = p.stdout + p.stderr
    except subprocess.TimeoutExpired as e:
        out = e.stdout.decode() if isinstance(e.stdout, bytes) else (e.stdout or "")
        out += "\nRUNNER: TIMEOUT\n"
    dt = time.time() - t0
    with open(log, "w") as f:
        f.write(out)
    shutil.rmtree(meta, ignore_errors=True)
    shutil.rmtree(tmp, ignore_errors=True)
    m = re.search(r"Invariant (\w+) is violated", out)
    if m:
        return "FAIL", None, dt, m.group(1)
    if "RUNNER: TIMEOUT" in out:
        return "TO", None, dt, None
    if "Model checking completed. No error has been found." in out:
        return "PASS", final_states(out), dt, None
    raise RuntimeError(f"TLC error {tag}:\n{out[-2000:]}")


def check_row(args, design, crashes, writes, kk, mp):
    k = mp if kk == FULL_K else kk
    tag = f"{design}-{'crash' if crashes else 'nocrash'}-{'writes' if writes else 'quiet'}-K{kk}-P{mp}"
    names = {"TypeOK": "safety", "FreeHoldsNothing": "safety", "NoGrowthPastStaleEmpty": "strict",
             "StrictOutsideWindow": "outside", "SetCompleteWhenKnown": "complete",
             "NoOverflow": "overflow", "NoFutileWork": "futile"}
    invs = [i for i in names if not (writes and i == "NoFutileWork")]
    verdict = {v: "PASS" for v in names.values()}
    if writes:
        verdict["futile"] = "-"
    # One loop finds every verdict and both bounds; only the last run explores the whole space.
    # A violated plain invariant is recorded and dropped; a violated bound is raised by one.
    bound, cost, size_on = args.start_bound, args.start_cost, True
    states, total, n = None, 0.0, 0
    while True:
        run_invs = invs + (["SizeWithinBound"] if size_on else []) + ["CostWithinBound"]
        v, s, dt, bad = run_tlc(args, f"{tag}-r{n}", design, crashes, writes, k, mp, bound, cost, run_invs)
        n += 1
        total += dt
        if v == "PASS":
            states = s
            break
        if v == "TO":
            for i in invs:
                if verdict[names[i]] == "PASS":
                    verdict[names[i]] = "TO"
            bound, cost = f">={bound}?(TO)", f">={cost}?(TO)"
            break
        if bad == "SizeWithinBound":
            bound += 1
        elif bad == "CostWithinBound":
            cost += 1
            if cost > 6 * mp:
                raise RuntimeError(f"{tag}: cost exceeds {6 * mp}")
        else:
            verdict[names[bad]] = "FAIL"
            invs.remove(bad)
            if bad == "NoOverflow":
                size_on = False
    if verdict["safety"] == "FAIL":
        raise RuntimeError(f"{tag}: safety violated")
    max_r = "cap" if verdict["overflow"] == "FAIL" else bound
    return dict(design=design, crashes=crashes, writes=writes, k=kk, max_pages=mp,
                safety=verdict["safety"], strict=verdict["strict"], outside=verdict["outside"],
                complete=verdict["complete"], max_R=max_r, max_cost=cost,
                futile=verdict["futile"], states=states or "-", secs=round(total, 1), runs=n)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", help="new directory for this run's configs, logs and results.json")
    ap.add_argument("--retable", metavar="DIR", help="only reprint the table of an earlier --out DIR")
    ap.add_argument("--jobs", type=int, default=3)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--max-pages", default="4")
    ap.add_argument("--cap", type=int, default=2)
    ap.add_argument("--live", type=int, default=2)
    ap.add_argument("--only", default="", help="comma list of designs")
    ap.add_argument("--k", default="", help="comma list of K values to run (full,1)")
    ap.add_argument("--crashes", default="", help="only rows with crashes on (1) or off (0)")
    ap.add_argument("--writes", default="", help="only rows with writes during a grow on (1) or off (0)")
    ap.add_argument("--timeout", type=int, default=600, help="seconds per TLC run")
    ap.add_argument("--start-bound", type=int, default=1,
                    help="first Bound to try; use only a value a smaller MaxPages already exceeded")
    ap.add_argument("--start-cost", type=int, default=0,
                    help="first CostBound to try; use only a value a smaller MaxPages already exceeded")
    args = ap.parse_args()
    if args.retable:
        return retable(os.path.abspath(args.retable))
    if not args.out:
        ap.error("--out is required")
    args.out = os.path.abspath(args.out)
    if os.path.exists(args.out):
        print("--out exists", file=sys.stderr)
        return 2
    os.makedirs(args.out)
    shutil.copy(SPEC, args.out)
    sha = hashlib.sha256(open(SPEC, "rb").read()).hexdigest()
    caps = [int(x) for x in args.max_pages.split(",")]
    only = set(filter(None, args.only.split(",")))
    ks = {FULL_K if x == "full" else int(x) for x in filter(None, args.k.split(","))}
    rows = [r for r in ROWS if (not only or r[0] in only) and (not ks or r[3] in ks)
            and (args.crashes == "" or r[1] == (args.crashes == "1"))
            and (args.writes == "" or r[2] == (args.writes == "1"))]
    jobs = [r + (mp,) for r in rows for mp in caps]
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.jobs) as pool:
        try:
            results = list(pool.map(lambda j: check_row(args, *j), jobs))
        except RuntimeError as e:
            print(e, file=sys.stderr)
            return 2
    return report(args.out, sha, results, f"Cap={args.cap} L={args.live} Slack={SLACK} MaxPages={caps}")


def retable(out):
    """Rebuild the table of an earlier --out directory, reading each row's state count from its
    last run log (runners before the final_states fix recorded a progress-line count)."""
    data = json.load(open(os.path.join(out, "results.json")))
    for r in data["results"]:
        tag = (f"{r['design']}-{'crash' if r['crashes'] else 'nocrash'}-"
               f"{'writes' if r['writes'] else 'quiet'}-K{r['k']}-P{r['max_pages']}")
        logs = [f for f in os.listdir(out) if re.fullmatch(re.escape(tag) + r"-r\d+\.log", f)]
        last = max(logs, key=lambda f: int(re.search(r"-r(\d+)\.log$", f).group(1)))
        text = open(os.path.join(out, last)).read()
        r["states"] = final_states(text) if "No error has been found" in text else "-"
    return report(out, data["spec_sha256"], data["results"], "(retable)")


def report(out, sha, results, consts):
    print(f"spec sha256 {sha}  {consts}")
    print("| design | crashes | writes in grow | K | MaxPages | safety | strict | strict outside window "
          "| set complete | max R | max cost/grow | no futile work | states | TLC s |")
    print("| --- " * 14 + "|")
    bad = []
    for r in results:
        print(f"| {r['design']} | {r['crashes']} | {r['writes']} | {r['k']} | {r['max_pages']} | {r['safety']} "
              f"| {r['strict']} | {r['outside']} | {r['complete']} | {r['max_R']} | {r['max_cost']} "
              f"| {r['futile']} | {r['states']} | {r['secs']} |")
        got = (r["strict"] == "PASS", r["outside"] == "PASS", r["complete"] == "PASS", r["max_R"] != "cap")
        want = EXPECTED.get((r["design"], r["crashes"], r["writes"], r["k"]), got)
        if r["safety"] == "FAIL" or (r["safety"] == "PASS" and got != want):
            bad.append({**r, "want": want})
    with open(os.path.join(out, "results.json"), "w") as f:
        json.dump({"spec_sha256": sha, "results": results, "mismatches": bad}, f, indent=2)
    if bad:
        print("MISMATCH:", json.dumps(bad, indent=2))
        return 1
    print("all results match EXPECTED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
