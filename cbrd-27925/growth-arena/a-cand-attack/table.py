#!/usr/bin/env python3
"""Print run.py results as Markdown: one compact line per row, or the full per-cell table.

Cells are cw, cW, Cw, CW (C = crashes, W = writes during grow).

Usage: python3 -I -B table.py RESULTS.json [RESULTS.json ...] [--full]
"""

import json
import sys

CELLS = [(False, False), (False, True), (True, False), (True, True)]


def cell_name(c, w):
    return ("C" if c else "c") + ("W" if w else "w")


def load(paths):
    rows = {}
    for p in paths:
        for r in json.load(open(p)):
            rows.setdefault(r["row"], {})[(r["crashes"], r["writes"])] = r
    return rows


def show(rows, key):
    return [str(rows[c][key]) if c in rows else "." for c in CELLS]


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    rows = load(args)
    if "--full" in sys.argv:
        print("| row | cell | safety | strict | worst R | cost/grow | extra | distinct states | secs |")
        print("| --- | --- | --- | --- | --- | --- | --- | --- | --- |")
        for name, cells in rows.items():
            for c in CELLS:
                if c not in cells:
                    continue
                r = cells[c]
                extra = ", ".join(f"{k}={v}" for k, v in r.items() if k.startswith(("cap_", "NoSet")))
                print(f"| {name} | {cell_name(*c)} | {r['safety']} | {r['strict']} | {r['max_R']} | {r['max_cost']} "
                      f"| {extra or '-'} | {r['states']} | {float(r['secs']):.0f} |")
        return
    print("| row | strict cw/cW/Cw/CW | worst R cw/cW/Cw/CW | cost cw/Cw | max states | max secs |")
    print("| --- | --- | --- | --- | --- | --- |")
    for name, cells in rows.items():
        states = max(int(r["states"]) for r in cells.values() if str(r["states"]).isdigit())
        secs = max(float(r["secs"]) for r in cells.values())
        cost = [str(cells[c]["max_cost"]) if c in cells else "." for c in (CELLS[0], CELLS[2])]
        print(f"| {name} | {'/'.join(show(cells, 'strict'))} | {'/'.join(show(cells, 'max_R'))} "
              f"| {'/'.join(cost)} | {states:,} | {secs:.0f} |")


if __name__ == "__main__":
    main()
