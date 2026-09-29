"""Compare the Linux functional table only; retain suite identity and raw evidence.

Run with `uv run python <this-file>` from cubrid-qahome-fetcher (BeautifulSoup).
Matching testcase names are baseline candidates, not proof of matching symptoms.
"""
import argparse
import json
import re
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from bs4 import BeautifulSoup

FETCHER = Path('/home/vimkim/gh/cubrid-qahome-fetcher')
OUTPUT = Path(__file__).parent
RUNS = {
    'feature': FETCHER / 'runs/20260929-140608-11.5.0.2625-1ec35f8',
    'develop': FETCHER / 'runs/20260929-140608-11.5.0.2622-e1c3db1',
}


def endpoint_key(url):
    parts = urlsplit(url)
    query = parse_qs(parts.query)
    identity = tuple((key, tuple(query[key])) for key in
                     ('statid', 'srctb', 'shellTestId', 'mainId', 'resultId') if key in query)
    return (parts.path.rsplit('/', 1)[-1], identity)


def testcase(path):
    # QA controller home directories and repository names are environment prefixes.
    match = re.search(r'(?:^|/)(sql|shell|shell_perf|isolation|HA|interface|random_query_generator)/', path)
    normalized = path[match.start():].lstrip('/') if match else path
    if ' => ' in normalized:
        normalized = normalized.rstrip('()') + '()'
    return normalized


def collect(run):
    manifest = json.loads((run / 'manifest.json').read_text())
    assert manifest['expected_build_text_found'], 'Build mismatch'
    # lxml repairs the portal's unclosed rowspan cell in the first Linux row.
    soup = BeautifulSoup(next((run / 'raw').glob('showFuntionRes*')).read_text(), 'lxml')
    table = soup.find('table', attrs={'name': 'linux_func'})
    assert table is not None
    summaries, endpoint_suites = {}, {}
    for row in table.find_all('tr'):
        cells = row.find_all(['td', 'th'], recursive=False)
        # Rows without results have no category link.
        categories = {'sql', 'sql_debug', 'medium', 'medium_debug', 'sql_by_cci',
            'shell', 'shell_debug', 'shell_heavy', 'shell_long', 'cci', 'cci_debug',
            'ha_shell', 'ha_repl', 'ha_repl_debug', 'shell_perf', 'isolation',
            'isolation_debug', 'jdbc', 'RQG', 'cdc_repl', 'shell_ext', 'unittest', 'unittest_debug'}
        category_cell = next((c for c in cells if c.get_text(' ', strip=True).replace('&nbsp', '').strip()
                             in categories), None)
        if category_cell is None:
            continue
        category = category_cell.get_text(' ', strip=True).replace('&nbsp', '').strip()
        offset = cells.index(category_cell)
        values = [c.get_text(' ', strip=True) for c in cells[offset + 1:]]
        summaries[category] = {'cells': values, 'links': [a.get('href') for a in row.find_all('a')]}
        for link in summaries[category]['links']:
            endpoint_suites.setdefault(endpoint_key(link), set()).add(category)
    page_suites = {}
    for page in manifest['fetched_pages']:
        suites = endpoint_suites.get(endpoint_key(page['url']), set())
        if suites:
            page_suites[page['path']] = suites
    failures = json.loads((run / 'failure-report.json').read_text())['failures']
    records = {}
    for failure in failures:
        for page in failure['raw_pages']:
            for suite in page_suites.get(page, set()):
                path = testcase(failure['test_path'])
                if not path:
                    continue
                if suite == 'jdbc' and ' => ' not in path:
                    continue
                key = (suite, path)
                record = records.setdefault(key, {'suite': suite, 'testcase': path,
                    'excluded_cdc': suite == 'cdc_repl' or '/cbrd_23842_cdc/' in path,
                    'findings': [], 'pages': []})
                evidence = {k: failure.get(k) for k in ('source_kind', 'first_nok',
                            'crash_summary', 'top_stack_frame', 'host')}
                if evidence not in record['findings']:
                    record['findings'].append(evidence)
                if page not in record['pages']:
                    record['pages'].append(page)
    # The fetcher currently misses Java method identities. Read explicit openFile
    # anchors and NOK headings as supplemental observations, preserving raw pages.
    for page, suites in page_suites.items():
        soup = BeautifulSoup((run / page).read_text(), 'lxml')
        observations = []
        for anchor in soup.find_all('a', onclick=True):
            match = re.search(r"openFile\('([^']+)'", anchor['onclick'])
            if match:
                row = anchor.find_parent('tr')
                observations.append((match[1], row.get_text(' ', strip=True)))
        text = soup.get_text('\n', strip=True)
        for match in re.finditer(r'\[NOK\]\s*\d+\.\s*(.*?)\s*\([^\n]*?\)\s*\n', text):
            observations.append((match[1], text[match.end():match.end() + 1200]))
        for path, evidence in observations:
            path = testcase(path)
            for suite in suites:
                record = records.setdefault((suite, path), {'suite': suite, 'testcase': path,
                    'excluded_cdc': suite == 'cdc_repl' or '/cbrd_23842_cdc/' in path,
                    'findings': [], 'pages': []})
                finding = {'source_kind': 'raw-page-observation', 'first_nok': evidence}
                if finding not in record['findings']:
                    record['findings'].append(finding)
                if page not in record['pages']:
                    record['pages'].append(page)
    return {'run': str(run), 'resolution': manifest['resolved'], 'suites': summaries,
            'warnings': manifest['parser_warnings'], 'records': list(records.values())}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--feature-run', type=Path, default=RUNS['feature'])
    parser.add_argument('--develop-run', type=Path, default=RUNS['develop'])
    parser.add_argument('--output', type=Path, default=OUTPUT / 'comparison_1ec35f8_codex.json')
    args = parser.parse_args()
    data = {role: collect(run) for role, run in
            {'feature': args.feature_run, 'develop': args.develop_run}.items()}
    for role, snapshot in data.items():
        for suite, summary in snapshot['suites'].items():
            cells = summary['cells']
            if len(cells) > 3:
                actual = sum(r['suite'] == suite for r in snapshot['records'])
                assert actual == int(cells[3]), (role, suite, actual, cells[3])
    baseline = {(r['suite'], r['testcase']): r for r in data['develop']['records']}
    for record in data['feature']['records']:
        match = baseline.get((record['suite'], record['testcase']))
        record['classification'] = ('excluded-cdc' if record['excluded_cdc'] else
            'baseline-testcase-needs-symptom-comparison' if match else 'feature-only-candidate')
        record['baseline'] = match
    args.output.write_text(json.dumps(data, indent=2) + '\n')
    for suite, summary in data['feature']['suites'].items():
        records = [r for r in data['feature']['records'] if r['suite'] == suite]
        candidates = [r for r in records if r['classification'] == 'feature-only-candidate']
        print(suite, 'feature', summary['cells'][:5], 'develop',
              data['develop']['suites'].get(suite, {}).get('cells', [])[:5],
              'parsed', len(records), 'candidates', len(candidates))
        for record in candidates:
            print('  ', record['testcase'])


if __name__ == '__main__':
    main()
