#!/usr/bin/env python3
"""Run every TLC check of the Sidecar lifecycle model and compare each result with its expectation.

Usage: python3 run.py [--out DIR] [--workers N] [NAME ...]

Prints one line per run: the result (PASS, or FAIL with the violated invariant), the distinct and
generated state counts, the time, and OK or UNEXPECTED against the table below.  TLC output goes to
DIR (default: a new directory under $TMPDIR), never into this directory.  Exit status 1 if any
result differs from its expectation.
"""
import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
SPEC = HERE / 'SidecarLifecycle.tla'
JAR = Path.home() / '.cache/tlaplus/tla2tools-1.7.4.jar'

# cfg name -> expected result: 'PASS' or the invariant expected to fail.
EXPECT = {
    'design_NoDanglingRef': 'PASS',
    'design_NoLostRow': 'PASS',
    'design_Bounded': 'PASS',
    'design_RetryNeedsCommit': 'PASS',
    'design_HeapPathNoRetry': 'PASS',
    'design_NoOrphan': 'PASS',
    'design_OneOwner': 'PASS',
    'design_StoreIdentity': 'PASS',
    'bound_1_two_commits': 'Bounded',
    'bound_3_four_commits': 'Bounded',
    'broken_no_retry': 'NoLostRow',
    'broken_no_dead_row_test': 'Bounded',
    'broken_reuse_no_pin': 'NoDanglingRef',
    'broken_reuse_pin_after': 'NoDanglingRef',
    'broken_delete_no_stamp': 'NoOrphan',
    'broken_delete_no_stamp_OneOwner': 'OneOwner',
    'broken_stamp_after_hot_readers': 'PASS',
    'broken_stamp_after_hot_store': 'PASS',
    'broken_vacuum_uncommitted': 'NoDanglingRef',
    'broken_resolve_after_latch': 'NoDanglingRef',
    'broken_resolve_after_latch_RetryNeedsCommit': 'RetryNeedsCommit',
    'broken_resolve_after_latch_HeapPathNoRetry': 'HeapPathNoRetry',
    'broken_snapshot_unregistered': 'NoDanglingRef',
    'later_reuse_pin_before_NoDanglingRef': 'PASS',
    'later_reuse_pin_before_NoLostRow': 'PASS',
    'later_reuse_pin_before_Bounded': 'PASS',
    'later_reuse_pin_before_NoOrphan': 'PASS',
    'later_reuse_pin_before_OneOwner': 'OneOwner',
    'later_reuse_pin_before_StoreIdentity': 'StoreIdentity',
    'later_reuse_pin_before_no_dead_row': 'NoDanglingRef',
    'fallback_two_commits': 'PASS',
    'fallback_four_commits': 'PASS',
    'broken_fallback_no_lock': 'NoDanglingRef',
    'lazy_design': 'PASS',
    'broken_lazy_across_commit': 'NoDanglingRef',
    'lazy_backstop_only_NoDanglingRef': 'PASS',
    'lazy_backstop_only_NoLazyAfterTranEnd': 'NoLazyAfterTranEnd',
    'lazy_backstop_other_keep': 'NoDanglingRef',
}


def run_one(name, out, workers):
    work = out / name
    work.mkdir(parents=True)
    shutil.copy(SPEC, work)
    shutil.copy(HERE / f'{name}.cfg', work)
    cmd = ['java', '-XX:+UseParallelGC', '-cp', str(JAR), 'tlc2.TLC', '-workers', str(workers),
           '-metadir', str(work / 'meta'), '-config', f'{name}.cfg', 'SidecarLifecycle']
    start = time.monotonic()
    with open(work / 'tlc.out', 'w') as log:
        subprocess.run(cmd, cwd=work, stdout=log, stderr=subprocess.STDOUT)
    secs = time.monotonic() - start
    text = (work / 'tlc.out').read_text()
    gen = re.findall(r'([\d,]+) states generated, ([\d,]+) distinct states found', text)
    distinct, generated = (gen[-1][1], gen[-1][0]) if gen else ('?', '?')
    violated = re.search(r'Invariant (\w+) is violated', text)
    if violated:
        result = violated.group(1)
    elif 'Model checking completed. No error has been found.' in text:
        result = 'PASS'
    else:
        result = 'ERROR'
    return result, distinct, generated, secs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', type=Path)
    ap.add_argument('--workers', type=int, default=min(32, os.cpu_count() or 1))
    ap.add_argument('names', nargs='*')
    args = ap.parse_args()
    if not shutil.which('java') or not JAR.exists():
        sys.exit(f'needs java on PATH and {JAR}')
    out = args.out or Path(tempfile.mkdtemp(prefix='sidecar-lifecycle-'))
    names = args.names or list(EXPECT)
    unexpected = 0
    total = time.monotonic()
    print(f'TLC output: {out}', flush=True)
    for name in names:
        result, distinct, generated, secs = run_one(name, out, args.workers)
        expect = EXPECT[name]
        ok = result == expect
        unexpected += not ok
        shown = 'PASS' if result == 'PASS' else ('ERROR' if result == 'ERROR' else f'FAIL {result}')
        print(f'{shown:<20} {name:<38} distinct={distinct:>12} generated={generated:>12} '
              f'{secs:7.1f}s  {"OK" if ok else "UNEXPECTED, expected " + expect}', flush=True)
    print(f'{len(names)} runs, {unexpected} unexpected, {time.monotonic() - total:.0f}s')
    sys.exit(1 if unexpected else 0)


if __name__ == '__main__':
    main()
