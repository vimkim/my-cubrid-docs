#!/usr/bin/env python3
"""Measure launcher exit, pipe EOF and inherited locks independently.
Run only inside a private PID/network/mount namespace (see run-probe.sh).
"""
import fcntl
import json
import os
from pathlib import Path
import selectors
import signal
import subprocess
import sys
import time

mode = sys.argv[1]
assert mode in ('absent', 'present', 'missingdb', 'direct-master', 'revive')
assert os.readlink('/proc/self/ns/pid') != os.environ['PROBE_HOST_PID_NS'], 'private namespace required'
root = Path(os.environ['CUBRID'])
cwd = root.parent
os.chdir(cwd)
report = {'mode': mode, 'version': '', 'commands': []}

def run(args, timeout=35):
    with open(cwd / 'commands.log', 'ab') as output:
        result = subprocess.run(args, stdout=output, stderr=output, timeout=timeout)
    report['commands'].append({'argv': args, 'rc': result.returncode})
    return result.returncode

def snapshot(targets):
    found = []
    for proc in Path('/proc').iterdir():
        if not proc.name.isdigit():
            continue
        try:
            name = (proc / 'comm').read_text().strip()
            if name not in ('cub_master', 'cub_server', 'cub_pl'):
                continue
            fds = {}
            for fd in (proc / 'fd').iterdir():
                try:
                    dest = os.readlink(fd)
                    if dest in targets or '_lgat' in dest or '.err' in dest:
                        fds[fd.name] = dest
                except FileNotFoundError:
                    pass
            found.append({'pid': int(proc.name), 'name': name, 'pgid': os.getpgid(int(proc.name)),
                          'sid': os.getsid(int(proc.name)), 'fds': fds})
        except FileNotFoundError:
            pass
    return found

def unlocked():
    with open(lockfile, 'a') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            return True
        except BlockingIOError:
            return False

report['version'] = subprocess.check_output(['cubrid', '--version'], text=True).strip()
if mode in ('absent', 'present', 'revive'):
    assert run(['cubrid', 'createdb', '--db-volume-size=20M', '--log-volume-size=20M',
                '-F', str(cwd), '-L', str(cwd), 'fdtest', 'en_US.utf8'], 60) == 0
if mode == 'present':
    assert run(['cub_master']) == 0
    time.sleep(2)

lockfile = str(cwd / 'caller.lock')
lock_fd = os.open(lockfile, os.O_CREAT | os.O_RDWR, 0o600)
fcntl.flock(lock_fd, fcntl.LOCK_EX)
argv = ['cub_master'] if mode == 'direct-master' else ['cubrid', 'server', 'start',
                                                         'no_such_db' if mode == 'missingdb' else 'fdtest']
t0 = time.monotonic()
child = subprocess.Popen(argv, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE, pass_fds=(lock_fd,))
os.close(lock_fd)
targets = [lockfile, os.readlink(f'/proc/self/fd/{child.stdout.fileno()}'),
           os.readlink(f'/proc/self/fd/{child.stderr.fileno()}')]
report['targets'] = {'lock': targets[0], 'stdout': targets[1], 'stderr': targets[2]}
report['launcher_pid'] = child.pid
report['observer_pgid'] = os.getpgrp()
sel = selectors.DefaultSelector()
streams = {'stdout': bytearray(), 'stderr': bytearray()}
eof = {'stdout': False, 'stderr': False}
for label, pipe in [('stdout', child.stdout), ('stderr', child.stderr)]:
    os.set_blocking(pipe.fileno(), False)
    sel.register(pipe, selectors.EVENT_READ, label)

def drain(seconds):
    until = time.monotonic() + seconds
    while time.monotonic() < until and sel.get_map():
        for key, _ in sel.select(min(0.1, max(0, until-time.monotonic()))):
            data = os.read(key.fd, 65536)
            if data:
                streams[key.data].extend(data)
            else:
                eof[key.data] = True
                sel.unregister(key.fileobj)
    return dict(eof)

while time.monotonic() - t0 < 30:
    drain(0.1)
    if child.poll() is not None:
        break
report['launcher_rc'] = child.poll()
report['launcher_elapsed_s'] = round(time.monotonic() - t0, 3)
report['eof_after_exit_plus_2s'] = drain(2)
report['lock_available_while_running'] = unlocked()
report['holders_after_exit'] = snapshot(targets)
if mode == 'revive':
    old_pid = next(p['pid'] for p in report['holders_after_exit'] if p['name'] == 'cub_server')
    os.kill(old_pid, signal.SIGKILL)
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        drain(0.2)
        current = snapshot(targets)
        if any(p['name'] == 'cub_server' and p['pid'] != old_pid for p in current):
            time.sleep(3)
            break
    report['killed_server_pid'] = old_pid
    report['holders_after_revive'] = snapshot(targets)
    assert any(p['name'] == 'cub_server' and p['pid'] != old_pid
               for p in report['holders_after_revive']), 'server did not revive'
    report['eof_after_revive'] = drain(2)
    report['lock_available_after_revive'] = unlocked()

if mode in ('absent', 'present', 'revive'):
    assert run(['cubrid', 'server', 'stop', 'fdtest']) == 0
    report['eof_after_server_stop'] = drain(2)
    report['lock_available_after_server_stop'] = unlocked()
    report['holders_after_server_stop'] = snapshot(targets)
assert run(['cubrid', 'service', 'stop']) == 0
report['eof_after_service_stop'] = drain(2)
report['lock_available_after_service_stop'] = unlocked()
report['holders_after_service_stop'] = snapshot(targets)
report['output'] = {name: data.decode(errors='replace') for name, data in streams.items()}
if mode in ('absent', 'present', 'revive'):
    assert run(['cubrid', 'deletedb', 'fdtest']) == 0
assert report['launcher_rc'] is not None, 'launcher itself did not exit'
assert all(eof.values()), 'output still open after cleanup'
assert report['lock_available_after_service_stop'], 'lock remained after cleanup'
assert not report['holders_after_service_stop'], 'CUBRID process remained after cleanup'
Path(sys.argv[2]).write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
print(json.dumps({key: report[key] for key in ['mode', 'version', 'launcher_rc', 'launcher_elapsed_s',
      'eof_after_exit_plus_2s', 'lock_available_while_running', 'eof_after_service_stop']}, ensure_ascii=False))
