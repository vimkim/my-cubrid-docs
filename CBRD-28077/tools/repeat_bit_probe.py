"""Minimal repro: does `UPDATE ... SET b = REPEAT(X'D1', 100)` store a different value when its plan is reused?"""
import sys, types
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import oosbench2 as o2
variant = sys.argv[1] if len(sys.argv) > 1 else 'develop'
args = types.SimpleNamespace(root=sys.argv[2] if len(sys.argv) > 2 else 'out-rb', tag='rb', variant=variant, sizes=[100], quick=False, only_scenarios=None)
bench = o2.Bench2(args)
inst = o2.Inst(variant, bench.run_dir)
inst.create(100)
try:
    inst.start('warm')
    sql = ("create table rb (id int primary key, b bit varying);\n"
           "insert into rb select rownum, REPEAT(X'AB', 100) from db_class limit 4;\n"
           "update rb set b = REPEAT(X'D1', 100) where id = 1;\n"
           "update rb set b = REPEAT(X'D1', 100) where id = 2;\n"
           "update rb set b = REPEAT(X'D1', 100) where id = 3;\n"
           "select id, bit_length(b), substring(hex(b) from 1 for 12) from rb order by id;\n"
           "select bit_length(REPEAT(X'D1', 100)), substring(hex(REPEAT(X'D1', 100)) from 1 for 12) from db_root;\n"
           "select bit_length(REPEAT(X'D1', 100)) from db_root;\n")
    out, _ = inst.sql(sql, 'rb', check=False)
    print(out)
finally:
    inst.drop()
