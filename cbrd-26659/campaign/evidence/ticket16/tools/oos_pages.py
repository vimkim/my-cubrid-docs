#!/usr/bin/env python3
"""CBRD-26659 ticket 16 -- inspect or corrupt bytes of a COPIED CUBRID data volume.

scan <volume> <pagesize>          list PAGE_OOS pages (ptype 8) with the first record's OOS_RECORD_HEADER
xor  <file> <offset> <length>     XOR 0xFF over <length> bytes at <offset>; prints the bytes before and after
set4 <file> <offset> <int>        overwrite 4 bytes at <offset> with a little-endian int32
lastpage <file> <pagesize>        index of the last page that is not all zero bytes

Layout used by scan (pinned engine, storage_common.h / file_io.h / slotted_page.c):
  FILEIO_PAGE.prv: lsa(8) pageid(4) volid(2) ptype(1) pflag(1) ...   -> ptype at page offset 14
  page area starts at 32; SPAGE_HEADER is 32 bytes; the first record therefore starts at page offset 64
  OOS_RECORD_HEADER {int length; int chunk_index; OID next {pageid(4) slotid(2) volid(2)}} = 16 bytes
"""
import json
import struct
import sys

PAGE_OOS = 8


def scan(path, pagesize):
    out = []
    with open(path, "rb") as f:
        pid = 0
        while True:
            page = f.read(pagesize)
            if len(page) < pagesize:
                break
            ptype = page[14]
            if ptype == PAGE_OOS:
                length, index, next_pageid, next_slotid, next_volid = struct.unpack_from("<iiihh", page, 64)
                num_slots, num_records = struct.unpack_from("<hh", page, 32)
                out.append({"pageid": pid, "ptype": ptype, "num_slots": num_slots, "num_records": num_records,
                            "first_record": {"offset": pid * pagesize + 64, "length": length, "chunk_index": index,
                                             "next": [next_volid, next_pageid, next_slotid]}})
            pid += 1
    print(json.dumps(out, indent=1))


def xor(path, offset, length):
    with open(path, "r+b") as f:
        f.seek(offset)
        before = f.read(length)
        after = bytes(b ^ 0xFF for b in before)
        f.seek(offset)
        f.write(after)
    print(json.dumps({"file": path, "offset": offset, "length": length, "before": before.hex(), "after": after.hex()}))


def set4(path, offset, value):
    with open(path, "r+b") as f:
        f.seek(offset)
        before = f.read(4)
        f.seek(offset)
        f.write(struct.pack("<i", value))
    print(json.dumps({"file": path, "offset": offset, "before": before.hex(), "after_int": value}))


def lastpage(path, pagesize):
    """Highest physical page (excluding the header page 0) whose LOG_PAGE header carries a plausible
    logical page id (0 <= id < 2**40); formatted-but-unwritten pages carry -1 or zeros."""
    with open(path, "rb") as f:
        f.seek(0, 2)
        n = f.tell() // pagesize
        for pid in range(n - 1, 0, -1):
            f.seek(pid * pagesize)
            (logical,) = struct.unpack("<q", f.read(8))
            if (0 < logical < (1 << 40)) or (pid == 1 and logical == 0):
                print(pid)
                return
    print(-1)


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "scan":
        scan(sys.argv[2], int(sys.argv[3]))
    elif cmd == "xor":
        xor(sys.argv[2], int(sys.argv[3]), int(sys.argv[4]))
    elif cmd == "set4":
        set4(sys.argv[2], int(sys.argv[3]), int(sys.argv[4]))
    elif cmd == "lastpage":
        lastpage(sys.argv[2], int(sys.argv[3]))
    else:
        sys.exit(__doc__)
