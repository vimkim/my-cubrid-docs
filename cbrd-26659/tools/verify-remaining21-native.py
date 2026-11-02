#!/usr/bin/env python3
import argparse
from collections import Counter, defaultdict
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import xml.etree.ElementTree as ET

parser = argparse.ArgumentParser(description='Verify retained Work704 shell testcase evidence without executing tests.')
parser.add_argument('--root', type=Path, required=True)
parser.add_argument('--testcases', type=Path, required=True)
parser.add_argument('--focused-helper', type=Path, default=Path('/home/vimkim/.agents/skills/cubrid-common/scripts/testkit-focused.py'))
args = parser.parse_args()
root = args.root.resolve(strict=True)
manifest_path = root / 'manifest.json'
assert hashlib.sha256(manifest_path.read_bytes()).hexdigest() == '2affce46d70bcbd51272b3a617492da2069f13e9b275792ef5893479b6a5192e'
manifest = json.loads(manifest_path.read_text())
assert manifest['engine_head'] == 'e3589ae42d42b04eb020e1ae43e165b01d31b12a'
assert manifest['tc_head'] == '01df2600ac75180812451462b5c044cfa56b732a'
historical_path = Path(manifest['historical_inventory'])
assert hashlib.sha256(historical_path.read_bytes()).hexdigest() == manifest['historical_inventory_sha256']
original = {row['original_path'] for row in json.loads(historical_path.read_text())['historical_failures']}
covered = set(manifest['covered_case_ids'])
selected = {row['original_path']: row for row in manifest['cases']}
assert len(original) == 61 and len(covered) == 40 and len(selected) == manifest['selected_count'] == 21
assert set(selected) == {name for name in original if Path(name).stem not in covered}
tree = {}
for raw in subprocess.check_output(['git', '-C', str(args.testcases), 'ls-tree', '-rz', manifest['tc_head'], '--', 'shell/']).split(b'\0'):
    if not raw:
        continue
    meta, name = raw.split(b'\t', 1)
    mode, kind, oid = meta.decode().split()
    assert kind == 'blob'
    tree[name.decode()] = {'mode': mode[-4:], 'oid': oid}
for name, row in selected.items():
    mode, kind, oid = subprocess.check_output(['git', '-C', str(args.testcases), 'ls-tree', manifest['tc_head'], '--', row['current_entry_source']], text=True).split('\t', 1)[0].split()
    assert kind == 'blob' and name not in tree
    tree[name] = {'mode': mode[-4:], 'oid': oid}
inputs = json.loads((root / 'input-inventory.json').read_text())
assert {row['path'] for row in inputs} == set(tree)
actual = {path.relative_to(root / 'corpus').as_posix() for path in (root / 'corpus').rglob('*') if path.is_file() or path.is_symlink()}
assert actual == set(tree)
for item in inputs:
    path = root / 'corpus' / item['path']
    if item['kind'] == 'symlink':
        assert path.is_symlink() and os.readlink(path) == item['target']
        data = os.readlink(path).encode()
    else:
        assert not path.is_symlink()
        data = path.read_bytes()
        assert len(data) == item['bytes'] and hashlib.sha256(data).hexdigest() == item['sha256']
        assert format(path.stat().st_mode & 0o7777, '04o') == item['mode'] == tree[item['path']]['mode']
    assert hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest() == tree[item['path']]['oid']
summary = json.loads((root / 'results.json').read_text())
assert summary['selected_count'] == summary['completed_attempts'] == len(summary['results']) == 21
assert summary['not_run'] == 0
assert {row['case'] for row in summary['results']} == set(selected)
assert summary['counts'] == dict(Counter(row['verdict'] for row in summary['results']))
proof = []
private = defaultdict(set)
owned_installs = set()
for record in summary['results']:
    attempt = Path(record['attempt'])
    identity = json.loads((attempt / 'identity.json').read_text())
    observation = json.loads((attempt / 'observation.json').read_text())
    assert identity['source_engine'] == manifest['engine_head'] and identity['tc_head'] == manifest['tc_head']
    assert identity['canonical_case'] == record['case']
    assert identity['preflight_exit'] == 0 and not identity['commit_mismatch_exception_used']
    assert 'commit_match=yes' in (attempt / 'preflight.log').read_text()
    assert hashlib.sha256((attempt / 'conf/shell.conf').read_bytes()).hexdigest() == identity['config_sha256']
    assert hashlib.sha256((attempt / 'expected-cases.txt').read_bytes()).hexdigest() == identity['expected_sha256']
    assert (attempt / 'expected-cases.txt').read_text().splitlines() == [str(root / 'corpus' / record['case'])]
    for relative, expected in identity['runtime_hashes'].items():
        assert hashlib.sha256((attempt / 'cubrid' / relative).read_bytes()).hexdigest() == expected
    assert identity['testkit_sha256'] == '31be3b1e542b05d1ac7581d47f785319ce61421f4b5d94681a9c558d71445f5a'
    assert int((attempt / 'exit.status').read_text()) == observation['exit'] == record['runner_exit']
    assert int((attempt / 'verify.status').read_text()) == record['verifier_exit']
    assert record['cleanup_clear'] and record['containment_observed']
    assert not observation['remaining_owned_processes'] and not observation['remaining_observed_namespace_holders']
    for kind in ['pid', 'ipc', 'mnt', 'user', 'net']:
        assert observation['observed_private_namespace_inodes'][kind]
        private[kind].update(observation['observed_private_namespace_inodes'][kind])
    owned_installs.add(str(attempt / 'cubrid'))
    xml_path = Path(record['result_dir']) / 'test-shell.xml'
    failures_text = []
    if xml_path.exists():
        nodes = list(ET.parse(xml_path).iter('testcase'))
        assert len(nodes) == 1 and nodes[0].get('name') == record['case']
        assert nodes[0].get('file') == str(root / 'corpus' / record['case'])
        failures = len(nodes[0].findall('failure')) + len(nodes[0].findall('error'))
        skips = len(nodes[0].findall('skipped'))
        for part in list(nodes[0]):
            for line in (part.text or '').splitlines():
                if re.match(r'^cbrd_\S+-\d+\s*:\s*NOK\b', line) and line not in failures_text:
                    failures_text.append(line)
        if record['verdict'] == 'PASS':
            assert failures == skips == 0
        elif record['verdict'] == 'FAIL':
            assert failures > 0
        elif record['verdict'] == 'SKIP':
            assert skips > 0
    else:
        assert record['verdict'] in ['TIMEOUT', 'INCONCLUSIVE']
    if record['verdict'] == 'TIMEOUT':
        assert observation['deadline_outcome']
        assert observation['invocation_seconds'] >= 120
        assert '120s' in json.loads((attempt / 'command.json').read_text())
    if record['verdict'] in ['PASS', 'FAIL']:
        result_dir = Path(record['result_dir'])
        expected = [str(root / 'corpus' / record['case'])]
        assert (result_dir / 'dispatch_tc_ALL.txt').read_text().splitlines() == expected
        finished = [line for path in result_dir.glob('dispatch_tc_FIN_*.txt') for line in path.read_text().splitlines() if line]
        assert finished == expected
        status = dict(line.split('=', 1) for line in (result_dir / 'test_status.data').read_text().splitlines())
        assert int(status['total_case_count']) == int(status['total_executed_case_count']) == 1
        assert int(status['total_skip_case_count']) == 0
        assert int(status['total_success_case_count']) == (record['verdict'] == 'PASS')
        assert int(status['total_fail_case_count']) == (record['verdict'] == 'FAIL')
    checked = subprocess.run(['python3', str(args.focused_helper), 'verify', '--suite', 'shell', '--result-dir', record['result_dir'], '--expected-list', str(attempt / 'expected-cases.txt'), '--run-log', str(attempt / 'run.log'), '--runner-exit', str(record['runner_exit'])], capture_output=True, text=True, timeout=30)
    assert (checked.returncode == 0) == (record['verdict'] == 'PASS')
    if record['verdict'] == 'PASS':
        assert record['ok_assertion_lines'] > 0
    proof.append({'case': record['case'], 'verdict': record['verdict'], 'assertion_failures': failures_text, 'focused_verifier_exit': checked.returncode, 'focused_verifier_output': checked.stdout + checked.stderr, 'attempt': str(attempt)})
initial = Path(manifest['initial_attempt_root']) / 'a01'
initial_identity = json.loads((initial / 'identity.json').read_text())
initial_observation = json.loads((initial / 'observation.json').read_text())
assert initial_identity['source_engine'] == manifest['engine_head'] and initial_identity['tc_head'] == manifest['tc_head']
assert initial_identity['preflight_exit'] == 0 and not initial_identity['commit_mismatch_exception_used']
assert initial_identity['runtime_hashes'] == json.loads((root / 'a01/identity.json').read_text())['runtime_hashes']
assert initial_observation['exit'] == 0
assert not initial_observation['remaining_owned_processes'] and not initial_observation['remaining_observed_namespace_holders']
for relative, expected in initial_identity['runtime_hashes'].items():
    assert hashlib.sha256((initial / 'cubrid' / relative).read_bytes()).hexdigest() == expected
owned_installs.add(str(initial / 'cubrid'))
for kind in ['pid', 'ipc', 'mnt', 'user', 'net']:
    assert initial_observation['observed_private_namespace_inodes'][kind]
    private[kind].update(initial_observation['observed_private_namespace_inodes'][kind])
old_config = dict(line.split('=', 1) for line in (initial / 'conf/shell.conf').read_text().splitlines() if line and not line.startswith('#') and '=' in line)
new_config = dict(line.split('=', 1) for line in (root / 'a01/conf/shell.conf').read_text().splitlines() if line and not line.startswith('#') and '=' in line)
for key in ['testcase_exclude_by_macro', 'testcase_timeout_in_secs', 'parallel_slots', 'scenario_disk', 'testcase_retry_num', 'test_continue_yn', 'testcase_update_yn', 'case_patch_dir']:
    assert old_config[key] == new_config[key]
remaining = []
for proc in Path('/proc').iterdir():
    if not proc.name.isdigit():
        continue
    try:
        if proc.stat().st_uid != os.getuid():
            continue
        values = (proc / 'environ').read_bytes().split(b'\0')
        owns = any(value.startswith(b'CUBRID=') and value.split(b'=', 1)[1].decode(errors='replace') in owned_installs for value in values)
        holds = any(os.readlink(proc / 'ns' / kind) in inodes for kind, inodes in private.items())
        if owns or holds:
            remaining.append({'pid': int(proc.name), 'owns_install': owns, 'holds_namespace': holds})
    except (FileNotFoundError, PermissionError, ProcessLookupError):
        continue
assert not remaining, remaining
assert 'total case count is 22, expected 1' in (initial / 'verify.log').read_text()
old_nodes = list(ET.parse(initial / 'CTP/result/shell/current_runtime_logs/test-shell.xml').iter('testcase'))
assert len(old_nodes) == 22
assert len([node for node in old_nodes if node.find('skipped') is not None]) == 21
target_nodes = [node for node in old_nodes if node.get('name') == manifest['cases'][0]['original_path']]
assert len(target_nodes) == 1 and target_nodes[0].find('failure') is not None
print(json.dumps({'verified': True, 'work_item': 704, 'engine': manifest['engine_head'], 'tc': manifest['tc_head'], 'source_inputs_verified': len(inputs), 'cases_verified': len(proof), 'counts': summary['counts'], 'initial_full_shell_attempt': {'verdict': 'INCONCLUSIVE', 'target_xml': 'FAIL', 'unrelated_macro_skip': 21, 'path': str(initial)}, 'remaining_owned_processes_or_namespace_holders': remaining, 'cases': proof}, ensure_ascii=False, indent=2))
