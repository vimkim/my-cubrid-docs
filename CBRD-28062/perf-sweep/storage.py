"""Parse SHOW HEAP CAPACITY / SHOW HEAP OOS output (csql ';line on') from the sweep databases.

usage: storage.py [ROOT] > storage.json   (reads ROOT/db/<label>/{sw,io}-storage.stdout)
"""
import json, re, sys
from pathlib import Path

ROOT = Path(sys.argv[1] if len(sys.argv) > 1 else '/mnt/nvme/data-5/tmp/CBRD-28062-perf-sweep')
LABELS = ('base', 't0', 't5000', 't7000', 't10500', 't14500', 't16236')
HEAP_KEYS = ('Num_recs', 'Num_relocated_recs', 'Num_overflowed_recs', 'Num_pages', 'Avg_rec_len')
OOS_KEYS = ('Has_oos_file', 'Oos_num_user_pages', 'Oos_num_recs', 'Oos_recs_sumlen', 'Oos_physical_bytes')


def blocks(text):
    out, cur = [], None
    for line in text.splitlines():
        m = re.match(r'<\d+>\s+Table_name\s*:\s*(\S+)', line)
        if m:
            cur = {'Table_name': m.group(1).removeprefix('dba.')}; out.append(cur); continue
        m = re.match(r'\s+(\w+)\s*:\s*(.*)$', line)
        if m and cur is not None: cur[m.group(1)] = m.group(2).strip()
    return out


def parse(path):
    tables = {}
    for b in blocks(path.read_text()):
        t = tables.setdefault(b['Table_name'], {})
        keys = OOS_KEYS if 'Has_oos_file' in b else HEAP_KEYS
        t.update({k: int(b[k]) for k in keys if k in b and b[k].lstrip('-').isdigit()})
    return tables


def main():
    out = {}
    for label in LABELS:
        d = ROOT / 'db' / label
        out[label] = {}
        for kind in ('sw', 'io'):
            out[label].update(parse(d / f'{kind}-storage.stdout'))
        out[label]['_load_seconds'] = {k: float((d / f'{k}-load.seconds').read_text()) for k in ('sw', 'io')}
        out[label]['_threshold_param'] = re.findall(r'oos_trigger_threshold=(\S+)', (d / 'sw-paramdump.stdout').read_text()) or None
    json.dump(out, sys.stdout, indent=1)


if __name__ == '__main__':
    main()
