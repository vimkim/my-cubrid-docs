from pathlib import Path
import hashlib
import json
import subprocess

import jsonschema

root = Path(__file__).parent
schemas = Path('/home/vimkim/gh/cubrid-ci/schema')
head_sha = '4be72fc209ae9cb8aa1709573d7d0ae7fc06df7c'
requested = ['test_medium', 'test_sql', 'test_shell']


def load(path):
    return json.loads(path.read_text())


def validate(data, name):
    jsonschema.Draft202012Validator(load(schemas / name)).validate(data)


def safe(base, relative):
    assert not Path(relative).is_absolute(), relative
    path = (base / relative).resolve()
    assert path.is_relative_to(base.resolve()), relative
    assert path.is_file(), path
    return path


result = load(root / 'base-result.json')
validate(result, 'command-result-v3.schema.json')
assert result['repository'] == 'CUBRID/cubrid'
assert result['selection']['commit'] == result['commit']
relationship = result['selection']['baseline']
assert relationship['pr_number'] == 7927
assert relationship['pr_url'] == 'https://github.com/CUBRID/cubrid/pull/7927'
assert relationship['head_sha'] == head_sha
assert relationship['head_ref'] == 'feat/oos-deferred-write'
assert relationship['target_ref'] == 'feature/oos-merge'
assert relationship['merge_base'] == result['commit']

out = Path(result['output_dir'])
manifest = load(out / 'manifest.json')
validate(manifest, 'manifest-v3.schema.json')
assert manifest == result
matches = []
for directory in (out / 'observations').iterdir():
    terminal_path = directory / 'result.json'
    if terminal_path.exists():
        terminal = load(terminal_path)
        if terminal.get('command') == result:
            matches.append((directory, terminal))
assert len(matches) == 1, len(matches)
directory, terminal = matches[0]
request = load(directory / 'request.json')
validate(request, 'collection-observation-request-v2.schema.json')
validate(terminal, 'collection-observation-result-v2.schema.json')
assert request['observation_id'] == terminal['observation_id'] == directory.name
assert request['repository'] == result['repository']
assert request['commit'] == result['commit']
assert request['selection'] == result['selection']
assert request['requested_suites'] == requested
assert set(manifest['suites']) == set(requested)
assert request['binary_budget'] == {
    'include': False, 'per_file_bytes': 268435456, 'total_bytes': 536870912,
}
assert request['fetch_concurrency'] == {'value': 40, 'source': 'default'}
budget = terminal['binary_budget']
assert budget['configured_bytes'] == budget['consumed_bytes'] + budget['remaining_bytes']
assert budget['consumed_bytes'] == 0 and not budget['artifacts']

validated = {}
raw_files = 0
raw_bytes = 0
for name in requested:
    state = manifest['suites'][name]
    if state['state'] != 'completed':
        validated[name] = {'state': state['state'], 'complete': False}
        continue
    summary_path = safe(out, state['summary'])
    suite_dir = summary_path.parent
    summary = load(summary_path)
    validate(summary, 'suite-summary-v2.schema.json')
    assert summary['suite'] == name
    assert summary['collection_state'] == 'complete'
    assert summary['run_id'] == state['execution']['run_id']
    assert summary['attempt'] == state['execution']['attempt']
    if 'status' in state:
        assert state['status']['reported_for_sha'] == result['commit']
    counts = summary['counts']
    assert counts['tests'] == sum(counts[k] for k in ('passed', 'failures', 'errors', 'skipped'))
    assert counts['planned'] == sum(counts[k] for k in ('run', 'unrun', 'skipped'))
    assert len(summary['failures']) == counts['failures'] + counts['errors']
    raw_index = load(suite_dir / 'raw/index.json')
    validate(raw_index, 'raw-evidence-index-v2.schema.json')
    assert raw_index['suite'] == name
    assert raw_index['run_id'] == summary['run_id']
    assert raw_index['attempt'] == summary['attempt']
    assert raw_index['summary_sha256'] == hashlib.sha256(summary_path.read_bytes()).hexdigest()
    seen_paths = set()
    for entry in raw_index['files']:
        assert entry['path'] not in seen_paths
        seen_paths.add(entry['path'])
        path = safe(suite_dir / 'raw', entry['path'])
        data = path.read_bytes()
        assert len(data) == entry['size_bytes']
        assert hashlib.sha256(data).hexdigest() == entry['sha256']
        raw_files += 1
        raw_bytes += len(data)
    seen_failures = set()
    for failure in summary['failures']:
        stable_id = failure['stable_id']
        assert stable_id not in seen_failures
        seen_failures.add(stable_id)
        metadata_path = safe(suite_dir, f'failures/{stable_id}/metadata.json')
        metadata = load(metadata_path)
        validate(metadata, 'failure-v2.schema.json')
        assert metadata == dict(schema_version=2, **failure)
        safe(suite_dir, metadata['message_path'])
        if metadata.get('diff_path'):
            safe(suite_dir, metadata['diff_path'])
    metadata_ids = {p.parent.name for p in (suite_dir / 'failures').glob('*/metadata.json')}
    assert metadata_ids == seen_failures
    acquisition = terminal['acquisition'][name]
    assert not acquisition.get('errors')
    assert set(acquisition['shards']) == {s['index'] for s in summary['shards']}
    for shard in summary['shards']:
        assert shard['build']['sha'] == result['commit']
        assert shard['build']['mode'] == 'debug'
        assert acquisition['shards'][shard['index']]['state'] == 'retained'
    validated[name] = {
        'state': state['state'], 'complete': True, 'verdict': summary['verdict'],
        'counts': counts, 'run_id': summary['run_id'], 'attempt': summary['attempt'],
        'testcase_shas': sorted({s['testcases']['sha'] for s in summary['shards']}),
        'shards': len(summary['shards']), 'failure_metadata_count': len(seen_failures),
        'summary_path': str(summary_path), 'raw_files': len(raw_index['files']),
    }

complete = all(s['complete'] for s in validated.values())
assert result['ok'] == complete
assert (terminal['outcome'] == 'complete') == complete
baseline_state = 'validated_exact' if complete else 'partial_exact' if any(s['complete'] for s in validated.values()) else 'unavailable'
assessment = load(root / 'assessment.json')
assessment['baseline'] = baseline_state
(root / 'assessment.json').write_text(json.dumps(assessment, indent=2) + '\n')
receipt = {
    'valid': True, 'baseline_state': baseline_state,
    'observation_id': directory.name, 'observation_dir': str(directory),
    'relationship': relationship, 'selection_coverage': result['selection']['coverage'],
    'selected_candidates': result['selection']['candidates'], 'suites': validated,
    'raw_files_validated': raw_files, 'raw_bytes_validated': raw_bytes,
    'manifest_sha256': hashlib.sha256((out / 'manifest.json').read_bytes()).hexdigest(),
}
(root / 'base-validation.json').write_text(json.dumps(receipt, indent=2) + '\n')
mode = subprocess.check_output([
    'python3', '/home/vimkim/.agents/skills/cubrid-ci-analyze/scripts/report_mode.py',
    str(root / 'assessment.json'),
], text=True)
(root / 'report-mode.json').write_text(mode)
print(json.dumps(receipt, indent=2))
print(mode)
