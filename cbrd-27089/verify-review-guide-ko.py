"""Audit the pinned PR7927 guide against fresh AST definitions and every net diff hunk.

Requirements: Python 3.12, tree-sitter==0.25.2, tree-sitter-cpp==0.23.4.
Usage: python verify-review-guide-ko.py ENGINE_WORKTREE --revision ENGINE_SHA [--final]
A --working draft audit reads current files and never claims a commit snapshot.
--render replaces CODE[symbol] draft tokens with exact source links.
"""
import json
from pathlib import Path
import re
import subprocess
import sys

from tree_sitter import Language, Parser
import tree_sitter_cpp

BASE = 'fb567a629cdb390fff920542173fa36f454c74a0'
PARSER = Parser(Language(tree_sitter_cpp.language()))


def walk(node):
    yield node
    for child in node.children:
        yield from walk(child)


def name_of(node):
    while True:
        nested = node.child_by_field_name('declarator')
        if nested:
            node = nested
        elif node.type in ('reference_declarator', 'pointer_declarator') and node.named_children:
            node = node.named_children[-1]
        else:
            break
    return node.text.decode()


def function_name(node, data):
    name = name_of(node.child_by_field_name('declarator'))
    if name in ('TEST', 'TEST_F', 'TEST_P'):
        match = re.search(r'TEST(?:_F|_P)?\s*\(\s*([^,]+),\s*([^\)]+)\)', node.text.decode())
        if match:
            name = match[1].strip() + '.' + match[2].strip()
    name = qualify(node, name)
    if name.endswith('heap_pending_record::heap_pending_record'):
        sig = node.text.decode().split('{', 1)[0]
        name += '(copy deleted)' if '= delete' in sig else '(move)' if '&&' in sig else '(default)'
    return name


def qualify(node, name):
    scopes = []
    parent = node.parent
    while parent:
        if parent.type in ('namespace_definition', 'class_specifier', 'struct_specifier', 'union_specifier'):
            scope = parent.child_by_field_name('name')
            if scope:
                scopes.append(scope.text.decode())
        parent = parent.parent
    return '::'.join(list(reversed(scopes)) + [name])


def symbols(data, path):
    tree = PARSER.parse(data)
    root = tree.root_node
    found = []
    for node in walk(root):
        kind = node.type
        name = None
        if kind == 'function_definition':
            declarator = node.child_by_field_name('declarator')
            if not declarator:
                continue
            name = function_name(node, data)
            body = node.child_by_field_name('body')
            sig = data[node.start_byte:body.start_byte].decode() if body else node.text.decode()
            kind = 'function'
        elif kind in ('class_specifier', 'struct_specifier', 'union_specifier', 'enum_specifier'):
            named = node.child_by_field_name('name')
            if not named or not node.child_by_field_name('body'):
                continue
            name = qualify(node, named.text.decode())
            kind = {'class_specifier': 'class', 'struct_specifier': 'struct',
                    'union_specifier': 'union', 'enum_specifier': 'enum'}[kind]
        elif kind in ('declaration', 'field_declaration'):
            ancestor = node.parent
            local = False
            while ancestor:
                if ancestor.type in ('function_definition', 'lambda_expression', 'friend_declaration'):
                    local = True
                    break
                ancestor = ancestor.parent
            if local:
                continue
            decl = node.child_by_field_name('declarator')
            if not decl or not any(n.type == 'function_declarator' for n in walk(decl)):
                continue
            name = qualify(node, name_of(decl))
            if 'heap_pending_record::heap_pending_record' in name:
                text = node.text.decode()
                name += '(copy deleted)' if '= delete' in text else '(move)' if '&&' in text else '(default)'
            kind = 'declaration'
        elif kind in ('preproc_def', 'preproc_function_def'):
            named = node.child_by_field_name('name')
            if named:
                name = named.text.decode()
                kind = 'macro'
        elif kind == 'lambda_expression':
            # Named local lambdas are separately documented under their enclosing function.
            enclosing = node.parent
            while enclosing and enclosing.type != 'function_definition':
                enclosing = enclosing.parent
            if not enclosing:
                continue
            owner = function_name(enclosing, data)
            owner_lambdas = [n for n in walk(enclosing) if n.type == 'lambda_expression']
            ordinal = next(i for i, n in enumerate(owner_lambdas) if n.start_byte == node.start_byte)
            parent = node.parent
            named = parent.child_by_field_name('declarator') if parent else None
            local = name_of(named) if named else f'lambda#{ordinal + 1}'
            name = owner + '::' + local
            kind = 'lambda'
        if name:
            found.append({'name': name, 'kind': kind, 'path': path, 'start': node.start_point.row + 1,
                          'end': node.end_point.row + 1, 'text': node.text.decode()})
    # Conditional compilation can hide GNU-style .c definitions from a translation-unit parse.
    if path.endswith('.c'):
        text = data.decode()
        present = {s['name'] for s in found if s['kind'] == 'function'}
        for match in re.finditer(r'^([A-Za-z_]\w*) \([^;{}]*?\n\{\n', text, re.M):
            name = match[1]
            if name in present:
                continue
            tail = re.search(r'^\}', text[match.end():], re.M)
            if tail:
                stop = match.end() + tail.end()
                found.append({'name': name, 'kind': 'function', 'path': path,
                              'start': text[:match.start()].count('\n') + 1,
                              'end': text[:stop].count('\n') + 1, 'text': text[match.start():stop],
                              'recovery': 'GNU top-level brace boundary'})
    return found


if __name__ == '__main__':
    import argparse
    import hashlib
    from importlib.metadata import version

    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('engine_worktree', type=Path)
    cli.add_argument('--revision')
    cli.add_argument('--working', action='store_true')
    cli.add_argument('--render', action='store_true')
    cli.add_argument('--final', action='store_true', help='Require finished guide and orchestrator receipt')
    args = cli.parse_args()
    repo = args.engine_worktree.resolve()
    here = Path(__file__).resolve().parent
    guide_path = here / 'review-guide-ko.md'
    guide = guide_path.read_text()

    def git(*arguments):
        return subprocess.check_output(['git', '-C', str(repo), *arguments])

    revision = 'WORKING_TREE_DRAFT' if args.working else git('rev-parse', args.revision or 'HEAD').decode().strip()
    paths = git('diff', '--name-only', BASE, *([] if args.working else [revision])).decode().splitlines()

    def blob(rev, path):
        if rev == 'WORKING_TREE_DRAFT':
            return (repo / path).read_bytes() if (repo / path).is_file() else None
        result = subprocess.run(['git', '-C', str(repo), 'show', f'{rev}:{path}'], capture_output=True)
        return result.stdout if result.returncode == 0 else None

    snapshots = {}
    for rev in (BASE, revision):
        rows = []
        for path in paths:
            if path.endswith(('.c', '.cpp', '.h', '.hpp')):
                data = blob(rev, path)
                if data is not None:
                    rows.extend(symbols(data, path))
        snapshots[rev] = rows
    old = {(row['path'], row['kind'], row['name']): row for row in snapshots[BASE]}
    new = {(row['path'], row['kind'], row['name']): row for row in snapshots[revision]}
    changed = []
    for key in sorted(old.keys() | new.keys()):
        before, after = old.get(key), new.get(key)
        if before and after and before['text'] == after['text']:
            continue
        changed.append({'path': key[0], 'kind': key[1], 'name': key[2],
                        'status': 'added' if not before else 'deleted' if not after else 'modified',
                        'base': before, 'head': after})

    overrides = {
        'build_heap_recdes_with_oos_eager': ('unit_tests/oos/test_oos_eager_diagnostics.cpp', 'build_record_with_stubs'),
        'cubrid_STORAGE_SOURCES': ('cubrid/CMakeLists.txt', r'^set\(STORAGE_SOURCES'),
        'sa_STORAGE_SOURCES': ('sa/CMakeLists.txt', r'^set\(STORAGE_SOURCES'),
        'sql_CMake_deferred': ('unit_tests/oos/sql/CMakeLists.txt', r'^add_test\(NAME test_oos_sql_deferred_write'),
    }
    ref_names = set(re.findall(r'CODE\[([^\]]+)\]', guide))
    # Rendered source refs are stable input to subsequent verifier runs.
    ref_names |= set(re.findall(r'<!-- source-ref:([^ ]+) -->', guide))
    locations = {}
    for name in sorted(ref_names):
        if name in overrides:
            path, selector = overrides[name]
            if selector.startswith('^'):
                data = blob(revision, path)
                match = re.search(selector, data.decode(), re.M)
                assert match, (name, path)
                line = data[:len(data.decode()[:match.start()].encode())].count(b'\n') + 1
                actual_name = name
            else:
                rows = [r for r in snapshots[revision] if r['path'] == path and r['name'] == selector
                        and r['kind'] == 'function']
                assert len(rows) == 1, (name, rows)
                line = rows[0]['start']
                actual_name = selector
        else:
            rows = [r for r in snapshots[revision]
                    if r['name'] == name or r['name'] == name + '(default)']
            rows = [r for r in rows if r['kind'] in ('function', 'class', 'struct', 'enum', 'macro')]
            # Prefer the out-of-line implementation when both declaration and definition exist.
            implementations = [r for r in rows if r['path'].endswith(('.c', '.cpp'))]
            if implementations:
                rows = implementations
            assert len(rows) == 1, (name, [(r['path'], r['start'], r['kind']) for r in rows])
            row = rows[0]
            path, line, actual_name = row['path'], row['start'], row['name']
        data = blob(revision, path)
        locations[name] = {'symbol': actual_name, 'path': path, 'line': line,
                           'line_text': data.decode().splitlines()[line - 1],
                           'file_sha256': hashlib.sha256(data).hexdigest()}
        if args.render:
            label = actual_name.removesuffix('(default)')
            guide = guide.replace(f'CODE[{name}]',
                f'[{label}]({repo / path}:{line}) (`{path}:{line}`) <!-- source-ref:{name} -->')
    if args.render:
        guide_path.write_text(guide)

    published_links = []
    for match in re.finditer(r'https://github.com/([^/]+/[^/]+)/blob/([a-f0-9]{40})/([^)#]+)(?:#L([0-9]+))?', guide):
        remote_repo, sha, path, line = match.groups()
        local_repo = (Path('/home/vimkim/gh/cubrid-oos-context') if remote_repo.endswith('cubrid-oos-context')
                      else here.parent if remote_repo.endswith('my-cubrid-docs')
                      else Path('/home/vimkim/gh/cubrid-manual') if remote_repo == 'CUBRID/cubrid-manual' else repo)
        result = subprocess.run(['git', '-C', str(local_repo), 'show', sha + ':' + path], capture_output=True)
        assert result.returncode == 0, match.group(0)
        lines = result.stdout.decode().splitlines()
        assert not line or int(line) <= len(lines), match.group(0)
        assert sha != revision, 'Final engine revision is unpublished; do not fabricate a published source link'
        published_links.append({'url': match.group(0), 'path': path, 'revision': sha,
                                'line': int(line) if line else None,
                                'line_text': lines[int(line) - 1] if line else None})
    remaining_placeholders = re.findall(r'FINAL_[A-Z_]+_PENDING|CODE\[[^\]]+\]', guide)
    if args.final:
        assert not args.working, 'Final audit needs immutable engine revision'
        assert not remaining_placeholders, remaining_placeholders
        receipt = here / 'review-guide-ko-orchestration.json'
        assert receipt.is_file(), 'Independent orchestrator receipt must be present'
        for location in locations.values():
            assert (repo / location['path']).read_bytes() == blob(revision, location['path']), location['path']

    anchors = re.findall(r'<a id="([^"]+)"></a>', guide)
    assert len(anchors) == len(set(anchors)), 'duplicate explicit anchors'
    fragment_links = re.findall(r'\]\(#([^\)]+)\)', guide)
    missing_anchors = sorted(set(fragment_links) - set(anchors))
    source_links = re.findall(r'\]\((/home/vimkim/gh/cb/[^\)]+):(\d+)\)', guide)
    wrong_source_links = []
    expected_sources = {(str(repo / loc['path']), loc['line']) for loc in locations.values()}
    for path, line in source_links:
        if (path, int(line)) not in expected_sources:
            wrong_source_links.append({'path': path, 'line': int(line)})

    # Name coverage is an inventory check; qualitative semantic coverage is a separate human review.
    missing_symbols = []
    compact_symbols = []
    for row in changed:
        name = row['name']
        check = name.split('::')[-1]
        if name.startswith(('OosSqlDeferredWrite.', 'OosSqlPacking.', 'OosServerTest.')):
            check = name.split('.')[-1]
        if row['kind'] == 'macro' and name.startswith(('_HEAP_', '_TEST_OOS_')):
            continue
        check = re.sub(r'\(default\)|\(move\)|\(copy deleted\)', '', check)
        if row['kind'] == 'lambda':
            owner = name.split('::lambda#')[0]
            check = owner.split('::')[-1] if '::lambda#' in name else name.split('::')[-2]
        if row['kind'] == 'declaration':
            compact_symbols.append(name)
        if not check or check not in guide:
            missing_symbols.append({'name': name, 'kind': row['kind'], 'path': row['path']})

    diff = git('diff', '-U0', BASE, *([] if args.working else [revision])).decode()
    hunks = []
    path = None
    for block in re.split(r'(?m)(?=^@@ )', diff):
        if not block.startswith('@@'):
            found_paths = re.findall(r'^\+\+\+ b/(.*)$', block, re.M)
            if found_paths:
                path = found_paths[-1]
            continue
        header = block.splitlines()[0]
        match = re.match(r'@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@', header)
        assert match and path
        old_start, old_count, start, count = [int(n) if n is not None else 1 for n in match.groups()]
        names = []
        for row in changed:
            if row['path'] != path:
                continue
            for side, span_start, span_count in [('base', old_start, old_count), ('head', start, count)]:
                node = row[side]
                if node and span_count and span_start <= node['end'] and span_start + span_count - 1 >= node['start']:
                    names.append(row['name'])
                    break
        lines = [line[1:] for line in block.splitlines()[1:]
                 if line[:1] in ('+', '-') and not line.startswith(('+++', '---'))]
        category = 'definition/declaration' if names else None
        if category is None:
            if path.endswith('CMakeLists.txt'):
                category = 'build sources/test registration/timeout'
            elif path in ('src/loaddb/load_server_loader.hpp', 'src/storage/heap_oos.hpp',
                          'src/storage/heap_oos_value_ref.hpp', 'src/transaction/locator.h'):
                category = 'documented type wiring/forward declarations/includes'
            elif all(not line.strip() or line.lstrip().startswith(('#include', '/*', '*', '//', '#ifndef', '#define', '#endif', '#ifdef', 'class '))
                     for line in lines):
                category = 'includes/header guard/format wrappers/whitespace'
            else:
                category = 'UNCLASSIFIED'
        hunks.append({'path': path, 'hunk': header, 'symbols': sorted(set(names)), 'category': category})
        found_paths = re.findall(r'^\+\+\+ b/(.*)$', block, re.M)
        if found_paths:
            path = found_paths[-1]
    unclassified = [row for row in hunks if row['category'] == 'UNCLASSIFIED']
    deferred = [r for r in snapshots[revision]
                if r['path'].endswith('test_oos_sql_deferred_write.cpp') and r['name'].startswith('OosSqlDeferredWrite.')]
    output = {
        'base': BASE, 'engine': revision, 'engine_worktree': str(repo),
        'guide_sha256': hashlib.sha256(guide.encode()).hexdigest(),
        'final_audit': args.final, 'remaining_placeholders': remaining_placeholders,
        'published_source_links': published_links,
        'parser_versions': {name: version(name) for name in ('tree-sitter', 'tree-sitter-cpp')},
        'changed_files': [p for p in paths if p != 'cubrid-cci'],
        'unrelated_submodule_diff_excluded': [p for p in paths if p == 'cubrid-cci'],
        'source_reference_count': len(locations), 'source_references': locations,
        'explicit_anchor_count': len(anchors), 'fragment_link_count': len(fragment_links),
        'missing_fragment_anchors': missing_anchors, 'wrong_source_links': wrong_source_links,
        'changed_symbol_count': len(changed), 'missing_symbol_names': missing_symbols,
        'mechanical_declarations_also_inventoried': sorted(set(compact_symbols)),
        'changed_symbols': [{k: v for k, v in r.items() if k not in ('base', 'head')} |
                            {'base_line': r['base']['start'] if r['base'] else None,
                             'final_line': r['head']['start'] if r['head'] else None} for r in changed],
        'hunk_count': len(hunks), 'unclassified_hunks': unclassified, 'hunks': hunks,
        'deferred_TEST_F_count': len(deferred),
        'qualification': 'Name/span/anchor/link audit; semantic explanations independently reviewed by orchestrator. ' +
                         ('Final audit verifies immutable source bytes and requires the independent receipt.' if args.final
                          else 'Draft audit is not the completed deliverable gate.')
    }
    (here / 'review-guide-ko-coverage.json').write_text(json.dumps(output, ensure_ascii=False, indent=2) + '\n')
    summary = {k: v for k, v in output.items() if k not in ('source_references', 'changed_symbols', 'hunks',
               'mechanical_declarations_also_inventoried', 'changed_files', 'published_source_links')}
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    if missing_symbols or missing_anchors or wrong_source_links or unclassified:
        sys.exit(1)
