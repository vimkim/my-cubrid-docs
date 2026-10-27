#!/usr/bin/env python3
"""Read-only offline controls; this does not execute SQL or implement buffer-pool batching.

The manifest must identify a stopped, dedicated fixture and every permanent volume.
Each request-types row is: captured_fd, byte_offset, byte_length, page_type.
ptype 2/14 is specific to the pinned CUBRID revision recorded in the manifest.
"""
import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import resource
import stat
import subprocess
import time

PAGE = 16384
CAP = 1048576

def page_counts(rows):
    counts = Counter()
    for fd, off, size, _ in rows:
        if off % PAGE or size % PAGE:
            raise ValueError('unaligned request')
        counts.update((fd, pos) for pos in range(off, off + size, PAGE))
    return counts

def request_hash(rows):
    return hashlib.sha256(''.join(f'{f}\t{o}\t{n}\n' for f,o,n,_ in rows).encode()).hexdigest()

def plan(rows, policy, window, gap):
    if policy in ('captured', 'window', 'global'):
        width = 1 if policy == 'captured' else len(rows) if policy == 'global' else window
        batches = [rows[i:i+width] for i in range(0, len(rows), width)]
    else:
        batches, batch, heaps = [], [], 0
        for row in rows:
            boundary = (policy == 'heap-batch' and row[3] == 2 and heaps >= window)
            boundary |= policy == 'oos-run' and bool(batch) and ((row[3] == 14) != (batch[-1][3] == 14))
            if boundary:
                batches.append(batch)
                batch, heaps = [], 0
            batch.append(row)
            heaps += row[3] == 2
        if batch:
            batches.append(batch)
    emitted, batch_ends = [], []
    for batch in batches:
        if policy == 'heap-batch':
            ordered = [r for r in batch if r[3] != 14] + sorted(r for r in batch if r[3] == 14)
        elif policy in ('window', 'global') or (policy == 'oos-run' and batch[0][3] == 14):
            ordered = sorted(batch)
        else:
            ordered = batch
        issued = []
        for fd, off, size, kind in ordered:
            if gap >= 0 and issued:
                f, start, length, old_kind = issued[-1]
                if f == fd and 0 <= off-start-length <= gap and off+size-start <= CAP:
                    issued[-1] = (f, start, off+size-start, old_kind)
                    continue
            issued.append((fd, off, size, kind))
        emitted.extend(issued)
        batch_ends.append(len(emitted))
    selected, actual = page_counts(rows), page_counts(emitted)
    if selected - actual:
        raise ValueError('lost selected page occurrences')
    if gap <= 0 and selected != actual:
        raise ValueError('changed page multiplicity without gap reads')
    extra = actual - selected
    stats = {'batch_count':len(batches), 'max_batch_input_requests':max(map(len,batches)),
             'max_batch_selected_bytes':max(sum(r[2] for r in b) for b in batches),
             'max_syscall_bytes':max(r[2] for r in emitted),
             'selected_requests':len(rows), 'issued_requests':len(emitted),
             'selected_bytes':sum(r[2] for r in rows), 'issued_bytes':sum(r[2] for r in emitted),
             'extra_page_occurrences':sum(extra.values()),
             'selected_page_multiset_sha256':request_hash([(f,o,PAGE,0) for (f,o),n in sorted(selected.items()) for _ in range(n)]),
             'issued_page_multiset_sha256':request_hash([(f,o,PAGE,0) for (f,o),n in sorted(actual.items()) for _ in range(n)]),
             'emitted_requests_sha256':request_hash(emitted)}
    return emitted, batch_ends, stats

def validate(manifest):
    install = str(Path(manifest['install']).resolve()) + '/'
    for proc in Path('/proc').iterdir():
        if not proc.name.isdigit():
            continue
        try:
            if str((proc/'exe').resolve()).startswith(install):
                raise RuntimeError('fixture installation has an active process: ' + proc.name)
        except (FileNotFoundError, PermissionError, ProcessLookupError):
            pass
    root = Path(manifest['volume_root']).resolve()
    opened = {}
    try:
        for item in manifest['volumes']:
            path = Path(item['path'])
            st = path.lstat()
            if (path.parent.resolve() != root or not stat.S_ISREG(st.st_mode)
                or st.st_uid != os.getuid() or st.st_nlink != 1
                or [st.st_dev,st.st_ino,st.st_size] != [item['dev'],item['ino'],item['size']]):
                raise RuntimeError('volume identity/scope mismatch: ' + str(path))
            fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
            current = os.fstat(fd)
            if (current.st_dev,current.st_ino,current.st_size) != (st.st_dev,st.st_ino,st.st_size):
                os.close(fd)
                raise RuntimeError('volume changed while opening')
            opened[str(path)] = fd
        return opened
    except BaseException:
        for fd in opened.values():
            os.close(fd)
        raise

def proc_io():
    return {k:int(v) for k,v in (line.split(':',1) for line in Path('/proc/self/io').read_text().splitlines())}

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--policy', choices=['captured','window','global','heap-batch','oos-run'], default='captured')
    parser.add_argument('--window', type=int, default=128)
    parser.add_argument('--gap', type=int, choices=[-1,0,PAGE], default=-1)
    parser.add_argument('--content-only', action='store_true')
    parser.add_argument('--cpu', type=int, default=16)
    args = parser.parse_args()
    if args.window < 1:
        parser.error('window must be positive')
    os.sched_setaffinity(0,{args.cpu})
    args.output.mkdir(parents=True,exist_ok=False)
    manifest=json.loads(args.manifest.read_text())
    rows=[tuple(map(int,line.split())) for line in Path(manifest['request_types']).read_text().splitlines()]
    planning_start=time.monotonic()
    emitted,ends,stats=plan(rows,args.policy,args.window,args.gap)
    planning_seconds=time.monotonic()-planning_start
    opened=validate(manifest)
    try:
        captured={int(old):opened[path] for old,path in manifest['fd_map'].items() if path in opened}
        if set(r[0] for r in rows)-set(captured):
            raise ValueError('captured descriptor outside allowed volumes')
        if args.content_only:
            digest=hashlib.sha256()
            for fd,off,size,_ in sorted(rows):
                data=os.pread(captured[fd],size,off)
                if len(data)!=size:
                    raise RuntimeError('short content read')
                digest.update(f'{fd}:{off}:{size}:'.encode())
                digest.update(data)
            result={'content_sha256':digest.hexdigest(),'selected_bytes':stats['selected_bytes']}
        else:
            filenames=list(opened)
            resident_cmd=['fincore','--json','--bytes','--output','FILE,SIZE,RES']+filenames
            for fd in opened.values():
                os.fsync(fd)
                os.posix_fadvise(fd,0,0,os.POSIX_FADV_DONTNEED)
            residency=json.loads(subprocess.check_output(resident_cmd,text=True))
            (args.output/'residency.json').write_text(json.dumps(residency,indent=2)+'\n')
            resident=sum(int(row['res']) for row in residency['fincore'])
            if resident>16*1024*1024:
                raise RuntimeError('file cache advice did not take effect')
            calls=[(captured[f],o,n) for f,o,n,_ in emitted]
            before=proc_io();load=os.getloadavg();cpu=time.process_time();start=time.monotonic()
            first_batch_seconds=None
            for number,(fd,off,size) in enumerate(calls,1):
                data=os.pread(fd,size,off)
                if len(data)!=size:
                    raise RuntimeError('short replay read')
                if number==ends[0]:
                    first_batch_seconds=time.monotonic()-start
            elapsed=time.monotonic()-start;cpu=time.process_time()-cpu;after=proc_io()
            result={**stats,'elapsed_seconds':elapsed,'cpu_seconds':cpu,'planning_seconds':planning_seconds,
                    'first_batch_io_seconds':first_batch_seconds,'resident_after_bytes':resident,
                    'io_delta':{k:after[k]-before[k] for k in before},'load':load,
                    'python_peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
                    'policy':args.policy,'window':args.window,'gap':args.gap}
        result.update({'source':manifest['source'],'manifest':str(args.manifest),
                       'manifest_sha256':hashlib.sha256(args.manifest.read_bytes()).hexdigest(),
                       'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()})
        (args.output/'result.json').write_text(json.dumps(result,indent=2)+'\n')
        print(json.dumps(result))
    finally:
        for fd in opened.values():
            os.close(fd)

if __name__=='__main__':
    main()
