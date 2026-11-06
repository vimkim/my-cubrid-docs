#!/usr/bin/env python3
"""Static check (text only, nothing is built or run): LOG_RCVINDEX enum in recovery.h versus RV_fun[] in recovery.c.

Usage: python3 -I probe_rvfun_contiguity.py <snapshot-root>   (a directory that holds src/transaction/recovery.{h,c})
Checks: enum values are contiguous from 0; RV_fun[] holds one entry per enum value, in enum order, with matching
name strings; RV_LAST_LOGID equals the last enum value.  This mirrors what rv_check_rvfuns () asserts in a debug
server at startup, so the real check (level 4) is a debug boot; this is the level 3 source form.
"""
import re, sys
root = sys.argv[1]
strip = lambda s: re.sub(r'//[^\n]*', '', re.sub(r'/\*.*?\*/', '', s, flags=re.S))
h = strip(open(root + '/src/transaction/recovery.h').read())
enum = re.search(r'typedef enum\s*\{(.*?)\}\s*LOG_RCVINDEX', h, re.S).group(1)
order, vals, cur = [], {}, -1
for tok in enum.split(','):
    m = re.match(r'\s*(RV[A-Z0-9_]+)\s*(?:=\s*(\w+))?\s*$', tok)
    if not m:
        continue
    n, v = m.groups()
    cur = cur + 1 if v is None else (int(v) if v.isdigit() else vals[v])
    vals[n] = cur
    if n not in ('RV_LAST_LOGID', 'RV_NOT_DEFINED'):
        order.append(n)
c = strip(open(root + '/src/transaction/recovery.c').read())
tbl = c[c.index('struct rvfun RV_fun[] = {'):]
tbl = tbl[:tbl.index('\n};')]
tab = re.findall(r'\{\s*(RV[A-Z0-9_]+)\s*,\s*"(RV[A-Z0-9_]+)"', tbl)
names = [a for a, _ in tab]
print('enum entries', len(order), 'table entries', len(tab), 'RV_LAST_LOGID', vals['RV_LAST_LOGID'])
print('enum contiguous from 0:', [vals[x] for x in order] == list(range(len(order))))
print('table order == enum order:', names == order)
print('table name string == enum name:', all(a == b for a, b in tab))
print('RV_LAST_LOGID == last enum value:', vals['RV_LAST_LOGID'] == vals[order[-1]])
print('OOS block (index: name):', {vals[n]: n for n in order if vals[n] >= 136})
