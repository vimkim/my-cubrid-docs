#!/usr/bin/env python3
"""Validate whole-process hardware counts and retain instruction-sampled reports."""
import json
import os
from pathlib import Path
import subprocess
from statistics import mean

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'cpu-attribution-20260909'


def validate(label, side):
    report = json.loads((OUT / (label + '.json')).read_text())
    old = json.loads((ROOT / (('baseline' if side == 'a' else 'candidate') + '-diagnostic-final.json')).read_text())
    assert len(report['records']) == 2 and all(r['exit_code'] == 0 for r in report['records'])
    for key in ('source_revision', 'binary_sha256', 'engine_library_sha256', 'test_source_sha256'):
        assert report[key] == old[key], (label, key)
    assert report['cpu_affinity'] == [6]
    samples = [json.loads(line.split(' ', 1)[1]) for line in report['records'][-1]['output'].splitlines()
               if line.startswith('PR7600_SAMPLE ')]
    assert [s['rep'] for s in samples] == list(range(-2, 51))
    assert all(s['rows'] == 1024 for s in samples)
    return report


def main():
    totals = {}
    print('| Workload | Run | User instructions | User cycles |')
    print('|---|---|---:|---:|')
    for workload in ('inline', 'nonpart'):
        totals[workload] = {}
        for run in ('a1', 'b1', 'b2', 'a2'):
            report = validate('perf-' + workload + '-' + run, run[0])
            counters = {}
            for line in report['records'][-1]['output'].splitlines():
                fields = line.split(';')
                if len(fields) > 4 and fields[2] in ('instructions:u', 'cycles:u'):
                    assert float(fields[4]) >= 99.9, 'counter multiplexing requires separate analysis'
                    counters[fields[2]] = int(fields[0])
            assert len(counters) == 2
            totals[workload][run] = counters
            print(f'| {workload} | {run} | {counters["instructions:u"]} | {counters["cycles:u"]} |')
        a = mean(totals[workload][r]['instructions:u'] for r in ('a1', 'a2'))
        b = mean(totals[workload][r]['instructions:u'] for r in ('b1', 'b2'))
        print(f'{workload}: instructions B/A={b/a:.8f}; delta={b-a:.0f}; delta/(53*1024)={(b-a)/(53*1024):.1f}')
    for side in ('a', 'b'):
        report = validate('profile-inline-' + side, side)
        print(report['records'][-1]['output'].split('[  PASSED  ]')[-1])
        command = ['perf', 'report', '-i', report['perf_data'], '--stdio', '--header',
                   '--children', '--no-inline', '-g', 'none', '--sort', 'symbol', '--percent-limit', '0']
        result = subprocess.run(command, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                env=dict(os.environ, DEBUGINFOD_URLS=''), timeout=60, check=True)
        destination = OUT / ('profile-summary-' + side + '.json')
        if destination.exists():
            assert json.loads(destination.read_text())['command'] == command
        else:
            destination.write_text(json.dumps({'command': command, 'output': result.stdout}, indent=2) + '\n')
        for line in result.stdout.splitlines():
            if any(word in line for word in ('Samples:', 'Event count', 'lost', 'partition_prune_insert',
                                             'heap_attrinfo_get_effective_key', 'partition_find_partition',
                                             'locator_attribute_info_force', 'heap_attrinfo_transform_to_disk')):
                print(side, line)


if __name__ == '__main__':
    main()
