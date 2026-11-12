"""CBRD-27788 AC-P2/AC-P3 re-measurement runner. Owns only the three oos-perf-27788r-* workenvs and their DBs."""
import argparse, hashlib, json, re, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
H = ROOT / 'harness'
ENGINES = {'base': 'oos-perf-27788r-dev', 'head': 'oos-perf-27788r-head', 'thr': 'oos-perf-27788r-thr'}
EXPECTED_SOURCE = {'base': '2dd94e32ab86a756b0f1ea2123ad7d2ac913321b', 'head': '67220b7e230ff1587ba5940001d72e10477a1fc4'}
PRESET = 'release_gcc_nounit'
IO_DB, SW_DB = 'io27788', 'sw27788'
DBS = [IO_DB, SW_DB]
CONF_TAIL = f"""
max_query_cache_entries=0
query_cache_size_in_pages=0

[@{SW_DB}]
data_buffer_size=4G
log_buffer_size=256M
"""


def wt(label): return Path('/home/vimkim/gh/cb') / ENGINES[label]


def source(label):
    sha = subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=wt(label), capture_output=True, text=True, check=True).stdout.strip()
    if EXPECTED_SOURCE.get(label, sha) != sha: raise RuntimeError(f'{label} worktree moved to {sha}')
    return sha


def environment(label):
    r = subprocess.run(['direnv', 'exec', str(wt(label)), 'python3', '-c', 'import os,json;print(json.dumps(dict(os.environ)))'],
                       capture_output=True, text=True, check=True, cwd=wt(label))
    env = json.loads(r.stdout)
    want = (Path('/home/vimkim/.cub/install') / wt(label).name / PRESET).resolve()
    if Path(env['CUBRID']).resolve() != want:
        raise RuntimeError(f'wrong install {env["CUBRID"]} != {want}')
    env['PATH'] = env['CUBRID'] + '/bin:' + env['PATH']
    return env


def command(argv, prefix, env=None, timeout=180, cwd=None):
    prefix = Path(prefix); prefix.parent.mkdir(parents=True, exist_ok=True)
    out_path, err_path = Path(str(prefix) + '.stdout'), Path(str(prefix) + '.stderr')
    if out_path.exists():
        raise RuntimeError('preserving existing logs ' + str(prefix))
    with out_path.open('w') as out, err_path.open('w') as err:
        child = subprocess.Popen(argv, env=env, cwd=cwd, stdin=subprocess.DEVNULL, stdout=out, stderr=err,
                                 start_new_session=True, close_fds=True)
        rc = child.wait(timeout=timeout)
    if rc:
        raise RuntimeError(f'command {argv[:4]} failed {rc}: {prefix}')
    return out_path


def servers(env, db):
    found = []; exe = (Path(env['CUBRID']) / 'bin/cub_server').resolve()
    for p in Path('/proc').iterdir():
        if not p.name.isdigit(): continue
        try:
            if (p / 'exe').resolve() != exe: continue
            e = dict(s.split(b'=', 1) for s in (p / 'environ').read_bytes().split(b'\0') if b'=' in s)
            if all(e.get(k.encode(), b'').decode() == env.get(k, '') for k in ['CUBRID', 'CUBRID_CONF', 'CUBRID_DATABASES']) \
                    and re.search(rf'\b{db}\b', (p / 'cmdline').read_bytes().replace(b'\0', b' ').decode()):
                found.append(int(p.name))
        except (FileNotFoundError, PermissionError, ProcessLookupError):
            pass
    return found


def registry(env):
    text = (Path(env['CUBRID_DATABASES']) / 'databases.txt').read_text()
    names = sorted(l.split()[0] for l in text.splitlines() if l.strip() and not l.lstrip().startswith('#'))
    if names != sorted(DBS):
        raise RuntimeError('unexpected registrations ' + repr(names))


def start(label, db, name):
    env = environment(label); registry(env)
    for other in DBS:
        if servers(env, other): raise RuntimeError('already running owned server ' + other)
    command(['taskset', '-c', '16-19', env['CUBRID'] + '/bin/cubrid', 'server', 'start', db], ROOT / 'lifecycle' / name, env, 120)
    pids = servers(env, db)
    if len(pids) != 1: raise RuntimeError('server identity missing ' + str(pids))
    command(['taskset', '-apc', '16-19', str(pids[0])], ROOT / 'lifecycle' / (name + '-affinity'), env)
    return env, pids[0]


def stop(label, db, name, env):
    registry(env)
    command([env['CUBRID'] + '/bin/cubrid', 'server', 'stop', db], ROOT / 'lifecycle' / name, env, 120)
    command([env['CUBRID'] + '/bin/cubrid', 'service', 'stop'], ROOT / 'lifecycle' / (name + '-service'), env, 120)
    if servers(env, db): raise RuntimeError('server remains')


def sql(label, db, name, text, env, timeout=3600):
    path = ROOT / label / (name + '.sql'); path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists(): raise RuntimeError('SQL exists ' + str(path))
    path.write_text(text)
    out = command([env['CUBRID'] + '/bin/csql', '-C', '-u', 'dba', '--no-pager', '--string-width', '1000000', '-t', '-N',
                   '-i', str(path), db], ROOT / label / name, env, timeout)
    if re.search('ERROR:|Error:', Path(str(ROOT / label / name) + '.stderr').read_text()):
        raise RuntimeError('SQL failed ' + str(out))
    return out


def gen(script, *args):
    return subprocess.run(['python3', '-B', str(script), *args], capture_output=True, text=True, check=True).stdout


def storage_sql(label, tables):
    q = []
    for t in tables:
        q.append(f'SHOW HEAP CAPACITY OF {t};')
        if label != 'base': q.append(f'SHOW HEAP OOS OF {t};')
    return ';line on\n' + '\n'.join(q) + '\n'


def prepare(label):
    path = ROOT / label; path.mkdir(exist_ok=False)
    pre = subprocess.run(['direnv', 'exec', str(wt(label)), 'sh', '-c', 'printf "%s\\n%s" "$CUBRID" "$PRESET_MODE"'],
                         capture_output=True, text=True, check=True, cwd=wt(label)).stdout.split('\n')
    command(['direnv', 'exec', str(wt(label)), 'cub-workenv', 'init', '--worktree', str(wt(label)), '--install', pre[0],
             '--preset', pre[1], '--no-db'], path / 'init', None, 600, cwd=wt(label))
    env = environment(label)
    cc = (wt(label) / f'build_preset_{PRESET}' / 'compile_commands.json').read_text()
    if 'CUBRID_UNIT_TEST_ENABLED' in cc: raise RuntimeError('unit-test instrumentation in build')
    conf = Path(env['CUBRID_CONF_FILE']); text = conf.read_text()
    text = re.sub(r'(?m)^data_buffer_size=.*$', 'data_buffer_size=512M', text)
    text = re.sub(r'(?m)^log_buffer_size=.*$', 'log_buffer_size=16M', text)
    text = re.sub(r'(?m)^max_clients=.*$', 'max_clients=20', text)
    conf.write_text(text + CONF_TAIL); (path / 'cubrid.conf').write_text(conf.read_text())
    for db in DBS:
        command(['cub-workenv', 'create-db', db, '--worktree', str(wt(label)), '--path', str(path / ('database-' + db))],
                path / ('create-' + db), env, 600, cwd=wt(label))
    env = environment(label)
    io_fixture = gen(H / 'io/io_bench.py', 'fixture', '--rows', '100000')
    sw_fixture = gen(H / 'sweep.py', 'fixture') + gen(H / 'bench.py', 'fixture') \
        + ''.join(gen(H / 'ordinary.py', 'fixture', '--prefix', f'r{r}_') for r in (1, 2))
    (ROOT / 'fixtures').mkdir(exist_ok=True)
    for name, text in (('io-fixture.sql', io_fixture), ('sw-fixture.sql', sw_fixture)):
        f = ROOT / 'fixtures' / name
        if f.exists() and f.read_text() != text: raise RuntimeError('fixture drift ' + name)
        f.write_text(text)
    for db, fixture, tables in ((IO_DB, io_fixture, ['perf_heap_14500', 'perf_overflow_22000']),
                                (SW_DB, sw_fixture, ['w36', 'w47', 'w78', 'w110', 'n', 'r1_seed', 'r2_seed'])):
        env, pid = start(label, db, f'{label}-{db}-load-start')
        try:
            sql(label, db, f'{db}-load', fixture, env)
            sql(label, db, f'{db}-storage', storage_sql(label, tables), env)
            sql(label, db, f'{db}-charset', ';line on\n' + ''.join(f'SHOW CREATE TABLE {t};\n' for t in tables)
                + "SELECT charset, lang FROM db_root;\nSELECT CASE WHEN 'A'='a' THEN 1 ELSE 0 END;\n", env)
            if db == IO_DB:
                sql(label, db, f'{db}-validate', ''.join(
                    f'SELECT COUNT(*), COUNT(DISTINCT id), COUNT(DISTINCT lookup_key), MIN(id), MAX(id), SUM(id), SUM(hot_col) FROM {t};\n'
                    for t in tables), env)
            command([env['CUBRID'] + '/bin/cubrid', 'spacedb', '-C', '--size-unit=M', db], path / f'{db}-spacedb', env)
            command([env['CUBRID'] + '/bin/cubrid', 'paramdump', '-C', db], path / f'{db}-paramdump', env)
        finally:
            stop(label, db, f'{label}-{db}-load-stop', env)
    (path / 'receipt.json').write_text(json.dumps({
        'source': source(label), 'fixtures': {n: hashlib.sha256((ROOT / 'fixtures' / n).read_bytes()).hexdigest()
                                              for n in ('io-fixture.sql', 'sw-fixture.sql')},
        'environment': {k: env[k] for k in env if k.startswith('CUBRID') or k in ('LANG', 'LC_ALL', 'PRESET_MODE')}}, indent=2) + '\n')
    print(label, 'prepared', flush=True)


ORDERS = [['base', 'head', 'thr'], ['thr', 'head', 'base'], ['head', 'thr', 'base'], ['base', 'thr', 'head'],
          ['head', 'base', 'thr'], ['thr', 'base', 'head']]


def cpu(rounds):
    for r in range(1, rounds + 1):
        for label in ORDERS[(r - 1) % len(ORDERS)]:
            name = f'cpu-r{r}-{label}'
            env, pid = start(label, SW_DB, name + '-start')
            try:
                common = ['--database', SW_DB, '--server-pid', str(pid), '--label', label, '--source', source(label)]
                oos = [] if label == 'base' else ['--show-oos']
                command(['python3', '-B', str(H / 'sweep.py'), 'measure', *common, '--output', str(ROOT / 'cpu' / name / 'sweep'), *oos],
                        ROOT / 'harness-logs' / (name + '-sweep'), env, 7200)
                command(['python3', '-B', str(H / 'ordinary.py'), 'measure', '--prefix', f'r{r}_', *common,
                         '--output', str(ROOT / 'cpu' / name / 'ordinary'), *oos], ROOT / 'harness-logs' / (name + '-ordinary'), env, 7200)
                command(['python3', '-B', str(H / 'bench.py'), 'measure', *common, '--output', str(ROOT / 'cpu' / name / 'bench')],
                        ROOT / 'harness-logs' / (name + '-bench'), env, 7200)
            finally:
                stop(label, SW_DB, name + '-stop', env)
            print(name, 'done', flush=True)


def io_sample(label, cache, layout, case, repeat, env, pid, warmup=False, prefix=''):
    name = f'{prefix}{cache}-{layout}-{case}-{repeat}-{label}' + ('-warmup' if warmup else '')
    out = ROOT / ('smoke-samples' if prefix else 'samples') / name
    cmd = ['python3', '-B', str(H / 'io/io_bench.py'), 'sample', '--database', IO_DB, '--server-pid', str(pid), '--label', label,
           '--source', source(label), '--worktree', str(wt(label)), '--output', str(out), '--layout', layout, '--case', case,
           '--cache', cache, '--repeat', str(repeat), '--client-cpu', '12']
    if warmup: cmd += ['--warmup']
    command(cmd, ROOT / 'harness-logs' / name, env, 600)
    s = json.loads((out / 'sample.json').read_text())
    print(name, round(s['elapsed_seconds'], 3), s.get('trace'), flush=True)


def smoke():
    for label in ENGINES:
        env, pid = start(label, IO_DB, label + '-smoke-start')
        try:
            for layout in ['heap', 'overflow']:
                for case in ['q1', 'q2', 'q3', 'q4', 'q5']:
                    io_sample(label, 'warm', layout, case, 0, env, pid, True, 'smoke-')
        finally:
            stop(label, IO_DB, label + '-smoke-stop', env)


def io():
    for layout in ['heap', 'overflow']:
        for case in ['q1', 'q2', 'q3', 'q4', 'q5']:
            for repeat in range(1, 6):
                for label in ORDERS[(repeat - 1) % len(ORDERS)]:
                    name = f'restart-{layout}-{case}-{repeat}-{label}'
                    env, pid = start(label, IO_DB, name + '-start')
                    try:
                        io_sample(label, 'restart-only', layout, case, repeat, env, pid)
                    finally:
                        stop(label, IO_DB, name + '-stop', env)
    for group, (layout, case) in enumerate((l, c) for l in ['heap', 'overflow'] for c in ['q1', 'q2', 'q3', 'q4', 'q5']):
        for label in ORDERS[group % len(ORDERS)]:
            name = f'warm-{layout}-{case}-{label}'
            env, pid = start(label, IO_DB, name + '-start')
            try:
                io_sample(label, 'warm', layout, case, 0, env, pid, True)
                for repeat in range(1, 6):
                    io_sample(label, 'warm', layout, case, repeat, env, pid)
            finally:
                stop(label, IO_DB, name + '-stop', env)


if __name__ == '__main__':
    a = argparse.ArgumentParser()
    a.add_argument('action', choices=['prepare', 'smoke', 'cpu', 'io'])
    a.add_argument('--label', choices=ENGINES)
    a.add_argument('--rounds', type=int, default=2)
    args = a.parse_args()
    if args.action == 'prepare': prepare(args.label)
    elif args.action == 'smoke': smoke()
    elif args.action == 'cpu': cpu(args.rounds)
    else: io()
