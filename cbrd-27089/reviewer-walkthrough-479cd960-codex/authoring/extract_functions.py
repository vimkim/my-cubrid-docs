from pathlib import Path
import subprocess,json,re
from tree_sitter import Language,Parser
import tree_sitter_cpp
ROOT=Path('/home/vimkim/gh/cb/CBRD-27089-has-oos-but-no-oos');OUT=Path(__file__).resolve().parents[1]
BASE='f4299ac0cd777a2a964c1f197ae5ebf9841a4936';HEAD='479cd960ec04196c92bf9789b1fc340af9046c2c'
def git(*a):return subprocess.check_output(['git',*a],cwd=ROOT)
parser=Parser(Language(tree_sitter_cpp.language()))
def walk(n):
 yield n
 for c in n.children:yield from walk(c)
def own_walk(n):
 yield n
 for c in n.children:
  if c.type not in ('function_definition','lambda_expression','class_specifier'):yield from own_walk(c)
def extract(data,path):
 root=parser.parse(data).root_node; fs=[]
 for n in walk(root):
  if n.type!='function_definition':continue
  d=n.child_by_field_name('declarator');body=n.child_by_field_name('body')
  if not d or not body:continue
  while d.child_by_field_name('declarator'):d=d.child_by_field_name('declarator')
  name=data[d.start_byte:d.end_byte].decode()
  # GoogleTest TEST_F is parsed as a function definition with a macro declarator.
  if name in ('TEST_F','TEST'):
   sig=data[n.start_byte:body.start_byte].decode();m=re.search(r'TEST(?:_F)?\s*\(\s*([^,]+),\s*([^\)]+)\)',sig)
   if m:name=m[1].strip()+'.'+m[2].strip()
  calls=[]
  for c in own_walk(body):
   if c.type=='call_expression':
    f=c.child_by_field_name('function')
    if f:calls.append({'name':data[f.start_byte:f.end_byte].decode(),'line':c.start_point.row+1})
  fs.append(dict(name=name,path=path,start=n.start_point.row+1,end=n.end_point.row+1,text=data[n.start_byte:n.end_byte].decode(),calls=calls))
 # Recover GNU-style top-level definitions that preprocessor branches hide from the whole-file parse.
 if path.endswith('.c'):
  present={f['name'] for f in fs};txt=data.decode()
  for m in re.finditer(r'^([a-zA-Z_]\w*) \([^;{}]*?\n\{\n',txt,re.M):
   name=m[1]
   if name in present:continue
   end=re.search(r'^\}',txt[m.end():],re.M)
   if not end:continue
   stop=m.end()+end.end();chunk=txt[m.start():stop];start=txt[:m.start()].count('\n')+1
   subtree=parser.parse(('void '+chunk).encode()).root_node;calls=[]
   for c in walk(subtree):
    if c.type=='call_expression':
     f=c.child_by_field_name('function')
     if f:calls.append({'name':f.text.decode(),'line':start+c.start_point.row})
   fs.append(dict(name=name,path=path,start=start,end=start+chunk.count('\n'),text=chunk,calls=calls,recovery='GNU boundary plus parsed call expressions'))
 return fs
paths=git('diff','--name-only',BASE,HEAD).decode().splitlines(); allsets={};changed=[]
for rev in [BASE,HEAD]:
 rows=[]
 for path in paths:
  if path.endswith(('.c','.cpp','.h')):rows+=extract(git('show',rev+':'+path),path)
 allsets[rev]=rows
old={(f['path'],f['name']):f for f in allsets[BASE]};new={(f['path'],f['name']):f for f in allsets[HEAD]}
for key in sorted(old.keys()|new.keys()):
 a=old.get(key);b=new.get(key)
 if a and b and a['text']==b['text']:continue
 changed.append(dict(name=key[1],path=key[0],status='newly created' if not a else 'deleted' if not b else 'modified',base=a,head=b))
(OUT/'evidence/functions-ast.json').write_text(json.dumps(dict(base=BASE,head=HEAD,functions=changed,all_functions=allsets),indent=2))
for f in changed:print(f['status'],f['path'],f['name'],f['base']['start'] if f['base'] else '-',f['head']['start'] if f['head'] else '-')
print('TOTAL',len(changed))
