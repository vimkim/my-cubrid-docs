#!/usr/bin/env python3
"""Fixed-source receipt and unchanged-baseline identity verification."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess

worktree = Path('/home/vimkim/gh/cb/pr7925-02-record-owner')
evidence = Path('/home/vimkim/tmp/pr7925-ticket02-evidence')
base = 'b59f243fd0f30bb94344558ffa1755c37c43d2d4'
dependency = '4be72fc209ae9cb8aa1709573d7d0ae7fc06df7c'
final = '1932b3ec3d1b83bec83b7de1a6dd482f3a03b63d'

def git(*args):
    return subprocess.check_output(['git', *args], cwd=worktree, text=True).strip()

baseline = json.loads((evidence / 'cases-baseline.json').read_text())
current = json.loads((evidence / 'cases-final.json').read_text())
def identities(receipt):
    return {(case['suite'], case['name']) for file in receipt['files'] for case in file['cases']}
missing = sorted(identities(baseline) - identities(current))
focused = []
for file in current['files']:
    if Path(file['file']).name in ('test_oos_sql_workspace_bytes.xml', 'test_oos_sql_deferred_write.xml', 'test_oos_workspace.xml'):
        focused.append({'xml': Path(file['file']).name, 'cases': len(file['cases']), 'failures': sum(case['failure'] for case in file['cases']), 'skipped': sum(case['skipped'] for case in file['cases']), 'disabled': file['declared_disabled']})
summary = current['summary']
assert summary == {'xml_files': 32, 'cases': 374, 'run': 374, 'failures': 0, 'skipped': 0, 'disabled': 0}
assert len(identities(baseline)) == 70 and not missing
assert sum(file['cases'] for file in focused) == 70
assert git('rev-parse', 'HEAD') == final
assert git('rev-parse', 'review/pr7925-combined') == final
assert git('status', '--short', '--untracked-files=all') == ''
assert git('-C', 'cubrid-cci', 'status', '--short', '--untracked-files=all') == ''
assert git('diff', '--name-only', base, final).splitlines() == ['src/transaction/locator_sr.c']
assert git('rev-parse', dependency + ':src/storage') == git('rev-parse', final + ':src/storage')
subprocess.run(['git', 'diff', '--check', base, final], cwd=worktree, check=True)
subprocess.run(['git', 'merge-base', '--is-ancestor', dependency, final], cwd=worktree, check=True)
source = worktree / 'src/transaction/locator_sr.c'
source_sha256 = hashlib.sha256(source.read_bytes()).hexdigest()
assert source_sha256 == 'e292ade0df72742d660a21f85ba29f00c65e340490350c765256f89d9896495a'
comparison = worktree / 'unit_tests/oos/sql/test_oos_sql_workspace_bytes.cpp'
assert hashlib.sha256(comparison.read_bytes()).hexdigest() == 'adc506598e3e69e4346e2392611b95cb00dbda8c060f9e3260e42f90c305feb6'
log = (evidence / 'oos-full-final.log').read_text()
assert '100% tests passed, 0 tests failed out of 38' in log
seconds = float(re.search(r'Total Test time \(real\) = ([0-9.]+) sec', log).group(1))
out = {'recorded_utc': datetime.now(timezone.utc).isoformat(), 'source': {'worktree': str(worktree), 'branch': git('branch', '--show-current'), 'base': base, 'dependency': dependency, 'historical_first_commit': '9ba5e42ad6dfaa74cc9062f6fe55a459ba088924', 'final_commit': final, 'private_integration_tip': git('rev-parse', 'review/pr7925-combined'), 'sha256': source_sha256, 'storage_tree': git('rev-parse', final + ':src/storage'), 'source_clean': True, 'owned_cci_clean': True, 'changed_files': ['src/transaction/locator_sr.c']},
       'ctest': {'passed': 38, 'total': 38, 'seconds': seconds, 'log': str(evidence / 'oos-full-final.log')},
       'google_test': summary, 'focused_cases_retained': focused, 'baseline_identities': 70, 'missing_baseline_identities': missing,
       'measurements': 'benchmark-summary-final.json', 'inventory': 'retained-inventory.json',
       'independent_reviews': {'standards': '0 breaches/0 actionable smells', 'spec': '0 remaining source findings/0 scope creep'},
       'limits': ['Private partition checks are interim until accepted prerequisite is integrated into shared feature/oos-merge.', 'Three sequential debug measurement samples per workload/revision; no Release improvement claim.', 'Fresh-workspace-LOB INSERT and failed-unlogged recovery remain excluded.', 'Doctor reports unconfirmed retained socket entries and inaccessible host PIDs; no cleanup or inactivity claim.']}
(evidence / 'verification-final.json').write_text(json.dumps(out, indent=2) + '\n')
print(json.dumps(out))
