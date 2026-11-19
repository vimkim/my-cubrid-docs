"""Aggregate CBRD-28062 sweep samples. Change = (base - X) / base; + is better, - is worse.

usage: summarize.py [ROOT] > summary.json
Every group keeps the per-sample values, so a reader can recompute medians and spreads.
"""
import json, statistics, sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(sys.argv[1] if len(sys.argv) > 1 else '/mnt/nvme/data-5/tmp/CBRD-28062-perf-sweep')
LABELS = ('base', 't0', 't5000', 't7000', 't10500', 't14500', 't16236')


def stats(values):
    m = statistics.median(values)
    return {'median': m, 'n': len(values), 'min': min(values), 'max': max(values),
            'spread_pct': (max(values) - min(values)) / m * 100 if m else 0.0, 'values': values}


def sample_values(s):
    c = s['counters']
    for name in ('instructions:u', 'cycles:u'):
        if c[name]['running_percent'] < 95: raise ValueError('multiplexed counter')
    out = {'instructions': c['instructions:u']['value'], 'cycles': c['cycles:u']['value'], 'elapsed': s['elapsed_seconds']}
    if 'trace' in s: out.update(fetch=s['trace']['fetch'], ioread=s['trace']['ioread'])
    if 'server_io_delta' in s: out.update(read_bytes=s['server_io_delta']['read_bytes'], write_bytes=s['server_io_delta']['write_bytes'])
    return out


def collect():
    groups = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
    rounds = defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: defaultdict(list))))
    for unit in sorted((ROOT / 'cpu').glob('r*-*')):
        rnd, label = unit.name[1:].split('-', 1)
        for kind in ('sweep', 'ordinary', 'dml'):
            m = json.loads((unit / kind / 'summary.json').read_text())
            if not m['complete']: raise ValueError(f'incomplete {unit}/{kind}')
            for s in m['samples']:
                if s['warmup']: continue
                key = (kind, s.get('table', 'n200k'), s['case'])
                for metric, v in sample_values(s).items():
                    groups[key][label][metric].append(v); rounds[key][label][rnd][metric].append(v)
    for unit in sorted((ROOT / 'insert').glob('r*-*')):  # extra INSERT-only repeats join the dml INSERT groups
        rnd, label = unit.name[1:].split('-', 1)
        m = json.loads((unit / 'dml' / 'summary.json').read_text())
        if not m['complete']: raise ValueError(f'incomplete {unit}')
        for s in m['samples']:
            if s['warmup']: continue
            key = ('dml', s['table'], s['case'])
            for metric, v in sample_values(s).items():
                groups[key][label][metric].append(v); rounds[key][label][rnd][metric].append(v)
    for unit in sorted((ROOT / 'cold').glob('r*-*')):
        rnd, label = unit.name[1:].split('-', 1)
        for f in sorted(unit.glob('*/summary.json')):
            m = json.loads(f.read_text())
            if not m['complete']: raise ValueError(f'incomplete {f}')
            for s in m['samples']:
                key = ('cold', s['table'], s['case'])
                for metric, v in sample_values(s).items():
                    groups[key][label][metric].append(v); rounds[key][label][rnd][metric].append(v)
    for f in sorted((ROOT / 'io' / 'samples').glob('*/sample.json')):
        s = json.loads(f.read_text())
        if not s['complete'] or s['warmup']: continue
        key = ('io', s['layout'], s['case'])
        v = sample_values({'counters': s['counters'], 'elapsed_seconds': s['elapsed_seconds'], 'trace': s['trace'],
                           'server_io_delta': s['server_io_delta']})
        for metric, x in v.items(): groups[key][s['label']][metric].append(x)
    return groups, rounds


def main():
    groups, rounds = collect()
    out = []
    for key in sorted(groups):
        by = groups[key]
        row = {'key': list(key), 'labels': {}}
        for label in LABELS:
            if label not in by: continue
            row['labels'][label] = {metric: stats(vals) for metric, vals in by[label].items()}
        if 'base' in row['labels']:
            for label, metrics in row['labels'].items():
                for metric, st in metrics.items():
                    b = row['labels']['base'].get(metric)
                    st['change_pct_vs_base'] = (b['median'] - st['median']) / b['median'] * 100 if b and b['median'] else None
                    if label != 'base' and key[0] != 'io' and key in rounds and label in rounds[key]:
                        pr = {r: statistics.median(v[metric]) for r, v in rounds[key][label].items() if metric in v}
                        pb = {r: statistics.median(v[metric]) for r, v in rounds[key]['base'].items() if metric in v}
                        st['change_pct_vs_base_by_round'] = {r: (pb[r] - pr[r]) / pb[r] * 100 for r in pr if r in pb and pb[r]}
        out.append(row)
    json.dump(out, sys.stdout, indent=1)


if __name__ == '__main__':
    main()
