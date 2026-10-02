from pathlib import Path
import hashlib,json,subprocess,sys
attempt=Path(sys.argv[1])
install=Path('/home/vimkim/.cub/install/CBRD-27443-fd-clean/debug_gcc')
engine=Path('/home/vimkim/gh/cb/CBRD-27443-fd-clean')
tests=Path('/home/vimkim/gh/cubrid-testcases-private-ex/CBRD-27443-fd-clean')
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
source=(attempt/'engine-commit.txt').read_text().strip()
test_sha=(attempt/'testcase-commit.txt').read_text().strip()
summary={'source':source,'tests':test_sha,'matrices':[],'installed_copy':[],'fixture_objects':[],'supplemental':[]}
assert source=='0809a480df55ac6767a905d03fa3d31edd40a93c'
for repo,sha in [(engine,source),(tests,test_sha)]:
 assert subprocess.check_output(['git','-C',str(repo),'rev-parse','HEAD'],text=True).strip()==sha
 assert not subprocess.check_output(['git','-C',str(repo),'status','--short'],text=True).strip()
assert not (attempt/'engine.patch').read_text() and not (attempt/'testcase.patch').read_text()
assert len((attempt/'expected-cases.txt').read_text().splitlines())==4
all_assertions={}
reports={}
expected_modes={'matrix','master-matrix','restart-matrix','boundary-matrix','rot','ha','repl','b-broker','b-failure','b-recovery','b-scaling','b-rot'}
for path in sorted((attempt/'home/.cache').glob('fd-*/matrix.json')):
 data=json.loads(path.read_text())
 mode=path.parent.name[3:].rsplit('.',1)[0]
 assert mode in expected_modes and mode not in reports,mode
 reports[mode]=data
 assert data['checks'] and all(c['pass'] for c in data['checks']),mode
 assert any(word in data['checks'][-1]['name'] for word in ('gone','reaped','removed')),mode
 for index,capture in enumerate(data['captures']):
  assert capture['launcher_rc'] is not None,mode
  assert capture['lock_available'],mode
  if mode=='master-matrix' and index==23:
   pid=int((Path(data['runtime_root']).parent/'init-master.pid').read_text())
   holders=capture['caller_holders']
   assert not capture['eof_s'] and capture['launcher_rc']==0
   assert len(holders)==1 and holders[0]['name']=='cub_master' and holders[0]['pid']==pid
   assert holders[0]['fds']['1']==capture['caller_targets'][2]
   assert holders[0]['fds']['2']==capture['caller_targets'][3]
   assert all(t not in holders[0]['fds'].values() for t in capture['caller_targets'][:2])
   names={c['name'] for c in data['checks'] if c['pass']}
   assert {'PID1 parent keeps original master PID','PID1 supervisor stdout stderr contract remains attached'} <= names
   summary['foreground_exception']={'mode':mode,'capture':index,'pid':pid,'contract':'PID1-supervised master retains only supervisor stdout/stderr; general file/lock released'}
  else:
   assert set(capture['eof_s'])==set(capture['output']),mode
   assert not capture['caller_holders'],mode
 if 'cleanup_processes' in data:
  if mode=='master-matrix':assert data['cleanup_processes'] and all(snapshot==[] for snapshot in data['cleanup_processes'])
  else:assert data['cleanup_processes']==[]
 if 'ipc' in data:assert data['ipc']['host']!=data['ipc']['private']
 all_assertions[mode]=data['checks']
 summary['matrices'].append({'mode':mode,'path':str(path),'runtime':data['runtime_root'],'checks':len(data['checks']),
     'captures':len(data['captures']),'console_interactions':data.get('console_interactions',[]),
     'logging_faults':data.get('logging_faults',[]),'rotating_failures':data.get('rotating_failures',[])})
assert set(reports)==expected_modes
expected=reports['matrix']['binary_sha256']
assert len(expected)==18
for obj,recorded in expected.items():
 actual=digest(install/obj); copied=digest(attempt/'cubrid'/obj)
 assert actual==copied==recorded,obj
 summary['installed_copy'].append({'object':obj,'installed':actual,'copy':copied})
roots=[]
for mode,data in reports.items():
 assert data['binary_sha256']==expected,mode
 roots.append((mode,Path(data['runtime_root'])))
 if mode=='repl':
  for name,node in data['topology'].items():
   assert node['sha256']==expected,name
  roots.append(('nodeb',Path(data['topology']['nodeb']['root'])))
presents=list((attempt/'home/.cache').glob('fd-present.*/present.json'))
assert len(presents)==1
present=json.loads(presents[0].read_text())
assert present['launcher_rc']==0 and all(present['eof_after_exit_plus_2s'].values())
assert present['lock_available_while_running'] and not present['holders_after_service_stop']
assert present['binary_sha256']==expected
roots.append(('present',Path(present['runtime_root'])))
for name,root in roots:
 for obj,expected_hash in expected.items():
  actual=digest(root/obj);assert actual==expected_hash,(name,obj)
  summary['fixture_objects'].append({'fixture':name,'root':str(root),'object':obj,'actual':actual})
for record in reports['b-broker']['restarts']:
 parent,child=record['parent'],record['after']
 assert child['fds']['0']=='/dev/null' and all(child['fds'][str(fd)]==parent['fds'][str(fd)] for fd in (1,2))
 assert not record['internal_leaks']
 summary['supplemental'].append({'pid':child['pid'],'check':'internal restart keeps dedicated parent stdio only'})
console=(Path(reports['b-broker']['runtime_root'])/'log/broker-console.log').read_text()
for name in ('cub_cas','cub_proxy'):
 for fd in (1,2):
  count=console.count('BROKER-ATTEMPT-'+name+'-%d\n'%fd)
  assert count==4000
  summary['supplemental'].append({'name':name,'fd':fd,'lines':count})
records=reports['repl']['replicated_records']
assert [r['id'] for r in records]==list(range(1,16))
summary['replicated_records']=records
faults=[f for data in reports.values() for f in data.get('logging_faults',[])]
assert len(faults)==12,len(faults)
for fault in faults:
 assert fault['prior_failure']['mtime_ns']!=fault['failure_mtime_ns']
 assert 'operation=open' in fault['failure']
summary['checks']=sum(m['checks'] for m in summary['matrices'])
summary['captures']=sum(m['captures'] for m in summary['matrices'])
summary['fault_count']=len(faults)
summary['scaling']=reports['b-scaling']['scaling']
(attempt/'all-assertions.json').write_text(json.dumps(all_assertions,indent=2)+'\n')
(attempt/'safe-summary.json').write_text(json.dumps(summary,indent=2)+'\n')
print(json.dumps({'checks':summary['checks'],'captures':summary['captures'],'faults':len(faults),'replicated_rows':len(records),
 'installed_pairs':len(summary['installed_copy']),'actual_fixture_files':len(summary['fixture_objects']),
 'supplemental':len(summary['supplemental']),'matrices':[(m['mode'],m['checks']) for m in summary['matrices']]}))
