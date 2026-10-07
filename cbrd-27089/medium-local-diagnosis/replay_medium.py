#!/usr/bin/env python3
"""Retain a complete native medium attempt with matched JDBC assets."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import zipfile


HELPER = Path('/home/vimkim/.agents/skills/cubrid-common/scripts/testkit-focused.py')
PUBLIC = Path('/home/vimkim/gh/cubrid-testcases/tc-pr-7927')
PRIVATE = Path('/home/vimkim/gh/cubrid-testcases-private-ex/tc-pr-7927')
SHELL_CASES = [
    'shell/_06_issues/_15_1h/bug_bts_15489/cases/bug_bts_15489.sh',
    'shell/_06_issues/_25_2h/cbrd_26280/cases/cbrd_26280.sh',
    'shell/_35_cherry/issue_21654_server_side_loaddb/partition_tbls/cases/partition_tbls.sh',
]


def output(*cmd):
    return subprocess.check_output(cmd, text=True).strip()


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('suite', choices=['shell', 'medium'])
    parser.add_argument('attempt', type=Path)
    parser.add_argument('--shell-case', choices=SHELL_CASES, action='append')
    parser.add_argument('--jdbc-dir', type=Path, required=True)
    parser.add_argument('--predecessors', action='store_true', help='Add complete _01_fixed before complete _02_xtests')
    parser.add_argument('--locale-library', type=Path, help='Reuse the proven compiled locale asset in a new attempt')
    parser.add_argument('--keep-cases', type=Path, help='DIAGNOSTIC ONLY: immutable reduced workload after complete baseline')
    parser.add_argument('--observe', action='store_true', help='Add after-query plan and OID observations in copied targets')
    parser.add_argument('--fresh-target-heaps', action='store_true', help='DIAGNOSTIC ONLY: disable heap reuse before the three target cases')
    parser.add_argument('--conversion-plans', action='store_true', help='DIAGNOSTIC ONLY: print the original unordered conversion SELECT plans')
    args = parser.parse_args()
    if args.suite == 'medium' and args.shell_case:
        parser.error('--shell-case applies only to shell')
    attempt = args.attempt.resolve()
    attempt.mkdir(parents=True, exist_ok=False)
    shutil.copyfile(Path(__file__), attempt / 'replay-script.py')
    with (attempt / 'preflight.txt').open('w') as stream:
        subprocess.run(['python3', str(HELPER), 'preflight', '--suite', args.suite],
                       stdout=stream, stderr=subprocess.STDOUT, check=True)
    install = Path(os.environ['CUBRID'])
    ctp = Path(os.environ['CTP_HOME'])
    tc = PRIVATE if args.suite == 'shell' else PUBLIC
    identity = {
        'source_root': output('git', 'rev-parse', '--show-toplevel'),
        'engine_revision': output('git', 'rev-parse', 'HEAD'),
        'engine_status': output('git', 'status', '--short'),
        'testcase_root': str(tc),
        'testcase_revision': output('git', '-C', str(tc), 'rev-parse', 'HEAD'),
        'testcase_status': output('git', '-C', str(tc), 'status', '--short'),
        'testcase_patch': output('git', '-C', str(tc), 'diff'),
        'ctp_revision': output('git', '-C', str(ctp), 'rev-parse', 'HEAD'),
        'ctp_status': output('git', '-C', str(ctp), 'status', '--short'),
        'testkit_version': output('testkit', '--version'),
        'testkit_sha256': digest(shutil.which('testkit')),
        'replay_script_sha256': digest(Path(__file__)),
        'focused_helper_sha256': digest(HELPER),
        'java_home': os.environ.get('JAVA_HOME'),
        'original_install': str(install),
        'attempt': str(attempt),
    }
    (attempt / 'identity.json').write_text(json.dumps(identity, indent=2) + '\n')
    shutil.copytree(install, attempt / 'cubrid', symlinks=True)
    jdbc = attempt / 'cubrid/jdbc'
    if jdbc.exists():
        jdbc.rename(attempt / 'original-jdbc-preserved')
    shutil.copytree(args.jdbc_dir.resolve(), jdbc, symlinks=True)
    identity['matched_jdbc_source'] = str(args.jdbc_dir.resolve())
    identity['matched_jdbc_hashes'] = {str(p.relative_to(jdbc)): digest(p) for p in sorted(jdbc.rglob('*')) if p.is_file()}
    shutil.copytree(ctp, attempt / 'CTP', symlinks=True)
    (attempt / 'home').mkdir()
    (attempt / 'conf').mkdir()
    registry = attempt / 'cubrid/databases'
    if registry.exists():
        registry.rename(attempt / 'copied-registry-preserved')
    registry.mkdir()
    (registry / 'databases.txt').touch()
    (attempt / 'cubrid/tmp').mkdir(exist_ok=True)
    expected = attempt / 'expected-cases.txt'
    conf = attempt / 'conf' / (args.suite + '.conf')
    if args.suite == 'medium':
        scenario = attempt / 'scenario/_02_xtests'
        shutil.copytree(PUBLIC / 'medium/_02_xtests', scenario)
        if args.predecessors:
            shutil.copytree(PUBLIC / 'medium/_01_fixed', attempt / 'scenario/_01_fixed')
            scenario = attempt / 'scenario'
        if args.fresh_target_heaps:
            for name in ['to_char_order_by', 'to_number_order_by', 'to_timestamp_order_by']:
                target = attempt / 'scenario/_02_xtests/cases' / (name + '.sql')
                target.write_text("set system parameters 'dont_reuse_heap_file=yes';\n" + target.read_text())
            identity['fresh_target_heaps'] = True
        if args.conversion_plans:
            for name in ['to_char_order_by', 'to_number_order_by', 'to_timestamp_order_by']:
                target = attempt / 'scenario/_02_xtests/cases' / (name + '.sql')
                target.write_text(re.sub(r'(?m)^(select to_(?:char|number|timestamp)\(f\) from foo\s*;)',
                                         r'--@queryplan\n\1', target.read_text()))
            identity['conversion_plans'] = True
        if args.keep_cases:
            keep = set(args.keep_cases.read_text().splitlines())
            for case in scenario.rglob('*.sql'):
                key = str(case.relative_to(attempt / 'scenario'))
                if key not in keep: case.unlink()
            identity['diagnostic_reduction'] = {'list': str(args.keep_cases), 'kept': sorted(keep)}
        if args.observe:
            jar = attempt / 'CTP/sql/lib/cubridqa-cqt.jar'
            saved = attempt / 'cqt-before-observation.jar'
            jar.rename(saved)
            member = 'com/navercorp/cubridqa/cqt/console/dao/ConsoleDAO.class'
            with zipfile.ZipFile(saved) as original, zipfile.ZipFile(jar, 'w') as observed:
                for item in original.infolist():
                    raw = original.read(item.filename)
                    if item.filename == member:
                        assert raw.count(b'getTableName') == 1
                        raw = raw.replace(b'getTableName', b'getOidString')
                    observed.writestr(item, raw)
            identity['cqt_oid_observation'] = {'original_sha256': digest(saved), 'observed_sha256': digest(jar), 'constant': 'getTableName -> getOidString', 'class': member}
            for name in ['to_char_order_by','to_number_order_by','to_timestamp_order_by']:
                target = attempt / 'scenario/_02_xtests/cases' / (name + '.sql')
                text = target.read_text()
                text = re.sub(r'(?m)^(select to_(?:char|number|timestamp)\(f\) from foo\s*;)', r'\1\n--@queryplan\nselect foo, f as probe_value from foo;', text)
                target.write_text(text)
            identity['after_query_observations'] = True
        data = attempt / 'mdb.tar.gz'
        shutil.copyfile(PUBLIC / 'medium/files/mdb.tar.gz', data)
        identity['mdb_sha256'] = digest(data)
        cases = sorted(scenario.rglob('*.sql'))
        identity['scenario_sha256'] = {
            str(p.relative_to(scenario)): digest(p)
            for p in sorted(scenario.rglob('*')) if p.is_file()
        }
        base_conf = attempt / 'CTP/conf/medium_dev.conf'
        extra = ['--data-file', str(data)]
    else:
        scenario = PRIVATE / 'shell'
        cases = [PRIVATE / p for p in (args.shell_case or SHELL_CASES)]
        base_conf = attempt / 'CTP/conf/shell_ci.conf'
        extra = []
    expected.write_text(''.join(str(p) + '\n' for p in cases))
    subprocess.run(['python3', str(HELPER), 'prepare-config', '--suite', args.suite,
                    '--base-conf', str(base_conf), '--output-conf', str(conf),
                    '--scenario', str(scenario), '--expected-list', str(expected), *extra], check=True)
    if args.suite == 'shell':
        # Native discovery adds corpus-wide macro skips to focused totals. None
        # of these selected cases has this macro, so the selected set is equal.
        macro = 'LINUX_NOT_SUPPORTED'
        if any(macro in p.read_text(errors='replace') for p in cases):
            raise RuntimeError('A selected case needs the preserved macro policy')
        rendered = re.sub(r'(?m)^testcase_exclude_by_macro=.*$',
                          'testcase_exclude_by_macro=', conf.read_text())
        conf.write_text(rendered)
    if args.locale_library:
        locale = attempt / 'cubrid/lib/libcubrid_all_locales.so'
        shutil.copyfile(args.locale_library, locale)
        identity['cached_locale'] = {'source': str(args.locale_library), 'sha256': digest(locale)}
        conf.write_text(re.sub(r'(?m)^need_make_locale=.*$', 'need_make_locale=no', conf.read_text()))
    settings = dict(re.findall(r'(?m)^([^#;\[\s][^=\n]*)=(.*)$', conf.read_text()))
    requirements = {'parallel_slots': '1', 'test_category': args.suite,
                    'testcase_exclude_from_file': ''}
    if args.suite == 'medium':
        requirements.update(create_table_reuseoid='no', data_file=str(data))
    else:
        requirements.update(scenario_disk='on', testcase_update_yn='false',
                            testcase_retry_num='0', test_continue_yn='false',
                            feedback_type='file', testcase_from_file=str(expected),
                            scenario_ram_mb='', testcase_workspace_dir='')
    for key, value in requirements.items():
        if settings.get(key) != value:
            raise RuntimeError(f'Unsafe effective config: {key}={settings.get(key)!r}')
    (attempt / 'config-inspection.json').write_text(json.dumps(requirements, indent=2) + '\n')
    identity['base_conf_sha256'] = digest(base_conf)
    identity['effective_conf_sha256'] = digest(conf)
    (attempt / 'identity.json').write_text(json.dumps(identity, indent=2) + '\n')
    env = os.environ.copy()
    for name in list(env):
        if name.startswith('CUBRID') and (name.endswith('_FILE') or name.endswith('_DIR')):
            env.pop(name)
    env.update(HOME=str(attempt / 'home'), CUBRID=str(attempt / 'cubrid'),
               CUBRID_DATABASES=str(registry), CUBRID_TMP=str(attempt / 'cubrid/tmp'),
               CTP_HOME=str(attempt / 'CTP'), TESTKIT_CONTAIN='1',
               TESTKIT_NATIVE='sql' if args.suite == 'medium' else 'shell')
    env['PATH'] = ':'.join([str(attempt / 'CTP/bin'), str(attempt / 'CTP/common/script'),
                           str(attempt / 'cubrid/bin'), env['PATH']])
    env['LD_LIBRARY_PATH'] = str(attempt / 'cubrid/lib') + ':' + env.get('LD_LIBRARY_PATH', '')
    for leaf in ['ccache', 'ccache-tmp']:
        (attempt / 'home' / leaf).mkdir()
    env['CCACHE_DIR'] = str(attempt / 'home/ccache')
    env['CCACHE_TEMPDIR'] = str(attempt / 'home/ccache-tmp')
    identity['runtime_adjustments'] = {
        'CCACHE_DIR': env['CCACHE_DIR'], 'CCACHE_TEMPDIR': env['CCACHE_TEMPDIR'],
        'macro_filter_cleared_without_selected_membership_change': args.suite == 'shell',
    }
    identity['controlled_predecessors'] = args.predecessors
    identity['selected_cubrid'] = shutil.which('cubrid', path=env['PATH'])
    identity['selected_release'] = subprocess.check_output(
        [str(attempt / 'cubrid/bin/cubrid_rel')], env=env, text=True).strip()
    (attempt / 'identity.json').write_text(json.dumps(identity, indent=2) + '\n')
    cmd = ['testkit', args.suite, '-c', str(conf)]
    (attempt / 'command.json').write_text(json.dumps(cmd) + '\n')
    print(f'Executing {args.suite}: {attempt}', flush=True)
    with (attempt / 'run.log').open('w') as stream:
        result = subprocess.run(cmd, env=env, stdout=stream, stderr=subprocess.STDOUT)
    (attempt / 'exit.status').write_text(str(result.returncode) + '\n')
    run_log = (attempt / 'run.log').read_text(errors='replace')
    if args.suite == 'shell':
        result_dir = attempt / 'CTP/result/shell/current_runtime_logs'
    else:
        matches = re.findall(r'Result Root Dir:\s*(\S+)', run_log)
        if not matches:
            (attempt / 'verification.txt').write_text(
                'INCONCLUSIVE: no result root; database preparation failed before case verdicts\n')
            print(f'Inconclusive attempt retained: {attempt}', flush=True)
            return 1
        result_dir = Path(matches[-1])
    (attempt / 'result-root.txt').write_text(str(result_dir) + '\n')
    with (attempt / 'verification.txt').open('w') as stream:
        verdict = subprocess.run(['python3', str(HELPER), 'verify', '--suite', args.suite,
                                  '--result-dir', str(result_dir), '--expected-list', str(expected),
                                  '--run-log', str(attempt / 'run.log'),
                                  '--runner-exit', str(result.returncode)],
                                 stdout=stream, stderr=subprocess.STDOUT)
    print(f'Runner exit {result.returncode}; verifier exit {verdict.returncode}; {result_dir}', flush=True)
    return verdict.returncode


if __name__ == '__main__':
    raise SystemExit(main())
