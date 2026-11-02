#!/usr/bin/env python3
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess

parser = argparse.ArgumentParser(description='Verify retained AES crash evidence against a testcase commit without starting a database.')
parser.add_argument('--attempt', required=True, type=Path)
parser.add_argument('--tc', required=True, type=Path)
parser.add_argument('--commit', required=True)
args = parser.parse_args()
attempt, repo = args.attempt.resolve(strict=True), args.tc.resolve(strict=True)
commit = subprocess.check_output(['git', '-C', str(repo), 'rev-parse', args.commit + '^{commit}'], text=True).strip()
identity = json.loads((attempt / 'identity.json').read_text())
observation = json.loads((attempt / 'observation.json').read_text())
environment = json.loads((attempt / 'environment.json').read_text())
assert identity['encryption'] == environment['OOS_CRASH_ENCRYPTION'] == 'AES'
assert environment['TESTKIT_NATIVE'] == 'shell' and environment['TESTKIT_CONTAIN'] == '1'
assert identity['preflight_exit'] == 0 and not identity['commit_mismatch_exception_used']
preflight = (attempt / 'preflight.log').read_text()
assert 'commit_match=yes' in preflight and 'installed_commit=e3589ae' in preflight
assert observation['exit'] == 0 and not observation['deadline_outcome']
assert 0 < observation['invocation_seconds'] < 130
assert not observation['remaining_owned_processes'] and not observation['remaining_observed_namespace_holders']
for relative, digest in identity['runtime_hashes'].items():
    assert hashlib.sha256((attempt / 'cubrid' / relative).read_bytes()).hexdigest() == digest
assert hashlib.sha256(Path(identity['testkit']).read_bytes()).hexdigest() == identity['testkit_sha256']
assert int((attempt / 'exit.status').read_text()) == int((attempt / 'verify.status').read_text()) == 0
for filename, key in [('conf/shell.conf', 'config_sha256'), ('expected-cases.txt', 'expected_sha256')]:
    assert hashlib.sha256((attempt / filename).read_bytes()).hexdigest() == identity[key]
expected = (attempt / 'expected-cases.txt').read_text().splitlines()
assert expected == [str(attempt / 'corpus' / identity['canonical_case'])]
values = dict(line.split('=', 1) for line in (attempt / 'conf/shell.conf').read_text().splitlines() if line and not line.startswith('#') and '=' in line)
for key, value in {'parallel_slots': '1', 'scenario_disk': 'on', 'testcase_timeout_in_secs': '120', 'testcase_retry_num': '0', 'test_continue_yn': 'false', 'testcase_update_yn': 'false', 'case_patch_dir': ''}.items():
    assert values[key] == value, key
command = json.loads((attempt / 'command.json').read_text())
assert command[:4] == ['timeout', '--signal=TERM', '--kill-after=10s', '120s']
assert command[4:] == [identity['testkit'], 'shell', '-c', str(attempt / 'conf/shell.conf')]
proof_path = Path(identity['pruning_result'])
assert hashlib.sha256(proof_path.read_bytes()).hexdigest() == identity['pruning_result_sha256']
proof = json.loads(proof_path.read_text())
assert proof['passed'] and not proof['errors']
selected = proof['native_candidate']
assert selected['suite'] == 'heavy' and selected['case'] == 'crash_committed' and selected['variant'] == 'owner_omitted'
assert selected['post_exit'] == 0 and selected['keep_exit'] == 0
inventory = json.loads(Path(selected['inventory_after']).read_text())
assert len(inventory) == len(identity['inputs']) > 0
assert set(inventory) == {row['projected'] for row in identity['inputs']}
assert set(inventory) == {str(p.relative_to(attempt / 'corpus')) for p in (attempt / 'corpus').rglob('*') if p.is_file()}
for row in identity['inputs']:
    relative = row['projected']
    target = attempt / 'corpus' / relative
    blob = subprocess.check_output(['git', '-C', str(repo), 'show', commit + ':' + row['source']])
    mode = subprocess.check_output(['git', '-C', str(repo), 'ls-tree', commit, '--', row['source']]).split()[0]
    assert target.is_file() and not target.is_symlink()
    assert target.read_bytes() == blob
    assert hashlib.sha256(blob).hexdigest() == row['sha256'] == inventory[relative]['sha256']
    assert format(target.stat().st_mode & 0o777, '04o') == row['mode'] == inventory[relative]['mode']
    assert int(mode, 8) & 0o777 == target.stat().st_mode & 0o777
assert not (attempt / 'corpus/shell_heavy/_40_guava/cbrd_26659_tde_wal/cases').exists()
focused = Path('/home/vimkim/.agents/skills/cubrid-common/scripts/testkit-focused.py')
result_dir = attempt / 'CTP/result/shell/current_runtime_logs'
verification = subprocess.run(['python3', str(focused), 'verify', '--suite', 'shell', '--result-dir', str(result_dir), '--expected-list', str(attempt / 'expected-cases.txt'), '--run-log', str(attempt / 'run.log'), '--runner-exit', '0'], capture_output=True, text=True)
assert verification.returncode == 0, verification.stdout + verification.stderr
logs = attempt / 'CTP/result/shell/case-logs/_40_guava/cbrd_26659_crash_committed/cases/case'
journal = [json.loads(line) for line in (logs / 'oos10.journal.log').read_text().splitlines()]
assert journal[0]['event'] == 'policy' and journal[-1]['event'] == 'process_cleanup'
assert journal[-1]['all_owned_children_exited'] and journal[-1]['all_owned_utility_groups_exited'] and not journal[-1]['errors']
assert not any(row['event'] == 'scenario_failure' for row in journal)
assert len([row for row in journal if row['event'] == 'scenario_pass' and row['mode'] == 'committed']) == 1
assert sorted((row['phase'], row['algorithm']) for row in journal if row['event'] == 'encrypted_file_ack') == [('baseline', 'AES'), ('recovered', 'AES')]
joined = {}
for phase in ['baseline', 'recovered']:
    receipts = [row for row in journal if row['event'] == 'command' and row['name'] == phase + '.tde-owned']
    helper = str(attempt / 'corpus/shell_heavy/_40_guava/oos_common/tde_observe.sh')
    assert len(receipts) == 1 and receipts[0]['exit'] == 0
    assert receipts[0]['argv'] == ['bash', helper, 'owned', phase + '.tde-headers.log', phase + '.oos.json', 'AES']
    state = json.loads((logs / (phase + '.oos.parse.log')).read_text())
    data = json.loads((logs / (phase + '.tde-owned.log')).read_text())
    assert data['heap']['algorithm'] == data['oos']['algorithm'] == 'AES'
    assert data['heap']['vfid'] == [state['heap_volume_id'], state['heap_file_id']]
    assert data['oos']['vfid'] == [state['oos_volume_id'], state['oos_file_id']]
    assert data['oos']['hfid'] == [state['heap_header_page_id'], state['heap_volume_id'], state['heap_file_id']]
    assert data['heap']['class_oid'] == data['oos']['class_oid'] == state['class_oid']
    assert data['heap']['table'] == data['oos']['table'] == state['table_name'] == 'dba.oos10_data'
    assert (logs / (phase + '.tde-headers.log')).stat().st_size > 0
    joined[phase] = data
assert joined['baseline']['heap'] == joined['recovered']['heap']
assert joined['baseline']['oos'] == joined['recovered']['oos']
for phase in ['crash.server', 'crash.master']:
    assert len([row for row in journal if row['event'] == 'exit_receipt' and row['phase'] == phase and row['exit'] == -9]) == 1
assert len([row for row in journal if row['event'] == 'ready_ack' and row['name'] == 'recovery']) == 1
activity = [row for row in journal if row['event'] == 'recovery_activity']
assert len(activity) == 1 and activity[0]['oos_trace']['REDOING'] > 0
assert len([row for row in journal if row['event'] == 'values_ack' and row['name'] == 'recovered.values' and row['expected_ids'] == [1, 2, 4, 5]]) == 1
assert len([row for row in journal if row['event'] == 'command' and row['name'] == 'checkdb' and row['exit'] == 0]) == 1
assertions = re.findall(r'^-+\s+(\d+)\s+: OK\s+(.+)$', (result_dir / 'test_local.log').read_text(), re.M)
assert len(assertions) == 11
assert 'AES OOS owner before crash and after recovery' in assertions[0][1]
assert assertions[-1][1] == 'cleanup: cubrid.conf restored'
teardown = json.loads((attempt / 'teardown.json').read_text())
assert len(teardown['scans']) == 2 and not teardown['cleanup_signals']
for scan in teardown['scans']:
    for key in ['remaining_owned_processes', 'remaining_observed_namespace_holders', 'host_mounts_under_attempt', 'host_unix_sockets_under_attempt']:
        assert not scan[key], (key, scan[key])
print(json.dumps({'attempt': str(attempt), 'tc_commit': commit, 'inputs': len(inventory), 'native_pass': 1, 'fail': 0, 'skip': 0, 'assertions': len(assertions), 'encryption': 'AES', 'encrypted_phases': ['baseline', 'recovered'], 'owned_helper_receipts': 2, 'oos_redo_events': activity[0]['oos_trace']['REDOING'], 'cleanup_scans': 2, 'unreadable_processes': [scan['unreadable_processes'] for scan in teardown['scans']], 'scope': 'Retained committed AES crash only; no native execution started.'}, indent=2))
