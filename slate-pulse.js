/* Visual game-day overview from current published forecast and DK line snapshots. */
(()=>{
 const root=document.getElementById('fd-slate-pulse');
 if(!root)return;
 const $=id=>root.querySelector('#'+id);
 const esc=x=>String(x??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
 const aliases={JAX:'JAC',LA:'LAR',WSH:'WAS'};
 const canon=x=>aliases[String(x||'').toUpperCase()]||String(x||'').toUpperCase();
 const num=x=>x!==null&&x!==undefined&&x!==''&&Number.isFinite(Number(x))?Number(x):null;
 const ct=(x,opts)=>new Date(x).toLocaleString('en-US',{timeZone:'America/Chicago',...opts});
 const fmtCountdown=ms=>{if(ms<=0)return 'Kickoff now';const mins=Math.ceil(ms/60000),days=Math.floor(mins/1440),hours=Math.floor((mins%1440)/60),rest=mins%60;return days?days+'d '+hours+'h':hours?hours+'h '+rest+'m':rest+'m';};
 const logo=team=>'https://a.espncdn.com/i/teamlogos/nfl/500/'+encodeURIComponent(canon(team).toLowerCase())+'.png';
 let nextKickoff=null;
 function renderClock(){const el=$('fd-pulse-countdown');if(el&&nextKickoff)el.textContent=fmtCountdown(nextKickoff-Date.now());}
 async function refresh(){
  try{
   const [fr,qr]=await Promise.all([
    fetch('data/live-v2.json?t='+Date.now(),{cache:'no-store'}),
    fetch('data/dk-game-odds.json?t='+Date.now(),{cache:'no-store'})
   ]);
   if(!fr.ok||!qr.ok)throw Error('Feed unavailable');
   const [forecast,market]=await Promise.all([fr.json(),qr.json()]);
   const now=Date.now(),fAt=Date.parse(forecast.generated_at_utc),qAt=Date.parse(market.snapshot_date_utc);
   if(!Number.isFinite(fAt)||fAt>now+300000||now-fAt>36*3600000||!Number.isFinite(qAt)||qAt>now+300000||now-qAt>36*3600000)throw Error('Stale feed');
   const schedule=window.fdScheduleWindow?.get(new Date());
   if(!schedule)throw Error('Schedule unavailable');
   const games=(forecast.games||[]).filter(g=>window.fdScheduleWindow.contains(schedule,g.kickoff_utc)&&Number.isFinite(Date.parse(g.kickoff_utc)));
   const projected=games.filter(g=>num(g.projected_home_score)!==null&&num(g.projected_away_score)!==null);
   const quoteMap=new Map((market.games||[]).filter(q=>q.bookmaker==='draftkings'&&q.home&&q.away).map(q=>[canon(q.away)+'|'+canon(q.home),q]));
   const lineCount=games.filter(g=>{
    const q=quoteMap.get(canon(g.away)+'|'+canon(g.home)),kick=Date.parse(g.kickoff_utc);
    if(!q||Math.abs(Date.parse(q.commence_time)-kick)>3600000)return false;
    const updated=Date.parse(q.updated_at_utc||q.observed_at_utc||market.snapshot_date_utc);
    const hasLine=num(q.total)!==null||num(q.home_spread)!==null;
    return hasLine&&Number.isFinite(updated)&&updated<=now&&now-updated<=36*3600000&&updated<kick;
   }).length;
   const pct=games.length?Math.round(projected.length/games.length*100):0;
   const ring=$('fd-pulse-ring');ring.style.setProperty('--coverage',pct+'%');
   ring.setAttribute('aria-label',projected.length+' of '+games.length+' games have published score forecasts');
   $('fd-pulse-coverage').textContent=games.length?pct+'%':'—';
   $('fd-pulse-ready').textContent=projected.length+' / '+games.length;
   $('fd-pulse-games').textContent=String(games.length);
   $('fd-pulse-lines').textContent=String(lineCount);
   $('fd-pulse-week').textContent='NFL '+forecast.season+' · WEEK '+forecast.week;
   const start=schedule.start,end=schedule.end;
   const dateLabel=x=>x&&String(x).length>=8?String(x).slice(4,6)+'/'+String(x).slice(6,8):'';
   $('fd-pulse-dates').textContent=dateLabel(start)+' – '+dateLabel(end)+' · CENTRAL TIME';
   const upcoming=games.filter(g=>Date.parse(g.kickoff_utc)>now).sort((a,b)=>Date.parse(a.kickoff_utc)-Date.parse(b.kickoff_utc));
   const card=$('fd-pulse-next');
   if(upcoming.length){
    const g=upcoming[0];nextKickoff=Date.parse(g.kickoff_utc);
    const when=ct(g.kickoff_utc,{weekday:'short',month:'short',day:'numeric',hour:'numeric',minute:'2-digit',timeZoneName:'short'});
    card.innerHTML='<div class="fd-pulse-next-kicker">NEXT KICKOFF <span id="fd-pulse-countdown">'+fmtCountdown(nextKickoff-now)+'</span></div><div class="fd-pulse-matchup"><div><img src="'+esc(logo(g.away))+'" alt="" loading="lazy"><strong>'+esc(canon(g.away))+'</strong></div><span>@</span><div><img src="'+esc(logo(g.home))+'" alt="" loading="lazy"><strong>'+esc(canon(g.home))+'</strong></div></div><div class="fd-pulse-kick-time">'+esc(when)+'</div><a href="#scoreboard">Open game center <span aria-hidden="true">↗</span></a>';
   }else{
    nextKickoff=null;
    card.innerHTML='<div class="fd-pulse-next-kicker">SLATE STATUS</div><strong class="fd-pulse-no-next">All scheduled games have kicked off.</strong><p>The scoreboard has the latest game status and results.</p><a href="#scoreboard">Open game center <span aria-hidden="true">↗</span></a>';
   }
   $('fd-pulse-updated').textContent='Forecast feed '+ct(fAt,{hour:'numeric',minute:'2-digit',timeZoneName:'short'})+' · DK lines checked '+ct(qAt,{hour:'numeric',minute:'2-digit',timeZoneName:'short'});
  }catch(e){
   nextKickoff=null;
   $('fd-pulse-ring').style.setProperty('--coverage','0%');
   $('fd-pulse-ring').setAttribute('aria-label','Current slate coverage unavailable');
   $('fd-pulse-coverage').textContent='—';$('fd-pulse-ready').textContent='—';$('fd-pulse-games').textContent='—';$('fd-pulse-lines').textContent='—';
   $('fd-pulse-week').textContent='SLATE FEED';
   $('fd-pulse-dates').textContent='CURRENT STATUS UNAVAILABLE';
   $('fd-pulse-next').innerHTML='<div class="fd-pulse-next-kicker">NEXT KICKOFF</div><strong class="fd-pulse-no-next">Waiting for fresh forecast and line feeds.</strong><a href="#scoreboard">Open game center <span aria-hidden="true">↗</span></a>';
   $('fd-pulse-updated').textContent='The slate overview will return when fresh matched feeds are available.';
  }
 }
 refresh();setInterval(refresh,60000);setInterval(renderClock,15000);
})();