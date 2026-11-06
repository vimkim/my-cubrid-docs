#!/usr/bin/env python3
"""Check OosSlackBound.tla: slack-bound designs against cand_fullboot.

One TLC run per (design, crashes, writes during a grow, MaxPages) explores the whole state space
with the safety invariants (TypeOK, FreeHoldsNothing, TrackerNeverHigh) and dumps every state into
a FIFO. grep reads the FIFO and keeps the value distribution of R, examined, maxDrift and the
sticky flags. For each reachable flag a second TLC run (BFS) prints the shortest counterexample,
at the smallest MaxPages only. Each job writes its JSON as soon as it ends, so a killed run
resumes with --resume.

Usage: python3 -I -B run.py --out DIR [--resume] [--jobs 4] [--workers 3]
       [--designs a,b] [--settings Q,W,CQ,CW] [--pages 7,8] [--live 2] [--cap 2]
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
SPEC = os.path.join(HERE, "OosSlackBound.tla")
JAR = os.path.expanduser("~/.cache/tlaplus/tla2tools-1.7.4.jar")

# name -> (Design, K, FreeGate, BootLap)
DESIGNS = {
    "cand_fullboot": ("set", 0, False, True),
    "slack_set_K1": ("set", 1, False, True),
    "slack_set_K2": ("set", 2, False, True),
    "slack_set_K1_noboot": ("set", 1, False, False),
    "count_K0": ("count", 0, False, True),
    "slack_count_K1": ("count", 1, False, True),
    "slack_count_K1_noboot": ("count", 1, False, False),
    "cand_freegate": ("set", 0, True, True),
}
# (crashes, writes during a grow) -> MaxPages per design.  Two caps where a design is bounded,
# to show the worst size does not move with the cap.  Skipped cells and why:
#   *_noboot without crashes is the same spec as its BootLap twin (BootLap acts only at a crash).
#   count with writes already reaches the cap without crashes, so crash+writes adds nothing; its
#   lap state makes P7 slow, so it runs at P5/P6.
#   crash+writes explodes (millions of states at P5); it runs for the two set designs only.
Q, W, CQ, CW = (False, False), (False, True), (True, False), (True, True)
JOBS = {
    "cand_fullboot": {Q: [6, 7], W: [6, 7], CQ: [6, 7], CW: [5]},
    "slack_set_K1": {Q: [6, 7], W: [6, 7], CQ: [6, 7], CW: [5]},
    "slack_set_K2": {Q: [6, 7], W: [6, 7], CQ: [6, 7]},
    "slack_set_K1_noboot": {CQ: [6, 7]},
    "count_K0": {Q: [6, 7], W: [5, 6], CQ: [6, 7]},
    "slack_count_K1": {Q: [6, 7], W: [5, 6], CQ: [6, 7]},
    "slack_count_K1_noboot": {CQ: [6, 7]},
    "cand_freegate": {Q: [6, 7], W: [6, 7], CQ: [6, 7]},
}
FLAGS = {"strongBroken": "NoGrowthPastStaleEmpty", "weakBroken": "NoGrowthPastSlack",
         "overflow": "NoOverflow", "futile": "NoFutileWork", "maxDrift": "NoDrift"}
TRACKED = ("R", "examined") + tuple(FLAGS)


def tb(b):
    return "TRUE" if b else "FALSE"


def write_cfg(path, d, crashes, writes, mp, cap, live, invariants):
    design, k, gate, boot = d
    with open(path, "w") as f:
        f.write("CONSTANTS\n")
        f.write(f'  Design = "{design}"\n  K = {k}\n  FreeGate = {tb(gate)}\n  BootLap = {tb(boot)}\n')
        f.write(f"  MaxPages = {mp}\n  Cap = {cap}\n  L = {live}\n")
        f.write(f"  Crashes = {tb(crashes)}\n  WritesDuringGrow = {tb(writes)}\n")
        f.write("SPECIFICATION Spec\n")
        f.write("INVARIANTS " + " ".join(invariants) + "\n")


def tlc_cmd(workdir, cfg, workers, dump=None):
    tmp = os.path.join(workdir, "tmp-" + cfg)
    os.makedirs(tmp, exist_ok=True)
    cmd = ["java", "-XX:+UseParallelGC", f"-Djava.io.tmpdir={tmp}", "-cp", JAR, "tlc2.TLC",
           "-workers", str(workers), "-deadlock", "-metadir", os.path.join(workdir, "states-" + cfg),
           "-config", cfg + ".cfg"]
    if dump:
        cmd += ["-dump", dump]
    return cmd + ["OosSlackBound.tla"], tmp


def finish(workdir, cfg, tmp, out):
    with open(os.path.join(workdir, cfg + ".log"), "w") as f:
        f.write(out)
    shutil.rmtree(os.path.join(workdir, "states-" + cfg), ignore_errors=True)
    shutil.rmtree(tmp, ignore_errors=True)


def explore(workdir, cfg, workers):
    """Full exploration; returns (TLC output, seconds, {var: set of values})."""
    # A name ending in .dump keeps TLC from appending the suffix; the FIFO keeps gigabytes off disk.
    dump = os.path.join(workdir, cfg + ".dump")
    if os.path.exists(dump):
        os.remove(dump)
    os.mkfifo(dump)
    cmd, tmp = tlc_cmd(workdir, cfg, workers, dump)
    pat = r"^/\\ (" + "|".join(TRACKED) + r") = "
    t0 = time.time()
    proc = subprocess.Popen(cmd, cwd=workdir, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    grep = subprocess.Popen(f"LC_ALL=C grep -E '{pat}' '{dump}' | sort -u", shell=True,
                            stdout=subprocess.PIPE, text=True)
    with concurrent.futures.ThreadPoolExecutor(1) as ex:
        fut = ex.submit(grep.stdout.read)
        out = proc.stdout.read()
        proc.wait()
        try:
            # TLC died before opening the dump: release grep from its blocking open.
            os.close(os.open(dump, os.O_WRONLY | os.O_NONBLOCK))
        except OSError:
            pass
        lines = fut.result().splitlines()
    grep.wait()
    secs = time.time() - t0
    os.remove(dump)
    finish(workdir, cfg, tmp, out)
    vals = {}
    for line in lines:
        m = re.match(r"^/\\ (\w+) = (.*)$", line)
        vals.setdefault(m.group(1), set()).add(m.group(2))
    return out, secs, vals


def counterexample(workdir, cfg, workers):
    cmd, tmp = tlc_cmd(workdir, cfg, workers)
    p = subprocess.run(cmd, cwd=workdir, capture_output=True, text=True)
    out = p.stdout + p.stderr
    finish(workdir, cfg, tmp, out)
    return out


def trace_of(out):
    """Action names and the variables that matter, per step."""
    steps = []
    for m in re.finditer(r"State (\d+): <([^>]*)>\n((?:/\\ .*\n)+)", out):
        body = dict(re.findall(r"/\\ (\w+) = (.*)", m.group(3)))
        act = m.group(2).split(" line")[0]
        steps.append(f"{m.group(1)} {act}: pg={body.get('pg')} R={body.get('R')} busy={body.get('busy')} "
                     f"cand={body.get('cand')} n={body.get('n')} unknown={body.get('unknown')} "
                     f"gpc={body.get('gpc')} stale={body.get('stale')}")
    return steps


def job_tag(name, crashes, writes, mp):
    return f"{name}-{'crash' if crashes else 'nocrash'}-{'writes' if writes else 'quiet'}-P{mp}"


def check(args, name, crashes, writes, mp, want_cex):
    tag = job_tag(name, crashes, writes, mp)
    res_path = os.path.join(args.out, tag + ".json")
    if os.path.exists(res_path):
        with open(res_path) as f:
            return json.load(f)
    d = DESIGNS[name]
    cfg = tag + "-all"
    write_cfg(os.path.join(args.out, cfg + ".cfg"), d, crashes, writes, mp, args.cap, args.live,
              ["TypeOK", "FreeHoldsNothing", "TrackerNeverHigh"])
    out, secs, vals = explore(args.out, cfg, args.workers)
    if "Model checking completed. No error has been found." not in out:
        raise RuntimeError(f"{cfg}: safety or TLC error\n{out[-3000:]}")
    states = int(re.findall(r"([\d,]+) distinct states found", out)[-1].replace(",", ""))
    res = {"design": name, "crashes": crashes, "writes": writes, "max_pages": mp, "states": states,
           "secs": round(secs, 1), "R": max(int(v) for v in vals["R"]),
           "examined": max(int(v) for v in vals["examined"]),
           "maxDrift": max(int(v) for v in vals["maxDrift"]), "traces": {}}
    for flag in ("strongBroken", "weakBroken", "overflow", "futile"):
        res[flag] = "TRUE" in vals[flag]
    if want_cex:
        for flag, inv in FLAGS.items():
            if res[flag] if flag != "maxDrift" else res[flag] > 0:
                c = f"{tag}-cex-{inv}"
                write_cfg(os.path.join(args.out, c + ".cfg"), d, crashes, writes, mp, args.cap, args.live, [inv])
                o = counterexample(args.out, c, args.workers)
                if f"Invariant {inv} is violated" not in o:
                    raise RuntimeError(f"{c}: expected a violation\n{o[-3000:]}")
                res["traces"][inv] = trace_of(o)
    with open(res_path, "w") as f:
        json.dump(res, f, indent=1)
    print(f"done {tag}: states={states} secs={res['secs']} R={res['R']} exam={res['examined']}", flush=True)
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--resume", action="store_true")
    ap.add_argument("--jobs", type=int, default=4)
    ap.add_argument("--workers", type=int, default=3)
    ap.add_argument("--cap", type=int, default=2)
    ap.add_argument("--live", type=int, default=2)
    ap.add_argument("--designs", default=",".join(DESIGNS))
    ap.add_argument("--settings", default="Q,W,CQ,CW", help="subset of Q,W,CQ,CW")
    ap.add_argument("--pages", help="override MaxPages for every job, e.g. 7,8")
    args = ap.parse_args()
    args.out = os.path.abspath(args.out)
    if os.path.exists(args.out) and not args.resume:
        print(f"--out {args.out} exists; pass --resume", file=sys.stderr)
        return 2
    os.makedirs(args.out, exist_ok=True)
    shutil.copy(SPEC, args.out)
    with open(SPEC, "rb") as f:
        sha = hashlib.sha256(f.read()).hexdigest()
    names = {"Q": Q, "W": W, "CQ": CQ, "CW": CW}
    wanted = {names[x] for x in args.settings.split(",")}
    override = [int(x) for x in args.pages.split(",")] if args.pages else None
    jobs = [(nm, c, w, mp, i == 0) for nm in args.designs.split(",") for (c, w), ps in JOBS[nm].items()
            if (c, w) in wanted for i, mp in enumerate(override or ps)]
    # Largest spaces first so the pool does not end on one long job.
    jobs.sort(key=lambda j: (not (j[1] and j[2]), not j[2], -j[3]))
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.jobs) as pool:
        results = list(pool.map(lambda j: check(args, *j), jobs))
    order = {nm: i for i, nm in enumerate(DESIGNS)}
    results.sort(key=lambda r: (order[r["design"]], r["crashes"], r["writes"], r["max_pages"]))
    with open(os.path.join(args.out, "results.json"), "w") as f:
        json.dump(results, f, indent=1)
    print(f"OosSlackBound.tla sha256 {sha}")
    print(f"Cap={args.cap} L={args.live}")
    print("| design | crashes | writes | MaxPages | current spec | slack spec | max R | max exam/grow "
          "| futile work | max drift | states | secs |")
    print("|" + " --- |" * 12)
    for r in results:
        size = "cap" if r["overflow"] else r["R"]
        print(f"| {r['design']} | {r['crashes']} | {r['writes']} | {r['max_pages']} "
              f"| {'FAIL' if r['strongBroken'] else 'PASS'} | {'FAIL' if r['weakBroken'] else 'PASS'} "
              f"| {size} | {r['examined']} | {'yes' if r['futile'] else 'no'} | {r['maxDrift']} "
              f"| {r['states']} | {r['secs']} |")
    return 0


if __name__ == "__main__":
    sys.exit(main())
