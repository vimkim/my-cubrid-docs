"""Retain bounded signatures and exact source object comparisons; no acquisition."""
import hashlib
import json
import re
import subprocess
from pathlib import Path

HERE = Path(__file__).parent
data = json.loads((HERE / 'ci-validation.json').read_text())
cases = json.loads((HERE / 'case-comparison.json').read_text())
sources = json.loads((HERE / 'testcase-sources.json').read_text())
source_checks = []
for name in sorted(cases['head']['cases']):
    h = cases['head']['cases'][name]
    b = cases['baseline']['cases'][name]
    repo = '/home/vimkim/gh/cubrid-testcases-private-ex/develop' if h['suite'] == 'test_shell' else '/home/vimkim/gh/cubrid-testcases/develop'
    scope = str(Path(name).parent.parent) if h['suite'] == 'test_shell' else name
    objects = []
    for side, item in [('head', h), ('baseline', b)]:
        listing = subprocess.check_output(['git', '-C', repo, 'ls-tree', '-r', item['testcase_sha'], '--', scope], text=True).splitlines()
        if h['suite'] == 'test_medium':
            answer = name.replace('/cases/', '/answers/').replace('.sql', '.answer')
            listing += subprocess.check_output(['git', '-C', repo, 'ls-tree', '-r', item['testcase_sha'], '--', answer], text=True).splitlines()
        objects.append(listing)
    source_checks.append(dict(name=name, repository=repo, head_testcase_sha=h['testcase_sha'], baseline_testcase_sha=b['testcase_sha'], compared_scope=scope, affected_objects_equal=objects[0] == objects[1], objects=objects[0]))

signatures = []
(HERE / 'excerpts').mkdir(exist_ok=True)
for side, bundle in data.items():
    for f in bundle['failures']:
        root = Path(f['evidence_dir'])
        message = (root / f['message_path']).read_text()
        lines = message.splitlines()
        diff = (root / f['diff_path']).read_text() if f.get('diff_path') else None
        index = set()
        if f['suite'] == 'test_medium':
            index.update(range(len(lines)))
        elif '27064' in f['name']:
            index.update(range(min(26, len(lines))))
            index.update(i for i, l in enumerate(lines) if re.fullmatch(r'\+ extractor_rc=\d+', l))
        elif '27075' in f['name']:
            index.update(range(min(13, len(lines))))
        elif 'partition_tbls' in f['name']:
            index.update(i for i, l in enumerate(lines) if re.search(r'Appropriate partition|Total [0-9]+ object|partition_tbls-[0-9]|instances committed', l))
        elif '26280' in f['name']:
            index.update(range(min(26, len(lines))))
            index.update(i for i, l in enumerate(lines) if re.search(r'^\+ test7_exit_code=|^\+ test7_status=|^Total 0 object|^Line 3:', l))
        elif '15489' in f['name']:
            for i, l in enumerate(lines):
                if re.search(r'^\+ total_pages=|^Total Pages:|^\+ internal_err=|^\+ sleep 60|^\+ \[.*100 -lt 100', l):
                    index.update(range(max(0, i - 1), min(len(lines), i + 3)))
        elif '15156' in f['name']:
            index.update(range(min(5, len(lines))))
            index.update(range(340, min(358, len(lines))))
        else:
            marker = next((i for i, l in enumerate(lines) if 'CONSOLE OUTPUT' in l), len(lines))
            index.update(range(marker))
        # Retain diagnostic lines, never setup/environment/credential values.
        blocked = re.compile(r'EnvIdentify|Hostname:|PASSWORD|TOKEN|SECRET|Authorization|(?:PATH|CLASSPATH|LD_LIBRARY_PATH)=', re.I)
        excerpt = '\n'.join(f'{i + 1}: {lines[i]}' for i in sorted(index) if i < len(lines) and not blocked.search(lines[i])) + '\n'
        stem = side + '-' + f['stable_id']
        (HERE / 'excerpts' / (stem + '-message.txt')).write_text(excerpt)
        if diff is not None:
            (HERE / 'excerpts' / (stem + '-diff.txt')).write_text(diff)
        signatures.append(dict(side=side, suite=f['suite'], name=f['name'], stable_id=f['stable_id'], message_path=str(root / f['message_path']), message_sha256=hashlib.sha256(message.encode()).hexdigest(), message_lines=len(lines), excerpt='excerpts/' + stem + '-message.txt', diff='excerpts/' + stem + '-diff.txt' if diff is not None else None))

inventory = []
for f in data['head']['failures']:
    name = f['name']
    if '27064' in name or '27075' in name:
        classification, relation, confidence, category = 'also_observed_on_base', 'unlikely', 'high prior-signature / medium mechanism', 'CDC extraction/history gap'
    elif 'partition_tbls' in name:
        classification, relation, confidence, category = 'additional_on_head', 'direct', 'high', 'Partition-domain validation / legacy expectation conflict'
    elif '26280' in name:
        classification, relation, confidence, category = 'uncomparable', 'plausible', 'high observation / low cause', 'Missing loader parser diagnostic'
    elif '15489' in name:
        classification, relation, confidence, category = 'uncomparable', 'unknown', 'high observation / low cause', 'Post-delete index capacity threshold'
    else:
        classification, relation, confidence, category = 'uncomparable', 'unknown', 'high order-only observation / low cause', 'Unordered presentation difference'
    inventory.append(dict(suite=f['suite'], name=name, result=f['result'], stable_id=f['stable_id'], classification=classification, pr_relation=relation, confidence=confidence, category=category, baseline_case=cases['baseline']['cases'][name]))
base_only = [f for f in data['baseline']['failures'] if cases['head']['cases'][f['name']]['result'] == 'pass']
assert len(inventory) == 8 and len(base_only) == 3
assert len({x['name'] for x in inventory}) == len(inventory)
assert all(s['affected_objects_equal'] for s in source_checks)
counts = {k: sum(x['classification'] == k for x in inventory) for k in ['also_observed_on_base', 'additional_on_head', 'uncomparable']}
assert counts == {'also_observed_on_base': 2, 'additional_on_head': 1, 'uncomparable': 5}
result = dict(head=inventory, base_only=[dict(name=f['name'], result=f['result'], stable_id=f['stable_id'], head_result='pass', causal_comparability='unverified CTP/runtime inputs') for f in base_only], classification_counts=counts, source_object_equality=source_checks, signatures=signatures, ctp_local_object_check=dict(repository='/home/vimkim/gh/ctp/run-sql', head_object='missing', baseline_object='missing', affected_tool_file_equality='unknown'))
(HERE / 'failure-comparison.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(dict(head_failures=len(inventory), base_only=len(base_only), classification_counts=counts, testcase_sources_read=len(sources), equality_cases=len(source_checks)), indent=2))
