const {chromium} = require('playwright');
const assert = require('node:assert/strict');
const fs = require('fs');

(async () => {
  const executablePath = ['/usr/bin/google-chrome','/usr/bin/chromium','/usr/bin/chromium-browser'].find(p=>fs.existsSync(p));
  const browser = await chromium.launch({headless:true,executablePath,args:['--no-sandbox','--disable-dev-shm-usage']});
  const page = await browser.newPage({viewport:{width:390,height:844}});
  const errors=[];
  page.on('pageerror',error=>errors.push(error.message));
  const lock={game_id:'2026_11_ARI_KC',away:'ARI',home:'KC',kickoff_utc:'2026-11-22T18:00:00Z',
    forecast_at_utc:'2026-11-22T17:28:22Z',captured_at_utc:'2026-11-22T17:30:02Z',lock_status:'official',
    projected_away_score:16,projected_home_score:28.8,
    game_ml_shadow:{markets:{game_total:{candidate:43.91},game_margin_home:{candidate:10.23}}}};
  await page.route('**/data/game-official-pregame-locks.json*',route=>route.fulfill({json:{records:[lock]}}));
  await page.route('**/data/player-history.json*',route=>route.fulfill({json:{players:[]}}));
  const loaded=page.waitForResponse(response=>response.url().includes('/data/live-v2.json?ts='),{timeout:60000});
  await page.goto('http://127.0.0.1:8123/index.html',{waitUntil:'domcontentloaded'});
  await loaded;
  await page.evaluate(()=>window.dispatchEvent(new CustomEvent('fd-open-matchup',{detail:{
    id:'fixture',state:'post',date:'2026-11-22T18:00:00Z',away:{abbr:'ARI',score:7},home:{abbr:'KC',score:34}
  }})));
  await page.waitForSelector('#fd-modal.open .fd-final-result',{timeout:30000});
  const text=await page.locator('#fd-modal .fd-final-result').innerText();
  assert.match(text,/ARI 16\.0 · KC 28\.8/);
  assert.match(text,/ARI 16\.8 · KC 27\.1/);
  assert.match(text,/Final score/i);
  assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth+1),true);
  assert.deepEqual(errors,[]);
  await browser.close();
  console.log('Finished game comparison browser check passed');
})().catch(error=>{console.error(error);process.exit(1)});
