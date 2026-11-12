import argparse
import collections
import json
import os
from pathlib import Path
import subprocess

parser = argparse.ArgumentParser(description='Check OOS CTest timeouts and exact-once GoogleTest coverage.')
parser.add_argument('test_dir', type=Path)
build = parser.parse_args().test_dir.resolve()
registry = json.loads(subprocess.check_output(['ctest', '--test-dir', str(build), '--show-only=json-v1'], text=True))
env = dict(os.environ)
for name in list(env):
    if name.startswith('GTEST_'):
        del env[name]

def cases(command, cwd, overlay):
    output = subprocess.check_output(command + ['--gtest_list_tests'], cwd=cwd,
                                     env=dict(env, **overlay), text=True, timeout=20)
    suite = None
    result = []
    for line in output.splitlines():
        line = line.split('#', 1)[0].rstrip()
        if not line:
            continue
        if not line.startswith(' ') and line.endswith('.'):
            suite = line
        elif line.startswith('  ') and suite:
            result.append(suite + line.strip())
    if not result:
        raise RuntimeError(f'no cases listed: {command}')
    return result

entries = collections.defaultdict(list)
timeouts = {}
for test in registry['tests']:
    command = test['command']
    properties = {p['name']: p['value'] for p in test['properties']}
    timeout = properties.get('TIMEOUT', 0)
    if not isinstance(timeout, (float, int)) or not 0 < timeout <= 60:
        raise RuntimeError(f'invalid timeout: {test["name"]}: {timeout}')
    timeouts[test['name']] = timeout
    binary = Path(command[0]).resolve()
    if not binary.name.startswith('test_'):
        continue
    properties = {p['name']: p['value'] for p in test['properties']}
    overlay = dict(item.split('=', 1) for item in properties.get('ENVIRONMENT', []))
    entries[binary].append((test['name'], command, properties.get('WORKING_DIRECTORY', str(binary.parent)), overlay))

if not entries:
    raise RuntimeError('no GoogleTest entries found')
failures = []
report = {}
for binary in sorted(entries):
    inventory = cases([str(binary), '--gtest_filter=*'], binary.parent, {})
    owners = {case: [] for case in inventory}
    for name, command, cwd, overlay in entries[binary]:
        selected = cases(command, cwd, overlay)
        report[name] = selected
        for case in selected:
            owners[case].append(name)
    for case, selected in owners.items():
        if len(selected) != 1:
            failures.append(f'{binary.name} {case}: {selected}')
print(json.dumps({'ctest_entries': len(timeouts), 'timeouts': timeouts, 'binaries': len(entries), 'cases': sum(len(v) for v in report.values()),
                  'entries': report, 'failures': failures}, indent=2))
raise SystemExit(bool(failures))
