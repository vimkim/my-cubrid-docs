import json, sys
from pathlib import Path
A = Path(__file__).resolve().parent
cpu = json.loads((A / 'cpu-summary.json').read_text())['cpu']
io = json.loads((A / 'io-summary.json').read_text())['io']
def f(x): return f'{x:+.2f}%'
def ins(r, l): return r['instructions:u']['change_pct'][l]
def cyc(r, l): return r['cycles:u']['change_pct'][l]
def tim(r, l): return r['elapsed']['change_pct'][l]
SIZE = {'w36': '4.6KB', 'w47': '6.0KB', 'w78': '9.9KB', 'w110': '13.8KB'}
print('## sweep')
print('| 값 | 질의 | base 명령어 | head 명령어 | sketch 명령어 | head cycles | sketch cycles | spread 최대 |')
print('|---|---|---:|---:|---:|---:|---:|---:|')
for t in SIZE:
    for c in ('length', 'substr', 'fullscan', 'narrow'):
        r = next(r for r in cpu if r['key'] == ['sweep', t, c])
        i = r['instructions:u']
        sp = max(i[l]['spread_pct'] for l in ('base', 'head', 'thr'))
        print(f"| {SIZE[t]} | {c} | {i['base']['median']/1e6:,.1f}M | {f(ins(r,'head'))} | {f(ins(r,'thr'))} | {f(cyc(r,'head'))} | {f(cyc(r,'thr'))} | {sp:.2f}% |")
print('## ordinary')
for r in cpu:
    if r['key'][0] == 'ordinary':
        i = r['instructions:u']
        print(f"| {r['key'][2]} | {i['base']['median']/1e6:,.1f}M | {i['head']['median']/1e6:,.1f}M | {f(ins(r,'head'))} | {f(ins(r,'thr'))} | {i['head']['n']} | {i['base']['spread_pct']:.2f}% / {i['head']['spread_pct']:.2f}% |")
print('## io')
for r in io:
    i = r['instructions:u']
    sp = max(i[l]['spread_pct'] for l in ('base', 'head', 'thr'))
    e = r['elapsed']
    print(f"| {r['key'][0]} | {r['key'][1]} | {r['key'][2]} | {i['base']['median']/1e6:,.1f}M | {f(ins(r,'head'))} | {f(ins(r,'thr'))} | {e['base']['median']:.2f} / {e['head']['median']:.2f} / {e['thr']['median']:.2f} | {r['ioread']['base']:,} / {r['ioread']['head']:,} / {r['ioread']['thr']:,} | {sp:.2f}% |")
