# Import the extractor without rerunning its top-level report generation.
from pathlib import Path
exec(Path(__file__).with_name('extract_functions.py').read_text().split("paths=git(")[0])
x=json.loads((OUT/'evidence/functions-ast.json').read_text())
names={f['name'] for f in x['functions'] if f['path'].startswith('src/')}
pat='('+'|'.join(sorted(names))+')[[:space:]]*\\('
indexes={}
for rev in [BASE,HEAD]:
 hits=git('grep','-l','-E',pat,rev,'--','src','unit_tests').decode().splitlines();files=[h.split(':',1)[1] for h in hits if h.endswith(('.c','.cpp','.h','.hpp'))]
 rows=[]
 for path in files:rows+=extract(git('show',rev+':'+path),path)
 indexes[rev]=rows
 print(rev[:8],len(files),'candidate files',len(rows),'function definitions')
(OUT/'evidence/callers-index.json').write_text(json.dumps(indexes,indent=2))
