#!/usr/bin/env python3
"""gaps.py ERRLOG [N]: the N longest pauses between consecutive 'Time:' records of a CUBRID error log, with the record before each."""
import re, sys
from datetime import datetime
path, n = sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else 5
recs = []
for line in open(path, errors='replace'):
    m = re.match(r'Time: (\d\d/\d\d/\d\d \d\d:\d\d:\d\d\.\d{3}) - (.*)', line)
    if m:
        recs.append((datetime.strptime(m.group(1), '%m/%d/%y %H:%M:%S.%f'), m.group(2)[:110]))
gaps = sorted(((b[0] - a[0]).total_seconds(), a) for a, b in zip(recs, recs[1:]))[-n:]
for g, (t, txt) in reversed(gaps):
    print(f'{g:7.3f}s after {t:%H:%M:%S.%f} {txt}')
