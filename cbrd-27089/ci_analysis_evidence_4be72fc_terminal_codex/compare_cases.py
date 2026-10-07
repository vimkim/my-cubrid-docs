"""Compare exact case coverage and runner/build inputs in validated local JUnit."""
from pathlib import Path
import hashlib
import json
import re
import xml.etree.ElementTree as ET

HERE = Path(__file__).parent
data = json.loads((HERE / 'ci-validation.json').read_text())
names = {f['name'] for bundle in data.values() for f in bundle['failures']}
result = {}
for side, bundle in data.items():
    found, provenance = {}, {}
    for suite, entry in bundle['summaries'].items():
        summary_path = Path(entry['summary_path'])
        summary = json.loads(summary_path.read_text())
        raw = summary_path.parent / 'raw'
        indexed = {f['path'] for f in json.loads((raw / 'index.json').read_text())['files']}
        for shard in summary['shards']:
            for filename in shard['junit_files']:
                relative = f"shards/{shard['index']}/{filename}"
                assert relative in indexed
                for testcase in ET.parse(raw / relative).iter('testcase'):
                    name = testcase.attrib.get('name', '')
                    if name not in names:
                        continue
                    assert name not in found, name
                    outcome = next((tag for tag in ('failure', 'error', 'skipped') if testcase.find(tag) is not None), 'pass')
                    found[name] = dict(suite=suite, result=outcome, shard=shard['index'], testcase_sha=shard['testcases']['sha'], raw_junit=str(raw / relative), duration=testcase.attrib.get('time'))
        log = (raw / 'github/collect.log').read_text()
        provenance[suite] = dict(ctp_shas=sorted(set(re.findall(r'\bCTP_SHA: ([0-9a-f]{40})', log))), ctp_branches=sorted(set(re.findall(r'\bCTP_BRANCH: ([^\s]+)', log))), conf_label={'test_medium': 'conf/medium_dev.conf', 'test_sql': 'conf/sql.conf', 'test_shell': 'conf/shell_ci.conf'}[suite], builds=list({json.dumps(s['build'], sort_keys=True): s['build'] for s in summary['shards']}.values()), testcases=list({json.dumps(s['testcases'], sort_keys=True): s['testcases'] for s in summary['shards']}.values()), plan_sha256=hashlib.sha256((raw / 'plan/plan.tsv').read_bytes()).hexdigest())
    assert set(found) == names, sorted(names - set(found))
    result[side] = dict(cases=found, provenance=provenance)
(HERE / 'case-comparison.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps({k: dict(cases=len(v['cases']), ctp_shas=v['provenance']['test_shell']['ctp_shas']) for k, v in result.items()}, indent=2))
