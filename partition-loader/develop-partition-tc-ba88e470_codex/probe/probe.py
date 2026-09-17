from pathlib import Path
import subprocess, json, os, hashlib
root=Path('/home/vimkim/probe-evidence'); root.mkdir(); os.chdir(root)
db='partition_probe'
result={}
def run(label,args,required=False):
    output_path=root/(label+'.output')
    with output_path.open('w') as out:
        p=subprocess.run(args,stdout=out,stderr=subprocess.STDOUT,text=True,timeout=60)
    p.stdout=output_path.read_text()
    result[label]={'argv':args,'returncode':p.returncode,'output':p.stdout}
    (root/(label+'.output')).write_text(p.stdout)
    if required and p.returncode: raise RuntimeError(label+': '+p.stdout)
    return p

def sql(label,query,required=False):
    return run(label,['csql','-u','dba','-t','-N','-c',query,db],required)
try:
    run('createdb',['cubrid','createdb','--db-volume-size=20M','--log-volume-size=20M',db,'en_US.utf8'],True)
    run('start',['cubrid','server','start',db],True)
    identities=[]
    for proc in Path('/proc').glob('[0-9]*'):
        try:
            exe=(proc/'exe').resolve(strict=True)
            if exe.name=='cub_server':
                identities.append({'pid':proc.name,'exe':str(exe),'sha256':hashlib.sha256(exe.read_bytes()).hexdigest(),'maps':(proc/'maps').read_text()})
        except (FileNotFoundError,PermissionError,ProcessLookupError): pass
    result['server_identity']=identities
    sql('schema','create table t(i int) partition by range(i) (partition p0 values less than (10));',True)
    for target in ['t__p__p0','t']:
        sql(target+'_clear','delete from t;',True)
        invalid=root/(target+'.objects'); invalid.write_text('%class '+target+' (i)\n1\n100\n')
        run(target+'_invalid_load',['cubrid','loaddb','-C','-v','-u','dba','-d',str(invalid),db])
        sql(target+'_parent_rows','select i from t order by i;',True)
        sql(target+'_partition_rows','select i from t__p__p0 order by i;',True)
        sql(target+'_count','select count(*) from t;',True)
        valid=root/(target+'.valid.objects'); valid.write_text('%class '+target+' (i)\n1\n')
        run(target+'_valid_load',['cubrid','loaddb','-C','-v','-u','dba','-d',str(valid),db])
        sql(target+'_after_valid_rows','select i from t order by i;',True)
    sql('sql_clear','delete from t;',True)
    sql('sql_invalid_insert','insert into t values (100);')
    sql('sql_partition_invalid_insert','insert into t__p__p0 values (100);')
finally:
    run('stop',['cubrid','server','stop',db])
    (root/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))
