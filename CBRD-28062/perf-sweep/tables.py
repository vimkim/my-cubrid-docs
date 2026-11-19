"""Print the Markdown tables of the CBRD-28062 sweep report from summary.json and storage.json.

usage: tables.py summary.json storage.json
"""
import json, sys

LABELS = ('t0', 't5000', 't7000', 't10500', 't14500', 't16236')
HEAD = ' | '.join(f'{l[1:]}' for l in LABELS)
SIZE = {'w36': '4.6KB', 'w47': '6.0KB', 'w78': '9.9KB', 'w110': '13.8KB'}
summary = {tuple(r['key']): r['labels'] for r in json.load(open(sys.argv[1]))}
storage = json.load(open(sys.argv[2]))


def f(x): return '—' if x is None else f'{x:+.2f}%'
def ins(row, label): return row[label]['instructions']['change_pct_vs_base'] if label in row else None
def spread(row): return max(row[l]['instructions']['spread_pct'] for l in row)


def change_table(kind, cases, names, sizes=SIZE, metric='instructions'):
    print(f'| 값 | 질의 | base 명령어 | {HEAD} | 레이블 중 최대 spread |')
    print('|---|---|---:|' + '---:|' * len(LABELS) + '---:|')
    for t, size in sizes.items():
        for c in cases:
            row = summary.get((kind, t, c))
            if not row: continue
            print(f"| {size} | {names.get(c, c)} | {row['base'][metric]['median'] / 1e6:,.1f}M | "
                  + ' | '.join(f(row[l][metric]['change_pct_vs_base']) if l in row else '—' for l in LABELS)
                  + f' | {spread(row):.2f}% |')


def round_agreement(kind, cases, sizes=SIZE):
    """Largest gap between round 1 and round 2 change (percentage points) per threshold."""
    worst = {l: 0.0 for l in LABELS}
    for t in sizes:
        for c in cases:
            row = summary.get((kind, t, c))
            if not row: continue
            for l in LABELS:
                r = row[l]['instructions'].get('change_pct_vs_base_by_round', {})
                if len(r) == 2: worst[l] = max(worst[l], abs(r['1'] - r['2']))
    return worst


if __name__ == '__main__':
    print('## AC-P2 (4~16KB full read)')
    change_table('sweep', ('length', 'substr', 'fullscan'), {'fullscan': 'LIKE 전체'})
    print('\n## small column (narrow)')
    change_table('sweep', ('narrow',), {})
    print('\n## INSERT / UPDATE')
    change_table('dml', ('insert', 'update_small', 'update_big'), {'insert': 'INSERT 20,000행', 'update_small': 'UPDATE 작은 컬럼',
                                                                     'update_big': 'UPDATE 큰 컬럼'})
    print('\n## ordinary control')
    change_table('ordinary', ('scan', 'predicate', 'update'), {'scan': 'scan', 'predicate': '조건 scan', 'update': 'UPDATE'},
                 sizes={'n200k': '92B행'})
    print('\n## cold (restart-only) instructions')
    change_table('cold', ('narrow', 'length'), {})
    print('\n## cold ioread (pages) base / ' + ' / '.join(LABELS))
    for t, size in SIZE.items():
        for c in ('narrow', 'length'):
            row = summary.get(('cold', t, c))
            if row: print(f"| {size} | {c} | " + ' | '.join(f"{row[l]['ioread']['median']:,.0f}" for l in ('base',) + LABELS if l in row) + ' |')
    print('\n## io_bench')
    for layout in ('heap', 'overflow'):
        for c in ('q1', 'q4', 'q5'):
            row = summary.get(('io', layout, c))
            if row:
                print(f"| {layout} | {c} | {row['base']['instructions']['median'] / 1e6:,.1f}M | "
                      + ' | '.join(f(ins(row, l)) for l in LABELS) + ' | '
                      + ' / '.join(f"{row[l]['ioread']['median']:,.0f}" for l in ('base',) + LABELS if l in row) + ' |')
    print('\n## round agreement (max |r1-r2| pp)')
    for kind, cases in (('sweep', ('length', 'substr', 'fullscan', 'narrow')), ('dml', ('insert', 'update_small', 'update_big'))):
        print(kind, {l: round(v, 2) for l, v in round_agreement(kind, cases).items()})
    print('\n## storage')
    tabs = ['w36', 'w47', 'w78', 'w110', 'perf_heap_14500', 'perf_overflow_22000']
    for label, v in storage.items():
        print(f"| {label} | " + ' | '.join(
            f"{v[t]['Num_pages']:,}p / {v[t].get('Oos_num_recs', 0):,}" if t in v else '—' for t in tabs) + ' |')
