/* FOURTHDOWN visual layer: enhances existing Top Picks, scoreboard and prop cards.
 * Read-only: no projections, DK picks, clocks, or historical records are modified.
 */
(function(root,factory){
 const api=factory();
 if(typeof module==="object"&&module.exports)module.exports=api;
 if(root&&root.document)api.mount(root);
})(typeof globalThis!=="undefined"?globalThis:this,function(){
 "use strict";
 const n=x=>x!==null&&x!==undefined&&x!==""&&Number.isFinite(Number(x))?Number(x):null;
 const clamp=x=>Math.max(0,Math.min(100,x));
 const esc=x=>String(x??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
 const canon=x=>({JAX:"JAC",LA:"LAR",WSH:"WAS"}[String(x||"").toUpperCase()]||String(x||"").toUpperCase());
 function gameSimulation(game,live,sims){
   const away=canon(game?.away?.abbr),home=canon(game?.home?.abbr),kick=Date.parse(game?.date);
   if(!away||!home||!Number.isFinite(kick))return null;
   const projection=(live?.games||[]).find(g=>canon(g.away)===away&&canon(g.home)===home&&Date.parse(g.kickoff_utc)===kick);
   if(!projection)return null;
   const sim=(sims?.games||[]).find(x=>String(x.game_id)===String(projection.game_id));
   if(!sim||n(sim.simulations)===null||n(sim.simulations)<=0)return null;
   const awayPct=n(sim.away_win_pct),homePct=n(sim.home_win_pct);
   if(awayPct===null||homePct===null||awayPct<0||homePct<0||awayPct>100||homePct>100||Math.abs(awayPct+homePct-100)>3)return null;
   return {projection,awayPct,homePct,simulations:sim.simulations};
 }
 function linePoints(rows,key){
   const xs=(rows||[]).filter(r=>n(r[key])!==null&&Number.isFinite(Date.parse(r.captured_at_utc)))
     .map(r=>({t:Date.parse(r.captured_at_utc),v:n(r[key])})).sort((a,b)=>a.t-b.t);
   const dedup=[];for(const p of xs)if(!dedup.length||dedup[dedup.length-1].t!==p.t||dedup[dedup.length-1].v!==p.v)dedup.push(p);
   return dedup;
 }
 function sparkline(points){
   if(points.length<2)return "";
   const v=points.map(p=>p.v),minimum=Math.min(...v),maximum=Math.max(...v),range=Math.max(0.5,maximum-minimum);
   const t0=points[0].t,t1=points[points.length-1].t,dt=Math.max(1,t1-t0);
   const coords=points.map(p=>[7+306*(p.t-t0)/dt,57-42*(p.v-minimum)/range]);
   const line=coords.map(([x,y])=>x.toFixed(1)+","+y.toFixed(1)).join(" ");
   const circles=coords.map(([x,y],i)=>i===0||i===coords.length-1?'<circle cx="'+x.toFixed(1)+'" cy="'+y.toFixed(1)+'" r="4.5"></circle>':"").join("");
   return '<svg class="fd-v5-spark" viewBox="0 0 320 70" role="img" aria-label="Saved DK line changed from '+esc(points[0].v.toFixed(1))+' to '+esc(points[points.length-1].v.toFixed(1))+' over '+points.length+' verified snapshots"><line x1="7" y1="57" x2="313" y2="57" class="fd-v5-axis"></line><polyline points="'+line+'"></polyline>'+circles+'</svg>';
 }
 function historyChart(records,field,title,formatter){
   const pts=linePoints(records,field);
   if(!pts.length)return '<div class="fd-v5-trend-card"><b>'+esc(title)+'</b><small>No verified pregame quotes</small></div>';
   const first=pts[0].v,last=pts[pts.length-1].v,delta=last-first;
   return '<div class="fd-v5-trend-card"><div class="fd-v5-trend-head"><b>'+esc(title)+'</b><span>'+esc(formatter(last))+'</span></div>'+
     (pts.length>1?sparkline(pts):'<div class="fd-v5-no-trend">One saved quote · no movement to chart</div>')+
     '<small>First saved '+esc(formatter(first))+' · Latest '+esc(formatter(last))+
     (pts.length>1?' · Change '+(delta>0?"+":"")+esc(delta.toFixed(1)):'')+'</small></div>';
 }
 function chartPanel(game,history){
   const collect=typeof window!=="undefined"?window.FDMarketHistory?.collect:null;
   if(typeof collect!=="function")return "";
   const rows=collect(game,history||{},{},{},null);
   if(!rows.length)return "";
   const sign=v=>v>0?"+"+v.toFixed(1):v===0?"PK":v.toFixed(1);
   return '<div class="fd-v5-trend-grid">'+historyChart(rows,"spread","Home spread",sign)+historyChart(rows,"total","Game total",v=>v.toFixed(1))+'</div><p class="fd-v5-caveat">Saved pregame DraftKings quotes only · first saved is not necessarily opening; last saved is not necessarily closing.</p>';
 }
 function meter(label,pct){
   const v=n(pct);if(v===null||v<0||v>100)return "";
   return '<div class="fd-v5-gauge" role="img" aria-label="'+esc(label)+': '+v.toFixed(1)+' percent in matched simulations"><div class="fd-v5-dial" style="--fd-v5-pct:'+clamp(v).toFixed(1)+'"><span>'+v.toFixed(0)+'<small>%</small></span></div><div><b>'+esc(label)+'</b><small>Simulated outcome rate<br>Not calibrated betting confidence</small></div></div>';
 }
 function scoreboardVisual(game,live,sims){
   const paired=gameSimulation(game,live,sims);
   if(!paired)return '<div class="fd-v5-score-graphic fd-v5-muted">Matching game simulation unavailable · prediction numbers remain in the card below.</div>';
   const p=paired.projection,away=n(p.projected_away_score),home=n(p.projected_home_score);
   const projected=away!==null&&home!==null?
      '<div class="fd-v5-forecast"><span>'+esc(canon(game.away.abbr))+'<b>'+away.toFixed(1)+'</b></span><i>PROJECTED</i><span>'+esc(canon(game.home.abbr))+'<b>'+home.toFixed(1)+'</b></span></div>':"";
   const winner=paired.homePct>=paired.awayPct?canon(game.home.abbr):canon(game.away.abbr);
   const winPct=Math.max(paired.homePct,paired.awayPct);
   const bar='<div class="fd-v5-split" role="img" aria-label="'+esc(canon(game.away.abbr))+' '+paired.awayPct.toFixed(1)+' percent and '+esc(canon(game.home.abbr))+' '+paired.homePct.toFixed(1)+' percent simulated win rate"><i style="width:'+clamp(paired.awayPct)+'%"></i><i style="width:'+clamp(paired.homePct)+'%"></i></div>';
   return '<div class="fd-v5-score-graphic">'+projected+bar+'<div class="fd-v5-prob-labels"><span>'+esc(canon(game.away.abbr))+' '+paired.awayPct.toFixed(1)+'%</span><span>'+esc(canon(game.home.abbr))+' '+paired.homePct.toFixed(1)+'%</span></div>'+meter(winner+' win',winPct)+'</div>';
 }
 function upgradePick(node){
   const first=node.querySelector(".fd-top-pick");if(!first||first.querySelector(".fd-v5-spot"))return;
   const header=document.createElement("div");header.className="fd-v5-spot";
   header.innerHTML='<span>★ FEATURED · HIGHEST-RANKED VISIBLE PICK</span><small>Ranked by the existing Top Picks logic</small>';
   first.prepend(header);
   const value=first.querySelector(".fd-top-pick-meta strong")?.textContent||"";
   const matched=value.match(/(\d+(?:\.\d+)?)% simulated/i);
   if(matched){const v=Number(matched[1]);if(v>=0&&v<=100){const gauge=document.createElement("div");gauge.innerHTML=meter("Simulation estimate",v);first.append(gauge);}}
 }
 function attachCards(win,state){
   const board=win.document.getElementById("scoreboard-cards");if(!board)return;
   const games=win.fdVisibleGames||[];
   board.querySelectorAll(":scope > article.scorecard").forEach(card=>{
     if(card.dataset.fdV5Ready)return;
     const id=card.querySelector("[data-matchup-id]")?.getAttribute("data-matchup-id");
     const game=games.find(g=>String(g.id)===String(id));
     if(!game)return;
     card.dataset.fdV5Ready="true";
     card.classList.add("fd-v5-broadcast-card");
     const score=win.document.createElement("div");
     score.className="fd-v5-score-box";
     score.innerHTML=scoreboardVisual(game,state.live,state.sim);
     const anchor=card.querySelector(".score-teams");
     if(anchor)anchor.insertAdjacentElement("afterend",score);
     else card.querySelector(".score-head")?.insertAdjacentElement("afterend",score);
     const details=card.querySelector("details.fd-market-history");
     if(details&&typeof win.FDMarketHistory?.collect==="function"){
       const html=chartPanel(game,state.history);
       if(html){const box=win.document.createElement("div");box.className="fd-v5-line-plots";box.innerHTML=html;details.append(box);}
     }
   });
 }
 function upgradeProps(win){
   // Existing Prop Desk already calculates the model-to-line visual correctly.
   // Enhance presentation and accessibility; never infer a DK line or an edge.
   win.document.querySelectorAll("#bet-cards .bet-card, #fd-extra-list .bet-card, .fd-unified-prop").forEach(card=>{
     if(card.dataset.fdV5Prop)return;
     card.dataset.fdV5Prop="true";card.classList.add("fd-v5-prop-card");
     const player=card.querySelector(".bet-name h3, .fd-unified-prop-head strong");
     if(player)player.classList.add("fd-v5-player-name");
     const visuals=card.querySelector(".fd-prop-visual");
     if(visuals)visuals.classList.add("fd-v5-prop-chart");
   });
 }
 function mount(win){
   const state={live:null,sim:null,history:{}};
   const redraw=()=>{
     const picks=win.document.getElementById("fd-top-picks-list");
     if(picks)upgradePick(picks);
     attachCards(win,state);upgradeProps(win);
   };
   const load=async()=>{
     const names=["data/live-v2.json","data/simulations.json","data/dk-game-line-history.json"];
     const results=await Promise.allSettled(names.map(p=>win.fetch(p,{cache:"no-store"}).then(r=>{if(!r.ok)throw Error("Unavailable: "+p);return r.json()})));
     state.live=results[0].status==="fulfilled"?results[0].value:null;
     state.sim=results[1].status==="fulfilled"?results[1].value:null;
     state.history=results[2].status==="fulfilled"?results[2].value?.games||{}:{};
     redraw();
   };
   let queued=false;
   const schedule=()=>{if(queued)return;queued=true;win.requestAnimationFrame(()=>{queued=false;redraw()});};
   for(const id of ["scoreboard-cards","fd-top-picks-list","bet-cards","fd-extra-list","fd-modal-body"]){
     const target=win.document.getElementById(id);
     if(target)new MutationObserver(schedule).observe(target,{childList:true,subtree:false});
   }
   redraw();load().catch(()=>{});win.setInterval(()=>load().catch(()=>{}),300000);
 }
 return {mount,gameSimulation,linePoints,sparkline,historyChart};
});
