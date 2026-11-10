import json, glob, statistics as st, sys, os
import sys
R=sys.argv[1]  # raw artifact directory (base/, cand/), kept outside Git
def load(label):
    out={}  # (tool,case) -> list of (start, [instr], [cyc])
    for d in sorted(glob.glob(f'{R}/{label}/*/')):
        tag=os.path.basename(d.rstrip('/'))
        for tool,f in (('bench','bench/summary.json'),('ordinary','ordinary/summary.json')):
            p=d+f
            if not os.path.exists(p): continue
            s=json.load(open(p))
            if not s.get('complete'): print('INCOMPLETE',p); continue
            cases={}
            for x in s['samples']:
                if x.get('warmup') or x['run']==0: continue
                c=x['case']
                cases.setdefault(c,[]).append((x['counters']['instructions:u']['value'],x['counters']['cycles:u']['value']))
            for c,v in cases.items():
                out.setdefault((tool,c),[]).append((tag,[a for a,b in v],[b for a,b in v]))
    return out
B=load('base'); C=load('cand')
def spread(v): return (max(v)-min(v))/st.median(v)*100
rows=[]
for k in sorted(B):
    if k not in C: continue
    print('==',k)
    res={}
    for name,D in (('base',B),('cand',C)):
        starts=D[k]
        meds=[st.median(i) for _,i,_ in starts]
        cm=[st.median(c) for _,_,c in starts]
        allv=[x for _,i,_ in starts for x in i]
        for (t,i,c),m,cc in zip(starts,meds,cm):
            print(f'  {name} {t} n={len(i)} instr_med={m:.0f} within_spread={spread(i):.3f}% cyc_med={cc:.0f}')
        res[name]=(st.median(meds),spread(meds) if len(meds)>1 else 0,max(spread(i) for _,i,_ in starts),st.median(cm),spread(cm) if len(cm)>1 else 0,len(starts),len(allv))
    b,c=res['base'],res['cand']
    pct=(b[0]-c[0])/b[0]*100; cp=(b[3]-c[3])/b[3]*100
    print(f'  instr: base {b[0]:.0f} cand {c[0]:.0f}  cand-vs-base {pct:+.3f}% (+=better)  between-start spread base {b[1]:.3f}% cand {c[1]:.3f}%  max within {b[2]:.3f}/{c[2]:.3f}%')
    print(f'  cycles: base {b[3]:.0f} cand {c[3]:.0f} {cp:+.2f}% between-start spread {b[4]:.1f}/{c[4]:.1f}%')
