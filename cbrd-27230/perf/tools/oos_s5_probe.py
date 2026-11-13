"""Probe the OOS S5 cost: does an UPDATE of the small column write new OOS records? Where does the CPU go?"""
import subprocess, sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import oosbench as o

root = Path(sys.argv[1] if len(sys.argv) > 1 else 'probe-out').resolve(); root.mkdir(parents=True, exist_ok=True)
inst = o.Instance('oos', root)
n, size = 30000, 8192
inst.create(size)
inst.db = inst.db  # boos8192
try:
    inst.start('warm')
    inst.sql(f"create table seq (n int primary key);\ninsert into seq select rownum from db_attribute a, db_attribute b, db_attribute c, db_attribute d limit {n};\n"
             f"create table t (id int primary key, k int not null, s varchar(50), big bit varying);\n"
             f"insert into t select n, mod(n, 1000), 's' || n, REPEAT(X'AB', {size}) from seq;\n", 'load')
    inst.sql('show heap oos of t;\n', 'oos-before', check=False)
    inst.start('io', evict=True)
    inst.wait_idle()
    perf = subprocess.Popen(['perf', 'record', '-g', '-F', '499', '-p', str(inst.pid), '-o', str(root / 'perf.data')],
                            stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(0.5)
    out, wall = inst.sql('update t set k = k + 1;\n', 'S5')
    perf.send_signal(2); perf.wait()
    print('S5 wall', wall)
    inst.wait_idle()
    inst.sql('show heap oos of t;\n', 'oos-after', check=False)
finally:
    inst.drop()
