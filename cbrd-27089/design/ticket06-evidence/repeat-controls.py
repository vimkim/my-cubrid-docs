#!/usr/bin/env python3
"""Sequential pinned-CPU ABBA repetitions of suspected small-row regressions."""
import os
from pathlib import Path
import subprocess
import sys

root = Path(__file__).resolve().parent
runner = root.parent / 'ticket01-evidence/run-isolated.py'
scratch = '/home/vimkim/gh/cb/CBRD-27089-has-oos-but-no-oos/.artifacts/pr7600-independent-RjRhFS'
for round_name, tree in [('a1', 'pr7600-original-baseline'), ('b1', 'pr7600-measure-candidate'),
                         ('b2', 'pr7600-measure-candidate'), ('a2', 'pr7600-original-baseline')]:
    for workload in ('small_inline', 'nonpartition_small', 'small_forced'):
        label = 'pinned-' + round_name + '-' + workload.replace('_', '-')
        env = dict(os.environ, PR7600_ROWS='1024', PR7600_REPETITIONS='11', PR7600_WORKLOAD=workload)
        subprocess.run([sys.executable, str(runner), label, '--source', '/home/vimkim/gh/cb/' + tree,
                        '--preset', 'release_gcc', '--binary', 'test_oos_sql_pr7600_measure',
                        '--filter', 'Pr7600Measure.Matrix', '--timeout', '600', '--cpu-affinity', '6',
                        '--scratch-root', scratch, '--output-dir', str(root)], env=env, check=True)
