const {chromium}=require('playwright');
const assert=require('node:assert/strict');
(async()=>{
 const browser=await chromium.launch({headless:true,executablePath:'/usr/bin/google-chrome',args:['--no-sandbox']});
 for(const width of [390,1440]){
  const page=await browser.newPage({viewport:{width,height:900}}),errors=[];page.on('pageerror',e=>errors.push(e.message));
  await page.clock.install({time:new Date('2026-11-10T18:00:00Z')});
  const id='2026_10_WAS_NYG', kickoff='2026-11-13T01:15:00Z';
  await page.route('https://site.api.espn.com/**',r=>r.fulfill({json:{events:[{id:'g',date:kickoff,competitions:[{competitors:[{homeAway:'home',team:{abbreviation:'NYG'}},{homeAway:'away',team:{abbreviation:'WAS'}}],status:{type:{state:'pre'}}}]}]}}));
  await page.route('**/data/**',r=>{let d={},u=r.request().url();
   if(u.includes('live-v2.json'))d={games:[{game_id:id,home:'NYG',away:'WAS',kickoff_utc:kickoff,projected_home_score:22,projected_away_score:20,analysis:{matchup_metrics:[{label:'EPA / pass',away_offense:{rank:10},home_defense:{rank:20},home_offense:{rank:15},away_defense:{rank:25}}]}}]};
   if(u.includes('projection-changes.json'))d={schema_version:1,games:{[id]:[{at:'2026-11-09T12:00:00Z',home:21,away:20},{at:'2026-11-10T12:00:00Z',home:22,away:20}]},players:{}};
   if(u.includes('player-research.json'))d={players:[{game_id:id,player_id:'p1',player:'Example Player',team:'WAS',market:'Passing yards',stat_key:'passing_yards',projection:100}]};
   if(u.includes('simulations.json'))d={games:[{game_id:id,home_win_pct:60,away_win_pct:39,simulations:10000}],players:[{game_id:id,player_id:'p1',stat_key:'passing_yards',mean_projection:100,sorted_draws:Array.from({length:100},(_,i)=>i*2)}]};
   if(u.includes('weekly-model-performance.json'))d={generated_at_utc:'2026-11-10T12:00:00Z',weekly_reports:[{season:2026,week:9,status:'graded_observed_only',completed_games:2,game_metrics:{home_margin:{mae:10,samples:2}},player_metrics:{passing_yards:{mae:20,samples:4}}}]};
   return r.fulfill({json:d});});
  await page.goto('http://127.0.0.1:8123/index.html');
  await page.waitForFunction(()=>document.querySelector('#fd-whats-changed')?.innerText.includes('21.0 → 22.0'));
  await page.waitForSelector('#scoreboard-cards .fd-scorecard-matchup');
  assert.match(await page.locator('#scoreboard-cards .fd-scorecard-matchup').first().textContent(),/Passing/);
  await page.goto('http://127.0.0.1:8123/bets.html');
  await page.waitForSelector('#bet-cards .fd-range');
  assert.match(await page.locator('#bet-cards .fd-range').first().innerText(),/Middle 80%/);
  await page.goto('http://127.0.0.1:8123/model-lab.html');
  await page.waitForFunction(()=>document.querySelector('#fd-weekly-report-card')?.innerText.includes('10.0 points'));
  assert.match(await page.locator('#fd-weekly-report-card').innerText(),/4 graded forecasts/);
  assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);
  assert.deepEqual(errors,[]);await page.close();console.log('Visual insights '+width+'px passed');
 }
 await browser.close();
})().catch(e=>{console.error(e);process.exit(1)});
