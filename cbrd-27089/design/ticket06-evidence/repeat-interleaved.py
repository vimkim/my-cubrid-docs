#!/usr/bin/env python3
"""Fixed, balanced same-host timing plan; no engine or shared database changes."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parent
RUNNER = ROOT.parent / 'ticket01-evidence/run-isolated.py'
TREES = {'a': 'pr7600-original-baseline', 'b': 'pr7600-measure-candidate'}
OUT = ROOT / 'interleaved-20260909'
SCRATCH = '/home/vimkim/gh/cb/CBRD-27089-has-oos-but-no-oos/.artifacts/pr7600-independent-RjRhFS'


def main():
    OUT.mkdir(exist_ok=False)
    plan = []
    controls = ('small_inline', 'nonpartition_small', 'small_forced')
    for block, order in enumerate(('abba', 'baab', 'abba', 'baab')):
        for workload in controls[block % 3:] + controls[:block % 3]:
            for slot, side in enumerate(order):
                plan.append((f'control-{block}-{workload.replace("_", "-")}-{slot}-{side}',
                             side, workload, 1024, 11))
    for slot, side in enumerate('abba'):
        plan.append((f'matrix-{slot}-{side}', side, '', 128, 9))
    manifest = {'script_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                'cpu': 6, 'plan': plan, 'runs': []}
    for label, side, workload, rows, repetitions in plan:
        # Refuse stale/different binaries before accepting any timing evidence.
        reference = ('baseline' if side == 'a' else 'candidate') + '-diagnostic-final.json'
        old = json.loads((ROOT / reference).read_text())
        for field in ('binary', 'engine_library', 'test_source'):
            assert hashlib.sha256(Path(old[field]).read_bytes()).hexdigest() == old[field + '_sha256'], field
        env = dict(os.environ, PR7600_ROWS=str(rows), PR7600_REPETITIONS=str(repetitions))
        env.pop('PR7600_WORKLOAD', None)
        if workload:
            env['PR7600_WORKLOAD'] = workload
        command = [sys.executable, str(RUNNER), label, '--source', '/home/vimkim/gh/cb/' + TREES[side],
                   '--preset', 'release_gcc', '--binary', 'test_oos_sql_pr7600_measure',
                   '--filter', 'Pr7600Measure.Matrix', '--timeout', '600', '--cpu-affinity', '6',
                   '--scratch-root', SCRATCH, '--output-dir', str(OUT)]
        start = time.time()
        before = os.getloadavg()
        result = subprocess.run(command, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        manifest['runs'].append({'label': label, 'command': command, 'start': start, 'end': time.time(),
                                 'load_before': before, 'load_after': os.getloadavg(),
                                 'exit_code': result.returncode, 'output': result.stdout})
        (OUT / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
        print(f'{len(manifest["runs"])}/{len(plan)} {label}: exit {result.returncode}', flush=True)
        if result.returncode:
            print(result.stdout, flush=True)
            raise SystemExit(result.returncode)


if __name__ == '__main__':
    main()
