#!/usr/bin/env python3
"""Serial native read-path experiment; execute in the selected completed workenv."""
import argparse
import hashlib
import importlib.util
import json
import os
import re
from pathlib import Path
import statistics
import subprocess
import time

ROOT = Path(os.environ['CBRD_SP_OUTPUT']).resolve()
BENCH = Path(os.environ['CBRD_SP_HARNESS']).resolve()
def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result
bench = module('bench', BENCH)

def command(argv, prefix, timeout=120, required=True):
    with Path(str(prefix)+'.stdout').open('w') as out, Path(str(prefix)+'.stderr').open('w') as err:
        child = subprocess.Popen(argv, stdin=subprocess.DEVNULL, stdout=out, stderr=err,
                                 start_new_session=True, close_fds=True)
        rc = child.wait(timeout=timeout)
    if required and rc:
        raise RuntimeError(f'{argv[0]} exited {rc}: {prefix}')
    return rc


def servers(install):
    found = []
    for proc in Path('/proc').iterdir():
        if not proc.name.isdigit():
            continue
        try:
            if (proc/'exe').resolve() != (install/'bin/cub_server').resolve():
                continue
            env = dict(x.split(b'=',1) for x in (proc/'environ').read_bytes().split(b'\0') if b'=' in x)
            argv = (proc/'cmdline').read_bytes().replace(b'\0',b' ').decode()
            if env.get(b'CUBRID_CONF_FILE',b'').decode() == os.environ['CUBRID_CONF_FILE'] and re.search(r'\boos27785\b',argv):
                found.append(int(proc.name))
        except (FileNotFoundError,PermissionError,ProcessLookupError):
            continue
    return found


import types
instance = types.SimpleNamespace(command=command, servers=servers)
ROWS = 20000
def literal(size):
    return "X'" + 'a15c' * (size // 2) + "'"
QUERIES = dict(bench.QUERIES)
ANSWERS = bench.expected(200000)
for table, size, count in [('sp_one', 5000, 1), ('sp_two', 5000, 2), ('sp_large', 32000, 1)]:
    QUERIES[table + '_small'] = f'SELECT SUM(CAST(v AS BIGINT)) FROM {table};'
    ANSWERS[table + '_small'] = (990000,)
    checks = ' + '.join(f'CASE WHEN {col} = {literal(size)} THEN 1 ELSE 0 END'
                        for col in ('a', 'b')[:count])
    QUERIES[table + '_full'] = f'SELECT SUM({checks}) FROM {table};'
    ANSWERS[table + '_full'] = (ROWS * count,)
    lengths = ' + '.join(f'BIT_LENGTH({col})' for col in ('a', 'b')[:count])
    QUERIES[table + '_length'] = f'SELECT SUM(CAST({lengths} AS BIGINT)) FROM {table};'
    ANSWERS[table + '_length'] = (ROWS * size * 8 * count,)
    if table == 'sp_large':
        for kind in ('small', 'full', 'length'):
            key = table + '_' + kind
            QUERIES[key] = QUERIES[key].replace('FROM sp_large;', 'FROM sp_large WHERE id <= 1000;')
        ANSWERS[table + '_small'] = (49500,)
        ANSWERS[table + '_full'] = (1000,)
        ANSWERS[table + '_length'] = (1000 * size * 8,)

def fixture_sql():
    sql = ''
    for table, size, count in [('sp_one', 5000, 1), ('sp_two', 5000, 2), ('sp_large', 32000, 1)]:
        cols = ', '.join(f'{col} BIT VARYING({size * 8})' for col in ('a', 'b')[:count])
        vals = ', '.join(literal(size) for _ in range(count))
        sql += (f'CREATE TABLE {table} (id INTEGER, v INTEGER, {cols});\n'
                f'INSERT INTO {table} SELECT id, v, {vals} FROM n WHERE id <= {ROWS};\n'
                f'COMMIT;\nUPDATE STATISTICS ON {table};\n')
    return sql

def sql_run(sql, prefix, install):
    path = Path(str(prefix) + '.sql')
    path.write_text(sql)
    bench.run(bench.csql_command('oos27785', path, str(install / 'bin/csql')), prefix, 240)
    return bench.results(Path(str(prefix) + '.stdout'))

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--label', required=True)
    p.add_argument('--name', required=True)
    p.add_argument('--setup', action='store_true')
    p.add_argument('--ordinary', action='store_true')
    p.add_argument('--profile', action='store_true')
    p.add_argument('--length-only', action='store_true')
    p.add_argument('--check-content', action='store_true')
    p.add_argument('--serial', action='store_true')
    p.add_argument('--scans', type=int, default=20)
    p.add_argument('--runs', type=int, default=5)
    a = p.parse_args()
    out = ROOT / a.label / a.name
    out.mkdir(parents=True, exist_ok=False)
    install = Path(os.environ['CUBRID']).resolve()
    worktree = Path(os.environ['CUBRID_CONF_FILE']).parents[2]
    registry = Path(os.environ['CUBRID_DATABASES']) / 'databases.txt'
    entries = [line.split()[0] for line in registry.read_text().splitlines()
               if line.strip() and not line.lstrip().startswith('#')]
    assert entries == ['oos27785'], entries
    assert not instance.servers(install), 'pre-existing server; preserve it'
    assert (install / 'bin/csql').resolve() == Path(subprocess.check_output(['which', 'csql'], text=True).strip()).resolve()
    manifest = dict(label=a.label, name=a.name, scans=a.scans, runs=a.runs,
                    fixture_sha256=hashlib.sha256(fixture_sql().encode()).hexdigest(),
                    harness_sha256=bench.digest(__file__), samples=[], complete=False,
                    worktree=str(worktree), source=subprocess.check_output(['git', '-C', str(worktree), 'rev-parse', 'HEAD'], text=True).strip(),
                    source_files={}, install=str(install), executable_hashes={}, config=Path(os.environ['CUBRID_CONF_FILE']).read_text())
    for name in ('src/storage/heap_file.c', 'src/storage/heap_oos.cpp', 'src/storage/oos_file.cpp'):
        manifest['source_files'][name] = bench.digest(worktree / name) if (worktree / name).exists() else None
    for name in ('bin/csql', 'bin/cub_server', 'lib/libcubrid.so.11.5'):
        manifest['executable_hashes'][name] = bench.digest(install / name)
    manifest['source_diff'] = subprocess.check_output(['git', '-C', str(worktree), 'diff', 'dcbf09e', '--', 'src'], text=True)
    def save():
        (out / 'summary.json').write_text(json.dumps(manifest, indent=2) + '\n')
    save()
    try:
        instance.command(['taskset', '-c', '16-19', 'cubrid', 'server', 'start', 'oos27785'], out / 'start', timeout=45)
        pids = instance.servers(install)
        assert len(pids) == 1, pids
        pid = pids[0]
        instance.command(['taskset', '-apc', '16-19', str(pid)], out / 'affinity')
        manifest['server'] = bench.process_identity(pid)
        manifest['maps'] = Path(f'/proc/{pid}/maps').read_text()
        assert str((install / 'lib/libcubrid.so.11.5').resolve()) in manifest['maps']
        if a.setup:
            sql_run(fixture_sql(), out / 'fixture', install)
        queries = dict(list(QUERIES.items())[:2]) if a.ordinary else QUERIES
        if a.length_only:
            queries = {key: sql for key, sql in queries.items() if not key.endswith('_full')}
        if a.check_content:
            for key in ('sp_one_full', 'sp_two_full', 'sp_large_full'):
                assert sql_run(QUERIES[key], out / (key + '-content'), install) == [ANSWERS[key]]
        if a.serial:
            queries = {key: sql.replace('SELECT ', 'SELECT /*+ RECOMPILE PARALLEL(0) NO_PARALLEL_HEAP_SCAN */ ', 1)
                       for key, sql in queries.items()}
        manifest['queries'] = queries
        for case, sql in queries.items():
            result = sql_run(sql, out / (case + '-validate'), install)
            assert result == [ANSWERS[case]], (case, result)
            trace = 'SET TRACE ON;\n' + sql + '\nSHOW TRACE;\nSET TRACE OFF;\n'
            tracepath = out / (case + '-trace.sql')
            tracepath.write_text(trace)
            instance.command([str(install / 'bin/csql'), '-C', '-u', 'dba', '--no-pager', '--string-width', '1000000', '-i', str(tracepath), 'oos27785'], out / (case + '-trace'))
            path = out / (case + '.sql')
            path.write_text((sql + '\n') * a.scans)
            for run in range(a.runs):
                prefix = out / (case + f'-r{run}')
                cmd = ['perf', 'stat', '-x', ';', '-e', 'instructions:u,cycles:u,task-clock', '-p', str(pid), '-o', str(prefix) + '.perf', '--', 'taskset', '-c', '12']
                cmd += bench.csql_command('oos27785', path, str(install / 'bin/csql'))
                wall = bench.run(cmd, prefix, 240)
                assert bench.results(Path(str(prefix) + '.stdout')) == [ANSWERS[case]] * a.scans
                assert bench.process_identity(pid) == manifest['server']
                manifest['samples'].append(dict(case=case, run=run, warmup=run == 0, elapsed_seconds=wall, counters=bench.counters(str(prefix) + '.perf')))
                save()
            retained = [s['counters']['instructions:u']['value'] for s in manifest['samples'] if s['case'] == case and not s['warmup']]
            print(f'{a.label}/{a.name} {case}: {statistics.median(retained):.0f} instructions', flush=True)
            if a.profile and case in ('wide', 'sp_one_full', 'sp_two_full', 'sp_large_full', 'sp_one_length', 'sp_two_length', 'sp_large_length'):
                data = out / (case + '.data')
                instance.command(['perf', 'record', '-q', '-e', 'cycles:u', '-F', '999', '--call-graph', 'fp', '-p', str(pid), '-o', str(data), '--', 'taskset', '-c', '12'] + bench.csql_command('oos27785', path, str(install / 'bin/csql')), out / (case + '-record'), timeout=240)
                instance.command(['perf', 'report', '--stdio', '--no-children', '--no-inline', '--call-graph', 'none', '--percent-limit', '0.3', '--sort', 'symbol,dso', '-i', str(data)], out / (case + '-profile'), timeout=120)
        if not a.ordinary:
            for table in ('n', 'sp_one', 'sp_two', 'sp_large'):
                sql = f'SHOW HEAP CAPACITY OF {table};\n'
                if a.label != 'base':
                    sql += f'SHOW HEAP OOS OF {table};\n'
                sql_run(sql, out / (table + '-storage'), install)
        manifest['complete'] = True
        save()
    finally:
        instance.command(['cubrid', 'server', 'stop', 'oos27785'], out / 'stop', timeout=45, required=False)
        instance.command(['cubrid', 'service', 'stop'], out / 'service-stop', timeout=45, required=False)
        assert not instance.servers(install), 'owned server remained active'

if __name__ == '__main__':
    main()
