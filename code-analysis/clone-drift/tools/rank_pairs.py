#!/usr/bin/env python3
"""Rank CPD clone pairs by drift likelihood.

usage: rank_pairs.py <cubrid-root> <outdir>
reads <outdir>/cpd-plain.xml, cpd-ignore.xml, lizard.csv; writes pairs.tsv
"""
import csv, subprocess, sys, xml.etree.ElementTree as ET, itertools, os, re
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor

ROOT, OUT = sys.argv[1], sys.argv[2]
NS = {"c": "https://pmd-code.org/schema/cpd-report"}
SKIP = re.compile(r"^src/(heaplayers|win_tools|base/(jisx0212|ksc5601|CRC)\.h)")
MAX_GROUP = 6

funcs = defaultdict(list)
with open(os.path.join(OUT, "lizard.csv")) as f:
    for r in csv.reader(f):
        funcs[r[6]].append((int(r[9]), int(r[10]), r[7]))

def func_at(path, a, b):
    best = None
    for s, e, n in funcs.get(path, []):
        ov = min(b, e) - max(a, s)
        if ov >= 0 and (best is None or ov > best[0] or (ov == best[0] and e - s < best[1][1] - best[1][0])):
            best = (ov, (s, e, n))
    return best[1] if best else (a, b, "<global>")

pairs = {}
for mode in ("plain", "ignore"):
    tree = ET.parse(os.path.join(OUT, f"cpd-{mode}.xml"))
    for d in tree.getroot().findall("c:duplication", NS):
        tokens, lines = int(d.get("tokens")), int(d.get("lines"))
        occ = []
        for fe in d.findall("c:file", NS):
            p = os.path.relpath(fe.get("path"), ROOT)
            if SKIP.match(p):
                continue
            a, b = int(fe.get("line")), int(fe.get("endline"))
            occ.append((p, a, b) + func_at(p, a, b))
        if len(occ) < 2 or len(occ) > MAX_GROUP:
            continue
        for x, y in itertools.combinations(occ, 2):
            kx, ky = (x[0], x[5], x[3]), (y[0], y[5], y[3])
            if kx == ky:
                continue
            key = tuple(sorted([kx, ky]))
            e = pairs.setdefault(key, {"tokens": 0, "lines": 0, "modes": set(), "ranges": []})
            e["tokens"] = max(e["tokens"], tokens)
            e["lines"] = max(e["lines"], lines)
            e["modes"].add(mode)
            e["ranges"].append((x[:3], y[:3]))

ends = {}
for fn in funcs:
    for s, e, n in funcs[fn]:
        ends[(fn, n, s)] = e

def last_change(path, s, e):
    try:
        out = subprocess.run(["git", "-C", ROOT, "blame", "--line-porcelain", "-L", f"{s},{e}", "HEAD", "--", path],
                             capture_output=True, text=True, timeout=60).stdout
    except Exception:
        return (0, "", "")
    best, cur = (0, "", ""), {}
    for line in out.splitlines():
        m = re.match(r"^([0-9a-f]{40}) ", line)
        if m:
            cur = {"h": m.group(1)}
        elif line.startswith("committer-time "):
            cur["t"] = int(line.split()[1])
        elif line.startswith("summary "):
            cur["s"] = line[8:]
            if cur.get("t", 0) > best[0]:
                best = (cur["t"], cur["h"][:10], cur["s"])
    return best

keys = list(pairs)
def side_info(k):
    path, name, s = k
    e = ends.get((path, name, s), s)
    return last_change(path, s, e)
uniq = sorted({k for key in keys for k in key})
with ThreadPoolExecutor(32) as ex:
    info = dict(zip(uniq, ex.map(side_info, uniq)))

def module(p):
    parts = p.split("/")
    return parts[1] if len(parts) > 2 else parts[0]

rows = []
for (ka, kb), e in pairs.items():
    ia, ib = info[ka], info[kb]
    cross_mod = module(ka[0]) != module(kb[0])
    cross_file = ka[0] != kb[0]
    gap_days = abs(ia[0] - ib[0]) / 86400
    score = (e["tokens"] / 100.0) * (1 + 2 * cross_mod + 0.5 * cross_file) * (1 + min(gap_days, 3650) / 365.0)
    rows.append((score, ka, kb, e, ia, ib, cross_mod, gap_days))
rows.sort(key=lambda r: -r[0])
import datetime
def d(t): return datetime.datetime.fromtimestamp(t, datetime.timezone.utc).strftime("%Y-%m-%d") if t else "-"
with open(os.path.join(OUT, "pairs.tsv"), "w") as f:
    f.write("rank\tscore\ttokens\tlines\tmodes\tcross_mod\tgap_days\tA_file\tA_func\tA_start\tA_last\tA_commit\tA_subject\tB_file\tB_func\tB_start\tB_last\tB_commit\tB_subject\n")
    for i, (sc, ka, kb, e, ia, ib, cm, g) in enumerate(rows, 1):
        f.write("\t".join(map(str, [i, f"{sc:.1f}", e["tokens"], e["lines"], "+".join(sorted(e["modes"])), int(cm), int(g),
                                    ka[0], ka[1], ka[2], d(ia[0]), ia[1], ia[2], kb[0], kb[1], kb[2], d(ib[0]), ib[1], ib[2]])) + "\n")
print(len(rows), "pairs")
