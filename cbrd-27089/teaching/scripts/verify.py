#!/usr/bin/env python3
"""Check book links, SVGs, hunk arithmetic, claim references and offline assets."""
from collections import Counter
from html.parser import HTMLParser
import json
from pathlib import Path
import re
from urllib.parse import urlsplit, unquote
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[1]

class Page(HTMLParser):
    def __init__(self,text):
        super().__init__()
        self.ids=[]; self.links=[]; self.remote=[]; self.svg=0
        self.feed(text)
    def handle_starttag(self,tag,attrs):
        attr=dict(attrs)
        if 'id' in attr: self.ids.append(attr['id'])
        if tag=='a' and 'href' in attr: self.links.append(attr['href'])
        if tag=='svg': self.svg+=1
        for key in ('src','srcset'):
            if key in attr and (attr[key].startswith(('http:','https:','//'))): self.remote.append(attr[key])

def main():
    problems=[]
    pages={p:Page(p.read_text()) for p in ROOT.rglob('*.html')}
    for path,page in pages.items():
        duplicate=[x for x,n in Counter(page.ids).items() if n>1]
        if duplicate: problems.append(f'Duplicate ids {path}: {duplicate}')
        if page.remote: problems.append(f'Remote resources {path}: {page.remote}')
        for link in page.links:
            parsed=urlsplit(link)
            if parsed.scheme or parsed.netloc: continue
            target=(path.parent/unquote(parsed.path)).resolve() if parsed.path else path
            if not target.exists(): problems.append(f'Missing link {path}: {link}')
            if parsed.fragment and target.suffix=='.html':
                other=pages.get(target)
                if other and unquote(parsed.fragment) not in other.ids:
                    problems.append(f'Missing fragment {path}: {link}')
    for svg in (ROOT/'assets').glob('*.svg'):
        tree=ET.parse(svg)
        ns={'s':'http://www.w3.org/2000/svg'}
        if tree.find('s:title',ns) is None or tree.find('s:desc',ns) is None:
            problems.append(f'SVG lacks title/description: {svg}')
    manifest=json.loads((ROOT/'analysis-manifest.json').read_text())
    text=(ROOT/'index.html').read_text()
    known={c['id'] for c in manifest['claims']}
    found=set(re.findall(r'C-\d{3}',text))
    if found!=known: problems.append(f'Claim mismatch: {found^known}')
    coverage=json.loads((ROOT/'evidence/hunk-coverage.json').read_text())
    counts={'hunks':len(coverage),'additions':sum(x['additions'] for x in coverage),'deletions':sum(x['deletions'] for x in coverage)}
    if counts != {'hunks':30,'additions':306,'deletions':23}: problems.append(f'Coverage counts: {counts}')
    for h in coverage:
        if h['id'].lower() not in pages[ROOT/'index.html'].ids: problems.append(f'Missing hunk {h["id"]}')
    if pages[ROOT/'index.html'].svg!=5: problems.append('Combined book must embed five SVGs')
    if re.search(r'@import|url\(["\x27]?https?://',text): problems.append('Remote CSS dependency')
    result={'status':'failed' if problems else 'passed','html_pages':len(pages),'svg_assets':5,'claims':len(known),**counts,'problems':problems}
    (ROOT/'evidence/validation.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))
    raise SystemExit(bool(problems))

if __name__=='__main__': main()
