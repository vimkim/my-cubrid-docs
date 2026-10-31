#!/usr/bin/env python3
"""Replay case pruning in isolated fixtures and verify the helper relocation."""
import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import tarfile
import tempfile

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--regular', type=Path, required=True)
p.add_argument('--heavy', type=Path, required=True)
p.add_argument('--artifacts', type=Path, required=True)
a = p.parse_args()
repos = [a.regular.resolve(strict=True), a.heavy.resolve(strict=True)]
artifacts = a.artifacts.resolve(strict=True)
assert all(artifacts != r and r not in artifacts.parents and artifacts not in r.parents for r in repos)
assert subprocess.run(['git', '-C', str(artifacts), 'rev-parse', '--is-inside-work-tree'], capture_output=True).returncode != 0
proof = artifacts / 'proof-work'
proof.mkdir(exist_ok=True)
work = Path(tempfile.mkdtemp(prefix='relocation-', dir=proof)).resolve()
prior = Path('/home/vimkim/temp/cbrd-26659-policy39-20261030/namespaced-ci-probe')
entrypoint, share = prior / 'docker-entrypoint-155c265.sh', prior / '13.list'
digest = lambda b: hashlib.sha256(b).hexdigest()
assert digest(entrypoint.read_bytes()) == '55965b9c36c67c4f4330b7954202ea292eb617b9139f9bfa46a6f27d283557d2'
assert digest(share.read_bytes()) == '91ced695f3703410067a2a9bb89bb7475bd389c5bb2436e25dde8c922ff825be'
lines = share.read_text().splitlines()
assert len(lines) == 72 and all(x.startswith('cubrid-testcases-private-ex/shell/') for x in lines)
assert not any('/cbrd_26659_schema_policy/cases/' in x for x in lines)
configs = [
    ('regular', repos[0], 'shell', 'a229e1978abc4cc6c280783703c03f75524c0f05', 'cbrd_26659_gap_ctas_cs', 'cbrd_26659_gap_ctas_cs.sh'),
    ('heavy', repos[1], 'shell_heavy', '631e3fd3cbc202cec45b56ae6cec7e4f1c86e2f1', 'cbrd_26659_gap_recreate', 'cbrd_26659_gap_recreate.sh'),
]
def git(repo, *args):
    return subprocess.check_output(['git', '-C', str(repo), *args])
def inv(root):
    result = {}
    for path in sorted(root.rglob('*')):
        assert not path.is_symlink(), f'symlink in fixture: {path}'
        if path.is_file():
            result[str(path.relative_to(root))] = {'sha256': digest(path.read_bytes()), 'mode': stat.S_IMODE(path.stat().st_mode)}
    return result

def baseline_file(repo, rev, path):
    return git(repo, 'show', f'{rev}:{path}')

def fixture(name, repo, suite, rev, case, filename, baseline):
    label = 'baseline' if baseline else 'current'
    folder = work / f'{name}-{label}'
    root = folder / 'cubrid-testcases-private-ex'
    base = f'{suite}/_40_guava'
    casepath = f'{base}/{case}/cases/{filename}'
    old = f'{base}/cbrd_26659_schema_policy/cases/policy_ddl.sh'
    roots = [f'{base}/{x}' for x in ('oos_coverage_gaps', 'oos_utility', 'oos_common', 'oos_native')]
    roots += [f'{base}/{case}']
    if baseline:
        archive_roots = [x for x in roots if subprocess.run(['git', '-C', str(repo), 'cat-file', '-e', f'{rev}:{x}'], capture_output=True).returncode == 0]
        data = git(repo, 'archive', rev, *archive_roots, old)
        with tarfile.open(fileobj=io.BytesIO(data)) as tar:
            for member in tar.getmembers():
                assert member.isfile() or member.isdir(), f'non-regular archive member: {member.name}'
            tar.extractall(root, filter='data')
    else:
        for item in roots:
            src, dst = repo / item, root / item
            if src.exists():
                assert not src.is_symlink() and not any(x.is_symlink() for x in src.rglob('*'))
                shutil.copytree(src, dst)
        src = repo / old
        if src.exists():
            assert not src.is_symlink()
            (root / old).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, root / old)
    if name == 'regular':
        disabled = f'disabled/failing/{casepath}.disabled'
        source = baseline_file(repo, rev, disabled) if baseline else (repo / disabled).read_bytes()
        dest = root / casepath
        assert not dest.exists(), f'representative unexpectedly exists: {dest}'
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(source)
        dest.chmod(0o644)
    assert (root / casepath).is_file()
    controller = (root / base / 'oos_coverage_gaps/controller.sh').read_text()
    paths = re.findall(r'bash\s+(\S*policy_ddl\.sh)', controller)
    assert len(paths) == 1, paths
    helper = ((root / casepath).parent / paths[0]).resolve()
    assert root in helper.parents
    before = inv(root)
    present_before = helper.is_file()
    selection = folder / 'selection.list'
    if name == 'regular':
        selection.write_bytes(share.read_bytes())
        assert 'cubrid-testcases-private-ex/' + casepath in lines
        selection_kind = 'original historical shard 13 (72 entries)'
    else:
        selection.write_text('cubrid-testcases-private-ex/' + casepath + '\n')
        selection_kind = 'generated focused selection'
    run = subprocess.run(['bash', str(entrypoint), 'keep', 'case', str(root / suite), str(selection)], env={**os.environ, 'WORKDIR': str(folder)}, capture_output=True, text=True)
    assert run.returncode == 0, (run.returncode, run.stdout, run.stderr)
    assert (root / casepath).is_file() and (root / base / 'oos_coverage_gaps/controller.sh').is_file()
    after = inv(root)
    return {'suite': name, 'variant': label, 'selection': selection_kind, 'fixture_root': str(root), 'case': casepath, 'controller_helper_argument': paths[0], 'resolved_helper': str(helper), 'helper_before': present_before, 'helper_after': helper.is_file(), 'old_helper_after': (root / old).is_file(), 'keep_exit': run.returncode, 'keep_stdout': run.stdout, 'keep_stderr': run.stderr, 'pre_inventory': before, 'post_inventory': after}

records = []
for config in configs:
    for baseline in (True, False):
        records.append(fixture(*config, baseline))
result = {'entrypoint_sha256': digest(entrypoint.read_bytes()), 'regular_selection_sha256': digest(share.read_bytes()), 'records': records, 'limits': 'Filesystem availability only; historical image identity, all historical failure causes, native verdict and engine fix are not established.'}
output = work / 'result.json'
output.write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(result, indent=2), flush=True)
for record in records:
    if record['variant'] == 'baseline':
        assert record['helper_before'] and not record['helper_after'] and not record['old_helper_after'], record
    else:
        assert record['helper_before'], f"{record['suite']} current controller helper missing before keep: {record['resolved_helper']}"
        assert record['helper_after'], f"{record['suite']} current controller helper missing after keep: {record['resolved_helper']}"

helper_hash = '99bb263ae729f3f02745f88601b86653813d136476af007c2417fae6aedd024c'
regular_callers = ['cbrd_26659_partition_lifecycle_common/controller.sh', 'cbrd_26659_partition_lifecycle_common/lifecycle.sh', 'cbrd_26659_policy_contract/cases/policy_controller.sh', 'cbrd_26659_schema_policy/cases/cbrd_26659_schema_policy.sh', 'oos_common/oos08_controller.sh', 'oos_coverage_gaps/controller.sh', 'oos_utility/policy_roundtrip.sh']
for name, repo, suite, rev, case, filename in configs:
    base = f'{suite}/_40_guava/'
    old = base + 'cbrd_26659_schema_policy/cases/policy_ddl.sh'
    new = base + 'oos_common/policy_ddl.sh'
    callers = [base + x for x in (regular_callers if name == 'regular' else ['oos_coverage_gaps/controller.sh'])]
    assert not (repo / old).exists()
    assert digest((repo / new).read_bytes()) == helper_hash
    assert stat.S_IMODE((repo / new).stat().st_mode) == 0o644
    for path in callers:
        original = baseline_file(repo, rev, path)
        if path.endswith('cbrd_26659_schema_policy.sh'):
            before, after = b'bash policy_ddl.sh', b'bash ../../oos_common/policy_ddl.sh'
        elif path.endswith('policy_roundtrip.sh'):
            before, after = b'$here/../cbrd_26659_schema_policy/cases/policy_ddl.sh', b'$here/../oos_common/policy_ddl.sh'
        else:
            before, after = b'../../cbrd_26659_schema_policy/cases/policy_ddl.sh', b'../../oos_common/policy_ddl.sh'
        assert original.count(before) == 1 and (repo / path).read_bytes() == original.replace(before, after), path
        assert stat.S_IMODE((repo / path).stat().st_mode) == 0o644, path
    paths = [suite] + (['disabled'] if name == 'regular' else [])
    changed = set(git(repo, 'diff', '--no-renames', '--name-only', rev, '--', *paths).decode().splitlines())
    untracked = set(git(repo, 'ls-files', '--others', '--exclude-standard', '--', *paths).decode().splitlines())
    allowed = set(callers + [old, new])
    if name == 'heavy':
        allowed.add(base + 'oos_common/README.md')
        readme = base + 'oos_common/README.md'
        assert (repo / readme).read_bytes().startswith(baseline_file(repo, rev, readme))
    assert changed | untracked == allowed, {'suite': name, 'changed': sorted(changed | untracked), 'expected': sorted(allowed)}
    if name == 'heavy':
        tsv = base + 'oos_common/pr8128-transfer.tsv'
        assert (repo / tsv).read_bytes() == baseline_file(repo, rev, tsv)
result['structural_checks'] = 'passed'
output.write_text(json.dumps(result, indent=2) + '\n')
print(f'Structural checks passed; result: {output}')
