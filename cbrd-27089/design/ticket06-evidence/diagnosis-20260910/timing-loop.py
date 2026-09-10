#!/usr/bin/env python3
"""Pinned ABBA/BAAB runtime feedback loop; inconclusive is never a pass."""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import statistics
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
OLD = HERE.parent
RUNNER = OLD.parent / 'ticket01-evidence/run-isolated.py'


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('output', type=Path)
    p.add_argument('--blocks', type=int, default=3)
    p.add_argument('--rows', type=int, default=256)
    p.add_argument('--repetitions', type=int, default=21)
    p.add_argument('--cpu', type=int, default=6)
    args = p.parse_args()
    assert args.blocks >= 2 and args.rows > 0 and args.repetitions > 2
    args.output.mkdir(parents=True, exist_ok=False)
    references = {}
    for side, name in [('a', 'baseline'), ('b', 'candidate')]:
        ref = json.loads((OLD / (name + '-diagnostic-final.json')).read_text())
        for key in ('binary', 'engine_library', 'test_source'):
            assert hashlib.sha256(Path(ref[key]).read_bytes()).hexdigest() == ref[key + '_sha256'], key
        references[side] = ref
    manifest = {'parameters': vars(args) | {'output': str(args.output)},
                'script_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                'references': references, 'runs': [], 'block_results': []}
    for block in range(args.blocks):
        order = 'abba' if block % 2 == 0 else 'baab'
        for workload in (('small_inline', 'nonpartition_small') if block % 2 == 0
                         else ('nonpartition_small', 'small_inline')):
            values = {'a': [], 'b': []}
            for slot, side in enumerate(order):
                label = f'block-{block}-{workload.replace("_", "-")}-{slot}-{side}'
                tree = 'pr7600-original-baseline' if side == 'a' else 'pr7600-measure-candidate'
                cmd = [sys.executable, str(RUNNER), label, '--source', '/home/vimkim/gh/cb/' + tree,
                       '--preset', 'release_gcc', '--binary', 'test_oos_sql_pr7600_measure',
                       '--filter', 'Pr7600Measure.Matrix', '--timeout', '90',
                       '--cpu-affinity', str(args.cpu), '--output-dir', str(args.output)]
                env = dict(os.environ, PR7600_ROWS=str(args.rows),
                           PR7600_REPETITIONS=str(args.repetitions), PR7600_WORKLOAD=workload)
                start = time.time()
                run = subprocess.run(cmd, env=env, capture_output=True, text=True, timeout=100)
                manifest['runs'].append({'label': label, 'command': cmd, 'start': start,
                                         'end': time.time(), 'load': os.getloadavg(),
                                         'exit_code': run.returncode})
                if run.returncode:
                    print(run.stdout + run.stderr)
                    (args.output / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
                    return 2
                record = json.loads((args.output / (label + '.json')).read_text())
                samples = [json.loads(line.split(' ', 1)[1])
                           for r in record['records'] for line in r['output'].splitlines()
                           if line.startswith('PR7600_SAMPLE ')]
                assert len(samples) == args.repetitions + 2
                assert all(s['rows'] == args.rows and s['workload'] == workload for s in samples)
                retained = [s for s in samples if s['rep'] >= 0]
                medians = {m: statistics.median(s[m] for s in retained)
                           for m in ('cpu_seconds', 'elapsed_seconds')}
                values[side].append(medians)
                print(label, medians, flush=True)
            result = {'block': block, 'workload': workload, 'medians': values}
            for metric in ('cpu_seconds', 'elapsed_seconds'):
                a = [s[metric] for s in values['a']]
                b = [s[metric] for s in values['b']]
                result[metric] = {'log_ratio': statistics.mean(map(math.log, b)) - statistics.mean(map(math.log, a)),
                                  'within_side_drift': max(abs(math.log(a[1]/a[0])), abs(math.log(b[1]/b[0])))}
            manifest['block_results'].append(result)
            (args.output / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    verdicts = []
    for metric in ('cpu_seconds', 'elapsed_seconds'):
        rows = manifest['block_results']
        controls = [r[metric] for r in rows if r['workload'] == 'nonpartition_small']
        inline = [r[metric] for r in rows if r['workload'] == 'small_inline']
        noise = max([abs(r['log_ratio']) for r in controls] +
                    [r[metric]['within_side_drift'] for r in rows])
        effects = [r['log_ratio'] for r in inline]
        red = all(effect > noise for effect in effects)
        print(metric, 'RED' if red else 'INCONCLUSIVE',
              'B/A=', [round(math.exp(e), 6) for e in effects], 'noise_factor=', round(math.exp(noise), 6))
        verdicts.append(red)
    manifest['verdict'] = 'RED' if all(verdicts) else 'INCONCLUSIVE'
    (args.output / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    return 1 if all(verdicts) else 2


if __name__ == '__main__':
    sys.exit(main())
