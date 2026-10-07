#!/usr/bin/env python3
"""Copy bounded native receipts; leave installations, DBs and full logs in attempt roots."""
import hashlib
import json
from pathlib import Path
import re
import shutil

ROOT = Path('/home/vimkim/tmp/pr7927-assessment-20261007')
OUT = Path(__file__).resolve().parent / 'evidence'
ATTEMPTS = ['head-shell-01', 'base-shell-01', 'head-medium-01', 'base-medium-01',
            'head-shell-02', 'base-shell-02', 'head-medium-02', 'base-medium-02',
            'head-partition-fixed', 'head-partition-fixed-02', 'final-partition']
OUT.mkdir(exist_ok=True)
manifest = {}
for name in ATTEMPTS:
    source = ROOT / name
    if not (source / 'exit.status').exists():
        continue
    target = OUT / name
    target.mkdir(exist_ok=True)
    for leaf in ['identity.json', 'preflight.txt', 'config-inspection.json', 'expected-cases.txt',
                 'command.json', 'exit.status', 'result-root.txt', 'verification.txt']:
        if (source / leaf).is_file():
            shutil.copyfile(source / leaf, target / leaf)
    for conf in (source / 'conf').glob('*.conf'):
        shutil.copyfile(conf, target / conf.name)
    runlog = (source / 'run.log').read_text(errors='replace')
    pattern = (r'(ccache: error|locale library|Can not|Cannot|ERROR|Error|INCONCLUSIVE|'
               r'Fail to|failed to|Ownership|Cannot change ownership|already exists|'
               r'# OF SELECTED|\[TESTCASE\]|Total Case:|Total Execution Case:|'
               r'Total Success Case:|Total Fail Case:|Total Skip Case:|Result Root Dir:|'
               r'TEST COMPLETE|ELAPSE TIME|admission:|sizing recorded)')
    excerpts = ['%d:%s' % (n, line) for n, line in enumerate(runlog.splitlines(), 1)
                if re.search(pattern, line, re.I)]
    (target / 'run-excerpts.txt').write_text('\n'.join(excerpts) + '\n')
    result_marker = source / 'result-root.txt'
    if result_marker.exists():
        result = Path(result_marker.read_text().strip())
        shell = (result / 'test-shell.xml').exists()
        leaves = ['test-shell.xml', 'test_status.data', 'dispatch_tc_ALL.txt',
                  'dispatch_tc_FIN_local.txt'] if shell else [
                      'linux_medium_64bit.xml', 'summary.info', 'summary_info', 'summary.xml']
        for leaf in leaves:
            if (result / leaf).is_file():
                shutil.copyfile(result / leaf, target / leaf)
        if shell:
            log = (result / 'test_local.log').read_text(errors='replace')
            excerpts = ['%d:%s' % (n, line) for n, line in enumerate(log.splitlines(), 1)
                        if (re.match(r'^-+ [0-9]+ : (OK|NOK)', line)
                            or re.search(r'^\+ (\[ [0-9]+ -lt 100|num_pages=|page.*=)|^Total [0-9]+ object|^Total Pages:', line)
                            or 'instances committed' in line
                            or re.search(r'(Appropriate partition does not exist|Invalid value for partition definition)', line))]
            (target / 'assertion-excerpts.txt').write_text('\n'.join(excerpts) + '\n')
            (target / 'assertion-counts.json').write_text(json.dumps({
                'ok': len(re.findall(r'^-+ [0-9]+ : OK', log, re.M)),
                'nok': len(re.findall(r'^-+ [0-9]+ : NOK', log, re.M)),
            }, indent=2) + '\n')
    manifest[name] = {
        'full_attempt': str(source),
        'run_log_sha256': hashlib.sha256((source / 'run.log').read_bytes()).hexdigest(),
        'retained': {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                     for p in sorted(target.iterdir()) if p.is_file()},
    }
probe = ROOT / 'head-partition-contract-03'
target = OUT / 'head-partition-contract-03'
target.mkdir(exist_ok=True)
for p in sorted(probe.iterdir()):
    if p.suffix in ['.txt', '.objects', '.json'] or p.name.endswith('_objects') or p.name.endswith('_schema'):
        shutil.copyfile(p, target / p.name)
manifest['head-partition-contract-03'] = {
    'full_attempt': str(probe),
    'retained': {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                 for p in sorted(target.iterdir()) if p.is_file()},
}
for suite in ['shell', 'medium']:
    pairs = [ROOT / ('head-' + suite + '-02'), ROOT / ('base-' + suite + '-02')]
    normalized = [(p / 'conf' / (suite + '.conf')).read_text().replace(str(p), '<ATTEMPT>') for p in pairs]
    (OUT / (suite + '-normalized.conf')).write_text(normalized[0])
    manifest[suite + '_effective_config_equivalence'] = {
        'equal_after_attempt_path_normalization': normalized[0] == normalized[1],
        'normalized_sha256': hashlib.sha256(normalized[0].encode()).hexdigest(),
        'note': 'Raw hashes differ for attempt-local input/selection paths; this is local head/base config equivalence only.',
    }
for name in ['head-partition-contract', 'head-partition-contract-02']:
    source = ROOT / name
    target = OUT / name
    target.mkdir(exist_ok=True)
    for p in sorted(source.iterdir()):
        if p.suffix in ['.txt', '.json', '.objects'] or p.name.endswith('_objects'):
            shutil.copyfile(p, target / p.name)
    shutil.copyfile(ROOT / (name + '.launch.log'), target / 'launch.log')
    manifest[name] = {
        'full_attempt': str(source),
        'retained': {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                     for p in sorted(target.iterdir()) if p.is_file()},
    }
shutil.copyfile(ROOT / 'head-doctor-final.txt', OUT / 'head-doctor-final.txt')
builds = {}
for kind in ['head', 'base']:
    p = Path('/home/vimkim/tmp/pr7927-assessment-' + kind + '-build.log')
    builds[kind] = {
        'full_log': str(p), 'sha256': hashlib.sha256(p.read_bytes()).hexdigest(),
        'tail': p.read_text(errors='replace').splitlines()[-12:],
    }
(OUT / 'build-receipts.json').write_text(json.dumps(builds, indent=2) + '\n')
(OUT / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
print(json.dumps({k: v for k, v in manifest.items() if 'equivalence' in k}, indent=2))
