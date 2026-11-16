#!/usr/bin/env python3
"""caslog-gap.py SQLLOG [N]: the N longest pauses between consecutive CAS SQL log lines, with the line before and after."""
import re, sys
from datetime import datetime
path, n = sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else 3
lines = []
for line in open(path, errors='replace'):
    m = re.match(r'(\d\d-\d\d-\d\d \d\d:\d\d:\d\d\.\d{3}) (.*)', line)
    if m:
        lines.append((datetime.strptime(m.group(1), '%y-%m-%d %H:%M:%S.%f'), m.group(2)[:90]))
gaps = sorted(((b[0] - a[0]).total_seconds(), a, b) for a, b in zip(lines, lines[1:]))[-n:]
for g, a, b in reversed(gaps):
    print(f'{g:7.3f}s  {a[0]:%H:%M:%S.%f} {a[1]}\n          -> {b[0]:%H:%M:%S.%f} {b[1]}')
