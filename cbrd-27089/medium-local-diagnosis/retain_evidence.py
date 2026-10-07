#!/usr/bin/env python3
"""Audit all expected artifacts, including native NOK runs, and retain evidence."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import xml.etree.ElementTree as ET

from detect_order import classify


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def counts(text):
    return {key: int(re.search(r'(?m)^' + key + r':(\d+)', text).group(1))
            for key in ['total', 'success', 'fail']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('attempt_root', type=Path)
    parser.add_argument('destination', type=Path)
    args = parser.parse_args()
    root, dest = args.attempt_root.resolve(), args.destination.resolve()
    dest.mkdir(exist_ok=True)
    records, verdict_rows, probes = [], [], {}
    answers = Path('/home/vimkim/gh/cubrid-testcases/tc-pr-7927/medium/_02_xtests/answers')
    for attempt in sorted(root.iterdir()):
        if not attempt.is_dir() or not (attempt / 'preflight.txt').exists():
            continue
        row = {'name': attempt.name, 'path': str(attempt)}
        identity = attempt / 'identity.json'
        row['identity'] = json.loads(identity.read_text()) if identity.exists() else None
        row['receipts'] = {}
        for leaf in ['preflight.txt', 'command.json', 'exit.status', 'verification.txt', 'result-root.txt',
                     'config-inspection.json', 'identity.json', 'run.log', 'replay-script.py', 'gdb-command.json',
                     'gdb-exit.status', 'gdb.log', 'gdb-probe.gdb']:
            file = attempt / leaf
            if file.exists():
                receipt = {'path': str(file), 'sha256': sha(file), 'bytes': file.stat().st_size}
                if leaf not in ['run.log', 'replay-script.py', 'gdb.log', 'identity.json', 'gdb-probe.gdb']:
                    receipt['text'] = file.read_text(errors='replace')
                row['receipts'][leaf] = receipt
        result_root = attempt / 'result-root.txt'
        if not result_root.exists():
            row['classification'] = 'INCONCLUSIVE_HARNESS'
            records.append(row)
            continue
        result = Path(result_root.read_text().strip())
        expected = (attempt / 'expected-cases.txt').read_text().splitlines()
        summary = (result / 'summary_info').read_text()
        info = (result / 'main.info').read_text()
        count, main_count = counts(summary), counts(info)
        actual, verdict = [], []
        for file in sorted(result.rglob('summary_info')):
            for line in file.read_text().splitlines():
                match = re.match(r'^(.+\.sql):(ok|nok)(?:\s|$)', line, re.I)
                if match:
                    actual.append(match[1]); verdict.append(match[2].lower())
        log = (attempt / 'run.log').read_text(errors='replace')
        execution = re.findall(r'(?m)^\[\d+:\d+:\d+\] Testing (.+\.sql) \((\d+)/(\d+) [^)]*\) \[(OK|NOK)\]', log)
        junit = ET.parse(next(result.glob('linux_medium_*.xml'))).getroot()
        junit_cases = list(junit.iter('testcase'))
        checks = {
            'expected_equals_summary_order': actual == expected,
            'expected_equals_execution_order': [item[0] for item in execution] == expected,
            'execution_ordinals_complete': [int(item[1]) for item in execution] == list(range(1, len(expected) + 1)),
            'execution_verdicts_equal_summary': [item[3].lower() for item in execution] == verdict,
            'summary_equals_main_counts': count == main_count,
            'all_expected_executed': count['total'] == len(expected) == int(re.search(r'(?m)^execute_case:(\d+)', info)[1]),
            'native_verdict_totals_reconcile': count['success'] == verdict.count('ok') and count['fail'] == verdict.count('nok'),
            'junit_case_count': len(junit_cases) == len(expected),
            'junit_failure_count': sum(case.find('failure') is not None for case in junit_cases) == count['fail'],
            'every_result_exists': all(Path(case).with_suffix('.result').is_file() for case in expected),
            'native_end_marker': '[MEDIUM] TEST END' in log,
            'result_path_matches': re.search(r'(?m)^result_path:(.*)', info)[1].strip() == str(result),
        }
        if not all(checks.values()):
            raise RuntimeError((attempt.name, checks))
        row.update(classification='DIAGNOSTIC_OBSERVATION' if row['identity'].get('after_query_observations') or row['identity'].get('conversion_plans')
                   else ('DIAGNOSTIC_REDUCTION' if row['identity'].get('diagnostic_reduction') else 'ORIGINAL_TESTS'),
                   counts=count, coverage_checks=checks, summary_info=summary, main_info=info)
        for index, (case, state) in enumerate(zip(expected, verdict), 1):
            sql = Path(case)
            verdict_rows.append('\t'.join([attempt.name, str(index), str(sql.relative_to(attempt / 'scenario')),
                                         state.upper(), sha(sql), sha(sql.with_suffix('.result'))]))
        signature = classify(attempt, answers)
        row['signature'] = signature
        row['selected_raw_results'] = {name: (attempt / 'scenario/_02_xtests/cases' / (name + '.result')).read_text()
                                       for name in signature['cases']}
        if (attempt / 'gdb.log').exists():
            raw = (attempt / 'gdb.log').read_text(errors='replace')
            probes[attempt.name] = {'command': json.loads((attempt / 'gdb-command.json').read_text()),
                'records': [json.loads(line.split('[DEBUG-pr7927-heap] ', 1)[1]) for line in raw.splitlines()
                            if '[DEBUG-pr7927-heap] ' in line]}
            shutil.copyfile(attempt / 'gdb.log', dest / (attempt.name + '-gdb.txt'))
        records.append(row)
    (dest / 'attempts.json').write_text(json.dumps(records, indent=2) + '\n')
    (dest / 'ordered-verdicts.tsv').write_text('attempt\tordinal\tcase\tnative_verdict\tsql_sha256\tresult_sha256\n' + '\n'.join(verdict_rows) + '\n')
    (dest / 'heap-boundary.json').write_text(json.dumps(probes, indent=2) + '\n')
    shutil.copyfile(root / 'input-manifest.json', dest / 'input-manifest.json')
    shutil.copyfile(root / 'ci-head-executed-order.txt', dest / 'ci-executed-order.txt')
    for name in ['head-predecessors-02', 'base-predecessors-02', 'head-observe-02', 'base-observe-02',
                 'head-fresh-heaps', 'base-fresh-heaps', 'head-plans', 'base-plans',
                 'head-plans-full', 'base-plans-full']:
        for target in ['to_char_order_by', 'to_number_order_by', 'to_timestamp_order_by']:
            source = root / name / 'scenario/_02_xtests/cases' / (target + '.result')
            shutil.copyfile(source, dest / (name + '-' + target + '.txt'))
    for leaf in ['cubrid.conf', 'cubrid_broker.conf', 'cubrid_ha.conf']:
        head = root / 'head-heap-boundary/effective-runtime-config' / leaf
        base = root / 'base-heap-boundary/effective-runtime-config' / leaf
        assert head.read_bytes() == base.read_bytes(), leaf
        shutil.copyfile(head, dest / ('runtime-' + leaf))
    print(json.dumps({'attempts': len(records), 'ordered_verdicts': len(verdict_rows),
                      'covered': sum('coverage_checks' in row for row in records),
                      'gdb_probes': {key: len(value['records']) for key, value in probes.items()}}))


if __name__ == '__main__':
    main()
