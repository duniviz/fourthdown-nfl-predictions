(function(root,factory){if(typeof module==='object'&&module.exports)module.exports=factory();else root.FDGameTopPicks=factory();})(typeof globalThis!=='undefined'?globalThis:this,function(){
 'use strict';
 const number=x=>x!==null&&x!==undefined&&x!==''&&Number.isFinite(Number(x))?Number(x):null;
 const pct=x=>number(x)!==null&&Number(x)>=0&&Number(x)<=100?Number(x):null;
 const norm=x=>String(x||'').toLowerCase().replace(/[^a-z0-9]/g,'');
 const canon=x=>({JAX:'JAC',LAR:'LA',WSH:'WAS'}[String(x||'').toUpperCase()]||String(x||'').toUpperCase());
 const esc=x=>String(x??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
 const fmt=x=>number(x)===null?'—':Number(x).toFixed(1);
 const yardMarkets=new Set(['passing_yards','rushing_yards','receiving_yards']);
 function sideRates(sim,line){
  const stored=number(sim?.dk_line),over=pct(sim?.over_pct),under=pct(sim?.under_pct);
  if(stored!==null&&Math.abs(stored-line)<0.0001&&over!==null&&under!==null)return {over,under};
  const draws=Array.isArray(sim?.sorted_draws)?sim.sorted_draws.map(number).filter(x=>x!==null):[];
  if(!draws.length)return {over:null,under:null};
  return {over:100*draws.filter(x=>x>line).length/draws.length,under:100*draws.filter(x=>x<line).length/draws.length};
 }
 function render({game={},projection=null,gameLine=null,gameSimulation=null,playerSimulations=[],players=[]}={}){
  const home=canon(game.home?.abbr||projection?.home),away=canon(game.away?.abbr||projection?.away);
  const gameId=String(projection?.game_id||'');
  const kickoff=Date.parse(game.date||projection?.kickoff_utc||''),now=Date.now();
  const candidates=[];
  const homeScore=number(projection?.projected_home_score),awayScore=number(projection?.projected_away_score);
  const spread=number(gameLine?.home_spread),totalLine=number(gameLine?.total);
  const quoteAvailable=spread!==null||totalLine!==null;
  if(gameSimulation&&quoteAvailable&&homeScore!==null&&awayScore!==null){
   const homePct=pct(gameSimulation.home_win_pct),awayPct=pct(gameSimulation.away_win_pct);
   if(homeScore!==awayScore){
    const team=homeScore>awayScore?home:away,confidence=team===home?homePct:awayPct;
    if(confidence!==null&&confidence>50)candidates.push({kind:'Winner',pick:team+' to win',confidence,detail:'Simulated win chance · '+away+' '+fmt(awayScore)+' – '+home+' '+fmt(homeScore)});
   }
   if(totalLine!==null&&number(gameSimulation.dk_total)===totalLine){
    const projectedTotal=homeScore+awayScore,over=projectedTotal>totalLine,confidence=pct(over?gameSimulation.over_cover_pct:gameSimulation.under_cover_pct);
    if(projectedTotal!==totalLine&&confidence!==null&&confidence>50)candidates.push({kind:'Game total',pick:(over?'Over ':'Under ')+fmt(totalLine),confidence,detail:'Model total '+fmt(projectedTotal)+' · saved DK total '+fmt(totalLine)});
   }
   if(spread!==null&&number(gameSimulation.dk_home_spread)===spread){
    const edge=homeScore-awayScore+spread;
    if(edge!==0){
     const homePick=edge>0,confidence=pct(homePick?gameSimulation.home_cover_pct:gameSimulation.away_cover_pct);
     const pickTeam=homePick?home:away,line=homePick?spread:-spread;
     if(confidence!==null&&confidence>50)candidates.push({kind:'Spread',pick:pickTeam+' '+(line>0?'+':'')+fmt(line),confidence,detail:'Model spread edge '+fmt(Math.abs(edge))+' points'});
    }
   }
  }
  const simulations=Array.isArray(playerSimulations)?playerSimulations:[];
  const playerKey=value=>norm(value).replace(/(?:jr|sr|ii|iii|iv|v)$/,'');
  const quoteTime=x=>{
   for(const value of [x.dk_quote_time,x.dk_quote_captured_at_utc,x.quote_time,x.captured_at_utc,x.snapshot_date_utc]){
    const stamp=Date.parse(value||'');
    if(Number.isFinite(stamp))return stamp;
   }
   return null;
  };
  for(const x of Array.isArray(players)?players:[]){
   const market=String(x.stat_key||'');
   const quoteAt=quoteTime(x);
   // A valid line already attached to the projection may lack quote metadata in
   // player-research. Keep it eligible for a future game unless marked stale;
   // when a timestamp exists, still require a genuinely pregame, saved quote.
   if(!yardMarkets.has(market)||x.verified_starter_only||x.dk_quote_stale||number(x.projection)===null||number(x.dk_line)===null||!Number.isFinite(kickoff)||kickoff<=now||(quoteAt!==null&&(quoteAt>=kickoff||quoteAt>now)))continue;
   if(gameId&&String(x.game_id||'')!==gameId)continue;
   const team=canon(x.team);
   if(team!==home&&team!==away)continue;
   const sim=simulations.find(s=>String(s.game_id)===String(x.game_id)&&String(s.stat_key)===market&&
    ((x.player_id&&s.player_id&&String(s.player_id)===String(x.player_id))||playerKey(s.player)===playerKey(x.player)));
   if(!sim)continue;
   const rates=sideRates(sim,Number(x.dk_line));
   if(rates.over===null||rates.under===null)continue;
   const side=rates.over>=rates.under?'Over':'Under',confidence=side==='Over'?rates.over:rates.under;
   if(confidence<=50)continue;
   const label=market==='passing_yards'?'Passing yards':market==='rushing_yards'?'Rushing yards':'Receiving yards';
   candidates.push({kind:label,pick:String(x.player)+' · '+side+' '+fmt(x.dk_line),confidence,
    detail:'Model '+fmt(x.projection)+' yards · saved DK line '+fmt(x.dk_line),
    overPct:rates.over,underPct:rates.under});
  }
  candidates.sort((a,b)=>b.confidence-a.confidence);
  const top=candidates.slice(0,3);
  const body=top.length?top.map((x,i)=>'<article class="fd-top-pick"><div class="fd-top-pick-kicker">#'+(i+1)+' · '+esc(x.kind)+'</div><h3>'+esc(x.pick)+'</h3><p>'+esc(x.detail)+'</p><div class="fd-top-pick-prob"><div class="fd-top-pick-prob-bar"><i style="width:'+x.confidence.toFixed(1)+'%"></i><b style="width:'+(100-x.confidence).toFixed(1)+'%"></b></div><div><span>Pick '+x.confidence.toFixed(1)+'% simulated</span><span>Other outcomes</span></div></div></article>').join(''):'<p class="fd-top-pick-empty">No picks have both a saved pregame line and a matching simulation for this game.</p>';
  const note=top.length<3?'Showing '+top.length+' qualifying pick'+(top.length===1?'':'s')+'. Yard picks need a saved pregame DraftKings line and a matching player simulation.':'Ranked by simulated hit chance · estimates, not guarantees.';
  return '<section class="fd-modal-section fd-top-picks fd-game-top-picks" aria-label="Top simulated picks for this game"><h3>Top picks for this game</h3><div class="fd-top-picks-list">'+body+'</div><p class="fd-top-picks-note">'+esc(note)+' · Estimates, not guarantees.</p></section>';
 }
 return {render};
});
