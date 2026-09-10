#!/usr/bin/env python3
"""Rebuild the bilingual PR7600 reviewer materials from owned source briefs."""
from pathlib import Path
import base64, datetime, hashlib, html, importlib.util, json, os, re, subprocess, sys
import markdown
from annotations import HUNKS, TESTS
from graphs import build_graphs

ROOT=Path(os.environ.get('PR7600_SOURCE_ROOT', '/home/vimkim/gh/cb/CBRD-27089-has-oos-but-no-oos'))
OUT=Path(__file__).resolve().parents[1]
HEAD='479cd960ec04196c92bf9789b1fc340af9046c2c'
BASE='f4299ac0cd777a2a964c1f197ae5ebf9841a4936'
PR='https://github.com/CUBRID/cubrid/pull/7600'
def git(*args):return subprocess.check_output(['git',*args],cwd=ROOT,text=True)
assert git('rev-parse','HEAD').strip()==HEAD, 'Source revision changed'
def sha(s):return hashlib.sha256(s.encode()).hexdigest()
def diff_link(path,line=None,side='R'):
    return PR+'/files#diff-'+sha(path)+(side+str(line) if line else '')
def blob(path,line,rev=HEAD):return f'https://github.com/CUBRID/cubrid/blob/{rev}/{path}#L{line}'
def md(s):return markdown.markdown(s,extensions=['tables','fenced_code','toc'])
def esc(s):return html.escape(str(s))

raw=(OUT/'evidence/pr.diff').read_text()
hunks=[];current=None;file=None
for line in raw.splitlines():
    if line.startswith('diff --git'):current=None
    if line.startswith('+++ b/'):file=line[6:]
    if line.startswith('@@'):
        m=re.match(r'@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@(.*)',line)
        current=dict(id=len(hunks)+1,path=file,old=int(m[1]),old_count=int(m[2] or 1),new=int(m[3]),new_count=int(m[4] or 1),header=line,lines=[])
        hunks.append(current)
    elif current is not None:current['lines'].append(line)
assert len(hunks)==len(HUNKS)==63
for h,(title,en,ko) in zip(hunks,HUNKS):h.update(title=title,en=en,ko=ko)

test_path='unit_tests/oos/sql/test_oos_sql_show.cpp'
src=git('show',HEAD+':'+test_path).splitlines()
starts=[(i+1,re.search(r'TEST_F \(OosSqlShow, (\w+)\)',s)[1]) for i,s in enumerate(src) if re.search(r'TEST_F \(OosSqlShow, (\w+)\)',s)]
added=[(n,name) for n,name in starts if n>=437]
assert len(added)==len(TESTS)==28
tests=[]
for i,((n,name),(en,ko)) in enumerate(zip(added,TESTS)):
    end=added[i+1][0]-1 if i+1<len(added) else next(j+1 for j in range(n,len(src)) if src[j]=='main (int argc, char **argv)')-2
    while not src[end-1].strip():end-=1
    tests.append(dict(name=name,start=n,end=end,en=en,ko=ko))

def render_code(h):
    old,new=h['old'],h['new'];rows=[]
    for s in h['lines']:
        if not s or s[0] not in ' +-':continue
        typ='added' if s[0]=='+' else 'removed' if s[0]=='-' else 'context'
        o='' if s[0]=='+' else old;n='' if s[0]=='-' else new
        u=blob(h['path'],n or o,HEAD if n else BASE)
        rows.append(f'<tr class="{typ}"><td class="ln">{o}</td><td class="ln"><a href="{u}" target="_blank" rel="noreferrer">{n}</a></td><td class="sign">{esc(s[0])}</td><td class="code">{esc(s[1:])}</td></tr>')
        if s[0]!='+':old+=1
        if s[0]!='-':new+=1
    assert old==h['old']+h['old_count'] and new==h['new']+h['new_count'],h['id']
    return '<div class="code-scroll" tabindex="0" aria-label="old/new line 번호가 있는 diff"><table class="diff-code"><thead><tr><th>old</th><th>new</th><th>±</th><th>code</th></tr></thead><tbody>'+''.join(rows)+'</tbody></table></div>'

english=(OUT/'authoring/reviewer-guide.en.md').read_text()
# Fact-check corrections against the final pinned helper's exact numbered source.
for a,b in [('12139–12155','12138–12153'),('12157–12168','12154–12164'),('12169–12176','12165–12172'),('12173–12182','12173–12180'),('12182–12187','12181–12185'),('12188–12206','12187–12203'),('12207–12215','12204–12211'),('12217–12229','12213–12224')]:english=english.replace(a,b)
english=english.replace("The exact line listing in the diff appendix is authoritative if a row in this teaching table spans a neighboring statement. ","")
(OUT/'authoring/reviewer-guide.en.md').write_text(english)
korean=(OUT/'authoring/reviewer-guide.ko.md').read_text()
en_append='\n\n## Complete annotated diff\n\nEach H-number corresponds to one unified diff hunk, with its old/new source intervals. Deleted lines are included. Rationale is grounded in the linked code and accepted decision; this is not an assertion of private author intent.\n'
ko_append='\n\n## 전체 diff 부록\n\nH 번호는 unified diff hunk 하나에 대응한다. 삭제한 줄도 포함한다. 설명은 실행 코드와 기록된 결정에 기반하며 작성자의 숨은 의도를 단정하지 않는다.\n'
cards=[]
for h in hunks:
    id=f"hunk-{h['id']:02d}"
    code=h['header']+'\n'+'\n'.join(h['lines'])
    source=f"[{h['path']} old:{h['old']} / new:{h['new']}]({diff_link(h['path'],h['new'])})"
    en_append+=f"\n### H{h['id']:02d} — {h['title']}\n\n{source}\n\n{h['en']}\n\n```diff\n{code}\n```\n"
    ko_append+=f"\n### H{h['id']:02d} — {h['title']}\n\n{source}\n\n{h['ko']}\n\n```diff\n{code}\n```\n"
    cards.append(f'<article class="hunk" id="{id}" data-search="{esc(h["path"]+" "+h["title"]+" "+h["ko"])}"><h3><a href="#{id}">H{h["id"]:02d}</a> · {esc(h["title"])}</h3><p class="meta">{esc(h["path"])} · old {h["old"]}–{h["old"]+h["old_count"]-1} / new {h["new"]}–{h["new"]+h["new_count"]-1}</p><p>{esc(h["ko"])}</p><p><a href="{diff_link(h["path"],h["new"])}">GitHub diff</a> · <a href="{blob(h["path"],h["new"])}">고정 HEAD 소스</a></p><details class="diff-details"><summary>정확한 변경 줄 펼치기 · {sum(s.startswith("+") for s in h["lines"])} 추가 / {sum(s.startswith("-") for s in h["lines"])} 삭제</summary>{render_code(h)}</details></article>')

testhtml=[];test_en='\n## Added SQL test catalog\n\nThese are source-level test contracts. The recorded 32/32 result is historical, not a run performed for this report.\n';test_ko='\n## 추가 SQL 테스트 설명\n\n테스트 코드의 계약이다. 32/32는 과거 실행이며 이번 실행 결과가 아니다.\n'
for i,t in enumerate(tests,1):
    link=blob(test_path,t['start'])
    test_en+=f"\n### T{i:02d} — {t['name']}\n\n[Source {t['start']}–{t['end']}]({link}). {t['en']}\n"
    test_ko+=f"\n### T{i:02d} — {t['name']}\n\n[Source {t['start']}–{t['end']}]({link}). {t['ko']}\n"
    code='\n'.join(f'{j+1:4d}  {src[j]}' for j in range(t['start']-1,t['end']))
    testhtml.append(f'<article class="test-entry" id="test-{i:02d}"><h3>T{i:02d} · {esc(t["name"])}</h3><p>{esc(t["ko"])}</p><p class="meta"><a href="{link}">Source {t["start"]}–{t["end"]}</a> · <a href="#hunk-62">H62</a></p><details><summary>이 테스트 코드 읽기</summary><pre><code>{esc(code)}</code></pre></details></article>')
(OUT/'review.en.md').write_text(english+test_en+en_append)
(OUT/'review.ko.md').write_text(korean+test_ko+ko_append)

CSS='''
:root{--bg:#f1f5f4;--surface:#fff;--border:#c5d4cf;--text:#192f2b;--text-dim:#526b63;--accent:#006c59;--good:#186949;--bad:#a62d35;--warn:#885707;--blue:#245d86;--addbg:#e8f5ed;--delbg:#fff0f0;--font:"IBM Plex Sans","Noto Sans CJK KR","Noto Sans KR",sans-serif;--mono:"IBM Plex Mono","DejaVu Sans Mono",monospace}
@media(prefers-color-scheme:dark){:root{--bg:#101e1b;--surface:#182b26;--border:#365148;--text:#e6f0ec;--text-dim:#aec6bc;--accent:#79d7b7;--good:#8de0ad;--bad:#ffacb1;--warn:#f4cc85;--blue:#9cc9ed;--addbg:#1c3b2b;--delbg:#42262a}}
*{box-sizing:border-box}html{font-size:17px;scroll-behavior:smooth}body{margin:0;background:var(--bg);color:var(--text);font-family:var(--font);line-height:1.7}a{color:var(--accent);text-underline-offset:3px}button,input,select{font:inherit}button,select{cursor:pointer;background:var(--surface);color:var(--text);border:1px solid var(--border);padding:.45rem .8rem;border-radius:3px}a:focus-visible,button:focus-visible,input:focus-visible,summary:focus-visible,[tabindex]:focus-visible{outline:3px solid var(--accent);outline-offset:3px}input{min-width:0;padding:.5rem;background:var(--surface);color:var(--text);border:1px solid var(--border)}.top{border-bottom:1px solid var(--border);padding:1.2rem 2rem;display:flex;gap:1.4rem;flex-wrap:wrap;align-items:center}.top strong{margin-right:auto}.wrap{max-width:1560px;margin:auto;display:grid;grid-template-columns:205px minmax(0,1fr);gap:2rem;padding:1.8rem 2rem}.toc{min-width:0;max-width:100%;position:sticky;top:1rem;align-self:start;max-height:calc(100dvh - 2rem);overflow:auto;font-size:.8rem}.toc a{display:block;padding:.45rem .6rem;text-decoration:none;border-left:2px solid transparent}.toc a.active{border-color:var(--accent);background:var(--surface)}main{min-width:0}h1{font-size:2.3rem;line-height:1.2;text-wrap:balance;letter-spacing:-.035em;margin:.4rem 0 1rem}h2{font-size:1.5rem;margin:2.5rem 0 1rem;line-height:1.4;scroll-margin-top:1.5rem}h3{font-size:1.02rem;overflow-wrap:anywhere;line-height:1.5}p{max-width:78ch;overflow-wrap:anywhere}h2{overflow-wrap:anywhere}section{min-width:0}.meta{font:.75rem/1.6 var(--mono);color:var(--text-dim);overflow-wrap:anywhere}.lead{font-size:1.1rem}.facts{display:flex;gap:1.5rem;flex-wrap:wrap;padding:1rem 0;border-block:1px solid var(--border)}.facts b{font-size:1.5rem}.facts span{color:var(--text-dim);font-size:.8rem}.cols{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:1rem}.ve-card{padding:1.3rem;background:var(--surface);border:1px solid var(--border);min-width:0}.ve-card h3{margin-top:0}.before{border-top:4px solid var(--bad)}.after{border-top:4px solid var(--good)}.track{display:grid;gap:.4rem;margin-top:1rem}.track div{padding:.7rem;border:1px solid var(--border)}.arrow{font-size:.8rem;text-align:center;color:var(--text-dim);padding:.1rem!important;border:0!important}.split{display:grid;grid-template-columns:1fr 1fr;gap:.7rem}.bad{color:var(--bad)}.good{color:var(--good)}.warn{color:var(--warn)}figure{margin:1.5rem 0}figcaption{font-size:.85rem;color:var(--text-dim);margin-top:.6rem}.reading table,table.matrix{border-collapse:collapse;width:100%;background:var(--surface);font-size:.87rem}.reading th,.reading td,table.matrix th,table.matrix td{border:1px solid var(--border);text-align:left;padding:.8rem;vertical-align:top;overflow-wrap:anywhere}.reading table{display:table}.table-scroll{overflow:auto}.reading{max-width:1100px}.reading p,.reading li{overflow-wrap:anywhere}.reading h1{display:none}.reading h2:first-of-type{margin-top:1rem}code,pre{font-family:var(--mono);font-size:.79rem}p code,li code,td code{overflow-wrap:anywhere}pre{overflow:auto;background:var(--surface);border:1px solid var(--border);padding:1rem;line-height:1.65;max-height:70vh}summary{cursor:pointer;padding:.6rem .8rem;background:var(--bg);font-size:.85rem}.hunk,.test-entry{background:var(--surface);padding:1.25rem;margin:1rem 0;border:1px solid var(--border);scroll-margin-top:1.5rem}.hunk:target,.test-entry:target{outline:2px solid var(--accent)}.hunk h3,.test-entry h3{margin-top:0}.hunk p,.test-entry p{max-width:none}.toolbar{display:flex;gap:.6rem;flex-wrap:wrap;position:sticky;top:0;background:var(--bg);padding:.8rem 0;z-index:5;border-bottom:1px solid var(--border)}.toolbar input{flex:1 1 16rem}.code-scroll{overflow:auto;max-height:70vh}.diff-code{border-collapse:collapse;font: .76rem/1.7 var(--mono);width:100%;white-space:pre;tab-size:8}.diff-code th{position:sticky;top:0;background:var(--surface);text-align:left;border-bottom:1px solid var(--border)}.diff-code .ln{color:var(--text-dim);text-align:right;padding:0 .7rem;user-select:none;width:3.5rem}.diff-code .sign{width:1.2rem}.diff-code td.code{padding-right:1rem}.added{background:var(--addbg)}.removed{background:var(--delbg)}.added .sign{color:var(--good)}.removed .sign{color:var(--bad)}.context{opacity:.85}.file-map{font-family:var(--mono);font-size:.78rem;overflow-wrap:anywhere}.file-map a{display:inline}.foot{font-size:.8rem;color:var(--text-dim);padding:2rem;border-top:1px solid var(--border)}[hidden]{display:none!important}
@media(max-width:1000px){.wrap{grid-template-columns:1fr;padding:1rem;gap:1rem}.toc{position:sticky;top:0;z-index:9;display:flex;gap:.3rem;background:var(--bg);overflow:auto;white-space:nowrap;max-height:none;padding:.3rem}.toc a{border-left:0;border-bottom:2px solid transparent}.toc a.active{border-bottom-color:var(--accent)}.top{padding:1rem}.cols{grid-template-columns:1fr}.toolbar{position:relative}h1{font-size:1.8rem}}@media(prefers-reduced-motion:reduce){html{scroll-behavior:auto}}@media print{.toc,.toolbar,.top{display:none}.wrap{display:block;padding:0}body{background:white;color:black}.hunk{break-inside:avoid}pre,.code-scroll{max-height:none}a{color:inherit}}
'''
favicon='<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 64 64%22%3E%3Crect width=%2264%22 height=%2264%22 fill=%22%23006c59%22/%3E%3Ctext x=%2232%22 y=%2244%22 text-anchor=%22middle%22 font-size=%2240%22 fill=%22white%22%3EP%3C/text%3E%3C/svg%3E">'
comparison='''<figure><div class="cols" role="img" aria-label="변경 전 root OOS와 child record의 분리, 변경 후 child 소유권 일치"><div class="ve-card before"><h3 class="bad">변경 전 · transform이 먼저</h3><div class="track"><div>Root class로 전체 record 변환</div><div class="arrow">OOS 생성 ↓</div><div>Root heap의 OOS file에 chain 기록</div><div class="arrow">이후 partition pruning ↓</div><div>Record는 p0 child heap에 저장</div></div><p class="bad">Stub의 주소로 읽을 수 있어도 owner heap은 다르다.</p></div><div class="ve-card after"><h3 class="good">현재 · key routing이 먼저</h3><div class="track"><div>Effective key로 p0 선택</div><div class="arrow">선택 owner 전달 ↓</div><div>전체 row 변환 · p0 OOS file에 기록</div><div class="arrow">최종 record routing · 일치 확인 ↓</div><div>Record도 p0 child heap에 저장</div></div><p class="good">Source identity를 유지하며 destination owner를 지정한다.</p></div></div><figcaption>핵심 차이: OOS file을 선택하기 전에 destination을 안다. <a href="#hunk-54">H54</a> · <a href="#hunk-28">H28</a> · <a href="#hunk-41">H41</a></figcaption></figure>'''
files=[]
for line in git('diff','--numstat',BASE+'...'+HEAD).splitlines():
    a,d,f=line.split('\t');files.append(dict(path=f,additions=int(a),deletions=int(d)))
filemap=''.join(f'<tr><td><a href="{diff_link(f["path"])}">{esc(f["path"])}</a></td><td class="good">+{f["additions"]}</td><td class="bad">−{f["deletions"]}</td></tr>' for f in files)
mechanics='''<section id="map"><h2>변경 파일과 책임</h2><p>새 파일·삭제 파일·dependency/config 교체는 없다. 모든 변경은 기존 10개 파일의 수정이다. Runtime 구현 7개와 테스트/등록 3개로 나뉜다.</p><div class="table-scroll"><table class="matrix file-map"><thead><tr><th>파일</th><th>추가</th><th>삭제</th></tr></thead><tbody>'''+filemap+'''</tbody></table></div><p><a href="index.html">의존 관계와 데이터 흐름을 interactive map으로 보기 →</a></p></section>'''
nav=[('overview','문제와 변경'),('map','변경 파일'),('guide','구현 설명'),('tests','28개 테스트'),('diff','63개 diff hunk'),('audit','근거와 검증')]
js='''
const input=document.querySelector('#search');const hunks=[...document.querySelectorAll('.hunk')];
function filter(){let q=input.value.trim().toLowerCase();let n=0;hunks.forEach(h=>{h.hidden=!h.dataset.search.toLowerCase().includes(q);if(!h.hidden)n++});document.querySelector('#count').textContent=n+' / 63 hunks'}input.addEventListener('input',filter);
document.querySelector('#expand').onclick=()=>hunks.filter(h=>!h.hidden).forEach(h=>h.querySelector('details').open=true);
document.querySelector('#collapse').onclick=()=>document.querySelectorAll('.diff-details').forEach(d=>d.open=false);
function reveal(){if(location.hash.startsWith('#hunk-')){input.value='';filter();let h=document.querySelector(location.hash);if(h){h.hidden=false;h.querySelector('details').open=true;h.scrollIntoView()}}}window.addEventListener('hashchange',reveal);reveal();
const links=[...document.querySelectorAll('.toc a')];const observer=new IntersectionObserver(entries=>{entries.forEach(e=>{if(e.isIntersecting){links.forEach(a=>a.classList.toggle('active',a.hash==='#'+e.target.id))}})},{rootMargin:'-5% 0px -75% 0px'});links.forEach(a=>{let s=document.querySelector(a.hash);if(s)observer.observe(s)});
document.addEventListener('keydown',e=>{if(e.key==='/'&&!['INPUT','TEXTAREA'].includes(e.target.tagName)){e.preventDefault();input.focus();input.scrollIntoView({block:'center'})}});
'''
audit='''<section id="audit"><h2>근거와 검증을 구별하기</h2><div class="ve-card"><p><strong>이 페이지가 수행한 일:</strong> 고정 source와 base diff 대조, 63 hunk 및 28 test 설명, current/old 구현 구별, offline HTML 생성과 브라우저 검증.</p><p><strong>새로 수행하지 않은 일:</strong> 엔진 build/test, CI 재실행, 성능 측정, disabled regression 재실행. 과거 32/32 결과와 별도 failed vacuum 결과를 이번 실행으로 표시하지 않는다.</p><p class="warn">검토 gate: SERVER_MODE lifecycle · control performance acceptance · final integrated evidence.</p><p><a href="evidence/pr.json">PR snapshot</a> · <a href="evidence/pr.diff">원본 diff</a> · <a href="evidence/manifest.json">revision·파일 hash</a> · <a href="evidence/validation.json">문서 검증 기록</a> · <a href="evidence/fact-check.md">Fact check</a></p></div></section>'''
page=f'''<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>PR7600 · OOS owner와 partition routing</title>{favicon}<style>{CSS}</style></head><body><header class="top"><strong>PR #7600 · Reviewer reading</strong><a href="index.html">네 가지 관점으로 발표하기</a><a href="review.en.md">English Markdown</a><a href="review.ko.md">한국어 Markdown</a></header><div class="wrap"><nav class="toc" aria-label="목차">{''.join(f'<a href="#{id}">{label}</a>' for id,label in nav)}</nav><main><section id="overview"><p class="meta">CUBRID / CBRD-27089 · HEAD 479cd960ec · BASE f4299ac0cd</p><h1>레코드를 보낼 곳을 먼저 결정한다</h1><p class="lead">Partition key로 목적지를 고른 뒤, 그 child heap의 OOS file에 값을 기록한다. Source identity와 destination owner를 분리하는 것이 이 변경의 핵심이다.</p><div class="facts"><div><b>10</b> <span>files</span></div><div><b>63</b> <span>diff hunks</span></div><div><b>28</b> <span>added SQL tests</span></div><div><b>1</b> <span>disabled vacuum regression</span></div></div>{comparison}</section>{mechanics}<section id="guide" class="reading"><h2>구현을 끝까지 읽기</h2>{md(korean)}</section><section id="tests"><h2>추가된 28개 SQL 테스트의 이유</h2><p>실패를 구별하는 oracle과 검증 범위를 먼저 읽고, 필요한 테스트 코드만 펼친다. 전체 suite에는 기존 4개 테스트가 더 있다.</p>{''.join(testhtml)}</section><section id="diff"><h2>전체 diff · 추가한 줄과 삭제한 줄</h2><p>H 번호는 고정 diff와 일대일 대응한다. 블록 설명을 읽은 뒤 정확한 줄을 펼친다. New line 링크는 고정 HEAD 소스로 연결된다.</p><div class="toolbar"><input id="search" type="search" aria-label="파일·이유 검색" placeholder="파일명 또는 설명 검색 · / 키"><button id="expand">검색 결과 코드 펼치기</button><button id="collapse">코드 모두 접기</button><span id="count" class="meta" aria-live="polite">63 / 63 hunks</span></div>{''.join(cards)}</section>{audit}</main></div><footer class="foot">pr-walkthrough + visual-explainer · English Markdown → Korean HTML · Source snapshot 479cd960ec · 정적 설명과 과거 실행을 구분한다.</footer><script>{js}</script></body></html>'''
(OUT/'review.ko.html').write_text(page)

# Reuse Warp's deterministic renderer. Embed its pinned D3 build so presentation also works offline.
spec=importlib.util.spec_from_file_location('warp_runtime',Path.home()/'.codex/skills/pr-walkthrough/scripts/d3_canvas_runtime.py')
runtime=importlib.util.module_from_spec(spec);spec.loader.exec_module(runtime)
data=dict(meta=dict(title='PR #7600 · OOS owner를 먼저 결정하기',prUrl=PR,baseRef='feat/oos @ f4299ac0cd',headRef='479cd960ec',summary='기본 구조 → 데이터 흐름 → 코드 의존 → SQL 관찰. 각 관점에서 Next tour step으로 진행하고, 오른쪽에서 근거와 전체 diff를 연다.'),graphs=build_graphs(diff_link))
(OUT/'graph.json').write_text(json.dumps(data,ensure_ascii=False,indent=2))
walk=runtime.html_template(data).replace('<html lang="en">','<html lang="ko">')
walk=walk.replace('</head>',favicon+'''<style>:root{--warp-accent:#9c58f0;--warp-font-sans:'Matter','DM Sans','Noto Sans CJK KR',sans-serif}html{font-size:17px}.d3-walkthrough-header{background:#121212;padding:20px 26px}.d3-walkthrough-header h1{font-size:2rem;line-height:1.25;letter-spacing:-.02em}.d3-canvas-layout{grid-template-columns:250px minmax(360px,1fr) 350px}.d3-detail-panel,.d3-control-panel{font-size:.88rem;line-height:1.65}.d3-detail-title{overflow-wrap:anywhere}.d3-summary{font-size:1rem}.d3-canvas-stage{background:#121212}.d3-control-button,.d3-graph-toggle,.d3-tour-card,.d3-search{border-radius:3px}.d3-detail-section:has(.d3-empty){display:none}.d3-help{color:#b4b4b2}.d3-file-link{overflow-wrap:anywhere}.d3-detail-panel{max-height:calc(100vh - 185px)}a:focus-visible,button:focus-visible,input:focus-visible{outline:3px solid #c59fff;outline-offset:2px}#pr-walkthrough-canvas{min-height:720px}.doclinks{display:flex;gap:18px;font-size:.85rem}@media(max-width:1050px){.d3-canvas-layout{grid-template-columns:1fr;grid-template-rows:auto 680px auto}.d3-control-panel{max-height:none}.d3-control-stack{grid-template-columns:repeat(2,minmax(0,1fr))}.d3-detail-panel{max-height:none}.d3-walkthrough-header h1{font-size:1.55rem}.d3-help{display:none}}@media(prefers-reduced-motion:reduce){*{scroll-behavior:auto!important}}</style></head>''')
walk=walk.replace('<div class="d3-kicker">Warp PR walkthrough</div>','<div class="d3-kicker">PR reviewer walkthrough</div>')
walk=walk.replace('</header>','<nav class="doclinks"><a href="review.ko.html">한국어 해설 · 63개 diff hunk</a><a href="review.en.md">English Markdown</a><a href="evidence/validation.json">검증 기록</a></nav></header>',1)
encoded_d3=base64.b64encode((OUT/'assets/d3-7.9.0.min.js').read_bytes()).decode('ascii')
offline_runtime='<script>(()=>{const s=document.createElement("script");s.textContent=new TextDecoder().decode(Uint8Array.from(atob("'+encoded_d3+'"),c=>c.charCodeAt(0)));document.head.appendChild(s)})();</script>'
walk=walk.replace('<script>window.PR_WALKTHROUGH_D3_DATA',offline_runtime+'<script>window.PR_WALKTHROUGH_D3_DATA',1)
for en,ko in [('Tour context','지금 설명할 내용'),('Explanation','설명'),('Changed files','변경 파일'),('Existing review discussion','기존 리뷰'),('None attached.','첨부 없음'),('No additional detail provided.','추가 설명 없음'),('Selected point','선택한 지점'),('Links','더 읽기'),('Open comment','리뷰 원문'),('Open PR','PR 열기')]:walk=walk.replace(en,ko)
(OUT/'index.html').write_text(walk)

sources={f['path']:sha(git('show',HEAD+':'+f['path'])) for f in files}
manifest=dict(created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),source_root=str(ROOT),head=HEAD,base=BASE,merge_base=git('merge-base',BASE,HEAD).strip(),pr_url=PR,files=files,hunks=[{k:v for k,v in h.items() if k!='lines'} for h in hunks],tests=tests,source_sha256=sources,skills=['warpdotdev/common-skills:.agents/skills/pr-walkthrough','nicobailon/visual-explainer:plugins/visual-explainer'],d3=dict(version='7.9.0',url='https://cdn.jsdelivr.net/npm/d3@7.9.0/dist/d3.min.js',embedded=True,sha256=sha((OUT/'assets/d3-7.9.0.min.js').read_text())),engine_tests_run=False,notes=['English source first; Korean rendering follows user preference over visual-explainer default.','Uses pr-walkthrough helper, with generated-document styling/localization adaptations and embedded official D3 for offline use.','Review readiness is not merge acceptance.','Existing local CCI mismatch not included in source diff.'])
(OUT/'evidence/manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2))
(OUT/'README.md').write_text('''# PR7600 reviewer materials

- [Korean guided walkthrough](index.html): pr-walkthrough, four views, source links and guided tours.
- [Korean visual diff explanation](review.ko.html): visual-explainer, before/after ownership, source walkthrough, 28 new SQL test explanations and all 63 annotated diff hunks.
- [English source Markdown](review.en.md) and [Korean Markdown](review.ko.md).
- [Source and coverage manifest](evidence/manifest.json), [artifact verification](evidence/validation.json), [fact-check](evidence/fact-check.md).

Open the HTML files directly. D3 7.9.0 is embedded from its pinned official distribution; neither page needs a server or network for presentation. GitHub/JIRA evidence links require network. System font fallbacks support Korean; font appearance varies by machine.

The four English view/control labels are retained for the upstream validator; explanation text is Korean. Search, node selection, guided tours, zoom, pan and keyboard controls are available on the map. The reading page supports hunk search, code expansion and exact revision links. All added/deleted lines are retained; related lines are explained as semantic blocks.

The review's source baseline is feat/oos f4299ac0cd and head is 479cd960ec. No engine tests were run for document production. Historical results and disabled tests are labeled explicitly. This is a local artifact, not a merge approval or newly posted PR review.

Rebuild from the original checkout: `python3 .warp/pr-walkthrough/authoring/build.py` (Python Markdown required). Authoring English/Korean briefs and annotation data are retained. The installed skills are not modified. The renderer helper is loaded from the installed pr-walkthrough skill; its version/hash is captured in the installation manifest.
''')
print(json.dumps(dict(output=str(OUT),files=10,hunks=len(hunks),added_sql_tests=len(tests),graph_nodes=sum(len(g['nodes']) for g in data['graphs']),html_bytes=len(page.encode())+len(walk.encode()))))
