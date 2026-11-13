#!/usr/bin/env python3
"""CBRD-27230 control: S5/S8s per repeat and the OOS pages of the control run (develop + oos c02f897268, 8 KB).

Usage: python3 control_table.py RUN_CONTROL_DIR
"""
import json
import statistics
import sys
from pathlib import Path

run = Path(sys.argv[1])
rows = [json.loads(l) for f in sorted(run.glob('results-*.jsonl')) for l in open(f)]


def ins(r):
    return ((r.get('instructions') or 0) + (r.get('drain_instructions') or 0)) / 1e9


print('| scenario | mode | build | rep 0 (G) | rep 1 (G) | rep 2 (G) | median (G) | wall s (median) | OS write MiB (median) | x develop |')
print('|---|---|---|---:|---:|---:|---:|---:|---:|---:|')
med = {}
for sc in ('S5', 'S8s'):
    for m in ('warm', 'io'):
        for v in ('develop', 'oos'):
            rs = sorted((r for r in rows if r['variant'] == v and r['mode'] == m and r['scenario'] == sc), key=lambda r: r['rep'])
            if not rs:
                continue
            vals = [ins(r) for r in rs]
            med[(sc, m, v)] = statistics.median(vals)
            osw = statistics.median((r['os_write_bytes'] + r.get('drain_os_write_bytes', 0)) / 2**20 for r in rs)
            wall = statistics.median(r['wall'] for r in rs)
            ratio = med[(sc, m, v)] / med[(sc, m, 'develop')] if (sc, m, 'develop') in med else float('nan')
            print(f'| {sc} | {m} | {v} | ' + ' | '.join(f'{x:.2f}' for x in vals) + f' | {med[(sc, m, v)]:.2f} | {wall:.2f} | {osw:,.0f} | x{ratio:.2f} |')
print()
print('| after | develop heap pages | oos OOS pages / recs |')
print('|---|---:|---:|')
pg = {}
order = []
for r in rows:
    if r['mode'] == 'pages':
        pg.setdefault(r['scenario'], {})[r['variant']] = r
        if r['scenario'] not in order:
            order.append(r['scenario'])
for k in order:
    if k.startswith(('after-load', 'warm-S5', 'io-S5', 'end')):
        d, o = pg[k].get('develop'), pg[k].get('oos')
        print(f'| {k} | {d["heap_pages"]:,} | {o["oos_pages"]:,} / {o["oos_recs"]:,} |')
chk = {}
for r in rows:
    if r['mode'] in ('checksum', 'content'):
        chk.setdefault((r['mode'], r['scenario']), {})[r['variant']] = tuple(r['values'])
bad = [k for k, v in chk.items() if len(set(v.values())) > 1]
print(f'\nchecksum/content points: {len(chk)}; disagreeing between develop and oos: {len(bad)}')
