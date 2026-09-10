from pathlib import Path
import json,re
out=Path(__file__).resolve().parents[1];x=json.loads((out/'evidence/functions-ast.json').read_text());meta=json.loads((out/'evidence/manifest.json').read_text())
hunks=[];h=None;old=new=0;path=None
for line in (out/'evidence/pr.diff').read_text().splitlines():
 if line.startswith('+++ b/'):path=line[6:]
 elif line.startswith('@@ '):
  m=re.match(r'@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))?',line);old=int(m[1]);new=int(m[3]);h={'id':len(hunks)+1,'path':path,'functions':set(),'non_function_changes':[]};hunks.append(h)
 elif h and line.startswith(('+','-')) and not line.startswith(('+++','---')):
  side='head' if line[0]=='+' else 'base';n=new if side=='head' else old
  matches=[f['name'] for f in x['functions'] if f['path']==path and f[side] and f[side]['start']<=n<=f[side]['end']]
  if matches:h['functions'].update(matches)
  else:h['non_function_changes'].append({'side':side,'line':n,'text':line[1:]})
  if side=='head':new+=1
  else:old+=1
 elif h and line.startswith(' '):old+=1;new+=1
for h in hunks:
 h['functions']=sorted(h['functions']);h['non_function_explanation']=meta['hunks'][h['id']-1]['en']
(out/'evidence/function-hunk-coverage.json').write_text(json.dumps(hunks,indent=2))
print('hunks',len(hunks),'with function matches',sum(bool(h['functions']) for h in hunks))
for h in hunks:
 if h['non_function_changes']:print(h['id'],h['path'],len(h['non_function_changes']),'outside function spans',[(z['line'],z['text'][:65]) for z in h['non_function_changes'][:3]])
