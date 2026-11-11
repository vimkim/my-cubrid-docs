#!/usr/bin/env python3
"""Summarize log_traffic_churn.py results.csv per build and mode.

Per (build, mode): per-cycle peak pages (largest of the four snapshots of a cycle; exact for stage 2 because
its page count never shrinks, a lower bound for stage 1), the peak of cycle 1 and of cycles 2+, the drain
time and the number of fillers of the UPDATE and DELETE drains in cycles 2+, and the reserved sectors of c.

usage: logtraffic_summary.py results.csv
"""
import csv
import statistics
import sys
from collections import defaultdict

PAGES = ("pages_peak_update", "pages_after_update_drain", "pages_after_delete_drain", "pages_after_reinsert")


def med(xs):
    return f"{statistics.median(xs):g} ({min(xs):g}-{max(xs):g})" if xs else "n/a"


def main(path):
    pages = defaultdict(lambda: defaultdict(dict))
    other = defaultdict(list)
    for r in csv.DictReader(open(path)):
        if r["item"] != "logtraffic":
            continue
        mode, _, name = r["metric"].partition("_")
        v, cy, key = float(r["value"]), int(r["iter"]), (r["label"], mode)
        if name in PAGES:
            pages[key][(r["round"], cy)][name] = v
        elif name == "sectors_c":
            other[(key, "sectors")].append(v)
        elif cy >= 2:
            other[(key, name)].append(v)
    print("| build | mode | cycle 1 peak | cycle 2+ peak | sectors c | UPDATE drain s (c2+) | UPDATE drain fillers | DELETE drain s | DELETE drain fillers |")
    print("| --- | --- | --- | --- | --- | --- | --- | --- | --- |")
    for key in sorted(pages):
        peaks = {k: max(d.values()) for k, d in pages[key].items()}
        c1 = [p for (rep, cy), p in peaks.items() if cy == 1]
        c2 = [p for (rep, cy), p in peaks.items() if cy >= 2]
        print(f"| {key[0]} | {key[1]} | {med(c1)} | {med(c2)} | {med(other[(key, 'sectors')])} | "
              f"{med(other[(key, 'update_drain_s')])} | {med(other[(key, 'update_drain_fillers')])} | "
              f"{med(other[(key, 'delete_drain_s')])} | {med(other[(key, 'delete_drain_fillers')])} |")


if __name__ == "__main__":
    main(sys.argv[1])
