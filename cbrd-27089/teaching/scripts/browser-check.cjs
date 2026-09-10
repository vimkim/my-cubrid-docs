#!/usr/bin/env node
// Browser-only validation; the book itself has no JavaScript dependency.
const fs=require('node:fs');
const path=require('node:path');
const {pathToFileURL}=require('node:url');
const root=path.resolve(__dirname,'..');
const modulePath=process.env.PLAYWRIGHT_MODULE || '/home/vimkim/.npm/_npx/9833c18b2d85bc59/node_modules/playwright';
const executablePath=process.env.CHROMIUM_PATH || '/home/vimkim/.cache/ms-playwright/chromium-1234/chrome-linux64/chrome';
const {chromium}=require(modulePath);

(async()=>{
 const browser=await chromium.launch({executablePath,headless:true,args:['--no-sandbox']});
 const results=[]; const failures=[];
 for(const width of [1280,390]){
  const context=await browser.newContext({viewport:{width,height:900},offline:true});
  const page=await context.newPage();
  const errors=[]; page.on('pageerror',e=>errors.push(String(e)));
  await page.goto(pathToFileURL(path.join(root,'index.html')).href);
  const metrics=await page.evaluate(()=>{
   const bad=[];
   for(const svg of document.querySelectorAll('svg')){
    const v=svg.viewBox.baseVal;
    for(const text of svg.querySelectorAll('text')){
     const b=text.getBBox();
     if(b.x<0||b.y<0||b.x+b.width>v.width+1||b.y+b.height>v.height+1)bad.push(text.textContent);
    }
   }
   return {title:document.title,chapters:document.querySelectorAll('main>article').length,svg:document.querySelectorAll('figure svg').length,
           horizontalPageOverflow:document.documentElement.scrollWidth>innerWidth+1,svgTextOutsideViewBox:bad,
           brokenImages:Array.from(document.images).filter(i=>!i.complete||i.naturalWidth===0).length,
           resources:performance.getEntriesByType('resource').map(e=>e.name)};
  });
  if(metrics.horizontalPageOverflow||metrics.svgTextOutsideViewBox.length||metrics.brokenImages||errors.length)failures.push({width,metrics,errors});
  await page.screenshot({path:path.join(root,`evidence/book-${width}.png`)});
  await page.locator('#chapter-02').scrollIntoViewIfNeeded();
  await page.locator('#chapter-02 figure').last().screenshot({path:path.join(root,`evidence/flow-${width}.png`)});
  await page.locator('#h25').scrollIntoViewIfNeeded();
  await page.screenshot({path:path.join(root,`evidence/diff-${width}.png`)});
  // Check actual in-document navigation, including a claim and an answer chapter.
  await page.locator('nav.toc a[href="#chapter-09"]').click();
  if(!page.url().endsWith('#chapter-09'))failures.push({width,navigation:'answers'});
  await page.locator('#chapter-09 .claim-ref').first().click();
  if(!page.url().match(/#C-\d+$/))failures.push({width,navigation:'claim'});
  results.push({width,...metrics,errors});
  await context.close();
 }
 const context=await browser.newContext({offline:true});
 const page=await context.newPage();
 for(const file of fs.readdirSync(path.join(root,'chapters')).filter(x=>x.endsWith('.html'))){
  await page.goto(pathToFileURL(path.join(root,'chapters',file)).href);
  if(await page.locator('article').count()!==1)failures.push({file,error:'missing article'});
 }
 await page.goto(pathToFileURL(path.join(root,'index.html')).href);
 await page.emulateMedia({media:'print'});
 const print=await page.evaluate(()=>({bodyBackground:getComputedStyle(document.body).backgroundColor,remoteResources:performance.getEntriesByType('resource').filter(e=>/^https?:/.test(e.name)).length}));
 await browser.close();
 const report={status:failures.length?'failed':'passed',browser:executablePath,network:'offline',results,individualChaptersOpened:10,print,failures};
 fs.writeFileSync(path.join(root,'evidence/browser-validation.json'),JSON.stringify(report,null,2)+'\n');
 console.log(JSON.stringify(report,null,2));
 process.exitCode=failures.length?1:0;
})().catch(error=>{console.error(error);process.exitCode=1;});
