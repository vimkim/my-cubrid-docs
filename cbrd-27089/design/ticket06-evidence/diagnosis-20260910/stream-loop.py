#!/usr/bin/env python3
"""Alternate live, pinned baseline/candidate batches; retain every timed sample."""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import queue
import random
import shutil
import signal
import statistics
import subprocess
import sys
import tempfile
import threading
import time

HERE = Path(__file__).resolve().parent
TREES = {'a': 'pr7600-original-baseline', 'b': 'pr7600-measure-candidate'}


def digest(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def git(tree, *args):
    return subprocess.check_output(['git', '-C', str(tree), *args], text=True)


class Worker:
    def __init__(self, label, side, workload, args):
        self.label = label
        self.log = []
        self.samples = []
        self.proc = None
        selected = 'a' if args.aa else side
        name = args.baseline if selected == 'a' else args.candidate
        tree = Path('/home/vimkim/gh/cb') / name
        install = Path('/home/vimkim/.cub/install') / name / 'release_gcc'
        self.fixture = args.fixtures / label
        self.fixture.mkdir(parents=True, exist_ok=True)
        runtime = self.fixture / 'install'
        if not runtime.exists():
            runtime.mkdir()
            for item in install.iterdir():
                if item.name == 'conf':
                    shutil.copytree(item, runtime / item.name)
                elif item.is_dir() and item.name in ('log', 'var', 'tmp', 'databases'):
                    (runtime / item.name).mkdir()
                else:
                    (runtime / item.name).symlink_to(item, target_is_directory=item.is_dir())
        assert (runtime / 'lib').resolve() == (install / 'lib').resolve()
        db = self.fixture / 'databases'
        db.mkdir(exist_ok=True)
        env = dict(os.environ, CUBRID=str(runtime), CUBRID_DATABASES=str(db),
                   PR7600_STREAM='1', PR7600_ROWS=str(args.rows),
                   PR7600_REPETITIONS='1000000', PR7600_WORKLOAD=workload)
        env['PATH'] = str(runtime / 'bin') + ':' + env.get('PATH', '')
        env['LD_LIBRARY_PATH'] = str(runtime / 'lib') + ':' + env.get('LD_LIBRARY_PATH', '')
        setup = ['bash', str(tree / 'unit_tests/oos/scripts/setup_unittestdb.sh')]
        r = subprocess.run(setup, env=env, cwd=self.fixture, capture_output=True, text=True, timeout=60)
        self.log.append(r.stdout + r.stderr)
        assert r.returncode == 0, self.log
        binary = tree / 'build_preset_release_gcc/bin' / args.binary
        library = install / 'lib/libcubridsa.so.11.5'
        self.provenance = {'label': label, 'side': side, 'workload': workload,
                           'source': str(tree), 'head': git(tree, 'rev-parse', 'HEAD').strip(),
                           'source_status': git(tree, 'status', '--short'),
                           'engine_diff': git(tree, 'diff', 'HEAD', '--', 'src'),
                           'cci': git(tree, 'submodule', 'status', 'cubrid-cci').strip(),
                           'binary': str(binary), 'binary_sha256': digest(binary),
                           'library': str(library), 'library_sha256': digest(library),
                           'harness_sha256': digest(tree / 'unit_tests/oos/sql' / (args.binary + '.cpp')),
                           'fixture': str(self.fixture), 'setup': setup,
                           'cache_sha256': digest(tree / 'build_preset_release_gcc/CMakeCache.txt')}
        cmd = [str(binary), '--gtest_filter=Pr7600Measure.Matrix',
               '--gtest_output=xml:' + str(args.output / (label + '.xml'))]
        if args.no_aslr:
            cmd = ['setarch', 'x86_64', '-R'] + cmd
        self.provenance['command'] = cmd
        self.proc = subprocess.Popen(cmd, env=env, cwd=self.fixture, stdin=subprocess.PIPE,
                                     stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                     text=True, bufsize=1, start_new_session=True)
        self.lines = queue.Queue()
        def read():
            for line in self.proc.stdout:
                self.lines.put(line)
            self.lines.put(None)
        self.reader = threading.Thread(target=read, daemon=True)
        self.reader.start()
        try:
            self.until('PR7600_READY')
            self.provenance['engine_mapping'] = [line for line in Path(f'/proc/{self.proc.pid}/maps').read_text().splitlines()
                                                 if 'libcubridsa' in line]
            assert self.provenance['engine_mapping']
            assert all(line.endswith(str(library.resolve())) for line in self.provenance['engine_mapping'])
        except BaseException:
            if self.proc.poll() is None:
                os.killpg(self.proc.pid, signal.SIGKILL)
                self.proc.wait()
            raise

    def until(self, marker):
        while True:
            line = self.lines.get(timeout=60)
            if line is None:
                raise RuntimeError(f'{self.label} ended unexpectedly: {self.log[-15:]}')
            self.log.append(line)
            if line.startswith('PR7600_SAMPLE '):
                self.samples.append(json.loads(line.split(' ', 1)[1]))
            if line.strip() == marker:
                return

    def batch(self):
        n = len(self.samples)
        self.proc.stdin.write('g')
        self.proc.stdin.flush()
        self.until('PR7600_DONE')
        self.until('PR7600_READY')
        assert len(self.samples) == n + 1
        return self.samples[-1]

    def close(self):
        if self.proc is not None and self.proc.poll() is None:
            self.proc.stdin.write('q')
            self.proc.stdin.flush()
            self.proc.wait(timeout=60)
            self.reader.join(timeout=3)
            while not self.lines.empty():
                line = self.lines.get()
                if line is not None:
                    self.log.append(line)
            assert self.proc.returncode == 0, self.log[-20:]


def interval(values):
    # Resample four consecutive ABBA/BAAB blocks as one unit, preserving short-term drift.
    groups = [statistics.mean(values[i:i+4]) for i in range(0, len(values), 4)]
    rng = random.Random(7600)
    boot = sorted(statistics.mean(rng.choices(groups, k=len(groups))) for _ in range(10000))
    return [math.exp(statistics.mean(values)), math.exp(boot[50]), math.exp(boot[9949])]


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('output', type=Path)
    p.add_argument('--fixtures', type=Path, required=True)
    p.add_argument('--cpu', type=int, default=6)
    p.add_argument('--rows', type=int, default=256)
    p.add_argument('--blocks', type=int, default=48)
    p.add_argument('--aa', action='store_true', help='negative control: both sides use baseline')
    p.add_argument('--no-aslr', action='store_true', help='disable ASLR only for the owned test processes')
    p.add_argument('--calibration', type=Path, help='previous matching A/A manifest; required for calibrated verdict')
    p.add_argument('--baseline', default=TREES['a'], help='measurement worktree basename')
    p.add_argument('--candidate', default=TREES['b'], help='measurement worktree basename')
    p.add_argument('--binary', choices=('test_oos_sql_pr7600_stream', 'test_oos_sql_pr7600_minimal',
                                       'test_oos_sql_pr7600_no_payload'),
                   default='test_oos_sql_pr7600_stream')
    args = p.parse_args()
    assert args.blocks >= 16 and args.blocks % 4 == 0 and args.rows > 0
    args.output = args.output.resolve()
    args.fixtures = args.fixtures.resolve()
    args.output.mkdir(parents=True, exist_ok=False)
    assert args.cpu in os.sched_getaffinity(0)
    os.sched_setaffinity(0, {args.cpu})
    calibration = None
    if args.calibration:
        calibration = json.loads(args.calibration.read_text())
        assert calibration['args']['aa'] and not args.aa
        for key in ('cpu', 'rows', 'blocks', 'no_aslr'):
            assert calibration['args'][key] == getattr(args, key), key
        assert calibration['args'].get('baseline', TREES['a']) == args.baseline
        assert calibration['args'].get('binary', 'test_oos_sql_pr7600_stream') == args.binary
    manifest = {'args': vars(args) | {'output': str(args.output), 'fixtures': str(args.fixtures),
                                     'calibration': str(args.calibration) if args.calibration else None},
                'runner_sha256': digest(__file__), 'started': time.time(),
                'load_before': os.getloadavg(), 'observations': []}
    workers = {}
    try:
        for workload in ('small_inline', 'nonpartition_small'):
            for side in 'ab':
                key = side + '-' + workload
                workers[key] = Worker(key, side, workload, args)
                if calibration and side == 'a':
                    old = json.loads((args.calibration.parent / (key + '.json')).read_text())['provenance']
                    for field in ('library_sha256', 'binary_sha256', 'harness_sha256', 'cci'):
                        assert old[field] == workers[key].provenance[field], 'calibration provenance changed: ' + field
        for _ in range(4):
            for w in workers.values():
                w.batch()
        start = time.monotonic()
        for block in range(args.blocks):
            order = 'abba' if block % 2 == 0 else 'baab'
            workloads = ('small_inline', 'nonpartition_small')
            if block % 2: workloads = workloads[::-1]
            for workload in workloads:
                obs = {'block': block, 'workload': workload, 'order': order, 'sides': {'a': [], 'b': []}}
                for side in order:
                    obs['sides'][side].append(workers[side + '-' + workload].batch())
                for metric in ('cpu_seconds', 'elapsed_seconds'):
                    obs[metric] = (statistics.mean(math.log(s[metric]) for s in obs['sides']['b']) -
                                   statistics.mean(math.log(s[metric]) for s in obs['sides']['a']))
                manifest['observations'].append(obs)
            if block % 8 == 7: print('completed blocks:', block + 1, flush=True)
        manifest['measurement_loop_seconds'] = time.monotonic() - start
        stats = {}
        red = True
        green = True
        for metric in ('cpu_seconds', 'elapsed_seconds'):
            inline = [o[metric] for o in manifest['observations'] if o['workload'] == 'small_inline']
            control = [o[metric] for o in manifest['observations'] if o['workload'] == 'nonpartition_small']
            stats[metric] = {'inline': interval(inline), 'nonpartitioned': interval(control),
                             'adjusted': interval([a-b for a,b in zip(inline,control)])}
            # Raw elapsed/CPU regression is the symptom. A shared slowdown in the
            # nonpartitioned workload is a separate observation, not automatically noise.
            st = stats[metric]
            if calibration:
                noise = calibration['statistics'][metric]['inline']
                # Identical processes can have a persistent side bias. Include its
                # full confidence envelope as symmetric noise; never select only
                # the A/A runs whose confidence interval happens to contain 1.
                factor = max(noise[2], 1 / noise[1], 1)
                st['calibration_noise_factor'] = factor
                red &= st['inline'][1] > factor
                green &= st['inline'][2] <= factor and st['inline'][1] >= 1 / factor
            else:
                red = False
                green = False
        manifest['statistics'] = stats
        manifest['verdict'] = 'RED' if red else ('GREEN_WITHIN_AA_RESOLUTION' if green else 'INCONCLUSIVE')
        for w in workers.values(): w.close()
        print(json.dumps({'verdict': manifest['verdict'], 'statistics': stats,
                          'measurement_loop_seconds': manifest['measurement_loop_seconds']}, indent=2), flush=True)
        return 1 if red else (0 if green else 2)
    finally:
        for key, w in workers.items():
            if w.proc is not None and w.proc.poll() is None:
                os.killpg(w.proc.pid, signal.SIGKILL)
                w.proc.wait()
            record = {'provenance': w.provenance, 'samples': w.samples, 'output': ''.join(w.log),
                      'exit_code': w.proc.returncode if w.proc else None}
            (args.output / (key + '.json')).write_text(json.dumps(record, indent=2) + '\n')
        manifest['ended'] = time.time()
        manifest['load_after'] = os.getloadavg()
        (args.output / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')


if __name__ == '__main__':
    sys.exit(main())
