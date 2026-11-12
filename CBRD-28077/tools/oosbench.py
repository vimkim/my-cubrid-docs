#!/usr/bin/env python3
"""CBRD-28077: compare develop, OOS, Sidecar and Inner Table on the same workloads.

Usage (each worktree is a release installation initialized with cub-workenv):

    python3 oosbench.py --root RUNS_DIR [--sizes 100,2048,8192,65536] [--variants develop,oos,sidecar,inner]
                        [--only-scenarios S1,S2] [--quick]

For every (size, variant) the driver creates a new database, loads one table, and runs the scenarios below
in a fixed order. It records one JSON line per measurement in RUNS_DIR/<stamp>/results.jsonl.

Table:   t (id INT PRIMARY KEY, k INT NOT NULL, s VARCHAR(50), big BIT VARYING)
         `big` is a BIT VARYING value of SIZE bytes. BIT VARYING is not compressed, so every variant stores
         SIZE bytes. Inner Table opts the table in with t__inner and inner_table_threshold=4060, the same row
         length at which OOS and Sidecar move values (a quarter of a 16 KB page).

Modes:   warm  data_buffer_size=LARGE, the measured statement runs after one unmeasured run
         io    data_buffer_size=SMALL, server restarted and the OS page cache of the DB files dropped
               (posix_fadvise DONTNEED, no root needed) just before the measured statement

Scenarios (the order is fixed because mutations change the table):
  S4  load: INSERT ... SELECT of N rows (warm only; first statement of the database)
  S1  narrow scan: SELECT SUM(k) FROM t                                    reads 3x per mode
  S2  wide scan:   SELECT COUNT(*) FROM t WHERE big > X'00'                 reads 3x per mode
  S3n PK lookups, small column: LOOKUPS x SELECT k ... WHERE id = ?          reads 3x per mode
  S3w PK lookups, big column:   LOOKUPS x SELECT COUNT(*) ... AND big > X'00'
  S5  UPDATE t SET k = k + 1 (all rows, one transaction)                    once per mode
  S6  UPDATE t SET big = <new value> WHERE id in a quarter of the rows       once per mode
  S7  LOOPS x (UPDATE big of one row; INSERT one row; COMMIT)               once per mode
  S8b LOOPS x (UPDATE big of one of 100 hot rows; COMMIT)                   once per mode
  S8s LOOPS x (UPDATE k of one of 100 hot rows; COMMIT)                     once per mode
  S9  DELETE a quarter of the rows (one transaction)                        once per mode
SIZE=100 keeps every value inline in every variant: that run is the feature-unused case (S10).

Every measurement waits until the server is idle (vacuum done) before it starts. Mutations also record a
"drain" sample: the work the server does after the statement until it is idle again (vacuum and flush).
"""

import argparse
import json
import os
import random
import re
import signal
import subprocess
import sys
import time
from pathlib import Path

CB = Path(os.environ.get('OOSBENCH_WORKTREES', '/home/vimkim/gh/cb'))  # parent of the b28077-* worktrees
VARIANTS = {
    'develop': {'worktree': CB / 'b28077-develop', 'conf': {}},
    'oos': {'worktree': CB / 'b28077-oos', 'conf': {}},
    'sidecar': {'worktree': CB / 'b28077-sidecar', 'conf': {}},
    'inner': {'worktree': CB / 'b28077-inner', 'conf': {'inner_table_threshold': '4060'}},
}
ROWS = {100: 1_000_000, 2048: 400_000, 8192: 120_000, 65536: 16_000}
BUFFER = {'warm': '4G', 'io': '128M'}
LOOKUPS = 5000
LOOPS = 3000
HOT = 100
READ_REPS = 3
SEED = 28077
STAT_KEYS = ('Num_data_page_fetches', 'Num_data_page_dirties', 'Num_data_page_ioreads', 'Num_data_page_iowrites',
             'Num_file_ioreads', 'Num_file_iowrites', 'Num_log_page_iowrites', 'Num_log_append_records')
STMT_TIMEOUT = 600  # each measured statement batch must finish in 10 minutes


class HarnessError(Exception):
    pass


def load_env(worktree):
    """The environment direnv gives the worktree: installation, registry, ports, preset and build directory."""
    out = subprocess.run(['direnv', 'exec', str(worktree), 'env', '-0'], cwd=worktree, stdin=subprocess.DEVNULL,
                         stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, check=True).stdout
    env = dict(item.split(b'=', 1) for item in out.split(b'\0') if b'=' in item)
    env = {k.decode(): v.decode() for k, v in env.items()}
    if env.get('CUBRID_RUNTIME_READY') != '1':
        raise HarnessError(f'{worktree}: cub-workenv environment is not ready')
    return env


def cpu_ticks(pid):
    fields = Path(f'/proc/{pid}/stat').read_text().rsplit(')', 1)[1].split()
    return int(fields[11]) + int(fields[12])


def proc_io(pid):
    got = {}
    for line in Path(f'/proc/{pid}/io').read_text().splitlines():
        k, v = line.split(':')
        got[k] = int(v)
    return {'os_read_bytes': got['read_bytes'], 'os_write_bytes': got['write_bytes']}


def csql_time(out):
    return sum(float(x) for x in re.findall(r'\((\d+\.\d+) sec\)', out))


class Perf:
    def __init__(self, pid, path):
        self.path = path
        self.proc = subprocess.Popen(['perf', 'stat', '-x,', '-e', 'instructions,cycles,task-clock', '-p', str(pid),
                                      '-o', str(path)], stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                                     stderr=subprocess.DEVNULL)
        time.sleep(0.3)
        if self.proc.poll() is not None:
            raise HarnessError(f'perf stat exited with {self.proc.returncode}')

    def stop(self):
        self.proc.send_signal(signal.SIGINT)
        self.proc.wait(timeout=60)
        got = {}
        for line in Path(self.path).read_text().splitlines():
            f = line.split(',')
            if len(f) > 2 and f[2] in ('instructions', 'cycles', 'task-clock'):
                try:
                    got[f[2].replace('-', '_')] = float(f[0])
                except ValueError:
                    pass
        return got


class Instance:
    """One variant's installation and the database of the current (size, variant)."""

    def __init__(self, name, run_dir):
        self.name = name
        spec = VARIANTS[name]
        self.worktree = spec['worktree']
        self.extra_conf = spec['conf']
        self.env = load_env(self.worktree)
        self.commit = subprocess.check_output(['git', '-C', str(self.worktree), 'rev-parse', 'HEAD'],
                                              text=True).strip()
        self.conf = Path(self.env['CUBRID_CONF_FILE'])
        self.run_dir = run_dir
        self.db = None
        self.pid = None
        self.n = 0
        self.mode = None

    # -- process helpers -------------------------------------------------------------------------------------
    def sh(self, cmd, timeout=1800, check=True):
        with open(self.dir / 'harness.log', 'a') as f:
            f.write(f'$ {" ".join(cmd)}\n')
            f.flush()
            r = subprocess.run(cmd, env=self.env, cwd=self.worktree, stdin=subprocess.DEVNULL, stdout=f,
                               stderr=subprocess.STDOUT, timeout=timeout, start_new_session=True)
        if check and r.returncode:
            raise HarnessError(f'{self.name}: {" ".join(cmd[:4])} failed with {r.returncode}')
        return r.returncode

    def sql(self, text, name, timeout=STMT_TIMEOUT, autocommit=True, check=True):
        self.n += 1
        stem = self.dir / f'{self.n:04d}-{name}'
        Path(f'{stem}.sql').write_text(text)
        cmd = ['csql', '-u', 'dba', '-i', f'{stem}.sql', self.db]
        if not autocommit:
            cmd.insert(1, '--no-auto-commit')
        t0 = time.monotonic()
        try:
            with open(f'{stem}.out', 'w') as out:
                r = subprocess.run(cmd, env=self.env, cwd=self.worktree, stdin=subprocess.DEVNULL, stdout=out,
                                   stderr=subprocess.STDOUT, timeout=timeout, start_new_session=True)
        except subprocess.TimeoutExpired:
            raise HarnessError(f'{self.name}: {name} timed out after {timeout}s; see {stem}.out')
        wall = time.monotonic() - t0
        text_out = Path(f'{stem}.out').read_text(errors='replace')
        if check and (r.returncode or re.search(r'ERROR', text_out)):
            raise HarnessError(f'{self.name}: SQL {name} failed; see {stem}.out')
        return text_out, wall

    def server_pid(self):
        exe = os.path.join(self.env['CUBRID'], 'bin', 'cub_server')
        for p in subprocess.run(['pgrep', '-u', str(os.getuid()), '-x', 'cub_server'], stdout=subprocess.PIPE,
                                text=True).stdout.split():
            try:
                if os.readlink(f'/proc/{p}/exe') == exe and self.db in Path(f'/proc/{p}/cmdline').read_text():
                    return int(p)
            except OSError:
                pass
        return None

    def statdump(self):
        path = self.dir / 'statdump.tmp'
        self.sh(['cubrid', 'statdump', '-c', '-o', str(path), self.db], timeout=120)
        got = {}
        for line in path.read_text().splitlines():
            m = re.match(r'\s*(\w+)\s*=\s*(\d+)\s*$', line)
            if m and m.group(1) in STAT_KEYS:
                got[m.group(1)] = int(m.group(2))
        return got

    def wait_idle(self, limit=1800):
        """Wait until the server uses at most 1% CPU over eight consecutive 0.25 s intervals; return seconds."""
        t0 = time.monotonic()
        streak = 0
        hz = os.sysconf('SC_CLK_TCK')
        while time.monotonic() - t0 < limit:
            before = cpu_ticks(self.pid)
            time.sleep(0.25)
            streak = streak + 1 if (cpu_ticks(self.pid) - before) / hz <= 0.0101 else 0
            if streak >= 8:
                return time.monotonic() - t0 - 2.0
        raise HarnessError(f'{self.name}: server did not become idle in {limit}s')

    # -- database lifecycle ----------------------------------------------------------------------------------
    def create(self, size):
        self.size = size
        self.db = f'b{self.name[:3]}{size}'
        self.dir = self.run_dir / f'{size}' / self.name
        self.dir.mkdir(parents=True, exist_ok=True)
        text = self.conf.read_text()
        cut = text.find('\n[@b')  # a section left by an interrupted run of this driver
        self.conf_backup = text[:cut].rstrip('\n') + '\n' if cut >= 0 else text
        self.sh(['cubrid', 'service', 'start'], check=False)
        self.sh(['cubrid', 'server', 'stop', self.db], check=False)
        self.sh(['just', 'db::delete', self.db], check=False)
        self.sh(['cub-workenv', 'create-db', self.db], timeout=600)
        self.db_dir = self.locate_db_dir()

    def locate_db_dir(self):
        reg = Path(self.env.get('CUBRID_DATABASES', '')) / 'databases.txt'
        for line in reg.read_text().splitlines():
            f = line.split()
            if f and f[0] == self.db:
                return [Path(f[1]), Path(f[3])]
        raise HarnessError(f'{self.name}: {self.db} not in {reg}')

    def set_mode(self, mode):
        section = {'data_buffer_size': BUFFER[mode], 'stored_procedure': 'no', **self.extra_conf}
        body = ''.join(f'{k}={v}\n' for k, v in section.items())
        self.conf.write_text(self.conf_backup + f'\n[@{self.db}]\n{body}')
        self.mode = mode

    def start(self, mode, evict=False):
        if self.pid:
            self.stop()
        self.set_mode(mode)
        if evict:
            self.evict()
        self.sh(['cubrid', 'server', 'start', self.db], timeout=900)
        self.pid = self.server_pid()
        if not self.pid:
            raise HarnessError(f'{self.name}: server pid not found')
        # The server collects global statistics only while a client watches them.
        self.watcher = subprocess.Popen(['cubrid', 'statdump', '-i', '3600', self.db], env=self.env,
                                        cwd=self.worktree, stdin=subprocess.DEVNULL,
                                        stdout=open(self.dir / 'watcher.log', 'a'), stderr=subprocess.STDOUT,
                                        start_new_session=True)
        time.sleep(1.0)

    def stop(self):
        w = getattr(self, 'watcher', None)
        if w:  # the utility may exit and leave its worker in the session, so always signal the group
            try:
                os.killpg(w.pid, signal.SIGTERM)  # the watcher's own session: the utility and its children
                w.wait(timeout=30)
            except (ProcessLookupError, subprocess.TimeoutExpired):
                try:
                    os.killpg(w.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
        self.watcher = None
        self.sh(['cubrid', 'server', 'stop', self.db], timeout=900, check=False)
        self.pid = None

    def evict(self):
        for d in self.db_dir:
            for p in d.rglob('*'):
                if p.is_file():
                    try:
                        fd = os.open(p, os.O_RDONLY)
                        os.posix_fadvise(fd, 0, 0, os.POSIX_FADV_DONTNEED)
                        os.close(fd)
                    except OSError:
                        pass

    def drop(self):
        if self.db:
            self.stop()
            self.conf.write_text(self.conf_backup)
            self.sh(['just', 'db::delete', self.db], check=False)

    def du(self):
        return sum(p.stat().st_size for d in self.db_dir for p in d.rglob('*') if p.is_file())


class Bench:
    def __init__(self, args):
        self.args = args
        self.run_dir = (Path(args.root) / time.strftime('run-%Y%m%d-%H%M%S')).resolve()
        self.run_dir.mkdir(parents=True)
        self.results = open(self.run_dir / 'results.jsonl', 'a')
        self.meta = {'loadavg_start': os.getloadavg(), 'started': time.strftime('%F %T'), 'args': vars(args),
                     'rows': ROWS, 'buffer': BUFFER, 'lookups': LOOKUPS, 'loops': LOOPS, 'variants': {}}

    def emit(self, rec):
        rec['loadavg'] = os.getloadavg()[0]
        rec['ts'] = time.strftime('%F %T')
        self.results.write(json.dumps(rec) + '\n')
        self.results.flush()
        print(json.dumps({k: rec[k] for k in ('variant', 'size', 'mode', 'scenario', 'rep', 'wall', 'instructions')
                          if k in rec}), flush=True)

    def measure(self, inst, scenario, sql, rep=0, autocommit=True, drain=False, rows=None):
        inst.wait_idle()
        s0, io0 = inst.statdump(), proc_io(inst.pid)
        perf = Perf(inst.pid, inst.dir / f'perf-{inst.n + 1:04d}.csv')
        try:
            out, wall = inst.sql(sql, f'{inst.mode}-{scenario}-{rep}', autocommit=autocommit)
        except HarnessError as e:
            counts = perf.stop()
            self.emit({'variant': inst.name, 'size': inst.size, 'mode': inst.mode, 'scenario': scenario, 'rep': rep,
                       'failed': str(e), **counts})
            inst.wait_idle(limit=3600)  # a killed client rolls back on the server
            return None
        finally:
            if perf.proc.poll() is None:
                counts = perf.stop()
        s1, io1 = inst.statdump(), proc_io(inst.pid)
        rec = {'variant': inst.name, 'size': inst.size, 'mode': inst.mode, 'scenario': scenario, 'rep': rep,
               'wall': wall, 'csql_time': csql_time(out), 'rows': rows, **counts,
               **{k: s1.get(k, 0) - s0.get(k, 0) for k in STAT_KEYS},
               **{k: io1[k] - io0[k] for k in io0}}
        if drain:
            perf = Perf(inst.pid, inst.dir / f'perf-{inst.n:04d}-drain.csv')
            try:
                rec['drain_seconds'] = inst.wait_idle()
            finally:
                d = perf.stop()
            rec.update({f'drain_{k}': v for k, v in d.items()})
            s2, io2 = inst.statdump(), proc_io(inst.pid)
            rec.update({f'drain_{k}': s2.get(k, 0) - s1.get(k, 0) for k in STAT_KEYS})
            rec.update({f'drain_{k}': io2[k] - io1[k] for k in io1})
        self.emit(rec)
        return out

    # -- workload text ---------------------------------------------------------------------------------------
    def value(self, byte):
        # The CAST matters: with a reused plan, a bare REPEAT(X'..', N) in UPDATE stores N/4 bytes of ASCII hex text
        # instead of N bytes (develop a7f220d5d7, found in CBRD-28077 run 2). The first execution is correct.
        return f"CAST(REPEAT(X'{byte}', {self.size}) AS BIT VARYING)"

    def load_sql(self, n):
        return (f'create table seq (n int primary key);\n'
                f'insert into seq select rownum from db_attribute a, db_attribute b, db_attribute c, db_attribute d '
                f'limit {n + LOOPS + 10};\n'
                f'create table t (id int primary key, k int not null, s varchar(50), big bit varying);\n'
                + ('create table t__inner (ck bigint primary key, chunk bit varying);\n'
                   if self.inst.name == 'inner' else ''))

    def lookups(self, wide):
        rnd = random.Random(SEED + (1 if wide else 0))
        ids = [rnd.randint(1, self.n) for _ in range(LOOKUPS)]
        if wide:
            return ''.join(f"select count(*) from t where id = {i} and big > X'00';\n" for i in ids)
        return ''.join(f'select k from t where id = {i};\n' for i in ids)

    def loop_sql(self, kind, mode):
        rnd = random.Random(f'{SEED}-{kind}-{mode}')
        out = []
        byte = 'C1' if mode == 'warm' else 'C2'
        for i in range(LOOPS):
            if kind == 'S7':
                new_id = self.n + 1 + i + (0 if mode == 'warm' else LOOPS * 2)
                out.append(f'update t set big = {self.value(byte)} where id = {rnd.randint(1, self.n)};\n'
                           f"insert into t values ({new_id}, {new_id} % 1000, 'ins', {self.value('E1')});\ncommit;\n")
            elif kind == 'S8b':
                out.append(f'update t set big = {self.value(byte)} where id = {rnd.randint(1, HOT)};\ncommit;\n')
            else:
                out.append(f'update t set k = k + 1 where id = {rnd.randint(1, HOT)};\ncommit;\n')
        return ''.join(out)

    # -- one (size, variant) ---------------------------------------------------------------------------------
    def want(self, s):
        return not self.args.only_scenarios or s in self.args.only_scenarios

    def run_one(self, name, size):
        inst = Instance(name, self.run_dir)
        self.inst, self.size, self.n = inst, size, ROWS[size] // (10 if self.args.quick else 1)
        self.meta['variants'][name] = {'commit': inst.commit, 'worktree': str(inst.worktree)}
        inst.create(size)
        try:
            inst.start('warm')
            inst.sql(self.load_sql(self.n), 'setup')
            self.measure(inst, 'S4', f"insert into t select n, mod(n, 1000), 's' || n, {self.value('AB')} from seq "
                                     f'where n <= {self.n};\n', rows=self.n, drain=True)
            inst.sql('update statistics on t with fullscan;\n', 'stats')
            self.evidence(inst, 'after-load')
            reads = [('S1', 'select sum(k) from t;\n'), ('S2', "select count(*) from t where big > X'00';\n"),
                     ('S3n', self.lookups(False)), ('S3w', self.lookups(True))]
            reads = [r for r in reads if self.want(r[0])]
            # io reads: restart and drop the OS cache before every measured statement
            for rep in range(READ_REPS):
                for sc, sql in reads:
                    inst.start('io', evict=True)
                    self.measure(inst, sc, sql, rep)
            # warm reads: one unmeasured run, then the measured ones
            inst.start('warm')
            for sc, sql in reads:
                inst.sql(sql, f'warmup-{sc}')
                for rep in range(READ_REPS):
                    self.measure(inst, sc, sql, rep)
            q = self.n // 4
            for mode in ('warm', 'io'):
                lo = 1 if mode == 'warm' else q + 1
                muts = [('S5', 'update t set k = k + 1;\n', True),
                        ('S6', f"update t set big = {self.value('B1' if mode == 'warm' else 'B2')} "
                               f'where id between {lo} and {lo + q - 1};\n', True),
                        ('S7', self.loop_sql('S7', mode), False),
                        ('S8b', self.loop_sql('S8b', mode), False),
                        ('S8s', self.loop_sql('S8s', mode), False),
                        ('S9', f'delete from t where mod(id, 4) = {0 if mode == "warm" else 1};\n', True)]
                for sc, sql, ac in muts:
                    if not self.want(sc):
                        continue
                    if mode == 'io':
                        inst.start('io', evict=True)
                    elif inst.mode != 'warm':
                        inst.start('warm')
                    self.measure(inst, sc, sql, 0, autocommit=ac, drain=True)
            self.evidence(inst, 'end')
        finally:
            inst.drop()

    def evidence(self, inst, tag):
        """Record where the values live and how much disk the database uses."""
        probe = {'oos': 'show heap oos of t;\n', 'sidecar': 'show heap sidecar of t;\n',
                 'inner': 'select count(*) from t__inner;\n'}.get(inst.name, '')
        out, _ = inst.sql('show heap capacity of t;\n' + probe, f'evidence-{tag}', check=False)
        self.emit({'variant': inst.name, 'size': inst.size, 'mode': 'evidence', 'scenario': tag,
                   'db_bytes': inst.du(), 'evidence_file': f'{inst.dir}/{inst.n:04d}-evidence-{tag}.out'})

    def main(self):
        (self.run_dir / 'meta.json').write_text(json.dumps(self.meta, indent=2, default=str))
        for i, size in enumerate(self.args.sizes):
            order = self.args.variants[i % len(self.args.variants):] + self.args.variants[:i % len(self.args.variants)]
            for name in order:
                try:
                    self.run_one(name, size)
                except HarnessError as e:
                    self.emit({'variant': name, 'size': size, 'mode': 'error', 'scenario': 'error', 'error': str(e)})
                (self.run_dir / 'meta.json').write_text(json.dumps(self.meta, indent=2, default=str))
        self.meta['finished'] = time.strftime('%F %T')
        (self.run_dir / 'meta.json').write_text(json.dumps(self.meta, indent=2, default=str))


def parse():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--root', required=True)
    ap.add_argument('--sizes', default='100,2048,8192,65536', type=lambda s: [int(x) for x in s.split(',')])
    ap.add_argument('--variants', default='develop,oos,sidecar,inner', type=lambda s: s.split(','))
    ap.add_argument('--only-scenarios', default=None, type=lambda s: set(s.split(',')))
    ap.add_argument('--quick', action='store_true', help='one tenth of the rows, for a harness check')
    return ap.parse_args()


if __name__ == '__main__':
    sys.exit(Bench(parse()).main())
