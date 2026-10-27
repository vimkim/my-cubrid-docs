#!/usr/bin/env python3
"""Read-only causal controls for the retained OOS trace, not an engine batch implementation.

Uses bounded_replay.py's manifest validator. Only an owned, stopped fixture is
accepted. Cold trials require zero resident bytes after file-specific eviction.
The native helper receives already validated O_RDONLY descriptors, never paths.
"""
import argparse
from collections import Counter
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import struct
import subprocess
import sys
import time

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('bounded', HERE / 'bounded_replay.py')
bounded = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bounded)


def save(path, value):
    path.write_text(json.dumps(value, indent=2) + '\n')


def schedule(rows, policy, window):
    if policy == 'captured':
        result = list(rows)
    elif policy == 'sorted':
        result = bounded.plan(rows, 'heap-batch', window, -1)[0]
    else:
        result, batch, heaps = [], [], 0
        for row in rows:
            if row[3] == 2 and heaps >= window:
                result.extend(r for r in batch if r[3] != 14)
                result.extend(r for r in batch if r[3] == 14)
                batch, heaps = [], 0
            batch.append(row)
            heaps += row[3] == 2
        result.extend(r for r in batch if r[3] != 14)
        result.extend(r for r in batch if r[3] == 14)
    if Counter(rows) != Counter(result):
        raise ValueError('request multiplicity changed')
    if policy == 'defer' and [r for r in result if r[3] == 14] != [r for r in rows if r[3] == 14]:
        raise ValueError('unsorted deferral changed OOS order')
    return result


def residency(paths):
    value = json.loads(subprocess.check_output(
        ['fincore', '--json', '--bytes', '--output', 'FILE,SIZE,RES', *paths], text=True))
    return value, sum(int(r['res']) for r in value['fincore'])


def host():
    return {'time_ns': time.time_ns(), 'load': os.getloadavg(),
            'io_pressure': Path('/proc/pressure/io').read_text(),
            'diskstats': [l.strip() for l in Path('/proc/diskstats').read_text().splitlines()
                          if ' nvme0n1 ' in l]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--probe', type=Path, required=True)
    parser.add_argument('--mode', choices=['normal', 'random', 'direct', 'warm'], required=True)
    parser.add_argument('--schedule', choices=['captured', 'defer', 'sorted'], required=True)
    parser.add_argument('--window', type=int, default=64)
    parser.add_argument('--cpu', type=int, default=16)
    parser.add_argument('--instrument', action='store_true')
    args = parser.parse_args()
    if args.window < 1 or sys.byteorder != 'little':
        parser.error('positive window and little-endian Linux host required')
    args.output.mkdir(parents=True, exist_ok=False)
    manifest = json.loads(args.manifest.read_text())
    rows = [tuple(map(int, line.split())) for line in Path(manifest['request_types']).read_text().splitlines()]
    if any(len(r) != 4 for r in rows):
        raise ValueError('invalid trace row')
    selected = schedule(rows, args.schedule, args.window)
    opened = bounded.validate(manifest)
    try:
        mapping = {int(old): opened[path] for old, path in manifest['fd_map'].items() if path in opened}
        if set(r[0] for r in rows) - set(mapping):
            raise ValueError('trace descriptor outside manifest')
        paths = list(opened)
        before, _ = residency(paths)
        save(args.output / 'resident-before.json', before)
        for fd in opened.values():
            os.fsync(fd)
            os.posix_fadvise(fd, 0, 0, os.POSIX_FADV_DONTNEED)
        after, resident_bytes = residency(paths)
        save(args.output / 'resident-after-eviction.json', after)
        if resident_bytes != 0:
            raise RuntimeError(f'file cache was not empty: {resident_bytes} bytes')

        def write_schedule(name, values):
            path = args.output / name
            with path.open('xb') as file:
                for fd, off, size, kind in values:
                    file.write(struct.pack('<iIQQ', mapping[fd], kind, off, size))
            return path

        binary = write_schedule('schedule.bin', selected)
        native_mode = 'normal' if args.mode == 'warm' else args.mode

        def run_probe(path, latency):
            cmd = [str(args.probe.resolve()), str(path), native_mode, str(args.cpu), str(latency),
                   *map(str, opened.values())]
            result = subprocess.run(cmd, capture_output=True, text=True,
                                    pass_fds=tuple(opened.values()), timeout=120)
            if result.returncode:
                raise RuntimeError(f'native probe failed ({result.returncode}): {result.stderr}')
            return json.loads(result.stdout)

        if args.mode == 'warm':
            warmup = run_probe(write_schedule('warmup.bin', rows), '-')
            save(args.output / 'warmup.json', warmup)
        ready, ready_bytes = residency(paths)
        save(args.output / 'resident-before-measurement.json', ready)
        save(args.output / 'host-before.json', host())
        latency = args.output / 'durations.bin' if args.instrument else '-'
        result = run_probe(binary, latency)
        save(args.output / 'host-after.json', host())
        final, final_bytes = residency(paths)
        save(args.output / 'resident-after-measurement.json', final)
        # Recheck file identity and absence of fixture processes after the read.
        checked = bounded.validate(manifest)
        for fd in checked.values():
            os.close(fd)
        result.update({'mode': args.mode, 'schedule': args.schedule, 'window': args.window,
                       'cpu': args.cpu, 'source': manifest['source'],
                       'resident_after_eviction_bytes': resident_bytes,
                       'resident_before_measurement_bytes': ready_bytes,
                       'resident_after_measurement_bytes': final_bytes,
                       'manifest_sha256': hashlib.sha256(args.manifest.read_bytes()).hexdigest(),
                       'trace_sha256': hashlib.sha256(Path(manifest['request_types']).read_bytes()).hexdigest(),
                       'ordered_requests_sha256': bounded.request_hash(selected),
                       'selected_page_multiset_sha256': bounded.request_hash([
                           (f, off, bounded.PAGE, 0) for (f, off), count
                           in sorted(bounded.page_counts(selected).items()) for _ in range(count)]),
                       'probe_sha256': hashlib.sha256(args.probe.read_bytes()).hexdigest(),
                       'driver_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest()})
        assert result['requests'] == len(rows)
        assert result['requested_bytes'] == sum(r[2] for r in rows)
        save(args.output / 'result.json', result)
        print(json.dumps(result), flush=True)
    finally:
        for fd in opened.values():
            os.close(fd)


if __name__ == '__main__':
    main()
