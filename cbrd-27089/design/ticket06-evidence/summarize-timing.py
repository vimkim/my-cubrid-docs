#!/usr/bin/env python3
"""Print per-run medians/MAD from retained validated timing evidence."""
import json
from pathlib import Path
from statistics import median

root = Path(__file__).resolve().parent
names = ('baseline-timing-a1', 'candidate-timing-b1', 'candidate-timing-b2', 'baseline-timing-a2')
series = {}
for name in names:
    report = json.loads((root / (name + '.json')).read_text())
    assert len(report['records']) == 2 and all(r['exit_code'] == 0 for r in report['records'])
    values = {}
    for line in report['records'][1]['output'].splitlines():
        if line.startswith('PR7600_SAMPLE '):
            sample = json.loads(line.removeprefix('PR7600_SAMPLE '))
            if sample['rep'] >= 0:
                values.setdefault(sample['workload'], []).append(sample)
    assert len(values) == 9 and all(len(v) == 9 for v in values.values())
    series[name] = values
print('| Workload | A1 ms (MAD) | B1 ms (MAD) | B2 ms (MAD) | A2 ms (MAD) | Pooled B/A |')
print('|---|---:|---:|---:|---:|---:|')
for workload in series[names[0]]:
    row, combined = [], [[], []]
    for name in names:
        values = [s['elapsed_seconds'] * 1000 for s in series[name][workload]]
        center = median(values)
        row.append(f'{center:.3f} ({median(abs(x-center) for x in values):.3f})')
        combined[name.startswith('candidate')].extend(values)
    print('| ' + workload + ' | ' + ' | '.join(row) + f' | {median(combined[1])/median(combined[0]):.3f} |')

print('\nPinned CPU 6, 1024 statements/sample, 11 samples/run; elapsed median (MAD), ms:')
for workload in ('small-inline', 'nonpartition-small', 'small-forced'):
    row = []
    for run in ('a1', 'b1', 'b2', 'a2'):
        path = root / f'pinned-{run}-{workload}.json'
        if not path.exists():
            row.append('pending')
            continue
        report = json.loads(path.read_text())
        assert all(r['exit_code'] == 0 for r in report['records'])
        values = []
        for line in report['records'][1]['output'].splitlines():
            if line.startswith('PR7600_SAMPLE '):
                sample = json.loads(line.removeprefix('PR7600_SAMPLE '))
                if sample['rep'] >= 0: values.append(sample['elapsed_seconds'] * 1000)
        assert len(values) == 11
        center = median(values)
        row.append(f'{center:.3f} ({median(abs(x-center) for x in values):.3f})')
    print(workload + ': ' + ' / '.join(row))
