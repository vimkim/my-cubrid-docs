"""Separate large-value materialization from the SQL equality operator."""
from pathlib import Path
import json
import os
import subprocess
import time
import measure_shared_reads as matrix

ROOT = matrix.ROOT
out = ROOT / os.environ.get('SP_PROBE_NAME', 'large-probe')
out.mkdir(exist_ok=False)
install = Path(os.environ['CUBRID']).resolve()
registry = Path(os.environ['CUBRID_DATABASES']) / 'databases.txt'
entries = [line.split()[0] for line in registry.read_text().splitlines()
           if line.strip() and not line.lstrip().startswith('#')]
assert entries == ['oos27785'], entries
assert not matrix.instance.servers(install)
queries = {
    'length_all': ('SELECT SUM(CAST(BIT_LENGTH(a) AS BIGINT)) FROM sp_large;', 5120000000),
    'equal_all': (matrix.QUERIES['sp_large_full'].replace(' WHERE id <= 1000', ''), 20000),
    'length_1000': (matrix.QUERIES['sp_large_length'], 256000000),
    'equal_1000': (matrix.QUERIES['sp_large_full'], 1000),
}
manifest = dict(queries=queries, samples={}, complete=False, dso_sha256=matrix.bench.digest(install/'lib/libcubrid.so.11.5'))
try:
    matrix.instance.command(['taskset','-c','16-19','cubrid','server','start','oos27785'],out/'start',timeout=45)
    pids=matrix.instance.servers(install)
    assert len(pids)==1
    pid=pids[0]
    matrix.instance.command(['taskset','-apc','16-19',str(pid)],out/'affinity')
    manifest['server']=matrix.bench.process_identity(pid)
    manifest['server_stderr']=str(Path(f'/proc/{pid}/fd/2').resolve())
    worktree = Path(os.environ['CUBRID_CONF_FILE']).parents[2]
    manifest['source_diff']=subprocess.check_output(['git', '-C', str(worktree), 'diff', 'HEAD', '--', 'src'], text=True)
    manifest['worktree']=str(worktree)
    for case,(sql,expected) in queries.items():
        path=out/(case+'.sql'); path.write_text(sql+'\n')
        cmd=['perf','stat','-x',';','-e','instructions:u,cycles:u,task-clock,minor-faults,major-faults,context-switches','-p',str(pid),'-o',str(out/(case+'.perf')),'--',
             'perf','record','-q','-e','cycles:u','-F','99','--call-graph','fp','-p',str(pid),'-o',str(out/(case+'.data')),'--','taskset','-c','12']
        cmd+=matrix.bench.csql_command('oos27785',path,str(install/'bin/csql'))
        wall=matrix.bench.run(cmd,out/case,180)
        assert matrix.bench.results(out/(case+'.stdout'))==[(expected,)]
        manifest['samples'][case]=dict(wall_seconds=wall,counters=matrix.bench.counters(out/(case+'.perf')))
        (out/'summary.json').write_text(json.dumps(manifest,indent=2)+'\n')
        matrix.instance.command(['perf','report','--stdio','--no-children','--no-inline','--call-graph','none','--sort','symbol,dso','--percent-limit','0.5','-i',str(out/(case+'.data'))],out/(case+'-profile'),timeout=30)
        print(case,manifest['samples'][case],flush=True)
    manifest['complete']=True
    (out/'summary.json').write_text(json.dumps(manifest,indent=2)+'\n')
finally:
    matrix.instance.command(['cubrid','server','stop','oos27785'],out/'stop',timeout=45,required=False)
    matrix.instance.command(['cubrid','service','stop'],out/'service-stop',timeout=45,required=False)
    assert not matrix.instance.servers(install)
