#!/usr/bin/env python3
"""race.py ATTEMPT...: per attempt, when the server's -1127 record (and its stack dump) began and how long the server log
stayed silent, against what the test CAS was doing then: the CAS SQL log lines around the stall start."""
import re, sys, os
from datetime import datetime
for a in sys.argv[1:]:
    base = os.path.expanduser(f'~/tk/{a}/srvlog')
    srv = [l for l in open(f'{base}/cubrid.err', errors='replace')]
    t0 = gap = None
    times = []
    for l in srv:
        m = re.match(r'Time: (\S+ \S+) - (.*)', l)
        if m:
            times.append((datetime.strptime(m.group(1), '%m/%d/%y %H:%M:%S.%f'), m.group(2)))
    for (t, txt), (u, _) in zip(times, times[1:]):
        if 'CODE = -1127' in txt:
            t0, gap = t, (u - t).total_seconds()
    cas = []
    for l in open(f'{base}/broker/sql_log/broker1_2.sql.log', errors='replace'):
        m = re.match(r'(\d\d-\d\d-\d\d \d\d:\d\d:\d\d\.\d{3}) (.*)', l)
        if m:
            cas.append((datetime.strptime(m.group(1), '%y-%m-%d %H:%M:%S.%f'), m.group(2)[:70]))
    before = [c for c in cas if c[0] <= t0][-2:]
    after = [c for c in cas if c[0] > t0][:1]
    down = any('SERVER DOWN' in c[1] for c in cas)
    print(f'{a}: -1127 at {t0:%H:%M:%S.%f}, server log silent {gap:.3f}s, CAS SERVER DOWN={down}')
    for t, txt in before + after:
        print(f'    {(t - t0).total_seconds():+7.3f}s {txt}')
