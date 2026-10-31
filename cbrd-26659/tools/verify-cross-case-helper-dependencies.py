#!/usr/bin/env python3
"""Check helper availability with real case pruning in isolated Git fixtures."""
import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import tarfile
import tempfile

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--regular', type=Path, required=True)
parser.add_argument('--heavy', type=Path, required=True)
parser.add_argument('--ci-source', type=Path, required=True)
parser.add_argument('--artifacts', type=Path, required=True)
args = parser.parse_args()
artifacts = args.artifacts.resolve(strict=True)
repositories = {'regular': args.regular.resolve(strict=True), 'heavy': args.heavy.resolve(strict=True)}
ci_source = args.ci_source.resolve(strict=True)
assert subprocess.run(['git', '-C', str(artifacts), 'rev-parse', '--is-inside-work-tree'], capture_output=True).returncode != 0
assert all(artifacts != repo and repo not in artifacts.parents and artifacts not in repo.parents for repo in [*repositories.values(), ci_source])
revisions = {'regular': '6334dc6cd74683ca6ba10439372a21bd36b453d3', 'heavy': '81e60724a30431282c08ae1f677bf8cefb3d95d7'}
suites = {'regular': 'shell', 'heavy': 'shell_heavy'}
source_revision = '155c265eb6e3deef49ce828e6f2b5846d3a9abf5'
source_path = 'docker/ci/docker-entrypoint.sh'
entrypoint_bytes = subprocess.check_output(['git', '-C', str(ci_source), 'show', f'{source_revision}:{source_path}'])
entrypoint_hash = hashlib.sha256(entrypoint_bytes).hexdigest()
assert entrypoint_hash == '55965b9c36c67c4f4330b7954202ea292eb617b9139f9bfa46a6f27d283557d2'
proof = artifacts / 'pruning-proof'
proof.mkdir(exist_ok=True)
run_root = Path(tempfile.mkdtemp(prefix='audit-', dir=proof)).resolve()
entrypoint = run_root / 'docker-entrypoint.sh'
entrypoint.write_bytes(entrypoint_bytes)
snapshots = {}
baseline_status = {}
for name, repo in repositories.items():
    baseline_status[name] = subprocess.check_output(['git', '-C', str(repo), 'status', '--porcelain=v1'])
    assert not baseline_status[name]
    assert subprocess.check_output(['git', '-C', str(repo), 'rev-parse', 'HEAD']).decode().strip() == revisions[name]
    snapshots[name] = subprocess.check_output(['git', '-C', str(repo), 'archive', revisions[name], suites[name] + '/_40_guava'])
scenarios = [
    ('schema_rewrites_sa', 'regular', 'disabled/long_running', 'metadata', 'SA schema', None),
    ('schema_rewrites_cs', 'regular', 'disabled/failing', 'metadata', 'CS schema', None),
    ('partition_partition_rejection', 'regular', 'disabled/failing', 'metadata', 'partition_rejection', None),
    ('show_contract', 'regular', 'disabled/failing', 'metadata', 'SHOW snapshots', None),
    ('tde_storage', 'regular', 'disabled/failing', 'tde', 'owned', None),
    ('crash_committed', 'regular', 'disabled/heavy', 'tde', 'AES only; default NONE', None),
    ('crash_undo', 'regular', 'disabled/heavy', 'tde', 'AES only; default NONE', None),
    ('tde_crash_committed', 'regular', 'disabled/failing', 'tde', 'AES wrapper', 'crash_committed'),
    ('tde_crash_undo', 'regular', 'disabled/failing', 'tde', 'AES wrapper', 'crash_undo'),
    ('crash_committed', 'heavy', 'active', 'tde', 'AES only; default NONE', None),
    ('crash_undo', 'heavy', 'active', 'tde', 'AES only; default NONE', None),
    ('policy_contract', 'regular', 'disabled/failing', 'metadata', 'direct owner control', None),
    ('tde_wal', 'heavy', 'active', 'tde', 'direct owner control', None),
]
records = []
for case, name, state, family, condition, sibling in scenarios:
    repo, revision, suite = repositories[name], revisions[name], suites[name]
    category = f'{suite}/_40_guava'
    canonical = f'{category}/cbrd_26659_{case}/cases/cbrd_26659_{case}.sh'
    original = canonical if state == 'active' else f'{state}/{canonical}.disabled'
    owner = 'policy_contract' if family == 'metadata' else 'tde_wal'
    owner_entry = f'{category}/cbrd_26659_{owner}/cases/cbrd_26659_{owner}.sh'
    owner_source = owner_entry if name == 'heavy' else f"disabled/{'failing' if family == 'metadata' else 'heavy'}/{owner_entry}.disabled"
    helper = f"{category}/cbrd_26659_{owner}/cases/{'policy_metadata.sh' if family == 'metadata' else 'tde_observe.sh'}"
    required = [helper] if family == 'metadata' else [helper, f'{category}/cbrd_26659_tde_wal/cases/tde_headers.awk', f'{category}/oos_common/oos_json.sh']
    variants = ['owner_selected_control'] if case == owner else ['owner_omitted', 'owner_selected_control']
    for variant in variants:
        folder = run_root / f'{name}-{case}-{variant}'
        root = folder / 'cubrid-testcases-private-ex'
        with tarfile.open(fileobj=io.BytesIO(snapshots[name])) as archive:
            assert all(member.isfile() or member.isdir() for member in archive.getmembers())
            archive.extractall(root, filter='data')
        projections = [(original, canonical), (owner_source, owner_entry)]
        if sibling:
            sibling_entry = f'{category}/cbrd_26659_{sibling}/cases/cbrd_26659_{sibling}.sh'
            projections.append((f'disabled/heavy/{sibling_entry}.disabled', sibling_entry))
        projection_records = []
        for source, destination in dict(projections).items():
            content = subprocess.check_output(['git', '-C', str(repo), 'show', f'{revision}:{source}'])
            mode = subprocess.check_output(['git', '-C', str(repo), 'ls-tree', revision, '--', source]).decode().split()[0]
            target = root / destination
            if source != destination:
                assert not target.exists(), destination
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(content)
                target.chmod(int(mode, 8) & 0o777)
            assert target.read_bytes() == content and target.stat().st_mode & 0o777 == int(mode, 8) & 0o777
            projection_records.append({'source': source, 'projected': destination, 'sha256': hashlib.sha256(content).hexdigest(), 'mode': mode})
        selected = [canonical]
        if variant == 'owner_selected_control':
            selected.append(owner_entry)
            if sibling:
                selected.append(sibling_entry)
        selection = folder / 'selection.list'
        selection.write_text(''.join('cubrid-testcases-private-ex/' + path + '\n' for path in dict.fromkeys(selected)))
        inputs = folder / 'inputs'
        inputs.mkdir()
        if family == 'metadata':
            (inputs / 'ddl.log').write_text("<1>\nCREATE TABLE: 'CREATE TABLE [audit_fixture] ([id] integer)'\n")
            command = ['bash', str(root / helper), str(inputs / 'ddl.log')]
        else:
            (inputs / 'headers.log').write_text('file header:\nvfid = 1|10\ntde_algorithm: AES\ntime_creation = 1, type = HEAP\nCLASS_OID: 1|2|3 (dba.audit_fixture)\nfile header:\nvfid = 1|20\ntde_algorithm: AES\ntime_creation = 1, type = OUT_OF_LINE_OVERFLOW_STORAGE\nCLASS_OID: 1|2|3 (dba.audit_fixture)\nOOS for HFID: 5|1|10\n')
            (inputs / 'state.json').write_text(json.dumps({'table_name': 'dba.audit_fixture', 'class_oid': [1, 2, 3], 'heap_header_page_id': 5, 'heap_volume_id': 1, 'heap_file_id': 10, 'oos_volume_id': 1, 'oos_file_id': 20}) + '\n')
            command = ['bash', str(root / helper), 'owned', str(inputs / 'headers.log'), str(inputs / 'state.json'), 'AES']
        before = {path: (root / path).is_file() for path in required}
        assert all(before.values())
        original_probe = subprocess.run(command, cwd=(root / canonical).parent, capture_output=True, text=True, timeout=10)
        assert original_probe.returncode == 0, original_probe.stderr
        execution = subprocess.run(['bash', str(entrypoint), 'keep', 'case', str(root / suite), str(selection)], env={**os.environ, 'WORKDIR': str(folder)}, capture_output=True, text=True, timeout=20)
        (folder / 'keep.stdout').write_text(execution.stdout)
        (folder / 'keep.stderr').write_text(execution.stderr)
        assert execution.returncode == 0, execution.stderr
        after = {path: (root / path).is_file() for path in required}
        retained = variant == 'owner_selected_control'
        assert (root / canonical).is_file()
        assert after[helper] == retained
        if family == 'tde':
            assert after[required[1]] == retained and after[required[2]]
        parser_probe = subprocess.run(command, cwd=(root / canonical).parent, capture_output=True, text=True, timeout=10)
        (folder / 'parser.stdout').write_text(parser_probe.stdout)
        (folder / 'parser.stderr').write_text(parser_probe.stderr)
        assert parser_probe.returncode == (0 if retained else 127), (case, parser_probe.returncode, parser_probe.stderr)
        for item in projection_records:
            target = root / item['projected']
            if item['projected'] == canonical or retained:
                assert target.is_file() and hashlib.sha256(target.read_bytes()).hexdigest() == item['sha256']
        record = {'repository': name, 'revision': revision, 'case': canonical, 'source_state': state, 'condition_from_source': condition, 'helper_family': family, 'variant': variant, 'fixture': str(folder), 'selection_kind': 'generated focused selection, not a historical shard list', 'selected_entries': list(dict.fromkeys(selected)), 'projections': projection_records, 'required_before': before, 'required_after': after, 'keep_exit': execution.returncode, 'synthetic_parser_before_exit': original_probe.returncode, 'synthetic_parser_after_exit': parser_probe.returncode}
        if sibling:
            record['sibling_entry_before'] = True
            record['sibling_entry_after'] = (root / sibling_entry).is_file()
            assert record['sibling_entry_after'] == retained
        records.append(record)
faults = []
owner_record = next(record for record in records if record['repository'] == 'heavy' and record['case'].endswith('/cbrd_26659_tde_wal.sh'))
owner_fixture = Path(owner_record['fixture'])
for relative in ['shell_heavy/_40_guava/cbrd_26659_tde_wal/cases/tde_headers.awk', 'shell_heavy/_40_guava/oos_common/oos_json.sh']:
    folder = run_root / ('missing-' + Path(relative).name)
    shutil.copytree(owner_fixture / 'cubrid-testcases-private-ex', folder / 'cubrid-testcases-private-ex')
    (folder / 'cubrid-testcases-private-ex' / relative).unlink()
    helper = folder / 'cubrid-testcases-private-ex/shell_heavy/_40_guava/cbrd_26659_tde_wal/cases/tde_observe.sh'
    execution = subprocess.run(['bash', str(helper), 'owned', str(owner_fixture / 'inputs/headers.log'), str(owner_fixture / 'inputs/state.json'), 'AES'], capture_output=True, text=True, timeout=10)
    assert execution.returncode != 0, relative
    (folder / 'parser.stdout').write_text(execution.stdout)
    (folder / 'parser.stderr').write_text(execution.stderr)
    faults.append({'removed_from_fixture': relative, 'fixture': str(folder), 'synthetic_parser_exit': execution.returncode})
for name, repo in repositories.items():
    assert subprocess.check_output(['git', '-C', str(repo), 'status', '--porcelain=v1']) == baseline_status[name]
    assert subprocess.check_output(['git', '-C', str(repo), 'rev-parse', 'HEAD']).decode().strip() == revisions[name]
result = {'entrypoint_source_revision': source_revision, 'entrypoint_sha256': entrypoint_hash, 'run_root': str(run_root), 'records': records, 'transitive_dependency_faults': faults, 'case_pruning_executions': len(records), 'owner_omitted_helper_losses': sum(record['variant'] == 'owner_omitted' for record in records), 'selected_owner_controls': sum(record['variant'] == 'owner_selected_control' for record in records), 'repository_status_unchanged': True, 'limits': ['Only isolated fixture case pruning and parsers on synthetic diagnostics were executed.', 'No testcase, database, daemon, native runner, CI trigger, or TC publication was executed.', 'Scenario reachability comes from revision-pinned source inspection, not live scenario execution.', 'The heavy pruning fixtures are structural probes, not evidence that QA currently shards shell_heavy.', 'Generated selections do not attest to any historical worker image, shard, or failure cause.']}
output = run_root / 'result.json'
output.write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps({'result': str(output), 'case_pruning_executions': len(records), 'owner_omitted_helper_losses': result['owner_omitted_helper_losses'], 'selected_owner_controls': result['selected_owner_controls'], 'transitive_dependency_faults': faults, 'repository_status_unchanged': True}, indent=2))
