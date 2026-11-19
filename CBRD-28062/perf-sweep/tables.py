"""Print the Markdown tables of the CBRD-28062 sweep report from summary.json and storage.json.

usage: tables.py summary.json storage.json [block ...]   (no block name prints every block)
Change = (base - X) / base; + is better. Column names are oos_trigger_threshold in bytes; 0 is the default.
"""
import json, sys

LABELS = ('t0', 't5000', 't7000', 't10500', 't14500', 't16236')
THR = ' | '.join(f'{int(l[1:]):,}' for l in LABELS)
SIZE = {'w36': '4.6KB', 'w47': '6.0KB', 'w78': '9.9KB', 'w110': '13.8KB'}
summary = {tuple(r['key']): r['labels'] for r in json.load(open(sys.argv[1]))}
storage = json.load(open(sys.argv[2]))
ALL = ('base',) + LABELS


def pct(x): return f'{x:+.2f}%'
def M(x): return f'{x / 1e6:,.1f}M'
def inst(key): return summary[key]
def chg(row, l, metric='instructions'): return pct(row[l][metric]['change_pct_vs_base'])
def spread(row): return max(row[l]['instructions']['spread_pct'] for l in row)


def header(first, extra_last=None):
    cols = f'| {first} | base | {THR} |' + (f' {extra_last} |' if extra_last else '')
    return cols + '\n|' + '---|' * len(first.split(' | ')) + '---:|' * (1 + len(LABELS) + (1 if extra_last else 0))


def read_table(kind, cases, names, sizes=SIZE):
    out = [header('값 | 질의', '엔진 7개 중 최대 spread')]
    for t, size in sizes.items():
        for c in cases:
            row = inst((kind, t, c))
            out.append(f"| {size} | {names.get(c, c)} | {M(row['base']['instructions']['median'])} | "
                       + ' | '.join(chg(row, l) for l in LABELS) + f' | {spread(row):.2f}% |')
    return '\n'.join(out)


def max_table():
    out = ['| 값 | 질의 | base 명령어 | 16,236 | 라운드 1 / 2 | spread base / 16,236 |', '|---|---|---|---:|---:|---:|']
    for t, size in SIZE.items():
        for c, name in (('length', 'length'), ('substr', 'substr'), ('fullscan', 'LIKE 전체')):
            row = inst(('sweep', t, c)); m = row['t16236']['instructions']; r = m['change_pct_vs_base_by_round']
            out.append(f"| {size} | {name} | {M(row['base']['instructions']['median'])} | {pct(m['change_pct_vs_base'])} | "
                       f"{pct(r['1'])} / {pct(r['2'])} | {row['base']['instructions']['spread_pct']:.2f}% / {m['spread_pct']:.2f}% |")
    return '\n'.join(out)


def fail_count_table():
    out = ['| 임계값 | ' + ' | '.join(f'{int(l[1:]):,}' for l in LABELS) + ' |', '|---|' + '---:|' * len(LABELS)]
    cells, worst = [], []
    for l in LABELS:
        ch = [inst(('sweep', t, c))[l]['instructions']['change_pct_vs_base'] for t in SIZE for c in ('length', 'substr', 'fullscan')]
        cells.append(f'{sum(x < -2 for x in ch)} / 12'); worst.append(f'{min(ch):+.2f}%')
    out.append('| −2%보다 나쁜 케이스 | ' + ' | '.join(cells) + ' |')
    out.append('| 가장 나쁜 케이스 | ' + ' | '.join(worst) + ' |')
    return '\n'.join(out)


def cold_ioread_table():
    out = ['| 값 | 질의 | ' + ' | '.join('base' if l == 'base' else f'{int(l[1:]):,}' for l in ALL) + ' |', '|---|---|' + '---:|' * len(ALL)]
    for t, size in SIZE.items():
        for c in ('narrow', 'length'):
            row = inst(('cold', t, c))
            out.append(f'| {size} | {c} | ' + ' | '.join(f"{row[l]['ioread']['median']:,.0f}" for l in ALL) + ' |')
    return '\n'.join(out)


def io_tables():
    ins = [header('배치 | 질의')]
    pages = ['| 배치 | 질의 | ' + ' | '.join('base' if l == 'base' else f'{int(l[1:]):,}' for l in ALL) + ' |', '|---|---|' + '---:|' * len(ALL)]
    for layout, name in (('heap', 'heap 14.5KB'), ('overflow', 'overflow 22KB')):
        for c in ('q1', 'q4', 'q5'):
            row = inst(('io', layout, c))
            ins.append(f"| {name} | {c} | {M(row['base']['instructions']['median'])} | " + ' | '.join(chg(row, l) for l in LABELS) + ' |')
            pages.append(f'| {name} | {c} | ' + ' | '.join(f"{row[l]['ioread']['median']:,.0f}" for l in ALL) + ' |')
    return '\n'.join(ins), '\n'.join(pages)


TABS = ['w36', 'w47', 'w78', 'w110', 'perf_heap_14500', 'perf_overflow_22000']
TAB_NAMES = ['4.6KB', '6.0KB', '9.9KB', '13.8KB', 'io heap 14.5KB', 'io overflow 22KB']


def storage_table():
    out = ['| 임계값 | ' + ' | '.join(TAB_NAMES) + ' |', '|---|' + '---|' * len(TABS)]
    for l in ALL:
        v = storage[l]
        out.append(f"| {'base (develop)' if l == 'base' else f'{int(l[1:]):,}'} | " + ' | '.join(
            f"{v[t]['Num_pages']:,} + {v[t].get('Oos_num_user_pages', 0):,} ({v[t].get('Oos_num_recs', 0):,})" for t in TABS) + ' |')
    return '\n'.join(out)


def pages_delta_table():
    out = ['| 임계값 | ' + ' | '.join(TAB_NAMES) + ' |', '|---|' + '---:|' * len(TABS)]
    total = lambda v, t: v[t]['Num_pages'] + v[t].get('Oos_num_user_pages', 0)
    for l in LABELS:
        out.append(f'| {int(l[1:]):,} | ' + ' | '.join(
            f"{total(storage[l], t):,} ({(total(storage[l], t) - total(storage['base'], t)) / total(storage['base'], t) * 100:+.1f}%)"
            for t in TABS) + ' |')
    out.append('| base 합계 | ' + ' | '.join(f"{total(storage['base'], t):,}" for t in TABS) + ' |')
    return '\n'.join(out)


def blocks():
    ioi, iop = io_tables()
    return {
        'ac_p2': read_table('sweep', ('length', 'substr', 'fullscan'), {'fullscan': 'LIKE 전체'}),
        'ac_p2_max': max_table(), 'fail_count': fail_count_table(),
        'narrow': read_table('sweep', ('narrow',), {'narrow': '작은 컬럼'}),
        'dml': read_table('dml', ('insert', 'update_small', 'update_big'),
                          {'insert': 'INSERT 20,000행', 'update_small': 'UPDATE 작은 컬럼', 'update_big': 'UPDATE 큰 컬럼'}),
        'ordinary': read_table('ordinary', ('scan', 'predicate', 'update'), {'scan': 'scan', 'predicate': '조건 scan', 'update': 'UPDATE + COMMIT'},
                               sizes={'n200k': '92B행 200,000'}),
        'cold': read_table('cold', ('narrow', 'length'), {'narrow': '작은 컬럼', 'length': 'length'}),
        'cold_ioread': cold_ioread_table(), 'io_instr': ioi, 'io_ioread': iop,
        'storage': storage_table(), 'pages_delta': pages_delta_table(),
    }


if __name__ == '__main__':
    b = blocks()
    for name in (sys.argv[3:] or b):
        print(f'<!-- {name} -->\n{b[name]}\n')
