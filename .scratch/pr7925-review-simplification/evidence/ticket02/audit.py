#!/usr/bin/env python3
"""Count actual GoogleTest XML case outcomes; retain case identities."""
import json
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

root = Path(sys.argv[1])
files = []
for path in sorted(root.glob('*.xml')):
    tree = ET.parse(path).getroot()
    cases = []
    for case in tree.iter('testcase'):
        cases.append({'suite': case.get('classname'), 'name': case.get('name'),
                      'status': case.get('status'), 'result': case.get('result'),
                      'seconds': float(case.get('time', '0')),
                      'failure': case.find('failure') is not None,
                      'skipped': case.find('skipped') is not None})
    files.append({'file': str(path), 'declared_tests': int(tree.get('tests', '0')),
                  'declared_disabled': int(tree.get('disabled', '0')), 'cases': cases})
all_cases = [case for file in files for case in file['cases']]
summary = {'xml_files': len(files), 'cases': len(all_cases),
           'run': sum(case['status'] == 'run' for case in all_cases),
           'failures': sum(case['failure'] for case in all_cases),
           'skipped': sum(case['skipped'] for case in all_cases),
           'disabled': sum(file['declared_disabled'] for file in files)}
out = {'summary': summary, 'files': files}
Path(sys.argv[2]).write_text(json.dumps(out, indent=2) + '\n')
print(json.dumps(summary))
