#!/usr/bin/env python3
"""Observe sampled page-cache residency immediately before demanded trace reads.

This is an instrumented observation, not a primary performance timing. A fixed
seed selects the same stratified random sample under every request permutation.
"""
import argparse
import ctypes
import hashlib
import json
import mmap
import os
from pathlib import Path
import random
import sys
import time

sys.dont_write_bytecode = True
import read_order_experiment as experiment


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--mode', choices=['normal', 'random'], required=True)
    parser.add_argument('--schedule', choices=['captured', 'defer', 'sorted'], required=True)
    parser.add_argument('--cpu', type=int, default=16)
    args = parser.parse_args()
    os.sched_setaffinity(0, {args.cpu})
    args.output.mkdir(parents=True, exist_ok=False)
    manifest = json.loads(args.manifest.read_text())
    rows = [tuple(map(int, line.split())) for line in Path(manifest['request_types']).read_text().splitlines()]
    if any(n != 1 for n in experiment.bounded.page_counts(rows).values()):
        raise ValueError('this observation requires pages demanded exactly once')
    selected = experiment.schedule(rows, args.schedule, 64)
    generator = random.Random(27791)
    sample_keys = set()
    for kind in [2, 14]:
        candidates = [r for r in rows if r[3] == kind]
        sample_keys.update(generator.sample(candidates, len(candidates) // 16))
    opened = experiment.bounded.validate(manifest)
    libc = ctypes.CDLL(None, use_errno=True)
    libc.mmap.argtypes = [ctypes.c_void_p, ctypes.c_size_t, ctypes.c_int,
                          ctypes.c_int, ctypes.c_int, ctypes.c_long]
    libc.mmap.restype = ctypes.c_void_p
    libc.mincore.argtypes = [ctypes.c_void_p, ctypes.c_size_t, ctypes.POINTER(ctypes.c_ubyte)]
    libc.mincore.restype = ctypes.c_int
    libc.munmap.argtypes = [ctypes.c_void_p, ctypes.c_size_t]
    mappings = {}
    try:
        fds = {int(old): opened[path] for old, path in manifest['fd_map'].items() if path in opened}
        page = os.sysconf('SC_PAGE_SIZE')
        for fd in opened.values():
            size = os.fstat(fd).st_size
            address = libc.mmap(None, size, mmap.PROT_READ, mmap.MAP_PRIVATE, fd, 0)
            if address == ctypes.c_void_p(-1).value:
                raise OSError(ctypes.get_errno(), 'mmap')
            mappings[fd] = address, size
            os.fsync(fd)
            os.posix_fadvise(fd, 0, 0, os.POSIX_FADV_DONTNEED)
            os.posix_fadvise(fd, 0, 0, os.POSIX_FADV_RANDOM if args.mode == 'random' else os.POSIX_FADV_NORMAL)
        before, resident = experiment.residency(list(opened))
        experiment.save(args.output / 'resident-before.json', before)
        if resident:
            raise RuntimeError(f'cache not empty: {resident}')
        observations = []
        before_io = experiment.bounded.proc_io()
        start = time.monotonic()
        for index, (old, offset, size, kind) in enumerate(selected):
            fd = fds[old]
            address, length = mappings[fd]
            if offset % page or size % page or offset < 0 or offset + size > length:
                raise ValueError('unaligned or out-of-range request')
            sample = (old, offset, size, kind) in sample_keys
            if sample:
                vector = (ctypes.c_ubyte * (size // page))()
                if libc.mincore(address + offset, size, vector):
                    raise OSError(ctypes.get_errno(), 'mincore')
                resident_pages = sum(v & 1 for v in vector)
                begin = time.monotonic_ns()
            data = os.pread(fd, size, offset)
            if len(data) != size:
                raise RuntimeError('short read')
            if sample:
                observations.append({'index': index, 'captured_fd': old, 'offset': offset,
                                     'kind': kind, 'resident_pages_before': resident_pages,
                                     'pages': len(vector), 'duration_ns': time.monotonic_ns() - begin})
        elapsed = time.monotonic() - start
        io = experiment.bounded.proc_io()
        summary = {}
        for kind in [2, 14]:
            items = [v for v in observations if v['kind'] == kind]
            summary[str(kind)] = {'samples': len(items),
                'fully_cached': sum(v['resident_pages_before'] == v['pages'] for v in items),
                'partly_cached': sum(0 < v['resident_pages_before'] < v['pages'] for v in items),
                'uncached': sum(v['resident_pages_before'] == 0 for v in items)}
        result = {'mode': args.mode, 'schedule': args.schedule, 'instrumented_elapsed_seconds': elapsed,
                  'read_bytes': io['read_bytes'] - before_io['read_bytes'], 'samples': summary,
                  'requests': len(selected), 'resident_before_bytes': resident,
                  'sample_seed': 27791,
                  'sample_sha256': experiment.bounded.request_hash(sorted(sample_keys)),
                  'script_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                  'trace_sha256': hashlib.sha256(Path(manifest['request_types']).read_bytes()).hexdigest()}
        checked = experiment.bounded.validate(manifest)
        for fd in checked.values():
            os.close(fd)
        experiment.save(args.output / 'observations.json', observations)
        experiment.save(args.output / 'result.json', result)
        print(json.dumps(result), flush=True)
    finally:
        for address, size in mappings.values():
            if libc.munmap(address, size) != 0:
                raise OSError(ctypes.get_errno(), 'munmap')
        for fd in opened.values():
            os.close(fd)


if __name__ == '__main__':
    main()
