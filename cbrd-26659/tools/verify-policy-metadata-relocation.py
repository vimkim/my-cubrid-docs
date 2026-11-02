#!/usr/bin/env python3
"""Prove metadata parser equivalence and availability under real case pruning."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

BASE = '6334dc6cd74683ca6ba10439372a21bd36b453d3'
CI_REV = '155c265eb6e3deef49ce828e6f2b5846d3a9abf5'
CI_PATH = 'docker/ci/docker-entrypoint.sh'
CI_HASH = '55965b9c36c67c4f4330b7954202ea292eb617b9139f9bfa46a6f27d283557d2'
HELPER_HASH = '1d5df9878f4b3a5048b5458171043e513a69a4454e3744b448284b322d5ea048'
CAT = 'shell/_40_guava'
OLD = f'{CAT}/cbrd_26659_policy_contract/cases/policy_metadata.sh'
NEW = f'{CAT}/oos_common/policy_metadata.sh'
OWNER = f'{CAT}/cbrd_26659_policy_contract/cases/cbrd_26659_policy_contract.sh'
CONTROLLERS = {
    f'{CAT}/oos_common/oos08_controller.sh': ('../../cbrd_26659_policy_contract/cases/policy_metadata.sh', '../../oos_common/policy_metadata.sh'),
    f'{CAT}/cbrd_26659_show_contract/cases/show_controller.sh': ('../../cbrd_26659_policy_contract/cases/policy_metadata.sh', '../../oos_common/policy_metadata.sh'),
    f'{CAT}/cbrd_26659_policy_contract/cases/policy_controller.sh': ('policy_metadata.sh', '../../oos_common/policy_metadata.sh'),
    f'{CAT}/cbrd_26659_partition_lifecycle_common/controller.sh': ('../../cbrd_26659_policy_contract/cases/policy_metadata.sh', '../../oos_common/policy_metadata.sh'),
}
DDL = "'CREATE TABLE [odd name] ([id] integer DEFAULT 7 NOT NULL, [note] varchar(20) DEFAULT 'x' COMMENT 'column', CONSTRAINT [pk id] PRIMARY KEY ([id])) COMMENT='table' COLLATE utf8_bin'\n"
VALID = ("<1>\nCREATE TABLE: " + DDL).encode()
EXPECTED = (json.dumps(DDL, ensure_ascii=False) + '\n').encode()
FIXTURES = [
    ('complete_ddl', VALID, ['input'], EXPECTED),
    ('report_text', b'CSQL report\n' + VALID + b'1 row selected.\n', ['input'], EXPECTED),
    ('missing', None, ['input'], None),
    ('empty', b'', ['input'], None),
    ('zero_arguments', VALID, [], None),
    ('two_arguments', VALID, ['input', 'input'], None),
    ('error_upper', b'ERROR\n' + VALID, ['input'], None),
    ('error_lower', b'error\n' + VALID, ['input'], None),
    ('fatal_upper', b'FATAL\n' + VALID, ['input'], None),
    ('fatal_mixed', b'FaTaL\n' + VALID, ['input'], None),
    ('zero_rows', b'CREATE TABLE: ' + DDL.encode(), ['input'], None),
    ('two_rows', b'<1>\n<2>\nCREATE TABLE: ' + DDL.encode(), ['input'], None),
    ('zero_fields', b'<1>\nno ddl\n', ['input'], None),
    ('two_fields', VALID + b'CREATE TABLE: ' + DDL.encode(), ['input'], None),
    ('unquoted', b'<1>\nCREATE TABLE: CREATE TABLE [x] ([a] int)\n', ['input'], None),
    ('missing_close_quote', b"<1>\nCREATE TABLE: 'CREATE TABLE [x] ([a] int)\n", ['input'], None),
    ('wrong_prefix', b"<1>\nCREATE TABLE: 'ALTER TABLE [x] ADD [a] int'\n", ['input'], None),
]
SCENARIOS = [
    ('schema_rewrites_sa', 'long_running', f'{CAT}/oos_common/oos08_controller.sh'),
    ('schema_rewrites_cs', 'failing', f'{CAT}/oos_common/oos08_controller.sh'),
    ('partition_partition_rejection', 'failing', f'{CAT}/oos_common/oos08_controller.sh'),
    ('show_contract', 'failing', f'{CAT}/cbrd_26659_show_contract/cases/show_controller.sh'),
    ('policy_contract', 'failing', f'{CAT}/cbrd_26659_policy_contract/cases/policy_controller.sh'),
]

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--regular', required=True, type=Path)
p.add_argument('--ci-source', required=True, type=Path)
p.add_argument('--artifacts', required=True, type=Path)
a = p.parse_args()
repo, ci, artifacts = (x.resolve(strict=True) for x in (a.regular, a.ci_source, a.artifacts))
for source in (repo, ci):
    top = Path(subprocess.check_output(['git', '-C', str(source), 'rev-parse', '--show-toplevel'], text=True).strip()).resolve()
    if artifacts == top or top in artifacts.parents or artifacts in top.parents:
        raise SystemExit(f'artifacts overlap source tree: {top}')
if subprocess.run(['git', '-C', str(artifacts), 'rev-parse', '--is-inside-work-tree'], capture_output=True).returncode == 0:
    raise SystemExit('artifacts must be outside Git trees')
run = Path(tempfile.mkdtemp(prefix='metadata-relocation-', dir=artifacts))

def git(*args):
    return subprocess.check_output(['git', '-C', str(repo), *args])

def blob(path):
    return git('show', f'{BASE}:{path}')

def identity(path):
    return {'sha256': hashlib.sha256(path.read_bytes()).hexdigest(), 'mode': format(path.stat().st_mode & 0o777, '04o'), 'bytes': path.stat().st_size}

def capture(label, command, cwd, env=None):
    result = subprocess.run(command, cwd=cwd, env=env, capture_output=True, timeout=30)
    (label.parent / (label.name + '.stdout')).write_bytes(result.stdout)
    (label.parent / (label.name + '.stderr')).write_bytes(result.stderr)
    record = {'command': list(map(str, command)), 'cwd': str(cwd), 'exit': result.returncode}
    (label.parent / (label.name + '.json')).write_text(json.dumps(record, indent=2) + '\n')
    return result

def inventory(root):
    result = {}
    for path in sorted(root.rglob('*')):
        if path.is_symlink():
            raise RuntimeError(f'symlink forbidden: {path}')
        if path.is_file():
            result[str(path.relative_to(root))] = identity(path)
        elif not path.is_dir():
            raise RuntimeError(f'non-regular file: {path}')
    return result

errors = []
def check(condition, message):
    if not condition:
        errors.append(message)

head = git('rev-parse', 'HEAD').decode().strip()
check(subprocess.run(['git', '-C', str(repo), 'merge-base', '--is-ancestor', BASE, head], capture_output=True).returncode == 0, f'HEAD does not descend from {BASE}: {head}')
status = git('status', '--porcelain=v1', '--untracked-files=all')
(run / 'status.txt').write_bytes(status)
(run / 'dirty.patch').write_bytes(git('diff', '--binary', BASE, '--'))
ci_bytes = subprocess.check_output(['git', '-C', str(ci), 'show', f'{CI_REV}:{CI_PATH}'])
check(hashlib.sha256(ci_bytes).hexdigest() == CI_HASH, 'CI entrypoint hash mismatch')
entrypoint = run / 'docker-entrypoint.sh'
entrypoint.write_bytes(ci_bytes)
baseline = blob(OLD)
check(len(baseline) == 525 and hashlib.sha256(baseline).hexdigest() == HELPER_HASH, 'baseline helper mismatch')
check(git('ls-tree', BASE, '--', OLD).decode().startswith('100644 '), 'baseline helper mode mismatch')
old_exists, new_exists = (repo / OLD).is_file(), (repo / NEW).is_file()
check(old_exists != new_exists, 'expected exactly one helper location')
current = NEW if new_exists else OLD
if (repo / current).is_file():
    check(identity(repo / current) == {'sha256': HELPER_HASH, 'mode': '0644', 'bytes': 525}, 'current helper identity mismatch')
changed = set(git('diff', '--no-renames', '--name-only', BASE, '--').decode().splitlines()) | set(git('ls-files', '--others', '--exclude-standard').decode().splitlines())
ignored = git('ls-files', '--others', '--ignored', '--exclude-standard', '--', CAT).decode().splitlines()
check(not ignored, f'ignored category files are not allowed: {ignored}')
expected_changes = set(CONTROLLERS) | {OLD, NEW} if new_exists else set()
check(changed == expected_changes, f'unexpected changed paths: {sorted(changed ^ expected_changes)}')
for path, (before, after) in CONTROLLERS.items():
    original = blob(path)
    check(original.count(before.encode()) == 1, f'baseline caller count: {path}')
    expected = original.replace(before.encode(), after.encode()) if new_exists else original
    check((repo / path).read_bytes() == expected, f'caller differs from exact replacement: {path}')
    check((repo / path).stat().st_mode & 0o777 == 0o644, f'caller mode differs: {path}')

parser_dir = run / 'parser'
parser_dir.mkdir()
(parser_dir / 'baseline.sh').write_bytes(baseline)
(parser_dir / 'current.sh').write_bytes((repo / current).read_bytes())
parser_records = []
for name, data, arguments, expected in FIXTURES:
    folder = parser_dir / name
    folder.mkdir()
    if data is not None:
        (folder / 'input').write_bytes(data)
    executions = []
    for version in ('baseline', 'current'):
        executions.append(capture(folder / version, ['bash', str(parser_dir / (version + '.sh')), *arguments], folder))
    first, second = executions
    check((first.returncode, first.stdout, first.stderr) == (second.returncode, second.stdout, second.stderr), f'parser mismatch: {name}')
    check((first.returncode != 0) if expected is None else (first.returncode == 0 and first.stdout == expected), f'parser expectation failed: {name}')
    parser_records.append({'name': name, 'input_hex': data.hex() if data is not None else None, 'arguments': arguments, 'expected_stdout': expected.decode() if expected is not None else None, 'expected_accept': expected is not None, 'baseline_exit': first.returncode, 'current_exit': second.returncode})

records = []
for name, bucket, controller in SCENARIOS:
    canonical = f'{CAT}/cbrd_26659_{name}/cases/cbrd_26659_{name}.sh'
    source = f'disabled/{bucket}/{canonical}.disabled'
    owner_source = f'disabled/failing/{OWNER}.disabled'
    for variant in (['owner_control'] if name == 'policy_contract' else ['owner_omitted', 'owner_selected_control']):
        folder = run / f'{name}-{variant}'
        root = folder / 'cubrid-testcases-private-ex'
        folder.mkdir()
        inventory(repo / CAT)
        shutil.copytree(repo / CAT, root / CAT, symlinks=False)
        projections = []
        for src, dst in dict([(source, canonical), (owner_source, OWNER)]).items():
            source_path, target = repo / src, root / dst
            check(not source_path.is_symlink() and source_path.is_file(), f'invalid projection source: {src}')
            check(source_path.read_bytes() == blob(src), f'disabled source changed: {src}')
            check(not target.exists(), f'projection already exists: {dst}')
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source_path, target)
            projections.append({'source': src, 'projected': dst, 'identity': identity(target), 'baseline_sha256': hashlib.sha256(blob(src)).hexdigest()})
        selected = [canonical] + ([OWNER] if variant == 'owner_selected_control' else [])
        selection = folder / 'selection.list'
        selection.write_text(''.join('cubrid-testcases-private-ex/' + item + '\n' for item in selected))
        controller_path = root / controller
        matches = re.findall(r'\bbash\s+([^\s"\']*policy_metadata\.sh)\s+', controller_path.read_text())
        if len(matches) != 1:
            raise RuntimeError(f'expected unique helper argument in {controller}: {matches}')
        cwd = (root / canonical).parent
        helper = (cwd / matches[0]).resolve()
        if root.resolve() not in helper.parents:
            raise RuntimeError(f'helper escapes fixture: {helper}')
        check(helper == (root / current).resolve(), f'controller resolved unexpected helper: {name}')
        (folder / 'input').write_bytes(VALID)
        before_inventory = inventory(root)
        (folder / 'inventory-before.json').write_text(json.dumps(before_inventory, indent=2) + '\n')
        pre = capture(folder / 'parser-before', ['bash', str(helper), str(folder / 'input')], cwd)
        keep = capture(folder / 'keep', ['bash', str(entrypoint), 'keep', 'case', str(root / 'shell'), str(selection)], folder, {**os.environ, 'WORKDIR': str(folder)})
        after_inventory = inventory(root)
        (folder / 'inventory-after.json').write_text(json.dumps(after_inventory, indent=2) + '\n')
        post = capture(folder / 'parser-after', ['bash', str(helper), str(folder / 'input')], cwd)
        check(pre.returncode == 0 and pre.stdout == EXPECTED, f'pre-pruning parser: {name}/{variant}')
        check(keep.returncode == 0, f'keep failed: {name}/{variant}')
        check((root / canonical).is_file() and controller_path.is_file(), f'entry/controller missing: {name}/{variant}')
        check(helper.is_file() and post.returncode == 0 and post.stdout == EXPECTED, f'helper lost after pruning: {name}/{variant}')
        if variant == 'owner_omitted':
            check(not (root / OWNER).exists(), f'owner unexpectedly retained: {name}')
        records.append({'scenario': name, 'variant': variant, 'corpus_root': str(root), 'entry': canonical, 'controller': controller, 'helper_argument': matches[0], 'resolved_helper': str(helper), 'selection': str(selection), 'projections': projections, 'before_inventory': str(folder / 'inventory-before.json'), 'after_inventory': str(folder / 'inventory-after.json'), 'before_exit': pre.returncode, 'keep_exit': keep.returncode, 'after_exit': post.returncode, 'helper_survived': helper.is_file()})

check(git('status', '--porcelain=v1', '--untracked-files=all') == status and git('rev-parse', 'HEAD').decode().strip() == head, 'source changed during proof')
result = {'baseline_revision': BASE, 'baseline_owner_source': f'disabled/failing/{OWNER}.disabled', 'baseline_owner_sha256': hashlib.sha256(blob(f'disabled/failing/{OWNER}.disabled')).hexdigest(), 'baseline_helper': OLD, 'baseline_helper_sha256': HELPER_HASH, 'current_helper': current, 'current_helper_identity': identity(repo / current), 'ci_revision': CI_REV, 'ci_source': CI_PATH, 'ci_sha256': hashlib.sha256(ci_bytes).hexdigest(), 'changed_paths': sorted(changed), 'controller_fingerprints': {path: {'baseline_sha256': hashlib.sha256(blob(path)).hexdigest(), 'current': identity(repo / path)} for path in CONTROLLERS}, 'parser_fixtures': parser_records, 'pruning': records, 'errors': errors, 'limits': ['Generated focused selections are not historical shards.', 'Pruning and synthetic parser observations do not prove native testcase or database success.', 'Scenario reachability is based on source inspection; no testcase or database command was run.']}
output = run / 'result.json'
output.write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps({'result': str(output), 'errors': errors}, indent=2))
raise SystemExit(1 if errors else 0)
