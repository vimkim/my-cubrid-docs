"""Aggregate CBRD-27788 re-measurement samples. Change = (base - X) / base; + is better, - is worse."""
import json, statistics, sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent
LABELS = ('base', 'head', 'thr')
METRICS = ('instructions:u', 'cycles:u')


def stats(values):
    m = statistics.median(values)
    return {'median': m, 'n': len(values), 'min': min(values), 'max': max(values),
            'spread_pct': (max(values) - min(values)) / m * 100 if m else 0.0}


def change(base, other):
    return (base - other) / base * 100


def compare(groups):
    rows = []
    for key in sorted(groups):
        by = groups[key]
        if 'base' not in by: continue
        row = {'key': list(key)}
        for metric in METRICS + ('elapsed',):
            row[metric] = {label: stats(by[label][metric]) for label in LABELS if label in by}
            b = row[metric]['base']['median']
            row[metric]['change_pct'] = {label: change(b, row[metric][label]['median']) for label in LABELS
                                         if label != 'base' and label in by}
        for extra in ('fetch', 'ioread', 'read_bytes'):
            if all(extra in by[label] for label in by):
                row[extra] = {label: statistics.median(by[label][extra]) for label in by}
        rows.append(row)
    return rows


def add(groups, key, label, sample, elapsed, extra=None):
    g = groups[key].setdefault(label, defaultdict(list))
    for metric in METRICS:
        c = sample['counters'][metric]
        if c['running_percent'] < 95: raise ValueError(f'perf running {c["running_percent"]} {key} {label}')
        g[metric].append(c['value'])
    g['elapsed'].append(elapsed)
    for k, v in (extra or {}).items(): g[k].append(v)


def io():
    groups = defaultdict(dict)
    for f in sorted((ROOT / 'samples').glob('*/sample.json')):
        s = json.loads(f.read_text())
        if s['warmup'] or not s['complete']: continue
        add(groups, (s['cache'], s['layout'], s['case']), s['label'], s, s['elapsed_seconds'],
            {'fetch': s['trace']['fetch'], 'ioread': s['trace']['ioread'], 'read_bytes': s['server_io_delta']['read_bytes']})
    return compare(groups)


def cpu():
    groups = defaultdict(dict)
    per_start = defaultdict(dict)
    for run in sorted((ROOT / 'cpu').glob('cpu-r*-*')):
        label = run.name.rsplit('-', 1)[1]
        for kind in ('sweep', 'ordinary'):
            m = json.loads((run / kind / 'summary.json').read_text())
            if not m['complete']: raise ValueError(f'incomplete {run}/{kind}')
            for s in m['samples']:
                if s['warmup']: continue
                key = (kind, s.get('table', 'n200k'), s['case'])
                add(groups, key, label, s, s['elapsed_seconds'])
                add(per_start, key + (run.name.split('-')[1],), label, s, s['elapsed_seconds'])
    return compare(groups), compare(per_start)


if __name__ == '__main__':
    out = {}
    section = sys.argv[1] if len(sys.argv) > 1 else 'all'
    if section in ('all', 'io'): out['io'] = io()
    if section in ('all', 'cpu'): out['cpu'], out['cpu_per_start'] = cpu()
    json.dump(out, sys.stdout, indent=1)
