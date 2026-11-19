"""CBRD-28062 oos_trigger_threshold sweep runner (adapted from the CBRD-27788 remeasure driver).

Owns only the oos-perf-28062-{dev,head} workenvs and their sw*/io* databases under ROOT.
One head build covers every threshold: each threshold has its own databases, loaded while its
oos_trigger_threshold was in effect, and a [@database] section in the worktree cubrid.conf.
Stages: prepare-env, prepare, cpu (sweep + ordinary + INSERT/UPDATE), cold (restart-only reads + trace), io.
"""
import argparse, hashlib, json, os, re, shutil, subprocess, sys, time
from functools import lru_cache
from pathlib import Path

ROOT = Path(os.environ.get('SWEEP_ROOT', '/mnt/nvme/data-5/tmp/CBRD-28062-perf-sweep'))
H = ROOT / 'harness'
EXTRA = Path(__file__).resolve().parent / 'extra.py'
CB = Path('/home/vimkim/gh/cb')
PRESET = 'release_gcc_nounit'
DEV, HEAD = 'oos-perf-28062-dev', 'oos-perf-28062-head'
EXPECTED = {DEV: '2e66081fd2', HEAD: '49d8df0dd5'}
CONFIGS = {'base': (DEV, None), 't0': (HEAD, None), 't5000': (HEAD, 5000), 't7000': (HEAD, 7000),
           't10500': (HEAD, 10500), 't14500': (HEAD, 14500), 't16236': (HEAD, 16236)}
LABELS = list(CONFIGS)
SERVER_CPUS, CLIENT_CPU = '16-19', '12'
TABLES_SW = ['w36', 'w47', 'w78', 'w110', 'n', 'r1_seed', 'r2_seed', 'r3_seed']
TABLES_IO = ['perf_heap_14500', 'perf_overflow_22000']


def db(label, kind): return kind + label
def wtname(label): return CONFIGS[label][0]
def wt(label): return CB / wtname(label)
def all_dbs(name): return sorted(db(l, k) for l, (w, _) in CONFIGS.items() if w == name for k in ('sw', 'io'))


def now(): return time.strftime('%Y%m%d-%H%M%S')


def source(label):
    """Full HEAD SHA. The dev worktree is develop 2e66081fd2 plus one broker-only include commit (see report)."""
    git = lambda *a: subprocess.run(['git', *a], cwd=wt(label), capture_output=True, text=True, check=True).stdout.strip()
    sha = git('rev-parse', 'HEAD')
    if wtname(label) == DEV:
        if git('diff', '--name-only', EXPECTED[DEV], 'HEAD') != 'src/broker/cas_cgw_odbc.c': raise RuntimeError('dev worktree moved')
    elif not sha.startswith(EXPECTED[HEAD]): raise RuntimeError(f'{label} worktree moved to {sha}')
    return sha


@lru_cache(None)
def environment(name):
    r = subprocess.run(['direnv', 'exec', str(CB / name), 'python3', '-c', 'import os,json;print(json.dumps(dict(os.environ)))'],
                       capture_output=True, text=True, check=True, cwd=CB / name)
    env = json.loads(r.stdout)
    want = (Path('/home/vimkim/.cub/install') / name / PRESET).resolve()
    if Path(env['CUBRID']).resolve() != want: raise RuntimeError(f'wrong install {env["CUBRID"]} != {want}')
    env['PATH'] = env['CUBRID'] + '/bin:' + env['PATH']
    env['LANG'] = 'en_US.UTF-8'
    return env


def command(argv, prefix, env=None, timeout=180, cwd=None):
    prefix = Path(prefix); prefix.parent.mkdir(parents=True, exist_ok=True)
    out_path, err_path = Path(str(prefix) + '.stdout'), Path(str(prefix) + '.stderr')
    if out_path.exists(): raise RuntimeError('preserving existing logs ' + str(prefix))
    with out_path.open('w') as out, err_path.open('w') as err:
        child = subprocess.Popen(argv, env=env, cwd=cwd, stdin=subprocess.DEVNULL, stdout=out, stderr=err,
                                 start_new_session=True, close_fds=True)
        rc = child.wait(timeout=timeout)
    if rc: raise RuntimeError(f'command {argv[:4]} failed {rc}: {prefix}')
    return out_path


def servers(env, dbname):
    found = []; exe = (Path(env['CUBRID']) / 'bin/cub_server').resolve()
    for p in Path('/proc').iterdir():
        if not p.name.isdigit(): continue
        try:
            if (p / 'exe').resolve() != exe: continue
            e = dict(s.split(b'=', 1) for s in (p / 'environ').read_bytes().split(b'\0') if b'=' in s)
            if all(e.get(k.encode(), b'').decode() == env.get(k, '') for k in ['CUBRID', 'CUBRID_CONF', 'CUBRID_DATABASES']) \
                    and re.search(rf'\b{dbname}\b', (p / 'cmdline').read_bytes().replace(b'\0', b' ').decode()):
                found.append(int(p.name))
        except (FileNotFoundError, PermissionError, ProcessLookupError):
            pass
    return found


def registry(env, name):
    text = (Path(env['CUBRID_DATABASES']) / 'databases.txt').read_text()
    names = sorted(l.split()[0] for l in text.splitlines() if l.strip() and not l.lstrip().startswith('#'))
    if not set(names) <= set(all_dbs(name)): raise RuntimeError('unexpected registrations ' + repr(names))


def start(label, kind, tag):
    name, dbn = wtname(label), db(label, kind); env = environment(name); registry(env, name)
    for other in all_dbs(name):
        if servers(env, other): raise RuntimeError('already running owned server ' + other)
    lc = ROOT / 'lifecycle' / f'{tag}-{now()}'
    command(['taskset', '-c', SERVER_CPUS, env['CUBRID'] + '/bin/cubrid', 'server', 'start', dbn], str(lc) + '-start', env, 300)
    pids = servers(env, dbn)
    if len(pids) != 1: raise RuntimeError('server identity missing ' + str(pids))
    command(['taskset', '-apc', SERVER_CPUS, str(pids[0])], str(lc) + '-affinity', env)
    return env, pids[0]


def stop(label, kind, tag, env):
    name, dbn = wtname(label), db(label, kind)
    lc = ROOT / 'lifecycle' / f'{tag}-{now()}'
    command([env['CUBRID'] + '/bin/cubrid', 'server', 'stop', dbn], str(lc) + '-stop', env, 300)
    command([env['CUBRID'] + '/bin/cubrid', 'service', 'stop'], str(lc) + '-service', env, 300)
    if servers(env, dbn): raise RuntimeError('server remains')


def csql(label, kind, path, text, env, timeout=7200):
    """Run SQL text through csql; refuse on stderr errors."""
    p = Path(path); p.parent.mkdir(parents=True, exist_ok=True)
    p.with_suffix('.sql').write_text(text)
    command([env['CUBRID'] + '/bin/csql', '-C', '-u', 'dba', '--no-pager', '--string-width', '1000000', '-t', '-N',
             '-i', str(p.with_suffix('.sql')), db(label, kind)], p, env, timeout)
    if re.search('ERROR:|Error:', Path(str(p) + '.stderr').read_text()):
        raise RuntimeError('SQL failed ' + str(p))


def gen(script, *args):
    return subprocess.run(['python3', '-B', str(script), *args], capture_output=True, text=True, check=True).stdout


def storage_sql(label, tables):
    q = []
    for t in tables:
        q.append(f'SHOW HEAP CAPACITY OF {t};')
        if label != 'base': q.append(f'SHOW HEAP OOS OF {t};')
    return ';line on\n' + '\n'.join(q) + '\n'


def conf_tail(name):
    out = '\nmax_query_cache_entries=0\nquery_cache_size_in_pages=0\n'
    for label, (w, thr) in CONFIGS.items():
        if w != name: continue
        extra = f'oos_trigger_threshold={thr}\n' if thr else ''
        out += f'\n[@{db(label, "sw")}]\ndata_buffer_size=4G\nlog_buffer_size=256M\nlog_max_archives=2\n{extra}'  # archives: see report, limit added after the cpu stage
        if extra: out += f'\n[@{db(label, "io")}]\n{extra}'
    return out


def prepare_env(name):
    path = ROOT / name; path.mkdir(exist_ok=False)
    wtp = CB / name
    pre = subprocess.run(['direnv', 'exec', str(wtp), 'sh', '-c', 'printf "%s\\n%s" "$CUBRID" "$PRESET_MODE"'],
                         capture_output=True, text=True, check=True, cwd=wtp).stdout.split('\n')
    if pre[1] != PRESET: raise RuntimeError('preset ' + pre[1])
    command(['direnv', 'exec', str(wtp), 'cub-workenv', 'init', '--worktree', str(wtp), '--install', pre[0],
             '--preset', pre[1], '--no-db'], path / 'init', None, 900, cwd=wtp)
    environment.cache_clear(); env = environment(name)
    cc = (wtp / f'build_preset_{PRESET}' / 'compile_commands.json').read_text()
    if 'CUBRID_UNIT_TEST_ENABLED' in cc: raise RuntimeError('unit-test instrumentation in build')
    conf = Path(env['CUBRID_CONF_FILE']); text = conf.read_text()
    text = re.sub(r'(?m)^data_buffer_size=.*$', 'data_buffer_size=512M', text)
    text = re.sub(r'(?m)^log_buffer_size=.*$', 'log_buffer_size=16M', text)
    text = re.sub(r'(?m)^max_clients=.*$', 'max_clients=20', text)
    conf.write_text(text + conf_tail(name)); (path / 'cubrid.conf').write_text(conf.read_text())
    print(name, 'env prepared', flush=True)


def prepare(label):
    name = wtname(label); path = ROOT / 'db' / label
    if (path / 'receipt.json').exists(): print(label, 'already prepared'); return
    path.mkdir(parents=True, exist_ok=False)
    env = environment(name)
    for kind in ('sw', 'io'):
        command(['cub-workenv', 'create-db', db(label, kind), '--worktree', str(CB / name), '--path', str(path / ('database-' + kind))],
                path / ('create-' + kind), env, 900, cwd=CB / name)
    sw_fixture = gen(H / 'sweep.py', 'fixture') + ''.join(gen(H / 'ordinary.py', 'fixture', '--prefix', f'r{r}_') for r in (1, 2, 3))
    io_fixture = gen(H / 'io/io_bench.py', 'fixture', '--rows', '100000')
    (ROOT / 'fixtures').mkdir(exist_ok=True)
    for fname, text in (('io-fixture.sql', io_fixture), ('sw-fixture.sql', sw_fixture)):
        f = ROOT / 'fixtures' / fname
        if f.exists() and f.read_text() != text: raise RuntimeError('fixture drift ' + fname)
        f.write_text(text)
    for kind, fixture, tables in (('sw', sw_fixture, ['w36', 'w47', 'w78', 'w110', 'r1_seed']), ('io', io_fixture, TABLES_IO)):
        env, pid = start(label, kind, f'{label}-{kind}-load')
        try:
            t0 = time.time()
            csql(label, kind, path / f'{kind}-load', fixture, env)
            (path / f'{kind}-load.seconds').write_text(f'{time.time() - t0:.1f}\n')
            csql(label, kind, path / f'{kind}-storage', storage_sql(label, tables), env)
            command([env['CUBRID'] + '/bin/cubrid', 'spacedb', '-C', '--size-unit=M', db(label, kind)], path / f'{kind}-spacedb', env)
            command([env['CUBRID'] + '/bin/cubrid', 'paramdump', '-C', db(label, kind)], path / f'{kind}-paramdump', env)
        finally:
            stop(label, kind, f'{label}-{kind}-load', env)
    (path / 'receipt.json').write_text(json.dumps({
        'label': label, 'source': source(label), 'threshold': CONFIGS[label][1],
        'fixtures': {n: hashlib.sha256((ROOT / 'fixtures' / n).read_bytes()).hexdigest() for n in ('io-fixture.sql', 'sw-fixture.sql')},
        'environment': {k: env[k] for k in env if k.startswith('CUBRID') or k in ('LANG', 'LC_ALL', 'PRESET_MODE')}}, indent=2) + '\n')
    print(label, 'prepared', flush=True)


def cpu_stats(cpus=(12, 16, 17, 18, 19)):
    rows = {}
    for line in Path('/proc/stat').read_text().splitlines():
        f = line.split()
        if f[0].startswith('cpu') and f[0] != 'cpu' and int(f[0][3:]) in cpus:
            v = list(map(int, f[1:9])); rows[int(f[0][3:])] = (sum(v), v[3] + v[4])
    return rows


def order(rnd):
    return LABELS if rnd % 2 else LABELS[::-1]


def unit_dir(kind, rnd, label):
    final = ROOT / kind / f'r{rnd}-{label}'; tmp = ROOT / kind / f'.tmp-r{rnd}-{label}'
    if final.exists(): return None, None
    if tmp.exists(): shutil.move(str(tmp), str(ROOT / 'failed' / f'{kind}-r{rnd}-{label}-{now()}'))
    tmp.mkdir(parents=True)
    return tmp, final


def meta(tmp, before):
    after = cpu_stats()
    busy = {c: round(100 * (1 - (after[c][1] - before[0][c][1]) / max(1, after[c][0] - before[0][c][0])), 1) for c in after}
    (tmp / 'meta.json').write_text(json.dumps({'load_before': before[1], 'load_after': os.getloadavg(),
                                                'cpu_busy_percent_incl_server': busy, 'seconds': time.time() - before[2]}, indent=1) + '\n')


def cpu(rounds, labels):
    for rnd in range(1, rounds + 1):
        for label in order(rnd):
            if label not in labels: continue
            tmp, final = unit_dir('cpu', rnd, label)
            if tmp is None: continue
            before = (cpu_stats(), os.getloadavg(), time.time())
            env, pid = start(label, 'sw', f'cpu-r{rnd}-{label}')
            try:
                dbn = db(label, 'sw'); src = source(label)
                common = ['--database', dbn, '--server-pid', str(pid), '--label', label, '--source', src]
                oos = [] if label == 'base' else ['--show-oos']
                e2 = dict(env, PYTHONPATH=str(H))
                logs = ROOT / 'harness-logs' / f'cpu-r{rnd}-{label}'
                command(['python3', '-B', str(H / 'sweep.py'), 'measure', *common, '--output', str(tmp / 'sweep'), *oos],
                        str(logs) + '-sweep', env, 14400)
                command(['python3', '-B', str(H / 'ordinary.py'), 'measure', '--prefix', f'r{rnd}_', *common,
                         '--output', str(tmp / 'ordinary'), *oos], str(logs) + '-ordinary', env, 14400)
                command(['python3', '-B', str(EXTRA), 'dml', *common, '--output', str(tmp / 'dml'), *oos],
                        str(logs) + '-dml', e2, 28800)
            finally:
                stop(label, 'sw', f'cpu-r{rnd}-{label}', env)
            meta(tmp, before); tmp.rename(final)
            print('cpu', rnd, label, 'done', time.strftime('%H:%M:%S'), flush=True)


def cold(rounds, labels):
    for rnd in range(1, rounds + 1):
        for label in order(rnd):
            if label not in labels: continue
            tmp, final = unit_dir('cold', rnd, label)
            if tmp is None: continue
            before = (cpu_stats(), os.getloadavg(), time.time())
            for table in ('w36', 'w47', 'w78', 'w110'):
                for case in ('narrow', 'length'):
                    tag = f'cold-r{rnd}-{label}-{table}-{case}'
                    env, pid = start(label, 'sw', tag)
                    try:
                        command(['python3', '-B', str(EXTRA), 'cold', '--database', db(label, 'sw'), '--server-pid', str(pid),
                                 '--label', label, '--source', source(label), '--table', table, '--case', case,
                                 '--output', str(tmp / f'{case}-{table}'), *([] if label == 'base' else ['--show-oos'])],
                                ROOT / 'harness-logs' / tag, dict(env, PYTHONPATH=str(H)), 900)
                    finally:
                        stop(label, 'sw', tag, env)
            meta(tmp, before); tmp.rename(final)
            print('cold', rnd, label, 'done', time.strftime('%H:%M:%S'), flush=True)


def dml2(rounds, labels, insert_runs, update_runs):
    """INSERT and UPDATE-big with an incompressible payload (the first cpu-stage versions used REPEAT text, which LZ4
    shrank to ~90 B per row, so they never exercised placement). INSERT is the noisiest case, so it gets more repeats."""
    for rnd in range(1, rounds + 1):
        for label in order(rnd):
            if label not in labels: continue
            tmp, final = unit_dir('dml2', rnd, label)
            if tmp is None: continue
            before = (cpu_stats(), os.getloadavg(), time.time())
            env, pid = start(label, 'sw', f'dml2-r{rnd}-{label}')
            try:
                common = ['--database', db(label, 'sw'), '--server-pid', str(pid), '--label', label, '--source', source(label)]
                oos = [] if label == 'base' else ['--show-oos']
                for case, runs in (('insert', insert_runs), ('update_big', update_runs)):
                    command(['python3', '-B', str(EXTRA), 'dml', *common, '--cases', case, '--runs', str(runs),
                             '--output', str(tmp / case), *oos], ROOT / 'harness-logs' / f'dml2-r{rnd}-{label}-{case}',
                            dict(env, PYTHONPATH=str(H)), 14400)
            finally:
                stop(label, 'sw', f'dml2-r{rnd}-{label}', env)
            meta(tmp, before); tmp.rename(final)
            print('dml2', rnd, label, 'done', time.strftime('%H:%M:%S'), flush=True)


IO_CASES = ('q1', 'q4', 'q5')


def io(repeats, labels):
    for layout in ('heap', 'overflow'):
        for case in IO_CASES:
            for repeat in range(1, repeats + 1):
                for label in order(repeat):
                    if label not in labels: continue
                    name = f'restart-{layout}-{case}-{repeat}-{label}'
                    out = ROOT / 'io' / 'samples' / name
                    if (out / 'sample.json').exists() and json.loads((out / 'sample.json').read_text())['complete']: continue
                    if out.exists(): shutil.move(str(out), str(ROOT / 'failed' / f'io-{name}-{now()}'))
                    env, pid = start(label, 'io', name)
                    try:
                        command(['python3', '-B', str(H / 'io/io_bench.py'), 'sample', '--database', db(label, 'io'),
                                 '--server-pid', str(pid), '--label', label, '--source', source(label), '--worktree', str(wt(label)),
                                 '--output', str(out), '--layout', layout, '--case', case, '--cache', 'restart-only',
                                 '--repeat', str(repeat), '--client-cpu', CLIENT_CPU],
                                ROOT / 'harness-logs' / ('io-' + name), env, 900)
                    finally:
                        stop(label, 'io', name, env)
                    s = json.loads((out / 'sample.json').read_text())
                    print(name, round(s['elapsed_seconds'], 3), s.get('trace'), flush=True)


if __name__ == '__main__':
    (ROOT / 'failed').mkdir(parents=True, exist_ok=True)
    a = argparse.ArgumentParser()
    a.add_argument('action', choices=['prepare-env', 'prepare', 'cpu', 'cold', 'io', 'dml2'])
    a.add_argument('--label', action='append')
    a.add_argument('--worktree', choices=[DEV, HEAD])
    a.add_argument('--rounds', type=int, default=2)
    a.add_argument('--repeats', type=int, default=3)
    a.add_argument('--insert-runs', type=int, default=11)
    a.add_argument('--update-runs', type=int, default=6)
    args = a.parse_args()
    labels = args.label or LABELS
    if args.action == 'prepare-env': prepare_env(args.worktree)
    elif args.action == 'prepare':
        for l in labels: prepare(l)
    elif args.action == 'cpu': cpu(args.rounds, labels)
    elif args.action == 'cold': cold(args.rounds, labels)
    elif args.action == 'dml2': dml2(args.rounds, labels, args.insert_runs, args.update_runs)
    else: io(args.repeats, labels)
