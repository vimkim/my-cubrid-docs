#!/usr/bin/env python3
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import xml.etree.ElementTree as ET

p = argparse.ArgumentParser(description='Verify the contained SHOW representative and its committed inputs')
for name in ('attempt', 'regular', 'engine', 'producer'):
    p.add_argument('--' + name, type=Path, required=True)
p.add_argument('--tc-commit', required=True)
a = p.parse_args()
d, tc, engine, producer = (getattr(a, name).resolve() for name in ('attempt', 'regular', 'engine', 'producer'))
load = lambda path: json.loads(path.read_text())
sha = lambda data: hashlib.sha256(data).hexdigest()
git = lambda repo, *args: subprocess.check_output(['git', '-C', str(repo), *args], env={**os.environ, 'GIT_OPTIONAL_LOCKS': '0'})
identity, env, obs = (load(d / name) for name in ('identity.json', 'environment.json', 'observation.json'))
setup = load(d / 'setup-before-native.json')
assert setup['native_command_started'] is False and setup['fresh_registry_entries'] == []
assert setup['fresh_registry'] == str(d / 'cubrid/databases')
assert setup['preserved_original_registry'] == str(d / 'cubrid-databases.copied')
assert (d / 'cubrid-databases.copied').is_dir()
for relative, record in setup['preserved_registry_files'].items():
    path = d / 'cubrid-databases.copied' / relative
    assert sha(path.read_bytes()) == record['sha256'] and path.stat().st_mode & 0o777 == record['mode']
assert setup['selected_tmp'] == str(d / 'cubrid/tmp') and setup['worst_socket_path_bytes_for_7digit_pid'] <= 107
assert identity['selected_tmp_relative'] == 'cubrid/tmp'
case = 'shell/_40_guava/cbrd_26659_show_contract/cases/cbrd_26659_show_contract.sh'
disabled = 'disabled/failing/' + case + '.disabled'
helper = 'shell/_40_guava/oos_common/policy_metadata.sh'
old = 'shell/_40_guava/cbrd_26659_policy_contract/cases/policy_metadata.sh'
engine_head = 'e3589ae42d42b04eb020e1ae43e165b01d31b12a'
testkit_hash = '31be3b1e542b05d1ac7581d47f785319ce61421f4b5d94681a9c558d71445f5a'
assert identity['source_engine'] == engine_head == git(engine, 'rev-parse', 'HEAD').decode().strip()
assert identity['source_status'].splitlines() == git(engine, 'status', '--porcelain=v1').decode().splitlines() == [' M cubrid-cci', ' M cubrid-jdbc']
assert producer == Path('/home/vimkim/temp/oos-tc-runtime-20261028/engine/CUBRID') == Path(identity['producer'])
assert identity['mode'] == 'optdebug' and identity['preflight_exit'] == 0 and identity['commit_mismatch_exception_used'] is False
assert identity['current_tc'] == '6334dc6cd74683ca6ba10439372a21bd36b453d3' and identity['tc_status']
assert sha((d / 'tested-tc.patch').read_bytes()) == identity['tc_patch_sha256']
assert git(tc, 'rev-parse', 'HEAD').strip() == git(tc, 'rev-parse', a.tc_commit + '^{commit}').strip()
assert identity['canonical_case'] == case and identity['disabled_source'] == disabled
assert not (tc / case).exists() and not (tc / old).exists()
assert subprocess.run(['git', '-C', str(tc), 'cat-file', '-e', f'{a.tc_commit}:{case}'], capture_output=True).returncode != 0
assert subprocess.run(['git', '-C', str(tc), 'cat-file', '-e', f'{a.tc_commit}:{old}'], capture_output=True).returncode != 0
inputs = identity['inputs']
assert len(inputs) == len({x['source'] for x in inputs}) == len({x['projected'] for x in inputs})
assert [x['source'] for x in inputs if x['projected'] == case] == [disabled]
assert all(x['source'] == x['projected'] for x in inputs if x['projected'] != case)
assert any(x['source'] == helper and x['sha256'] == '1d5df9878f4b3a5048b5458171043e513a69a4454e3744b448284b322d5ea048' for x in inputs)
corpus = d / 'corpus'
assert not (corpus / old).exists() and not (corpus / 'shell/_40_guava/cbrd_26659_policy_contract/cases').exists()
for item in inputs:
    source, projected = tc / item['source'], corpus / item['projected']
    assert sha(source.read_bytes()) == item['sha256'] == sha(projected.read_bytes()) == sha(git(tc, 'show', f"{a.tc_commit}:{item['source']}")), item['source']
    mode = git(tc, 'ls-tree', a.tc_commit, '--', item['source']).decode().split()[0]
    assert source.stat().st_mode & 0o777 == item['mode'] == projected.stat().st_mode & 0o777 == int(mode, 8) & 0o777, item['source']
assert {str(x.relative_to(corpus)) for x in corpus.rglob('*') if x.is_file()} == {x['projected'] for x in inputs}
pruning = Path(identity['pruning_result'])
assert sha(pruning.read_bytes()) == identity['pruning_result_sha256']
after = load(Path(identity['artifacts_root']) / 'after-parent.json')
assert after['exit'] == 0 and after['parser_fixture_count'] == 17 and after['keep_invocations'] == 9
assert after['result'] == str(pruning) and after['show_fixture']['after_inventory'] == identity['post_pruning_inventory']
records = [x for x in load(pruning)['pruning'] if x['scenario'] == 'show_contract' and x['variant'] == 'owner_omitted']
assert len(records) == 1 and records[0] == after['show_fixture']
assert records[0]['keep_exit'] == 0 and records[0]['helper_survived'] is True
inventory = load(Path(identity['post_pruning_inventory']))
assert set(inventory) == {x['projected'] for x in inputs}
for item in inputs:
    entry = inventory[item['projected']]
    assert entry['sha256'] == item['sha256'] and int(entry['mode'], 8) == item['mode'] and entry['bytes'] == (corpus / item['projected']).stat().st_size
runtime = identity['runtime_hashes']
assert set(runtime) == {'bin/cubrid', 'bin/csql', 'bin/cub_server', 'bin/cub_master', 'bin/cubrid_rel', 'lib/libcascci.so'}
for path, digest in runtime.items():
    assert sha((producer / path).read_bytes()) == digest == sha((d / 'cubrid' / path).read_bytes())
assert identity['testkit_sha256'] == testkit_hash and sha(Path(identity['testkit']).read_bytes()) == testkit_hash
assert (identity['native_timeout_seconds'], identity['outer_invocation_seconds'], identity['termination_grace_seconds']) == (120, 120, 10)
assert sha((d / 'conf/shell.conf').read_bytes()) == identity['config_sha256']
assert sha((d / 'expected-cases.txt').read_bytes()) == identity['expected_sha256']
expected = str(corpus / case)
assert (d / 'expected-cases.txt').read_text().splitlines() == [expected]
lines = [line.split('=', 1) for line in (d / 'conf/shell.conf').read_text().splitlines() if line and not line.startswith('#') and '=' in line]
config = dict(lines)
for key, value in {'scenario': str(corpus / 'shell'), 'testcase_timeout_in_secs': '120', 'testcase_retry_num': '0', 'test_continue_yn': 'false', 'testcase_update_yn': 'false', 'parallel_slots': '1', 'scenario_disk': 'on', 'case_patch_dir': '', 'testcase_from_file': str(d / 'expected-cases.txt')}.items():
    assert [v for k, v in lines if k == key] == [value], key
for key, value in {'HOME': 'home', 'CUBRID': 'cubrid', 'CUBRID_DATABASES': 'cubrid/databases', 'CUBRID_TMP': 'cubrid/tmp', 'CUBRID_CONF_FILE': 'cubrid/conf/cubrid.conf', 'CUBRID_BROKER_CONF_FILE': 'cubrid/conf/cubrid_broker.conf', 'CTP_HOME': 'CTP', 'init_path': 'CTP/shell/init_path', 'CUBRID_TESTCASES_PRIVATE_EX_DIR': 'corpus', 'TMPDIR': 'tmp', 'OOS_NATIVE_CACHE': 'tmp/native-cache', 'TESTKIT_SLOT_ROOT': 'slots'}.items():
    assert env[key] == str(d / value)
assert env['TESTKIT_NATIVE'] == 'shell' and env['TESTKIT_CONTAIN'] == '1'
assert env['LD_LIBRARY_PATH'].split(':') == [str(d / 'cubrid/lib'), str(d / 'cubrid/cci/lib')]
preflight = (d / 'preflight.log').read_text()
assert all(x in preflight for x in ('source_head=' + engine_head, 'source_dirty=yes', 'installed_commit=e3589ae', 'commit_match=yes', 'commit_mismatch_allowed=no', 'containment=available', 'testkit_sha256=' + testkit_hash))
command = load(d / 'command.json')
assert command == ['timeout', '--signal=TERM', '--kill-after=10s', '120s', identity['testkit'], 'shell', '-c', str(d / 'conf/shell.conf')]
assert (d / 'exit.status').read_text().strip() == (d / 'verify.status').read_text().strip() == '0'
assert (d / 'verify.log').read_text().splitlines()[:4] == ['suite=shell', 'total=1', 'success=1', 'fail=0']
logs = d / 'CTP/result/shell/current_runtime_logs'
assert dict(line.split('=', 1) for line in (logs / 'test_status.data').read_text().splitlines()) == dict(total_case_count='1', total_executed_case_count='1', total_success_case_count='1', total_fail_case_count='0', total_skip_case_count='0')
for name in ('dispatch_tc_ALL.txt', 'dispatch_tc_FIN_local.txt'):
    assert (logs / name).read_text().splitlines() == [expected]
xml = ET.parse(logs / 'test-shell.xml').getroot()
cases = xml.findall('.//testcase')
assert len(cases) == 1 and cases[0].get('name') == case and cases[0].get('file') == expected
assert all(not xml.findall('.//' + tag) for tag in ('failure', 'error', 'skipped'))
phases = ['mixed_records', 'stable_stats', 'targets', 'arguments', 'permissions', 'preserved', 'owned_cleanup', 'cleanup']
for name in ('feedback.log', 'test_local.log'):
    data = (logs / name).read_text()
    assert re.findall(r'^cbrd_26659_show_contract-(\d+) : (OK|NOK)\b', data, re.MULTILINE) == [(str(i), 'OK') for i in range(1, 9)]
    for i, phase in enumerate(phases, 1):
        assert re.search(r'^cbrd_26659_show_contract-' + str(i) + r' : OK\s+[\'"]?\s*' + phase + ':', data, re.MULTILINE)
feedback = (logs / 'feedback.log').read_text()
assert '[OK]:  ' + expected in feedback and '[TEST STOP]' in feedback
art = d / 'CTP/result/shell/case-logs/_40_guava/cbrd_26659_show_contract/cases/case'
actual_environment = dict(line.split('=', 1) for line in (art / 'show.identity.log').read_text().splitlines() if line.startswith(('CUBRID=', 'CUBRID_DATABASES=', 'CUBRID_TMP=')))
assert set(actual_environment) == {'CUBRID', 'CUBRID_DATABASES', 'CUBRID_TMP'}
assert all(actual_environment[key] == env[key] for key in actual_environment)
assert len(actual_environment['CUBRID_TMP'].encode()) + len('/cubrid_tcp_setup_server') + 7 <= 107
assert (art / 'show.controller-exit.log').read_text().strip() == 'controller_exit_status=0'
assert (art / 'show.cleanup.log').read_text().strip() == 'owned_cleanup=1'
journal = [json.loads(line) for line in (art / 'show.journal.log').read_text().splitlines()]
assert len(journal) == 7 and {x['phase'] for x in journal} == set(phases[:7]) and all(x['event'] == 'PASS' for x in journal)
ddl_dump = re.findall(r'^EVIDENCE=(show\.[^\r\n]+\.ddl\.json)\n([^\n]*)', (art / 'show.controller.log').read_text(), re.MULTILINE)
ddl = dict(ddl_dump)
assert len(ddl_dump) == len(ddl) > 1 and 'show.before.ddl.json' in ddl and 'show.final.ddl.json' in ddl
assert isinstance(json.loads(ddl['show.before.ddl.json']), str)
assert all(value == ddl['show.before.ddl.json'] for value in ddl.values())
assert re.search(r'^cbrd_26659_show_contract-8 : OK\s+cleanup: framework configuration restored\s*$', feedback, re.MULTILINE)
assert obs['exit'] == 0 and obs['deadline_outcome'] is False and 0 < obs['invocation_seconds'] <= 120
assert obs['observed_processes'] and all(obs['observed_private_namespace_inodes'][ns] for ns in ('pid', 'ipc', 'mnt', 'user'))
assert obs['remaining_owned_processes'] == obs['remaining_observed_namespace_holders'] == []
teardown = load(d / 'teardown.json')
assert teardown['cleanup_signals'] == [] and len(teardown['scans']) == 2
for scan in teardown['scans']:
    for key in ('remaining_owned_processes', 'remaining_observed_namespace_holders', 'host_mounts_under_attempt', 'host_unix_sockets_under_attempt'):
        assert scan[key] == [], key
print(json.dumps({'result': 'PASS', 'tc_commit': a.tc_commit, 'case': case, 'inputs_verified': len(inputs), 'invocation_seconds': obs['invocation_seconds'], 'limitations': ['The original SHOW case remains disabled in the testcase repository.', 'Cleanup covers observed owned processes, namespace holders, and paths under the attempt, not all host IPC.', 'Runtime and testkit hashes do not establish source provenance.', 'One representative case passed; this does not establish schema, partition, or whole-suite results.']}, indent=2))
