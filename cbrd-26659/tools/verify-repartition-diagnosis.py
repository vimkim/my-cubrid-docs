#!/usr/bin/env python3
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tarfile
import xml.etree.ElementTree as ET

parser = argparse.ArgumentParser(description='Verify Work702 REPARTITION evidence without executing testcases.')
parser.add_argument('--root', required=True, type=Path)
parser.add_argument('--engine', required=True, type=Path)
parser.add_argument('--focused-helper', type=Path, default=Path('/home/vimkim/.agents/skills/cubrid-common/scripts/testkit-focused.py'))
args = parser.parse_args()
root = args.root.resolve(strict=True)
engine_head = 'e3589ae42d42b04eb020e1ae43e165b01d31b12a'
tc_head = '01df2600ac75180812451462b5c044cfa56b732a'
spec_hash = '6300aa1fa6ffb54033b9c7f7ea959466e9d88f0530e1ab0d7178b4459d4fcf63'
assert hashlib.sha256((root / 'spec-snapshot.md').read_bytes()).hexdigest() == spec_hash
assert json.loads((root / 'spec-identity.json').read_text())['sha256'] == spec_hash
original = json.loads((root / 'original-replay-proof.json').read_text())
original_attempt = Path(original['attempt'])
original_log = (original_attempt / 'CTP/result/shell/current_runtime_logs/test_local.log').read_text()
owners = {}
for policy in original['policies']:
    archive_path = Path(policy['archive'])
    digest = hashlib.sha256(archive_path.read_bytes()).hexdigest()
    assert digest == policy['archive_sha256']
    archive_name = 'repartition.' + policy['policy'] + '.partition_existing.tar.gz'
    assert re.search(re.escape(digest) + r'\s+[^\n]*' + re.escape(archive_name), original_log)
    with tarfile.open(archive_path) as archive:
        members = [name for name in archive.getnames() if name.endswith('schema08.partition_existing.root_owner.json')]
        assert len(members) == 1
        owner = json.loads(archive.extractfile(members[0]).read())
    assert owner == policy['root_owner'] == json.loads(Path(policy['extracted_owner']).read_text())
    assert owner['has_oos_file'] == 1 and owner['oos_num_recs'] == 2
    owners[policy['policy']] = owner
    controller = original_attempt / 'CTP/result/shell/case-logs/_40_guava/cbrd_26659_partition_repartition/cases/case' / ('schema08.' + policy['policy'] + '.controller.log')
    failures = [line for line in controller.read_text().splitlines() if line.startswith('FAIL expected_contract=')]
    assert failures == ['FAIL expected_contract=partition_existing.root_has_no_oos']
assert set(owners) == {'default', 'force_outline'}
profiles = [('original', original_attempt, 'FAIL')]
for tag in ['mre01', 'mre02', 'mre03', 'mre04', 'mre05', 'mre06', 'mre07', 'mre06r', 'mre08r']:
    profiles.append((tag, root / tag / 'a25', 'PASS' if tag == 'mre08r' else 'FAIL'))
private_namespaces = {kind: set() for kind in ['pid', 'ipc', 'mnt', 'user']}
owned_installs = set()
owned_slots = set()
known_generations = set()
checks = []
for tag, attempt, expected in profiles:
    identity = json.loads((attempt / 'identity.json').read_text())
    assert identity['source_engine'] == engine_head and identity['tc_head'] == tc_head
    assert identity['preflight_exit'] == 0 and not identity['commit_mismatch_exception_used']
    assert 'commit_match=yes' in (attempt / 'preflight.log').read_text()
    corpus = attempt.parent / 'corpus'
    inventory = json.loads((attempt.parent / 'input-inventory.json').read_text())
    modified = set() if tag == 'original' else {'shell/_40_guava/cbrd_26659_partition_repartition/cases/cbrd_26659_partition_repartition.sh', 'shell/_40_guava/oos_common/oos08_controller.sh'}
    for item in inventory['files']:
        path = corpus / item['path']
        if item['path'] not in modified:
            assert hashlib.sha256(path.read_bytes()).hexdigest() == item['sha256'], str(path)
        assert format(path.stat().st_mode & 0o777, '04o') == item['mode'], str(path)
    for relative, digest in identity['runtime_hashes'].items():
        assert hashlib.sha256((attempt / 'cubrid' / relative).read_bytes()).hexdigest() == digest
    observation = json.loads((attempt / 'observation.json').read_text())
    assert observation['exit'] == 0 and not observation['deadline_outcome']
    assert not observation['remaining_owned_processes'] and not observation['remaining_observed_namespace_holders']
    owned_installs.add(str(attempt / 'cubrid'))
    owned_slots.add(str(attempt / 'slots'))
    known_generations.update((row['pid'], str(row['start_ticks'])) for row in observation['observed_processes'])
    for kind in private_namespaces:
        assert observation['observed_private_namespace_inodes'][kind]
        private_namespaces[kind].update(observation['observed_private_namespace_inodes'][kind])
    result_dir = attempt / 'CTP/result/shell/current_runtime_logs'
    xml_cases = ET.parse(result_dir / 'test-shell.xml').getroot().findall('.//testcase')
    assert len(xml_cases) == 1 and not xml_cases[0].findall('skipped')
    expected_case = (attempt / 'expected-cases.txt').read_text().strip()
    assert xml_cases[0].get('file') == expected_case
    assert (result_dir / 'dispatch_tc_ALL.txt').read_text().splitlines() == [expected_case]
    finished = [line for path in result_dir.glob('dispatch_tc_FIN_*.txt') for line in path.read_text().splitlines() if line]
    assert finished == [expected_case]
    failed = bool(xml_cases[0].findall('failure') or xml_cases[0].findall('error'))
    assert failed == (expected == 'FAIL')
    log = (result_dir / 'test_local.log').read_text()
    if failed:
        assert 'FAIL expected_contract=partition_existing.root_has_no_oos' in log
    verified = subprocess.run(['python3', str(args.focused_helper), 'verify', '--suite', 'shell', '--result-dir', str(result_dir), '--expected-list', str(attempt / 'expected-cases.txt'), '--run-log', str(attempt / 'run.log'), '--runner-exit', '0'], text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=30)
    assert (verified.returncode == 0) == (expected == 'PASS'), verified.stdout
    if tag != 'original':
        record = json.loads((root / tag / 'result.json').read_text())
        case_logs = attempt / 'CTP/result/shell/case-logs/_40_guava/cbrd_26659_partition_repartition/cases/case'
        for key, filename in {'before': 'schema08.before_owner.json.log', 'root_after': 'schema08.partition_existing.root_owner.json.log', 'child_after': 'schema08.child_owner.json.log'}.items():
            assert record['owners'][key] == json.loads((case_logs / filename).read_text())
        metadata = json.loads((attempt / 'diagnostic-input.json').read_text())
        assert metadata['original_oracle_unchanged'] == '.has_oos_file==0'
        assert hashlib.sha256((attempt / 'diagnostic-input.patch').read_bytes()).hexdigest() == metadata['patch_sha256']
        logical = (case_logs / 'schema08.logical.stdout.log').read_text()
        assert re.search(r'\bn\s*:\s*' + str(record['settings']['rows']) + r'\b', logical)
        assert re.search(r'\bexact_rows\s*:\s*' + str(record['settings']['rows']) + r'\b', logical)
    checks.append({'tag': tag, 'verdict': expected, 'runner_exit': 0, 'verifier_exit': verified.returncode, 'cleanup_clear': True})
large = json.loads((root / 'mre06r/result.json').read_text())
small = json.loads((root / 'mre08r/result.json').read_text())
sa = json.loads((root / 'mre07/result.json').read_text())
assert {key for key in large['settings'] if large['settings'][key] != small['settings'][key]} == {'small_payload'}
assert {key for key in large['settings'] if large['settings'][key] != sa['settings'][key]} == {'mode'}
assert large['owners']['root_after']['has_oos_file'] == 1
assert small['owners']['root_after']['has_oos_file'] == 0
assert sa['owners']['root_after']['has_oos_file'] == 1 and sa['owners']['root_after']['oos_num_recs'] == 0
assert sa['owners']['before']['oos_file_id'] == sa['owners']['root_after']['oos_file_id']
assert sa['owners']['root_after']['oos_file_id'] != sa['owners']['child_after']['oos_file_id']
unqualified = json.loads((root / 'replay01/a25/observer-failure-and-cleanup.json').read_text())
assert unqualified['runner_exit'].startswith('unknown') and not unqualified['matching_owned_processes']
prototype = json.loads((root / 'mre08/prototype-control-status.json').read_text())
assert prototype['framework_failure'] == 'missing all_required_phases'
old_helper = (root / 'mre08/corpus/shell/_40_guava/oos_common/oos08_controller.sh').read_text()
new_helper = (root / 'mre08r/corpus/shell/_40_guava/oos_common/oos08_controller.sh').read_text()
assert old_helper == new_helper.replace('pass all_required_phases', 'pass diagnostic_observations_complete')
source = subprocess.check_output(['git', '-C', str(args.engine), 'show', engine_head + ':src/storage/oos_file.cpp'], text=True)
function = source[source.index('oos_get_stats_by_vfid (THREAD_ENTRY'):]
assert function.index('out->has_oos_file = 1;') < function.index('out->num_recs = (int) total_recs;')
remaining = []
namespace_holders = []
foreign_namespace_matches = []
for proc in Path('/proc').iterdir():
    if not proc.name.isdigit():
        continue
    try:
        if proc.stat().st_uid != os.getuid():
            continue
        env = (proc / 'environ').read_bytes().split(b'\0')
        selected = dict(value.decode(errors='replace').split('=', 1) for value in env if value.startswith((b'CUBRID=', b'TESTKIT_SLOT_ROOT=')))
        start_ticks = (proc / 'stat').read_text().rsplit(')', 1)[1].split()[19]
        known_generation = (int(proc.name), start_ticks) in known_generations
        task_owned = known_generation or selected.get('CUBRID') in owned_installs or selected.get('TESTKIT_SLOT_ROOT') in owned_slots
        if task_owned:
            remaining.append(int(proc.name))
        namespaces = {kind: os.readlink(proc / 'ns' / kind) for kind in private_namespaces}
        matching = {kind: namespaces[kind] for kind in namespaces if namespaces[kind] in private_namespaces[kind]}
        if matching:
            record = {'pid': int(proc.name), 'name': (proc / 'comm').read_text().strip(), 'start_ticks': start_ticks, 'matching_namespaces': matching, 'selected_environment': selected}
            foreign = not task_owned and bool(selected.get('CUBRID')) and bool(selected.get('TESTKIT_SLOT_ROOT'))
            (foreign_namespace_matches if foreign else namespace_holders).append(record)
    except (FileNotFoundError, PermissionError, ProcessLookupError):
        continue
assert not remaining, remaining
if namespace_holders:
    print(json.dumps({'namespace_holders': namespace_holders}, ensure_ascii=False), file=sys.stderr)
assert not namespace_holders, namespace_holders
print(json.dumps({'verified': True, 'engine_head': engine_head, 'tc_head': tc_head, 'spec_sha256': spec_hash, 'qualified_observations': checks, 'unqualified_attempts_retained': ['replay01 observer failure', 'mre08 prototype completion-marker failure'], 'original_policy_archives_verified': sorted(owners), 'remaining_owned_processes': remaining, 'remaining_owned_or_unattributed_namespace_holders': namespace_holders, 'foreign_namespace_matches': foreign_namespace_matches, 'scope': 'Evidence and diagnosis only; original testcase is still FAIL and no Engine/TC fix is certified.'}, ensure_ascii=False, indent=2))
