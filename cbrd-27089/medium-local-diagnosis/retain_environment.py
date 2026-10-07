#!/usr/bin/env python3
"""Retain pinned historical CTP comparisons and local build/input identities."""
import hashlib
import io
import json
from pathlib import Path
import platform
import re
import subprocess
import zipfile


ROOT = Path('/home/vimkim/tmp/pr7927-medium-diagnosis-20261007')
DEST = Path(__file__).with_name('evidence')
CTP = Path('/home/vimkim/gh/ctp/run-sql')


def out(*args):
    return subprocess.check_output(args, text=True).strip()


def sha(data):
    return hashlib.sha256(data).hexdigest()


def entries(data):
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        return {name: sha(archive.read(name)) for name in archive.namelist() if not name.endswith('/')}


def main():
    assets, jars = {}, {}
    for role, ref in [('head_ci', '44e3f97c788ad82091d5b66d728852f3279b1e86'),
                      ('base_ci', '4d0043a7b149b3fc5d3ccb2e08c98cf8d77b34fb')]:
        files = {}
        for path in ['CTP/conf/medium_dev.conf', 'CTP/sql/configuration/test_config/test_default.xml',
                     'CTP/sql/lib/cubridqa-cqt.jar', 'CTP/sql/bin/run.sh']:
            data = subprocess.check_output(['git', '-C', str(CTP), 'show', ref + ':' + path])
            files[path] = {'sha256': sha(data), 'bytes': len(data)}
            if path.endswith('cubridqa-cqt.jar'):
                jars[role] = data
        assets[role] = {'revision': ref, 'files': files}
    jars['native'] = (CTP / 'CTP/sql/lib/cubridqa-cqt.jar').read_bytes()
    assets['comparison'] = {
        'historical_delta_paths': out('git', '-C', str(CTP), 'diff', '--name-only',
            assets['base_ci']['revision'], assets['head_ci']['revision']).splitlines(),
        'cqt_all_uncompressed_entries_equal': entries(jars['head_ci']) == entries(jars['base_ci']) == entries(jars['native']),
        'native_cqt_sha256': sha(jars['native']),
        'ci_execution_orders_byte_equal': (ROOT / 'ci-head-executed-order.txt').read_bytes() == (ROOT / 'ci-base-executed-order.txt').read_bytes(),
        'ci_order_case_count': len((ROOT / 'ci-head-executed-order.txt').read_text().splitlines()),
        'native_ctp_revision': out('git', '-C', str(CTP), 'rev-parse', 'HEAD'),
        'native_ctp_status': out('git', '-C', str(CTP), 'status', '--short'),
    }
    (DEST / 'asset-comparison.json').write_text(json.dumps(assets, indent=2) + '\n')
    environment = {'kernel': platform.platform(), 'os_release': Path('/etc/os-release').read_text(),
                   'gcc': out('gcc', '--version').splitlines()[0], 'java': 'javac 1.8.0_462',
                   'sources': {}, 'runtime_configs_head_base_byte_equal': {},
                   'exploratory_fresh_database_attempts': []}
    for side, name in [('head', 'CBRD-27089-pr7927-value-ref-extraction'), ('base', 'pr7927-assessment-base')]:
        source = Path('/home/vimkim/gh/cb') / name
        install = Path('/home/vimkim/.cub/install') / name / 'debug_gcc'
        cache = source / 'build_preset_debug_gcc/CMakeCache.txt'
        flags = {}
        for line in cache.read_text().splitlines():
            match = re.match(r'((?:CMAKE_BUILD_TYPE|CMAKE_CXX_COMPILER|CMAKE_C_COMPILER|CMAKE_CXX_FLAGS|CMAKE_C_FLAGS|UNIT_TEST[^:]*)):[^=]+=(.*)', line)
            if match:
                flags[match[1]] = match[2]
        environment['sources'][side] = {'root': str(source), 'commit': out('git', '-C', str(source), 'rev-parse', 'HEAD'),
            'status': out('git', '-C', str(source), 'status', '--short'), 'build_cache_sha256': sha(cache.read_bytes()),
            'relevant_build_options': flags,
            'installed_binaries': {path: sha((install / path).read_bytes())
                                   for path in ['bin/cub_server', 'bin/cubrid_rel', 'lib/libcubrid.so'] if (install / path).exists()}}
    for leaf in ['cubrid.conf', 'cubrid_broker.conf', 'cubrid_ha.conf']:
        head = ROOT / 'head-heap-boundary/effective-runtime-config' / leaf
        base = ROOT / 'base-heap-boundary/effective-runtime-config' / leaf
        environment['runtime_configs_head_base_byte_equal'][leaf] = {'equal': head.read_bytes() == base.read_bytes(),
                                                                     'sha256': sha(head.read_bytes())}
    for name in ['head-numeric-01', 'head-numeric-02', 'head-numeric-03']:
        attempt = ROOT / name
        row = {'name': name, 'path': str(attempt),
               'use': 'Exploratory fresh DB, not the matched native medium starting state. Java object identity output is not physical OID evidence.'}
        if attempt.exists():
            row['files'] = {str(path.relative_to(attempt)): sha(path.read_bytes()) for path in sorted(attempt.iterdir())
                if path.is_file() and path.name in ['identity.json', 'command.json', 'exit.status', 'run.log', 'probe-script.py', 'NumericProbe.java']}
        environment['exploratory_fresh_database_attempts'].append(row)
    (DEST / 'environment.json').write_text(json.dumps(environment, indent=2) + '\n')
    print('Historical/native CQT entries equal:', assets['comparison']['cqt_all_uncompressed_entries_equal'])
    for side in ['head', 'base']:
        print(side, environment['sources'][side]['relevant_build_options'])


if __name__ == '__main__':
    main()
