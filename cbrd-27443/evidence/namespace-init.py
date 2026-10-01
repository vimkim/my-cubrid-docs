#!/usr/bin/env python3
"""PID-namespace init: reap orphaned daemon children while the probe runs."""
import os
import sys

assert os.getpid() == 1, 'must be namespace PID 1'
child = os.fork()
if child == 0:
    os.execv(sys.executable, [sys.executable, *sys.argv[1:]])
while True:
    pid, status = os.waitpid(-1, 0)
    if pid == child:
        code = os.waitstatus_to_exitcode(status)
        sys.exit(code if code >= 0 else 128 - code)
