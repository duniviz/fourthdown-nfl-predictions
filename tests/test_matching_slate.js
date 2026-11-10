const {chromium}=require('playwright');
const assert=require('node:assert/strict');
(async()=>{
 const browser=await chromium.launch({headless:true,executablePath:'/usr/bin/google-chrome',args:['--no-sandbox']});
 for(const [width,height] of [[390,844],[1440,900]]){
  const page=await browser.newPage({viewport:{width,height}});const errors=[];page.on('pageerror',e=>errors.push(e.message));
  await page.clock.install({time:new Date('2026-11-10T01:00:00Z')});
  const oldGame={id:'old',date:'2026-11-10T01:15:00Z',competitions:[{competitors:[{homeAway:'home',team:{abbreviation:'MIN'},score:'0'},{homeAway:'away',team:{abbreviation:'BUF'},score:'0'}],status:{type:{state:'pre'}}}]};
  const newGame={id:'next',date:'2026-11-13T01:15:00Z',competitions:[{competitors:[{homeAway:'home',team:{abbreviation:'NYG'},score:'0'},{homeAway:'away',team:{abbreviation:'WAS'},score:'0'}],status:{type:{state:'pre'}}}]};
  await page.route('https://site.api.espn.com/**',r=>r.fulfill({json:{events:[oldGame,newGame]}}));
  await page.route('**/data/**',r=>{
    const path=r.request().url();let data={};
    if(path.includes('live-v2.json'))data={season:2026,week:10,generated_at_utc:'2026-11-10T00:50:00Z',games:[{game_id:'2026_10_WAS_NYG',home:'NYG',away:'WAS',kickoff_utc:newGame.date,projected_home_score:22,projected_away_score:20,projected_total:42,predicted_winner:'NYG'}]};
    if(path.includes('player-research.json'))data={players:[{player:'Upcoming Player',player_id:'p1',team:'WAS',game_id:'2026_10_WAS_NYG',market:'Passing yards',stat_key:'passing_yards',projection:200}]};
    if(path.includes('player-history.json'))data={players:[{player:'Prior Player',player_id:'p2',team:'BUF',game_id:'2026_09_BUF_MIN',kickoff_utc:oldGame.date,forecast_captured_at_utc:'2026-11-09T23:00:00Z',market:'Passing yards',stat_key:'passing_yards',projection:200}]};
    if(path.includes('dk-game-odds.json'))data={snapshot_date_utc:'2026-11-10T00:50:00Z',games:[{home:'NYG',away:'WAS',bookmaker:'draftkings',commence_time:newGame.date,total:44,home_spread:-3}]};
    if(path.includes('simulations.json'))data={games:[{game_id:'2026_10_WAS_NYG',home_win_pct:60,away_win_pct:39,tie_pct:1,simulations:10000}],players:[]};
    return r.fulfill({json:data});
  });
  await page.goto('http://127.0.0.1:8123/index.html',{waitUntil:'domcontentloaded'});
  await page.waitForFunction(()=>document.querySelector('#scoreboard-cards')?.innerText.includes('BUF'));
  await page.waitForFunction(()=>document.querySelector('#fd-watch-grid')?.innerText.includes('current scoreboard slate'));
  assert.doesNotMatch(await page.locator('#fd-watch-grid').innerText(),/WAS @ NYG/);
  assert.doesNotMatch(await page.locator('#fd-confidence-list').innerText(),/WAS @ NYG/);
  assert.doesNotMatch(await page.locator('#scoreboard-cards').innerText(),/WAS vs NYG/);
  await page.goto('http://127.0.0.1:8123/bets.html',{waitUntil:'domcontentloaded'});
  await page.waitForFunction(()=>document.querySelector('#bet-cards')?.innerText.includes('Prior Player'));
  assert.doesNotMatch(await page.locator('#bet-cards').innerText(),/Upcoming Player/);
  await page.clock.setFixedTime(new Date('2026-11-10T06:01:00Z'));
  await page.goto('http://127.0.0.1:8123/index.html',{waitUntil:'domcontentloaded'});
  await page.waitForFunction(()=>document.querySelector('#scoreboard-cards')?.innerText.includes('WAS'));
  await page.waitForFunction(()=>document.querySelector('#fd-watch-grid')?.innerText.includes('WAS @ NYG'));
  await page.waitForFunction(()=>document.querySelector('#fd-confidence-list')?.innerText.includes('WAS @ NYG'));
  assert.doesNotMatch(await page.locator('#scoreboard-cards').innerText(),/BUF vs MIN/);
  await page.goto('http://127.0.0.1:8123/bets.html',{waitUntil:'domcontentloaded'});
  await page.waitForFunction(()=>document.querySelector('#bet-cards')?.innerText.includes('Upcoming Player'));
  assert.doesNotMatch(await page.locator('#bet-cards').innerText(),/Prior Player/);
  assert.deepEqual(errors,[]);await page.close();console.log(`Slate alignment ${width}px passed`);
 }
 await browser.close();
})().catch(e=>{console.error(e);process.exit(1)});
