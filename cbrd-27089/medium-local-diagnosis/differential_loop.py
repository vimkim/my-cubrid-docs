#!/usr/bin/env python3
"""Drive a fresh native attempt and detect PR7927's exact ordering symptom.

Exit 0: original answers; 1: exact three-case CI signature;
2: another order or an inconclusive setup. This is a diagnostic oracle,
not a replacement for the retained native complete-case verifier.
"""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys

from detect_order import classify


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('side', choices=['head', 'base'])
    parser.add_argument('attempt', type=Path)
    parser.add_argument('--keep-cases', type=Path)
    parser.add_argument('--locale-library', type=Path)
    parser.add_argument('--observe', action='store_true')
    parser.add_argument('--fresh-target-heaps', action='store_true')
    parser.add_argument('--conversion-plans', action='store_true')
    args = parser.parse_args()
    name = 'CBRD-27089-pr7927-value-ref-extraction' if args.side == 'head' else 'pr7927-assessment-base'
    source = Path('/home/vimkim/gh/cb') / name
    install = Path('/home/vimkim/.cub/install') / name / 'debug_gcc'
    env = os.environ.copy()
    java = Path('/home/vimkim/.local/share/mise/installs/java/temurin-8.0.462+8')
    env.update(CUBRID=str(install), CUBRID_DATABASES=str(source / '.cub-workenv/databases'),
               CUBRID_TMP=str(source / '.cub-workenv/tmp'),
               CTP_HOME='/home/vimkim/gh/ctp/run-sql/CTP', JAVA_HOME=str(java))
    env['PATH'] = str(java / 'bin') + ':' + str(install / 'bin') + ':' + env['PATH']
    env['LD_LIBRARY_PATH'] = str(install / 'lib') + ':' + env.get('LD_LIBRARY_PATH', '')
    command = [sys.executable, str(Path(__file__).with_name('replay_medium.py')), 'medium',
               str(args.attempt.resolve()), '--predecessors', '--jdbc-dir',
               '/home/vimkim/.cub/install/pr7927-assessment-base/debug_gcc/jdbc']
    for name in ['keep_cases', 'locale_library']:
        if getattr(args, name):
            command += ['--' + name.replace('_', '-'), str(getattr(args, name).resolve())]
    for name in ['observe', 'fresh_target_heaps', 'conversion_plans']:
        if getattr(args, name):
            command += ['--' + name.replace('_', '-')]
    process = subprocess.run(command, cwd=source, env=env)
    try:
        result = classify(args.attempt.resolve(), Path('/home/vimkim/gh/cubrid-testcases/tc-pr-7927/medium/_02_xtests/answers'))
    except (FileNotFoundError, AssertionError) as error:
        print(f'INCONCLUSIVE: {error}', file=sys.stderr)
        return 2
    result['replay_exit'] = process.returncode
    result['driving_command'] = command
    (args.attempt / 'signature.json').write_text(json.dumps(result, indent=2) + '\n')
    print(result['status'])
    return {'ANSWER_EQUAL': 0, 'CI_SIGNATURE': 1, 'OTHER': 2}[result['status']]


if __name__ == '__main__':
    raise SystemExit(main())
