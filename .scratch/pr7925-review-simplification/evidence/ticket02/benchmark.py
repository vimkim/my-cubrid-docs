#!/usr/bin/env python3
"""Focused debug loader measurements; retain CLI-owned DBs and all receipts.

Run through selected installation-use lock. Creates two wholly internal DBs
using cub-workenv (one per workload), never invokes deletion or process cleanup.
Each repeat uses a new table; verifies values and OOS placement before DROP.
"""
import csv
import os
from pathlib import Path
import random
import re
import subprocess
import sys

phase = sys.argv[1]
worktree = Path('/home/vimkim/gh/cb/pr7925-02-record-owner')
output = Path('/home/vimkim/tmp/pr7925-ticket02-evidence') / ('benchmark-' + phase)
output.mkdir()
assert os.environ['CUBRID'] == '/home/vimkim/.cub/install/pr7925-02-record-owner/debug_gcc'
assert os.environ['PRESET_MODE'] == 'debug_gcc'

def run(argv, stem, input_text=None):
    with (output / (stem + '.out')).open('w') as log:
        subprocess.run(argv, input=input_text, text=True, stdout=log,
                       stderr=subprocess.STDOUT, check=True, timeout=180, cwd=worktree)
    text = (output / (stem + '.out')).read_text()
    if 'ERROR:' in text:
        raise RuntimeError(stem + ': ERROR in output')
    return text

with (output / 'results.csv').open('w') as result:
    writer = csv.writer(result)
    writer.writerow(['phase', 'workload', 'rows', 'payload_bytes', 'repeat', 'elapsed', 'user_cpu', 'system_cpu'])
    for workload, rows, size in [('small', 50000, 48), ('oos', 5000, 5000)]:
        name = 't02_' + phase[:2] + '_' + workload
        # Path is inside the selected worktree; CLI records creation provenance.
        dbpath = worktree / '.cub-workenv' / 'ticket02-benchmark' / name
        run(['cub-workenv', 'create-db', name, '--worktree', str(worktree), '--path', str(dbpath)], workload + '-create')
        rng = random.Random(27424)
        payload = bytes(rng.randrange(256) for _ in range(size)).hex()
        for repeat in range(3):
            stem = workload + '-' + str(repeat)
            table = 'bench_' + str(repeat)
            run(['csql', '-S', '-u', 'dba', '-c', 'CREATE TABLE ' + table + '(id INTEGER, v BIT VARYING); COMMIT;', name], stem + '-schema')
            fixture = output / (stem + '.objects')
            with fixture.open('w') as objects:
                objects.write('%class ' + table + ' (id v)\n')
                for i in range(rows):
                    objects.write(str(i) + " X'" + payload + "'\n")
            timing = output / (stem + '.timing')
            run(['/usr/bin/time', '-f', '%e,%U,%S', '-o', str(timing), 'cubrid', 'loaddb', '-S', '-u', 'dba', '-d', str(fixture), name], stem + '-load')
            query = 'SELECT CASE WHEN COUNT(*)=' + str(rows) + ' AND MIN(id)=0 AND MAX(id)=' + str(rows-1)
            query += " AND SUM(CASE WHEN v=X'" + payload + "' THEN 1 ELSE 0 END)=" + str(rows)
            query += " THEN 'VALUE_OK' ELSE 'VALUE_BAD' END AS verdict FROM " + table + '; SHOW HEAP OOS OF ' + table + ';'
            text = run(['csql', '-S', '-u', 'dba', '--line-output', '-c', query, name], stem + '-check')
            assert "'VALUE_OK'" in text and 'VALUE_BAD' not in text
            counts = [int(n) for n in re.findall(r'Oos_num_recs\s*:\s*(\d+)', text)]
            assert counts == ([0] if workload == 'small' else [rows]), counts
            run(['csql', '-S', '-u', 'dba', '-c', 'DROP TABLE ' + table + '; COMMIT;', name], stem + '-drop')
            values = timing.read_text().strip().split(',')
            writer.writerow([phase, workload, rows, size, repeat] + values)
            result.flush()
            print(phase, workload, repeat, values, flush=True)
