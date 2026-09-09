#!/usr/bin/env python3
"""Validate all planned runs and compare process medians within balanced blocks."""
import hashlib
import json
import math
from pathlib import Path
from statistics import median

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'interleaved-20260909'


def geometric(values):
    return math.exp(sum(math.log(x) for x in values) / len(values))


def main():
    manifest = json.loads((OUT / 'manifest.json').read_text())
    assert len(manifest['runs']) == len(manifest['plan']) == 52
    assert manifest['script_sha256'] == hashlib.sha256((ROOT / 'repeat-interleaved.py').read_bytes()).hexdigest()
    samples = {}
    for planned, execution in zip(manifest['plan'], manifest['runs']):
        label, side, workload, rows, repetitions = planned
        assert execution['label'] == label and execution['exit_code'] == 0
        report = json.loads((OUT / (label + '.json')).read_text())
        assert report['cpu_affinity'] == [6]
        assert len(report['records']) == 2 and all(r['exit_code'] == 0 for r in report['records'])
        old = json.loads((ROOT / (('baseline' if side == 'a' else 'candidate') + '-diagnostic-final.json')).read_text())
        for field in ('binary_sha256', 'engine_library_sha256', 'test_source_sha256', 'source_revision'):
            assert report[field] == old[field], (label, field)
        grouped = {}
        for line in report['records'][1]['output'].splitlines():
            if line.startswith('PR7600_SAMPLE '):
                sample = json.loads(line[len('PR7600_SAMPLE '):])
                assert sample['rows'] == rows
                grouped.setdefault(sample['workload'], []).append(sample)
        assert len(grouped) == (1 if workload else 9)
        if workload:
            assert list(grouped) == [workload]
        for name, values in grouped.items():
            assert [s['rep'] for s in values] == list(range(-2, repetitions))
            for metric in ('cpu_seconds', 'elapsed_seconds'):
                points = [s[metric] for s in values if s['rep'] >= 0]
                assert all(x > 0 and math.isfinite(x) for x in points)
                center = median(points)
                samples.setdefault(name, {}).setdefault(metric, {})[label] = {
                    'median': center, 'mad': median(abs(x - center) for x in points)}
    print('All 52 process runs passed; expected samples, affinity and binary provenance verified.')
    for metric in ('cpu_seconds', 'elapsed_seconds'):
        print('\n' + metric)
        print('| Control | Block 0 B/A | Block 1 B/A | Block 2 B/A | Block 3 B/A | Geomean B/A |')
        print('|---|---:|---:|---:|---:|---:|')
        for workload in ('small_inline', 'nonpartition_small', 'small_forced'):
            ratios = []
            for block in range(4):
                prefix = f'control-{block}-{workload.replace("_", "-")}-'
                sides = {side: [v['median'] for label, v in samples[workload][metric].items()
                                if label.startswith(prefix) and label.endswith(side)] for side in 'ab'}
                assert all(len(v) == 2 for v in sides.values())
                ratios.append(geometric(sides['b']) / geometric(sides['a']))
            print('| ' + workload + ' | ' + ' | '.join(f'{r:.4f}' for r in ratios)
                  + f' | {geometric(ratios):.4f} |')
        print('\n| Matrix workload | A1 ms (MAD) | B1 ms (MAD) | B2 ms (MAD) | A2 ms (MAD) |')
        print('|---|---:|---:|---:|---:|')
        for workload, metrics in samples.items():
            values = [metrics[metric][f'matrix-{slot}-{side}'] for slot, side in enumerate('abba')]
            print('| ' + workload + ' | ' + ' | '.join(
                f'{v["median"]*1000:.3f} ({v["mad"]*1000:.3f})' for v in values) + ' |')
    print('\nLoad average (1 minute), before/after all processes:',
          min(r[k][0] for r in manifest['runs'] for k in ('load_before', 'load_after')),
          max(r[k][0] for r in manifest['runs'] for k in ('load_before', 'load_after')))
    print('Process wall seconds:', manifest['runs'][-1]['end'] - manifest['runs'][0]['start'])


if __name__ == '__main__':
    main()
