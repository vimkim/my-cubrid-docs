#!/usr/bin/env python3
"""Check OosReuseFirst.tla for each design and setting; print one results table.

Per (design, crashes, writes during a grow, MaxPages):
  1. One full breadth-first run with CONSTRAINT Track.  Track prints every new maximum of R
     (file size), examined (pages fixed per grow) and sysops (dealloc + alloc + re-init per
     grow), and the first violation of Safe, SetComplete, StrictRule, NoFutileWork, NoOverflow.
     With several TLC workers each worker prints its own maxima; the maximum over all lines is
     exact.  The run also gives distinct states and wall time.
  2. For each violated property, one run with that INVARIANT and one TLC worker: breadth-first
     search returns a shortest counterexample.  Its action sequence goes to results.json and
     the full trace to <cfg>.log.

max_R is "cap" when NoOverflow fails (the file reached MaxPages: unbounded in this model).

Usage: python3 -I -B run.py --collect DIR
       python3 -I -B run.py --out NEW_DIR [--jobs 12] [--workers 1] [--max-pages 4,5]
           [--settings nocrash-quiet,nocrash-writes,crash-quiet,crash-writes]
           [--only a,b] [--misfit] [--relatch-any] [--no-ce]
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
SPEC = os.path.join(HERE, "OosReuseFirst.tla")
JAR = os.path.expanduser("~/.cache/tlaplus/tla2tools-1.7.4.jar")

# name -> (Design, Recheck, FastPathOn, LazyRemove)
DESIGNS = {
    "cand_fullboot": ("cand", 0, True, False),
    "cand_recheck": ("cand", 1, True, False),
    "cand_lazy": ("cand", 1, True, True),
    "reuse": ("reuse", 1, False, False),
    "reuse_fast": ("reuse", 1, True, False),
    "reuse_lazy": ("reuse", 1, True, True),
    "reuse_norecheck": ("reuse", 0, False, False),
    "reuse_noreinit": ("reuse_noreinit", 1, False, False),
    "reuse_nocheck": ("reuse_nocheck", 1, True, True),
    "hybrid": ("hybrid", 1, False, False),
    "hybrid_cand": ("hybrid_cand", 1, False, False),
    "hybrid_leaky": ("hybrid_leaky", 1, False, False),
}
PROPS = {"Safe": "TypeOK Safe", "SetComplete": "SetComplete", "StrictRule": "StrictRule",
         "NoFutileWork": "NoFutileWork", "NoOverflow": "NoOverflow"}
SETTINGS = {"nocrash-quiet": (False, False), "nocrash-writes": (False, True),
            "crash-quiet": (True, False), "crash-writes": (True, True)}


def b(x):
    return "TRUE" if x else "FALSE"


def write_cfg(path, name, crashes, writes, mp, args, extra):
    design, recheck, fast, lazy = DESIGNS[name]
    with open(path, "w") as f:
        f.write("CONSTANTS\n")
        f.write(f'  Design = "{design}"\n  MaxPages = {mp}\n  Cap = {args.cap}\n  L = {args.live}\n')
        f.write(f"  Recheck = {recheck}\n  Crashes = {b(crashes)}\n  WritesDuringGrow = {b(writes)}\n")
        f.write(f"  MayNotFit = {b(args.misfit)}\n  FastPathOn = {b(fast)}\n  LazyRemove = {b(lazy)}\n")
        f.write(f"  RelatchOnce = {b(not args.relatch_any)}\n")
        f.write("  Bound = 0\n  CostBound = 0\n  SysopBound = 0\n")
        f.write("SPECIFICATION Spec\n" + extra + "\n")


def tlc(work, cfg, workers):
    tmp = os.path.join(work, "tmp-" + cfg)
    meta = os.path.join(work, "states-" + cfg)
    os.makedirs(tmp, exist_ok=True)
    gc = max(1, workers // 2)
    cmd = ["java", "-Xmx8g", "-XX:+UseParallelGC", f"-XX:ParallelGCThreads={gc}", f"-Djava.io.tmpdir={tmp}",
           "-cp", JAR, "tlc2.TLC", "-workers", str(workers), "-deadlock", "-metadir", meta,
           "-config", cfg + ".cfg", "OosReuseFirst.tla"]
    t0 = time.time()
    proc = subprocess.run(cmd, cwd=work, capture_output=True, text=True)
    secs = round(time.time() - t0, 1)
    out = proc.stdout + proc.stderr
    with open(os.path.join(work, cfg + ".log"), "w") as f:
        f.write(out)
    shutil.rmtree(meta, ignore_errors=True)
    shutil.rmtree(tmp, ignore_errors=True)
    return out, secs


def trace_actions(out):
    """Action names of the error trace, with R and live after each step."""
    steps = []
    for blk in re.split(r"^State \d+: ", out, flags=re.M)[1:]:
        act = re.match(r"<(\w+)", blk)
        r = re.search(r"^/\\ R = (\d+)", blk, re.M)
        pg = re.search(r"^/\\ pg = <<([^>]*)>>", blk, re.M)
        steps.append(f"{act.group(1) if act else '?'}[R={r.group(1) if r else '?'} pg={pg.group(1).replace(' ', '') if pg else '?'}]")
    return steps


TAG = re.compile(r"^(?P<name>[a-z_]+)-(?P<setting>(?:no)?crash-(?:quiet|writes))-P(?P<mp>\d+)"
                 r"(?P<misfit>-misfit)?(?P<ra>-relatchany)?$")


def wall_secs(out):
    m = re.search(r"Finished in ((?:\d+h )?(?:\d+min )?\d+s)", out)
    if not m:
        return None
    unit = {"h": 3600, "min": 60, "s": 1}
    return sum(int(n) * unit[u] for n, u in re.findall(r"(\d+)(h|min|s)", m.group(1)))


def parse(work, tag):
    """Result row for the measuring log <tag>.log and its counterexample logs."""
    t = TAG.match(tag).groupdict()
    crashes, _ = SETTINGS[t["setting"]]
    out = open(os.path.join(work, tag + ".log")).read()
    if "Model checking completed. No error has been found." not in out:
        return {"design": t["name"], "setting": t["setting"], "max_pages": int(t["mp"]), "error": out[-2000:]}
    rec = {}
    for k, v in re.findall(r'<<"REC", "(\w+)", (\d+)>>', out):
        rec[k] = max(rec.get(k, 0), int(v))
    viol = set(re.findall(r'<<"VIOL", "(\w+)">>', out))
    states = re.search(r"([\d,]+) distinct states found, 0 states left", out).group(1).replace(",", "")
    workers = re.search(r"with (\d+) worker", out)
    r = {"design": t["name"], "setting": t["setting"], "max_pages": int(t["mp"]), "misfit": bool(t["misfit"]),
         "relatch_any": bool(t["ra"]), "states": int(states), "secs": wall_secs(out),
         "workers": int(workers.group(1)) if workers else None,
         "max_R": "cap" if "NoOverflow" in viol else rec.get("maxR", 0),
         "max_cost": rec.get("maxCost", 0), "max_sysops": rec.get("maxSysops", 0)}
    for p in PROPS:
        if p == "NoFutileWork" and crashes:
            r[p] = "-"
            continue
        r[p] = "FAIL" if p in viol else "PASS"
        ce = os.path.join(work, f"{tag}-ce-{p}.log")
        if p in viol and os.path.exists(ce):
            r[p + "_ce"] = trace_actions(open(ce).read())
    return r


def check(args, name, setting, mp):
    crashes, writes = SETTINGS[setting]
    tag = (f"{name}-{setting}-P{mp}{'-misfit' if args.misfit else ''}"
           f"{'-relatchany' if args.relatch_any else ''}")
    write_cfg(os.path.join(args.out, tag + ".cfg"), name, crashes, writes, mp, args, "CONSTRAINT Track")
    out, _ = tlc(args.out, tag, args.workers)
    viol = set(re.findall(r'<<"VIOL", "(\w+)">>', out))
    for p in PROPS:
        if p in viol and not (p == "NoFutileWork" and crashes) and not args.no_ce:
            cfg = f"{tag}-ce-{p}"
            write_cfg(os.path.join(args.out, cfg + ".cfg"), name, crashes, writes, mp, args,
                      "INVARIANTS " + PROPS[p])
            tlc(args.out, cfg, 1)
    return parse(args.out, tag)


def report(work, results, header):
    order = list(DESIGNS)
    results.sort(key=lambda r: (order.index(r["design"]), list(SETTINGS).index(r["setting"]),
                                r["max_pages"], r.get("misfit", False), r.get("relatch_any", False)))
    print(header)
    cols = ["design", "setting", "max_pages", "misfit", "relatch_any", "Safe", "SetComplete", "StrictRule",
            "NoOverflow", "max_R", "max_cost", "max_sysops", "NoFutileWork", "states", "secs", "workers"]
    print("| " + " | ".join(cols) + " | shortest counterexample lengths |")
    print("|" + " --- |" * (len(cols) + 1))
    for r in results:
        if "error" in r:
            print(f"| {r['design']} | {r['setting']} | {r['max_pages']} | TLC ERROR, see log |")
            continue
        ces = ", ".join(f"{p}:{len(r[p + '_ce'])}" for p in PROPS if p + "_ce" in r)
        print("| " + " | ".join(str(r[c]) for c in cols) + f" | {ces or '-'} |")
    with open(os.path.join(work, "results.json"), "w") as f:
        json.dump({"header": header, "results": results}, f, indent=1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out")
    ap.add_argument("--collect", metavar="DIR", help="rebuild the table from DIR's logs and exit")
    ap.add_argument("--jobs", type=int, default=12)
    ap.add_argument("--workers", type=int, default=1, help="TLC workers per measuring run")
    ap.add_argument("--max-pages", default="4,5")
    ap.add_argument("--cap", type=int, default=2)
    ap.add_argument("--live", type=int, default=2)
    ap.add_argument("--settings", default=",".join(SETTINGS))
    ap.add_argument("--only", default="")
    ap.add_argument("--misfit", action="store_true", help="MayNotFit = TRUE")
    ap.add_argument("--relatch-any", action="store_true", help="RelatchOnce = FALSE")
    ap.add_argument("--no-ce", action="store_true", help="skip counterexample runs")
    args = ap.parse_args()
    if args.collect:
        return collect(os.path.abspath(args.collect))
    args.out = os.path.abspath(args.out)
    if os.path.exists(args.out):
        print(f"--out {args.out} exists", file=sys.stderr)
        return 2
    os.makedirs(args.out)
    shutil.copy(SPEC, args.out)
    sha = hashlib.sha256(open(SPEC, "rb").read()).hexdigest()
    names = [n for n in DESIGNS if not args.only or n in args.only.split(",")]
    settings = args.settings.split(",")
    caps = [int(x) for x in args.max_pages.split(",")]
    jobs = [(n, s, mp) for n in names for s in settings for mp in caps]
    jobs.sort(key=lambda j: (-j[2], -sum(SETTINGS[j[1]])))
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.jobs) as pool:
        results = list(pool.map(lambda j: check(args, *j), jobs))
    report(args.out, results, f"spec sha256 {sha}  Cap={args.cap} L={args.live}")
    return 0


def collect(work):
    """Rebuild the table from the logs of a finished or stopped run directory."""
    sha = hashlib.sha256(open(os.path.join(work, "OosReuseFirst.tla"), "rb").read()).hexdigest()
    tags = sorted(f[:-4] for f in os.listdir(work) if f.endswith(".cfg") and "-ce-" not in f
                  and os.path.exists(os.path.join(work, f[:-4] + ".log")))
    report(work, [parse(work, t) for t in tags], f"spec sha256 {sha}  (collected from {work})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
