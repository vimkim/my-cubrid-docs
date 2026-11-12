#!/usr/bin/env python3
"""CBRD-28077 supplementary run: aggregate results-*.jsonl of oosbench2.py.

Usage: python3 analyze2.py RUN_DIR [--out tables.md] [--json summary.json]

Cells are medians over repeats; "spread" is (max - min) / median. Ratios divide by develop (a7f220d5d7).
"""

import argparse
import collections
import glob
import json
import statistics
from pathlib import Path

BUILDS = ('develop', 'develop-e64a', 'oos', 'sidecar', 'inner')
DESIGNS = ('oos', 'sidecar', 'inner')
SCEN = ('S4', 'S1', 'S2', 'S3n', 'S3w', 'S5', 'S6', 'S7', 'S8b', 'S8s', 'S9', 'S11', 'S12')
LABEL = {'S4': '적재 INSERT', 'S1': '작은 컬럼 scan', 'S2': '큰 값 비교 scan', 'S3n': 'PK 조회 5천 회, 작은 컬럼',
         'S3w': 'PK 조회 5천 회, 큰 컬럼', 'S5': '작은 컬럼 UPDATE 전체', 'S6': '큰 컬럼 UPDATE 1/8',
         'S7': 'UPDATE+INSERT+COMMIT 600회', 'S8b': '큰 컬럼 UPDATE+COMMIT 600회',
         'S8s': '작은 컬럼 UPDATE+COMMIT 600회', 'S9': 'DELETE 1/8', 'S11': '8 client 큰 컬럼 UPDATE',
         'S12': '8 client 큰 값 INSERT'}


def metric(r, name):
    if name == 'ins':
        return (r.get('instructions') or 0) + (r.get('drain_instructions') or 0)
    if name == 'fetch':
        return (r.get('Num_data_page_fetches') or 0) + (r.get('drain_Num_data_page_fetches') or 0)
    if name == 'osr':
        return (r.get('os_read_bytes') or 0) + (r.get('drain_os_read_bytes') or 0)
    if name == 'osw':
        return (r.get('os_write_bytes') or 0) + (r.get('drain_os_write_bytes') or 0)
    if name == 'wall':
        return r.get('wall')
    if name == 'cycles':
        return (r.get('cycles') or 0) + (r.get('drain_cycles') or 0)
    raise KeyError(name)


def load(run_dir):
    rows = []
    for f in sorted(glob.glob(str(Path(run_dir) / 'results-*.jsonl'))):
        rows += [json.loads(l) for l in open(f)]
    cells = collections.defaultdict(list)
    checks = collections.defaultdict(dict)
    sums = collections.defaultdict(dict)
    evidence, failed = [], []
    for r in rows:
        if r['mode'] == 'check':
            checks[(r['size'], r['phase_mode'], r['scenario'], r['rep'])][r['variant']] = (r['digest'], r['affected'])
        elif r['mode'] == 'checksum':
            sums[(r['size'], r['scenario'])][r['variant']] = tuple(r['values'] or ())
        elif r['mode'] == 'evidence':
            evidence.append(r)
        elif r['mode'] == 'lencheck':
            sums[(r['size'], 'len:' + r['scenario'])][r['variant']] = (r['wrong_length_rows'],)
            if r['wrong_length_rows']:
                failed.append({**r, 'failed': f"{r['wrong_length_rows']} rows with a wrong big length"})
        elif r['mode'] == 'error' or 'failed' in r or r.get('client_errors'):
            failed.append(r)
        else:
            cells[(r['size'], r['mode'], r['scenario'], r['variant'])].append(r)
    return cells, checks, sums, evidence, failed


def stat(cells, key, name):
    v = [metric(r, name) for r in cells.get(key, [])]
    v = [x for x in v if x is not None]
    if not v:
        return None
    med = statistics.median(v)
    return {'med': med, 'min': min(v), 'max': max(v), 'n': len(v),
            'spread': (max(v) - min(v)) / med if med else 0.0}


def fmt(v, name):
    if v is None:
        return '-'
    if name == 'wall':
        return f'{v:.2f}s'
    if name in ('osr', 'osw'):
        return f'{v / 2**20:,.0f}MiB'
    for unit, div in (('G', 1e9), ('M', 1e6), ('k', 1e3)):
        if v >= div:
            return f'{v / div:.2f}{unit}' if div == 1e9 else f'{v / div:.1f}{unit}'
    return f'{v:.0f}'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('run_dir')
    ap.add_argument('--out')
    ap.add_argument('--json')
    a = ap.parse_args()
    cells, checks, sums, evidence, failed = load(a.run_dir)
    sizes = sorted({k[0] for k in cells})
    md = [f'# CBRD-28077 보강 실행 표 ({Path(a.run_dir).name})', '',
          '값은 반복의 중앙값이다. 괄호 안은 (최대-최소)/중앙값으로 잰 반복 간 흔들림이다. 비율은 develop `a7f220d5d7` 대비다.', '']
    summary = {}
    for s in sizes:
        for mode in ('io', 'warm'):
            for name, title in (('ins', '서버 명령어 수(drain 포함)'), ('fetch', 'data page fetch(drain 포함)'),
                                ('osr', 'OS 읽기 바이트'), ('osw', 'OS 쓰기 바이트(drain 포함)'), ('wall', '경과 시간')):
                rows = []
                for sc in SCEN:
                    st = {v: stat(cells, (s, mode, sc, v), name) for v in BUILDS}
                    if not any(st.values()):
                        continue
                    base = st['develop']['med'] if st['develop'] else None
                    cells_txt = []
                    for v in BUILDS:
                        x = st[v]
                        if not x:
                            cells_txt.append('-')
                            continue
                        r = f' ×{x["med"] / base:.2f}' if base and v != 'develop' else ''
                        cells_txt.append(f'{fmt(x["med"], name)}{r} ({x["spread"]:.2f})')
                        summary.setdefault(f'{s}/{mode}/{sc}/{name}', {})[v] = x
                    rows.append(f'| {sc} {LABEL[sc]} | ' + ' | '.join(cells_txt) + ' |')
                if rows:
                    md += [f'## {s} B, {mode}: {title}', '', '| 시나리오 | ' + ' | '.join(BUILDS) + ' |',
                           '|---|' + '---|' * len(BUILDS)] + rows + ['']
    # correctness
    md += ['## 결과 일치 검사', '']
    bad = []
    for k, per in sorted(checks.items()):
        if len(set(per.values())) > 1:
            bad.append((k, per))
    md.append(f'- 측정한 문장 {len(checks)}개(크기·모드·시나리오·반복) 중 빌드 사이에 결과 digest나 영향받은 행 수가 다른 것: {len(bad)}개')
    for k, per in bad[:20]:
        md.append(f'  - {k}: {per}')
    sbad = [(k, per) for k, per in sorted(sums.items()) if len(set(per.values())) > 1]
    md.append(f'- 단계별 테이블 checksum(count, sum(k), sum(id), sum(bit_length(big))) {len(sums)}개 중 빌드 사이에 다른 것: {len(sbad)}개')
    for k, per in sbad[:20]:
        md.append(f'  - {k}: {per}')
    md += ['', '## 실패', '']
    md += [f"- {r['size']} {r['variant']} {r['mode']} {r['scenario']}: "
           f"{r.get('failed') or r.get('error') or ('client_errors=' + str(r.get('client_errors')))}" for r in failed] or ['- 없음']
    md += ['', '## 저장 공간(볼륨 파일 합계)', '', '| 크기 | 시점 | ' + ' | '.join(BUILDS) + ' |', '|---|---|' + '---|' * len(BUILDS)]
    ev = collections.defaultdict(dict)
    for e in evidence:
        ev[(e['size'], e['scenario'])][e['variant']] = e['db_bytes']
    for (s, tag), per in sorted(ev.items()):
        md.append(f'| {s} | {tag} | ' + ' | '.join(f"{per[v] / 2**20:,.0f}MiB" if v in per else '-' for v in BUILDS) + ' |')
    text = '\n'.join(md) + '\n'
    if a.out:
        Path(a.out).write_text(text)
    else:
        print(text)
    if a.json:
        Path(a.json).write_text(json.dumps({'summary': summary, 'bad_checks': len(bad), 'bad_sums': len(sbad),
                                            'checks': len(checks), 'sums': len(sums), 'failed': len(failed)},
                                           indent=1, default=str))


if __name__ == '__main__':
    main()
