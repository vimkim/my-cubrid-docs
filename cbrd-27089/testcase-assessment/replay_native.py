#!/usr/bin/env python3
"""Retain an isolated PR7927 native replay; invoke from a loaded engine worktree."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess


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
    args = parser.parse_args()
    if args.suite == 'medium' and args.shell_case:
        parser.error('--shell-case applies only to shell')
    attempt = args.attempt.resolve()
    attempt.mkdir(parents=True, exist_ok=False)
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
        data = attempt / 'mdb.tar.gz'
        shutil.copyfile(PUBLIC / 'medium/files/mdb.tar.gz', data)
        identity['mdb_sha256'] = digest(data)
        cases = sorted(scenario.joinpath('cases').glob('*.sql'))
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
