#!/usr/bin/env python3
"""Filter pairs.tsv: drop table/enum/switch-only clones, add function diff size.

usage: filter_pairs.py <cubrid-root> <outdir>   -> <outdir>/review.tsv
"""
import csv, os, re, sys, difflib
ROOT, OUT = sys.argv[1], sys.argv[2]
lz = {}
with open(os.path.join(OUT, "lizard.csv")) as f:
    for r in csv.reader(f):
        lz[(r[6], r[7], int(r[9]))] = int(r[10])
cache = {}
def lines(p):
    if p not in cache:
        with open(os.path.join(ROOT, p), errors="replace") as f:
            cache[p] = f.read().splitlines()
    return cache[p]
TRIVIAL = re.compile(r"^\s*(case\b.*:|return\b[^;]*;|break;|default:|[{}];?|/?\*.*|//.*|#.*|\"[^\"]*\",?|[A-Z0-9_]+\s*(=\s*[^,]*)?,?|)\s*$")
CTRL = re.compile(r"\b(if|for|while|goto)\b|->|\(")
def body(p, fn, s):
    e = lz.get((p, fn, s), s)
    return [l.strip() for l in lines(p)[s-1:e] if l.strip()]
rows = list(csv.DictReader(open(os.path.join(OUT, "pairs.tsv")), delimiter="\t"))
out = []
for r in rows:
    if "<global>" in (r["A_func"], r["B_func"]):
        continue
    a = body(r["A_file"], r["A_func"], int(r["A_start"]))
    b = body(r["B_file"], r["B_func"], int(r["B_start"]))
    if not a or not b:
        continue
    triv = sum(1 for l in a if TRIVIAL.match(l)) / len(a)
    ctrl = sum(1 for l in a if re.search(r"\b(if|while|for)\s*\(", l))
    if triv > 0.6 or ctrl < 3:
        continue
    sm = difflib.SequenceMatcher(None, a, b, autojunk=False)
    diff_lines = sum(max(i2 - i1, j2 - j1) for t, i1, i2, j1, j2 in sm.get_opcodes() if t != "equal")
    ratio = sm.ratio()
    if diff_lines == 0:
        continue
    r.update(diff_lines=diff_lines, sim=f"{ratio:.2f}", trivial=f"{triv:.2f}", A_len=len(a), B_len=len(b))
    out.append(r)
cols = list(rows[0].keys()) + ["diff_lines", "sim", "trivial", "A_len", "B_len"]
with open(os.path.join(OUT, "review.tsv"), "w") as f:
    w = csv.DictWriter(f, cols, delimiter="\t"); w.writeheader(); w.writerows(out)
print(len(out), "pairs kept")
