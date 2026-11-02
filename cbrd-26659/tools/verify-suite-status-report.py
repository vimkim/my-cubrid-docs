#!/usr/bin/env python3
import argparse
from collections import Counter
import csv
import hashlib
import json
from pathlib import Path
import subprocess
import xml.etree.ElementTree as ET

parser = argparse.ArgumentParser(description='Validate retained suite evidence and count distinct OOS testcase identities without running tests.')
parser.add_argument('--evidence', type=Path, required=True)
parser.add_argument('--schemas', type=Path, default=Path('/home/vimkim/gh/cubrid-ci/schema'))
parser.add_argument('--output', type=Path, required=True)
args = parser.parse_args()
root = args.evidence.resolve(strict=True)
assert not args.output.exists(), 'use a fresh output path'
assert subprocess.run(['git', '-C', str(root), 'rev-parse', '--is-inside-work-tree'], capture_output=True).returncode != 0
assert subprocess.run(['git', '-C', str(args.output.parent.resolve(strict=True)), 'rev-parse', '--is-inside-work-tree'], capture_output=True).returncode != 0
baseline = json.loads((root / 'baseline.json').read_text())
command = json.loads((root / 'collect-result.json').read_text())
bundle = Path(command['output_dir']).resolve(strict=True)
manifest = json.loads((bundle / 'manifest.json').read_text())
observations = []
for candidate in (bundle / 'observations').glob('*/result.json'):
    data = json.loads(candidate.read_text())
    if data.get('command') == command:
        observations.append(candidate.parent)
assert len(observations) == 1
observation = observations[0]
request = json.loads((observation / 'request.json').read_text())
result = json.loads((observation / 'result.json').read_text())
assert request['observation_id'] == result['observation_id']
assert request['commit'] == command['commit'] == manifest['commit'] == baseline['engine']['head']
assert request['requested_suites'] == ['test_medium', 'test_sql', 'test_shell']
assert manifest == command and result['command'] == command
validations = [(observation / 'request.json', 'collection-observation-request-v1'),
               (observation / 'result.json', 'collection-observation-result-v1'),
               (root / 'collect-result.json', 'command-result-v2'),
               (bundle / 'manifest.json', 'manifest-v2')]
ci = {}
shell_cases = {}
for suite in ['test_medium', 'test_shell']:
    item = command['suites'][suite]
    assert item['state'] == 'completed'
    summary_path = bundle / item['summary']
    summary = json.loads(summary_path.read_text())
    index_path = summary_path.parent / 'raw/index.json'
    index = json.loads(index_path.read_text())
    validations.extend([(summary_path, 'suite-summary-v2'), (index_path, 'raw-evidence-index-v2')])
    assert summary['run_id'] == item['execution']['run_id'] == 41431239377
    assert summary['attempt'] == item['execution']['attempt'] == 1
    assert index['run_id'] == summary['run_id'] and index['attempt'] == summary['attempt'] and index['suite'] == suite
    assert hashlib.sha256(summary_path.read_bytes()).hexdigest() == index['summary_sha256']
    raw = summary_path.parent / 'raw'
    for declared in index['files']:
        path = (raw / declared['path']).resolve(strict=True)
        assert path.is_relative_to(raw.resolve())
        content = path.read_bytes()
        assert len(content) == declared['size_bytes'] and hashlib.sha256(content).hexdigest() == declared['sha256']
    counts = summary['counts']
    assert counts['tests'] == counts['passed'] + counts['failures'] + counts['errors'] + counts['skipped']
    assert counts['planned'] == counts['run'] + counts['unrun'] + counts['skipped']
    assert len(summary['failures']) == counts['failures'] + counts['errors']
    tc_head = baseline['regular' if suite == 'test_shell' else 'public']['head']
    for shard in summary['shards']:
        assert shard['build']['sha'] == command['commit'] and shard['testcases']['sha'] == tc_head
        assert result['acquisition'][suite]['shards'][shard['index']]['state'] == 'retained'
    seen = Counter()
    statuses = Counter()
    for path in raw.glob('shards/*/*.xml'):
        for node in ET.parse(path).iter('testcase'):
            name = node.get('name')
            assert name
            status = 'FAIL' if node.find('failure') is not None else 'ERROR' if node.find('error') is not None else 'SKIP' if node.find('skipped') is not None else 'PASS'
            seen[name] += 1
            statuses[status] += 1
            if suite == 'test_shell':
                assert name not in shell_cases
                shell_cases[name] = {'status': status, 'xml': str(path)}
    assert sum(seen.values()) == counts['tests']
    assert statuses == Counter({'PASS': counts['passed'], 'FAIL': counts['failures'], 'ERROR': counts['errors'], 'SKIP': counts['skipped']})
    ci[suite] = {'counts': counts, 'shards': len(summary['shards']), 'source': str(summary_path), 'raw_hashes': len(index['files'])}
validation_log = []
for path, schema in validations:
    execution = subprocess.run(['jsonschema', '-i', str(path), str(args.schemas / (schema + '.schema.json'))], capture_output=True, text=True)
    validation_log.append({'path': str(path), 'schema': schema, 'exit': execution.returncode, 'stderr': execution.stderr})
    assert execution.returncode == 0, validation_log[-1]
regular = Path(baseline['regular']['path'])
public = Path(baseline['public']['path'])
heavy = Path(baseline['heavy']['path'])
source_paths = {}
for name in ['regular', 'public', 'heavy']:
    repo = Path(baseline[name]['path'])
    assert subprocess.check_output(['git', '-C', str(repo), 'rev-parse', 'HEAD'], text=True).strip() == baseline[name]['head']
    assert subprocess.check_output(['git', '-C', str(repo), 'status', '--porcelain=v1'], text=True) == baseline[name]['status']
    source_paths[name] = subprocess.check_output(['git', '-C', str(repo), 'ls-tree', '-r', '--name-only', baseline[name]['head']], text=True).splitlines()
active = [name for name in source_paths['regular'] if name.startswith('shell/_40_guava/cbrd_26659') and Path(name).name == Path(name).parent.parent.name + '.sh']
quarantine = list(csv.DictReader((regular / 'disabled/oos-pr8128.tsv').open(), delimiter='\t'))
assert len(active) == 31 and len(quarantine) == 64
assert Counter(row['ci_result'] for row in quarantine) == {'FAIL': 61, 'PASS': 3}
assert all((regular / row['disabled_path']).is_file() for row in quarantine)
assert 'shell/_40_guava/cbrd_27237_rollback_vacuum/cases/cbrd_27237_rollback_vacuum.sh' in {row['original_path'] for row in quarantine}
for name in active:
    assert shell_cases[name]['status'] == 'PASS'
sql = [name for name in source_paths['public'] if name.startswith('sql/_36_guava/cbrd_26659/cases/') and name.endswith('.sql')]
assert len(sql) == 28
for name in sql:
    answer = name.replace('/cases/', '/answers/').removesuffix('.sql') + '.answer'
    assert answer in source_paths['public']
heavy_entries = [name for name in source_paths['heavy'] if name.startswith('shell_heavy/_40_guava/cbrd_26659') and Path(name).name == Path(name).parent.parent.name + '.sh']
heavy_ids = {Path(name).stem for name in heavy_entries}
assert len(heavy_ids) == 38
heavy_records = json.loads((root / 'heavy/records.json').read_text())
assert {row['id'] for row in heavy_records['cases']} == heavy_ids
for row in heavy_records['cases']:
    path = Path(row['path'])
    assert hashlib.sha256(path.read_bytes()).hexdigest() == row['sha256_current']
    assert row['historical_status'] == 'PASS'
heavy_attempts = {row['historical_run'] for row in heavy_records['cases']}
assert len(heavy_attempts) == 1
heavy_xml = Path(next(iter(heavy_attempts))) / 'CTP/result/shell/current_runtime_logs/test-shell.xml'
heavy_nodes = list(ET.parse(heavy_xml).iter('testcase'))
assert len(heavy_nodes) == 38
assert {Path(node.get('name')).stem for node in heavy_nodes} == heavy_ids
assert all(not list(node) for node in heavy_nodes)
ha = json.loads((root / 'ha/records.json').read_text())
ha_ids = {row['id'] for row in ha['cases']}
assert len(ha_ids) == 6
ha_statuses = Counter(row['current_selection_status'] for row in ha['cases'] if row['selection'] == 'active')
assert ha_statuses == {'PASS': 2, 'FAIL': 2}
for row in ha['cases']:
    assert hashlib.sha256(Path(row['path']).read_bytes()).hexdigest() == row['sha256']
    if row['selection'] == 'active':
        latest = [item for item in row['attempts'] if Path(item['attempt']).name == 'ha-native-05-final']
        assert len(latest) == 1
        raw = Path(latest[0]['xml'])
        assert hashlib.sha256(raw.read_bytes()).hexdigest() == latest[0]['xml_sha256']
        nodes = [node for node in ET.parse(raw).iter('testcase') if Path(node.get('name')).stem == row['id']]
        assert len(nodes) == 1
        status = 'FAIL' if nodes[0].find('failure') is not None else 'ERROR' if nodes[0].find('error') is not None else 'SKIP' if nodes[0].find('skipped') is not None else 'PASS'
        assert status == row['current_selection_status'] == latest[0]['status']
normal_ids = {Path(name).stem for name in active} | {Path(row['original_path']).stem for row in quarantine}
assert len(normal_ids) == 95 and not normal_ids & heavy_ids and not normal_ids & ha_ids and not heavy_ids & ha_ids
assert len(normal_ids | heavy_ids | ha_ids) == 139
assert len(sql) + len(normal_ids | heavy_ids | ha_ids) == 167
assert command['suites']['test_sql']['state'] == 'collection_failed'
assert any(row['kind'] == 'integrity' and row['suite'] == 'test_sql' for row in command['errors'])
assert len(result['acquisition']['test_sql']['shards']) == 10 and all(row['state'] == 'retained' for row in result['acquisition']['test_sql']['shards'].values())
sql_raw = bundle / 'providers/github-actions/runs/41431239377/attempts/1/test_sql/raw/shards/01'
done = dict(line.split('=', 1) for line in (sql_raw / 'shard.done').read_text().splitlines())
sql_xml_count = len(list(ET.parse(sql_raw / 'linux_sql_64bit.xml').iter('testcase')))
assert int(done['assigned']) == 3533 and sql_xml_count == 3531
assessment = {'identity': 'established', 'observation': result['outcome'], 'manifest': 'validated', 'requested_summaries': 'partial', 'result_matches_observation': True, 'requested_suites_reconciled': False, 'baseline': 'not_assessed'}
assessment_path = root / 'report-mode-assessment.json'
assessment_path.write_text(json.dumps(assessment, indent=2) + '\n')
mode = json.loads(subprocess.check_output(['python3', '/home/vimkim/.agents/skills/cubrid-ci-analyze/scripts/report_mode.py', str(assessment_path)], text=True))
assert mode['mode'] == 'warning' and not mode['regression_conclusions_allowed']
old_failure = {name: data for name, data in shell_cases.items() if name == 'shell/_40_guava/cbrd_25977/cases/cbrd_25977.sh'}
assert len(old_failure) == 1 and next(iter(old_failure.values()))['status'] == 'PASS'
output = {'engine': command['commit'], 'run': 41431239377, 'observation': str(observation), 'schema_validations': validation_log, 'ci': ci, 'ci_report_mode': mode, 'sql_integrity': {'assigned': int(done['assigned']), 'junit': sql_xml_count, 'suite_validated': False}, 'inventory': {'sql': len(sql), 'regular_active': len(active), 'regular_quarantined': len(quarantine), 'regular_total': len(normal_ids), 'heavy': len(heavy_ids), 'ha': len(ha_ids), 'unique_shell_families': 139, 'functional_sql_and_shell': 167}, 'regular_active_verdicts': Counter(shell_cases[name]['status'] for name in active), 'ha_selected_verdicts': ha_statuses, 'historical_non_oos_failure_current': old_failure, 'new_test_execution': False}
args.output.write_text(json.dumps(output, indent=2, ensure_ascii=False) + '\n')
print(json.dumps({key: value for key, value in output.items() if key not in ['schema_validations', 'historical_non_oos_failure_current']}, indent=2, ensure_ascii=False))
