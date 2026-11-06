#!/usr/bin/env python3
"""Check OffPathSweep.tla for each off-path design and print the result tables.

Measurements come from TLC registers (Measure, GapMeasure in the spec): every worker prints each
new maximum it sees, and this script takes the maximum over all prints.  That is exact because TLC
evaluates an invariant on every distinct state and an action property on every generated step.

Per (design, crashes, writes during a grow), MaxPages = 5:
  main     TypeOK, Safe, DebtExact; max R, max gap at a reservation (0 = strict rule)
  cost     max pages the allocation path fixes in one grow
  bound    when max R reached MaxPages: NoOverflow at MaxPages 5, 6, 7.  The first MaxPages
           where it passes gives the bound (behaviour below the cap does not depend on
           MaxPages); no pass up to 7 is reported as "cap".
Then: crash-budget runs, the Recheck=FALSE bug run, strict-rule counterexamples, fairness runs.

Usage: python3 -I -B run.py --out NEW_DIR [--tokens 12]
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
import threading
import time

HERE = os.path.dirname(os.path.abspath(__file__))
SPEC = os.path.join(HERE, "OffPathSweep.tla")
JAR = os.path.expanduser("~/.cache/tlaplus/tla2tools-1.7.4.jar")
P0 = 5

# name -> (Worker, Fallback, S, Boot)
DESIGNS = {
    "cand_base": (False, True, 0, "sync"),   # cand_fullboot, no fast path
    "off_S0": (True, True, 0, "sync"),       # cand_fullboot + fast path / drain
    "off_S1": (True, True, 1, "sync"),
    "off_S2": (True, True, 2, "sync"),
    "pure_bg": (True, False, 0, "bg"),       # off path only, no fallback
    "off_S1_bg": (True, True, 1, "bg"),
    "off_S1_bgslack": (True, True, 1, "bg_slack"),
}
SETTINGS = [(c, w) for c in (False, True) for w in (False, True)]
BIG = {("off_S2", True, True), ("off_S1", True, True), ("off_S1_bg", True, True),
       ("off_S1_bgslack", True, True), ("pure_bg", True, True), ("off_S2", True, False),
       ("off_S1_bg", True, False), ("off_S1_bgslack", True, False)}


def expected_bounded(d, crashes):
    if d == "pure_bg":
        return False
    if d in ("off_S1_bg", "off_S1_bgslack"):
        return not crashes
    return True


def expected_gap(d, crashes):
    s = DESIGNS[d][2]
    if d == "pure_bg" or (crashes and d in ("off_S1_bg", "off_S1_bgslack")):
        return None  # not checked: grows past the cap
    return s


class Tokens:
    """At most `n` TLC workers run at once across all jobs."""

    def __init__(self, n):
        self.n, self.cv = n, threading.Condition()

    def take(self, k):
        with self.cv:
            self.cv.wait_for(lambda: self.n >= k)
            self.n -= k

    def give(self, k):
        with self.cv:
            self.n += k
            self.cv.notify_all()


def tla(b):
    return "TRUE" if b else "FALSE"


def write_cfg(path, d, crashes, writes, pages, recheck=True, max_crash=0, track_gap=False,
              track_cost=False, invariants=(), props=(), spec="Spec", order="any"):
    worker, fallback, s, boot = DESIGNS[d]
    with open(path, "w") as f:
        f.write("CONSTANTS\n")
        for k, v in [("MaxPages", pages), ("Cap", 2), ("L", 2), ("S", s), ("Fallback", tla(fallback)),
                     ("Boot", f'"{boot}"'), ("Worker", tla(worker)), ("Recheck", tla(recheck)),
                     ("Order", f'"{order}"'), ("Crashes", tla(crashes)), ("MaxCrash", max_crash),
                     ("WritesDuringGrow", tla(writes)), ("TrackGap", tla(track_gap)),
                     ("TrackCost", tla(track_cost))]:
            f.write(f"  {k} = {v}\n")
        f.write(f"SPECIFICATION {spec}\n")
        if invariants:
            f.write("INVARIANTS " + " ".join(invariants) + "\n")
        if props:
            f.write("PROPERTIES " + " ".join(props) + "\n")


def parse(out):
    hi = {}
    for i, v in re.findall(r'<<"HI", (\d+), (-?\d+)>>', out):
        hi[int(i)] = max(hi.get(int(i), 0), int(v))
    m = re.search(r"([\d,]+) distinct states found", out[out.rfind("distinct states found") - 40:]) \
        if "distinct states found" in out else None
    states = int(m.group(1).replace(",", "")) if m else None
    m = re.search(r"Invariant (\w+) is violated", out)
    if m:
        return "FAIL", m.group(1), states, hi
    m = re.search(r"Action property (\w+) is violated", out)
    if m:
        return "FAIL", m.group(1), states, hi
    if "Temporal properties were violated" in out:
        return "FAIL", "temporal", states, hi
    if "Model checking completed. No error has been found." in out:
        return "PASS", None, states, hi
    return None, None, states, hi


def trace(out, keep=("pg", "R", "busy", "Q", "unknown", "gpc", "chk", "stale", "wpc", "wp", "ncrash", "live")):
    """Compact counterexample: one line per state with the named variables."""
    lines, cur = [], None
    for ln in out.splitlines():
        m = re.match(r"State (\d+): <(\w+)", ln)
        if m:
            cur = [f"{m.group(1)}:{m.group(2)}"]
            lines.append(cur)
            continue
        m = re.match(r"/\\ (\w+) = (.*)", ln)
        if m and cur is not None and m.group(1) in keep:
            cur.append(f"{m.group(1)}={m.group(2)}")
        if "Back to state" in ln or "Stuttering" in ln:
            lines.append([ln.strip()])
    return [" ".join(x) for x in lines]


def tlc(args, cfg, workers):
    log = os.path.join(args.out, cfg + ".log")
    tmp = os.path.join(args.out, "tmp-" + cfg)
    os.makedirs(tmp, exist_ok=True)
    cmd = ["java", "-XX:+UseParallelGC", f"-Djava.io.tmpdir={tmp}", "-cp", JAR, "tlc2.TLC",
           "-workers", str(workers), "-deadlock", "-metadir", os.path.join(args.out, "states-" + cfg),
           "-config", cfg + ".cfg", "OffPathSweep.tla"]
    args.tokens.take(workers)
    try:
        t0 = time.time()
        proc = subprocess.run(cmd, cwd=args.out, capture_output=True, text=True)
        secs = round(time.time() - t0, 1)
    finally:
        args.tokens.give(workers)
    out = proc.stdout + proc.stderr
    with open(log, "w") as f:
        f.write(out)
    shutil.rmtree(os.path.join(args.out, "states-" + cfg), ignore_errors=True)
    shutil.rmtree(tmp, ignore_errors=True)
    verdict, what, states, hi = parse(out)
    if verdict is None:
        raise RuntimeError(f"TLC error in {cfg}:\n{out[-3000:]}")
    return {"cfg": cfg, "verdict": verdict, "what": what, "states": states, "secs": secs, "hi": hi,
            "trace": trace(out) if verdict == "FAIL" else None}


def run(args, cfg, workers=2, **kw):
    write_cfg(os.path.join(args.out, cfg + ".cfg"), **kw)
    return tlc(args, cfg, workers)


def check(args, d, c, w):
    tag = f"{d}-{'crash' if c else 'nocrash'}-{'writes' if w else 'quiet'}"
    big = (d, c, w) in BIG
    base = dict(d=d, crashes=c, writes=w)
    main = run(args, f"{tag}-main", 6 if big else 2, pages=P0, track_gap=True,
               invariants=["TypeOK", "Safe", "DebtExact", "Measure"], props=["GapMeasure"], **base)
    cost = run(args, f"{tag}-cost", 6 if big else 2, pages=P0, track_cost=True,
               invariants=["Measure"], **base)
    res = {"design": d, "crashes": c, "writes": w, "safety": main["verdict"], "safety_what": main["what"],
           "states": main["states"], "secs": main["secs"] + cost["secs"],
           "gap": main["hi"].get(3, 0), "cost": cost["hi"].get(2, 0), "maxR_P5": main["hi"].get(1, 0)}
    if res["maxR_P5"] < P0:
        res["bound"] = res["maxR_P5"]
        return res
    res["bound"] = "cap"
    for p in (P0, P0 + 1, P0 + 2):
        r = run(args, f"{tag}-overflow-P{p}", 6 if big and p > P0 else 2, pages=p,
                invariants=["NoOverflow", "Measure"], **base)
        res[f"overflow_P{p}"] = r["verdict"]
        res["secs"] += r["secs"]
        if r["verdict"] == "PASS":
            res["bound"] = r["hi"].get(1, 0)
            break
        res["overflow_trace"] = r["trace"]
        if not expected_bounded(d, c):
            break  # one failing size is enough for a design expected to grow
    return res


def crash_budget(args, d, k, w):
    tag = f"budget-{d}-k{k}-{'writes' if w else 'quiet'}"
    out = {"design": d, "max_crash": k, "writes": w, "bound": "cap", "secs": 0}
    for p in (P0, P0 + 1, P0 + 2):
        r = run(args, f"{tag}-P{p}", 3, d=d, crashes=True, writes=w, pages=p, max_crash=k,
                invariants=["NoOverflow", "Measure"])
        out["secs"] += r["secs"]
        if r["verdict"] == "PASS":
            out["bound"] = r["hi"].get(1, 0)
            out["states"] = r["states"]
            break
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", required=True)
    ap.add_argument("--tokens", type=int, default=12)
    ap.add_argument("--live-pages", type=int, default=4)
    args = ap.parse_args()
    args.out = os.path.abspath(args.out)
    if os.path.exists(args.out):
        print("--out exists; choose a new directory", file=sys.stderr)
        return 2
    os.makedirs(args.out)
    shutil.copy(SPEC, args.out)
    sha = hashlib.sha256(open(SPEC, "rb").read()).hexdigest()
    args.tokens = Tokens(args.tokens)

    jobs = sorted(((d, c, w) for d in DESIGNS for c, w in SETTINGS), key=lambda j: j not in BIG)
    LP = args.live_pages
    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
            fs = [pool.submit(check, args, *j) for j in jobs]
            fb = [pool.submit(crash_budget, args, d, k, w) for d in ("off_S1", "off_S1_bgslack", "off_S1_bg")
                  for k in (1, 2) for w in (False, True)]
            extra = {
                "bug_norecheck": pool.submit(run, args, "bug-norecheck", 1, d="off_S1", crashes=False,
                                             writes=True, pages=P0, recheck=False, invariants=["TypeOK", "Safe"]),
                "strict_off_S1": pool.submit(run, args, "strict-off_S1", 1, d="off_S1", crashes=False,
                                             writes=False, pages=P0, track_gap=True, props=["Strict"]),
                "strict_off_S0_crash": pool.submit(run, args, "strict-off_S0-crash", 2, d="off_S0", crashes=True,
                                                   writes=True, pages=P0, track_gap=True, props=["Strict"]),
                "strict_cand_base_crash": pool.submit(run, args, "strict-cand_base-crash", 2, d="cand_base",
                                                      crashes=True, writes=True, pages=P0, track_gap=True,
                                                      props=["Strict"]),
                "overflow_pure_bg": pool.submit(run, args, "overflow-pure_bg-nocrash", 1, d="pure_bg",
                                                crashes=False, writes=False, pages=P0, invariants=["NoOverflow"]),
                "overflow_off_S1_bgslack_crash": pool.submit(run, args, "overflow-off_S1_bgslack-crash", 1,
                                                             d="off_S1_bgslack", crashes=True, writes=False,
                                                             pages=P0, invariants=["NoOverflow"]),
                # Fairness does not remove a reachable state: the same overflow under WeakSpec.
                "fair_overflow_pure_bg": pool.submit(run, args, "fair-overflow-pure_bg", 2, d="pure_bg",
                                                     crashes=False, writes=True, pages=LP, spec="WeakSpec",
                                                     order="fifo", invariants=["NoOverflow"]),
            }
            live = {}
            for d in ("pure_bg", "off_S1"):
                for sp, o in (("Spec", "fifo"), ("WeakSpec", "any"), ("WeakSpec", "fifo")):
                    live[(d, sp, o)] = pool.submit(run, args, f"live-{d}-{sp}-{o}", 2, d=d, crashes=False,
                                                   writes=True, pages=LP, spec=sp, order=o,
                                                   props=["EmptyEventuallyGone"])
            live[("cand_base", "WeakSpec", "fifo")] = pool.submit(
                run, args, "live-cand_base-WeakSpec-fifo", 2, d="cand_base", crashes=False, writes=True,
                pages=LP, spec="WeakSpec", order="fifo", props=["EmptyEventuallyGone"])
            results = [f.result() for f in fs]
            budgets = [f.result() for f in fb]
            extras = {k: f.result() for k, f in extra.items()}
            lives = {k: f.result() for k, f in live.items()}
    except RuntimeError as e:
        print(e, file=sys.stderr)
        return 2

    mism = []
    print(f"spec sha256 {sha}  Cap=2 L=2 MaxPages={P0} (bound runs up to {P0 + 2}), liveness MaxPages={LP}")
    print("| design | crashes | writes in grow | safety | bound (max R) | max gap | max cost/grow | states (main) | secs |")
    print("| --- | --- | --- | --- | --- | --- | --- | --- | --- |")
    for r in sorted(results, key=lambda r: (list(DESIGNS).index(r["design"]), r["crashes"], r["writes"])):
        print(f"| {r['design']} | {r['crashes']} | {r['writes']} | {r['safety']} | {r['bound']} | {r['gap']} "
              f"| {r['cost']} | {r['states']} | {round(r['secs'], 1)} |")
        if r["safety"] != "PASS":
            mism.append(("safety", r))
        if (r["bound"] != "cap") != expected_bounded(r["design"], r["crashes"]):
            mism.append(("bound", r))
        g = expected_gap(r["design"], r["crashes"])
        if g is not None and r["gap"] != g:
            mism.append(("gap", r))
    print()
    print("| crash budget: design | max restarts | writes in grow | bound (max R) | secs |")
    print("| --- | --- | --- | --- | --- |")
    for b in budgets:
        print(f"| {b['design']} | {b['max_crash']} | {b['writes']} | {b['bound']} | {round(b['secs'], 1)} |")
    print()
    for k, e in extras.items():
        print(f"{k}: {e['verdict']} {e['what'] or ''} states={e['states']} secs={e['secs']}")
        if e["trace"]:
            for ln in e["trace"]:
                print("    " + ln)
    want = {"bug_norecheck": "FAIL", "strict_off_S1": "FAIL", "strict_off_S0_crash": "PASS",
            "strict_cand_base_crash": "PASS", "overflow_pure_bg": "FAIL", "overflow_off_S1_bgslack_crash": "FAIL",
            "fair_overflow_pure_bg": "FAIL"}
    for k, v in want.items():
        if extras[k]["verdict"] != v:
            mism.append((k, extras[k]["verdict"]))
    print()
    print("| liveness: design | spec | worker order | EmptyEventuallyGone | states | secs |")
    print("| --- | --- | --- | --- | --- | --- |")
    want_live = {("pure_bg", "Spec", "fifo"): "FAIL", ("pure_bg", "WeakSpec", "any"): "FAIL",
                 ("pure_bg", "WeakSpec", "fifo"): "PASS", ("off_S1", "Spec", "fifo"): "FAIL",
                 ("off_S1", "WeakSpec", "any"): "FAIL", ("off_S1", "WeakSpec", "fifo"): "PASS",
                 ("cand_base", "WeakSpec", "fifo"): "FAIL"}
    for k, l in lives.items():
        print(f"| {k[0]} | {k[1]} | {k[2]} | {l['verdict']} | {l['states']} | {l['secs']} |")
        if want_live[k] != l["verdict"]:
            mism.append(("live", k, l["verdict"]))
    with open(os.path.join(args.out, "results.json"), "w") as f:
        json.dump({"sha": sha, "results": results, "budgets": budgets, "extras": extras,
                   "live": {"/".join(k): v for k, v in lives.items()}, "mismatches": mism}, f, indent=2)
    if mism:
        print("MISMATCH:", json.dumps(mism, indent=2, default=str))
        return 1
    print("all results match EXPECTED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
