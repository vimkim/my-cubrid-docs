from broker_fixture import *
# Observation-only differential: baseline is expected to retain caller pipes.
conf.write_text(common.replace('MIN_NUM_APPL_SERVER=1', 'MIN_NUM_APPL_SERVER=32').replace('MAX_NUM_APPL_SERVER=2', 'MAX_NUM_APPL_SERVER=32'))
report['configuration'] = conf.read_text()
for limit in (128, 256):
    result = collect(command='bash -c '+shlex.quote('ulimit -Sn '+str(limit)+'; ulimit -Sn > soft-limit; exec cubrid broker start'), assert_eof=False)
    check((root.parent/'soft-limit').read_text().strip()==str(limit), 'launcher soft limit '+str(limit))
    alive=[p for p in processes() if p['name']=='cub_cas' and p['state']!='Z']
    observation={'limit':limit,'launcher_rc':result['launcher_rc'],'cas_count':len(alive),'eof_s':result['eof_s'],'lock_available':result['lock_available'],'output':result['output']}
    report.setdefault('scaling',[]).append(observation)
    save()
    if result['launcher_rc']==0:
        check(len(alive)==32, 'all32 configured CAS are alive')
        sql()
        observation['sql_pass']=True
    else:
        observation['sql_pass']=False
    control(['cubrid','broker','stop'], expected=None)
    save()
cleanup()
print(json.dumps(report['scaling']))
