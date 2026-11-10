/* Display saved pregame spread and total snapshots for this matchup only. */
(function(root,factory){const api=factory();if(typeof module==='object'&&module.exports)module.exports=api;root.FDMarketHistory=api;})(typeof globalThis!=='undefined'?globalThis:this,function(){
 const esc=x=>String(x??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
 const canon=x=>({WSH:'WAS',JAX:'JAC',LA:'LAR'}[String(x||'').toUpperCase()]||String(x||'').toUpperCase());
 const num=x=>x!==null&&x!==undefined&&x!==''&&Number.isFinite(Number(x));
 const time=x=>{const d=new Date(x);return Number.isFinite(d.getTime())?d.toLocaleString('en-US',{timeZone:'America/Chicago',month:'short',day:'numeric',hour:'numeric',minute:'2-digit',timeZoneName:'short'}):'Time unavailable';};
 const signed=x=>Number(x)===0?'PK':(Number(x)>0?'+':'')+Number(x).toFixed(1);
 function collect(game,history,opening,current,observedAt,now){
  const kick=Date.parse(game?.date),away=canon(game?.away?.abbr),home=canon(game?.home?.abbr);if(!Number.isFinite(kick)||!away||!home)return [];
  const rows=[];
  for(const [key,arr] of Object.entries(history||{})){const [a,h,t]=key.split('|');if(canon(a)===away&&canon(h)===home&&Date.parse(t)===kick&&Array.isArray(arr))rows.push(...arr);}
  for(const q of Object.values(opening||{})){if(canon(q.away)===away&&canon(q.home)===home&&Date.parse(q.commence_time)===kick&&q.bookmaker==='draftkings')rows.push({...q,captured_at_utc:q.opening_captured_at_utc});}
  if(Number.isFinite(observedAt))for(const q of Object.values(current||{})){if(canon(q.away)===away&&canon(q.home)===home&&Date.parse(q.commence_time)===kick&&q.bookmaker==='draftkings')rows.push({...q,captured_at_utc:new Date(observedAt).toISOString()});}
  const limit=now??Date.now(),out=[];
  for(const row of rows){const captured=Date.parse(row.captured_at_utc);if(!Number.isFinite(captured)||captured>=kick||captured>limit)continue;
   const valid=field=>{const verified=Date.parse(row[field+'_last_verified_at_utc']||row.updated_at_utc||row.captured_at_utc);return num(row[field])&&Number.isFinite(verified)&&verified<=captured&&verified<kick;};
   const spread=valid('home_spread')?Number(row.home_spread):null,total=valid('total')?Number(row.total):null;
   if(spread!==null||total!==null)out.push({captured_at_utc:row.captured_at_utc,spread,total});
  }
  return out.sort((a,b)=>Date.parse(a.captured_at_utc)-Date.parse(b.captured_at_utc)).filter((x,i,a)=>!i||Date.parse(x.captured_at_utc)!==Date.parse(a[i-1].captured_at_utc)||x.spread!==a[i-1].spread||x.total!==a[i-1].total);
 }
 function render(game,history,opening,current,observedAt,now){
  const records=collect(game,history,opening,current,observedAt,now),home=game?.home?.abbr||'',away=game?.away?.abbr||'';
  const summary=(field,label,format)=>{const xs=records.filter(x=>x[field]!==null);if(!xs.length)return '<div class="fd-history-team"><h4>'+esc(label)+'</h4><p>No saved pregame snapshots available.</p></div>';const first=xs[0],last=xs[xs.length-1];return '<div class="fd-history-team"><h4>'+esc(label)+'</h4><p>First saved: <strong>'+esc(format(first[field]))+'</strong> · '+esc(time(first.captured_at_utc))+'</p><p>Latest saved: <strong>'+esc(format(last[field]))+'</strong> · '+esc(time(last.captured_at_utc))+'</p>'+(xs.length===1?'<small>One snapshot saved; movement is not yet available.</small>':'')+'</div>';};
  const a=summary('spread','Spread · '+away,x=>signed(-x)),h=summary('spread','Spread · '+home,signed),total=summary('total','Game total',x=>Number(x).toFixed(1));
  const entries=records.slice(-12).reverse().map(q=>'<div class="fd-market-history-game"><strong>'+esc(time(q.captured_at_utc))+'</strong><span>'+(q.spread===null?'Spread unavailable':esc(away)+' '+esc(signed(-q.spread))+' · '+esc(home)+' '+esc(signed(q.spread)))+' · '+(q.total===null?'Total unavailable':'O/U '+q.total.toFixed(1))+'</span></div>').join('');
  return '<details class="fd-market-history"><summary>ATS &amp; O/U line movement</summary><p class="fd-insight-note">Saved pregame DraftKings snapshots for this game only, in Central Time. First saved may not be the actual opening line; latest saved may not be the closing line.</p><div class="fd-market-history-grid">'+a+h+total+'</div>'+(entries?'<div class="fd-history-team"><h4>Recent saved snapshots</h4>'+entries+'</div>':'<p class="fd-insight-note">Waiting for the first saved line for this matchup.</p>')+'</details>';
 }
 return {collect,render};
});
