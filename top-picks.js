/* Current-slate Top 5 board. Player gaps are research signals, not calibrated probabilities. */
(function(){
 const root=document.getElementById('fd-top-picks-list'),status=document.getElementById('fd-top-picks-status');
 if(!root||!status)return;
 const tabs=[...document.querySelectorAll('[data-fd-top-picks-tab]')];
 let active='blended',boards={players:[],scoring:[],blended:[]};
 const esc=x=>String(x??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
 const norm=x=>String(x||'').toLowerCase().replace(/[^a-z0-9]/g,'');
 const aliases={JAX:'JAC',LA:'LAR',WSH:'WAS'};
 const canon=x=>aliases[String(x||'').toUpperCase()]||String(x||'').toUpperCase();
 const teams={ARI:'arizona cardinals',ATL:'atlanta falcons',BAL:'baltimore ravens',BUF:'buffalo bills',CAR:'carolina panthers',CHI:'chicago bears',CIN:'cincinnati bengals',CLE:'cleveland browns',DAL:'dallas cowboys',DEN:'denver broncos',DET:'detroit lions',GB:'green bay packers',HOU:'houston texans',IND:'indianapolis colts',JAC:'jacksonville jaguars',KC:'kansas city chiefs',LV:'las vegas raiders',LAC:'los angeles chargers',LAR:'los angeles rams',MIA:'miami dolphins',MIN:'minnesota vikings',NE:'new england patriots',NO:'new orleans saints',NYG:'new york giants',NYJ:'new york jets',PHI:'philadelphia eagles',PIT:'pittsburgh steelers',SF:'san francisco 49ers',SEA:'seattle seahawks',TB:'tampa bay buccaneers',TEN:'tennessee titans',WAS:'washington commanders'};
 const propAliases={player_passing_completions:'player_pass_completions',player_passing_attempts:'player_pass_attempts',player_rushing_attempts:'player_rush_attempts',player_passing_yards:'player_pass_yds',player_rushing_yards:'player_rush_yds',player_receiving_yards:'player_rec_yds'};
 const marketNames={player_pass_completions:'Completions',player_pass_attempts:'Pass attempts',player_rush_attempts:'Rush attempts',player_receptions:'Receptions',player_pass_yds:'Passing yards',player_rush_yds:'Rushing yards',player_rec_yds:'Receiving yards'};
 const nameOf=x=>teams[canon(x)]||String(x||'');
 const number=x=>x!==null&&x!==''&&x!==undefined&&Number.isFinite(Number(x))?Number(x):null;
 function render(){
  const rows=boards[active]||[];
  root.innerHTML=rows.length?rows.map((x,i)=>'<article class="fd-top-pick"><div class="fd-top-pick-kicker">#'+(i+1)+' · '+esc(x.kind)+'</div><h3>'+esc(x.pick)+'</h3><p>'+esc(x.detail)+'</p><div class="fd-top-pick-meta">'+(x.confidence!==null?'<strong>'+Number(x.confidence).toFixed(1)+'% simulated</strong>':'<strong>Projection gap · no probability</strong>')+'<span>'+esc(x.game||'')+'</span></div></article>').join(''):'<p class="fd-top-pick-empty">No eligible current-slate picks are available from fresh feeds. The board will update when matching forecasts, lines, and simulations are published.</p>';
  tabs.forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.fdTopPicksTab===active)));
  status.textContent=active==='players'?'Largest current player model-to-DK differences. These are not calibrated probabilities or betting recommendations.':active==='scoring'?'Game total picks ranked by the published simulation rate for the exact current DraftKings total.':'Game winner, spread, and total picks ranked by published simulation rates for matched current DraftKings lines. Player props stay separate because player hit rates are not calibrated.';
 }
 tabs.forEach(b=>b.addEventListener('click',()=>{active=b.dataset.fdTopPicksTab;render();}));
 async function refresh(){
  try{
   const paths=['data/live-v2.json','data/dk-game-odds.json','data/simulations.json','data/count-projections.json','data/dk-odds.json','data/research-prop-desk.json'];
   const rs=await Promise.all(paths.map(p=>fetch(p+'?t='+Date.now(),{cache:'no-store'})));
   if(rs.some(r=>!r.ok))throw Error('Feed unavailable');
   const [forecast,market,sim,count,dk,desk]=await Promise.all(rs.map(r=>r.json()));
   const now=Date.now(),stamp=Date.parse(forecast.generated_at_utc),quoteStamp=Date.parse(market.snapshot_date_utc);
   if(!Number.isFinite(stamp)||stamp>now+300000||now-stamp>36*3600000||!Number.isFinite(quoteStamp)||quoteStamp>now+300000||now-quoteStamp>36*3600000)throw Error('Stale current-slate feed');
   const slate=window.fdScheduleWindow?.get(new Date());
   if(!slate)throw Error('Schedule window unavailable');
   const upcoming=(forecast.games||[]).filter(g=>g.kickoff_utc&&Date.parse(g.kickoff_utc)>now&&window.fdScheduleWindow.contains(slate,g.kickoff_utc));
   const quotes=new Map((market.games||[]).filter(q=>q.bookmaker==='draftkings'&&q.home&&q.away).map(q=>[canon(q.away)+'|'+canon(q.home),q]));
   const simulations=Array.isArray(sim.games)?sim.games:[];
   const candidates=[];
   for(const p of upcoming){
    const q=quotes.get(canon(p.away)+'|'+canon(p.home)),s=simulations.find(x=>String(x.game_id)===String(p.game_id));
    if(!q||!s||Math.abs(Date.parse(q.commence_time)-Date.parse(p.kickoff_utc))>3600000)continue;
    const qtime=Date.parse(q.updated_at_utc||q.observed_at_utc||market.snapshot_date_utc),kick=Date.parse(p.kickoff_utc);
    if(!Number.isFinite(qtime)||qtime>now||now-qtime>36*3600000||qtime>=kick)continue;
    const home=number(p.projected_home_score),away=number(p.projected_away_score);
    const pct=x=>number(x)!==null&&Number(x)>=0&&Number(x)<=100?Number(x):null;
    const base={game:p.away+' @ '+p.home,detail:'Projected score '+away?.toFixed(1)+'–'+home?.toFixed(1)};
    if(home!==null&&away!==null&&home!==away){
     const team=home>away?p.home:p.away,confidence=pct(team===p.home?s.home_win_pct:s.away_win_pct);
     if(confidence!==null&&confidence>50)candidates.push({...base,kind:'Winner',pick:team+' to win',confidence});
    }
    const total=number(q.total),projected=home!==null&&away!==null?home+away:null,simTotal=number(s.dk_total);
    if(total!==null&&projected!==null&&simTotal===total&&projected!==total){
     const over=projected>total,confidence=pct(over?s.over_cover_pct:s.under_cover_pct);
     if(confidence!==null&&confidence>50){const item={...base,kind:'Game total',pick:(over?'Over ':'Under ')+total.toFixed(1),confidence,detail:'Projected total '+projected.toFixed(1)+' · DK total '+total.toFixed(1)};boards.scoring.push(item);candidates.push(item);}
    }
    const spread=number(q.home_spread),simSpread=number(s.dk_home_spread);
    if(spread!==null&&simSpread===spread&&home!==null&&away!==null){
     const edge=(home-away)+spread;
     if(edge!==0){const homePick=edge>0,confidence=pct(homePick?s.home_cover_pct:s.away_cover_pct);if(confidence!==null&&confidence>50)candidates.push({...base,kind:'Against the spread',pick:homePick?p.home+' '+(spread>0?'+':'')+spread.toFixed(1):p.away+' '+(-spread>0?'+':'')+(-spread).toFixed(1),confidence,detail:'Model spread edge '+Math.abs(edge).toFixed(1)+' pts'});}
    }
   }
   boards.scoring=boards.scoring.sort((a,b)=>b.confidence-a.confidence).slice(0,5);
   boards.blended=candidates.sort((a,b)=>b.confidence-a.confidence).slice(0,5);
   boards.players=[];
   const kickoffById=new Map(upcoming.map(g=>[String(g.game_id),Date.parse(g.kickoff_utc)]));
   const oddsRows=Array.isArray(dk.rows)?dk.rows:[];
   const playerCandidates=[];
   const countStamp=Date.parse(count.generated_at_utc);
   if(Number.isFinite(countStamp)&&countStamp<=now&&now-countStamp<=36*3600000){
    for(const x of count.players||[]){
     const team=canon(x.team),opponent=canon(x.opponent),marketKey=propAliases[x.market_key]||x.market_key,start=kickoffById.get(String(x.game_id));
     if(!marketNames[marketKey]||!start)continue;
     const quote=oddsRows.filter(q=>norm(q.player)===norm(x.player)&&q.market_key===marketKey&&norm(q.away_team+' '+q.home_team).includes(norm(nameOf(team)))&&Math.abs(Date.parse(q.commence_time)-start)<3600000)
      .filter(q=>{const t=Date.parse(q.last_update||q.updated_at_utc);return Number.isFinite(t)&&t<=now&&now-t<=36*3600000&&t<start;})
      .sort((a,b)=>Date.parse(b.last_update||b.updated_at_utc)-Date.parse(a.last_update||a.updated_at_utc))[0];
     const line=number(quote?.line),projection=number(x.projection);
     if(line!==null&&projection!==null&&line!==projection){const gap=projection-line;playerCandidates.push({kind:marketNames[marketKey],pick:x.player+' · '+(gap>0?'Over ':'Under ')+line.toFixed(1),game:team+' @ '+opponent,detail:'Model '+projection.toFixed(1)+' vs DK '+line.toFixed(1)+' · '+(gap>0?'+':'')+gap.toFixed(1)+' gap',confidence:null,rank:Math.abs(gap)/Math.max(1,Math.abs(line))});}
    }
   }
   const yardStamp=Date.parse(desk.generated_at_utc);
   if(Number.isFinite(yardStamp)&&yardStamp<=now&&now-yardStamp<=36*3600000){
    const keys={passing_yards:'player_pass_yds',rushing_yards:'player_rush_yds',receiving_yards:'player_rec_yds'};
    for(const x of desk.comparisons||[]){
     const marketKey=keys[x.market],team=canon(x.team),start=kickoffById.get(String(x.game_id));
     if(!marketKey||!start)continue;
     const quote=oddsRows.filter(q=>norm(q.player)===norm(x.player_name)&&q.market_key===marketKey&&norm(q.away_team+' '+q.home_team).includes(norm(nameOf(team)))&&Math.abs(Date.parse(q.commence_time)-start)<3600000)
      .filter(q=>{const t=Date.parse(q.last_update||q.updated_at_utc);return Number.isFinite(t)&&t<=now&&now-t<=36*3600000&&t<start;})
      .sort((a,b)=>Date.parse(b.last_update||b.updated_at_utc)-Date.parse(a.last_update||a.updated_at_utc))[0];
     const projection=number(x.projected_yards),line=number(quote?.line);
     if(line!==null&&projection!==null&&line!==projection){const gap=projection-line,g=upcoming.find(game=>String(game.game_id)===String(x.game_id));playerCandidates.push({kind:marketNames[marketKey],pick:x.player_name+' · '+(gap>0?'Over ':'Under ')+line.toFixed(1),game:team+' @ '+canon(g?.home===team?g?.away:g?.home),detail:'Model '+projection.toFixed(1)+' vs DK '+line.toFixed(1)+' · '+(gap>0?'+':'')+gap.toFixed(1)+' gap'+(x.ranking_status==='eligible'?'':' · status unverified'),confidence:null,rank:Math.abs(gap)/Math.max(1,Math.abs(line))});}
    }
   }
   const seen=new Set();boards.players=playerCandidates.sort((a,b)=>b.rank-a.rank).filter(x=>{const k=x.pick+'|'+x.kind;if(seen.has(k))return false;seen.add(k);return true;}).slice(0,5);
   render();
   status.textContent='Updated '+new Date().toLocaleTimeString('en-US',{timeZone:'America/Chicago',hour:'numeric',minute:'2-digit',timeZoneName:'short'})+' · Current slate only.';
  }catch(e){
   boards={players:[],scoring:[],blended:[]};render();status.textContent='Current Top 5 unavailable: waiting for fresh, matching forecast, DraftKings, and simulation feeds.';
  }
 }
 render();refresh();setInterval(refresh,300000);
})();