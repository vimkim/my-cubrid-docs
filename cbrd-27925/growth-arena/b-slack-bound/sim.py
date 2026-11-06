#!/usr/bin/env python3
"""Count growth-path reclaim work per design under steady churn at constant live data.

One record per page, as in the a01 snapshot TC (~10.7KB records). Page kinds:
  used     holds a record
  visible  empty and in the bestspace cache: vacuum's oos_delete_chain calls oos_stats_update,
           so an insert takes it through oos_find_best_page and never reaches the grow path
  hidden   empty and not in the cache: emptied by an INSERT rollback (oos_rv_redo_delete removes
           the page from bestspace), or evicted from the cache. Only a growth-path reclaim frees it
  free     deallocated, inside a reserved sector; file_alloc takes it before reserving a sector

Each step: vacuum deletes one random record; the fast path frees the page with probability
`fast`, else the page stays empty and is hidden with probability `hide`. Then one insert runs;
with probability `rb` an extra insert runs first and rolls back, leaving a hidden empty page.
An insert takes a visible empty page if any; otherwise it grows: the design may reclaim one
page, then file_alloc takes a free page or appends a new one.

Designs:
  current   d52b1889e: armed while any chain delete is not settled by a full lap; the lap walks
            from the cursor to the next empty page, or the whole file when there is none
  set K     exact emptied-page set; reclaims one member when the set holds more than K
  count K   exact counter, no VPIDs; when it exceeds K the cursor lap walks to the next empty page
  count e   as count, with K = max(64, e * pages)
Crashes and concurrency are not simulated here; TLC covers them.
"""
import bisect
import math
import random


class File:
    def __init__(self, live):
        self.kind = ["used"] * live
        self.used = list(range(live))
        self.pos = {p: p for p in range(live)}
        self.visible, self.hidden, self.free = set(), set(), []
        self.empties = []  # sorted visible | hidden, for the cursor lap
        self.cursor = 0
        self.peak = live

    def size(self):
        return len(self.kind)

    def take_used(self, rng):
        i = rng.randrange(len(self.used))
        p = self.used[i]
        last = self.used.pop()
        if last != p:
            self.used[i] = last
            self.pos[last] = i
        del self.pos[p]
        return p

    def put_used(self, p):
        self.kind[p] = "used"
        self.pos[p] = len(self.used)
        self.used.append(p)

    def make_empty(self, p, kind):
        self.kind[p] = kind
        (self.visible if kind == "visible" else self.hidden).add(p)
        bisect.insort(self.empties, p)

    def leave_empty(self, p):
        (self.visible if self.kind[p] == "visible" else self.hidden).discard(p)
        del self.empties[bisect.bisect_left(self.empties, p)]

    def reclaim(self, p):
        self.leave_empty(p)
        self.kind[p] = "free"
        self.free.append(p)

    def lap(self):
        """Pages a cursor lap examines before it finds an empty page, and that page (or None)."""
        if not self.empties:
            return self.size(), None
        i = bisect.bisect_right(self.empties, self.cursor)
        p = self.empties[i] if i < len(self.empties) else self.empties[0]
        dist = p - self.cursor if p > self.cursor else p + self.size() - self.cursor
        return dist, p

    def alloc(self):
        if self.free:
            return self.free.pop()
        self.kind.append("free")
        self.peak = max(self.peak, self.size())
        return self.size() - 1


def run(design, k, eps, live, steps, fast, hide, rb, seed):
    rng = random.Random(seed)
    f = File(live)
    pending = 0
    st = {"grows": 0, "reclaim_grows": 0, "examined": 0, "max_exam": 0}

    def grow():
        nonlocal pending
        st["grows"] += 1
        exam, victim = 0, None
        tracked = len(f.empties)
        if design == "current":
            if pending > 0:
                exam, victim = f.lap()
                if victim is None:
                    pending = 0
        elif design == "set":
            if tracked > k:
                exam, victim = 1, next(iter(f.hidden or f.visible))
        elif design == "count":
            kk = max(k, int(eps * f.size())) if eps else k
            if tracked > kk:
                exam, victim = f.lap()
        if victim is not None:
            f.reclaim(victim)
            f.cursor = victim
            st["reclaim_grows"] += 1
        st["examined"] += exam
        st["max_exam"] = max(st["max_exam"], exam)
        return f.alloc()

    def insert():
        if f.visible:
            p = next(iter(f.visible))
            f.leave_empty(p)
        else:
            p = grow()
        return p

    for _ in range(steps):
        p = f.take_used(rng)
        pending += 1
        if rng.random() < fast:
            f.kind[p] = "free"
            f.free.append(p)
        else:
            f.make_empty(p, "hidden" if rng.random() < hide else "visible")
        if rng.random() < rb:
            q = insert()
            pending += 1
            f.make_empty(q, "hidden")
        f.put_used(insert())
    return st, f


def main():
    live, steps, seed = 4096, 200_000, 7
    loads = [
        ("vacuum only, fast path 0.9", dict(fast=0.9, hide=0.0, rb=0.0)),
        ("rollback 5%, fast path 0.9", dict(fast=0.9, hide=0.0, rb=0.05)),
        ("fast path 0.5, half the misses hidden", dict(fast=0.5, hide=0.5, rb=0.0)),
        ("no fast path, all hidden", dict(fast=0.0, hide=1.0, rb=0.0)),
    ]
    designs = [("current", "current", 0, 0), ("cand (set K=0)", "set", 0, 0), ("set K=8", "set", 8, 0),
               ("set K=64", "set", 64, 0), ("count K=0", "count", 0, 0), ("count K=64", "count", 64, 0),
               ("count e=0.1", "count", 64, 0.1)]
    print(f"live={live} records (one per page), steps={steps}, seed={seed}")
    print("| workload | design | grows | grows with reclaim | reclaims saved vs cand | mean pages examined "
          "per grow | max | peak pages | peak sectors |")
    print("| --- | --- | --- | --- | --- | --- | --- | --- | --- |")
    for wname, kw in loads:
        base = None
        for dname, design, k, eps in designs:
            st, f = run(design, k, eps, live, steps, seed=seed, **kw)
            if design == "set" and k == 0:
                base = st["reclaim_grows"]
            saved = "" if base is None or design == "current" else base - st["reclaim_grows"]
            g = st["grows"]
            print(f"| {wname} | {dname} | {g} | {st['reclaim_grows']} ({100 * st['reclaim_grows'] / max(g, 1):.1f}%) "
                  f"| {saved} | {st['examined'] / max(g, 1):.2f} | {st['max_exam']} | {f.peak} "
                  f"| {math.ceil(f.peak / 64)} |")


if __name__ == "__main__":
    main()
