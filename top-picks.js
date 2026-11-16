/* Current-slate Top 5 board. Yardage picks join the blend only with an exact-line simulation. */
function topPicksTabsCollapsed(boards){
 const sig=rows=>(rows||[]).map(row=>[row.kind,row.pick].join('|')).join('\n');
 const present=['players','scoring','blended'].map(key=>sig(boards&&boards[key])).filter(Boolean);
 return present.length>0&&new Set(present).size===1;
}
function topPicksHeading(count){
 const n=Number(count)||0;
 if(n>=5) return {title:'Top 5 Picks', note:''};
 if(n<=0) return {title:'Top Picks', note:''};
 const noun=n===1?'pick':'picks';
 return {title:'Top Picks', note:n+' qualifying '+noun+' this week. A pick needs a matching simulation above 50%, so fewer than five can qualify.'};
}
(function(){
 if(typeof document==='undefined') return;
 const root=document.getElementById('fd-top-picks-list'),status=document.getElementById('fd-top-picks-status');
 if(!root||!status)return;
 const tabs=[...document.querySelectorAll('[data-fd-top-picks-tab]')];
 let active='blended',boards={players:[],scoring:[],blended:[]};
 const esc=x=>String(x??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
 const norm=x=>String(x||'').toLowerCase().replace(/[^a-z0-9]/g,'');
 const canon=x=>window.fdTeams?window.fdTeams.label(x):({JAX:'JAC',LA:'LAR',WSH:'WAS'}[String(x||'').toUpperCase()]||String(x||'').toUpperCase());
 const teams={ARI:'arizona cardinals',ATL:'atlanta falcons',BAL:'baltimore ravens',BUF:'buffalo bills',CAR:'carolina panthers',CHI:'chicago bears',CIN:'cincinnati bengals',CLE:'cleveland browns',DAL:'dallas cowboys',DEN:'denver broncos',DET:'detroit lions',GB:'green bay packers',HOU:'houston texans',IND:'indianapolis colts',JAC:'jacksonville jaguars',KC:'kansas city chiefs',LV:'las vegas raiders',LAC:'los angeles chargers',LAR:'los angeles rams',MIA:'miami dolphins',MIN:'minnesota vikings',NE:'new england patriots',NO:'new orleans saints',NYG:'new york giants',NYJ:'new york jets',PHI:'philadelphia eagles',PIT:'pittsburgh steelers',SF:'san francisco 49ers',SEA:'seattle seahawks',TB:'tampa bay buccaneers',TEN:'tennessee titans',WAS:'washington commanders'};
 const marketNames={passing_yards:'Passing yards',rushing_yards:'Rushing yards',receiving_yards:'Receiving yards'};
 const quoteMarkets={passing_yards:'player_pass_yds',rushing_yards:'player_rush_yds',receiving_yards:'player_rec_yds'};
 const nameOf=x=>teams[canon(x)]||String(x||'');
 const teamMatches=(value,abbr)=>canon(value)===canon(abbr)||norm(value)===norm(nameOf(abbr))||norm(value).includes(norm(nameOf(abbr)));
 function sideRates(sim,line){
  const stored=number(sim?.dk_line),over=pct(sim?.over_pct),under=pct(sim?.under_pct);
  if(stored!==null&&Math.abs(stored-line)<.0001&&over!==null&&under!==null)return {over,under};
  const draws=Array.isArray(sim?.sorted_draws)?sim.sorted_draws.map(number).filter(x=>x!==null):[];
  if(!draws.length)return {over:null,under:null};
  return {over:100*draws.filter(x=>x>line).length/draws.length,under:100*draws.filter(x=>x<line).length/draws.length};
 }
 const number=x=>x!==null&&x!==''&&x!==undefined&&Number.isFinite(Number(x))?Number(x):null;
 const pct=x=>number(x)!==null&&Number(x)>=0&&Number(x)<=100?Number(x):null;
 function render(){
  if(topPicksTabsCollapsed(boards)&&active!=='blended') active='blended';
  const rows=boards[active]||[];
  const heading=topPicksHeading(rows.length);
  const title=document.getElementById('fd-top-picks-title');
  if(title) title.textContent=heading.title;
  root.innerHTML=rows.length?rows.map((x,i)=>'<article class="fd-top-pick"><div class="fd-top-pick-kicker">#'+(i+1)+' · '+esc(x.kind)+'</div><div class="fd-top-pick-matchup"><span>GAME</span><strong>'+esc(x.game||'Matchup unavailable')+'</strong></div><h3>'+esc(x.pick)+'</h3><details class="fd-pick-reason"><summary>Why this pick?</summary><p>'+esc(x.detail)+'</p></details>'+(Number.isFinite(x.overPct)&&Number.isFinite(x.underPct)?'<div class="fd-top-pick-prob"><div class="fd-top-pick-prob-bar"><i style="width:'+x.overPct+'%"></i><b style="width:'+x.underPct+'%"></b></div><div><span>Over '+x.overPct.toFixed(1)+'% sim</span><span>Under '+x.underPct.toFixed(1)+'% sim</span></div></div>':'')+'<div class="fd-top-pick-meta">'+(x.confidence!==null?'<strong>'+Number(x.confidence).toFixed(1)+'% simulated</strong>':'<strong>'+(x.line===null?'Projection only':'No matched simulation')+'</strong>')+'</div></article>').join(''):'<p class="fd-top-pick-empty">No current-slate yardage projections or eligible scoring picks are available yet. Yardage projections remain visible when a live DK prop line is unavailable.</p>';
  const tabsWrap=document.querySelector('.fd-top-picks-tabs');
  if(tabsWrap) tabsWrap.hidden=topPicksTabsCollapsed(boards);
  tabs.forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.fdTopPicksTab===active)));
  const base=active==='players'?'Passing, rushing, and receiving yards only. Player cards show yardage projections, DK lines, and simulated over/under rates when available.':active==='scoring'?'One leading O/U, outright-winner, and spread pick, when current DraftKings lines and matching simulations support them.':'Top five across O/U, winner, spread, and player yardage picks with an exact matching simulation above 50%.';
  status.textContent=(heading.note?heading.note+' ':'')+base;
 }
 tabs.forEach(b=>b.addEventListener('click',()=>{active=b.dataset.fdTopPicksTab;render();}));
 async function refresh(){
  try{
   const paths=['data/live-v2.json','data/dk-game-odds.json','data/simulations.json','data/dk-odds.json','data/research-prop-desk.json'];
   const rs=await Promise.all(paths.map(p=>fetch(p+'?t='+Date.now(),{cache:'no-store'})));
   if(!rs[0].ok||!rs[4].ok)throw Error('Forecast or yardage feed unavailable');
   const [forecast,market,sim,dk,desk]=await Promise.all(rs.map(r=>r.ok?r.json():Promise.resolve({})));
   const now=Date.now(),stamp=Date.parse(forecast.generated_at_utc),quoteStamp=Date.parse(market.snapshot_date_utc),simStamp=Date.parse(sim.generated_at_utc);
   if(!Number.isFinite(stamp)||stamp>now+300000||now-stamp>36*3600000)throw Error('Stale forecast feed');
   const gameOddsFresh=Number.isFinite(quoteStamp)&&quoteStamp<=now+300000&&now-quoteStamp<=36*3600000;
   const simulationFresh=Number.isFinite(simStamp)&&simStamp<=now+300000&&now-simStamp<=36*3600000;
   const slate=window.fdScheduleWindow?.get(new Date());
   if(!slate)throw Error('Schedule window unavailable');
   const upcoming=(forecast.games||[]).filter(g=>g.kickoff_utc&&Date.parse(g.kickoff_utc)>now&&window.fdScheduleWindow.contains(slate,g.kickoff_utc));
   const quotes=new Map();
   for(const q of (gameOddsFresh?market.games||[]:[])){
    if(q.bookmaker!=='draftkings'||!q.home||!q.away)continue;
    const key=canon(q.away)+'|'+canon(q.home),prior=quotes.get(key),stampQ=Date.parse(q.updated_at_utc||q.observed_at_utc||market.snapshot_date_utc);
    if(!prior||stampQ>Date.parse(prior.updated_at_utc||prior.observed_at_utc||market.snapshot_date_utc))quotes.set(key,q);
   }
   const gameSims=simulationFresh&&Array.isArray(sim.games)?sim.games:[];
   const playerSims=simulationFresh&&Array.isArray(sim.players)?sim.players:[];
   const gamePicks=[];
   for(const p of upcoming){
    const q=quotes.get(canon(p.away)+'|'+canon(p.home)),s=gameSims.find(x=>String(x.game_id)===String(p.game_id));
    if(!q||!s||Math.abs(Date.parse(q.commence_time)-Date.parse(p.kickoff_utc))>3600000)continue;
    const qtime=Date.parse(q.updated_at_utc||q.observed_at_utc||market.snapshot_date_utc),kick=Date.parse(p.kickoff_utc);
    if(!Number.isFinite(qtime)||qtime>now||now-qtime>36*3600000||qtime>=kick)continue;
    const home=number(p.projected_home_score),away=number(p.projected_away_score);
    const base={game:canon(p.away)+' @ '+canon(p.home),detail:'Projected score '+(home===null||away===null?'—':canon(p.away)+' '+away.toFixed(1)+' – '+canon(p.home)+' '+home.toFixed(1))};
    if(home!==null&&away!==null&&home!==away){
     const team=home>away?p.home:p.away,confidence=pct(team===p.home?s.home_win_pct:s.away_win_pct);
     if(confidence!==null&&confidence>50)gamePicks.push({...base,kind:'Winner',pick:canon(team)+' to win',confidence});
    }
    const total=number(q.total),projected=home!==null&&away!==null?home+away:null;
    if(total!==null&&projected!==null&&number(s.dk_total)===total&&projected!==total){
     const over=projected>total,confidence=pct(over?s.over_cover_pct:s.under_cover_pct);
     if(confidence!==null&&confidence>50)gamePicks.push({...base,kind:'O/U',pick:(over?'Over ':'Under ')+total.toFixed(1),confidence,detail:'Projected total '+projected.toFixed(1)+' · DK total '+total.toFixed(1)});
    }
    const spread=number(q.home_spread);
    if(spread!==null&&number(s.dk_home_spread)===spread&&home!==null&&away!==null){
     const edge=(home-away)+spread;
     if(edge!==0){const homePick=edge>0,confidence=pct(homePick?s.home_cover_pct:s.away_cover_pct);if(confidence!==null&&confidence>50)gamePicks.push({...base,kind:'Spread',pick:homePick?canon(p.home)+' '+(spread>0?'+':'')+spread.toFixed(1):canon(p.away)+' '+(-spread>0?'+':'')+(-spread).toFixed(1),confidence,detail:'Model spread edge '+Math.abs(edge).toFixed(1)+' pts'});}
    }
   }
   boards.scoring=['O/U','Winner','Spread'].map(kind=>gamePicks.filter(x=>x.kind===kind).sort((a,b)=>b.confidence-a.confidence)[0]).filter(Boolean).sort((a,b)=>b.confidence-a.confidence);
   const blend=[...gamePicks];
   const playerCandidates=[];
   const yardStamp=Date.parse(desk.generated_at_utc);
   if(Number.isFinite(yardStamp)&&yardStamp<=now&&now-yardStamp<=36*3600000){
    for(const x of desk.comparisons||[]){
     const key=x.market,marketKey=quoteMarkets[key],team=canon(x.team),opponent=canon(x.opponent);
     const game=upcoming.find(g=>(canon(g.away)===team&&canon(g.home)===opponent)||(canon(g.home)===team&&canon(g.away)===opponent));
     if(!marketKey||!game)continue;
     const start=Date.parse(game.kickoff_utc);
     const quote=(dk.rows||[]).filter(q=>norm(q.player)===norm(x.player_name)&&q.market_key===marketKey&&
       teamMatches(q.away_team||q.away,game.away)&&teamMatches(q.home_team||q.home,game.home)&&
       Math.abs(Date.parse(q.commence_time)-start)<3600000)
      .filter(q=>{const t=Date.parse(q.last_update||q.updated_at_utc);return Number.isFinite(t)&&t<=now&&now-t<=36*3600000&&t<start;})
      .sort((a,b)=>Date.parse(b.last_update||b.updated_at_utc)-Date.parse(a.last_update||a.updated_at_utc))[0];
     const projection=number(x.projected_yards),line=number(quote?.line);
     if(projection===null)continue;
     const gap=line===null?null:projection-line;
     const playerSim=playerSims.find(s=>String(s.game_id)===String(game.game_id)&&s.stat_key===key&&
      ((String(s.player_id)===String(x.player_id))||(norm(s.player)===norm(x.player_name))));
     const rates=line===null?{over:null,under:null}:sideRates(playerSim,line);
     let side=rates.over!==null&&rates.under!==null?(rates.over>=rates.under?'Over':'Under'):gap===null?null:gap>0?'Over':gap<0?'Under':null;
     const confidence=side==='Over'?rates.over:side==='Under'?rates.under:null;
     if(line!==null&&!side)continue;
     const item={kind:marketNames[key],pick:x.player_name+' · '+(line===null?projection.toFixed(1)+' projected yards':side+' '+line.toFixed(1)),game:canon(game.away)+' @ '+canon(game.home),
      detail:line===null?'Model yardage projection · current DK prop line unavailable':'Model '+projection.toFixed(1)+' vs DK '+line.toFixed(1)+' · '+(gap>0?'+':'')+gap.toFixed(1)+' gap'+(rates.over===null?' · simulation unavailable':''),
      confidence,overPct:rates.over,underPct:rates.under,line,rank:line===null?projection:Math.abs(gap)/Math.max(1,Math.abs(line))};
     playerCandidates.push(item);
     if(confidence!==null&&confidence>50)blend.push(item);
    }
   }
   const seen=new Set();
   boards.players=playerCandidates.sort((a,b)=>(b.confidence??-1)-(a.confidence??-1)||b.rank-a.rank).filter(x=>{const k=x.pick+'|'+x.kind;if(seen.has(k))return false;seen.add(k);return true;}).slice(0,5);
   boards.blended=blend.sort((a,b)=>b.confidence-a.confidence).slice(0,5);
   render();
   const heading=topPicksHeading((boards[active]||[]).length);
   status.textContent=(heading.note?heading.note+' ':'')+'Updated '+new Date().toLocaleTimeString('en-US',{timeZone:'America/Chicago',hour:'numeric',minute:'2-digit',timeZoneName:'short'})+' · Current slate only.';
  }catch(e){
   boards={players:[],scoring:[],blended:[]};render();status.textContent='Current Top 5 unavailable: waiting for fresh, matching forecast, DraftKings, and simulation feeds.';
  }
 }
 render();refresh();setInterval(refresh,300000);
})();
if(typeof module==='object'&&module.exports) module.exports={topPicksHeading,topPicksTabsCollapsed};