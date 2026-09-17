from pathlib import Path
import shutil, subprocess, json, hashlib, sys
root=Path(__file__).parent
label=sys.argv[1]
assert label in ('baseline','patched','probe')
home=root/label/'home'
home.mkdir(parents=True)
install=Path('/home/vimkim/.cub/install/develop/debug_gcc')
shutil.copytree(install,home/'CUBRID',symlinks=True,ignore=shutil.ignore_patterns('databases','log','tmp','var'))
for d in ['databases','log/server','log/broker/sql_log','tmp','var/CUBRID_SOCK']:
    (home/'CUBRID'/d).mkdir(parents=True,exist_ok=True)
(home/'CUBRID/databases/databases.txt').write_text('')
shutil.copytree(home/'CUBRID/conf',home/'.CUBRID_SHELL_FM/conf')
shutil.copytree(home/'CUBRID/databases',home/'.CUBRID_SHELL_FM/databases')
ctp=Path('/home/vimkim/CTP')
shutil.copytree(ctp,home/'CTP',symlinks=True,ignore=shutil.ignore_patterns('result','.git','*.log'))
previous=Path('/home/vimkim/.cache/codex/pr7927-512b361-remaining/baseline/home')
shutil.copy2(previous/'.bash_profile',home/'.bash_profile')
(home/'java').mkdir()
case=Path('shell/_35_cherry/issue_21654_server_side_loaddb/partition_tbls')
tc=Path('/home/vimkim/gh/tc/develop-partition-tc')
source=root/'original-tc' if label=='baseline' else tc/case
shutil.copytree(source,home/'cubrid-testcases-private-ex'/case)
conf=(previous/'shell.conf').read_text().replace('scenario=/home/vimkim/cubrid-testcases-private-ex/shell','scenario=/home/vimkim/cubrid-testcases-private-ex/'+str(case))
(home/'shell.conf').write_text(conf)
manifest={'engine_revision':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),'preset':'debug_gcc','install':str(install),'testcase_revision':subprocess.check_output(['git','-C',str(tc),'rev-parse','HEAD'],text=True).strip(),'testcase_label':label,'hashes':{}}
for base,paths in [(install,['bin/cub_server','bin/csql','bin/cubrid','lib/libcubridsa.so','lib/libcubrid.so','lib/libcubridcs.so']),(source,['cases/partition_tbls.sh','cases/bug_bts_11093.answer','cases/bug_bts_11093.answer_WIN'])]:
    for p in paths:
        manifest['hashes'][str(base/p)]=hashlib.sha256((base/p).read_bytes()).hexdigest()
(root/label/'identity.json').write_text(json.dumps(manifest,indent=2)+'\n')
