#!/usr/bin/env python3
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import xml.etree.ElementTree as ET

parser = argparse.ArgumentParser(description='Verify retained evidence for the original show_contract shell case')
for option in ('attempt', 'testcases', 'engine', 'producer'):
    parser.add_argument('--' + option, required=True, type=Path)
args = parser.parse_args()
a = args.attempt.resolve()
tc = args.testcases.resolve()
engine = args.engine.resolve()
producer = args.producer.resolve()
id = json.loads((a / 'identity.json').read_text())
obs = json.loads((a / 'observation.json').read_text())
env = json.loads((a / 'environment.json').read_text())
command = json.loads((a / 'command.json').read_text())
sha = lambda data: hashlib.sha256(data).hexdigest()
git = lambda root, *argv: subprocess.check_output(['git', '-C', str(root), *argv], env={**os.environ, 'GIT_OPTIONAL_LOCKS': '0'})
assert id['source_engine'] == 'e3589ae42d42b04eb020e1ae43e165b01d31b12a'
assert id['current_tc'] == 'a229e1978abc4cc6c280783703c03f75524c0f05'
assert git(engine, 'rev-parse', 'HEAD').decode().strip() == id['source_engine']
assert git(tc, 'rev-parse', 'HEAD').decode().strip() == id['current_tc']
assert git(tc, 'status', '--porcelain=v1') == b''
assert git(engine, 'status', '--porcelain=v1').decode().splitlines() == [' M cubrid-cci', ' M cubrid-jdbc']
assert id['producer'] == str(producer)
assert id['mode'] == 'optdebug' and id['preflight_exit'] == 0 and id['original_tc_status'] == ''
assert len(id['inputs']) == 53
assert len({x['source'] for x in id['inputs']}) == len({x['projected'] for x in id['inputs']}) == 53
for item in id['inputs']:
    source, projected = tc / item['source'], a / 'corpus' / item['projected']
    blob = git(tc, 'show', id['current_tc'] + ':' + item['source'])
    tree = git(tc, 'ls-tree', id['current_tc'], '--', item['source']).decode().split()
    assert len(tree) >= 4 and int(tree[0], 8) & 0o777 == item['mode'], item['source']
    assert source.is_file() and projected.is_file(), item['source']
    assert sha(blob) == sha(source.read_bytes()) == sha(projected.read_bytes()) == item['sha256'], item['source']
    assert source.stat().st_mode & 0o777 == projected.stat().st_mode & 0o777 == item['mode'], item['source']
case = id['canonical_case']
assert id['disabled_source'].endswith(case + '.disabled')
assert not (tc / case).exists()
assert next(x for x in id['inputs'] if x['source'] == id['disabled_source'])['sha256'] == '632ad5def8ba41eb8173ffea71d0df0ed64006c7270d3a1599bda4adf532ff9f'
for path, digest in id['runtime_hashes'].items():
    assert sha((producer / path).read_bytes()) == sha((a / 'cubrid' / path).read_bytes()) == digest, path
assert sha(Path(command[4]).read_bytes()) == '31be3b1e542b05d1ac7581d47f785319ce61421f4b5d94681a9c558d71445f5a'
assert command[:4] == ['timeout', '--signal=TERM', '--kill-after=10s', '120s']
assert command[5:] == ['shell', '-c', str(a / 'conf/shell.conf')]
assert (id['native_timeout_seconds'], id['outer_invocation_seconds'], id['termination_grace_seconds']) == (120, 120, 10)
assert sha((a / 'conf/shell.conf').read_bytes()) == id['config_sha256']
expected = str(a / 'corpus' / case)
assert sha((a / 'expected-cases.txt').read_bytes()) == id['expected_sha256']
assert (a / 'expected-cases.txt').read_text().splitlines() == [expected]
assert env['CUBRID_TMP'] == str(a / 'cubrid/tmp') and env['CUBRID'] == str(a / 'cubrid')
assert env['CUBRID_TESTCASES_PRIVATE_EX_DIR'] == str(a / 'corpus') and env['TESTKIT_CONTAIN'] == '1' and env['TESTKIT_NATIVE'] == 'shell'
assert (a / 'exit.status').read_text().strip() == (a / 'verify.status').read_text().strip() == '0'
assert (a / 'verify.log').read_text().splitlines()[:4] == ['suite=shell', 'total=1', 'success=1', 'fail=0']
logs = a / 'CTP/result/shell/current_runtime_logs'
assert dict(line.split('=', 1) for line in (logs / 'test_status.data').read_text().splitlines()) == {'total_case_count':'1', 'total_executed_case_count':'1', 'total_success_case_count':'1', 'total_fail_case_count':'0', 'total_skip_case_count':'0'}
for name in ('dispatch_tc_ALL.txt', 'dispatch_tc_FIN_local.txt'):
    assert (logs / name).read_text().splitlines() == [expected]
xml = ET.parse(logs / 'test-shell.xml').getroot()
cases = xml.findall('.//testcase')
assert len(cases) == 1 and cases[0].get('name') == case and cases[0].get('file') == expected
assert not any(cases[0].find(tag) is not None for tag in ('failure', 'error', 'skipped'))
assert len(xml.findall('.//failure')) == len(xml.findall('.//error')) == len(xml.findall('.//skipped')) == 0
feedback = (logs / 'feedback.log').read_text()
assert '[OK]:  ' + expected in feedback and '[TEST STOP]' in feedback
phases = ['mixed_records', 'stable_stats', 'targets', 'arguments', 'permissions', 'preserved', 'owned_cleanup', 'cleanup']
for name in ('feedback.log', 'test_local.log'):
    data = (logs / name).read_text()
    for number, phase in enumerate(phases, 1):
        assert re.search(r'cbrd_26659_show_contract-' + str(number) + r' : OK\s+[\'\"]?\s*' + phase + r':', data), (name, phase)
art = a / 'CTP/result/shell/case-logs/_40_guava/cbrd_26659_show_contract/cases/case'
identity = (art / 'show.identity.log').read_text()
assert 'CUBRID_TMP=' + env['CUBRID_TMP'] + '\n' in identity
assert all(re.search(r'^' + ns + r'=' + ns + r':\[\d+\]$', identity, re.M) for ns in ('pid', 'ipc', 'mnt', 'user'))
config_hash = re.search(r'^([0-9a-f]{64})  .*cubrid\.conf$', identity, re.M).group(1)
assert sha((a / 'cubrid/conf/cubrid.conf').read_bytes()) == config_hash
journal = [json.loads(line) for line in (art / 'show.journal.log').read_text().splitlines()]
assert len(journal) == 7 and {x['phase'] for x in journal} == set(phases[:7]) and all(x['event'] == 'PASS' for x in journal)
assert (art / 'show.controller-exit.log').read_text().strip() == 'controller_exit_status=0'
case_ns = int((art / 'show.case-timing.log').read_text().strip().split('=', 1)[1])
assert obs['exit'] == 0 and obs['deadline_outcome'] is False and 0 < obs['invocation_seconds'] < 120
assert obs['observed_processes'] and all(obs['observed_private_namespace_inodes'][ns] for ns in ('pid', 'ipc', 'mnt', 'user'))
assert obs['remaining_owned_processes'] == [] and obs['remaining_observed_namespace_holders'] == []
print(json.dumps({'result':'PASS', 'case':case, 'engine':id['source_engine'], 'testcases':id['current_tc'], 'projected_inputs_verified':len(id['inputs']), 'native_case_seconds':float(cases[0].get('time')), 'controller_seconds':case_ns / 1e9, 'invocation_seconds':obs['invocation_seconds'], 'timeout_seconds':120, 'deadline_reached':obs['deadline_outcome'], 'observed_processes':len(obs['observed_processes']), 'remaining_owned_processes':0, 'remaining_observed_namespace_holders':0, 'limitations':['timeout termination was not exercised', 'cleanup check covers observed owned processes and namespace holders, not all host IPC', 'testkit binary hash is verified; exact source provenance is not established', 'one representative case passed; 60 historical cases were not run', 'the historical failure and engine-fix cause are not revalidated']}, indent=2))
