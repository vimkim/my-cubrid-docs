#!/usr/bin/env python3
"""Build an offline book from editable Markdown/SVG and a pinned Git diff.

Requires Python-Markdown (available in this environment). No network access.
Only generated artifacts inside this teaching directory are written.
"""
import hashlib
import html
import json
from pathlib import Path
import re
import subprocess
import sys
import xml.etree.ElementTree as ET

import markdown
from claim_catalog import CLAIMS, BASE
from hunk_notes import NOTES, LINE_GUIDES

ROOT = Path(__file__).resolve().parents[1]
HEAD = 'b871ea386d2c5419b7abae07dda58b9b7f36377a'
SOURCE = Path('/home/vimkim/gh/cb/CBRD-27089-has-oos-but-no-oos')
REPO = 'https://github.com/CUBRID/cubrid'

def git(*args):
    return subprocess.check_output(['git','-C',str(SOURCE),*args], text=True)

def write(relative, value):
    path = ROOT / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value, encoding='utf-8')

def dump(relative, value):
    write(relative, json.dumps(value, indent=2, ensure_ascii=False) + '\n')

def source_link(path, start, end, rev=HEAD):
    return f'[{path}:{start}–{end}]({REPO}/blob/{rev}/{path}#L{start}-L{end})'

def hunks(diff):
    result = []
    path = None
    current = None
    for line in diff.splitlines():
        if line.startswith('diff --git '):
            path = line.split(' b/',1)[1]
            current = None
        elif line.startswith('@@ '):
            match = re.match(r'@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@(.*)',line)
            old, oldcount, new, newcount, symbol = match.groups()
            current = dict(path=path,old=int(old),new=int(new),old_count=int(oldcount or 1),
                           new_count=int(newcount or 1),symbol=symbol.strip(),header=line,lines=[])
            result.append(current)
        elif current is not None and line[:1] in (' ','+','-','\\'):
            current['lines'].append(line)
    return result

def make_evidence():
    if git('rev-parse','HEAD').strip() != HEAD:
        raise RuntimeError('Source HEAD moved; revise provenance before rebuilding this pinned book')
    if git('merge-base',BASE,HEAD).strip() != BASE:
        raise RuntimeError('Unexpected merge base')
    diff = git('diff','--no-ext-diff','--no-color','--unified=3',f'{BASE}...{HEAD}')
    parsed = hunks(diff)
    keys = {(h['path'],h['old']) for h in parsed}
    if keys != set(NOTES):
        raise RuntimeError(f'Hunk commentary mismatch: missing {keys-set(NOTES)}, extra {set(NOTES)-keys}')
    changed = git('diff','--name-only',f'{BASE}...{HEAD}').splitlines()
    for path in changed:
        if (SOURCE/path).read_bytes() != subprocess.check_output(['git','-C',str(SOURCE),'show',f'{HEAD}:{path}']):
            raise RuntimeError(f'Changed evidence file differs from pinned head: {path}')
    write('evidence/pr-7600.patch',diff)
    write('evidence/git-provenance.txt',f'HEAD {HEAD}\nBASE {BASE}\nMERGE_BASE {BASE}\n'+git('diff','--stat',f'{BASE}...{HEAD}')+'\nWorking tree (excluded unrelated changes):\n'+git('status','--short'))
    write('evidence/second-commit.patch',git('show','--format=fuller','--no-color',HEAD,'--', 'src/storage/heap_file.c', 'unit_tests/oos/sql/test_oos_sql_show.cpp'))
    claims = list(CLAIMS)
    coverage = []
    content = ['# 6. Every changed line, in its source context','',
               'This chapter covers all 30 default-context Git hunks. Read chapters 1–5 first, then use this appendix to connect every addition and deletion to the mechanism. The complete original diff is preserved in `evidence/pr-7600.patch`. Blank lines and brace-only changes are shown along with executable statements.','',
               'Each listing shows **old line | new line | diff sign | source text**. A dash means that side has no line. `+` is added at the head, `-` is deleted from the base, and a blank sign is unchanged context. Source text is preserved apart from display tab expansion. Hunk headers come from Git and may name a preceding symbol; the commentary identifies the actual affected function.','',
               'For each hunk: identify inputs, follow the described state changes, then explain what its omission would affect. Structural signature/include hunks make the changed code callable; they need not each produce an independent runtime effect.','',
               '## Coverage index','', '| Hunk | File | Old lines | New lines | Lesson |','|---|---|---|---|---|']
    details = []
    for index,h in enumerate(parsed,1):
        title, explanation = NOTES[(h['path'],h['old'])]
        identifier = f'H{index:02}'
        cid = f'C-{100+index:03}'
        old_end=h['old']+h['old_count']-1
        new_end=h['new']+h['new_count']-1
        content.append(f'| [{identifier}](#{identifier.lower()}) | `{h["path"]}` | {h["old"]}–{old_end} | {h["new"]}–{new_end} | {title} |')
        old,new=h['old'],h['new']
        listing=[]
        adds=dels=0
        for line in h['lines']:
            prefix=line[0]
            if prefix=='\\':
                listing.append(line)
                continue
            left=str(old) if prefix!='+' else '—'
            right=str(new) if prefix!='-' else '—'
            listing.append(f'{left:>6} {right:>6} {prefix} {line[1:]}')
            old += prefix!='+'
            new += prefix!='-'
            adds += prefix=='+'
            dels += prefix=='-'
        assert old==old_end+1 and new==new_end+1
        details.extend([f'<a id="{identifier.lower()}"></a>',f'## {identifier}. {title}','',
                        f'[{cid}] Head: {source_link(h["path"],h["new"],new_end)}. Base: {source_link(h["path"],h["old"],old_end,BASE)}.','',
                        '```text',*listing,'```','',explanation,''])
        if (h['path'],h['old']) in LINE_GUIDES:
            details += ['### Statement-by-statement reading guide','', '| Head lines | Meaning |', '|---|---|']
            details += [f'| {interval} | {meaning} |' for interval,meaning in LINE_GUIDES[(h['path'],h['old'])]]
            details += ['']
        claims.append(dict(id=cid,text=title+f'. Exact changes and commentary are in {identifier} of chapter 6.',kind='source_fact',confidence='high',evidence=[dict(type='test' if h['path'].startswith('unit_tests') else 'source',path=h['path'],start_line=h['new'],end_line=new_end,symbol=title)]))
        coverage.append(dict(id=identifier,claim=cid,path=h['path'],old_start=h['old'],old_end=old_end,new_start=h['new'],new_end=new_end,additions=adds,deletions=dels))
    content += ['',*details,'## Hunk checkpoint','',
                'Explain H10 without using the word “flag” ambiguously. Then trace H25 for both a successful forced-outline INSERT and a probe that reports false. Finally, walk H30 from the first tuple through cursor termination and explain the lifetime of each temporary value.']
    write('chapters/06-annotated-diff.md','\n'.join(content)+'\n')
    dump('evidence/hunk-coverage.json',coverage)
    assert sum(x['additions'] for x in coverage)==306
    assert sum(x['deletions'] for x in coverage)==23
    manifest=json.loads((ROOT/'analysis-manifest.json').read_text())
    manifest['claims']=claims
    manifest['unknowns']=[c['id'] for c in claims if c['kind']=='unknown']
    runtime=json.loads((ROOT/'evidence/regression.json').read_text())
    manifest['runtime_checks']=[dict(id='R-001',question='Does the recorded regression binary pass the selected ownership test in a fresh private SA database?',command=['python3','scripts/run-regression.py'],exit_code=runtime['records'][-1]['exit_code'],result_artifact='evidence/regression.json',cleanup=runtime['cleanup'])]
    manifest['source']['base_revision']=BASE
    manifest['source']['evidence_policy']='Pinned Git source only; six changed files verified equal to HEAD; unrelated dirty/submodule/untracked state excluded. Pre-existing runtime binary separately hashed.'
    manifest['supplemental_sources']=[
        dict(path='/home/vimkim/gh/cubrid-oos-context/OOS-CONTEXT.md',role='normative specification; loaded earlier in this conversation and reconciled with pinned source'),
        dict(path='/home/vimkim/gh/cubrid-manual/en/sql/partition.rst',revision='3b6ae97bfbdc664b010ffa933ded5a05b291ae03',start_line=1,end_line=120,role='partition terminology and range syntax'),
        dict(path='/home/vimkim/gh/my-cubrid-docs/cbrd-27089/CBRD-27089-oos-chain-owner-b871ea3_codex.md',role='earlier report; historical results, not newly executed'),
        dict(path='/home/vimkim/gh/my-cubrid-jira/issues/CBRD-27089-partition-oos-owner_b871ea3_codex.md',role='local issue intent and historical reproduction')]
    dump('analysis-manifest.json',manifest)
    snapshots={}
    sourcemap=['# 10. Source map and evidence ledger','',
               'Claims below connect the narrative and diagrams to exact source intervals. All unmarked source intervals refer to the pinned head. History claims explicitly identify the base. Source facts describe code; inferences explain consequences; runtime observations apply to the recorded binary/input; unknowns name missing evidence.','',
               f'Head: `{HEAD}`. Base: `{BASE}`. Full SHA links remain usable after the PR changes. The captured source intervals are also in `evidence/source-excerpts.json` for offline inspection.','',
               '## Supplemental reading','',
               '- OOS normative context: `/home/vimkim/gh/cubrid-oos-context/OOS-CONTEXT.md`, last-updated label 2026-08-28. Its target policy differs from the pinned layout code; see chapter 2.',
               '- [CUBRID manual, partitioning](https://github.com/CUBRID/cubrid-manual/blob/3b6ae97bfbdc664b010ffa933ded5a05b291ae03/en/sql/partition.rst#L1-L120): local checkout at `3b6ae97bfbdc664b010ffa933ded5a05b291ae03`, lines 1–120; used for SQL concepts, not proof of OOS implementation.',
               '- [Earlier PR report](https://github.com/vimkim/my-cubrid-docs/blob/main/cbrd-27089/CBRD-27089-oos-chain-owner-b871ea3_codex.md): historical broader tests and issue narrative; no new CI or backup claim.',
               '- Local issue draft: `/home/vimkim/gh/my-cubrid-jira/issues/CBRD-27089-partition-oos-owner_b871ea3_codex.md`; intent and prior results.','',
               '## Claims','']
    for c in claims:
        sourcemap += [f'<a id="{c["id"]}"></a>',f'### {c["id"]} · {c["kind"]}','',c['text'],'']
        for e in c['evidence']:
            if e['type']=='runtime':
                sourcemap += ['Runtime check R-001: `evidence/regression.json`.','']
                continue
            rev=e.get('revision',HEAD)
            sourcemap += [f'- {source_link(e["path"],e["start_line"],e["end_line"],rev)} — `{e.get("symbol","")}`'+(' **BASE history**' if rev==BASE else '')]
            key=f'{rev}:{e["path"]}:{e["start_line"]}-{e["end_line"]}'
            lines=git('show',f'{rev}:{e["path"]}').splitlines()
            assert 0<e['start_line']<=e['end_line']<=len(lines),key
            snapshots[key]='\n'.join(f'{n}: {lines[n-1]}' for n in range(e['start_line'],e['end_line']+1))
        if c.get('rationale'): sourcemap += ['', 'Rationale: '+c['rationale']]
        if c.get('resolution'): sourcemap += ['', 'Resolve by: '+c['resolution']]
        sourcemap += ['']
    write('chapters/10-source-map.md','\n'.join(sourcemap))
    dump('evidence/source-excerpts.json',snapshots)
    return manifest

def render_markdown(text, chapter_id):
    body=markdown.markdown(text,extensions=['tables','fenced_code','toc','sane_lists'],extension_configs={'toc':{'permalink':False}})
    # Prefix generated heading ids; explicit hunk/claim anchors remain globally stable.
    body=re.sub(r'(<h[1-6] id=")([^"]+)',lambda m:m[1]+chapter_id+'-'+m[2],body)
    def embed(match):
        alt,src=match.groups()
        asset=(ROOT/'chapters'/src).resolve()
        if asset.parent != ROOT/'assets' or asset.suffix!='.svg':
            raise RuntimeError(f'Unexpected diagram path {src}')
        raw=asset.read_text()
        # SVG ids must be unique when all five diagrams share the same HTML page.
        prefix=asset.stem+'-'
        raw=re.sub(r'id="([^"]+)"',lambda m:'id="'+prefix+m[1]+'"',raw)
        raw=re.sub(r'url\(#([^)]+)\)',lambda m:'url(#'+prefix+m[1]+')',raw)
        raw=re.sub(r'aria-labelledby="([^"]+)"',lambda m:'aria-labelledby="'+' '.join(prefix+i for i in m[1].split())+'"',raw)
        return f'<figure>{raw}<figcaption>{alt}</figcaption></figure>'
    body=re.sub(r'<img alt="([^"]*)" src="([^"]+\.svg)"\s*/?>',embed,body)
    body=re.sub(r'\[(C-\d{3})\]',r'<a class="claim-ref" href="#\1">[\1]</a>',body)
    body=body.replace('<table>','<div class="table-scroll"><table>').replace('</table>','</table></div>')
    return body

def document(body, toc, title='Where the row goes, the OOS value follows'):
    css=(ROOT/'assets/report.css').read_text()+'\n'+(ROOT/'assets/book.css').read_text()
    return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{html.escape(title)} · PR 7600</title><style>{css}</style></head>
<body><header id="top"><div class="eyebrow">CUBRID · source reading course · PR 7600</div><h1>{html.escape(title)}</h1><p class="subtitle">From heap pages and partition classes to every changed line of the two-pass OOS write path.</p><span class="badge">30 annotated hunks</span><span class="badge">6 changed files</span><span class="badge">Head b871ea386</span><span class="badge">Offline · Markdown + SVG</span><p class="provenance">Base 2940b1cfb · pinned on 2026-09-08 · English · basic C/C++ and SQL prerequisites</p></header>
<nav class="toc" aria-label="Reading order">{toc}</nav><main>{body}</main><footer>Built from editable Markdown and SVG. Source claims use the pinned revision; the fresh runtime observation uses the separately hashed pre-existing binary. Study questions are answered separately in chapter 9. <a href="#top">Back to top</a></footer></body></html>'''

def main():
    manifest=make_evidence()
    chapters=sorted((ROOT/'chapters').glob('*.md'))
    rendered=[]
    toc=[]
    combined=['# PR 7600 teaching book','',f'Head `{HEAD}`; base `{BASE}`.','',
              'Read the numbered chapters in order. See README.md for build and verification instructions.','']
    for path in chapters:
        text=path.read_text()
        title=text.splitlines()[0].removeprefix('# ')
        cid='chapter-'+path.stem[:2]
        toc_title=re.sub(r'^\d+\.\s*','',title)
        toc.append(f'<li><a href="#{cid}">{html.escape(toc_title)}</a></li>')
        body=render_markdown(text,cid)
        rendered.append((cid,title,body,path.stem))
        combined += [text.replace('../assets/','assets/'),'']
    write('report.md','\n'.join(combined))
    articles=[]
    for i,(cid,title,body,stem) in enumerate(rendered):
        previous=f'<a href="#{rendered[i-1][0]}">← Previous chapter</a>' if i else '<a href="#top">Reading map</a>'
        following=f'<a href="#{rendered[i+1][0]}">Next chapter →</a>' if i+1<len(rendered) else '<a href="#top">Reading map</a>'
        articles.append(f'<article id="{cid}">{body}<div class="chapter-nav">{previous}{following}</div></article>')
        # Standalone chapter pages retain local navigation to the combined book for claims/hunks.
        pagebody=re.sub(r'href="#(C-\d+|h\d+)"',r'href="../index.html#\1"',body)
        write('chapters/'+stem+'.html',document(f'<article>{pagebody}</article>',f'<a href="../index.html#{cid}">Full book and reading map</a>',title))
    write('index.html',document(''.join(articles),'<ol>'+''.join(toc)+'</ol>'))
    inventory={}
    for path in sorted((ROOT/'chapters').glob('*.md'))+sorted((ROOT/'assets').glob('*.svg')):
        inventory[str(path.relative_to(ROOT))]=hashlib.sha256(path.read_bytes()).hexdigest()
    dump('evidence/build-inputs.json',dict(source_head=HEAD,source_base=BASE,python_markdown_version=markdown.__version__,inputs=inventory))
    print(json.dumps(dict(status='built',chapters=len(chapters),hunks=len(NOTES),claims=len(manifest['claims']),entry=str(ROOT/'index.html'))))

if __name__=='__main__':
    main()
