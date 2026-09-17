#!/usr/bin/env python3
"""Sample one campaign invocation's own CPU, memory and storage (campaign ticket 17).

    resource_sampler.py --command CMD [ARG ...] --out FILE [--interval SECONDS]
                        [--storage DIR ...] [--label TEXT]

Ticket 17 criterion 5 asks that the resource ceilings -- 8 logical CPUs, 16 GiB of memory and
100 GiB of working storage under /home (decision ticket 08) -- are "checked against measured
peak usage of the representative cases". The ceilings are aggregate campaign limits, so what
has to be measured is the invocation's own footprint and not the host's, which on this shared
machine carries other people's work.

The sampler therefore measures the process tree it starts, and nothing else: every interval it
walks /proc, takes the transitive descendants of the command it launched, and sums their
resident memory and their utime+stime deltas. CPU is reported in logical CPUs (1.0 = one core
saturated), which is the unit the 8-CPU ceiling is in. Storage is the disk usage (`st_blocks`,
the measure ticket 44 finding F7 established the 100 GiB cap is in) of the directories named
with --storage, sampled before and after and at every interval.

Two limits of the method, recorded rather than hidden:
  * a process that lives and dies between two samples is not seen, so peaks are lower bounds;
  * the campaign runs CTP under `unshare --pid`, whose children are still descendants of this
    command in the parent PID namespace, so they are seen -- but a process that reparents to
    init inside that namespace after its parent exits is lost from the tree. The sampler
    reports how many samples it took so a suspiciously small count is visible.

Standard library only.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import threading
import time
from pathlib import Path

CLK_TCK = os.sysconf("SC_CLK_TCK")
PAGE_SIZE = os.sysconf("SC_PAGE_SIZE")


def proc_table():
    """pid -> (ppid, rss_bytes, cpu_ticks) for every process this user can read."""
    table = {}
    for entry in os.listdir("/proc"):
        if not entry.isdigit():
            continue
        try:
            with open(f"/proc/{entry}/stat", "rb") as fh:
                raw = fh.read().decode("utf-8", "replace")
            rparen = raw.rindex(")")
            fields = raw[rparen + 2:].split()
            ppid = int(fields[1])
            utime, stime = int(fields[11]), int(fields[12])
            rss_pages = int(fields[21])
        except (OSError, ValueError, IndexError):
            continue
        table[int(entry)] = (ppid, rss_pages * PAGE_SIZE, utime + stime)
    return table


def descendants(table, root):
    children = {}
    for pid, (ppid, _, _) in table.items():
        children.setdefault(ppid, []).append(pid)
    seen, stack = set(), [root]
    while stack:
        pid = stack.pop()
        if pid in seen:
            continue
        seen.add(pid)
        stack.extend(children.get(pid, ()))
    return seen


def disk_usage(paths):
    total = 0
    for p in paths:
        root = Path(p)
        if not root.exists():
            continue
        for f in root.rglob("*"):
            try:
                if f.is_file() and not f.is_symlink():
                    total += f.stat().st_blocks * 512
            except OSError:
                pass
    return total


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", required=True)
    ap.add_argument("--interval", type=float, default=0.5)
    ap.add_argument("--storage", action="append", default=[])
    ap.add_argument("--label", default="")
    ap.add_argument("--command", nargs=argparse.REMAINDER, required=True)
    args = ap.parse_args(argv)
    if not args.command:
        ap.error("--command needs a command")

    samples = []
    stop = threading.Event()
    storage_before = disk_usage(args.storage)
    started = time.time()
    proc = subprocess.Popen(args.command)

    def sample_loop():
        # A plain sum of the tree's tick counters is not monotonic: when a process exits its
        # counter leaves the sum and the next delta goes negative. Ticks are therefore kept per
        # pid, and a pid that disappears keeps contributing its last reading through `retired`.
        live, retired, prev_ticks, prev_t = {}, 0, None, None
        while not stop.is_set():
            table = proc_table()
            pids = descendants(table, proc.pid)
            rss = sum(table[p][1] for p in pids if p in table)
            seen = {p: table[p][2] for p in pids if p in table}
            for gone in set(live) - set(seen):
                retired += live.pop(gone)
            live.update(seen)
            ticks = retired + sum(live.values())
            now = time.time()
            cpus = None
            if prev_ticks is not None and now > prev_t:
                cpus = round(max(0.0, ticks - prev_ticks) / CLK_TCK / (now - prev_t), 3)
            samples.append({
                "t": round(now - started, 2),
                "processes": len(pids),
                "rss_bytes": rss,
                "cpus": cpus,
                "storage_bytes": disk_usage(args.storage) if args.storage else None,
            })
            prev_ticks, prev_t = ticks, now
            stop.wait(args.interval)

    thread = threading.Thread(target=sample_loop, daemon=True)
    thread.start()
    rc = proc.wait()
    stop.set()
    thread.join(timeout=5)
    ended = time.time()
    storage_after = disk_usage(args.storage)

    cpu_values = [s["cpus"] for s in samples if s["cpus"] is not None]
    rss_values = [s["rss_bytes"] for s in samples]
    store_values = [s["storage_bytes"] for s in samples if s["storage_bytes"] is not None]
    result = {
        "label": args.label,
        "command": args.command,
        "exit_status": rc,
        "started_at": time.strftime("%Y-%m-%dT%H:%M:%S%z", time.localtime(started)),
        "ended_at": time.strftime("%Y-%m-%dT%H:%M:%S%z", time.localtime(ended)),
        "wall_seconds": round(ended - started, 2),
        "interval_seconds": args.interval,
        "sample_count": len(samples),
        "peak_processes": max((s["processes"] for s in samples), default=0),
        "peak_rss_bytes": max(rss_values, default=0),
        "peak_rss_gib": round(max(rss_values, default=0) / 1024 ** 3, 3),
        "peak_cpus": max(cpu_values, default=0.0),
        "mean_cpus": round(sum(cpu_values) / len(cpu_values), 3) if cpu_values else 0.0,
        "storage_roots": args.storage,
        "storage_before_bytes": storage_before,
        "storage_after_bytes": storage_after,
        "storage_delta_gib": round((storage_after - storage_before) / 1024 ** 3, 3),
        "storage_peak_gib": round(max(store_values + [storage_after]) / 1024 ** 3, 3) if (store_values or storage_after) else 0.0,
        "measure": "disk usage (st_blocks * 512), the measure ticket 44 F7 established the 100 GiB cap is in",
        "samples": samples,
    }
    Path(args.out).write_text(json.dumps(result, indent=2))
    print(f"[resource_sampler] {args.label or args.command[0]}: {result['wall_seconds']} s, "
          f"peak {result['peak_cpus']} cpu / {result['peak_rss_gib']} GiB rss / "
          f"{result['storage_delta_gib']} GiB storage delta, {len(samples)} samples, exit {rc}", file=sys.stderr)
    return rc


if __name__ == "__main__":
    sys.exit(main())
