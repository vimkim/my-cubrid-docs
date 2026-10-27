#!/usr/bin/env python3
"""Balanced, serial read-order controls. Raw trials stay outside the repository."""
import argparse
import itertools
import json
from pathlib import Path
import statistics
import subprocess
import sys


def summarize(results):
    groups = {}
    for mode in ['normal', 'random', 'direct', 'warm']:
        for policy in ['captured', 'defer', 'sorted']:
            selected = [r for r in results if r['mode'] == mode and r['schedule'] == policy]
            if not selected:
                continue
            times = [r['elapsed_seconds'] for r in selected]
            groups[f'{mode}/{policy}'] = {
                'n': len(selected), 'median_seconds': statistics.median(times),
                'min_seconds': min(times), 'max_seconds': max(times),
                'median_cpu_seconds': statistics.median(r['cpu_seconds'] for r in selected),
                'median_read_bytes': statistics.median(r['read_bytes'] for r in selected),
                'median_voluntary_switches': statistics.median(r['voluntary_switches'] for r in selected),
                'median_resident_after_bytes': statistics.median(r['resident_after_measurement_bytes'] for r in selected)}
    return groups


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--probe', type=Path, required=True)
    parser.add_argument('--repeats', type=int, default=6)
    parser.add_argument('--cpu', type=int, default=16)
    args = parser.parse_args()
    if args.repeats < 1:
        parser.error('positive repeat count required')
    args.output.mkdir(parents=True, exist_ok=False)
    driver = Path(__file__).resolve().with_name('read_order_experiment.py')
    modes = ['normal', 'random', 'direct', 'warm']
    permutations = list(itertools.permutations(['captured', 'defer', 'sorted']))
    results = []
    cases = []
    for repeat in range(args.repeats):
        for mode in modes[repeat % 4:] + modes[:repeat % 4]:
            for policy in permutations[(repeat + modes.index(mode)) % len(permutations)]:
                cases.append({'round': repeat + 1, 'mode': mode, 'schedule': policy})
    (args.output / 'schedule.json').write_text(json.dumps(cases, indent=2) + '\n')
    for number, case in enumerate(cases, 1):
        output = args.output / f"r{case['round']}-{case['mode']}-{case['schedule']}"
        cmd = [sys.executable, '-B', str(driver), '--manifest', str(args.manifest.resolve()),
               '--output', str(output), '--probe', str(args.probe.resolve()), '--mode', case['mode'],
               '--schedule', case['schedule'], '--cpu', str(args.cpu)]
        trial = subprocess.run(cmd, capture_output=True, text=True)
        if trial.returncode:
            print(trial.stdout, trial.stderr, flush=True)
            raise SystemExit(trial.returncode)
        result = json.loads((output / 'result.json').read_text())
        result['round'] = case['round']
        results.append(result)
        for field in ['requests', 'requested_bytes', 'checksum', 'selected_page_multiset_sha256',
                      'manifest_sha256', 'trace_sha256', 'probe_sha256', 'driver_sha256']:
            assert len({r[field] for r in results}) == 1, field
        with (args.output / 'progress.jsonl').open('a') as file:
            file.write(json.dumps(result) + '\n')
        print(f"{number}/{len(cases)} r{case['round']} {case['mode']}/{case['schedule']}: "
              f"{result['elapsed_seconds']:.4f}s cpu={result['cpu_seconds']:.4f}s "
              f"read={result['read_bytes']} cached_after={result['resident_after_measurement_bytes']}", flush=True)
        (args.output / 'summary.json').write_text(json.dumps(summarize(results), indent=2) + '\n')
    print(json.dumps(summarize(results), indent=2), flush=True)


if __name__ == '__main__':
    main()
