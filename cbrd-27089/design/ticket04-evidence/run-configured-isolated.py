#!/usr/bin/env python3
"""Run every configured test binary with a fresh private fixture; never execute shared-path fixture commands."""
import json
from pathlib import Path
import subprocess
import sys

source = Path('/home/vimkim/gh/cb/CBRD-27089-has-oos-but-no-oos')
root = Path(__file__).resolve().parent
if (root / 'configured-suite-results.json').exists():
    raise SystemExit('Existing suite evidence must not be overwritten; select a new evidence directory/run label.')
runner = root.parent / 'ticket01-evidence/run-isolated.py'
scratch = source / '.artifacts/pr7600-independent-RjRhFS'
catalog = json.loads(subprocess.check_output(
    ['ctest', '--test-dir', str(source / 'build_preset_debug_gcc'), '--show-only=json-v1'], text=True))
records = []
sa = {'test_oos', 'test_oos_delete', 'test_oos_remove_file', 'test_oos_bestspace',
      'test_oos_growth_sweep', 'test_oos_record_flags', 'test_byte_span_writer', 'test_oos_tde_gate'}
server = {'test_oos_server', 'test_oos_delete_server', 'test_oos_remove_file_server',
          'test_oos_mock_vacuum_server', 'test_oos_vacuum_server', 'test_oos_real_vacuum_server'}
selected = [t for t in catalog['tests'] if t['name'] not in {'oos_setup_db', 'oos_cleanup_db'}]
assert len(selected) == 25, 'Configured suite changed; inspect before running'
for test in selected:
    name = test['name']
    assert test['command'] == [str(source / 'build_preset_debug_gcc/bin' / name)]
    assert name in sa or name in server or name.startswith('test_oos_sql_')
    mode = ['--server-test'] if name in server else ['--sa-test'] if name in sa else []
    label = 'verified-full-' + name.replace('_', '-')
    command = [sys.executable, str(runner), label, '--binary', name, '--timeout', '600',
               '--scratch-root', str(scratch), '--output-dir', str(root)] + mode
    result = subprocess.run(command)
    records.append({'test': name, 'exit_code': result.returncode, 'evidence': label + '.json'})
report = dict(catalog=catalog, results=records,
              fixture_substitution='Each binary uses a fresh isolated setup; original shared setup/cleanup never executed.',
              differences='Private cwd/config/database per binary; 600s diagnostic timeout; no test filters.',
              success=all(r['exit_code'] == 0 for r in records))
(root / 'configured-suite-results.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(records, indent=2))
raise SystemExit(0 if report['success'] else 1)
