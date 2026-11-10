/* Recent actual results against saved pregame DraftKings game lines. */
(function(root,factory){const api=factory();if(typeof module==='object'&&module.exports)module.exports=api;root.FDMarketHistory=api;})(typeof globalThis!=='undefined'?globalThis:this,function(){
 const esc=x=>String(x??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
 const canon=x=>({WSH:'WAS',JAX:'JAC',LA:'LAR'}[String(x||'').toUpperCase()]||String(x||'').toUpperCase());
 const num=x=>x!==null&&x!==undefined&&x!==''&&Number.isFinite(Number(x));
 const result=x=>Math.abs(x)<1e-8?'Push':x>0?'Cover':'No cover';
 function prepare(rows,team,cutoff){return (Array.isArray(rows)?rows:[]).filter(r=>{
  const kick=Date.parse(r.kickoff_utc),quote=Date.parse(r.dk_at_utc);
  return (canon(r.home)===team||canon(r.away)===team)&&Number.isFinite(kick)&&kick<cutoff&&Number.isFinite(quote)&&quote<kick&&num(r.home_score)&&num(r.away_score)&&(num(r.dk_home_spread)||num(r.dk_total));
 }).sort((a,b)=>Date.parse(b.kickoff_utc)-Date.parse(a.kickoff_utc));}
 function line(r,team){
  const home=canon(r.home),away=canon(r.away),score=Number(r.home_score)-Number(r.away_score),total=Number(r.home_score)+Number(r.away_score);
  const homeCover=num(r.dk_home_spread)?score+Number(r.dk_home_spread):null;
  const ats=homeCover===null?'ATS unavailable':result(home===team?homeCover:-homeCover);
  const ou=!num(r.dk_total)?'O/U unavailable':total===Number(r.dk_total)?'Push':total>Number(r.dk_total)?'Over':'Under';
  const spread=num(r.dk_home_spread)?' · '+esc(home)+' spread '+(Number(r.dk_home_spread)>0?'+':'')+Number(r.dk_home_spread).toFixed(1):'';
  const totalText=num(r.dk_total)?' · total '+Number(r.dk_total).toFixed(1):'';
  return '<div class="fd-market-history-game"><strong>'+esc(away)+' '+Number(r.away_score)+' · '+esc(home)+' '+Number(r.home_score)+'</strong><span>'+esc(ats)+' ATS · '+esc(ou)+spread+totalText+'</span><small>'+esc(new Date(r.kickoff_utc).toLocaleDateString('en-US',{timeZone:'America/Chicago',month:'short',day:'numeric',year:'numeric'}))+' CT · saved pregame DK line</small></div>';
 }
 function summary(rows,team){
  let cover=0,fail=0,push=0,over=0,under=0,opush=0;
  for(const r of rows){const margin=Number(r.home_score)-Number(r.away_score);if(num(r.dk_home_spread)){const v=(margin+Number(r.dk_home_spread))*(canon(r.home)===team?1:-1);if(Math.abs(v)<1e-8)push++;else if(v>0)cover++;else fail++;}if(num(r.dk_total)){const d=Number(r.home_score)+Number(r.away_score)-Number(r.dk_total);if(Math.abs(d)<1e-8)opush++;else if(d>0)over++;else under++;}}
  return (cover+fail+push?'ATS '+cover+'–'+fail+'–'+push:'ATS unavailable')+' · '+(over+under+opush?'O/U '+over+'–'+under+'–'+opush:'O/U unavailable');
 }
 function render(game,history,now){
  if(!game?.home?.abbr||!game?.away?.abbr)return '';
  const cutoff=Math.min(Date.parse(game.date)||Infinity,now??Date.now()),away=canon(game.away.abbr),home=canon(game.home.abbr);
  const a=prepare(history,away,cutoff).slice(0,5),h=prepare(history,home,cutoff).slice(0,5);
  const meetings=prepare(history,away,cutoff).filter(r=>canon(r.home)===home||canon(r.away)===home).slice(0,5);
  const block=(label,rows,team)=>'<div class="fd-history-team"><h4>'+esc(label)+'</h4>'+(rows.length?'<p>'+esc(summary(rows,team))+' · '+rows.length+' saved games</p>'+rows.map(r=>line(r,team)).join(''):'<p>No verified saved game lines and scores available.</p>')+'</div>';
  return '<details class="fd-market-history"><summary>ATS &amp; over/under history</summary><p class="fd-insight-note">Last 5 available archived games, not necessarily the last 5 played. ATS is from each team’s perspective. Lines are saved pregame snapshots, not necessarily closing lines.</p><div class="fd-market-history-grid">'+block(game.away.abbr+' recent',a,away)+block(game.home.abbr+' recent',h,home)+'</div><div>'+block('Previous meetings · '+game.away.abbr+' ATS',meetings,away)+'</div></details>';
 }
 return {prepare,summary,render};
});
