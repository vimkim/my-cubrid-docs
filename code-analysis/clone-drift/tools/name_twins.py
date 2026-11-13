#!/usr/bin/env python3
"""Pair same-named functions in different files (catches rewritten copies CPD misses).

usage: name_twins.py <cubrid-root> <outdir>  -> <outdir>/twins.tsv
"""
import csv, os, re, sys, difflib, subprocess
from collections import defaultdict
ROOT, OUT = sys.argv[1], sys.argv[2]
SKIP = re.compile(r"^src/(heaplayers|win_tools)/")
by = defaultdict(list)
for r in csv.reader(open(os.path.join(OUT, "lizard.csv"))):
    nloc, path, name, s, e = int(r[0]), r[6], r[7], int(r[9]), int(r[10])
    short = name.split("::")[-1]
    if nloc < 6 or SKIP.match(path) or short in ("main", "operator", "usage") or short.startswith("~"):
        continue
    by[short].append((path, name, s, e, nloc))
cache = {}
def body(p, s, e):
    if p not in cache:
        cache[p] = open(os.path.join(ROOT, p), errors="replace").read().splitlines()
    toks = re.findall(r"[A-Za-z_]\w*|\S", "\n".join(cache[p][s:e]))
    return toks
def mod(p): return p.split("/")[1]
rows = []
for short, occ in by.items():
    files = {o[0] for o in occ}
    if len(files) < 2 or len(occ) > 4:
        continue
    for i in range(len(occ)):
        for j in range(i + 1, len(occ)):
            a, b = occ[i], occ[j]
            if a[0] == b[0]:
                continue
            ta, tb = body(*a[0:1], a[2], a[3]), body(b[0], b[2], b[3])
            sim = difflib.SequenceMatcher(None, ta, tb, autojunk=False).ratio()
            if sim < 0.45 or sim > 0.995:
                continue
            rows.append((sim * min(a[4], b[4]) * (2 if mod(a[0]) != mod(b[0]) else 1), sim, short, a, b))
rows.sort(key=lambda r: -r[0])
with open(os.path.join(OUT, "twins.tsv"), "w") as f:
    f.write("score\tsim\tname\tA\tA_nloc\tB\tB_nloc\tcross_mod\n")
    for sc, sim, short, a, b in rows:
        f.write(f"{sc:.0f}\t{sim:.2f}\t{short}\t{a[0]}:{a[2]}\t{a[4]}\t{b[0]}:{b[2]}\t{b[4]}\t{int(mod(a[0])!=mod(b[0]))}\n")
print(len(rows), "twin pairs")
