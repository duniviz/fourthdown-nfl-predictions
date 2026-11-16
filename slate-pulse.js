/* Compact live scoreboard that opens the existing matchup detail view. */
(()=>{
 const root=document.getElementById('fd-slate-pulse');
 if(!root)return;
 const $=id=>root.querySelector('#'+id);
 const esc=x=>String(x??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
 const aliases={JAX:'JAC',LA:'LAR',WSH:'WAS'};
 const canon=x=>aliases[String(x||'').toUpperCase()]||String(x||'').toUpperCase();
 const n=x=>x!==null&&x!==undefined&&x!==''&&Number.isFinite(Number(x));
 const teamLogo=t=>'https://a.espncdn.com/i/teamlogos/nfl/500/'+encodeURIComponent(canon(t).toLowerCase())+'.png';
 const teamMarkup=(team,score,showScore)=>'<div class="fd-live-team"><img src="'+esc(teamLogo(team.abbr||team.name))+'" alt="'+esc(team.abbr||team.name||'Team')+' logo" loading="lazy"><strong>'+esc(window.fdTeams?window.fdTeams.label(team.abbr||team.name):team.abbr||team.name)+'</strong><b>'+esc(showScore&&n(score)?score:'—')+'</b></div>';
 const ct=(x,opts)=>new Date(x).toLocaleString('en-US',{timeZone:'America/Chicago',...opts});
 let forecasts=[];
 function projectionFor(g){
  return forecasts.find(p=>{
   const same=(canon(p.home)===canon(g.home.abbr)&&canon(p.away)===canon(g.away.abbr))||(canon(p.away)===canon(g.home.abbr)&&canon(p.home)===canon(g.away.abbr));
   return same&&Math.abs(Date.parse(p.kickoff_utc)-Date.parse(g.date))<12*3600000;
  });
 }
 function card(g,state,index){
  const live=state==='in',final=state==='post',projection=projectionFor(g),kick=Date.parse(g.date);
  const label=live?'LIVE':final?'FINAL':Number.isFinite(kick)?ct(g.date,{weekday:'short',hour:'numeric',minute:'2-digit',timeZoneName:'short'}):'UPCOMING';
  const projected=projection&&n(projection.projected_away_score)&&n(projection.projected_home_score);
  const aux=live?(g.status||'In progress'):final?'Final':projected?'MODEL · '+Number(projection.projected_away_score).toFixed(1)+' – '+Number(projection.projected_home_score).toFixed(1):label;
  const score=live||final;
  return '<button type="button" class="fd-live-board-card '+(live?'is-live':final?'is-final':'is-upcoming')+'" data-game-id="'+esc(g.id)+'" aria-label="'+esc((live?'Open live matchup: ':final?'Open final matchup: ':'Open matchup: ')+g.away.abbr+' at '+g.home.abbr+(live||final?', '+g.away.score+' to '+g.home.score:'') )+'">'+
   '<span class="fd-live-card-kicker"><span class="fd-live-state">'+esc(label)+'</span><span class="fd-live-card-number">#'+(index+1)+'</span></span>'+
   '<span class="fd-live-scoreline">'+teamMarkup(g.away,g.away.score,score)+'<span class="fd-live-at">@</span>'+teamMarkup(g.home,g.home.score,score)+'</span>'+
   '<span class="fd-live-card-detail">'+esc(aux)+'</span><span class="fd-live-card-link">Open matchup <b aria-hidden="true">↗</b></span></button>';
 }
 let fallbackById=new Map(),showingForecastFallback=false;
 function render(){
  const all=Array.isArray(window.fdAllGames)?window.fdAllGames:[];
  const live=all.filter(g=>g.state==='in').sort((a,b)=>Date.parse(a.date)-Date.parse(b.date));
  let upcoming=all.filter(g=>g.state==='pre').sort((a,b)=>Date.parse(a.date)-Date.parse(b.date));
  const finals=all.filter(g=>g.state==='post').sort((a,b)=>Date.parse(b.date)-Date.parse(a.date));
  fallbackById=new Map();
  showingForecastFallback=false;
  if(!live.length&&!upcoming.length){
   const now=Date.now();
   upcoming=forecasts.filter(p=>Date.parse(p.kickoff_utc)>now).map(p=>{
    const g={id:String(p.game_id),date:p.kickoff_utc,state:'pre',status:'Scheduled',broadcast:'NFL',link:null,
     away:{abbr:canon(p.away),name:canon(p.away),logo:'',score:null,record:''},
     home:{abbr:canon(p.home),name:canon(p.home),logo:'',score:null,record:''}};
    fallbackById.set(String(g.id),g);
    return g;
   }).sort((a,b)=>Date.parse(a.date)-Date.parse(b.date));
   showingForecastFallback=upcoming.length>0;
  }
  const chosen=live.length?live.slice(0,5):upcoming.length?upcoming.slice(0,4):finals.slice(0,4);
  const mode=live.length?'LIVE NOW':upcoming.length?'UP NEXT':'FINAL SCORES';
  $('fd-live-board-kicker').textContent=mode+' · NFL WEEK '+(forecasts[0]?.week||'');
  $('fd-live-board-status').textContent=live.length?live.length+' game'+(live.length===1?'':'s')+' in progress · Scores refresh with the live scoreboard feed.':showingForecastFallback?'Live scores are unavailable · Showing upcoming matchups with published projections.':upcoming.length?'No games live right now · Showing the next kickoffs.':'No live or upcoming games · Latest finals shown.';
  $('fd-live-board-cards').innerHTML=chosen.length?chosen.map((g,i)=>card(g,g.state,i)).join(''):'<p class="fd-live-board-empty">Waiting for the live scoreboard and forecast feeds…</p>';
 }
 root.addEventListener('click',event=>{
  const button=event.target.closest('[data-game-id]');
  if(!button)return;
  const game=(window.fdAllGames||[]).find(g=>String(g.id)===button.dataset.gameId)||fallbackById.get(button.dataset.gameId);
  if(!game)return;
  window.dispatchEvent(new CustomEvent('fd-open-matchup',{detail:game}));
 });
 async function loadForecasts(){
  try{
   const r=await fetch('data/live-v2.json?t='+Date.now(),{cache:'no-store'});
   if(r.ok){const data=await r.json();forecasts=Array.isArray(data.games)?data.games:[];}
  }catch(_){}
  render();
 }
 render();
 loadForecasts();
 window.addEventListener('fd-scoreboard-updated',render);
 setInterval(render,15000);
})();