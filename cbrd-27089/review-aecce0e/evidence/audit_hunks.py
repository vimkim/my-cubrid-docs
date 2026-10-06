"""Independently map every net-diff hunk to an explained symbol or wiring."""
import json
from pathlib import Path
import re
import subprocess
import sys

HERE = Path(__file__).parent
inventory = json.loads((HERE / 'symbols.json').read_text())
symbols = inventory['symbols']
repo = sys.argv[1]
diff = subprocess.check_output(['git', '-C', repo, 'diff', '-U0', inventory['base'], inventory['head']]).decode()
rows = []
path = None
blocks = re.split(r'(?m)(?=^@@ )', diff)
for block in blocks:
    if not block.startswith('@@'):
        paths = re.findall(r'^\+\+\+ b/(.*)$', block, re.M)
        if paths:
            path = paths[-1]
        continue
    header = block.splitlines()[0]
    match = re.match(r'@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@', header)
    assert match and path
    a, ac, b, bc = [int(v) if v is not None else 1 for v in match.groups()]
    matches = []
    for symbol in symbols:
        if symbol['path'] != path:
            continue
        for side, start, count in [('base', a, ac), ('head', b, bc)]:
            node = symbol[side]
            if node and count and start <= node['end'] and start + count - 1 >= node['start']:
                matches.append(symbol['name'])
                break
    changed = [line[1:] for line in block.splitlines()[1:]
               if line[:1] in ('+', '-') and not line.startswith(('+++', '---'))]
    category = 'explained definition/declaration' if matches else None
    if not category:
        if path.endswith('CMakeLists.txt'):
            category = 'build source list or test timeout'
        elif all(not line.strip() or line.lstrip().startswith(('#include', '/*', '*', '//', 'class ', 'extern '))
                 for line in changed):
            category = 'includes, forward declaration, formatting wrapper or whitespace'
        else:
            category = 'REQUIRES_REVIEW'
    rows.append({'path': path, 'hunk': header, 'symbols': sorted(set(matches)), 'category': category})
    paths = re.findall(r'^\+\+\+ b/(.*)$', block, re.M)
    if paths:
        path = paths[-1]
unknown = [r for r in rows if r['category'] == 'REQUIRES_REVIEW']
assert not unknown, unknown
output = {'base': inventory['base'], 'head': inventory['head'], 'hunk_count': len(rows),
          'definition_or_declaration_hunks': sum(bool(r['symbols']) for r in rows),
          'other_classified_hunks': sum(not r['symbols'] for r in rows), 'unclassified_hunks': [], 'hunks': rows}
(HERE / 'hunk-coverage.json').write_text(json.dumps(output, indent=2) + '\n')
print(json.dumps({k: v for k, v in output.items() if k != 'hunks'}, indent=2))
