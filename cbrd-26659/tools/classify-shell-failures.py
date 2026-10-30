#!/usr/bin/env /usr/bin/python3
"""Inventory the historical disabled shell cases from retained collector bundles.

--evidence-root is the providers/github-actions/runs directory for engine c4c4f5c.
Requires /usr/bin/python3 and the local cubrid-ci JSON schemas. Inputs are read-only.
"""
import argparse
import collections
import csv
import hashlib
import json
from pathlib import Path
import re
import subprocess
import xml.etree.ElementTree as ET

import jsonschema

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--testcases', required=True, type=Path)
parser.add_argument('--evidence-root', required=True, type=Path)
parser.add_argument('--output', required=True, type=Path)
parser.add_argument('--expected-tc-head', default='a229e1978abc4cc6c280783703c03f75524c0f05')
parser.add_argument('--schema-root', type=Path, default=Path('/home/vimkim/gh/cubrid-ci/schema'))
args = parser.parse_args()
tc = args.testcases.resolve()
runs = args.evidence_root.resolve()
output = args.output.resolve()
if output == tc or tc in output.parents or output == runs or runs in output.parents:
    raise SystemExit('output must be outside the input trees')
engine = 'c4c4f5c5ed55fb0130c72bb261061ec441662554'
expected_runs = {'40311481032': '10a8fc82d34cd2c54c2caa403886e3528852d6fe', '40324320840': '10fb4b63f741a4cc231f37b8184b80839f9d452b'}
head = subprocess.check_output(['git', '-C', str(tc), 'rev-parse', 'HEAD'], text=True).strip()
if head != args.expected_tc_head:
    raise SystemExit(f'testcase HEAD mismatch: {head}')
manifest = tc / 'disabled/oos-pr8128.tsv'
with manifest.open(newline='', encoding='utf-8') as f:
    reader = csv.DictReader(f, delimiter='\t')
    expected_columns = ['original_path', 'disabled_path', 'ci_result', 'seconds', 'reasons', 'original_sha256', 'evidence_run_id', 'evidence_tc_sha']
    if reader.fieldnames != expected_columns:
        raise SystemExit('unexpected manifest columns')
    rows = list(reader)
if len(rows) != 64 or collections.Counter(r['ci_result'] for r in rows) != {'FAIL': 61, 'PASS': 3} or len({r['original_path'] for r in rows}) != 64 or len({r['disabled_path'] for r in rows}) != 64:
    raise SystemExit('manifest counts or path uniqueness mismatch')
validators = {}
for name in ('suite-summary-v2', 'raw-evidence-index-v2', 'failure-v2'):
    schema = json.loads((args.schema_root / f'{name}.schema.json').read_text())
    validators[name] = jsonschema.validators.validator_for(schema)(schema)
bundles = {}
for run, tc_sha in expected_runs.items():
    suite = runs / run / 'attempts/1/test_shell'
    summary_bytes = (suite / 'summary.json').read_bytes()
    summary = json.loads(summary_bytes)
    index = json.loads((suite / 'raw/index.json').read_bytes())
    validators['suite-summary-v2'].validate(summary)
    validators['raw-evidence-index-v2'].validate(index)
    if any(x['run_id'] != int(run) or x['attempt'] != 1 or x['suite'] != 'test_shell' for x in (summary, index)) or summary['collection_state'] != 'complete' or index['summary_sha256'] != hashlib.sha256(summary_bytes).hexdigest():
        raise SystemExit(f'bad suite identity or summary hash: {run}')
    indexed = set()
    for item in index['files']:
        p = (suite / 'raw' / item['path']).resolve()
        if (suite / 'raw').resolve() not in p.parents or item['path'] in indexed:
            raise SystemExit(f'unsafe or duplicate raw path: {item["path"]}')
        b = p.read_bytes()
        if len(b) != item['size_bytes'] or hashlib.sha256(b).hexdigest() != item['sha256']:
            raise SystemExit(f'raw hash mismatch: {p}')
        indexed.add(item['path'])
    if summary['counts']['failures'] != len(summary['failures']):
        raise SystemExit(f'failure count mismatch: {run}')
    for failure in summary['failures']:
        meta = suite / 'failures' / failure['stable_id'] / 'metadata.json'
        data = json.loads(meta.read_text())
        validators['failure-v2'].validate(data)
        if {k: v for k, v in data.items() if k != 'schema_version'} != failure:
            raise SystemExit(f'metadata mismatch: {meta}')
    bundles[run] = (suite, summary, indexed)

cases = []
passes = []
for line, row in enumerate(rows, 2):
    run = row['evidence_run_id']
    if run not in expected_runs or row['evidence_tc_sha'] != expected_runs[run]:
        raise SystemExit(f'unknown run or testcase revision at manifest line {line}')
    disabled = (tc / row['disabled_path']).resolve()
    if tc not in disabled.parents:
        raise SystemExit(f'unsafe disabled path at manifest line {line}')
    try:
        historical = subprocess.run(['git', '-C', str(tc), 'show', f'{row["evidence_tc_sha"]}:{row["original_path"]}'], capture_output=True, check=True).stdout
    except subprocess.CalledProcessError as e:
        raise SystemExit(f'historical testcase object missing or unreadable at line {line}: {e.stderr.decode(errors="replace")}')
    digest = hashlib.sha256(historical).hexdigest()
    if digest != row['original_sha256'] or hashlib.sha256(disabled.read_bytes()).hexdigest() != digest:
        raise SystemExit(f'testcase content hash mismatch at manifest line {line}')
    base = {'original_path': row['original_path'], 'disabled_path': row['disabled_path'], 'manifest_line': line, 'sha256': digest, 'historical_run_id': run, 'historical_tc_sha': row['evidence_tc_sha'], 'historical_seconds': row['seconds']}
    if row['ci_result'] == 'PASS':
        suite, summary, indexed = bundles[run]
        matching = []
        for raw_path in sorted(indexed):
            if re.fullmatch(r'shards/[^/]+/test-shell\.xml', raw_path):
                xml = ET.parse(suite / 'raw' / raw_path)
                matching.extend((raw_path, x) for x in xml.iter('testcase') if x.get('name') == row['original_path'])
        if len(matching) != 1 or list(matching[0][1]) or float(matching[0][1].get('time')) != float(row['seconds']):
            raise SystemExit(f'JUnit pass mismatch at manifest line {line}')
        raw_path, element = matching[0]
        shard_index = raw_path.split('/')[1]
        shards = [s for s in summary['shards'] if s['index'] == shard_index]
        if len(shards) != 1 or shards[0]['build']['sha'] != engine or shards[0]['build']['mode'] != 'debug' or shards[0]['testcases']['sha'] != row['evidence_tc_sha']:
            raise SystemExit(f'pass shard identity mismatch at manifest line {line}')
        passes.append({**base, 'shard': shard_index, 'raw_junit_file': str(suite / 'raw' / raw_path)})
        continue
    suite, summary, indexed = bundles[run]
    matches = [f for f in summary['failures'] if f['name'] == row['original_path']]
    if len(matches) != 1:
        raise SystemExit(f'expected one failure record at manifest line {line}, got {len(matches)}')
    failure = matches[0]
    shard_matches = [s for s in summary['shards'] if s['index'] == failure['shard']]
    if len(shard_matches) != 1:
        raise SystemExit(f'invalid shard at manifest line {line}')
    shard = shard_matches[0]
    if shard['build']['sha'] != engine or shard['build']['mode'] != 'debug' or shard['testcases']['sha'] != row['evidence_tc_sha']:
        raise SystemExit(f'shard identity mismatch at manifest line {line}')
    if float(row['seconds']) != failure['duration_seconds']:
        raise SystemExit(f'duration mismatch at manifest line {line}')
    message_path = (suite / failure['message_path']).resolve()
    if suite.resolve() not in message_path.parents:
        raise SystemExit('unsafe message path')
    message = message_path.read_text()
    diff_path = (suite / failure['diff_path']).resolve() if failure['diff_path'] else None
    if diff_path and suite.resolve() not in diff_path.parents:
        raise SystemExit('unsafe diff path')
    diff = diff_path.read_text() if diff_path else ''
    xml_path = f' shards/{failure["shard"]}/test-shell.xml'.strip()
    if xml_path not in indexed:
        raise SystemExit(f'unindexed JUnit evidence: {xml_path}')
    xml = ET.parse(suite / 'raw' / xml_path)
    xml_cases = [x for x in xml.iter('testcase') if x.get('name') == row['original_path']]
    if len(xml_cases) != 1 or len(xml_cases[0].findall('failure')) != 1 or (xml_cases[0].find('failure').text or '') != message:
        raise SystemExit(f'JUnit message mismatch at manifest line {line}')
    if xml_cases[0].get('classname') != failure['class_name'] or float(xml_cases[0].get('time')) != failure['duration_seconds']:
        raise SystemExit(f'JUnit identity mismatch at manifest line {line}')
    assertions = []
    seen = set()
    basename = Path(row['original_path']).stem
    pattern = re.compile(r'^' + re.escape(basename) + r'-(\d+) : NOK(?:\s+(.*))?$')
    for path, content in ((diff_path, diff), (message_path, message)):
        for n, text in enumerate(content.splitlines(), 1):
            match = pattern.match(text)
            if match and path == diff_path and text not in message.splitlines():
                raise SystemExit(f'diff assertion absent from JUnit message at manifest line {line}')
            if match and (match.group(1), match.group(2) or '') not in seen:
                seen.add((match.group(1), match.group(2) or ''))
                assertions.append({'number': int(match.group(1)), 'label': match.group(2) or '', 'text': text, 'file': str(path), 'line': n})
    phases = []
    errors = []
    for n, text in enumerate(message.splitlines(), 1):
        try:
            event = json.loads(text)
            if isinstance(event, dict) and event.get('event') == 'FAIL':
                phases.append({'phase': event.get('phase'), 'text': text, 'file': str(message_path), 'line': n})
        except ValueError:
            pass
        if re.match(r'^(?:bash: |[^+ ]+\.sh: line \d+: ).*(?:No such file or directory|CUBRID_TMP: unbound variable)', text) or text == 'ERROR: No such file or directory':
            errors.append({'text': text, 'file': str(message_path), 'line': n})
    specific = [a for a in assertions if a['label'] and not re.search(r'controller (?:exit|status|failed)|controller exit|intended churn/storage assertions failed|required schedule incomplete|failed or missing|contract failed|stored record/visibility assertion failed|record boundary assertion failed', a['label'], re.I)]
    tags = []
    if errors:
        first = errors[0]
        text = first['text']
        if 'CUBRID_TMP: unbound variable' in text:
            group = 'CUBRID_TMP unbound variable'
        else:
            missing = re.search(r'(cbrd_\d+_[^ /:]+/cases/[^ /:]+\.sh): No such file or directory', text)
            group = f'missing shell file: {missing.group(1)}' if missing else 'No such file or directory: path unspecified'
        tags.append('message reports a shell error')
    elif phases:
        first = phases[0]
        group = f'JSON FAIL phase: {first["phase"]}'
    elif any('record boundary assertion failed:' in a['label'] for a in assertions):
        first = next(a for a in assertions if 'record boundary assertion failed:' in a['label'])
        group = 'record boundary assertion failed; controller exit=1'
    elif specific:
        first = specific[0]
        label = first['label']
        group = f'NOK assertion: {label.split(":", 1)[0]}'
    else:
        first = assertions[0] if assertions else None
        label = first['label'] if first else ''
        if 'intended churn/storage assertions failed (controller exit 1)' in label:
            group = 'controller exit 1: intended churn/storage assertions failed'
        elif 'snapshot/reclaim controller failed (controller exit 1)' in label:
            group = 'controller exit 1: snapshot/reclaim'
        elif 'rollback-after-vacuum intended pre-image failed (controller exit 1)' in label:
            group = 'controller exit 1: rollback-after-vacuum pre-image'
        else:
            group = 'no specific failure point in extracted evidence'
    if phases:
        tags.extend('JSON FAIL phase: ' + str(x['phase']) for x in phases)
    if any('controller' in a['label'] for a in assertions):
        tags.append('controller failure or status reported')
    if not assertions:
        tags.append('no top-level NOK assertion extracted')
    first_specific = specific[0] if specific else (phases[0] if phases else (errors[0] if errors else None))
    cases.append({**base, 'historical_engine_sha': engine, 'historical_build_mode': shard['build']['mode'], 'historical_build_run_id': shard['build']['run_id'], 'historical_build_run_attempt': shard['build']['run_attempt'], 'historical_attempt': 1, 'shard': failure['shard'], 'stable_id': failure['stable_id'], 'metadata_file': str(suite / 'failures' / failure['stable_id'] / 'metadata.json'), 'message_file': str(message_path), 'diff_file': str(diff_path) if diff_path else None, 'raw_junit_file': str(suite / 'raw' / xml_path), 'assertions': assertions, 'json_fail_events': phases, 'observed_shell_errors': errors, 'first_specific_failure': first_specific, 'primary_signature_evidence': first, 'primary_symptom_group': group, 'secondary_symptom_tags': sorted(set(tags)), 'cause_status': 'unknown', 'current_reproduction': 'not_run'})
counts = dict(sorted(collections.Counter(c['primary_symptom_group'] for c in cases).items()))
result = {'engine_sha': engine, 'testcase_head': head, 'manifest_file': str(manifest), 'manifest_sha256': hashlib.sha256(manifest.read_bytes()).hexdigest(), 'counts': {'manifest_rows': len(rows), 'historical_failures': len(cases), 'historical_slow_passes': len(passes), 'primary_groups': counts}, 'validation': {'schemas': ['suite-summary-v2', 'raw-evidence-index-v2', 'failure-v2'], 'raw_index_files_verified': {run: len(bundles[run][2]) for run in sorted(bundles)}, 'summary_hash_and_run_attempt_suite_checked': True, 'referenced_shard_build_and_testcase_checked': True, 'all_manifest_current_and_historical_entry_sha256_checked': True, 'failure_messages_equal_indexed_junit': True, 'note': 'Raw index verifies retained file integrity against its recorded hashes; it is not an independent provider attestation. Specific observations are signature-based and are not proof of causal order.'}, 'historical_slow_passes': passes, 'historical_failures': cases}
output.parent.mkdir(parents=True, exist_ok=True)
output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + '\n')
for group, count in counts.items():
    print(f'{count:2}  {group}')
