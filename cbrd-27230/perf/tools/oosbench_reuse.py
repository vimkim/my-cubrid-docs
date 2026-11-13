#!/usr/bin/env python3
"""CBRD-27230 reuse re-measurement: oosbench2.py (unchanged procedure) plus three extra records.

  pages    after every measured mutation (drain included) and after load/end: the heap page count and, for the
           OOS builds, the OOS file's user pages and record count (`show heap capacity/oos of t`). This is the
           "OOS pages before/after the UPDATE" evidence; "before" is the previous record.
  content  after every checksum: how many rows hold each of the byte patterns the workload writes (a content
           check; the harness's own checksum only sees bit_length(big), so a stale or wrong OOS stub would
           pass it).

Usage: python3 oosbench_reuse.py --root DIR --tag TAG --variant {develop,reuse-base,reuse} [--sizes 8192,4096,65536]
"""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import oosbench2 as o2  # noqa: E402

PATTERNS = ('AB', 'B0', 'B1', 'B2', 'B3', 'B4', 'B5', 'E1', 'D1', 'D2')


def table_rows(out):
    """Rows of every `Table_name ...` result table in csql output, as dicts keyed by column name."""
    lines = out.splitlines()
    rows = []
    for i, line in enumerate(lines):
        if line.strip().startswith('Table_name') and i + 2 < len(lines):
            head, vals = line.split(), lines[i + 2].split()
            if len(head) == len(vals):
                rows.append(dict(zip(head, (v.strip("'") for v in vals))))
    return rows


class BenchReuse(o2.Bench2):
    def pages(self, inst, tag):
        text = 'show heap capacity of t;\n' + ('' if inst.name == 'develop' else 'show heap oos of t;\n')
        out, _ = inst.sql(text, f'pages-{tag}', check=False)
        merged = {}
        for r in table_rows(out):
            merged.update(r)
        self.emit({'variant': inst.name, 'size': inst.size, 'mode': 'pages', 'scenario': tag,
                   'phase_mode': inst.mode,
                   'heap_pages': int(merged['Num_pages']) if 'Num_pages' in merged else None,
                   'heap_recs': int(merged['Num_recs']) if 'Num_recs' in merged else None,
                   'oos_pages': int(merged['Oos_num_user_pages']) if 'Oos_num_user_pages' in merged else None,
                   'oos_recs': int(merged['Oos_num_recs']) if 'Oos_num_recs' in merged else None,
                   'db_bytes': inst.du()})

    def m(self, inst, scenario, sql, rep, autocommit=True, drain=False, expect=None):
        out = super().m(inst, scenario, sql, rep, autocommit=autocommit, drain=drain, expect=expect)
        if drain and out is not None:
            self.pages(inst, f'{inst.mode}-{scenario}-{rep}')
        return out

    def concurrent(self, inst, scenario, rep):
        super().concurrent(inst, scenario, rep)
        self.pages(inst, f'{inst.mode}-{scenario}-{rep}')

    def evidence(self, inst, tag):
        super().evidence(inst, tag)
        self.pages(inst, tag)

    def checksum(self, inst, tag):
        super().checksum(inst, tag)
        cols = ', '.join(f"sum(case when big = CAST(REPEAT(X'{x}', {inst.size}) AS BIT VARYING) then 1 else 0 end)"
                         for x in PATTERNS)
        out, _ = inst.sql(f'select count(*), {cols} from t;\n', f'content-{tag}')
        vals = re.findall(r'^\s+(\d+(?:\s+\d+){%d})\s*$' % len(PATTERNS), out, re.M)
        self.emit({'variant': inst.name, 'size': inst.size, 'mode': 'content', 'scenario': tag,
                   'values': vals[0].split() if vals else None})


if __name__ == '__main__':
    sys.exit(BenchReuse(o2.parse()).main())
