const {chromium}=require('playwright');
const assert=require('node:assert/strict');
(async()=>{
 const browser=await chromium.launch({headless:true,executablePath:'/usr/bin/google-chrome',args:['--no-sandbox']});
 for(const width of [390,1440]){
  const page=await browser.newPage({viewport:{width,height:900}}),errors=[];page.on('pageerror',e=>errors.push(e.message));
  await page.clock.install({time:new Date('2026-11-10T18:00:00Z')});
  const id='2026_10_WAS_NYG', id2='2026_10_PHI_DAL', kickoff='2026-11-13T01:15:00Z';
  await page.route('https://site.api.espn.com/**',r=>r.fulfill({json:{events:[{id:'g',date:kickoff,competitions:[{competitors:[{homeAway:'home',team:{abbreviation:'NYG'}},{homeAway:'away',team:{abbreviation:'WAS'}}],status:{type:{state:'pre'}}}]}]}}));
  await page.route('**/data/**',r=>{let d={},u=r.request().url();
   if(u.includes('live-v2.json'))d={season:2026,week:10,generated_at_utc:'2026-11-10T12:00:00Z',games:[{game_id:id,home:'NYG',away:'WAS',kickoff_utc:kickoff,projected_home_score:22,projected_away_score:20,analysis:{matchup_metrics:[{label:'EPA / pass',away_offense:{rank:10},home_defense:{rank:20},home_offense:{rank:15},away_defense:{rank:25}}]}},{game_id:id2,home:'DAL',away:'PHI',kickoff_utc:kickoff,projected_home_score:20.5,projected_away_score:17.5}]};
   if(u.includes('projection-changes.json'))d={schema_version:1,games:{[id]:[{at:'2026-11-09T12:00:00Z',home:21,away:20},{at:'2026-11-10T12:00:00Z',home:22,away:20}],[id2]:[{at:'2026-11-09T12:00:00Z',home:20,away:17},{at:'2026-11-10T12:00:00Z',home:20.5,away:17.5}]},players:{[id+'|p1|passing_yards']:[{at:'2026-11-09T12:00:00Z',value:100},{at:'2026-11-10T12:00:00Z',value:100.1}],[id+'|p2|rushing_yards']:[{at:'2026-11-09T12:00:00Z',value:3},{at:'2026-11-10T12:00:00Z',value:5}],[id+'|p3|carries']:[{at:'2026-11-09T12:00:00Z',value:2.2},{at:'2026-11-10T12:00:00Z',value:3}],[id+'|p4|carries']:[{at:'2026-11-09T12:00:00Z',value:2},{at:'2026-11-10T12:00:00Z',value:3}]}};
   if(u.includes('dk-game-line-history.json'))d={games:{['NYG|WAS|'+kickoff]:[{captured_at_utc:'2026-11-09T12:00:00Z',total:42},{captured_at_utc:'2026-11-10T12:00:00Z',total:43}]}};
   if(u.includes('player-research.json'))d={players:[{game_id:id,player_id:'p1',player:'Tiny Yards',team:'WAS',market:'Passing yards',stat_key:'passing_yards',projection:100.1},{game_id:id,player_id:'p2',player:'Meaningful Yards',team:'WAS',market:'Rushing yards',stat_key:'rushing_yards',projection:5},{game_id:id,player_id:'p3',player:'Small Count',team:'WAS',market:'Carries',stat_key:'carries',projection:3},{game_id:id,player_id:'p4',player:'Meaningful Count',team:'WAS',market:'Carries',stat_key:'carries',projection:3}]};
   if(u.includes('simulations.json'))d={games:[{game_id:id,home_win_pct:60,away_win_pct:39,simulations:10000}],players:[{game_id:id,player_id:'p1',stat_key:'passing_yards',mean_projection:100,sorted_draws:Array.from({length:100},(_,i)=>i*2)}]};
   if(u.includes('weekly-model-performance.json'))d={generated_at_utc:'2026-11-10T12:00:00Z',weekly_reports:[{season:2026,week:9,status:'graded_observed_only',completed_games:2,game_metrics:{home_margin:{mae:10,samples:2}},player_metrics:{passing_yards:{mae:20,samples:4}}}]};
   return r.fulfill({json:d});});
  await page.goto('http://127.0.0.1:8123/index.html');
  await page.waitForFunction(()=>document.querySelector('#fd-whats-changed')?.innerText.includes('21.0 → 22.0'));
  const changed=await page.locator('#fd-whats-changed').innerText();
  assert.match(changed,/Total 42.0 → 43.0/);
  assert.match(changed,/Meaningful Yards/);
  assert.match(changed,/Meaningful Count/);
  assert.doesNotMatch(changed,/Tiny Yards|Small Count|PHI @ DAL/);
  await page.waitForSelector('#scoreboard-cards .fd-adv-card');
  assert.match(await page.locator('#scoreboard-cards .fd-adv-card').first().textContent(),/Passing/);
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
