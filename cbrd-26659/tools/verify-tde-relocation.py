#!/usr/bin/env python3
"""Verify the TDE helper contract and real CI case pruning in disposable copies."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import tempfile
import traceback

BASES = {'regular': '41eae6a9c30f98434521c44476aa27e768e3332b', 'heavy': '81e60724a30431282c08ae1f677bf8cefb3d95d7'}
CI_REV = '155c265eb6e3deef49ce828e6f2b5846d3a9abf5'
CI_PATH = 'docker/ci/docker-entrypoint.sh'
CI_HASH = '55965b9c36c67c4f4330b7954202ea292eb617b9139f9bfa46a6f27d283557d2'
STATE = {'table_name': 'dba.audit_fixture', 'class_oid': [1, 2, 3], 'heap_header_page_id': 5, 'heap_volume_id': 1, 'heap_file_id': 10, 'oos_volume_id': 1, 'oos_file_id': 20}
IDENTITY = dict(STATE)
SCOPE = 'product prior-node flag diagnostic; no ciphertext inspection'
PARAMS = {'tde_keys_file_path': ['/tmp/keys with spaces', '/tmp/keys with spaces'], 'tde_default_algorithm': ['AES'], 'er_log_tde': ['Y'], 'enable_string_compression': ['n']}
PARAM_TEXT = 'tde_keys_file_path = "/tmp/keys with spaces"\ntde_keys_file_path = "/tmp/keys with spaces"\ntde_default_algorithm = AES\ner_log_tde = Y\nenable_string_compression = n\n'

def headers(algorithm):
    return (f'file header:\nvfid = 1|10\ntde_algorithm: {algorithm}\ntime_creation = 1, type = HEAP\nCLASS_OID: 1|2|3 (dba.audit_fixture)\n'
            f'file header:\nvfid = 1|20\ntde_algorithm: {algorithm}\ntime_creation = 1, type = OUT_OF_LINE_OVERFLOW_STORAGE\nCLASS_OID: 1|2|3 (dba.audit_fixture)\nOOS for HFID: 5|1|10\n')

def owned(algorithm):
    return {'file_headers': 2, 'heap': {'vfid': [1, 10], 'algorithm': algorithm, 'kind': 'HEAP', 'class_oid': [1, 2, 3], 'table': 'dba.audit_fixture'}, 'oos': {'vfid': [1, 20], 'algorithm': algorithm, 'kind': 'OUT_OF_LINE_OVERFLOW_STORAGE', 'class_oid': [1, 2, 3], 'table': 'dba.audit_fixture', 'hfid': [5, 1, 10]}}

def ident(path):
    b = path.read_bytes()
    return {'sha256': hashlib.sha256(b).hexdigest(), 'mode': format(stat.S_IMODE(path.stat().st_mode), '04o'), 'bytes': len(b)}

def inventory(root):
    result = {}
    for path in sorted(root.rglob('*')):
        if path.is_symlink() or not (path.is_file() or path.is_dir()):
            raise RuntimeError(f'unsupported corpus file: {path}')
        if path.is_file():
            result[str(path.relative_to(root))] = ident(path)
    return result

def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')

class Proof:
    def __init__(self, run):
        self.run = run
        self.result = {'run_root': str(run), 'errors': [], 'checks': [], 'observations': [], 'sources': {}, 'parser_fixtures': [], 'pruning': [], 'native_execution': 'not_run', 'native_candidate': None, 'verifier_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
        self.counter = 0

    def check(self, ok, message):
        self.result['checks'].append({'check': message, 'passed': bool(ok)})
        if not ok:
            self.result['errors'].append(message)

    def capture(self, label, argv, cwd, env=None):
        self.counter += 1
        folder = self.run / 'commands'
        folder.mkdir(exist_ok=True)
        prefix = folder / f'{self.counter:04d}-{label}'
        try:
            proc = subprocess.run([str(x) for x in argv], cwd=cwd, env=env, capture_output=True, timeout=60)
            code, out, err = proc.returncode, proc.stdout, proc.stderr
        except subprocess.TimeoutExpired as exc:
            code, out, err = None, exc.stdout or b'', (exc.stderr or b'') + b'\nTIMEOUT\n'
        except OSError as exc:
            code, out, err = None, b'', str(exc).encode()
        prefix.with_suffix('.stdout').write_bytes(out)
        prefix.with_suffix('.stderr').write_bytes(err)
        record = {'label': label, 'argv': list(map(str, argv)), 'cwd': str(cwd), 'exit': code, 'stdout': str(prefix.with_suffix('.stdout')), 'stderr': str(prefix.with_suffix('.stderr'))}
        write_json(prefix.with_suffix('.json'), record)
        self.result['observations'].append(record)
        return code, out, err

    def git(self, repo, *args, required=True):
        code, out, err = self.capture('git', ['git', '-C', repo, *args], self.run)
        if required and code != 0:
            raise RuntimeError(f'git {args} failed: {err.decode(errors="replace")}')
        return code, out

    def blob(self, suite, path):
        return self.git(suite['repo'], 'show', f"{suite['base']}:{path}")[1]

    def baseline_mode(self, suite, path):
        raw = self.git(suite['repo'], 'ls-tree', suite['base'], '--', path)[1]
        return int(raw.split()[0], 8) & 0o777

    def compare_path(self, suite, path, replacement=None):
        source = suite['repo'] / path
        original = self.blob(suite, path)
        expected = original
        if replacement and suite['moved']:
            old, new, count = replacement
            self.check(original.count(old) == count, f"{suite['name']} baseline replacement count {path}")
            expected = original.replace(old, new)
        self.check(source.is_file() and not source.is_symlink() and source.read_bytes() == expected, f"{suite['name']} bytes {path}")
        self.check(source.is_file() and stat.S_IMODE(source.stat().st_mode) == self.baseline_mode(suite, path), f"{suite['name']} mode {path}")


def fixtures():
    data = json.dumps(STATE) + '\n'
    rows = []
    def add(name, command, files, arguments, expected):
        rows.append((name, command, files, arguments, expected))
    add('identity-ok', 'identity', {'before': data, 'after': data}, ['before', 'after'], IDENTITY)
    for key in STATE:
        changed = dict(STATE); changed[key] = 'wrong'
        missing = dict(STATE); del missing[key]
        add('identity-wrong-' + key, 'identity', {'before': data, 'after': json.dumps(changed)}, ['before', 'after'], None)
        add('identity-missing-' + key, 'identity', {'before': json.dumps(missing), 'after': data}, ['before', 'after'], None)
    for side in ('before', 'after'):
        files = {'before': data, 'after': data}; files[side] += data
        add('identity-multiple-' + side, 'identity', files, ['before', 'after'], None)
    marker = lambda index: f'TDE: prior_set_tde_encrypted(): rcvindex = {index}\n'
    for index, count, minimum in [('RVOOS_INSERT', 2, 2), ('RVOOS_DELETE', 3, 2)]:
        add('wal-' + index, 'wal', {'diag': marker(index) * count}, ['diag', index, str(minimum)], {'recovery_index': index, 'encrypted_flag_events': count, 'minimum': minimum, 'scope': SCOPE})
    for name, diag, index, minimum in [('empty', '', 'RVOOS_INSERT', '1'), ('error', 'ERROR\n', 'RVOOS_INSERT', '1'), ('fatal', 'FATAL\n', 'RVOOS_INSERT', '1'), ('unknown', 'UNKNOWN-CLASS\n', 'RVOOS_INSERT', '1'), ('index', marker('RVOOS_INSERT'), 'BAD', '1'), ('minimum-zero', marker('RVOOS_INSERT'), 'RVOOS_INSERT', '0'), ('minimum-leading-zero', marker('RVOOS_INSERT'), 'RVOOS_INSERT', '01'), ('minimum-missing', marker('RVOOS_INSERT'), 'RVOOS_INSERT', ''), ('insufficient', marker('RVOOS_INSERT'), 'RVOOS_INSERT', '2')]:
        add('wal-invalid-' + name, 'wal', {'diag': diag}, ['diag', index, minimum], None)
    add('parameters-ok', 'parameters', {'diag': PARAM_TEXT}, ['diag', '/tmp/keys with spaces'], PARAMS)
    for name, text in [('missing', PARAM_TEXT.replace('er_log_tde = Y\n', '')), ('wrong', PARAM_TEXT + 'er_log_tde = n\n'), ('error', PARAM_TEXT + 'ERROR\n')]:
        add('parameters-invalid-' + name, 'parameters', {'diag': text}, ['diag', '/tmp/keys with spaces'], None)
    for algorithm in ('NONE', 'AES'):
        add('owned-' + algorithm, 'owned', {'diag': headers(algorithm), 'state': data}, ['diag', 'state', algorithm], owned(algorithm))
    for key in STATE:
        changed = dict(STATE); changed[key] = 'wrong'
        add('owned-wrong-' + key, 'owned', {'diag': headers('AES'), 'state': json.dumps(changed)}, ['diag', 'state', 'AES'], None)
    h = headers('AES')
    invalid = {'algorithm': h.replace('tde_algorithm: AES', 'tde_algorithm: NONE', 1), 'duplicate-vfid': h.replace('vfid = 1|20', 'vfid = 1|10'), 'missing-heap': h[h.index('file header:', 1):], 'missing-oos': h[:h.index('file header:', 1)], 'duplicate-header-field': h.replace('vfid = 1|10', 'vfid = 1|10\nvfid = 1|10'), 'missing-header-field': h.replace('tde_algorithm: AES\n', '', 1), 'malformed-vfid': h.replace('vfid = 1|10', 'vfid = bad'), 'wrong-hfid': h.replace('5|1|10', '6|1|10'), 'wrong-class': h.replace('1|2|3', '1|2|4', 1), 'wrong-table': h.replace('dba.audit_fixture', 'dba.other', 1)}
    for name, text in invalid.items():
        add('owned-invalid-' + name, 'owned', {'diag': text, 'state': data}, ['diag', 'state', 'AES'], None)
    add('owned-multiple-json', 'owned', {'diag': h, 'state': data + data}, ['diag', 'state', 'AES'], None)
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for option in ('regular', 'heavy', 'ci-source', 'artifacts'):
        parser.add_argument('--' + option, required=True, type=Path)
    args = parser.parse_args()
    artifacts = args.artifacts.resolve(strict=True)
    paths = [args.regular.resolve(strict=True), args.heavy.resolve(strict=True), args.ci_source.resolve(strict=True)]
    if any(artifacts == p or p in artifacts.parents or artifacts in p.parents for p in paths):
        raise SystemExit('artifact path overlaps a source')
    if subprocess.run(['git', '-C', str(artifacts), 'rev-parse', '--is-inside-work-tree'], capture_output=True).returncode == 0:
        raise SystemExit('artifact path is inside a Git worktree')
    run = Path(tempfile.mkdtemp(prefix='tde-relocation-', dir=artifacts)).resolve()
    proof = Proof(run)
    result = proof.result
    suites = []
    try:
        for name, repo in zip(('regular', 'heavy'), paths):
            cat = ('shell' if name == 'regular' else 'shell_heavy') + '/_40_guava'
            suite = {'name': name, 'repo': repo, 'base': BASES[name], 'cat': cat, 'old': cat + '/cbrd_26659_tde_wal/cases', 'new': cat + '/oos_common'}
            suites.append(suite)
            head = proof.git(repo, 'rev-parse', 'HEAD')[1].decode().strip()
            status = proof.git(repo, 'status', '--porcelain=v1', '--untracked-files=all')[1]
            (run / (name + '-status-before.txt')).write_bytes(status)
            (run / (name + '-diff.patch')).write_bytes(proof.git(repo, 'diff', '--binary', suite['base'], '--')[1])
            proof.check(proof.git(repo, 'merge-base', '--is-ancestor', suite['base'], head, required=False)[0] == 0, f'{name} baseline ancestor')
            ignored = proof.git(repo, 'ls-files', '--others', '--ignored', '--exclude-standard', '--', cat)[1].decode().splitlines()
            proof.check(not ignored, f'{name} no ignored category files: {ignored}')
            suite.update(head=head, status=status)
            oldhelper, newhelper = (repo / suite['old'] / 'tde_observe.sh'), (repo / suite['new'] / 'tde_observe.sh')
            oldawk, newawk = (repo / suite['old'] / 'tde_headers.awk'), (repo / suite['new'] / 'tde_headers.awk')
            valid_old = oldhelper.is_file() and oldawk.is_file() and not newhelper.exists() and not newawk.exists()
            valid_new = newhelper.is_file() and newawk.is_file() and not oldhelper.exists() and not oldawk.exists()
            proof.check(valid_old or valid_new, f'{name} exactly one complete helper layout')
            suite['moved'] = valid_new
            suite['helper'] = newhelper if valid_new else oldhelper
            suite['awk'] = newawk if valid_new else oldawk
            original = proof.blob(suite, suite['old'] + '/tde_observe.sh')
            oldline, newline = b'. "$here/../../oos_common/oos_json.sh"', b'. "$here/oos_json.sh"'
            proof.check(original.count(oldline) == 1, f'{name} baseline helper source count')
            expected = original.replace(oldline, newline) if valid_new else original
            proof.check(suite['helper'].is_file() and suite['helper'].read_bytes() == expected, f'{name} exact helper bytes')
            for filename, live, baseline in [('helper', suite['helper'], suite['old'] + '/tde_observe.sh'), ('awk', suite['awk'], suite['old'] + '/tde_headers.awk'), ('json', repo / suite['new'] / 'oos_json.sh', suite['new'] + '/oos_json.sh')]:
                proof.check(live.is_file() and stat.S_IMODE(live.stat().st_mode) == proof.baseline_mode(suite, baseline), f'{name} {filename} mode')
                if filename != 'helper':
                    proof.check(live.is_file() and live.read_bytes() == proof.blob(suite, baseline), f'{name} {filename} baseline bytes')
            all_base = proof.git(repo, 'ls-tree', '-r', '--name-only', suite['base'])[1].decode().splitlines()
            all_current = proof.git(repo, 'ls-files', '--cached', '--others', '--exclude-standard')[1].decode().splitlines()
            def is_entry(path):
                parts = path.split('/')
                return (cat + '/cbrd_26659_' in path and len(parts) >= 5 and
                        parts[-2] == 'cases' and parts[-1] in (parts[-3] + '.sh', parts[-3] + '.sh.disabled'))
            baseline_entries = sorted(path for path in all_base if is_entry(path))
            current_entries = sorted(path for path in set(all_current) if is_entry(path) and (repo / path).is_file())
            write_json(run / (name + '-activation.json'), {'baseline': baseline_entries, 'current': current_entries})
            proof.check(baseline_entries == current_entries, f'{name} testcase activation paths unchanged')
            active = [path for path in current_entries if path.startswith(cat + '/')]
            proof.check(len(active) == (31 if name == 'regular' else 38), f'{name} active testcase count unchanged')
            for entry in baseline_entries:
                case = entry.split('/')[-3]
                if case in ('cbrd_26659_crash_committed', 'cbrd_26659_crash_undo', 'cbrd_26659_tde_crash_committed', 'cbrd_26659_tde_crash_undo'):
                    proof.compare_path(suite, entry)
            crash = suite['new'] + '/oos_crash.sh'
            proof.compare_path(suite, crash, (b'$here/../cbrd_26659_tde_wal/cases/tde_observe.sh', b'$here/tde_observe.sh', 2))
            wal = cat + '/cbrd_26659_tde_wal/cases/cbrd_26659_tde_wal.sh'
            wal_source = ('disabled/heavy/' + wal + '.disabled') if name == 'regular' else wal
            proof.compare_path(suite, wal_source, (b'bash tde_observe.sh ', b'bash ../../oos_common/tde_observe.sh ', 5))
            if name == 'regular':
                storage = 'disabled/failing/' + cat + '/cbrd_26659_tde_storage/cases/cbrd_26659_tde_storage.sh.disabled'
                proof.compare_path(suite, storage, (b'../../cbrd_26659_tde_wal/cases/tde_observe.sh', b'../../oos_common/tde_observe.sh', 1))
            else:
                proof.check(not proof.git(repo, 'diff', '--name-only', suite['base'], '--', 'shell', cat + '/oos_common/pr8128-transfer.tsv')[1], 'heavy historical shell and transfer manifest unchanged')
            changed = set(proof.git(repo, 'diff', '--no-renames', '--name-only', suite['base'], '--')[1].decode().splitlines())
            changed.update(proof.git(repo, 'ls-files', '--others', '--exclude-standard')[1].decode().splitlines())
            scope = {path for path in changed if path.startswith(suite['old'] + '/')}
            allowed = {suite['old'] + '/tde_observe.sh', suite['old'] + '/tde_headers.awk'}
            if name == 'heavy': allowed.add(wal_source)
            proof.check(not (scope - allowed), f'{name} no unexpected changes in WAL case directory: {sorted(scope - allowed)}')
            result['sources'][name] = {'repo': str(repo), 'baseline': suite['base'], 'head': head, 'status_before': str(run / (name + '-status-before.txt')), 'diff': str(run / (name + '-diff.patch')), 'layout': 'moved' if valid_new else 'old', 'helper': str(suite['helper']), 'helper_identity': ident(suite['helper'])}
            suite['wal'] = wal
        for filename in ('tde_headers.awk', 'oos_json.sh'):
            p1 = suites[0]['awk'] if filename.startswith('tde_') else suites[0]['repo'] / suites[0]['new'] / filename
            p2 = suites[1]['awk'] if filename.startswith('tde_') else suites[1]['repo'] / suites[1]['new'] / filename
            proof.check(ident(p1) == ident(p2), f'cross-suite {filename} identity')
        proof.check(suites[0]['moved'] == suites[1]['moved'], 'cross-suite layout matches')
        proof.check(ident(suites[0]['helper']) == ident(suites[1]['helper']), 'cross-suite helper identity')
        ci = proof.git(paths[2], 'show', f'{CI_REV}:{CI_PATH}')[1]
        proof.check(hashlib.sha256(ci).hexdigest() == CI_HASH, 'pinned CI entrypoint hash')
        entrypoint = run / 'docker-entrypoint.sh'; entrypoint.write_bytes(ci)
        result['ci'] = {'repo': str(paths[2]), 'revision': CI_REV, 'path': CI_PATH, 'sha256': hashlib.sha256(ci).hexdigest()}

        for suite in suites:
            name, repo, cat = suite['name'], suite['repo'], suite['cat']
            tree = run / 'parser' / name
            for variant in ('baseline', 'current'):
                root = tree / variant
                olddir = root / suite['old']; newdir = root / suite['new']
                olddir.mkdir(parents=True); newdir.mkdir(parents=True)
                if variant == 'baseline':
                    for file in ('tde_observe.sh', 'tde_headers.awk'):
                        (olddir / file).write_bytes(proof.blob(suite, suite['old'] + '/' + file))
                    (newdir / 'oos_json.sh').write_bytes(proof.blob(suite, suite['new'] + '/oos_json.sh'))
                else:
                    target = newdir if suite['moved'] else olddir
                    shutil.copy2(suite['helper'], target / 'tde_observe.sh')
                    shutil.copy2(suite['awk'], target / 'tde_headers.awk')
                    shutil.copy2(repo / suite['new'] / 'oos_json.sh', newdir / 'oos_json.sh')
            for fname, command, files, arguments, expected in fixtures():
                folder = tree / 'inputs' / fname; folder.mkdir(parents=True)
                for key, value in files.items(): (folder / key).write_text(value)
                argv = [str(folder / x) if x in files else x for x in arguments]
                runs = []
                for variant in ('baseline', 'current'):
                    helperdir = suite['old'] if variant == 'baseline' or not suite['moved'] else suite['new']
                    helper = tree / variant / helperdir / 'tde_observe.sh'
                    runs.append(proof.capture(name + '-' + fname + '-' + variant, ['bash', helper, command, *argv], folder))
                (c1, o1, e1), (c2, o2, e2) = runs
                normalize = lambda b: b.replace(str(tree / 'baseline' / suite['old']).encode(), b'<helper>').replace(str(tree / 'current' / (suite['new'] if suite['moved'] else suite['old'])).encode(), b'<helper>')
                proof.check((c1, o1, normalize(e1)) == (c2, o2, normalize(e2)), f'{name} parser equivalence {fname}')
                try: accepted = c1 == c2 == 0 and json.loads(o1) == json.loads(o2) == expected
                except (ValueError, UnicodeError): accepted = False
                proof.check((c1 not in (0, None) and c2 not in (0, None)) if expected is None else accepted, f'{name} parser independent expectation {fname}')
                result['parser_fixtures'].append({'suite': name, 'name': fname, 'expected': expected, 'baseline_exit': c1, 'current_exit': c2, 'input_dir': str(folder)})
            for missing in ('tde_headers.awk', 'oos_json.sh'):
                source = tree / 'current'; dest = tree / ('fault-' + missing)
                shutil.copytree(source, dest)
                helperdir = suite['new'] if suite['moved'] else suite['old']
                (dest / (helperdir if missing.startswith('tde_') else suite['new']) / missing).unlink()
                folder = tree / 'inputs' / 'owned-AES'
                code, _, _ = proof.capture(name + '-fault-' + missing, ['bash', dest / helperdir / 'tde_observe.sh', 'owned', folder / 'diag', folder / 'state', 'AES'], folder)
                proof.check(code not in (0, None), f'{name} missing {missing} rejected')

        for suite in suites:
            name, repo, cat = suite['name'], suite['repo'], suite['cat']
            cases = ['tde_storage', 'crash_committed', 'crash_undo', 'tde_crash_committed', 'tde_crash_undo', 'tde_wal'] if name == 'regular' else ['crash_committed', 'crash_undo', 'tde_wal']
            snapshot = run / 'snapshot' / name / 'cubrid-testcases-private-ex' / cat
            source_inventory = inventory(repo / cat)
            write_json(run / 'snapshot' / (name + '-source-inventory.json'), source_inventory)
            snapshot.parent.mkdir(parents=True)
            shutil.copytree(repo / cat, snapshot)
            for case in cases:
                canonical = f'{cat}/cbrd_26659_{case}/cases/cbrd_26659_{case}.sh'
                bucket = 'failing' if case.startswith('tde_') and case != 'tde_wal' else 'heavy'
                source = f'disabled/{bucket}/{canonical}.disabled' if name == 'regular' else canonical
                sibling = case.removeprefix('tde_') if case.startswith('tde_crash_') else None
                variants = ['owner_control'] if case == 'tde_wal' else ['owner_omitted', 'owner_selected_control']
                if sibling: variants.append('wrapper_only_negative')
                for variant in variants:
                    folder = run / 'pruning' / name / case / variant
                    root = folder / 'cubrid-testcases-private-ex'
                    root.joinpath(cat).parent.mkdir(parents=True)
                    shutil.copytree(snapshot, root / cat)
                    projections = [(source, canonical)]
                    wal_source = f"disabled/heavy/{suite['wal']}.disabled" if name == 'regular' else suite['wal']
                    projections.append((wal_source, suite['wal']))
                    sibling_entry = None
                    if sibling:
                        sibling_entry = f'{cat}/cbrd_26659_{sibling}/cases/cbrd_26659_{sibling}.sh'
                        projections.append((f'disabled/heavy/{sibling_entry}.disabled', sibling_entry))
                    projection_records = []
                    for src, dst in dict(projections).items():
                        source_path, target = repo / src, root / dst
                        if src != dst:
                            proof.check(not target.exists(), f'{name} projection absent {case} {dst}')
                            target.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(source_path, target)
                        proof.check(target.is_file() and ident(target) == ident(source_path), f'{name} projection identity {case} {dst}')
                        if src != dst and src != wal_source and case != 'tde_storage':
                            proof.compare_path(suite, src)
                        projection_records.append({'source': str(source_path), 'destination': dst, 'identity': ident(target), 'baseline_sha256': hashlib.sha256(proof.blob(suite, src)).hexdigest()})
                    selected = [canonical]
                    if variant == 'owner_selected_control': selected.append(suite['wal'])
                    if sibling and variant != 'wrapper_only_negative': selected.append(sibling_entry)
                    selection = folder / 'selection.list'
                    selection.write_text(''.join('cubrid-testcases-private-ex/' + x + '\n' for x in dict.fromkeys(selected)))
                    controller = root / (suite['new'] + '/oos_crash.sh' if 'crash' in case else canonical)
                    text = controller.read_text()
                    if 'crash' in case:
                        matches = re.findall(r'bash\s+"\$here/([^"\n]*tde_observe\.sh)"\s+owned', text)
                        proof.check(len(matches) == 2 and len(set(matches)) == 1, f'{name} controller helper sites {case}')
                        helper = (controller.parent / matches[0]).resolve()
                        argument = '$here/' + matches[0]
                    else:
                        matches = re.findall(r'bash\s+([^\s]*tde_observe\.sh)\s+', text)
                        proof.check(bool(matches) and len(set(matches)) == 1, f'{name} caller helper sites {case}')
                        argument = matches[0]
                        helper = (root / canonical).parent.joinpath(argument).resolve()
                    expected_helper = root / (suite['new'] if suite['moved'] else suite['old']) / 'tde_observe.sh'
                    proof.check(helper == expected_helper.resolve(), f'{name} resolved helper {case}')
                    required = [helper, helper.parent / 'tde_headers.awk', root / suite['new'] / 'oos_json.sh', controller, root / canonical]
                    inputs = folder / 'inputs'; inputs.mkdir()
                    (inputs / 'diag').write_text(headers('AES')); (inputs / 'state').write_text(json.dumps(STATE) + '\n')
                    command = ['bash', helper, 'owned', inputs / 'diag', inputs / 'state', 'AES']
                    before = inventory(root); write_json(folder / 'inventory-before.json', before)
                    pre = proof.capture(name + '-' + case + '-' + variant + '-pre', command, (root / canonical).parent)
                    keep = proof.capture(name + '-' + case + '-' + variant + '-keep', ['bash', entrypoint, 'keep', 'case', root / cat.split('/')[0], selection], folder, {**os.environ, 'WORKDIR': str(folder)})
                    after = inventory(root); write_json(folder / 'inventory-after.json', after)
                    post = proof.capture(name + '-' + case + '-' + variant + '-post', command, (root / canonical).parent)
                    try: preok = pre[0] == 0 and json.loads(pre[1]) == owned('AES')
                    except ValueError: preok = False
                    try: postok = post[0] == 0 and json.loads(post[1]) == owned('AES')
                    except ValueError: postok = False
                    proof.check(preok, f'{name} {case} {variant} pre-pruning AES probe')
                    proof.check(keep[0] == 0, f'{name} {case} {variant} real keep case')
                    if variant != 'wrapper_only_negative':
                        proof.check(postok, f'{name} {case} {variant} post-pruning AES probe')
                        for path in required:
                            rel = str(path.relative_to(root))
                            proof.check(rel in before and after.get(rel) == before[rel], f'{name} {case} {variant} retained {rel}')
                        if variant == 'owner_omitted': proof.check(not (root / suite['wal']).exists(), f'{name} {case} owner omitted')
                        if sibling: proof.check((root / sibling_entry).is_file(), f'{name} {case} selected sibling retained')
                    else:
                        proof.check(not (root / sibling_entry).exists(), f'{name} {case} wrapper-only loses sibling')
                    record = {'suite': name, 'case': case, 'variant': variant, 'corpus_root': str(root), 'selection': str(selection), 'selected': list(dict.fromkeys(selected)), 'projections': projection_records, 'controller': str(controller), 'helper_argument': argument, 'resolved_helper': str(helper), 'inventory_before': str(folder / 'inventory-before.json'), 'inventory_after': str(folder / 'inventory-after.json'), 'pre_exit': pre[0], 'keep_exit': keep[0], 'post_exit': post[0], 'helper_survived': helper.is_file(), 'sibling_survived': (root / sibling_entry).is_file() if sibling else None}
                    result['pruning'].append(record)
                    if name == 'heavy' and case == 'crash_committed' and variant == 'owner_omitted': result['native_candidate'] = record
            after_source = inventory(repo / cat)
            write_json(run / 'snapshot' / (name + '-source-inventory-after.json'), after_source)
            proof.check(source_inventory == after_source, f'{name} category unchanged during proof')
            proof.check(proof.git(repo, 'status', '--porcelain=v1', '--untracked-files=all')[1] == suite['status'], f'{name} status unchanged during proof')
            proof.check(proof.git(repo, 'rev-parse', 'HEAD')[1].decode().strip() == suite['head'], f'{name} HEAD unchanged during proof')
    except Exception:
        result['errors'].append('blocked by exception; see exception.txt')
        (run / 'exception.txt').write_text(traceback.format_exc())
    finally:
        result['limits'] = ['Pruning uses generated selections, not historical shards.', 'Wrapper sibling coupling remains a separate dependency.', 'No native testcase, database, CI, or publication was run.']
        result['passed'] = not result['errors']
        write_json(run / 'result.json', result)
        print(json.dumps({'result': str(run / 'result.json'), 'passed': result['passed'], 'errors': result['errors'], 'native_candidate': result['native_candidate']}, indent=2))
    return 0 if result['passed'] else 1

if __name__ == '__main__':
    raise SystemExit(main())
