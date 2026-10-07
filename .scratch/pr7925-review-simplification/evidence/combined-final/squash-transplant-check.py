import argparse, json, subprocess
from pathlib import Path
p=argparse.ArgumentParser()
p.add_argument('worktree')
p.add_argument('tip')
p.add_argument('output',type=Path)
a=p.parse_args()
def git(*args,data=None):
    return subprocess.run(['git','-C',a.worktree,*args],input=data,text=True,check=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).stdout.strip()
boundary='4be72fc209ae9cb8aa1709573d7d0ae7fc06df7c'
base='fb567a629cdb390fff920542173fa36f454c74a0'
refs_before=git('show-ref')
status_before=git('status','--porcelain=v1')
git('merge-base','--is-ancestor',boundary,a.tip)
virtual=git('commit-tree',git('rev-parse',boundary+'^{tree}'),'-p',base,data='Temporary equal-tree dependency squash simulation\n')
synthetic=virtual
rows=[]
for commit in git('rev-list','--reverse',boundary+'..'+a.tip).splitlines():
    parents=git('rev-list','--parents','-n','1',commit).split()[1:]
    assert len(parents)==1, (commit,parents)
    tree=git('merge-tree','--write-tree','--merge-base='+parents[0],virtual,commit).splitlines()[0]
    rows.append({'task_commit':commit,'original_parent':parents[0],'conflicts':0,'result_tree':tree})
    virtual=git('commit-tree',tree,'-p',virtual,data='Temporary task-only replay '+commit+'\n')
assert refs_before==git('show-ref')
assert status_before==git('status','--porcelain=v1')
equals=git('rev-parse',virtual+'^{tree}')==git('rev-parse',a.tip+'^{tree}')
assert equals
record={'method':'Temporary Git objects only; no refs, source files or working trees changed. Simulated dependency squash retains the exact selected dependency tree over the common base. Only post-boundary commits replayed with explicit original-parent merge bases.','dependency_boundary':boundary,'common_base':base,'task_tip':a.tip,'synthetic_equal_tree_squash':synthetic,'replayed_task_commits':rows,'dependency_commits_replayed':0,'total_conflicts':0,'final_tree_equals_selected_task_tree':equals,'limitation':'Actual squash/dependency/shared source changes require comparison, authorization and checks. This object simulation is not runtime verification or source promotion.'}
a.output.write_text(json.dumps(record,indent=2)+'\n')
print(json.dumps({'file':str(a.output),'task_commits':len(rows),'conflicts':0,'equal_tree':equals,'refs_and_worktree_unchanged':True}))
