#!/usr/bin/env python3
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import xml.etree.ElementTree as ET

parser = argparse.ArgumentParser(description='Verify retained SQL restoration evidence without running tests.')
parser.add_argument('--artifacts', type=Path, required=True)
parser.add_argument('--testcases', type=Path, required=True)
parser.add_argument('--engine', type=Path, required=True)
parser.add_argument('--reactivated-commit', required=True)
parser.add_argument('--producer', type=Path, required=True)
parser.add_argument('--original-artifacts', type=Path, default=Path('/home/vimkim/temp/cbrd-26659-sql-disabled-20261030'))
args = parser.parse_args()
if sys.flags.optimize:
    parser.error('Run without -O; this verifier uses assertions.')
root = args.artifacts.resolve()
base = '45e21ad799d82ebadc04a93c7d2f69517d53bf39'
engine = 'e3589ae42d42b04eb020e1ae43e165b01d31b12a'
fixed = (root / 'answer-fix-commit.txt').read_text().strip()
final = args.reactivated_commit
assert re.fullmatch(r'[0-9a-f]{40}', fixed) and re.fullmatch(r'[0-9a-f]{40}', final)
for rev in [base, fixed, final]:
    assert subprocess.check_output(['git', '-C', str(args.testcases), 'rev-parse', rev + '^{commit}'], text=True).strip() == rev
subprocess.run(['git', '-C', str(args.testcases), 'merge-base', '--is-ancestor', base, fixed], check=True)
subprocess.run(['git', '-C', str(args.testcases), 'merge-base', '--is-ancestor', fixed, final], check=True)
header = subprocess.check_output(['git', '-C', str(args.engine), 'show', engine + ':src/base/error_code.h'], text=True)
assert re.search(r'^#define\s+ER_HEAP_OOS_OVERPASS_MAXOBJ_SIZE\s+-1388\s*$', header, re.M)
normal = 'sql/_36_guava/cbrd_26659/'
disabled = 'disabled/failing/' + normal
cases = [('r01', 'rb05', 'record_boundaries', 1), ('b01', 'b03', 'sql05_bigone', 2), ('l01', 'l01', 'sql09_lob_maxcols', 1)]
names = ['cbrd_26659_oos_' + item[2] for item in cases]
trees = {}
for rev in [base, fixed, final]:
    lines = subprocess.check_output(['git', '-C', str(args.testcases), 'ls-tree', '-r', rev], text=True).splitlines()
    trees[rev] = {line.split('\t', 1)[1]: tuple(line.split('\t', 1)[0].split()) for line in lines}
changed = {path for path in trees[base].keys() | trees[fixed].keys() if trees[base].get(path) != trees[fixed].get(path)}
assert changed == {disabled + 'answers/' + name + '.answer' for name in names}, changed
base_cases = {p for p in trees[base] if p.startswith(normal + 'cases/') and p.endswith('.sql')}
base_answers = {p for p in trees[base] if p.startswith(normal + 'answers/') and p.endswith('.answer')}
assert len(base_cases) == len(base_answers) == 25
assert {Path(p).stem for p in base_cases} == {Path(p).stem for p in base_answers}
assert all(trees[base][p] == trees[final].get(p) for p in base_cases | base_answers)
final_cases = {p for p in trees[final] if p.startswith(normal + 'cases/') and p.endswith('.sql')}
final_answers = {p for p in trees[final] if p.startswith(normal + 'answers/') and p.endswith('.answer')}
assert len(final_cases) == len(final_answers) == 28
assert {Path(p).stem for p in final_cases} == {Path(p).stem for p in final_answers}
assert not any(p.startswith(disabled) for p in trees[final])
manifest = subprocess.check_output(['git', '-C', str(args.testcases), 'show', final + ':disabled/oos-pr8128.tsv'])
assert manifest == b'original_path\tdisabled_path\tci_result\tseconds\treasons\toriginal_sha256\n'
jars = {'sql/lib/cubridqa-cqt.jar': '926a1a6c3d73f91344a3e4a2446b51c7fe7329be5de413d90979ba8209052f0f', 'sql/lib/cubrid_jdbc.jar': '17e2e0ee4c0756b4b0a7cd679f1fea4630124f5704bc69db0c2107235190ff98'}
runtime_files = ['bin/cub_master', 'bin/cub_server', 'bin/csql', 'bin/cubrid', 'bin/cubrid_rel', 'lib/libcubrid.so.11.5']
records = []
for attempt, old_attempt, suffix, changes in cases:
    name = 'cbrd_26659_oos_' + suffix
    run = root / attempt
    identity = json.loads((run / 'identity.json').read_text())
    observation = json.loads((run / 'observation.json').read_text())
    assert (identity['engine'], identity['testcases'], identity['case'], identity['preflight_exit'], identity['testcase_timeout_seconds']) == (engine, fixed, name, 0, 120)
    preflight = (run / 'preflight.log').read_text()
    assert 'source_head=' + engine in preflight and 'commit_match=yes' in preflight
    assert '11.5.0.2793-e3589ae' in (run / 'runtime.txt').read_text()
    assert len(identity['input_files']) == 2
    original = {}
    for folder, ext, disabled_ext in [('cases', '.sql', '.disabled'), ('answers', '.answer', '')]:
        source = disabled + folder + '/' + name + ext + disabled_ext
        target = normal + folder + '/' + name + ext
        old = subprocess.check_output(['git', '-C', str(args.testcases), 'show', base + ':' + source])
        data = subprocess.check_output(['git', '-C', str(args.testcases), 'show', fixed + ':' + source])
        final_data = subprocess.check_output(['git', '-C', str(args.testcases), 'show', final + ':' + target])
        assert trees[base][source][0] == trees[fixed][source][0] == trees[final][target][0]
        assert final_data == data
        if folder == 'cases':
            assert old == data
        else:
            assert old.count(b'Error:-1384') == changes and old.replace(b'Error:-1384', b'Error:-1388') == data
        copy = run / 'testcases' / target
        entry, = [item for item in identity['input_files'] if item['source'] == source]
        assert Path(entry['copy']) == copy and copy.read_bytes() == data
        assert entry['sha256'] == hashlib.sha256(data).hexdigest()
        original[folder] = old
    for path, digest in jars.items():
        assert hashlib.sha256((run / 'CTP' / path).read_bytes()).hexdigest() == identity[path + '_sha256'] == digest
    for path in runtime_files:
        assert hashlib.sha256((run / 'cubrid' / path).read_bytes()).digest() == hashlib.sha256((args.producer / path).read_bytes()).digest()
    case = run / 'testcases' / normal / 'cases' / (name + '.sql')
    assert (run / 'expected-cases.txt').read_text().splitlines() == [str(case)]
    assert (run / 'wrapper-exit.status').read_text().strip() == '0' and (run / 'exit.status').read_text().strip() == '0'
    assert observation['runner_exit'] == observation['verify_exit'] == 0 and observation['watchdog'] is None
    assert observation['case_dispatch_observed'] is True and observation['case_timeout_seconds'] == 120
    log = (run / 'run.log').read_text()
    result = Path(observation['result_root'])
    assert result.is_relative_to(run / 'CTP/sql/result')
    assert re.findall(r'^Result Root Dir:(.+)$', log, re.M) == [str(result)]
    assert re.findall(r'^\[\d\d:\d\d:\d\d\] Testing (.+?) \(1/1 100\.00%\) \[([^]]+)\]$', log, re.M) == [(str(case), 'OK')]
    timing = []
    for filename in ['main.info', 'summary_info']:
        values = dict(line.partition(':')[::2] for line in (result / filename).read_text().splitlines() if ':' in line)
        assert (values['total'], values['success'], values['fail']) == ('1', '1', '0')
        timing.append(int(values['totalTime'].removesuffix('ms')))
        if filename == 'main.info':
            assert values['execute_case'] == '1' and values['result_path'] == str(result) and values['build'] == '11.5.0.2793-e3589ae'
    xml = ET.parse(result / 'linux_sql_64bit.xml')
    suite, = xml.findall('.//testsuite')
    element, = xml.findall('.//testcase')
    assert suite.get('tests') == '1' and suite.get('failures') == '0'
    assert suite.get('errors', '0') == suite.get('skipped', '0') == '0'
    assert element.get('name') == element.get('file') == str(case)
    assert not any(element.findall(tag) for tag in ['failure', 'error', 'skipped'])
    assert timing[0] == timing[1] and 0 <= timing[0] < 120000
    assert float(element.get('time')) == timing[0] / 1000
    assert case.with_suffix('.result').read_bytes() == (run / 'testcases' / normal / 'answers' / (name + '.answer')).read_bytes()
    old_run = args.original_artifacts.resolve() / old_attempt
    old_id = json.loads((old_run / 'identity.json').read_text())
    old_obs = json.loads((old_run / 'observation.json').read_text())
    assert (old_id['engine'], old_id['testcases'], old_id['case'], old_id['preflight_exit']) == (engine, base, name, 0)
    assert old_obs['runner_exit'] == 0 and old_obs['verify_exit'] == 1 and old_obs['watchdog'] is None
    old_case = old_run / 'testcases' / normal / 'cases' / (name + '.sql')
    old_log = (old_run / 'run.log').read_text()
    old_result = Path(old_obs['result_root'])
    assert old_result.is_relative_to(old_run / 'CTP/sql/result')
    assert re.findall(r'^Result Root Dir:(.+)$', old_log, re.M) == [str(old_result)]
    assert re.findall(r'^\[\d\d:\d\d:\d\d\] Testing (.+?) \(1/1 100\.00%\) \[([^]]+)\]$', old_log, re.M) == [(str(old_case), 'NOK')]
    for filename in ['main.info', 'summary_info']:
        old_values = dict(line.partition(':')[::2] for line in (old_result / filename).read_text().splitlines() if ':' in line)
        assert (old_values['total'], old_values['success'], old_values['fail']) == ('1', '0', '1')
    old_xml = ET.parse(old_result / 'linux_sql_64bit.xml')
    old_suite, = old_xml.findall('.//testsuite')
    assert old_suite.get('tests') == '1' and old_suite.get('failures') == '1'
    old_element, = old_xml.findall('.//testcase')
    assert old_element.get('name') == old_element.get('file') == str(old_case) and len(old_element.findall('failure')) == 1
    assert not old_element.findall('error') and not old_element.findall('skipped')
    assert (old_run / 'expected-cases.txt').read_text().splitlines() == [str(old_case)]
    assert old_case.read_bytes() == original['cases']
    assert (old_run / 'testcases' / normal / 'answers' / (name + '.answer')).read_bytes() == original['answers']
    assert old_case.with_suffix('.result').read_bytes() == original['answers'].replace(b'Error:-1384', b'Error:-1388')
    records.append({'case': name, 'seconds': float(element.get('time')), 'original': 'NOK', 'restored': 'PASS'})

control = root / 'g02'
events_list = json.loads((control / 'control-events.json').read_text())
events = {event['event']: event for event in events_list}
assert len(events) == len(events_list)
control_id = json.loads((control / 'identity.json').read_text())
assert control_id['engine'] == engine and control_id['testcase_timeout_seconds'] == 120 and control_id['synthetic_control']['not_original_coverage'] is True
control_case = Path(control_id['input_files'][0]['copy'])
assert hashlib.sha256(control_case.read_bytes()).hexdigest() == control_id['input_files'][0]['sha256']
assert control_id['synthetic_control']['query'].encode() in control_case.read_bytes()
wrapper = Path(control_id['synthetic_control']['wrapper'])
assert hashlib.sha256(wrapper.read_bytes()).hexdigest() == '7e9851812e46478541ca05516614cc4f274f66b352b2760f9243f108434b937d'
for name in ['prefix-live', 'active-30', 'active-90', 'timeout-started']:
    event = events[name]
    assert event['wrapper_alive'] is True and event['verdict_present'] is False and event['last_byte_newline'] is False
    snapshot = (control / (name + '.log')).read_bytes()
    assert re.search(rb'Testing ' + re.escape(str(control_case).encode()) + rb' \(1/1 100\.00%\)$', snapshot)
assert 30 <= events['active-30']['since_prefix'] < 90 <= events['active-90']['since_prefix'] < 120 <= events['timeout-started']['since_prefix'] < 125
p30, = [p for p in events['active-30']['owned_processes'] if p['comm'] == 'cub_server']
p90, = [p for p in events['active-90']['owned_processes'] if p['comm'] == 'cub_server']
assert (p30['pid'], p30['start_ticks'], p30['namespaces']) == (p90['pid'], p90['start_ticks'], p90['namespaces'])
assert p90['cpu_ticks'] > p30['cpu_ticks']
assert events['wrapper-exit']['exit'] == 124
observation = json.loads((control / 'observation.json').read_text())
assert observation['watchdog'] == 'testcase_timeout_120s' and observation['runner_exit'] == 255 and observation['verify_exit'] == 1
assert (control / 'exit.status').read_text().strip() == '255'
for path in [control / 'post-cleanup.json', root / 'sql3-post-cleanup.json']:
    cleanup = json.loads(path.read_text())
    assert cleanup['owned_processes'] == [] and cleanup['contained_namespace_process_holders'] == []
    namespaces = cleanup['observed_contained_namespaces']
    assert namespaces and len(namespaces) == len(set(namespaces))
assert set(p30['namespaces'].values()).issubset(set(json.loads((control / 'post-cleanup.json').read_text())['observed_contained_namespaces']))
print(json.dumps({'restored_sql3_pass': True, 'active_pair_count': 28, 'disabled_count': 0, 'four_expectation_changes': True, 'guard_real120verified': True, 'originalfailurespreserved': True, 'cases': records}, indent=2))
