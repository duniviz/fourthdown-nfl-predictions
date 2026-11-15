/* Current-slate Top 5 board. Yardage picks join the blend only with an exact-line simulation. */
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
 const marketNames={passing_yards:'Passing yards',rushing_yards:'Rushing yards',receiving_yards:'Receiving yards'};
 const quoteMarkets={passing_yards:'player_pass_yds',rushing_yards:'player_rush_yds',receiving_yards:'player_rec_yds'};
 const nameOf=x=>teams[canon(x)]||String(x||'');
 const number=x=>x!==null&&x!==''&&x!==undefined&&Number.isFinite(Number(x))?Number(x):null;
 const pct=x=>number(x)!==null&&Number(x)>=0&&Number(x)<=100?Number(x):null;
 function render(){
  const rows=boards[active]||[];
  root.innerHTML=rows.length?rows.map((x,i)=>'<article class="fd-top-pick"><div class="fd-top-pick-kicker">#'+(i+1)+' · '+esc(x.kind)+'</div><h3>'+esc(x.pick)+'</h3><p>'+esc(x.detail)+'</p><div class="fd-top-pick-meta">'+(x.confidence!==null?'<strong>'+Number(x.confidence).toFixed(1)+'% simulated</strong>':'<strong>Projection gap · no matched simulation</strong>')+'<span>'+esc(x.game||'')+'</span></div></article>').join(''):'<p class="fd-top-pick-empty">No eligible current-slate picks are available from fresh feeds. The board will update when matching forecasts, lines, and simulations are published.</p>';
  tabs.forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.fdTopPicksTab===active)));
  status.textContent=active==='players'?'Passing, rushing, and receiving yards only. Player cards show projection gaps; exact-line simulation rates appear when available.':active==='scoring'?'One leading O/U, outright-winner, and spread pick, when current DraftKings lines and matching simulations support them.':'Top five across O/U, winner, spread, and player yardage picks with an exact matching simulation above 50%.';
 }
 tabs.forEach(b=>b.addEventListener('click',()=>{active=b.dataset.fdTopPicksTab;render();}));
 async function refresh(){
  try{
   const paths=['data/live-v2.json','data/dk-game-odds.json','data/simulations.json','data/dk-odds.json','data/research-prop-desk.json'];
   const rs=await Promise.all(paths.map(p=>fetch(p+'?t='+Date.now(),{cache:'no-store'})));
   if(rs.some(r=>!r.ok))throw Error('Feed unavailable');
   const [forecast,market,sim,dk,desk]=await Promise.all(rs.map(r=>r.json()));
   const now=Date.now(),stamp=Date.parse(forecast.generated_at_utc),quoteStamp=Date.parse(market.snapshot_date_utc),simStamp=Date.parse(sim.generated_at_utc);
   if(!Number.isFinite(stamp)||stamp>now+300000||now-stamp>36*3600000||!Number.isFinite(quoteStamp)||quoteStamp>now+300000||now-quoteStamp>36*3600000)throw Error('Stale current-slate feed');
   const simulationFresh=Number.isFinite(simStamp)&&simStamp<=now+300000&&now-simStamp<=36*3600000;
   const slate=window.fdScheduleWindow?.get(new Date());
   if(!slate)throw Error('Schedule window unavailable');
   const upcoming=(forecast.games||[]).filter(g=>g.kickoff_utc&&Date.parse(g.kickoff_utc)>now&&window.fdScheduleWindow.contains(slate,g.kickoff_utc));
   const quotes=new Map();
   for(const q of market.games||[]){
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
    const base={game:p.away+' @ '+p.home,detail:'Projected score '+(home===null||away===null?'—':away.toFixed(1)+'–'+home.toFixed(1))};
    if(home!==null&&away!==null&&home!==away){
     const team=home>away?p.home:p.away,confidence=pct(team===p.home?s.home_win_pct:s.away_win_pct);
     if(confidence!==null&&confidence>50)gamePicks.push({...base,kind:'Winner',pick:team+' to win',confidence});
    }
    const total=number(q.total),projected=home!==null&&away!==null?home+away:null;
    if(total!==null&&projected!==null&&number(s.dk_total)===total&&projected!==total){
     const over=projected>total,confidence=pct(over?s.over_cover_pct:s.under_cover_pct);
     if(confidence!==null&&confidence>50)gamePicks.push({...base,kind:'O/U',pick:(over?'Over ':'Under ')+total.toFixed(1),confidence,detail:'Projected total '+projected.toFixed(1)+' · DK total '+total.toFixed(1)});
    }
    const spread=number(q.home_spread);
    if(spread!==null&&number(s.dk_home_spread)===spread&&home!==null&&away!==null){
     const edge=(home-away)+spread;
     if(edge!==0){const homePick=edge>0,confidence=pct(homePick?s.home_cover_pct:s.away_cover_pct);if(confidence!==null&&confidence>50)gamePicks.push({...base,kind:'Spread',pick:homePick?p.home+' '+(spread>0?'+':'')+spread.toFixed(1):p.away+' '+(-spread>0?'+':'')+(-spread).toFixed(1),confidence,detail:'Model spread edge '+Math.abs(edge).toFixed(1)+' pts'});}
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
       norm(q.away_team).includes(norm(nameOf(game.away)))&&norm(q.home_team).includes(norm(nameOf(game.home)))&&
       Math.abs(Date.parse(q.commence_time)-start)<3600000)
      .filter(q=>{const t=Date.parse(q.last_update||q.updated_at_utc);return Number.isFinite(t)&&t<=now&&now-t<=36*3600000&&t<start;})
      .sort((a,b)=>Date.parse(b.last_update||b.updated_at_utc)-Date.parse(a.last_update||a.updated_at_utc))[0];
     const projection=number(x.projected_yards),line=number(quote?.line);
     if(line===null||projection===null||line===projection)continue;
     const gap=projection-line,side=gap>0?'Over':'Under';
     const playerSim=playerSims.find(s=>String(s.game_id)===String(game.game_id)&&String(s.player_id)===String(x.player_id)&&s.stat_key===key);
     const simLine=number(playerSim?.dk_line),confidence=simLine!==null&&Math.abs(simLine-line)<.0001?pct(side==='Over'?playerSim.over_pct:playerSim.under_pct):null;
     const item={kind:marketNames[key],pick:x.player_name+' · '+side+' '+line.toFixed(1),game:canon(game.away)+' @ '+canon(game.home),
      detail:'Model '+projection.toFixed(1)+' vs DK '+line.toFixed(1)+' · '+(gap>0?'+':'')+gap.toFixed(1)+' gap'+(confidence===null?' · simulation unavailable':''),
      confidence,rank:Math.abs(gap)/Math.max(1,Math.abs(line))};
     playerCandidates.push(item);
     if(confidence!==null&&confidence>50)blend.push(item);
    }
   }
   const seen=new Set();
   boards.players=playerCandidates.sort((a,b)=>b.rank-a.rank).filter(x=>{const k=x.pick+'|'+x.kind;if(seen.has(k))return false;seen.add(k);return true;}).slice(0,5);
   boards.blended=blend.sort((a,b)=>b.confidence-a.confidence).slice(0,5);
   render();
   status.textContent='Updated '+new Date().toLocaleTimeString('en-US',{timeZone:'America/Chicago',hour:'numeric',minute:'2-digit',timeZoneName:'short'})+' · Current slate only.';
  }catch(e){
   boards={players:[],scoring:[],blended:[]};render();status.textContent='Current Top 5 unavailable: waiting for fresh, matching forecast, DraftKings, and simulation feeds.';
  }
 }
 render();refresh();setInterval(refresh,300000);
})();