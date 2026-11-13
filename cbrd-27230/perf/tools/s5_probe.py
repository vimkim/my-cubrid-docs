#!/usr/bin/env python3
"""CBRD-27230: what does `UPDATE t SET k = k + 1` do to the OOS file? Same table as CBRD-28077 run 3, 6.1
(30,000 rows of 8 KB, `big` never assigned).

Usage: python3 s5_probe.py OUTDIR VARIANT MODE      MODE is stat, peak or profile

stat     two S5 runs, each measured like the harness (perf stat instructions, drain included), with the OOS
         page count and the database volume bytes after load and after each run
peak     two S5 runs without perf; a sampler runs `show heap oos of t` every ~0.3 s from before the statement
         until the server is idle again, to catch the page count while the statement and vacuum run
profile  one S5 under `perf record -g` (a profile, not a measurement)
"""
import subprocess, sys, threading, time, types
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import oosbench as b
import oosbench2 as o2
import oosbench_reuse as r

out = Path(sys.argv[1]).resolve()
variant, mode = sys.argv[2], sys.argv[3]
N, SIZE = 30000, 8192
SQL = 'update t set k = k + 1;\n'


class Sampler(threading.Thread):
    def __init__(self, inst):
        super().__init__(daemon=True)
        self.inst, self.stop_evt, self.series = inst, threading.Event(), []

    def run(self):
        t0 = time.monotonic()
        while not self.stop_evt.is_set():
            p = subprocess.run(['csql', '-u', 'dba', '-c', 'show heap oos of t;', self.inst.db], env=self.inst.env,
                               cwd=self.inst.worktree, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                               stderr=subprocess.STDOUT, text=True, timeout=120)
            rows = r.table_rows(p.stdout)
            if rows:
                self.series.append((round(time.monotonic() - t0, 2), int(rows[0]['Oos_num_user_pages']),
                                    int(rows[0]['Oos_num_recs'])))
            self.stop_evt.wait(0.3)


args = types.SimpleNamespace(root=str(out), tag=f's5probe-{mode}', variant=variant, sizes=[SIZE], quick=False,
                             only_scenarios=None)
bench = r.BenchReuse(args)
inst = o2.Inst(variant, bench.run_dir)
bench.inst, bench.size, bench.n = inst, SIZE, N
inst.create(SIZE)
try:
    inst.start('warm')
    inst.sql(bench.load_sql(N), 'setup')
    inst.sql(f"insert into t select n, mod(n, 1000), 's' || n, {bench.value('AB')} from seq where n <= {N};\n", 'load')
    inst.sql('update statistics on t with fullscan;\n', 'stats')
    inst.wait_idle()
    bench.pages(inst, 'before-S5')
    if mode == 'stat':
        for rep in range(2):
            bench.m(inst, 'S5', SQL, rep, drain=True)
        bench.checksum(inst, 'end')
    elif mode == 'peak':
        for rep in range(2):
            s = Sampler(inst)
            s.start()
            _, wall = inst.sql(SQL, f'S5-peak-{rep}')
            time.sleep(15)  # the sampler keeps the server busy, so wait_idle would never return before it stops
            s.stop_evt.set()
            s.join()
            inst.wait_idle()
            bench.emit({'variant': variant, 'size': SIZE, 'mode': 'peak', 'scenario': f'S5-{rep}', 'wall': wall,
                        'samples': s.series, 'max_oos_pages': max(x[1] for x in s.series),
                        'final_oos_pages': s.series[-1][1], 'db_bytes': inst.du()})
            bench.pages(inst, f'after-S5-peak-{rep}')
    else:
        perf = subprocess.Popen(['perf', 'record', '-g', '-F', '499', '-p', str(inst.pid), '-o',
                                 str(bench.run_dir / 'perf.data')], stdin=subprocess.DEVNULL,
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(0.5)
        _, wall = inst.sql(SQL, 'S5-profile')
        inst.wait_idle()
        perf.send_signal(2)
        perf.wait()
        bench.pages(inst, 'after-S5-profile')
        with open(bench.run_dir / 'perf-report.txt', 'w') as f:
            subprocess.run(['perf', 'report', '--stdio', '--children', '--no-demangle', '--percent-limit', '1.5',
                            '-i', str(bench.run_dir / 'perf.data'), '--comm', 'cub_server', '-g', 'none'],
                           stdin=subprocess.DEVNULL, stdout=f, stderr=subprocess.DEVNULL)
        print('S5 wall', round(wall, 2))
finally:
    inst.drop()
