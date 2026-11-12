"""Probe the OOS warm S6 cost at 64 KB: load, S5 (UPDATE k), then UPDATE big of 750 rows under perf record."""
import subprocess, sys, time, types
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import oosbench2 as o2
out = Path(sys.argv[1] if len(sys.argv) > 1 else 'out-s6').resolve()
args = types.SimpleNamespace(root=str(out), tag='s6', variant='oos', sizes=[65536], quick=False, only_scenarios=None)
bench = o2.Bench2(args); inst = o2.Inst('oos', bench.run_dir)
bench.inst, bench.size, bench.n = inst, 65536, o2.ROWS[65536]
inst.create(65536)
try:
    inst.start('warm')
    inst.sql(bench.load_sql(bench.n), 'setup')
    inst.sql(f"insert into t select n, mod(n, 1000), 's' || n, {bench.value('AB')} from seq where n <= {bench.n};\n", 'load')
    inst.sql('show heap oos of t;\n', 'oos-0', check=False)
    inst.sql('update t set k = k + 1;\n', 'S5'); inst.wait_idle()
    inst.sql('show heap oos of t;\n', 'oos-1', check=False)
    perf = subprocess.Popen(['perf', 'record', '-g', '-F', '499', '-p', str(inst.pid), '-o', str(out / 'perf-s6.data')],
                            stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(0.5)
    sql, _ = bench.mut_sql('S6', 0)
    s0 = inst.statdump()
    o, wall = inst.sql(sql, 'S6')
    s1 = inst.statdump()
    perf.send_signal(2); perf.wait()
    print('S6 wall', round(wall, 1), 'fetches', s1['Num_data_page_fetches'] - s0['Num_data_page_fetches'])
    inst.wait_idle()
    inst.sql('show heap oos of t;\n', 'oos-2', check=False)
finally:
    inst.drop()
