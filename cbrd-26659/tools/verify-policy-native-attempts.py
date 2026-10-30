#!/usr/bin/env python3
import argparse
import hashlib
import json
import pathlib
import re
import subprocess
import xml.etree.ElementTree as ET

p = argparse.ArgumentParser()
for arg in ('artifacts', 'testcases', 'engine', 'producer'):
    p.add_argument('--' + arg, type=pathlib.Path, required=True)
a = p.parse_args()
root, tc, engine, producer = a.artifacts.resolve(), a.testcases.resolve(), a.engine.resolve(), a.producer.resolve()
tc_commit = 'a229e1978abc4cc6c280783703c03f75524c0f05'
engine_commit = 'e3589ae42d42b04eb020e1ae43e165b01d31b12a'
case = 'shell/_40_guava/cbrd_26659_gap_ctas_cs/cases/cbrd_26659_gap_ctas_cs.sh'
helper = 'shell/_40_guava/cbrd_26659_schema_policy/cases/policy_ddl.sh'
focused = '/home/vimkim/.agents/skills/cubrid-common/scripts/testkit-focused.py'
testkit_hash = '31be3b1e542b05d1ac7581d47f785319ce61421f4b5d94681a9c558d71445f5a'
sha = lambda data: hashlib.sha256(data).hexdigest()
load = lambda path: json.loads(path.read_text())
git = lambda repo, *args: subprocess.check_output(['git', '-C', str(repo), *args])
assert git(tc, 'rev-parse', 'HEAD').decode().strip() == tc_commit
assert not git(tc, 'status', '--porcelain')
assert git(engine, 'rev-parse', 'HEAD').decode().strip() == engine_commit
setup = load(root / 'ctas01/setup-failure.json')
assert setup['native_invoked'] is False and 'cases directory' in setup['cause']
assert not (root / 'ctas01/run.log').exists()
assert 'FileNotFoundError' in (root / 'prepare-ctas01.log').read_text()
assert (root / 'prepare-representative-v1.py').is_file()
results = [{'attempt': 'ctas01', 'disposition': 'SETUP_FAILURE', 'native_invoked': False}]
identities = []
for name in ('ctas02', 'ctas03'):
    d = root / name
    identity, observation = load(d / 'identity.json'), load(d / 'observation.json')
    identities.append(identity)
    assert identity['source_engine'] == engine_commit and identity['current_tc'] == tc_commit
    assert identity['mode'] == 'optdebug' and pathlib.Path(identity['producer']) == producer
    assert identity['canonical_case'] == case and identity['preflight_exit'] == 0
    assert len(identity['inputs']) == 56 and len({x['source'] for x in identity['inputs']}) == 56
    assert any(x['source'] == helper and x['sha256'] == '99bb263ae729f3f02745f88601b86653813d136476af007c2417fae6aedd024c' for x in identity['inputs'])
    for entry in identity['inputs']:
        source, projected = tc / entry['source'], d / 'corpus' / entry['projected']
        assert sha(source.read_bytes()) == entry['sha256'] == sha(projected.read_bytes())
        assert source.stat().st_mode & 0o777 == entry['mode'] == projected.stat().st_mode & 0o777
        assert sha(git(tc, 'show', f"{tc_commit}:{entry['source']}")) == entry['sha256']
        mode = git(tc, 'ls-tree', tc_commit, '--', entry['source']).decode().split()[0]
        assert int(mode, 8) & 0o777 == entry['mode']
    for path, digest in identity['runtime_hashes'].items():
        assert sha((producer / path).read_bytes()) == digest == sha((d / 'cubrid' / path).read_bytes())
    assert sha((d / 'conf/shell.conf').read_bytes()) == identity['config_sha256']
    assert sha((d / 'expected-cases.txt').read_bytes()) == identity['expected_sha256']
    assert (d / 'expected-cases.txt').read_text().strip() == str(d / 'corpus' / case)
    preflight = (d / 'preflight.log').read_text()
    assert all(x in preflight for x in ('commit_match=yes', 'containment=available', 'testkit_sha256=' + testkit_hash))
    command = load(d / 'command.json')
    assert command[:4] == ['timeout', '--signal=TERM', '--kill-after=10s', '120s']
    assert command[5:] == ['shell', '-c', str(d / 'conf/shell.conf')]
    assert sha(pathlib.Path(command[4]).read_bytes()) == testkit_hash
    assert 'testcase_timeout_in_secs=120' in (d / 'conf/shell.conf').read_text()
    log = (d / 'run.log').read_text()
    assert all(s in log for s in ('[SHELL] TEST END', 'TEST COMPLETE', 'ELAPSE'))
    result = d / 'CTP/result/shell/current_runtime_logs'
    cases = ET.parse(result / 'test-shell.xml').getroot().findall('.//testcase')
    assert len(cases) == 1 and cases[0].get('name') == case and len(cases[0]) == 0
    status = dict(line.split('=', 1) for line in (result / 'test_status.data').read_text().splitlines())
    assert status == dict(total_case_count='1', total_executed_case_count='1', total_success_case_count='1', total_fail_case_count='0', total_skip_case_count='0')
    logs = d / 'CTP/result/shell/case-logs/_40_guava/cbrd_26659_gap_ctas_cs/cases/case'
    checks = (logs / 'utility.controller.log').read_text().splitlines()
    assert len(checks) == 26 and all(line.startswith('PASS ') for line in checks)
    assertions = re.findall(r'^cbrd_26659_gap_ctas_cs-(\d+) : (OK|NOK)\b.*$', (result / 'test_local.log').read_text(), re.MULTILINE)
    assert assertions == [(str(i), 'OK') for i in range(1, 28)]
    assert 'PASS source.policy' in checks and 'PASS ctas.policy' in checks
    assert load(logs / 'gap.source.policy.check.log') == {'payload': 'DEFAULT'}
    assert load(logs / 'gap.ctas.policy.check.log') == {'payload': 'FORCE_OUTLINE'}
    cleanup = load(logs / 'oos12.cleanup.log')
    assert all(cleanup[k] is True for k in ('config_restored', 'owned_command_groups_absent', 'owned_directories_absent', 'owned_registry_absent'))
    assert cleanup['failures'] == cleanup['normal_stop_failures'] == [] and all(not v for v in cleanup['owned_server_pids'].values())
    assert all(observation['observed_private_namespace_inodes'].values())
    assert observation['remaining_owned_processes'] == observation['remaining_observed_namespace_holders'] == []
    exit_code = int((d / 'exit.status').read_text())
    verification = subprocess.run(['python3', focused, 'verify', '--suite', 'shell', '--result-dir', str(result), '--expected-list', str(d / 'expected-cases.txt'), '--run-log', str(d / 'run.log'), '--runner-exit', str(exit_code)], capture_output=True, text=True)
    assert verification.returncode == int((d / 'verify.status').read_text())
    if name == 'ctas02':
        assert exit_code == -9 and observation['deadline_outcome'] is True and verification.returncode != 0
        disposition = 'INCOMPLETE_TIMEOUT_WITH_PASS_CASE_ARTIFACTS'
    else:
        assert exit_code == 0 and observation['deadline_outcome'] is False and verification.returncode == 0
        assert observation['cleanup_signals'] == []
        assert [x['name'] for x in observation['probes']] == ['strace-attach']
        assert 'commit_match=yes' in (d / 'preflight-exact-environment.log').read_text()
        probe = load(d / 'strace-attach-result.json')
        assert probe['exit'] == 0 and probe['started_seconds'] > observation['test_end_observed_seconds']
        assert not load(d / 'observations/after-cleanup.json')['processes']
        disposition = 'PASS'
    results.append(dict(attempt=name, disposition=disposition, inputs_verified=56, testcase_ok_assertions=len(assertions), controller_pass_checks=len(checks), xml_seconds=float(cases[0].get('time')), invocation_seconds=observation['invocation_seconds'], exit=exit_code, verifier_exit=verification.returncode, remaining_owned=0, remaining_observed_namespace_holders=0))
assert identities[0]['inputs'] == identities[1]['inputs'] and identities[0]['runtime_hashes'] == identities[1]['runtime_hashes']
for relative in ('conf/shell.conf', 'expected-cases.txt', 'environment.json'):
    assert (root / 'ctas02' / relative).read_text().replace('ctas02', 'ATTEMPT') == (root / 'ctas03' / relative).read_text().replace('ctas03', 'ATTEMPT')
comparison = load(root / 'ctas03/pre-execution-comparison.json')
assert all(comparison[k] is True for k in ('inputs_56_identical', 'runtime_hashes_identical', 'config_identical_after_attempt_path_substitution', 'expected_case_identical_after_attempt_path_substitution', 'selected_environment_identical_after_attempt_path_substitution'))
history = load(root / 'ctas02/historical-input-comparison.json')
old = history['historical_tc']
for key, expected in [('same', 40), ('different', 11), ('missing_at_historical_tc', 5)]:
    assert len(history[key]) == expected
    for path in history[key]:
        prior = subprocess.run(['git', '-C', str(tc), 'show', f'{old}:{path}'], capture_output=True)
        if key == 'missing_at_historical_tc':
            assert prior.returncode != 0
        else:
            assert prior.returncode == 0 and (prior.stdout == (root / 'ctas02/corpus' / path).read_bytes()) == (key == 'same')
assert helper in history['same']
print(json.dumps({'attempts': results, 'current_fully_qualified_cases': 1, 'group_cases_unrun': 38, 'historical_projection': {'same': 40, 'different': 11, 'absent': 5}, 'limits': ['ctas02 termination cause unknown', 'ctas03 strace may affect observed execution', 'ambient environment was not fully snapshotted', 'historical engine, runner, environment and helper revisions are confounders', 'runtime hashes do not prove exact binary source provenance', 'no whole-group verdict']}, indent=2))
