#!/usr/bin/env python3
"""Check CandAttack.tla for each relaxation of cand_fullboot and print one table row per setting.

Per row: Safety, Strict (no sector reserved while a stale empty page exists), NoOverflow at
MaxPages (FAIL = "cap", unbounded in the model), worst size (least passing Bound), worst pages
examined per grow (least passing CostBound), distinct states and TLC seconds of the Strict run.

Usage: python3 -I -B run.py --out NEW_DIR [--only NAME[,NAME]] [--jobs 4] [--workers 3]
"""

import argparse
import concurrent.futures
import json
import os
import re
import shutil
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
SPEC = os.path.join(HERE, "CandAttack.tla")
JAR = os.path.expanduser("~/.cache/tlaplus/tla2tools-1.7.4.jar")

# The prior model's restrictions: one rollback that takes at most one new latch per grow, eager
# removal on refill, a deduplicating set that never overflows (K = MaxPages), one grower, no insert
# failure.  The lap is the d52b1889e sweep shape ("call").
BASE = dict(MaxPages=4, Cap=2, L=2, NG=1, NU=1, K=4, Lazy=False, Dedupe=True, EpochFix=True,
            InsertFails=False, FailNote=False, AllocNote=False, LapMode="call", GrowLock=False,
            InPlace=False, RelatchOnce=True, Revisit=True)

# name -> (overrides, extra invariants checked once)
ROWS = {
    "base": ({}, []),
    "span_lap": (dict(LapMode="span"), []),
    "relatch_free": (dict(RelatchOnce=False), []),
    "relatch_free_NU2": (dict(RelatchOnce=False, NU=2), []),
    "lazy": (dict(Lazy=True), []),
    "dup_list": (dict(Dedupe=False, Lazy=True), ["NoSetOverflow"]),
    "K1": (dict(K=1), []),
    "K1_noepoch": (dict(K=1, EpochFix=False), []),
    "K1_span": (dict(K=1, LapMode="span"), []),
    "NG2": (dict(NG=2), []),
    "NG2_growlock": (dict(NG=2, GrowLock=True), []),
    "NG2_inplace": (dict(NG=2, InPlace=True), []),
    "fail_eager": (dict(InsertFails=True), []),
    "fail_lazy": (dict(InsertFails=True, Lazy=True), []),
    "fail_note": (dict(InsertFails=True, FailNote=True), []),
    "fail_allocnote": (dict(InsertFails=True, Lazy=True, AllocNote=True), []),
    "visit_once": (dict(Revisit=False), []),
    "combo": (dict(Lazy=True, K=2, InPlace=True, InsertFails=True, FailNote=True), []),
    "combo_NG2": (dict(Lazy=True, K=2, NG=2, InPlace=True, InsertFails=True, FailNote=True), []),
}


def cfg_text(consts, crashes, writes, bound, cost, invariants):
    b = lambda v: ("TRUE" if v else "FALSE") if isinstance(v, bool) else f'"{v}"' if isinstance(v, str) else str(v)
    lines = ["CONSTANTS", f"  TrackCost = {b('CostWithinBound' in invariants)}"]
    for k, v in consts.items():
        lines.append(f"  {k} = {b(v)}")
    lines += [f"  Crashes = {b(crashes)}", f"  WritesDuringGrow = {b(writes)}",
              f"  Bound = {bound}", f"  CostBound = {cost}",
              "SPECIFICATION Spec", "INVARIANTS " + " ".join(invariants), ""]
    return "\n".join(lines)


def tlc(args, name, consts, crashes, writes, bound, cost, invariants):
    tag = f"{name}-{'C' if crashes else 'c'}{'W' if writes else 'w'}-{'_'.join(invariants)}-B{bound}-K{cost}-P{consts['MaxPages']}"
    work = os.path.join(args.out, tag)
    os.makedirs(work, exist_ok=True)
    cfg = cfg_text(consts, crashes, writes, bound, cost, invariants)
    log = os.path.join(work, "tlc.log")
    if os.path.exists(log) and open(SPEC).read() == open(os.path.join(work, "CandAttack.tla")).read() \
            and open(os.path.join(work, "MC.cfg")).read() == cfg:
        return verdict(open(log).read(), float(open(os.path.join(work, "secs")).read()), work)
    shutil.copy(SPEC, work)
    with open(os.path.join(work, "MC.cfg"), "w") as f:
        f.write(cfg)
    cmd = ["java", "-XX:+UseParallelGC", f"-Djava.io.tmpdir={work}", "-cp", JAR, "tlc2.TLC",
           "-workers", str(args.workers), "-deadlock", "-metadir", os.path.join(work, "states"),
           "-config", "MC.cfg", "CandAttack.tla"]
    t0 = time.time()
    try:
        p = subprocess.run(cmd, cwd=work, capture_output=True, text=True, timeout=args.timeout)
        out = p.stdout + p.stderr
    except subprocess.TimeoutExpired as e:
        out = (e.stdout or b"").decode() if isinstance(e.stdout, bytes) else (e.stdout or "")
        out += "\nTIMEOUT\n"
    secs = time.time() - t0
    shutil.rmtree(os.path.join(work, "states"), ignore_errors=True)
    v = verdict(out, secs, work)
    with open(log, "w") as f:
        f.write(out)
    with open(os.path.join(work, "secs"), "w") as f:
        f.write(f"{secs:.1f}")
    return v


def verdict(out, secs, work):
    """(PASS | FAIL:<invariant> | TIMEOUT, distinct states, seconds, run dir)"""
    states = re.findall(r"([\d,]+) distinct states found", out)
    states = states[-1].replace(",", "") if states else "?"
    m = re.search(r"Invariant (\w+) is violated", out)
    if m:
        return "FAIL:" + m.group(1), states, secs, work
    if "Model checking completed. No error has been found." in out:
        return "PASS", states, secs, work
    if out.endswith("TIMEOUT\n"):
        return "TIMEOUT", states, secs, work
    raise RuntimeError(f"TLC error in {work}:\n{out[-2000:]}")


def least(args, name, consts, crashes, writes, inv, lo, hi):
    while lo < hi:
        mid = (lo + hi) // 2
        bound = mid if inv == "SizeWithinBound" else consts["MaxPages"]
        cost = mid if inv == "CostWithinBound" else 100
        v, *_ = tlc(args, name, consts, crashes, writes, bound, cost, [inv])
        if v == "TIMEOUT":
            return f"?(>={lo})"
        if v == "PASS":
            hi = mid
        elif v != "FAIL:" + inv:
            raise RuntimeError(f"unexpected {v} for {inv}")
        else:
            lo = mid + 1
    return hi


def row(args, name, crashes, writes):
    over, extra = ROWS[name]
    consts = dict(BASE, **over)
    mp = consts["MaxPages"]
    res = {"row": name, "crashes": crashes, "writes": writes}
    v, res["states"], res["secs"], res["dir_strict"] = tlc(args, name, consts, crashes, writes, mp, 100, ["Safety", "Strict"])
    if v == "PASS":
        res["safety"] = res["strict"] = "PASS"
    elif v == "FAIL:Strict":
        res["strict"] = "FAIL"
        res["safety"], res["states"], res["secs"], _ = tlc(args, name, consts, crashes, writes, mp, 100, ["Safety"])
    else:
        res["safety"] = res["strict"] = v
    ov, _, _, res["dir_cap"] = tlc(args, name, consts, crashes, writes, mp, 100, ["NoOverflow"])
    res["max_R"] = ("cap" if ov == "FAIL:NoOverflow" else "?" if ov == "TIMEOUT"
                    else least(args, name, consts, crashes, writes, "SizeWithinBound", 1, mp))
    res["max_cost"] = "-" if writes else least(args, name, consts, crashes, writes, "CostWithinBound", 0, 3 * mp + 1)
    for inv in extra:
        res[inv], *_ = tlc(args, name, consts, crashes, writes, mp, 100, [inv])
    if isinstance(res["max_R"], int):
        big = dict(consts, MaxPages=mp + 2, K=consts["K"] + 2 if consts["K"] == mp else consts["K"])
        res["cap_P%d" % (mp + 2)], *_ = tlc(args, name, big, crashes, writes, mp + 2, 100, ["NoOverflow"])
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--only", default="")
    ap.add_argument("--jobs", type=int, default=4)
    ap.add_argument("--workers", type=int, default=3)
    ap.add_argument("--timeout", type=int, default=600)
    ap.add_argument("--tag", default="all")
    ap.add_argument("--cells", default="", help="subset of cells, e.g. cw,cW (C = crashes, W = writes in grow)")
    args = ap.parse_args()
    args.out = os.path.abspath(args.out)
    os.makedirs(args.out, exist_ok=True)
    names = [n for n in ROWS if not args.only or n in args.only.split(",")]
    combos = [(c, w) for c in (False, True) for w in (False, True)]
    if args.cells:
        combos = [(c == "C", w == "W") for c, w in args.cells.split(",")]
    jobs = [(n, c, w) for n in names for c, w in combos]
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.jobs) as pool:
        results = list(pool.map(lambda j: row(args, *j), jobs))
    print("| row | crashes | writes in grow | safety | strict | worst R | worst cost/grow | extra | distinct states | secs |")
    print("| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |")
    for r in results:
        extra = ", ".join(f"{k}={v}" for k, v in r.items() if k.startswith(("cap_", "NoSet")))
        print(f"| {r['row']} | {r['crashes']} | {r['writes']} | {r['safety']} | {r['strict']} | {r['max_R']} "
              f"| {r['max_cost']} | {extra or '-'} | {r['states']} | {r['secs']:.0f} |")
    with open(os.path.join(args.out, f"results-{args.tag}.json"), "w") as f:
        json.dump(results, f, indent=2)
    return 0


if __name__ == "__main__":
    sys.exit(main())
