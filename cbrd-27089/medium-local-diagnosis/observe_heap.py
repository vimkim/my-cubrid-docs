#!/usr/bin/env python3
"""Attach read-only GDB probes to one owned native disposable server."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import shutil


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('side', choices=['head', 'base'])
    parser.add_argument('attempt', type=Path)
    parser.add_argument('--locale-library', type=Path, required=True)
    args = parser.parse_args()
    attempt = args.attempt.resolve()
    script = Path(__file__).with_name('heap-boundary.gdb')
    command = [sys.executable, str(Path(__file__).with_name('differential_loop.py')),
               args.side, str(attempt), '--observe', '--locale-library', str(args.locale_library)]
    runner = subprocess.Popen(command)
    started = time.monotonic()
    debugger = None
    while runner.poll() is None and time.monotonic() - started < 480:
        log = attempt / 'run.log'
        if log.exists() and log.read_text(errors='replace').count('] Testing ') >= 350:
            for proc in Path('/proc').iterdir():
                if not proc.name.isdigit():
                    continue
                try:
                    executable = (proc / 'exe').resolve(strict=True)
                except (FileNotFoundError, PermissionError, ProcessLookupError):
                    continue
                if executable == attempt / 'cubrid/bin/cub_server':
                    env = os.environ.copy()
                    env['PR7927_DATA_PAGE'] = '21643' if args.side == 'head' else '21515'
                    pinned_script = attempt / 'gdb-probe.gdb'
                    shutil.copyfile(script, pinned_script)
                    gdb_command = ['gdb', '-q', '-nx', '-batch',
                                   '-ex', 'set sysroot /',
                                   '-ex', 'set solib-search-path ' + str(attempt / 'cubrid/lib'),
                                   str(executable), '-p', proc.name, '-x', str(pinned_script)]
                    (attempt / 'gdb-command.json').write_text(json.dumps({
                        'command': gdb_command, 'filter_data_page': env['PR7927_DATA_PAGE'],
                        'probe_sha256': hashlib.sha256(pinned_script.read_bytes()).hexdigest(),
                        'pid_cmdline': (proc / 'cmdline').read_bytes().decode(errors='replace').replace('\0', ' ')}) + '\n')
                    stream = (attempt / 'gdb.log').open('w')
                    debugger = subprocess.Popen(gdb_command, env=env, stdout=stream, stderr=subprocess.STDOUT)
                    break
            if debugger:
                break
        time.sleep(0.1)
    if debugger is None:
        print('INCONCLUSIVE: no owned server attachment', file=sys.stderr)
    status = runner.wait()
    if debugger:
        try:
            code = debugger.wait(timeout=30)
        except subprocess.TimeoutExpired:
            debugger.terminate()
            code = debugger.wait(timeout=10)
        (attempt / 'gdb-exit.status').write_text(str(code) + '\n')
        stream.close()
    return status


if __name__ == '__main__':
    raise SystemExit(main())
