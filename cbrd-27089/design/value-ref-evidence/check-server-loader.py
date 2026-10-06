#!/usr/bin/env python3
"""Run against a fresh task-owned database in its initialized CUBRID environment.
Usage: python3 check-server-loader.py DATABASE ARTIFACT_DIRECTORY
The caller creates/starts and later stops the database; this script creates tables.
"""
import pathlib
import re
import subprocess
import sys

db, artifact_dir = sys.argv[1:]
out = pathlib.Path(artifact_dir).resolve()
out.mkdir(parents=True, exist_ok=True)

def run(args, name, success=True):
    result = subprocess.run(args, text=True, capture_output=True, timeout=120)
    (out / (name + '.log')).write_text(result.stdout + result.stderr)
    if success and result.returncode:
        raise RuntimeError(f'{name}: exit {result.returncode}; see {out}')
    return result

def sql(command, name):
    return run(['csql', '-C', '-u', 'dba', '-t', '-N', '-c', command, db], name).stdout

def scalar(command, expected, name):
    actual = sql(command, name).strip()
    assert actual == str(expected), (name, actual, expected)

def load(table, rows, name, success=True):
    data = out / (name + '.objects')
    with data.open('w') as f:
        f.write(f'%class {table}(id payload)\n')
        for row_id, count in rows:
            f.write(f"{row_id} X'{('AB' * count)}'\n")
    return run(['cubrid', 'loaddb', '-C', '-u', 'dba', '--no-statistics', '-d', str(data), db], name, success)

sql('CREATE TABLE oos_ref_bulk(id INT PRIMARY KEY, payload BIT VARYING STORAGE FORCE_OUTLINE); '
    'CREATE TABLE oos_ref_parts(id INT PRIMARY KEY, payload BIT VARYING STORAGE FORCE_OUTLINE) '
    'PARTITION BY RANGE(id) (PARTITION p0 VALUES LESS THAN(400), PARTITION p1 VALUES LESS THAN(800));', 'schema')
load('oos_ref_bulk', [(i, 20000) for i in range(600)], 'bulk')
scalar('SELECT COUNT(*) FROM oos_ref_bulk WHERE BIT_LENGTH(payload)=160000', 600, 'bulk-values')
load('oos_ref_bulk', [(1000, 9 * 1024 * 1024)], 'oversized-row')
scalar('SELECT BIT_LENGTH(payload) FROM oos_ref_bulk WHERE id=1000', 9 * 1024 * 1024 * 8, 'oversized-value')
load('oos_ref_parts', [(i, 20000) for i in range(800)], 'partition-root')
scalar('SELECT COUNT(*) FROM oos_ref_parts__p__p0 WHERE BIT_LENGTH(payload)=160000', 400, 'child-p0')
scalar('SELECT COUNT(*) FROM oos_ref_parts__p__p1 WHERE BIT_LENGTH(payload)=160000', 400, 'child-p1')
# A directly named child must reject a row outside its range.
rejected = load('oos_ref_parts__p__p0', [(900, 20000)], 'wrong-child', False)
assert rejected.returncode != 0, 'wrong-child unexpectedly succeeded'
scalar('SELECT COUNT(*) FROM oos_ref_parts', 800, 'after-rejection')
# A later operation remains usable after the failed load.
load('oos_ref_bulk', [(1001, 30000)], 'after-failure-load')
scalar('SELECT BIT_LENGTH(payload) FROM oos_ref_bulk WHERE id=1001', 240000, 'after-failure-value')
print('PASS bulk payload lifetime and 8MiB batching, 9MiB row, partition routing, child rejection and next load')
