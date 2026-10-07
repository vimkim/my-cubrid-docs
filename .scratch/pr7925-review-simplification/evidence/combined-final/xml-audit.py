import argparse, json
from pathlib import Path
from xml.etree import ElementTree as ET
p=argparse.ArgumentParser()
p.add_argument('xml_dir',type=Path)
p.add_argument('source')
p.add_argument('output',type=Path)
p.add_argument('--baseline',type=Path)
a=p.parse_args()
def audit(root):
    rows=[]
    files=[]
    disabled=0
    for path in sorted(root.glob('*.xml')):
        tree=ET.parse(path).getroot()
        tests=list(tree.iter('testcase'))
        disabled+=int(tree.get('disabled','0'))
        current=[]
        for case in tests:
            row={'suite':case.get('classname'),'name':case.get('name'),'run':case.get('status')=='run','failure':case.find('failure') is not None,'skipped':case.find('skipped') is not None or case.get('result')=='skipped'}
            rows.append(row)
            current.append(row)
        assert len(tests)==int(tree.get('tests',len(tests))), str(path)
        files.append({'file':path.name,'cases':len(tests),'failures':sum(r['failure'] for r in current),'skipped':sum(r['skipped'] for r in current)})
    identities=[(r['suite'],r['name']) for r in rows]
    assert len(identities)==len(set(identities)), 'Duplicate case identities'
    return {'files':files,'rows':rows,'summary':{'xml_files':len(files),'cases':len(rows),'run':sum(r['run'] for r in rows),'failures':sum(r['failure'] for r in rows),'skipped':sum(r['skipped'] for r in rows),'disabled':disabled}}
r=audit(a.xml_dir)
r['source_commit']=a.source
r['xml_directory']=str(a.xml_dir)
r['dependency_boundary']='4be72fc209ae9cb8aa1709573d7d0ae7fc06df7c'
if a.baseline:
    base=audit(a.baseline)
    actual={(row['suite'],row['name']) for row in r['rows']}
    expected={(row['suite'],row['name']) for row in base['rows']}
    r['focused_baseline_identities_retained']=expected<=actual
    r['focused_baseline_case_count']=len(expected)
    assert expected<=actual, sorted(expected-actual)
a.output.write_text(json.dumps(r,indent=2)+'\n')
print(json.dumps({'source':a.source,**r['summary'],'focused_baseline_identities_retained':r.get('focused_baseline_identities_retained')}))
assert r['summary']['xml_files']>0
assert r['summary']['run']==r['summary']['cases']
assert r['summary']['failures']==r['summary']['skipped']==r['summary']['disabled']==0
