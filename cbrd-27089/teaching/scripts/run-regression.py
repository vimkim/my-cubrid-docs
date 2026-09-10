#!/usr/bin/env python3
"""Run the existing PR regression in an owned, isolated SA database environment."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
SOURCE = Path('/home/vimkim/gh/cb/CBRD-27089-has-oos-but-no-oos')
INSTALL = Path('/home/vimkim/.cub/install/CBRD-27089-has-oos-but-no-oos/debug_gcc')
BINARY = SOURCE / 'build_preset_debug_gcc/bin/test_oos_sql_show'

def main():
    sandbox = Path(tempfile.mkdtemp(prefix='pr7600-teaching-'))
    home = sandbox / 'install'
    home.mkdir()
    for item in INSTALL.iterdir():
        if item.name == 'conf':
            shutil.copytree(item, home / item.name)
        elif item.is_dir() and item.name in ('log', 'var', 'tmp'):
            (home / item.name).mkdir()
        else:
            (home / item.name).symlink_to(item, target_is_directory=item.is_dir())
    databases = sandbox / 'databases'
    databases.mkdir()
    env = dict(os.environ, CUBRID=str(home), CUBRID_DATABASES=str(databases))
    env['PATH'] = str(home / 'bin') + os.pathsep + env.get('PATH', '')
    env['LD_LIBRARY_PATH'] = str(home / 'lib') + os.pathsep + env.get('LD_LIBRARY_PATH', '')
    commands = [
        ['bash', str(SOURCE / 'unit_tests/oos/scripts/setup_unittestdb.sh')],
        [str(BINARY), '--gtest_filter=OosSqlShow.PartitionedForceOutlineStoresOosInPrunedHeap'],
    ]
    records = []
    for command in commands:
        result = subprocess.run(command, env=env, cwd=sandbox, text=True, stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, timeout=120)
        records.append({'command': command, 'exit_code': result.returncode, 'output': result.stdout})
        print(result.stdout, flush=True)
        if result.returncode:
            break
    result = {'source_revision': subprocess.check_output(['git', '-C', str(SOURCE), 'rev-parse', 'HEAD'], text=True).strip(),
              'binary': str(BINARY), 'binary_sha256': hashlib.sha256(BINARY.read_bytes()).hexdigest(),
              'sandbox': str(sandbox), 'environment': {key: env[key] for key in ('CUBRID', 'CUBRID_DATABASES', 'LD_LIBRARY_PATH')},
              'records': records, 'cleanup': 'Owned private SA database and copied configuration retained at sandbox path for inspection; no server started or shared database touched.'}
    (ROOT / 'evidence/regression.json').write_text(json.dumps(result, indent=2) + '\n')
    raise SystemExit(records[-1]['exit_code'])

if __name__ == '__main__':
    main()
