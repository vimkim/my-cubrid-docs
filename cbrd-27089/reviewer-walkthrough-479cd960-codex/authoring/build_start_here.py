from pathlib import Path
import markdown, shutil
out=Path(__file__).resolve().parents[1]
# One reading column; paper/ink with the established green accent. No graph controls.
css='''
:root{--bg:#f1f5f4;--surface:#fff;--text:#192f2b;--text-dim:#526b63;--border:#c5d4cf;--accent:#006c59}
@media(prefers-color-scheme:dark){:root{--bg:#101e1b;--surface:#182b26;--text:#e6f0ec;--text-dim:#aec6bc;--border:#365148;--accent:#79d7b7}}
*{box-sizing:border-box}html{font-size:18px}body{margin:0;background:var(--bg);color:var(--text);font-family:'IBM Plex Sans','Noto Sans CJK KR','Noto Sans KR',sans-serif;line-height:1.9}main{max-width:760px;margin:auto;padding:2rem 1.25rem 5rem}h1{font-size:1.85rem;line-height:1.45;letter-spacing:-.025em;text-wrap:balance}h2{font-size:1.3rem;margin:3.2rem 0 1rem;padding-top:1.2rem;border-top:1px solid var(--border);line-height:1.5}p,li,h1,h2,a{overflow-wrap:anywhere}p{margin:1.1rem 0}li{margin:.55rem 0}a{color:var(--accent);text-underline-offset:4px}nav{font-size:.85rem;display:flex;flex-wrap:wrap;gap:1rem}code{font-family:'IBM Plex Mono','DejaVu Sans Mono',monospace;font-size:.82rem}pre{overflow:auto;padding:1rem;line-height:1.8;background:var(--surface);border:1px solid var(--border)}details{margin:1.5rem 0;background:var(--surface);padding:.7rem 1rem;border:1px solid var(--border)}summary{cursor:pointer;color:var(--accent)}details p:last-child{margin-bottom:.4rem}a:focus-visible,summary:focus-visible{outline:3px solid var(--accent);outline-offset:4px}.meta{font-size:.8rem;color:var(--text-dim)}@media(max-width:500px){main{padding:1.2rem 1rem 3rem}h1{font-size:1.55rem}}
'''
for lang in ['en','ko']:
 source=(out/f'authoring/start-here.{lang}.md').read_text()
 (out/f'start-here.{lang}.md').write_text(source)
 if lang=='ko':
  body=markdown.markdown(source.replace('<details>','<details markdown="1">'),extensions=['fenced_code','md_in_html'])
  page='''<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>PR7600 · 행 하나로 이해하기</title><link rel="icon" href="data:image/svg+xml,%3Csvg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 64 64%22%3E%3Ctext y=%2250%22 font-size=%2250%22%3EP%3C/text%3E%3C/svg%3E"><style>'''+css+'''</style></head><body><main><nav aria-label="다른 읽기 형식"><a href="start-here.en.md">English</a><a href="start-here.ko.md">한국어 Markdown</a></nav><p class="meta">먼저 읽는 안내 · PR #7600</p>'''+body+'''</main></body></html>'''
  (out/'start-here.ko.html').write_text(page)
# Make the short guide discoverable from the existing bundle landing pages.
for name in ['review.en.md','review.ko.md','README.md']:
 p=out/name;s=p.read_text()
 if 'start-here.ko.html' not in s:s='[Start here: short English guide](start-here.en.md) · [먼저 읽기: 한국어 안내](start-here.ko.html)\n\n'+s
 p.write_text(s)
for name in ['review.ko.html','index.html']:
 p=out/name;s=p.read_text()
 if 'start-here.ko.html' not in s:s=s.replace('<body>','<body><p style="padding:1rem;margin:0;font-size:1rem"><a href="start-here.ko.html">처음 읽는다면: 행 하나로 이해하는 짧은 안내 →</a></p>',1)
 p.write_text(s)
print('Built English/Korean short guides and linked them from the existing reports.')
