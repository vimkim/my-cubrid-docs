#!/usr/bin/env python3
"""Replay historical shard 13 pruning on fresh, isolated filesystem fixtures.

Print JSON to stdout. Inputs are retained evidence and local Git objects; only
new directories beneath ARTIFACTS/pruning-proof-fixtures are written.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
import xml.etree.ElementTree as ET

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--artifacts', type=Path, required=True)
parser.add_argument('--testcases', type=Path, required=True)
parser.add_argument('--image-source', type=Path, required=True)
parser.add_argument('--engine-source', type=Path, required=True)
parser.add_argument('--fixture-root', type=Path)
args = parser.parse_args()
artifacts = args.artifacts.resolve(strict=True)
allowed = (artifacts / 'pruning-proof-fixtures').resolve()
fixture_root = (args.fixture_root or allowed).resolve()
if fixture_root != allowed and allowed not in fixture_root.parents:
    parser.error('fixture root must be inside ARTIFACTS/pruning-proof-fixtures')
for repository in (args.testcases, args.image_source, args.engine_source):
    repo = repository.resolve(strict=True)
    if fixture_root == repo or repo in fixture_root.parents or fixture_root in repo.parents:
        parser.error('fixture root must be separate from source repositories')
if subprocess.run(['git', '-C', str(artifacts), 'rev-parse', '--is-inside-work-tree'], capture_output=True).returncode == 0:
    parser.error('artifacts must be outside a Git worktree')

raw = Path('/home/vimkim/.local/share/cubrid-ci-data/github-actions/CUBRID-cubrid/pr-8128/c4c4f5c5ed55fb0130c72bb261061ec441662554/providers/github-actions/runs/40311481032/attempts/1/test_shell/raw')
probe = artifacts / 'namespaced-ci-probe'
entrypoint = probe / 'docker-entrypoint-155c265.sh'
share = probe / '13.list'
log = probe / 'shard-13-job.log'
image_commit = '155c265eb6e3deef49ce828e6f2b5846d3a9abf5'
tc_commit = '10a8fc82d34cd2c54c2caa403886e3528852d6fe'
workflow_commit = '4781495f01523a3ecc5891e3377ad62cf876a1cd'
prefix = 'cubrid-testcases-private-ex/shell/_40_guava/'
case = prefix + 'cbrd_26659_gap_ctas_cs/cases/cbrd_26659_gap_ctas_cs.sh'
helper = prefix + 'cbrd_26659_schema_policy/cases/policy_ddl.sh'
owner = prefix + 'cbrd_26659_schema_policy/cases/cbrd_26659_schema_policy.sh'
controller = prefix + 'oos_coverage_gaps/controller.sh'
files = [case, helper, owner, controller]
entry_bytes = entrypoint.read_bytes()
share_bytes = share.read_bytes()
assert hashlib.sha256(entry_bytes).hexdigest() == '55965b9c36c67c4f4330b7954202ea292eb617b9139f9bfa46a6f27d283557d2'
assert hashlib.sha256(share_bytes).hexdigest() == '91ced695f3703410067a2a9bb89bb7475bd389c5bb2436e25dde8c922ff825be'
assert subprocess.check_output(['git', '-C', str(args.image_source), 'show', image_commit + ':docker/ci/docker-entrypoint.sh']) == entry_bytes
workflow = subprocess.check_output(['git', '-C', str(args.engine_source), 'show', workflow_commit + ':.github/workflows/gha-ci.yml'])
assert b'cubridci/cubridci:test_rl8.10' in workflow
run = json.loads((raw / 'github/run.json').read_text())
assert (run['id'], run['run_attempt'], run['head_sha'], run['path']) == (40311481032, 1, workflow_commit, '.github/workflows/gha-ci.yml')
meta = (raw / 'plan/split.meta').read_text().splitlines()
assert all(x in meta for x in ('unit=case', 'par=50', 'sha=c4c4f5c5ed55fb0130c72bb261061ec441662554', "tc_sha='" + tc_commit + "'"))
jobs = json.loads((raw / 'github/jobs.json').read_text())['jobs']
job = next(j for j in jobs if j['id'] == 121534251605)
assert job['name'] == 'shard shell 13' and any(s['name'] == 'Keep only my share' and s['conclusion'] == 'success' for s in job['steps'])
log_text = log.read_text()
assert hashlib.sha256(log.read_bytes()).hexdigest() == '72c5187762b4ab6f5a55da9d3254659dfcd704c1c094762de75cf5a003fd984c'
assert log_text.count('delete_testcase_after_each_execution_yn=false') == 2
assert '7dc9f4192bb96988d1bab78df3e45df88628b814' in log_text
lines = share_bytes.decode().splitlines()
assert len(lines) == 72 and lines[21] == case
assert not any(line.startswith(prefix + 'cbrd_26659_schema_policy/cases/') for line in lines)
sources = {path: subprocess.check_output(['git', '-C', str(args.testcases), 'show', tc_commit + ':' + path.split('/', 1)[1]]) for path in files}
helper_hash = hashlib.sha256(sources[helper]).hexdigest()
assert helper_hash == '99bb263ae729f3f02745f88601b86653813d136476af007c2417fae6aedd024c'
current_helper = args.testcases / helper.split('/', 1)[1]
assert current_helper.read_bytes() == sources[helper] and len(sources[helper]) == 1493
snapshot = json.loads((artifacts / 'group-snapshot.json').read_text())
observation = json.loads((artifacts / 'group-assignment-observation.json').read_text())
group = snapshot['historical_group']
records = observation['group_records']
inventory_path = Path('/home/vimkim/temp/cbrd-26659-shell61-20261030/inventory.json')
assert hashlib.sha256(inventory_path.read_bytes()).hexdigest() == snapshot['source_inventory_sha256'] == '1e5c58351a016f6a79d7c7af7f0d33473933c8247346b85446953333ab9b2366'
inventory = json.loads(inventory_path.read_text())
assert group == [row for row in inventory['historical_failures'] if 'policy_ddl.sh' in row['primary_symptom_group']]
assert len(group) == len(records) == 39
assert {x['original_path'] for x in group} == {x['case'] for x in records}
assert all(x['historical_tc_sha'] == tc_commit and x['historical_run_id'] == '40311481032' and x['historical_attempt'] == 1 for x in group)
assert len({x['shard'] for x in records}) == 30
assert observation['owner_case'] == owner.split('/', 1)[1] and observation['owner_shards'] == ['31']
assert sum(x['schema_policy_case_in_same_junit'] for x in records) == 0
executed = {path.parent.name: [case.get('name') for case in ET.parse(path).iter('testcase')] for path in (raw / 'shards').glob('*/test-shell.xml')}
assert [shard for shard, names in executed.items() if observation['owner_case'] in names] == ['31']
for record in records:
    names = executed[record['shard']]
    assert record['case'] in names and len(names) == record['executed_cases_in_shard']
    assert record['schema_policy_case_in_same_junit'] == (observation['owner_case'] in names)
fixture_root.mkdir(parents=True, exist_ok=True)
results = []
for variant, selection in [('actual_share', share_bytes), ('owner_selected_control', share_bytes + owner.encode() + b'\n')]:
    work = Path(tempfile.mkdtemp(prefix=variant + '-', dir=fixture_root)).resolve()
    assert fixture_root in work.parents
    for path, data in sources.items():
        destination = work / path
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(data)
    (work / 'share.list').write_bytes(selection)
    relative = (work / case).parent / '../../cbrd_26659_schema_policy/cases/policy_ddl.sh'
    assert relative.resolve() == work / helper and relative.read_bytes() == sources[helper]
    execution = subprocess.run(['bash', str(entrypoint), 'keep', 'case', str(work / 'cubrid-testcases-private-ex/shell'), str(work / 'share.list')], env={**os.environ, 'WORKDIR': str(work)}, capture_output=True, text=True)
    assert execution.returncode == 0, execution.stderr
    presence = {name: (work / path).is_file() for name, path in [('representative', case), ('controller', controller), ('helper', helper), ('schema_owner', owner)]}
    expected = variant == 'owner_selected_control'
    assert presence == {'representative': True, 'controller': True, 'helper': expected, 'schema_owner': expected}
    assert relative.resolve() == work / helper and relative.is_file() == expected
    results.append({'variant': variant, 'fixture': str(work), 'keep_exit': execution.returncode, 'presence': presence, 'relative_helper_resolves_to_expected_path': True, 'relative_helper_present': relative.is_file()})
print(json.dumps({'source_mechanism_verified': True, 'actual_historical_image_identity_verified': False, 'historical_attribution': 'strong_inference', 'historical_image_tag': 'cubridci/cubridci:test_rl8.10', 'engine_sha': 'c4c4f5c5ed55fb0130c72bb261061ec441662554', 'workflow_sha': workflow_commit, 'tc_sha': tc_commit, 'entrypoint_source_sha': image_commit, 'entrypoint_sha256': hashlib.sha256(entry_bytes).hexdigest(), 'share_sha256': hashlib.sha256(share_bytes).hexdigest(), 'helper_sha256': helper_hash, 'helper_bytes': len(sources[helper]), 'workflow_sha256': hashlib.sha256(workflow).hexdigest(), 'job_log_sha256': hashlib.sha256(log.read_bytes()).hexdigest(), 'group_source_inventory_sha256': snapshot['source_inventory_sha256'], 'observed_junit_group_cases': len(records), 'observed_junit_group_shards': len({x['shard'] for x in records}), 'observed_junit_cases_with_owner_in_same_set': 0, 'observed_junit_owner_shards': observation['owner_shards'], 'variants': results, 'limits': ['Historical image digest and entrypoint bytes are not established.', 'JUnit executed sets are not exact shard lists for all group cases.', 'This probe does not establish one cause for all 39 cases or a native test verdict.']}, indent=2))
