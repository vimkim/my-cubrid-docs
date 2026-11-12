import csv, sys, statistics as st
from collections import defaultdict
path, metrics = sys.argv[1], sys.argv[2].split(',')
arms = ('base', 'new', 'fix')
d = defaultdict(dict)
for row in csv.DictReader(open(path)):
    d[(row['label'], int(row['rep']))][row['metric']] = row['value']
reps = sorted({r for (_, r) in d})
ok = [r for r in reps if all(d.get((a, r), {}).get('exit') == '0' for a in arms)]
print(f"reps={len(reps)} all_arms_ok={len(ok)} failed={[(a, r) for r in reps for a in arms if d.get((a, r), {}).get('exit') != '0']}")
loads = [float(d[(a, r)][k]) for r in ok for a in arms for k in ('load1_before', 'load1_after')]
print(f"load1 min={min(loads):.1f} median={st.median(loads):.1f} max={max(loads):.1f}")
def iqr(v):
    q = st.quantiles(v, n=4, method='inclusive'); return q[0], q[2]
def cell(v):
    lo, hi = iqr(v); return f"{st.median(v):.2f} ({min(v):.2f}-{max(v):.2f}, IQR {lo:.2f}-{hi:.2f})"
print("| metric | base | new | fix | new/base | fix/base | paired fix-base med (neg/pos) | fix-base within base IQR width | paired fix-new med (neg/pos) |")
print("|---|---|---|---|---|---|---|---|---|")
for m in metrics:
    v = {a: [float(d[(a, r)][m]) for r in ok if m in d[(a, r)]] for a in arms}
    if not all(v.values()): continue
    fb = [float(d[('fix', r)][m]) - float(d[('base', r)][m]) for r in ok]
    fn = [float(d[('fix', r)][m]) - float(d[('new', r)][m]) for r in ok]
    lo, hi = iqr(v['base']); mb = st.median(v['base'])
    print(f"| {m} | {cell(v['base'])} | {cell(v['new'])} | {cell(v['fix'])} | {st.median(v['new'])/mb-1:+.1%} | {st.median(v['fix'])/mb-1:+.1%} "
          f"| {st.median(fb):+.2f} ({sum(x<0 for x in fb)}/{sum(x>0 for x in fb)}) | {'yes' if abs(st.median(fb)) <= hi - lo else 'no'} | {st.median(fn):+.2f} ({sum(x<0 for x in fn)}/{sum(x>0 for x in fn)}) |")
