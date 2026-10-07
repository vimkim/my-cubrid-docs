#!/usr/bin/env python3
"""Check partition loader semantics in a fresh, allocated host work environment."""
import json
import os
from pathlib import Path
import subprocess
import sys


destination = Path(sys.argv[1]).resolve()
destination.mkdir(parents=True, exist_ok=False)
source = Path.cwd()
database = os.environ.get('PR7927_PROBE_DATABASE', 'probe7927')
events = []


def run(label, command, required_exit=0):
    path = destination / (label + '.txt')
    # Startup daemons inherit stdout. A file preserves output without waiting
    # for a pipe held open by the master/server after the utility exits.
    with path.open('w') as stream:
        result = subprocess.run(command, cwd=destination, text=True,
                                stdout=stream, stderr=subprocess.STDOUT)
    result.stdout = path.read_text()
    events.append({'label': label, 'command': command, 'exit': result.returncode})
    (destination / 'events.json').write_text(json.dumps(events, indent=2) + '\n')
    if required_exit is not None and result.returncode != required_exit:
        raise RuntimeError(f'{label}: unexpected exit {result.returncode}')
    return result


def sql(label, statement):
    return run(label, ['csql', '-C', '-u', 'dba', '-t', '-N', '-c', statement, database]).stdout.strip()


def scalar(label, statement, expected):
    actual = sql(label, statement)
    if actual != str(expected):
        raise RuntimeError(f'{label}: expected {expected}, got {actual!r}')


def load(label, path, expected_inserted, expected_failed,
         expected_error='Appropriate partition does not exist'):
    result = run(label, ['cubrid', 'loaddb', '-C', '-v', '-u', 'dba', '-c', '100',
                         '-d', str(path), database], None)
    expected = f'Total {expected_inserted} object(s) inserted, {expected_failed} object(s) failed.'
    if expected not in result.stdout:
        raise RuntimeError(f'{label}: missing {expected}')
    if expected_failed:
        if result.returncode == 0 or expected_error not in result.stdout:
            raise RuntimeError(f'{label}: invalid partition row accepted or wrong error')
    elif result.returncode != 0:
        raise RuntimeError(f'{label}: valid load rejected')


try:
    run('engine_revision', ['git', '-C', str(source), 'rev-parse', 'HEAD'])
    run('engine_release', ['cubrid_rel'])
    run('create', ['cub-workenv', 'create-db', database, '--worktree', str(source)])
    run('start', ['cubrid', 'server', 'start', database])
    sql('schema', 'create table t(i int) partition by range(i) '
        '(partition p0 values less than(10)); insert into t values(1);')
    run('unload', ['cubrid', 'unloaddb', '-u', 'dba', database])
    objects = destination / (database + '_objects')
    original = objects.read_text()
    if not any(line.startswith('%class ') and 't__p__p0' in line for line in original.splitlines()):
        raise RuntimeError('Generated objects did not target the child partition')
    valid = destination / 'valid.objects'
    valid.write_text(original)
    objects.write_text(original + '100\n')
    sql('empty_before_invalid', 'delete from t;')
    load('generated_invalid_child', objects, 0, 1)
    for table in ['t', 't__p__p0']:
        scalar('rollback_' + table, 'select count(*) from ' + table, 0)
    load('generated_valid_child', valid, 1, 0)
    for table in ['t', 't__p__p0']:
        scalar('recovery_' + table, 'select case when count(*)=1 and min(i)=1 and max(i)=1 '
               'then 1 else 0 end from ' + table, 1)
    sql('routing_schema', 'create table tr(i int) partition by range(i) '
        '(partition p0 values less than(10), partition p1 values less than(20));')
    fixtures = {
        'root_valid': '%class dba.tr (i)\n1\n11\n',
        'child_valid': '%class dba.tr__p__p0 (i)\n2\n',
        'child_invalid_sibling': '%class dba.tr__p__p0 (i)\n3\n11\n',
        'root_invalid': '%class dba.tr (i)\n4\n100\n',
        'root_recovery': '%class dba.tr (i)\n12\n',
    }
    for label, text in fixtures.items():
        (destination / (label + '.objects')).write_text(text)
    load('root_valid', destination / 'root_valid.objects', 2, 0)
    load('child_valid', destination / 'child_valid.objects', 1, 0)
    for label in ['before_failure', 'after_child_failure', 'after_root_failure']:
        if label == 'after_child_failure':
            load('child_invalid_sibling', destination / 'child_invalid_sibling.objects', 0, 1,
                 'Invalid value for partition definition')
        if label == 'after_root_failure':
            load('root_invalid', destination / 'root_invalid.objects', 0, 1)
        for table, count, minimum, maximum in [('tr', 3, 1, 11), ('tr__p__p0', 2, 1, 2), ('tr__p__p1', 1, 11, 11)]:
            scalar(label + '_' + table, f'select case when count(*)={count} and min(i)={minimum} '
                   f'and max(i)={maximum} then 1 else 0 end from {table}', 1)
    load('root_recovery', destination / 'root_recovery.objects', 1, 0)
    scalar('root_recovery_count', 'select count(*) from tr', 4)
    scalar('root_recovery_destination', 'select count(*) from tr__p__p1 where i=12', 1)
    (destination / 'verdict.txt').write_text('PASS: generated child, root routing, sibling rejection, '
                                           'rollback/counts, committed-row preservation and recovery\n')
finally:
    run('stop', ['cubrid', 'server', 'stop', database], None)
    run('service_stop', ['cubrid', 'service', 'stop'], None)
    # Keep DB and its creation receipt for inspection. No filesystem deletion.
