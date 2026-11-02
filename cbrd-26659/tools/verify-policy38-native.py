#!/usr/bin/env python3
import argparse
import collections
import hashlib
import json
import os
from pathlib import Path
import subprocess
import xml.etree.ElementTree as ET

parser = argparse.ArgumentParser(description='Verify Work699 native shell evidence without rerunning testcases.')
parser.add_argument('--root', type=Path, required=True)
parser.add_argument('--testcases', type=Path, required=True)
parser.add_argument('--focused-helper', type=Path, default=Path('/home/vimkim/.agents/skills/cubrid-common/scripts/testkit-focused.py'))
args = parser.parse_args()
root = args.root.resolve(strict=True)
manifest_path = root / 'manifest.json'
assert hashlib.sha256(manifest_path.read_bytes()).hexdigest() == '8b92058232c3dfaa68bfe63d746b2cad138299f95c8383b80f934fec41bba312'
manifest = json.loads(manifest_path.read_text())
assert manifest['engine_head'] == 'e3589ae42d42b04eb020e1ae43e165b01d31b12a'
assert manifest['tc_head'] == '01df2600ac75180812451462b5c044cfa56b732a'
historical_path = Path(manifest['historical_inventory'])
assert hashlib.sha256(historical_path.read_bytes()).hexdigest() == manifest['historical_inventory_sha256']
historical = json.loads(historical_path.read_text())
group = {row['original_path'] for row in historical['historical_failures'] if 'policy_ddl.sh' in row['primary_symptom_group']}
excluded = 'shell/_40_guava/cbrd_26659_gap_ctas_cs/cases/cbrd_26659_gap_ctas_cs.sh'
selected = [row for row in manifest['cases'] if row['selection'] == 'pending']
assert len(group) == 39
assert len(selected) == 38
assert {row['original_path'] for row in selected} == group - {excluded}
inputs = json.loads((root / 'input-inventory.json').read_text())
projected = {row['target']: row for row in inputs['projections']}
assert set(projected) == group - {excluded}
assert len(inputs['files']) == 536
assert {str(path.relative_to(root / 'corpus')) for path in (root / 'corpus').rglob('*') if path.is_file()} == {row['path'] for row in inputs['files']}
for item in inputs['files']:
    path = root / 'corpus' / item['path']
    assert not path.is_symlink(), str(path)
    assert hashlib.sha256(path.read_bytes()).hexdigest() == item['sha256'], str(path)
    assert format(path.stat().st_mode & 0o777, '04o') == item['mode'], str(path)
    source = projected[item['path']]['source'] if item['path'] in projected else item['path']
    blob = subprocess.check_output(['git', '-C', str(args.testcases), 'show', manifest['tc_head'] + ':' + source])
    assert blob == path.read_bytes(), str(path)
summary = json.loads((root / 'results.json').read_text())
assert summary['selected_count'] == 38
assert summary['completed_attempts'] == 38
assert summary['not_run'] == 0
assert len(summary['results']) == 38
assert {row['case'] for row in summary['results']} == group - {excluded}
assert len({row['case'] for row in summary['results']}) == 38
assert summary['counts'] == dict(collections.Counter(row['verdict'] for row in summary['results']))
proof = []
private_namespaces = collections.defaultdict(set)
owned_installs = set()
for record in summary['results']:
    attempt = Path(record['attempt'])
    identity = json.loads((attempt / 'identity.json').read_text())
    observation = json.loads((attempt / 'observation.json').read_text())
    assert identity['source_engine'] == manifest['engine_head']
    assert identity['tc_head'] == manifest['tc_head']
    assert identity['canonical_case'] == record['case']
    assert not identity['commit_mismatch_exception_used']
    assert identity['preflight_exit'] == 0
    assert 'commit_match=yes' in (attempt / 'preflight.log').read_text()
    assert hashlib.sha256((attempt / 'conf/shell.conf').read_bytes()).hexdigest() == identity['config_sha256']
    assert hashlib.sha256((attempt / 'expected-cases.txt').read_bytes()).hexdigest() == identity['expected_sha256']
    assert (attempt / 'expected-cases.txt').read_text().splitlines() == [str(root / 'corpus' / record['case'])]
    for relative, expected_hash in identity['runtime_hashes'].items():
        assert hashlib.sha256((attempt / 'cubrid' / relative).read_bytes()).hexdigest() == expected_hash, str(attempt / relative)
    assert identity['testkit_sha256'] == '31be3b1e542b05d1ac7581d47f785319ce61421f4b5d94681a9c558d71445f5a'
    assert int((attempt / 'exit.status').read_text()) == record['runner_exit'] == observation['exit']
    assert int((attempt / 'verify.status').read_text()) == record['verifier_exit']
    assert record['cleanup_clear']
    assert not observation['remaining_owned_processes']
    assert not observation['remaining_observed_namespace_holders']
    assert record['containment_observed']
    xml_path = Path(record['result_dir']) / 'test-shell.xml'
    if xml_path.exists():
        xml_cases = ET.parse(xml_path).getroot().findall('.//testcase')
        assert len(xml_cases) == 1
        assert xml_cases[0].get('name') == record['case']
        assert xml_cases[0].get('file') == str(root / 'corpus' / record['case'])
        xml_failures = len(xml_cases[0].findall('failure')) + len(xml_cases[0].findall('error'))
        if record['verdict'] == 'FAIL':
            assert xml_failures > 0
        elif record['verdict'] == 'PASS':
            assert xml_failures == 0
    else:
        assert record['verdict'] in {'TIMEOUT', 'INCONCLUSIVE'}
    for kind in ['pid', 'ipc', 'mnt', 'user']:
        assert observation['observed_private_namespace_inodes'][kind]
        private_namespaces[kind].update(observation['observed_private_namespace_inodes'][kind])
    owned_installs.add(str(attempt / 'cubrid'))
    checked = subprocess.run(['python3', str(args.focused_helper), 'verify', '--suite', 'shell', '--result-dir', record['result_dir'], '--expected-list', str(attempt / 'expected-cases.txt'), '--run-log', str(attempt / 'run.log'), '--runner-exit', str(record['runner_exit'])], text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=30)
    if record['verdict'] == 'PASS':
        assert checked.returncode == 0, checked.stdout
        assert record['ok_assertion_lines'] > 0
    else:
        assert checked.returncode != 0
    proof.append({'case': record['case'], 'verdict': record['verdict'], 'focused_verifier_exit': checked.returncode, 'focused_verifier_output': checked.stdout, 'attempt': str(attempt)})
remaining_owned = []
remaining_namespace_holders = []
for proc in Path('/proc').iterdir():
    if not proc.name.isdigit():
        continue
    try:
        if proc.stat().st_uid != os.getuid():
            continue
        values = (proc / 'environ').read_bytes().split(b'\0')
        selected_installs = [value.split(b'=', 1)[1].decode(errors='replace') for value in values if value.startswith(b'CUBRID=')]
        if any(value in owned_installs for value in selected_installs):
            remaining_owned.append(int(proc.name))
        held = {kind: os.readlink(proc / 'ns' / kind) for kind in private_namespaces}
        if any(held[kind] in private_namespaces[kind] for kind in held):
            remaining_namespace_holders.append({'pid': int(proc.name), 'namespaces': held})
    except (FileNotFoundError, PermissionError, ProcessLookupError):
        continue
assert not remaining_owned, remaining_owned
assert not remaining_namespace_holders, remaining_namespace_holders
print(json.dumps({'verified': True, 'engine_head': manifest['engine_head'], 'tc_head': manifest['tc_head'], 'input_files_verified': len(inputs['files']), 'cases_verified': len(proof), 'counts': summary['counts'], 'remaining_owned_processes': remaining_owned, 'remaining_namespace_holders': remaining_namespace_holders, 'cases': proof}, ensure_ascii=False, indent=2))
