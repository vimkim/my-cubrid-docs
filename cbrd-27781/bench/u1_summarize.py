#!/usr/bin/env python3
"""Summarize u1_growth_lock.sh results.csv: median and range per (point, n, label), and the
head and mid change against base by medians. Usage: u1_summarize.py results.csv"""
import csv, statistics, sys
from collections import defaultdict
d = defaultdict(list)
for r in csv.DictReader(open(sys.argv[1])):
    try:
        d[(r['point'], int(r['n']), r['metric'], r['label'])].append(float(r['value']))
    except ValueError:
        pass
labels = ['base', 'mid', 'head']
metrics = ['insert_rows_per_sec', 'ins_stmt_p50_ms', 'ins_stmt_p99_ms', 'server_ctxsw',
           'server_task_clock_ms', 'load_before', 'errors']
points = sorted({(p, n) for (p, n, _, _) in d}, key=lambda x: (x[0] != 'insert', x[1]))
for m in metrics:
    print(f'\n### {m}\n')
    print('| point | N | ' + ' | '.join(f'{l} median (min-max, runs)' for l in labels) + ' | mid vs base | head vs base |')
    print('|---|---|' + '---|' * (len(labels) + 2))
    for p, n in points:
        cells, med = [], {}
        for l in labels:
            v = d.get((p, n, m, l), [])
            if not v:
                cells.append('-'); continue
            med[l] = statistics.median(v)
            cells.append(f'{med[l]:.6g} ({min(v):.6g}-{max(v):.6g}, {len(v)})')
        rel = []
        for l in ('mid', 'head'):
            rel.append(f'{100 * (med[l] - med["base"]) / med["base"]:+.1f}%' if l in med and med.get('base') else '-')
        print(f'| {p} | {n} | ' + ' | '.join(cells) + ' | ' + ' | '.join(rel) + ' |')
