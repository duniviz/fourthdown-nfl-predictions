'use strict';
const {chromium}=require('playwright');
const assert=require('node:assert/strict');
(async()=>{
 const fs=require('fs');const executablePath=['/usr/bin/google-chrome','/usr/bin/chromium','/usr/bin/chromium-browser'].find(p=>fs.existsSync(p));
 const browser=await chromium.launch({headless:true,executablePath,args:['--no-sandbox']});
 const page=await browser.newPage({viewport:{width:390,height:844}});const errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.route('**/data/*.json*',route=>{const name=route.request().url();let body={};if(name.includes('live-v2'))body={generated_at_utc:'2099-01-01T00:00:00Z',games:[{game_id:'example',kickoff_utc:'2099-01-02T00:00:00Z',away:'MIN',home:'SF',projected_away_score:18,projected_home_score:24,projected_margin_home:6,projected_total:42,analysis:{home:{},away:{}}}]};return route.fulfill({json:body})});
 await page.goto('http://127.0.0.1:8123/game-preview.html?game=example');
 await page.waitForSelector('h1');assert.match(await page.locator('h1').innerText(),/MIN.*at.*SF/);assert.match(await page.locator('body').innerText(),/Model projection/);assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);assert.deepEqual(errors,[]);
 await browser.close();console.log('Mobile preview check passed');
})().catch(e=>{console.error(e);process.exit(1)});
