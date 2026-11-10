const {chromium}=require('playwright');
const assert=require('node:assert/strict');
(async()=>{
 const browser=await chromium.launch({headless:true,executablePath:process.env.CHROME_PATH||'/usr/bin/google-chrome',args:['--no-sandbox']});
 for(const width of [390,1440]){
  const page=await browser.newPage({viewport:{width,height:900}});const errors=[];
  page.on('pageerror',e=>errors.push(e.message));
  await page.route('**/data/player-ml-runtime.json*',r=>r.fulfill({json:{generated_at_utc:'2026-11-10T03:00:00Z',decisions:{passing_yards:{active:true,paired:110,weeks:5,baseline_mae:60,candidate_mae:55},rushing_yards:{active:false,paired:0,weeks:0}}}}));
  await page.route('**/data/game-ml-runtime.json*',r=>r.fulfill({json:{decisions:{game_total:{active:false,paired:100,weeks:6,baseline_mae:12,candidate_mae:14}}}}));
  await page.goto('http://127.0.0.1:8123/model-lab.html',{waitUntil:'networkidle'});
  assert.equal(await page.locator('#player-ml-live-status').isVisible(),true);
  assert.match(await page.locator('#player-ml-live-status').innerText(),/ML active/);
  assert.match(await page.locator('#player-ml-live-status').innerText(),/Not enough matched results/);
  assert.match(await page.locator('#game-ml-live-status').innerText(),/12.00 \/ ML 14.00/);
  assert.equal(await page.locator('.clear-advanced').evaluate(e=>e.open),false);
  assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth),true,`overflow at ${width}`);
  assert.deepEqual(errors,[]);await page.close();console.log(`Labs ${width}px passed`);
 }
 await browser.close();
})().catch(e=>{console.error(e);process.exit(1)});
