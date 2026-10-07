"""Validate this review's pinned CI bundles; never reacquire remote evidence."""
import hashlib
import json
from pathlib import Path
import sys

import jsonschema

SCHEMAS = Path('/home/vimkim/gh/cubrid-ci/schema')
HERE = Path(__file__).parent
HEAD = '4be72fc209ae9cb8aa1709573d7d0ae7fc06df7c'
BASE = 'fb567a629cdb390fff920542173fa36f454c74a0'
SUITES = ['test_medium', 'test_sql', 'test_shell']


def read(path):
    return json.loads(path.read_text())


def validate(kind, value):
    jsonschema.Draft202012Validator(read(SCHEMAS / (kind + '.schema.json'))).validate(value)


def safe(root, name):
    assert not Path(name).is_absolute(), name
    path = (root / name).resolve()
    assert path.is_relative_to(root.resolve()) and path.is_file(), str(path)
    return path


def bundle(result_path, baseline=False):
    command = read(result_path)
    version = 3 if baseline else 2
    ov = 2 if baseline else 1
    validate(f'command-result-v{version}', command)
    root = Path(command['output_dir'])
    snapshot = HERE / (('baseline' if baseline else 'head') + '-manifest.json')
    manifest = read(snapshot if snapshot.exists() else root / 'manifest.json')
    validate(f'manifest-v{version}', manifest)
    assert manifest == command
    if not snapshot.exists():
        snapshot.write_bytes((root / 'manifest.json').read_bytes())
    observations = [p for p in (root / 'observations').glob('*/result.json')
                    if read(p).get('command') == command]
    assert len(observations) == 1
    observation_path = observations[0]
    terminal = read(observation_path)
    request = read(observation_path.with_name('request.json'))
    validate(f'collection-observation-result-v{ov}', terminal)
    validate(f'collection-observation-request-v{ov}', request)
    assert terminal['observation_id'] == request['observation_id'] == observation_path.parent.name
    assert terminal['outcome'] == 'complete'
    assert command['ok'] and not command['errors']
    assert terminal['command'] == command
    for label, value in [('request', request), ('result', terminal)]:
        (HERE / (('base' if baseline else 'head') + '-observation-' + label + '.json')).write_text(json.dumps(value, indent=2) + '\n')
    assert request['repository'] == command['repository'] == 'CUBRID/cubrid'
    assert request['requested_suites'] == SUITES
    assert set(command['suites']) == set(SUITES)
    assert not request['binary_budget']['include']
    budget = terminal['binary_budget']
    assert budget['configured_bytes'] == budget['consumed_bytes'] + budget['remaining_bytes']
    assert budget['consumed_bytes'] == 0 and not budget['artifacts']
    assert request['binary_budget'] == {'include': False, 'per_file_bytes': 268435456, 'total_bytes': 536870912}
    assert request['fetch_concurrency'] == {'value': 40, 'source': 'default'}
    sha = BASE if baseline else HEAD
    assert command['commit'] == request['commit'] == sha
    if baseline:
        assert request['selection'] == command['selection']
        selection = command['selection']
        relation = selection['baseline']
        assert selection['commit'] == relation['merge_base'] == BASE
        assert relation['head_sha'] == HEAD and relation['pr_number'] == 7927
        assert relation['target_ref'] == 'feature/oos-merge'
    else:
        assert request['pr'] == command['pr']
        assert command['pr']['head_sha'] == HEAD and command['pr']['number'] == 7927
        status = read(HERE / 'status.json')
        assert status['repository'] == command['repository']
        assert all(status['pr'][k] == command['pr'][k] for k in ('number', 'url', 'title', 'head_sha'))
    failures = []
    summaries = {}
    raw_count = 0
    raw_bytes = 0
    for suite in SUITES:
        state = command['suites'][suite]
        assert state['state'] == 'completed'
        if not baseline:
            assert state['execution']['run_id'] == 37595050033 and state['execution']['attempt'] == 1
        summary_path = safe(root, state['summary'])
        summary = read(summary_path)
        validate('suite-summary-v2', summary)
        assert summary['suite'] == suite
        assert summary['collection_state'] == 'complete'
        assert state['status']['reported_for_sha'] == sha
        acquisition = terminal['acquisition'][suite]
        assert not acquisition.get('errors')
        assert set(acquisition['shards']) == {s['index'] for s in summary['shards']}
        assert all(s['state'] == 'retained' for s in acquisition['shards'].values())
        assert state['execution'] == {'run_id': summary['run_id'], 'attempt': summary['attempt']}
        counts = summary['counts']
        assert counts['tests'] == sum(counts[k] for k in ['passed', 'failures', 'errors', 'skipped'])
        assert counts['planned'] == counts['run'] + counts['unrun'] + counts['skipped']
        assert len(summary['failures']) == counts['failures'] + counts['errors']
        index = read(summary_path.parent / 'raw/index.json')
        validate('raw-evidence-index-v2', index)
        assert index['summary_sha256'] == hashlib.sha256(summary_path.read_bytes()).hexdigest()
        assert (index['suite'], index['run_id'], index['attempt']) == (suite, summary['run_id'], summary['attempt'])
        assert len({f['path'] for f in index['files']}) == len(index['files'])
        for raw in index['files']:
            data = safe(summary_path.parent / 'raw', raw['path']).read_bytes()
            assert len(data) == raw['size_bytes']
            assert hashlib.sha256(data).hexdigest() == raw['sha256']
            raw_count += 1
            raw_bytes += len(data)
        for shard in summary['shards']:
            assert shard['build']['sha'] == sha
            # Suite runs may consume an exact-Engine build from another execution.
            # Build identity is independently recorded by the collector's provenance receipts.
            assert shard['build']['run_id'] > 0 and shard['build']['run_attempt'] > 0
            shard_root = summary_path.parent / 'raw/shards' / shard['index']
            build = dict(line.split('=', 1) for line in safe(shard_root, 'build.read').read_text().splitlines()
                         if '=' in line)
            assert build['sha'] == shard['build']['sha']
            assert build['mode'] == shard['build']['mode']
            assert build['ns'] == shard['build']['namespace']
            assert int(build['run_id']) == shard['build']['run_id']
            assert int(build['run_attempt']) == shard['build']['run_attempt']
            testcase = dict(line.split('=', 1) for line in safe(shard_root, 'tc.read').read_text().splitlines()
                            if '=' in line)
            assert testcase['tc_sha'] == shard['testcases']['sha']
            assert testcase['tc_branch'] == shard['testcases']['branch']
        ids = set()
        for failure in summary['failures']:
            assert failure['stable_id'] not in ids
            ids.add(failure['stable_id'])
            metadata = read(safe(summary_path.parent, 'failures/' + failure['stable_id'] + '/metadata.json'))
            validate('failure-v2', metadata)
            assert metadata == dict(schema_version=2, **failure)
            for key in ['message_path', 'diff_path']:
                if failure.get(key):
                    safe(summary_path.parent, failure[key])
            shard = next(s for s in summary['shards'] if s['index'] == failure['shard'])
            failures.append(dict(suite=suite, **failure, testcase_sha=shard['testcases']['sha'],
                                 evidence_dir=str(summary_path.parent)))
        assert {p.parent.name for p in (summary_path.parent / 'failures').glob('*/metadata.json')} == ids
        summaries[suite] = {'counts': counts, 'run_id': summary['run_id'], 'attempt': summary['attempt'],
                            'testcase_shas': sorted({s['testcases']['sha'] for s in summary['shards']}),
                            'build_modes': sorted({s['build']['mode'] for s in summary['shards']}),
                            'summary_path': str(summary_path), 'shards': len(summary['shards'])}
    return {'commit': sha, 'output_dir': str(root), 'observation': observation_path.parent.name,
            'collected_at': command['collected_at'], 'raw_files_validated': raw_count,
            'summaries': summaries, 'failures': failures, 'raw_bytes_validated': raw_bytes,
            'relationship': command.get('selection', {}).get('baseline'),
            'selection': command.get('selection'), 'binary_budget': budget}


if __name__ == '__main__':
    temp = Path(sys.argv[1])
    result = {'head': bundle(temp / 'result.json')}
    baseline = 'not_assessed'
    if (temp / 'base-result.json').exists():
        result['baseline'] = bundle(temp / 'base-result.json', True)
        baseline = 'validated_exact'
    assessment = dict(identity='established', observation='complete', manifest='validated',
                      requested_summaries='validated', result_matches_observation=True,
                      requested_suites_reconciled=True, baseline=baseline)
    (temp / 'assessment.json').write_text(json.dumps(assessment, indent=2) + '\n')
    (Path(__file__).parent / 'ci-validation.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({k: {x: v[x] for x in ['commit', 'observation', 'raw_files_validated', 'summaries']}
                      for k, v in result.items()}, indent=2))
