#!/usr/bin/env python3
"""CBRD-28077 supplementary run: repeated, cross-checked, concurrent measurements.

Reuses the instance helpers of oosbench.py (run 1) and changes the procedure:

  * five builds: run 1's four plus develop e64a04a79 (the develop base of Sidecar), to measure how much
    the develop revisions differ from each other
  * one driver process per build, all started together, so every build sees the same background load
  * repeats: reads 3x (io) and 5x (warm); every mutation 3x per mode, each repeat on rows that no other
    repeat touches, so repeats are comparable without reloading the table
  * a result digest for every read and a table checksum after every phase, compared across builds
  * a 4 KB value: the row just exceeds the move-out threshold (develop keeps three rows per page)
  * S11/S12: eight concurrent clients (big-value UPDATE+COMMIT, big-value INSERT+COMMIT)

Usage: python3 oosbench2.py --root DIR --tag TAG --variant NAME [--sizes ...] [--quick]
"""

import argparse
import hashlib
import json
import os
import random
import re
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import oosbench as b  # noqa: E402

b.VARIANTS['develop-e64a'] = {'worktree': b.CB / 'b28077-develop-e64a', 'conf': {}}
SHORT = {'develop': 'dv', 'develop-e64a': 'de', 'oos': 'os', 'sidecar': 'sc', 'inner': 'in'}
ROWS = {100: 200_000, 4096: 80_000, 8192: 40_000, 65536: 6_000}
IO_READ_REPS, WARM_READ_REPS, MUT_REPS = 3, 3, 3
LOOPS = 600
HOT = 100
CLIENTS, CLIENT_LOOPS = 8, 250
SEED = 280772
CHECKSUM = "select count(*), sum(cast(k as bigint)), sum(cast(id as bigint)), sum(cast(bit_length(big) as bigint)) from t;\n"


def digest(out):
    """Hash of the result lines of csql output, without timing lines."""
    lines = [l.strip() for l in out.splitlines()
             if l.strip() and 'sec)' not in l and not l.startswith('===') and 'Line' not in l]
    return hashlib.sha1('\n'.join(lines).encode()).hexdigest()[:12]


class Inst(b.Instance):
    def create(self, size):
        self.size = size
        self.db = f'b{SHORT[self.name]}{size}'
        self.dir = self.run_dir / f'{size}' / self.name
        self.dir.mkdir(parents=True, exist_ok=True)
        text = self.conf.read_text()
        cut = text.find('\n[@b')
        self.conf_backup = text[:cut].rstrip('\n') + '\n' if cut >= 0 else text
        self.sh(['cubrid', 'service', 'start'], check=False)
        self.sh(['cubrid', 'server', 'stop', self.db], check=False)
        self.sh(['just', 'db::delete', self.db], check=False)
        self.sh(['cub-workenv', 'create-db', self.db], timeout=600)
        self.db_dir = self.locate_db_dir()


class Bench2(b.Bench):
    def __init__(self, args):
        self.args = args
        self.run_dir = (Path(args.root) / f'run-{args.tag}').resolve()
        self.run_dir.mkdir(parents=True, exist_ok=True)
        self.results = open(self.run_dir / f'results-{args.variant}.jsonl', 'a')
        self.meta = {'loadavg_start': os.getloadavg(), 'started': time.strftime('%F %T'), 'args': vars(args),
                     'rows': ROWS, 'buffer': b.BUFFER, 'lookups': b.LOOKUPS, 'loops': LOOPS,
                     'clients': CLIENTS, 'client_loops': CLIENT_LOOPS}

    # -- measurements ----------------------------------------------------------------------------------------
    def m(self, inst, scenario, sql, rep, autocommit=True, drain=False, expect=None):
        out = self.measure(inst, scenario, sql, rep, autocommit=autocommit, drain=drain)
        if out is None:
            return None
        rec = {'variant': inst.name, 'size': inst.size, 'mode': 'check', 'scenario': scenario, 'rep': rep,
               'phase_mode': inst.mode, 'digest': digest(out),
               'affected': sum(int(x) for x in re.findall(r'(\d+) rows? affected', out))}
        self.emit(rec)
        return out

    def checksum(self, inst, tag):
        bad, _ = inst.sql(f'select count(*) from t where bit_length(big) <> {8 * inst.size} or big is null;\n',
                          f'lencheck-{tag}')
        m = re.findall(r'^\s+(\d+)\s*$', bad, re.M)
        self.emit({'variant': inst.name, 'size': inst.size, 'mode': 'lencheck', 'scenario': tag,
                   'wrong_length_rows': int(m[0]) if m else None})
        out, _ = inst.sql(CHECKSUM, f'checksum-{tag}')
        vals = re.findall(r'^\s+(-?\d+)\s+(-?\d+)\s+(-?\d+)\s+(-?\d+)\s*$', out, re.M)
        self.emit({'variant': inst.name, 'size': inst.size, 'mode': 'checksum', 'scenario': tag,
                   'values': vals[0] if vals else None})

    def concurrent(self, inst, scenario, rep):
        """CLIENTS csql processes at once; the measured window spans all of them."""
        files = []
        for c in range(CLIENTS):
            rnd = random.Random(f'{SEED}-{scenario}-{rep}-{c}')
            lines = []
            for i in range(CLIENT_LOOPS):
                if scenario == 'S11':
                    lines.append(f"update t set big = {self.value('D1')} where id = {rnd.randint(1, self.n)};\ncommit;\n")
                else:
                    new_id = 10_000_000 + rep * 1_000_000 + c * 10_000 + i
                    lines.append(f"insert into t values ({new_id}, {new_id % 1000}, 'c', {self.value('D2')});\ncommit;\n")
            f = inst.dir / f'{scenario}-{rep}-{c}.sql'
            f.write_text(''.join(lines))
            files.append(f)
        inst.wait_idle()
        s0, io0 = inst.statdump(), b.proc_io(inst.pid)
        perf = b.Perf(inst.pid, inst.dir / f'perf-{scenario}-{rep}.csv')
        t0 = time.monotonic()
        procs = [subprocess.Popen(['csql', '--no-auto-commit', '-u', 'dba', '-i', str(f), inst.db], env=inst.env,
                                  cwd=inst.worktree, stdin=subprocess.DEVNULL,
                                  stdout=open(f.with_suffix('.out'), 'w'), stderr=subprocess.STDOUT,
                                  start_new_session=True) for f in files]
        rcs = [p.wait(timeout=b.STMT_TIMEOUT) for p in procs]
        wall = time.monotonic() - t0
        counts = perf.stop()
        s1, io1 = inst.statdump(), b.proc_io(inst.pid)
        errors = sum(f.with_suffix('.out').read_text(errors='replace').count('ERROR') for f in files)
        self.emit({'variant': inst.name, 'size': inst.size, 'mode': inst.mode, 'scenario': scenario, 'rep': rep,
                   'wall': wall, 'clients': CLIENTS, 'ops': CLIENTS * CLIENT_LOOPS, 'client_rc': rcs,
                   'client_errors': errors, **counts,
                   **{k: s1.get(k, 0) - s0.get(k, 0) for k in b.STAT_KEYS},
                   **{k: io1[k] - io0[k] for k in io0}})

    # -- workload text ---------------------------------------------------------------------------------------
    def mut_sql(self, sc, slot):
        """Mutation text for one repeat; SLOT (0..5) selects rows no other repeat touches."""
        n, q = self.n, self.n // 8
        rnd = random.Random(f'{SEED}-{sc}-{slot}')
        byte = f'{0xB0 + slot:02X}'
        if sc == 'S5':
            return 'update t set k = k + 1;\n', True
        if sc == 'S6':
            lo = slot * q + 1
            return f'update t set big = {self.value(byte)} where id between {lo} and {lo + q - 1};\n', True
        if sc == 'S9':
            return f'delete from t where mod(id, 8) = {slot};\n', True
        out = []
        for i in range(LOOPS):
            if sc == 'S7':
                new_id = n + 1 + slot * LOOPS + i
                out.append(f'update t set big = {self.value(byte)} where id = {rnd.randint(1, n)};\n'
                           f"insert into t values ({new_id}, {new_id % 1000}, 'ins', {self.value('E1')});\ncommit;\n")
            elif sc == 'S8b':
                out.append(f'update t set big = {self.value(byte)} where id = {rnd.randint(1, HOT)};\ncommit;\n')
            else:
                out.append(f'update t set k = k + 1 where id = {rnd.randint(1, HOT)};\ncommit;\n')
        return ''.join(out), False

    # -- one size --------------------------------------------------------------------------------------------
    def run_one(self, name, size):
        inst = Inst(name, self.run_dir)
        self.inst, self.size, self.n = inst, size, ROWS[size] // (10 if self.args.quick else 1)
        self.meta.setdefault('variants', {})[name] = {'commit': inst.commit, 'worktree': str(inst.worktree)}
        inst.create(size)
        try:
            inst.start('warm')
            inst.sql(self.load_sql(self.n), 'setup')
            self.measure(inst, 'S4', f"insert into t select n, mod(n, 1000), 's' || n, {self.value('AB')} from seq "
                                     f'where n <= {self.n};\n', rows=self.n, drain=True)
            inst.sql('update statistics on t with fullscan;\n', 'stats')
            self.evidence(inst, 'after-load')
            self.checksum(inst, 'after-load')
            reads = [('S1', 'select sum(k) from t;\n'), ('S2', "select count(*) from t where big > X'00';\n"),
                     ('S3n', self.lookups(False)), ('S3w', self.lookups(True))]
            for rep in range(IO_READ_REPS):
                for sc, sql in reads:
                    inst.start('io', evict=True)
                    self.m(inst, sc, sql, rep)
            inst.start('warm')
            for sc, sql in reads:
                inst.sql(sql, f'warmup-{sc}')
                for rep in range(WARM_READ_REPS):
                    self.m(inst, sc, sql, rep)
            # mutations: warm repeats use slots 0..2, io repeats slots 3..5
            for mode in ('warm', 'io'):
                for rep in range(MUT_REPS):
                    slot = rep + (0 if mode == 'warm' else MUT_REPS)
                    for sc in ('S5', 'S6', 'S7', 'S8b', 'S8s'):
                        sql, ac = self.mut_sql(sc, slot)
                        if mode == 'io':
                            inst.start('io', evict=True)
                        elif inst.mode != 'warm':
                            inst.start('warm')
                        self.m(inst, sc, sql, rep, autocommit=ac, drain=True)
                self.checksum(inst, f'after-mutations-{mode}')
            if inst.mode != 'warm':
                inst.start('warm')
            for rep in range(MUT_REPS):
                for sc in ('S11', 'S12'):
                    self.concurrent(inst, sc, rep)
            self.checksum(inst, 'after-concurrent')
            for mode in ('warm', 'io'):
                for rep in range(MUT_REPS):
                    slot = rep + (0 if mode == 'warm' else MUT_REPS)
                    sql, ac = self.mut_sql('S9', slot)
                    inst.start(mode, evict=(mode == 'io')) if (mode == 'io' or inst.mode != 'warm') else None
                    self.m(inst, 'S9', sql, rep, autocommit=ac, drain=True)
            self.checksum(inst, 'end')
            self.evidence(inst, 'end')
        finally:
            inst.drop()

    def main(self):
        meta_path = self.run_dir / f'meta-{self.args.variant}.json'
        meta_path.write_text(json.dumps(self.meta, indent=2, default=str))
        for size in self.args.sizes:
            try:
                self.run_one(self.args.variant, size)
            except b.HarnessError as e:
                self.emit({'variant': self.args.variant, 'size': size, 'mode': 'error', 'scenario': 'error',
                           'error': str(e)})
            meta_path.write_text(json.dumps(self.meta, indent=2, default=str))
        self.meta['finished'] = time.strftime('%F %T')
        meta_path.write_text(json.dumps(self.meta, indent=2, default=str))


def parse():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--root', required=True)
    ap.add_argument('--tag', required=True)
    ap.add_argument('--variant', required=True, choices=sorted(SHORT))
    ap.add_argument('--sizes', default='8192,65536,4096,100', type=lambda s: [int(x) for x in s.split(',')])
    ap.add_argument('--quick', action='store_true')
    ap.add_argument('--only-scenarios', default=None)
    return ap.parse_args()


if __name__ == '__main__':
    sys.exit(Bench2(parse()).main())
