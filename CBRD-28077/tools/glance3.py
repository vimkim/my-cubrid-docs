#!/usr/bin/env python3
"""CBRD-28077 run 3: at-a-glance matrix and compact per-scenario tables (Markdown).

Usage: python3 glance3.py RUN_DIR
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import analyze2 as a

READS = {'S1', 'S2', 'S3n', 'S3w'}
MOVED = (4096, 8192, 65536)


def ratio(cells, s, m, sc, v, name='ins'):
    x, b = a.stat(cells, (s, m, sc, v), name), a.stat(cells, (s, m, sc, 'develop'), name)
    return x['med'] / b['med'] if x and b and b['med'] else None


def rng(vals):
    vals = [v for v in vals if v is not None]
    if not vals:
        return '-'
    lo, hi = min(vals), max(vals)
    return f'×{lo:.2f}' if abs(hi - lo) < 0.005 else f'×{lo:.2f}~{hi:.2f}'


def main():
    cells, *_ = a.load(sys.argv[1])
    out = ['### 한눈에 보기: 값이 행 밖으로 나가는 크기(4 KB, 8 KB, 64 KB)', '',
           '서버 명령어 수(drain 포함)의 develop 대비 비율 범위다. 범위는 세 크기와 io·warm 두 조건, 즉 최대 6개 중앙값의 최소~최대다.', '',
           '| 시나리오 | develop e64a (대조) | OOS | Sidecar | Inner Table |', '|---|---|---|---|---|']
    for sc in a.SCEN:
        out.append(f'| {sc} {a.LABEL[sc]} | ' + ' | '.join(
            rng([ratio(cells, s, m, sc, v) for s in MOVED for m in ('io', 'warm')])
            for v in ('develop-e64a', 'oos', 'sidecar', 'inner')) + ' |')
    out += ['', '### 한눈에 보기: 기능 미사용(100 B)', '',
            '| 시나리오 | develop e64a (대조) | OOS | Sidecar | Inner Table |', '|---|---|---|---|---|']
    for sc in a.SCEN:
        out.append(f'| {sc} {a.LABEL[sc]} | ' + ' | '.join(
            rng([ratio(cells, 100, m, sc, v) for m in ('io', 'warm')])
            for v in ('develop-e64a', 'oos', 'sidecar', 'inner')) + ' |')
    out.append('')
    for sc in a.SCEN:
        io_name = 'osr' if sc in READS else 'osw'
        io_label = 'OS 읽기' if sc in READS else 'OS 쓰기'
        out += [f'#### {sc} {a.LABEL[sc]}', '',
                f'| 값 | 조건 | OOS | Sidecar | Inner Table | develop 절대값 (명령어 / {io_label} / 시간) |', '|---|---|---|---|---|---|']
        for s in MOVED:
            for m in ('io', 'warm'):
                b = a.stat(cells, (s, m, sc, 'develop'), 'ins')
                if not b:
                    continue
                bio, bw = a.stat(cells, (s, m, sc, 'develop'), io_name), a.stat(cells, (s, m, sc, 'develop'), 'wall')
                parts = []
                for v in ('oos', 'sidecar', 'inner'):
                    r, rio = ratio(cells, s, m, sc, v), ratio(cells, s, m, sc, v, io_name)
                    if r is None:
                        parts.append('-')
                        continue
                    t = f'×{r:.2f}'
                    if r >= 1.5 or r <= 0.67:
                        t = f'**{t}**'
                    if rio is not None and m == 'io' or (rio is not None and sc not in READS):
                        t += f' / {io_label} ×{rio:.2f}'
                    parts.append(t)
                out.append(f'| {s // 1024} KB | {m} | ' + ' | '.join(parts) +
                           f" | {a.fmt(b['med'], 'ins')} / {a.fmt(bio['med'], io_name) if bio else '-'} / {a.fmt(bw['med'], 'wall')} |")
        out.append('')
    print('\n'.join(out))


if __name__ == '__main__':
    main()
