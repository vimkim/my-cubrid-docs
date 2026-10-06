"""Inventory changed C++ definitions, declarations, types, macros and lambdas."""
import json
from pathlib import Path
import re
import subprocess
import sys

from tree_sitter import Language, Parser
import tree_sitter_cpp

BASE = 'fb567a629cdb390fff920542173fa36f454c74a0'
HEAD = 'aecce0e1216a813771621c13112c8f27d43df22e'
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
    repo = Path(sys.argv[1])
    def git(*args):
        return subprocess.check_output(['git', '-C', str(repo), *args])
    paths = git('diff', '--name-only', BASE, HEAD).decode().splitlines()
    revisions = {}
    for rev in (BASE, HEAD):
        rows = []
        for path in paths:
            if not path.endswith(('.c', '.cpp', '.h', '.hpp')):
                continue
            result = subprocess.run(['git', '-C', str(repo), 'show', rev + ':' + path], capture_output=True)
            if result.returncode == 0:
                rows.extend(symbols(result.stdout, path))
        revisions[rev] = rows
    old = {(s['path'], s['kind'], s['name']): s for s in revisions[BASE]}
    new = {(s['path'], s['kind'], s['name']): s for s in revisions[HEAD]}
    changed = []
    for key in sorted(old.keys() | new.keys()):
        a, b = old.get(key), new.get(key)
        if a and b and a['text'] == b['text']:
            continue
        changed.append({'path': key[0], 'kind': key[1], 'name': key[2],
                        'status': 'added' if not a else 'deleted' if not b else 'modified', 'base': a, 'head': b})
    output = {'base': BASE, 'head': HEAD, 'symbols': changed}
    (Path(__file__).parent / 'symbols.json').write_text(json.dumps(output, indent=2) + '\n')
    for s in changed:
        print(s['status'], s['kind'], s['path'], s['name'], s['head']['start'] if s['head'] else '-')
    print('TOTAL', len(changed))
