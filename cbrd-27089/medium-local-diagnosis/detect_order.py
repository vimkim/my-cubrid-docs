#!/usr/bin/env python3
"""Classify the exact three CI order signatures without sorting presentation."""
import argparse,json,hashlib
from collections import Counter
from pathlib import Path
NAMES=['to_char_order_by','to_number_order_by','to_timestamp_order_by']
def selections(path):
    blocks=[]
    for block in path.read_text().split('==================================================='):
        lines=[line.strip() for line in block.splitlines() if line.strip()]
        if lines and lines[0].startswith(('to_char(f)','to_number(f)','to_timestamp(f)')):
            rows=lines[1:]
            if 'Query plan:' in rows: rows=rows[:rows.index('Query plan:')]
            blocks.append(rows)
    return blocks

def classify(attempt,answers):
    cases=attempt/'scenario/_02_xtests/cases'
    result={}; flags=[]
    for name in NAMES:
        a=selections(answers/(name+'.answer')); h=selections(cases/(name+'.result'))
        assert len(a)==len(h)==(12 if name=='to_char_order_by' else 3),(name,len(a),len(h))
        groups=[]
        for i in range(0,len(a),3):
            groups.append({'unsorted':h[i],'answer_unsorted':a[i],
              'value_multiset_equal':Counter(h[i])==Counter(a[i]),
              'ascending_equal':h[i+1]==a[i+1],'descending_equal':h[i+2]==a[i+2]})
        if name=='to_timestamp_order_by': expected=[a[0][3],a[0][1],a[0][2],a[0][0],a[0][4]]
        else: expected=[a[0][4],a[0][2],a[0][3],a[0][0],a[0][1]]
        exact=True
        for i in range(0,len(a),3):
            wanted=[a[i][4],a[i][2],a[i][3],a[i][0],a[i][1]] if name!='to_timestamp_order_by' else expected
            exact &= h[i]==wanted
        contract=all(g['value_multiset_equal'] and g['ascending_equal'] and g['descending_equal'] for g in groups)
        state='CI_SIGNATURE' if exact and contract else ('ANSWER_EQUAL' if h==a else 'OTHER')
        flags.append(state);result[name]={'state':state,'groups':groups,'result_sha256':hashlib.sha256((cases/(name+'.result')).read_bytes()).hexdigest()}
    status='CI_SIGNATURE' if all(f=='CI_SIGNATURE' for f in flags) else ('ANSWER_EQUAL' if all(f=='ANSWER_EQUAL' for f in flags) else 'OTHER')
    return {'attempt':str(attempt),'status':status,'cases':result}
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('attempt',type=Path);p.add_argument('--answers',type=Path,default=Path('/home/vimkim/gh/cubrid-testcases/tc-pr-7927/medium/_02_xtests/answers'));p.add_argument('--output',type=Path)
    a=p.parse_args();j=classify(a.attempt,a.answers);s=json.dumps(j,indent=2)+'\n'
    if a.output:a.output.write_text(s)
    print(s);raise SystemExit({'CI_SIGNATURE':1,'ANSWER_EQUAL':0,'OTHER':2}[j['status']])
