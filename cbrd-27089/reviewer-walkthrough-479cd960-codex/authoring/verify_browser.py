from pathlib import Path
import json, datetime
from playwright.sync_api import sync_playwright
out=Path(__file__).resolve().parents[1]
results={'checked_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'upstream_validator':'PASS: static and Chromium, four graphs, 26 nodes, 19 directed edges and tours','engine_tests_run':False,'browser':[]}
with sync_playwright() as p:
 browser=p.chromium.launch()
 for filename in ['index.html','review.ko.html']:
  for width,scheme in [(1440,'light'),(390,'dark')]:
   context=browser.new_context(viewport={'width':width,'height':1000},offline=True,color_scheme=scheme)
   page=context.new_page();errors=[];network=[]
   page.on('pageerror',lambda e:errors.append(str(e)))
   page.on('request',lambda r:network.append(r.url) if r.url.startswith('http') else None)
   page.goto((out/filename).as_uri());page.wait_for_timeout(500)
   overflow=page.evaluate('document.documentElement.scrollWidth > innerWidth')
   assert not overflow, (filename,width,"document overflow")
   assert not errors, errors
   assert not network,network
   if filename=='index.html':
    assert page.locator('.d3-node').count()==5
    page.locator('[data-graph-id="data-flow"]').click()
    assert page.locator('.d3-node').count()==8
    before=page.locator('#pr-walkthrough-details').inner_text()
    page.locator('[data-d3-action="tour-next"]').click()
    after=page.locator('#pr-walkthrough-details').inner_text()
    assert before!=after
   else:
    assert page.locator('article.hunk').count()==63
    page.locator('#search').fill('heap_file.c')
    page.wait_for_timeout(100)
    assert '63 / 63' not in page.locator('#count').inner_text()
    page.locator('#search').fill('')
   page.evaluate('window.scrollTo({top:0,behavior:"instant"})')
   page.screenshot(path=str(out/'evidence'/f'{filename}-{width}.png'),full_page=False)
   results['browser'].append(dict(page=filename,width=width,color_scheme=scheme,offline=True,external_requests=network,errors=errors,document_overflow=overflow))
   context.close()
 browser.close()
(out/'evidence/validation.json').write_text(json.dumps(results,indent=2))
print(json.dumps(results,indent=2))
