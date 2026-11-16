#!/usr/bin/env python3
"""Print the log header fields of an active log volume (page 0, after the 16-byte page header).
Offsets from `ptype /o struct log_header` of the 11.5.0.2962-f69816c debug libcubrid.so."""
import struct, sys

def lsa(raw):
    v = struct.unpack('<q', raw)[0]
    pageid = v & ((1 << 48) - 1)
    if pageid >= 1 << 47:
        pageid -= 1 << 48
    off = (v >> 48) & 0xffff
    if off >= 1 << 15:
        off -= 1 << 16
    return f'{pageid}|{off}'

with open(sys.argv[1], 'rb') as f:
    h = f.read(16 + 400)[16:]
print('magic', h[0:25].split(b'\0')[0].decode(errors='replace'))
print('npages', struct.unpack_from('<i', h, 96)[0], 'fpageid', struct.unpack_from('<q', h, 104)[0])
print('append_lsa', lsa(h[112:120]), 'chkpt_lsa', lsa(h[120:128]))
print('nxarv_pageid', struct.unpack_from('<q', h, 128)[0], 'nxarv_phy_pageid', struct.unpack_from('<i', h, 136)[0])
print('nxarv_num', struct.unpack_from('<i', h, 140)[0], 'last_arv_num_for_syscrashes', struct.unpack_from('<i', h, 144)[0],
      'last_deleted_arv_num', struct.unpack_from('<i', h, 148)[0], 'was_active_log_reset', h[378])
