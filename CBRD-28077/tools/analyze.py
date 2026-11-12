#!/usr/bin/env python3
"""CBRD-28077: summarize oosbench.py results.jsonl into Markdown tables and a JSON summary.

Usage: python3 analyze.py RUN_DIR [--out summary.md]

Every cell is the median over repeats. Ratios are variant / develop, so a value below 1 means the variant
does less work (or takes less time) than develop.
"""

import argparse
import collections
import json
import statistics
from pathlib import Path

VARIANTS = ('develop', 'oos', 'sidecar', 'inner')
SCEN = ('S4', 'S1', 'S2', 'S3n', 'S3w', 'S5', 'S6', 'S7', 'S8b', 'S8s', 'S9')
LABEL = {'S4': 'load INSERT', 'S1': 'narrow scan', 'S2': 'wide scan', 'S3n': 'PK lookup, small col',
         'S3w': 'PK lookup, big col', 'S5': 'UPDATE small col (all)', 'S6': 'UPDATE big col (1/4)',
         'S7': 'UPDATE+INSERT+COMMIT loop', 'S8b': 'UPDATE big+COMMIT loop', 'S8s': 'UPDATE small+COMMIT loop',
         'S9': 'DELETE 1/4'}
METRICS = {
    'instructions': ('server instructions', lambda r: r.get('instructions')),
    'total_instructions': ('server instructions incl. drain', lambda r: (r.get('instructions') or 0)
                           + (r.get('drain_instructions') or 0)),
    'fetches': ('data page fetches', lambda r: r.get('Num_data_page_fetches')),
    'ioreads': ('data page I/O reads', lambda r: r.get('Num_data_page_ioreads')),
    'os_read': ('OS read bytes', lambda r: r.get('os_read_bytes')),
    'os_write': ('OS write bytes incl. drain', lambda r: (r.get('os_write_bytes') or 0)
                 + (r.get('drain_os_write_bytes') or 0)),
    'log_writes': ('log page writes incl. drain', lambda r: (r.get('Num_log_page_iowrites') or 0)
                   + (r.get('drain_Num_log_page_iowrites') or 0)),
    'wall': ('wall seconds', lambda r: r.get('wall')),
    'drain_seconds': ('drain seconds', lambda r: r.get('drain_seconds')),
}


def load(run_dir):
    rows = [json.loads(l) for l in open(Path(run_dir) / 'results.jsonl')]
    cells = collections.defaultdict(list)
    failed, evidence = [], []
    for r in rows:
        if r['mode'] == 'evidence':
            evidence.append(r)
        elif r['mode'] == 'error' or 'failed' in r:
            failed.append(r)
        else:
            cells[(r['size'], r['mode'], r['scenario'], r['variant'])].append(r)
    return cells, failed, evidence


def med(cells, key, metric):
    vals = [METRICS[metric][1](r) for r in cells.get(key, [])]
    vals = [v for v in vals if v is not None]
    return statistics.median(vals) if vals else None


def spread(cells, key, metric):
    vals = [METRICS[metric][1](r) for r in cells.get(key, [])]
    vals = [v for v in vals if v]
    if len(vals) < 2:
        return None
    return (max(vals) - min(vals)) / statistics.median(vals)


def human(v, metric):
    if v is None:
        return '-'
    if metric in ('wall', 'drain_seconds'):
        return f'{v:.2f}'
    if metric in ('os_read', 'os_write'):
        return f'{v / 2**20:,.0f} MiB'
    if v >= 1e9:
        return f'{v / 1e9:.2f} G'
    if v >= 1e6:
        return f'{v / 1e6:.1f} M'
    if v >= 1e3:
        return f'{v / 1e3:.1f} k'
    return f'{v:.0f}'


def ratio_table(cells, sizes, mode, metric):
    out = [f'| scenario | ' + ' | '.join(f'{s} B' for s in sizes) + ' |',
           '|---|' + '---|' * len(sizes)]
    for sc in SCEN:
        if mode == 'io' and sc == 'S4':
            continue
        row = [f'{sc} {LABEL[sc]}']
        for s in sizes:
            base = med(cells, (s, mode, sc, 'develop'), metric)
            parts = []
            for v in VARIANTS[1:]:
                x = med(cells, (s, mode, sc, v), metric)
                parts.append('-' if x is None or not base else f'{x / base:.2f}')
            row.append(' / '.join(parts))
        out.append('| ' + ' | '.join(row) + ' |')
    return '\n'.join(out)


def abs_table(cells, size, mode, metric):
    out = ['| scenario | ' + ' | '.join(VARIANTS) + ' |', '|---|' + '---|' * len(VARIANTS)]
    for sc in SCEN:
        if mode == 'io' and sc == 'S4':
            continue
        if not any(cells.get((size, mode, sc, v)) for v in VARIANTS):
            continue
        out.append(f'| {sc} {LABEL[sc]} | ' + ' | '.join(human(med(cells, (size, mode, sc, v), metric), metric)
                                                        for v in VARIANTS) + ' |')
    return '\n'.join(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('run_dir')
    ap.add_argument('--out')
    a = ap.parse_args()
    cells, failed, evidence = load(a.run_dir)
    sizes = sorted({k[0] for k in cells})
    md = [f'# Summary of {a.run_dir}', '',
          'Ratios are OOS / Sidecar / Inner Table divided by develop (median of repeats). Below 1 is better.', '']
    for mode in ('io', 'warm'):
        for metric in ('total_instructions', 'fetches', 'wall'):
            md += [f'## {mode}: {METRICS[metric][0]}, ratio to develop', '', ratio_table(cells, sizes, mode, metric), '']
        if mode == 'io':
            md += [f'## io: {METRICS["os_read"][0]}, ratio to develop', '', ratio_table(cells, sizes, mode, 'os_read'), '']
        md += [f'## {mode}: {METRICS["os_write"][0]}, ratio to develop', '',
               ratio_table(cells, sizes, mode, 'os_write'), '']
    for s in sizes:
        for mode in ('io', 'warm'):
            for metric in ('total_instructions', 'fetches', 'os_read', 'os_write', 'wall'):
                md += [f'### {s} B, {mode}: {METRICS[metric][0]}', '', abs_table(cells, s, mode, metric), '']
    md += ['## Storage', '', '| size | variant | tag | DB bytes |', '|---|---|---|---|']
    for e in evidence:
        md.append(f"| {e['size']} | {e['variant']} | {e['scenario']} | {e['db_bytes'] / 2**20:,.0f} MiB |")
    md += ['', '## Failed statements', '']
    md += [f"- {r['size']} {r['variant']} {r['mode']} {r['scenario']}: {r.get('failed') or r.get('error')}"
           for r in failed] or ['- none']
    # repeat stability of reads
    worst = []
    for k in cells:
        for m in ('instructions', 'wall'):
            sp = spread(cells, k, m)
            if sp is not None:
                worst.append((sp, m, k))
    worst.sort(reverse=True)
    md += ['', '## Largest repeat spread ((max-min)/median)', '']
    md += [f'- {m} {k}: {sp:.2f}' for sp, m, k in worst[:15]]
    text = '\n'.join(md) + '\n'
    if a.out:
        Path(a.out).write_text(text)
    else:
        print(text)


if __name__ == '__main__':
    main()
