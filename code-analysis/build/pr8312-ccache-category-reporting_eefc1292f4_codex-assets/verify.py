import argparse
import collections
import gzip
import json
import os
from pathlib import Path
import random
import re
import subprocess
import tempfile
import textwrap

parser = argparse.ArgumentParser(description='Verify the PR8312 ccache report with synthetic logs.')
parser.add_argument('source_worktree', type=Path)
args = parser.parse_args()
WORKTREE = args.source_worktree.resolve()
source_commit = subprocess.check_output(['git', '-C', str(WORKTREE), 'rev-parse', 'HEAD'], text=True).strip()
if source_commit != 'eefc1292f4e65cb6c505c2965591873e3bf2300f':
    raise SystemExit('The source worktree must be at reviewed commit eefc1292f4e65cb6c505c2965591873e3bf2300f.')
ROOT = Path(tempfile.mkdtemp(prefix='pr8312-ccache-review-'))
workflow = subprocess.check_output(
    ['git', '-C', str(WORKTREE), 'show', source_commit + ':.github/workflows/gha-ci.yml'], text=True)
block = workflow.split('          # Parallel compiles share the log,', 1)[1]
block = '          # Parallel compiles share the log,' + block.split('\n      - name: 4.', 1)[0]
report = textwrap.dedent(block)
(ROOT / 'report.sh').write_text(report)
tally = report.split("tally='\n", 1)[1].split("\n  }'", 1)[0] + '\n  }'
(ROOT / 'tally.awk').write_text(tally)

checks = []

def check(name, condition):
    if not condition:
        raise AssertionError(name)
    checks.append(name)

def record(pid, body):
    return f'[2026-11-02T14:40:49.947000 {pid:<5}] {body}\n'

def run_report(name, log, **overrides):
    directory = ROOT / name
    directory.mkdir(exist_ok=True)
    runner = directory / 'runner'
    runner.mkdir(exist_ok=True)
    shared = directory / 'shared'
    logfile = directory / 'ccache.log'
    if log is not None:
        logfile.write_text(log)
    env = dict(os.environ, CCACHE_LOGFILE=str(logfile), RUNNER_TEMP=str(runner),
               BUILD_LOG_DIR=str(shared / 'runs/123/build/debug'),
               CI_ROOT=str(shared), ARTIFACT_URL_BASE='http://example.invalid')
    env.update({key: str(value) for key, value in overrides.items()})
    completed = subprocess.run(['bash', '--noprofile', '--norc', '-euo', 'pipefail',
                                str(ROOT / 'report.sh')], env=env, capture_output=True, text=True)
    (directory / 'stdout').write_text(completed.stdout)
    (directory / 'stderr').write_text(completed.stderr)
    return completed, Path(env['BUILD_LOG_DIR']) / 'ccache-results.tsv.gz'

events = []
expected = []
paths = [('/workspace/build', '/workspace/src/a.c', 'cache hit (direct)'),
         ('/workspace/build/3rdparty/Build/lib', '../../Source/lib/b.c', 'cache hit (preprocessed)'),
         ('/workspace/build/CMakeFiles/CMakeScratch/TryCompile-abc', 'testCCompiler.c', 'cache miss'),
         ('/workspace/build', '../3rdparty/Source/lz4/lib/lz4.c', 'multiple source files'),
         ('/workspace/build', '/workspace/src/c.c', 'cache file missing')]
for number, (cwd, src, result) in enumerate(paths):
    pid = 21000 + number
    events.append([record(pid, '=== CCACHE 3.7.7 STARTED ==='),
                   record(pid, 'Working directory: ' + cwd),
                   record(pid, 'Source file: ' + src),
                   record(pid, 'Result: ' + result)])
    expected.append(f'{result}\t{cwd}\t{src}')
serial = ''.join(''.join(e) for e in events)
p, artifact = run_report('serial', serial)
check('normal report succeeds', p.returncode == 0)
check('exact aggregate', 'cache hit (direct) 1, cache hit (preprocessed) 1, cache miss 1, cache hit rate 66.67 %' in p.stdout)
check('source direct category', re.search(r'CUBRID source:\s+hit \(direct\) 1, hit \(preprocessed\) 0, miss 0, hit rate 100.00 %', p.stdout))
check('external preprocessed category', re.search(r'external libraries:\s+hit \(direct\) 0, hit \(preprocessed\) 1, miss 0, hit rate 100.00 %', p.stdout))
check('CMake miss category', re.search(r'CMake checks:\s+hit \(direct\) 0, hit \(preprocessed\) 0, miss 1, hit rate 0.00 %', p.stdout))
check('all event kinds in table', collections.Counter(gzip.decompress(artifact.read_bytes()).decode().splitlines()) == collections.Counter(expected))
check('published URL matches artifact', 'http://example.invalid/runs/123/build/debug/ccache-results.tsv.gz' in p.stdout)

rng = random.Random(8312)
for repetition in range(20):
    queues = [list(e) for e in events]
    interleaved = []
    while any(queues):
        index = rng.choice([i for i, queue in enumerate(queues) if queue])
        entry = queues[index].pop(0)
        if rng.choice([True, False]):
            entry = record(31000, 'Command line: gcc ' + ' -DCCACHE_TEST=1' * 400).rstrip('\n') + entry
        interleaved.append(entry)
    p, artifact = run_report(f'interleaved-{repetition}', ''.join(interleaved))
    check(f'interleaved {repetition}: aggregate unchanged', p.returncode == 0 and 'cache hit rate 66.67 %' in p.stdout)
    check(f'interleaved {repetition}: correct event paths', collections.Counter(gzip.decompress(artifact.read_bytes()).decode().splitlines()) == collections.Counter(expected))

pid_reuse = ''.join([record(123, 'Working directory: /workspace/3rdparty/Build/lib'),
                     record(123, 'Source file: a.c'), record(123, 'Result: cache miss'),
                     record(123, '=== CCACHE 3.7.7 STARTED ==='), record(123, 'Result: multiple source files')])
p, artifact = run_report('pid-reuse', pid_reuse)
check('PID reuse clears paths', gzip.decompress(artifact.read_bytes()).decode().splitlines()[-1] == 'multiple source files\t\t')

bad_path = ROOT / 'not-a-directory'
bad_path.write_text('intentionally a regular file')
for name, overrides in [('runner-failure', {'RUNNER_TEMP': bad_path}),
                        ('artifact-dir-failure', {'BUILD_LOG_DIR': bad_path})]:
    p, artifact = run_report(name, serial, **overrides)
    check(f'{name}: nonfatal', p.returncode == 0)
    check(f'{name}: counts retained', 'cache hit rate 66.67 %' in p.stdout)
    check(f'{name}: warning without success link', '::warning::could not write' in p.stdout and 'ccache, per-file results:' not in p.stdout)
for name, log in [('missing-log', None), ('empty-log', ''),
                  ('only-uncacheable', record(123, 'Result: multiple source files'))]:
    p, artifact = run_report(name, log)
    check(f'{name}: nonfatal warning', p.returncode == 0 and '::warning::' in p.stdout)

for name, cwd, src in [('absolute-source', '/workspace/build', '/workspace/3rdparty/Source/lib/a.c'),
                        ('relative-source', '/workspace/build', '../3rdparty/Source/lib/a.c'),
                        ('external-cmake', '/workspace/build/3rdparty/Build/lib/CMakeFiles/CMakeScratch/TryCompile-abc', 'a.c')]:
    log = record(123, 'Working directory: ' + cwd) + record(123, 'Source file: ' + src) + record(123, 'Result: cache miss')
    p, artifact = run_report(name, log)
    check(f'{name}: external classification', p.returncode == 0 and re.search(r'external libraries:\s+hit \(direct\) 0, hit \(preprocessed\) 0, miss 1,', p.stdout))

p, artifact = run_report('missing-metadata', record(123, 'Result: cache miss'))
check('missing metadata defaults to CUBRID without a warning',
      p.returncode == 0 and '::warning::' not in p.stdout
      and re.search(r'CUBRID source:\s+hit \(direct\) 0, hit \(preprocessed\) 0, miss 1,', p.stdout))

syntax = subprocess.run(['bash', '-n', str(ROOT / 'report.sh')], capture_output=True, text=True)
check('bash syntax', syntax.returncode == 0)
lint = subprocess.run(['shellcheck', '-s', 'bash', '-e', 'SC2016', str(ROOT / 'report.sh')], capture_output=True, text=True)
(ROOT / 'shellcheck.txt').write_text(lint.stdout + lint.stderr)
check('shellcheck report fragment', lint.returncode == 0)

summary = {'passed': len(checks), 'checks': checks, 'source_commit': source_commit,
           'shellcheck_suppression': 'SC2016: AWK $0 must remain literal inside the single-quoted tally program',
           'limitation': 'Synthetic ccache 3.7.7-format logs; no CI builds or live artifact server checks'}
(ROOT / 'verification.json').write_text(json.dumps(summary, indent=2) + '\n')
print(json.dumps({'passed': len(checks), 'evidence': str(ROOT / 'verification.json')}))
