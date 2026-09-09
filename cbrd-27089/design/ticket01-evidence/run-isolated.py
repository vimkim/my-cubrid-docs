#!/usr/bin/env python3
"""Run existing OOS SQL binaries with private config/databases; retain evidence."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

SOURCE = Path('/home/vimkim/gh/cb/CBRD-27089-has-oos-but-no-oos')
INSTALL = Path('/home/vimkim/.cub/install/CBRD-27089-has-oos-but-no-oos/debug_gcc')
BUILD = SOURCE / 'build_preset_debug_gcc'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git(*args):
    return subprocess.check_output(['git', '-C', str(SOURCE), *args], text=True)


def main():
    global SOURCE, INSTALL, BUILD
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=SOURCE, help='pinned source worktree for paired runs')
    parser.add_argument('--preset', choices=('debug_gcc', 'release_gcc'), default='debug_gcc')
    parser.add_argument('--timeout', type=int, default=180)
    parser.add_argument('--cpu-affinity', type=int, help='pin this runner and its child processes to one allowed CPU')
    parser.add_argument('--binary-source', type=Path, help='test-only overlay: binary from this worktree against --source engine')
    parser.add_argument('--scratch-root', type=Path, help='existing private parent directory for test fixtures')
    parser.add_argument('label')
    parser.add_argument('--binary', default='test_oos_sql_show')
    parser.add_argument('--filter', default='*')
    parser.add_argument('--output-dir', type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument('--reference-lib-dir', type=Path)
    parser.add_argument('--server-test', action='store_true', help='run an existing in-process SERVER_MODE OOS binary')
    parser.add_argument('--sa-test', action='store_true', help='run an allowlisted non-SQL SA_MODE OOS binary')
    parser.add_argument('--sql-file', type=Path, help='run a retained SQL batch through standalone csql')
    parser.add_argument('--gdb-script', type=Path, help='run a retained scoped debugger check around the selected test')
    parser.add_argument('--perf-stat', action='store_true', help='count user instructions/cycles for the entire test process')
    parser.add_argument('--perf-record', action='store_true', help='sample user instructions and DWARF stacks for the entire test process')
    args = parser.parse_args()
    if args.cpu_affinity is not None:
        if args.cpu_affinity not in os.sched_getaffinity(0):
            parser.error('selected CPU is outside the allowed affinity set')
        os.sched_setaffinity(0, {args.cpu_affinity})
    SOURCE = args.source.resolve()
    BUILD = SOURCE / ('build_preset_' + args.preset)
    INSTALL = Path('/home/vimkim/.cub/install') / SOURCE.name / args.preset
    if args.sql_file and args.gdb_script:
        parser.error('select either a SQL batch or a debugger-wrapped test')
    if (args.perf_stat or args.perf_record) and (args.gdb_script or args.sql_file or args.server_test or args.sa_test):
        parser.error('perf supports an unwrapped standalone SQL test only')
    if args.perf_stat and args.perf_record:
        parser.error('select stat or record, not both')
    if not args.label.replace('-', '').isalnum():
        parser.error('label must contain only letters, digits, and hyphens')
    server_binaries = {'test_oos_server', 'test_oos_delete_server', 'test_oos_remove_file_server',
                       'test_oos_mock_vacuum_server', 'test_oos_vacuum_server', 'test_oos_real_vacuum_server'}
    sa_binaries = {'test_oos', 'test_oos_delete', 'test_oos_remove_file', 'test_oos_bestspace',
                   'test_oos_growth_sweep', 'test_oos_record_flags', 'test_byte_span_writer', 'test_oos_tde_gate'}
    if args.sa_test and (args.server_test or args.sql_file or args.binary not in sa_binaries):
        parser.error('SA unit mode requires an allowlisted binary and no server/SQL override')
    if args.server_test and (args.sql_file or args.reference_lib_dir or args.binary not in server_binaries):
        parser.error('server mode requires an allowlisted server binary and no SQL/reference-SA override')
    if not args.server_test and not args.sa_test and (not args.binary.startswith('test_oos_sql_') or '/' in args.binary):
        parser.error('only existing OOS standalone SQL test binaries are allowed')
    args.output_dir.mkdir(parents=True, exist_ok=True)
    evidence = args.output_dir / (args.label + '.json')
    if evidence.exists():
        parser.error('use a new label; existing evidence is never overwritten')
    sandbox = Path(tempfile.mkdtemp(prefix='pr7600-ticket01-', dir=args.scratch_root))
    runtime = sandbox / 'install'
    runtime.mkdir()
    for item in INSTALL.iterdir():
        if item.name == 'conf':
            shutil.copytree(item, runtime / item.name)
        elif item.is_dir() and item.name in ('log', 'var', 'tmp', 'databases'):
            (runtime / item.name).mkdir()
        else:
            (runtime / item.name).symlink_to(item, target_is_directory=item.is_dir())
    databases = sandbox / 'databases'
    databases.mkdir()
    env = dict(os.environ, CUBRID=str(runtime), CUBRID_DATABASES=str(databases))
    if args.server_test:
        # PL uses Unix sockets with a 108-byte pathname limit. Keep databases on the spacious
        # requested filesystem, but give this fixture its own short socket-only directory.
        env['CUBRID_TMP'] = tempfile.mkdtemp(prefix='pr7600-sock-', dir='/tmp')
    env['PATH'] = str(runtime / 'bin') + os.pathsep + env.get('PATH', '')
    env['LD_LIBRARY_PATH'] = str(runtime / 'lib') + os.pathsep + env.get('LD_LIBRARY_PATH', '')
    library = INSTALL / 'lib/libcubridsa.so.11.5'
    if args.server_test:
        library = INSTALL / 'lib/libcubrid.so.11.5'
    if args.reference_lib_dir:
        library = args.reference_lib_dir.resolve() / 'libcubridsa.so.11.5'
        if args.sql_file and (library.parent / 'libcubridsa.so').resolve() != library:
            parser.error('csql dlopens libcubridsa.so; its reference alias must resolve to the pinned library')
        env['LD_LIBRARY_PATH'] = str(library.parent) + os.pathsep + env['LD_LIBRARY_PATH']
    binary = BUILD / 'bin' / args.binary
    if args.binary_source:
        if args.sql_file or not args.server_test:
            parser.error('test-only overlay currently supports SERVER_MODE tests only')
        binary = args.binary_source.resolve() / ('build_preset_' + args.preset) / 'bin' / args.binary
    if args.sql_file:
        binary = INSTALL / 'bin/csql'
    shutil.copyfile(BUILD / 'build.log', sandbox / 'build.log')
    report = {
        'label': args.label, 'source_revision': git('rev-parse', 'HEAD').strip(),
        'runner': str(Path(__file__).resolve()), 'runner_sha256': digest(Path(__file__)),
        'source_status': git('status', '--short'),
        'engine_test_diff': git('diff', 'HEAD', '--', 'src', 'unit_tests'),
        'submodule_status': git('submodule', 'status', 'cubrid-cci'),
        'build_mode': args.preset + ' / ' + ('SERVER_MODE' if args.server_test else 'SA_MODE'),
        'command_timeout_seconds': args.timeout,
        'measurement_environment': {key: value for key, value in env.items() if key.startswith('PR7600_')},
        'cpu_affinity': sorted(os.sched_getaffinity(0)),
        'binary': str(binary), 'binary_sha256': digest(binary),
        'engine_library': str(library), 'engine_library_sha256': digest(library),
        'cmake_cache_sha256': digest(BUILD / 'CMakeCache.txt'),
        'build_log': str(sandbox / 'build.log'),
        'sandbox': str(sandbox),
        'environment': {key: env[key] for key in ('CUBRID', 'CUBRID_DATABASES', 'LD_LIBRARY_PATH')},
        'socket_directory': env.get('CUBRID_TMP'),
        'records': [],
        'cleanup': 'Private database/config retained; no network server or shared database touched.',
    }
    if not args.server_test:
        report.update(libcubridsa=str(library), libcubridsa_sha256=digest(library))
    test_source = SOURCE / 'unit_tests/oos/sql' / (args.binary + '.cpp')
    if test_source.exists():
        report.update(test_source=str(test_source), test_source_sha256=digest(test_source))
    if args.binary_source:
        report['test_binary_source'] = str(args.binary_source.resolve())
        report['test_binary_source_diff'] = subprocess.check_output(
            ['git', '-C', str(args.binary_source), 'diff', 'HEAD', '--', 'unit_tests'], text=True)
    if args.server_test:
        report['resolved_libraries'] = subprocess.check_output(['ldd', str(binary)], env=env, text=True)
        matching = [line.split('=>', 1)[1].split()[0] for line in report['resolved_libraries'].splitlines()
                    if 'libcubrid.so.11.5 =>' in line]
        if len(matching) != 1 or Path(matching[0]).resolve() != library.resolve():
            raise RuntimeError('SERVER_MODE engine library resolution differs from the recorded engine')
    commands = [
        ['bash', str(SOURCE / 'unit_tests/oos/scripts/setup_unittestdb.sh')],
        [str(binary), '--gtest_filter=' + args.filter,
         '--gtest_output=xml:' + str(sandbox / 'gtest.xml')],
    ]
    if args.sql_file:
        report['sql_file'] = str(args.sql_file.resolve())
        report['sql_sha256'] = digest(args.sql_file)
        report['dlopen_library_alias'] = str((library.parent / 'libcubridsa.so').resolve())
        commands[1] = [str(binary), '-S', '-u', 'DBA', '--no-auto-commit',
                       '-i', str(args.sql_file.resolve()), 'unittestdb']
    if args.gdb_script:
        report['gdb_script'] = str(args.gdb_script.resolve())
        report['gdb_script_sha256'] = digest(args.gdb_script)
        report['gdb_script_contents'] = args.gdb_script.read_text()
        commands[1] = ['gdb', '-nx', '-q', '-batch', '-iex', 'set debuginfod enabled off',
                       '-x', str(args.gdb_script.resolve()), '--args'] + commands[1]
    if args.perf_stat or args.perf_record:
        report['perf_scope'] = 'Entire SQL test process, including initialization, warmups, verification and rollback; not timed batches only.'
        report['perf_version'] = subprocess.check_output(['perf', '--version'], text=True).strip()
        if args.perf_stat:
            commands[1] = ['perf', 'stat', '-x', ';', '-e', 'instructions:u,cycles:u', '--'] + commands[1]
        else:
            report['perf_data'] = str(sandbox / 'perf.data')
            commands[1] = ['perf', 'record', '-e', 'instructions:u', '-c', '2000000',
                           '--call-graph', 'dwarf,4096', '-o', report['perf_data'], '--'] + commands[1]
    try:
        for command in commands:
            try:
                result = subprocess.run(command, env=env, cwd=sandbox, text=True,
                                        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=args.timeout)
            except subprocess.TimeoutExpired as exc:
                output = exc.stdout or b''
                if isinstance(output, bytes):
                    output = output.decode(errors='replace')
                report['records'].append({'command': command, 'exit_code': 124, 'output': output,
                                          'timed_out': True})
                print(output, flush=True)
                break
            report['records'].append({'command': command, 'exit_code': result.returncode,
                                      'output': result.stdout})
            print(result.stdout, flush=True)
            if result.returncode:
                break
    finally:
        evidence.write_text(json.dumps(report, indent=2) + '\n')
        print('Evidence:', evidence, flush=True)
    raise SystemExit(report['records'][-1]['exit_code'])


if __name__ == '__main__':
    main()
