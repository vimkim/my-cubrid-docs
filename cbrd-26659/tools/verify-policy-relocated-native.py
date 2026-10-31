#!/usr/bin/env python3
import argparse
import hashlib
import json
import pathlib
import re
import subprocess
import sys
import xml.etree.ElementTree as ET

p = argparse.ArgumentParser()
for key in ('artifacts', 'regular', 'engine', 'producer'):
    p.add_argument('--' + key, type=pathlib.Path, required=True)
p.add_argument('--tc-commit', required=True)
a = p.parse_args()
root, tc, engine, producer = (x.resolve() for x in (a.artifacts, a.regular, a.engine, a.producer))
case = 'shell/_40_guava/cbrd_26659_gap_ctas_cs/cases/cbrd_26659_gap_ctas_cs.sh'
disabled = 'disabled/failing/' + case + '.disabled'
helper = 'shell/_40_guava/oos_common/policy_ddl.sh'
old_helper = 'shell/_40_guava/cbrd_26659_schema_policy/cases/policy_ddl.sh'
engine_head = 'e3589ae42d42b04eb020e1ae43e165b01d31b12a'
testkit_hash = '31be3b1e542b05d1ac7581d47f785319ce61421f4b5d94681a9c558d71445f5a'
focused = '/home/vimkim/.agents/skills/cubrid-common/scripts/testkit-focused.py'
sha = lambda data: hashlib.sha256(data).hexdigest()
load = lambda path: json.loads(path.read_text())
git = lambda repo, *args: subprocess.check_output(['git', '-C', str(repo), *args])
assert producer == pathlib.Path('/home/vimkim/temp/oos-tc-runtime-20261028/engine/CUBRID')
assert git(engine, 'rev-parse', 'HEAD').decode().strip() == engine_head
assert git(tc, 'rev-parse', 'HEAD').decode().strip() == git(tc, 'rev-parse', a.tc_commit + '^{commit}').decode().strip()
assert not git(tc, 'status', '--porcelain')
assert not (tc / old_helper).exists()
assert subprocess.run(['git', '-C', str(tc), 'cat-file', '-e', f'{a.tc_commit}:{old_helper}'], capture_output=True).returncode != 0
results, identities = [], []
for name in ('fixed01', 'fixed02'):
    d = root / name
    identity, observation, env = load(d / 'identity.json'), load(d / 'observation.json'), load(d / 'environment.json')
    identities.append(identity)
    assert identity['source_engine'] == engine_head and identity['mode'] == 'optdebug'
    assert pathlib.Path(identity['producer']) == producer and identity['tc_base'] == 'a229e1978abc4cc6c280783703c03f75524c0f05'
    assert identity['tc_dirty'] and sha((d / 'tested-tc.patch').read_bytes()) == identity['tc_patch_sha256']
    assert identity['canonical_case'] == case and identity['preflight_exit'] == 0
    assert identity['testkit_sha256'] == testkit_hash
    assert (identity['native_timeout_seconds'], identity['outer_invocation_seconds'], identity['termination_grace_seconds']) == (120, 120, 10)
    inputs = identity['inputs']
    assert len(inputs) == len({x['source'] for x in inputs}) == len({x['projected'] for x in inputs}) == 53
    assert [x['source'] for x in inputs if x['projected'] == case] == [disabled]
    assert any(x['source'] == helper and x['projected'] == helper and x['sha256'] == '99bb263ae729f3f02745f88601b86653813d136476af007c2417fae6aedd024c' for x in inputs)
    assert all(x['source'] == x['projected'] for x in inputs if x['projected'] != case)
    corpus = d / 'corpus/cubrid-testcases-private-ex'
    assert not (corpus / old_helper).exists()
    for entry in inputs:
        source, projection = tc / entry['source'], corpus / entry['projected']
        assert sha(source.read_bytes()) == entry['sha256'] == sha(projection.read_bytes())
        assert source.stat().st_mode & 0o777 == entry['mode'] == projection.stat().st_mode & 0o777
        assert sha(git(tc, 'show', f"{a.tc_commit}:{entry['source']}")) == entry['sha256']
        mode = git(tc, 'ls-tree', a.tc_commit, '--', entry['source']).decode().split()[0]
        assert int(mode, 8) & 0o777 == entry['mode']
    pruning_path = pathlib.Path(identity['pruning_result'])
    if 'pruning_result_sha256' in identity:
        assert sha(pruning_path.read_bytes()) == identity['pruning_result_sha256']
    records = [x for x in load(pruning_path)['records'] if x['suite'] == 'regular' and x['variant'] == 'current']
    assert len(records) == 1
    record = records[0]
    assert record['case'] == case and record['keep_exit'] == 0 and record['helper_after'] is True and record['old_helper_after'] is False
    assert record['post_inventory'] == {x['projected']: {'sha256': x['sha256'], 'mode': x['mode']} for x in inputs}
    assert len(identity['runtime_hashes']) == 6
    assert set(identity['runtime_hashes']) == {'bin/cubrid', 'bin/csql', 'bin/cub_server', 'bin/cub_master', 'bin/cubrid_rel', 'lib/libcascci.so'}
    for path, digest in identity['runtime_hashes'].items():
        assert sha((producer / path).read_bytes()) == digest == sha((d / 'cubrid' / path).read_bytes())
    assert sha((d / 'conf/shell.conf').read_bytes()) == identity['config_sha256']
    assert sha((d / 'expected-cases.txt').read_bytes()) == identity['expected_sha256']
    assert (d / 'expected-cases.txt').read_text().strip() == str(corpus / case)
    config = dict(line.split('=', 1) for line in (d / 'conf/shell.conf').read_text().splitlines() if line and not line.startswith('#') and '=' in line)
    for k, v in {'scenario': str(corpus / 'shell'), 'testcase_timeout_in_secs': '120', 'testcase_retry_num': '0', 'test_continue_yn': 'false', 'testcase_update_yn': 'false', 'parallel_slots': '1', 'scenario_disk': 'on', 'case_patch_dir': '', 'testcase_from_file': str(d / 'expected-cases.txt')}.items():
        assert config[k] == v
    for k, v in {'HOME': d / 'home', 'CUBRID': d / 'cubrid', 'CUBRID_DATABASES': d / 'cubrid/databases', 'CUBRID_TMP': d / 'cubrid/tmp', 'CUBRID_CONF_FILE': d / 'cubrid/conf/cubrid.conf', 'CUBRID_BROKER_CONF_FILE': d / 'cubrid/conf/cubrid_broker.conf', 'CTP_HOME': d / 'CTP', 'CUBRID_TESTCASES_PRIVATE_EX_DIR': corpus, 'TMPDIR': d / 'tmp', 'OOS_NATIVE_CACHE': d / 'tmp/native-cache', 'TESTKIT_SLOT_ROOT': d / 'slots'}.items():
        assert env[k] == str(v)
    assert env['TESTKIT_NATIVE'] == 'shell' and env['TESTKIT_CONTAIN'] == '1'
    preflight = (d / 'preflight.log').read_text()
    assert all(x in preflight for x in ('commit_match=yes', 'commit_mismatch_allowed=no', 'containment=available', 'testkit_sha256=' + testkit_hash))
    command = load(d / 'command.json')
    assert command[:4] == ['timeout', '--signal=TERM', '--kill-after=10s', '120s']
    assert command[5:] == ['shell', '-c', str(d / 'conf/shell.conf')]
    assert sha(pathlib.Path(command[4]).read_bytes()) == testkit_hash
    result = d / 'CTP/result/shell/current_runtime_logs'
    cases = ET.parse(result / 'test-shell.xml').getroot().findall('.//testcase')
    assert len(cases) == 1 and cases[0].get('name') == case and len(cases[0]) == 0
    status = dict(line.split('=', 1) for line in (result / 'test_status.data').read_text().splitlines())
    assert status == dict(total_case_count='1', total_executed_case_count='1', total_success_case_count='1', total_fail_case_count='0', total_skip_case_count='0')
    logs = d / 'CTP/result/shell/case-logs/_40_guava/cbrd_26659_gap_ctas_cs/cases/case'
    checks = (logs / 'utility.controller.log').read_text().splitlines()
    assert len(checks) == 26 and all(line.startswith('PASS ') for line in checks)
    assert 'PASS source.policy' in checks and 'PASS ctas.policy' in checks
    assertions = re.findall(r'^cbrd_26659_gap_ctas_cs-(\d+) : (OK|NOK)\b.*$', (result / 'test_local.log').read_text(), re.MULTILINE)
    assert assertions == [(str(i), 'OK') for i in range(1, 28)]
    assert load(logs / 'gap.source.policy.check.log') == {'payload': 'DEFAULT'}
    assert load(logs / 'gap.ctas.policy.check.log') == {'payload': 'FORCE_OUTLINE'}
    cleanup = load(logs / 'oos12.cleanup.log')
    assert all(cleanup[k] is True for k in ('config_restored', 'owned_command_groups_absent', 'owned_directories_absent', 'owned_registry_absent'))
    assert cleanup['failures'] == cleanup['normal_stop_failures'] == [] and all(not v for v in cleanup['owned_server_pids'].values())
    assert all(observation['observed_private_namespace_inodes'].values())
    scans = [observation] if name == 'fixed01' else observation['residue_scans']
    assert len(scans) == (1 if name == 'fixed01' else 2)
    for scan in scans:
        assert scan['remaining_owned_processes'] == scan['remaining_observed_namespace_holders'] == []
        if name == 'fixed02':
            assert scan['host_mounts_under_attempt'] == scan['host_unix_sockets_under_attempt'] == []
    exit_code = int((d / 'exit.status').read_text())
    assert observation['exit'] == exit_code
    verify = subprocess.run(['python3', focused, 'verify', '--suite', 'shell', '--result-dir', str(result), '--expected-list', str(d / 'expected-cases.txt'), '--run-log', str(d / 'run.log'), '--runner-exit', str(exit_code)], capture_output=True, text=True)
    assert verify.returncode == int((d / 'verify.status').read_text())
    if exit_code == 0 and verify.returncode == 0 and observation['deadline_outcome'] is False and observation.get('cleanup_signals') == [] and observation['invocation_seconds'] <= 120:
        disposition = 'PASS'
    elif exit_code == -9 and verify.returncode != 0 and observation['deadline_outcome'] is True:
        disposition = 'INCOMPLETE_TIMEOUT_WITH_PASS_CASE_ARTIFACTS'
    else:
        disposition = 'INCOMPLETE_WITH_PASS_CASE_ARTIFACTS'
    results.append(dict(attempt=name, disposition=disposition, inputs_verified=53, testcase_ok_assertions=27, controller_pass_checks=26, case_seconds=float(cases[0].get('time')), invocation_seconds=observation['invocation_seconds'], exit=exit_code, verifier_exit=verify.returncode))
assert identities[0]['inputs'] == identities[1]['inputs'] and identities[0]['runtime_hashes'] == identities[1]['runtime_hashes']
for relative in ('conf/shell.conf', 'expected-cases.txt', 'environment.json'):
    assert (root / 'fixed01' / relative).read_text().replace('fixed01', 'ATTEMPT') == (root / 'fixed02' / relative).read_text().replace('fixed02', 'ATTEMPT')
assert results[0]['disposition'] == 'INCOMPLETE_TIMEOUT_WITH_PASS_CASE_ARTIFACTS'
qualified = int(any(x['disposition'] == 'PASS' for x in results))
assert load(root / 'fixed02/observation.json')['trace']['requested'] is False
assert load(root / 'fixed02/observation.json')['test_end_seen_seconds'] is None
print(json.dumps({'attempts': results, 'full_pass_qualified_case_count': qualified, 'remaining_group_cases': 38, 'limits': ['fixed01 termination cause remains unresolved', 'fixed02 used process observation without strace; TEST END was not latched, so no post-END wait interval was measured', 'kernel stack reads were permission-limited and ambient environment was not fully captured', 'runtime hashes do not prove exact binary source provenance or historical image identity', 'no whole-group verdict']}, indent=2), flush=True)
if not qualified:
    sys.exit(1)
