#!/usr/bin/env python3
"""CBRD-28077 run 2: one Markdown "card" per scenario, comparing every build across sizes and modes.

Usage: python3 cards2.py RUN_DIR > cards.md

Each card has one row per (value size, mode). Cells: server instructions as a ratio to develop a7f220d5d7,
with the repeat spread in brackets, then the scenario's I/O metric (OS read bytes for reads, OS write bytes
for writes) as a ratio. A final column gives develop's absolute numbers so ratios can be scaled back.
"""

import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import analyze2 as a  # noqa: E402

READS = {'S1', 'S2', 'S3n', 'S3w'}
ORDER = ('S1', 'S2', 'S3n', 'S3w', 'S4', 'S5', 'S6', 'S7', 'S8b', 'S8s', 'S9', 'S11', 'S12')


def cell(cells, key, base_key, name):
    x, b = a.stat(cells, key, name), a.stat(cells, base_key, name)
    if not x or not b or not b['med']:
        return None, None
    return x['med'] / b['med'], x['spread']


def main():
    run = sys.argv[1]
    cells, *_ = a.load(run)
    sizes = sorted({k[0] for k in cells})
    out = []
    for sc in ORDER:
        io_name = 'osr' if sc in READS else 'osw'
        io_label = 'OS 읽기' if sc in READS else 'OS 쓰기'
        rows = []
        for s in sizes:
            for mode in ('io', 'warm'):
                base = (s, mode, sc, 'develop')
                if not cells.get(base):
                    continue
                parts = []
                for v in a.BUILDS[1:]:
                    r, sp = cell(cells, (s, mode, sc, v), base, 'ins')
                    rio, _ = cell(cells, (s, mode, sc, v), base, io_name)
                    if r is None:
                        parts.append('-')
                        continue
                    flag = ' **' if (v != 'develop-e64a' and (r >= 1.5 or r <= 0.67)) else ''
                    io_txt = f' · {io_label} ×{rio:.2f}' if rio is not None else ''
                    parts.append(f'{flag.strip()}×{r:.2f}{flag.strip()} ({sp:.2f}){io_txt}')
                d = a.stat(cells, base, 'ins')
                dio = a.stat(cells, base, io_name)
                dw = a.stat(cells, base, 'wall')
                absd = f"{a.fmt(d['med'], 'ins')} 명령어, {a.fmt(dio['med'], io_name) if dio else '-'}, {a.fmt(dw['med'], 'wall')}"
                rows.append(f'| {s} B | {mode} | ' + ' | '.join(parts) + f' | {absd} |')
        if not rows:
            continue
        out += [f'#### {sc} {a.LABEL[sc]}', '',
                '| 값 | 조건 | develop-e64a | OOS | Sidecar | Inner Table | develop 절대값 (명령어, ' + io_label + ', 시간) |',
                '|---|---|---|---|---|---|---|'] + rows + ['']
    print('\n'.join(out))


if __name__ == '__main__':
    main()
