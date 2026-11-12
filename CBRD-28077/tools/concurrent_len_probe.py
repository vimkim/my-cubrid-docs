"""Probe: after 8 concurrent clients (S11 big UPDATE+COMMIT, S12 big INSERT+COMMIT) on 100-byte values,
does any row of a build end with a `big` value whose length is not 800 bits?

Usage: python3 concurrent_len_probe.py VARIANT OUTDIR [ROUNDS]
"""
import sys
import types
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import oosbench2 as o2  # noqa: E402

variant, outdir = sys.argv[1], Path(sys.argv[2])
rounds = int(sys.argv[3]) if len(sys.argv) > 3 else 3
args = types.SimpleNamespace(root=str(outdir), tag='probe', variant=variant, sizes=[100], quick=False,
                             only_scenarios=None)
bench = o2.Bench2(args)
inst = o2.Inst(variant, bench.run_dir)
bench.inst, bench.size, bench.n = inst, 100, o2.ROWS[100]
inst.create(100)
try:
    inst.start('warm')
    inst.sql(bench.load_sql(bench.n), 'setup')
    inst.sql(f"insert into t select n, mod(n, 1000), 's' || n, REPEAT(X'AB', 100) from seq where n <= {bench.n};\n", 'load')
    for rep in range(rounds):
        for sc in ('S11', 'S12'):
            bench.concurrent(inst, sc, rep)
    inst.wait_idle()
    out, _ = inst.sql("select count(*), sum(cast(bit_length(big) as bigint)) from t;\n"
                      "select id, k, s, bit_length(big), substring(hex(big) from 1 for 40) from t "
                      "where bit_length(big) <> 800 or big is null order by id;\n", 'lengths', check=False)
    print(out)
finally:
    inst.drop()
