#!/usr/bin/env python3
"""CBRD-27230 reuse re-measurement: aggregate results-*.jsonl of oosbench_reuse.py.

Usage: python3 analyze_reuse.py RUN_DIR [--out tables.md] [--json summary.json]

Cells are medians over the repeats of one (size, mode, scenario, build); ratios divide the reuse build by
reuse-base (b049fa155c) and by develop (a7f220d5d7). "spread" is (max - min) / median.
"""
import argparse
import collections
import json
import os
import sys
from pathlib import Path

os.environ['BUILDS'] = 'develop,reuse-base,reuse'
sys.path.insert(0, str(Path(__file__).resolve().parent))
import analyze2 as a  # noqa: E402

B = ('develop', 'reuse-base', 'reuse')
HEAD = ('S5', 'S8s', 'S6', 'S7', 'S8b')
ALL = a.SCEN


def ratio(x, y):
    return x / y if x is not None and y else None


def r2(v):
    return '-' if v is None else f'x{v:.2f}'


def rows_of(run_dir):
    out = []
    for f in sorted(Path(run_dir).glob('results-*.jsonl')):
        out += [json.loads(l) for l in open(f)]
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('run_dir')
    ap.add_argument('--out')
    ap.add_argument('--json')
    args = ap.parse_args()
    cells, checks, sums, evidence, failed = a.load(args.run_dir)
    raw = rows_of(args.run_dir)
    sizes = sorted({k[0] for k in cells if k[1] in ('io', 'warm')})
    md, js = [], {}

    def med(s, m, sc, v, name='ins'):
        st = a.stat(cells, (s, m, sc, v), name)
        return st['med'] if st else None

    def sp(s, m, sc, v, name='ins'):
        st = a.stat(cells, (s, m, sc, v), name)
        return st['spread'] if st else None

    md += ['## 1. Server instructions (drain included), median of the repeats', '',
           'reuse/base and reuse/dev divide the reuse build by reuse-base and by develop. The three builds ran at the same time.', '']
    for s in sizes:
        md += [f'### {s} B', '',
               '| scenario | mode | develop | reuse-base | reuse | reuse/base | reuse/dev | base/dev | spread dev / base / reuse |',
               '|---|---|---:|---:|---:|---:|---:|---:|---|']
        for sc in ALL:
            for m in ('io', 'warm'):
                v = {b: med(s, m, sc, b) for b in B}
                if not any(v.values()):
                    continue
                if sc in ('S11', 'S12') and m == 'io':
                    continue
                rb, rd, bd = ratio(v['reuse'], v['reuse-base']), ratio(v['reuse'], v['develop']), ratio(v['reuse-base'], v['develop'])
                md.append(f'| {sc} {a.LABEL[sc]} | {m} | ' + ' | '.join(a.fmt(v[b], 'ins') if v[b] else '-' for b in B)
                          + f' | {r2(rb)} | {r2(rd)} | {r2(bd)} | '
                          + ' / '.join('-' if sp(s, m, sc, b) is None else f'{sp(s, m, sc, b):.2f}' for b in B) + ' |')
                js[f'{s}/{m}/{sc}'] = {'ins': v, 'reuse/base': rb, 'reuse/dev': rd, 'base/dev': bd}
        md.append('')

    md += ['## 2. Per-repeat values of S5 and S8s (instructions incl. drain, G)', '',
           'S5 repeats run on the table in the state the previous repeat left it; rep 0 of warm is the first UPDATE after load.', '',
           '| size | mode | scenario | build | rep 0 | rep 1 | rep 2 |', '|---|---|---|---|---:|---:|---:|']
    for s in sizes:
        for sc in ('S5', 'S8s'):
            for m in ('warm', 'io'):
                for b in B:
                    recs = sorted(cells.get((s, m, sc, b), []), key=lambda r: r['rep'])
                    vals = [a.metric(r, 'ins') / 1e9 for r in recs]
                    md.append(f'| {s} | {m} | {sc} | {b} | ' + ' | '.join(f'{x:.2f}' for x in vals) + ' |')
    md.append('')

    md += ['## 3. S5 detail: other metrics, median', '',
           '| size | mode | build | instructions | cycles | data page fetches | OS write MiB | OS read MiB | wall s | drain s |',
           '|---|---|---|---:|---:|---:|---:|---:|---:|---:|']
    for s in sizes:
        for sc in ('S5', 'S8s'):
            for m in ('warm', 'io'):
                for b in B:
                    recs = cells.get((s, m, sc, b), [])
                    if not recs:
                        continue
                    drain = sorted(r.get('drain_seconds') or 0 for r in recs)[len(recs) // 2]
                    md.append(f'| {s} | {m} {sc} | {b} | {a.fmt(med(s, m, sc, b), "ins")} | {a.fmt(med(s, m, sc, b, "cycles"), "ins")} | '
                              f'{a.fmt(med(s, m, sc, b, "fetch"), "fetch")} | {med(s, m, sc, b, "osw") / 2**20:,.0f} | '
                              f'{med(s, m, sc, b, "osr") / 2**20:,.0f} | {med(s, m, sc, b, "wall"):.2f} | {drain:.1f} |')
    md.append('')

    pages = collections.defaultdict(dict)
    order = collections.defaultdict(list)
    for r in raw:
        if r['mode'] == 'pages':
            k = (r['size'], r['scenario'])
            pages[k][r['variant']] = (r['heap_pages'], r['oos_pages'], r['oos_recs'], r['heap_recs'])
            if k not in order[r['size']]:
                order[r['size']].append(k)
    md += ['## 4. Heap and OOS file pages after each measured step', '',
           'Each cell is "OOS user pages / OOS records"; heap pages in brackets. The record before a step is the "before" of that step. '
           'develop has no OOS file (heap pages only).', '']
    for s in sizes:
        md += [f'### {s} B', '', '| after | develop heap pages | reuse-base OOS pages / recs [heap] | reuse OOS pages / recs [heap] |',
               '|---|---:|---:|---:|']
        for k in order[s]:
            p = pages[k]
            d = p.get('develop')
            def cell(b):
                x = p.get(b)
                return '-' if not x else f'{x[1]:,} / {x[2]:,} [{x[0]:,}]'
            md.append(f'| {k[1]} | {"-" if not d else format(d[0], ",")} | {cell("reuse-base")} | {cell("reuse")} |')
        md.append('')

    md += ['## 5. Result checks across builds', '']
    bad = [(k, per) for k, per in sorted(checks.items()) if len(set(per.values())) > 1]
    md.append(f'- Measured statements with a digest and affected-row count: {len(checks)}; builds that disagree: {len(bad)}')
    for k, per in bad[:20]:
        md.append(f'  - {k}: {per}')
    sbad = [(k, per) for k, per in sorted(sums.items()) if len(set(per.values())) > 1]
    md.append(f'- Table checksums (count, sum(k), sum(id), sum(bit_length(big))) and wrong-length counts: {len(sums)}; builds that disagree: {len(sbad)}')
    for k, per in sbad[:20]:
        md.append(f'  - {k}: {per}')
    content = collections.defaultdict(dict)
    for r in raw:
        if r['mode'] == 'content':
            content[(r['size'], r['scenario'])][r['variant']] = tuple(r['values'] or ())
    cbad = [(k, per) for k, per in sorted(content.items()) if len(set(per.values())) > 1 or any(not v for v in per.values())]
    md.append(f'- Content checks (rows holding each written byte pattern): {len(content)} points; builds that disagree or returned nothing: {len(cbad)}')
    for k, per in cbad[:20]:
        md.append(f'  - {k}: {per}')
    badlen = [r for r in raw if r['mode'] == 'lencheck' and r.get('wrong_length_rows')]
    md.append(f'- Rows with a wrong big length: {sum(r["wrong_length_rows"] for r in badlen)}')
    md.append(f'- Builds present per check point: ' + ', '.join(sorted({v for per in checks.values() for v in per})))
    md += ['', '## 6. Failures', '']
    md += [f"- {r['size']} {r['variant']} {r['mode']} {r['scenario']}: "
           f"{r.get('failed') or r.get('error') or ('client_errors=' + str(r.get('client_errors')))}" for r in failed] or ['- none']
    md += ['', '## 7. Load average at each record (1 min)', '']
    for b in B:
        la = [r['loadavg'] for r in raw if r.get('variant') == b and 'loadavg' in r]
        if la:
            md.append(f'- {b}: min {min(la):.1f}, median {sorted(la)[len(la) // 2]:.1f}, max {max(la):.1f} ({len(la)} records)')
    text = '\n'.join(md) + '\n'
    if args.out:
        Path(args.out).write_text(text)
    else:
        print(text)
    if args.json:
        Path(args.json).write_text(json.dumps({'cells': js, 'bad_checks': len(bad), 'bad_sums': len(sbad), 'bad_content': len(cbad),
                                               'checks': len(checks), 'sums': len(sums), 'content': len(content),
                                               'failed': len(failed)}, indent=1, default=str))


if __name__ == '__main__':
    main()
