#!/usr/bin/env python3
"""Print a TLC counterexample from tlc.log as one line per step: action, then the variables that changed.

Usage: python3 -I -B trace.py RUN_DIR_OR_TLC_LOG [VAR,VAR,...]
"""

import os
import re
import sys

path = sys.argv[1]
if os.path.isdir(path):
    path = os.path.join(path, "tlc.log")
only = set(sys.argv[2].split(",")) if len(sys.argv) > 2 else None
text = open(path).read()
m = re.search(r"Invariant (\w+) is violated", text)
print("violated:", m.group(1) if m else "none")
steps = re.findall(r"^State (\d+): <(\w+)[^>]*>\n(.*?)(?=\n\n|\Z)", text, re.S | re.M)
prev = {}
for num, action, body in steps:
    cur = {}
    for line in re.findall(r"^/\\ (\w+) = (.*)$", body, re.M):
        cur[line[0]] = line[1]
    diff = {k: v for k, v in cur.items() if prev.get(k) != v and (only is None or k in only)}
    print(f"{num:>3} {action:<16} " + "  ".join(f"{k}={v}" for k, v in sorted(diff.items())))
    prev = cur
