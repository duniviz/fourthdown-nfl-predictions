(function(root,factory){if(typeof module==='object'&&module.exports)module.exports=factory();else{root.FDGamePreview=factory();root.FDGamePreview.start();}})(typeof globalThis!=='undefined'?globalThis:this,function(){
'use strict';
const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const finite=v=>v!==null&&v!==undefined&&v!==''&&Number.isFinite(Number(v));
const num=v=>finite(v)?Number(v).toFixed(1):'—';
const canon=v=>({JAC:'JAX',LAR:'LA',WAS:'WSH'}[String(v||'').toUpperCase()]||String(v||'').toUpperCase());
const time=v=>{if(!v)return 'Unavailable';const d=new Date(v);return Number.isFinite(d.getTime())?d.toLocaleString('en-US',{timeZone:'America/Chicago',dateStyle:'medium',timeStyle:'short'})+' CT':'Unavailable'};
const signed=v=>Number(v)>0?'+'+num(v):num(v);
const names={ARI:'Cardinals',ATL:'Falcons',BAL:'Ravens',BUF:'Bills',CAR:'Panthers',CHI:'Bears',CIN:'Bengals',CLE:'Browns',DAL:'Cowboys',DEN:'Broncos',DET:'Lions',GB:'Packers',HOU:'Texans',IND:'Colts',JAX:'Jaguars',KC:'Chiefs',LA:'Rams',LAC:'Chargers',LV:'Raiders',MIA:'Dolphins',MIN:'Vikings',NE:'Patriots',NO:'Saints',NYG:'Giants',NYJ:'Jets',PHI:'Eagles',PIT:'Steelers',SEA:'Seahawks',SF:'49ers',TB:'Buccaneers',TEN:'Titans',WSH:'Commanders'};
const teamName=team=>names[canon(team)]||String(team||'Team');
function overview(p){
 const away=teamName(p.away),home=teamName(p.home),ap=p.projected_away_score,hp=p.projected_home_score;
 const paragraphs=[];
 if(finite(ap)&&finite(hp)){
  const diff=Math.abs(Number(hp)-Number(ap));
  if(diff<.05)paragraphs.push('FOURTHDOWN sees this one as a toss-up, with both teams projected for '+num(hp)+' points.');
  else {const winner=Number(hp)>Number(ap)?home:away,loser=Number(hp)>Number(ap)?away:home;
   paragraphs.push('The '+winner+' get the nod in FOURTHDOWN’s forecast, '+num(Math.max(Number(hp),Number(ap)))+'–'+num(Math.min(Number(hp),Number(ap)))+' over the '+loser+'. '+(diff<=3?'It’s a close one on paper.':diff>=10?'The model sees a sizable gap between the teams.':'The model gives them a '+num(diff)+'-point edge.'));}
 }
 const points=(p.analysis?.matchup_metrics||[]).find(m=>m.label==='Points / game');
 const sides=[{off:home,def:away,offense:points?.home_offense,defense:points?.away_defense}, {off:away,def:home,offense:points?.away_offense,defense:points?.home_defense}].filter(x=>finite(x.offense?.value)&&finite(x.defense?.value));
 if(sides.length){
  // Highlight the defense with the strongest available points-allowed ranking.
  sides.sort((a,b)=>(finite(a.defense.rank)?Number(a.defense.rank):999)-(finite(b.defense.rank)?Number(b.defense.rank):999));
  const s=sides[0];paragraphs.push('One matchup to watch: the '+s.off+' are averaging '+num(s.offense.value)+' points per game, while the '+s.def+' are allowing '+num(s.defense.value)+'.');
 }
 const redzone=(p.analysis?.matchup_metrics||[]).find(m=>m.label==='Red-zone TD rate');
 const matchups=[{off:home,def:away,offense:redzone?.home_offense,defense:redzone?.away_defense},{off:away,def:home,offense:redzone?.away_offense,defense:redzone?.home_defense}].filter(x=>finite(x.offense?.rank)&&finite(x.defense?.rank)&&Number(x.offense.rank)<=8&&Number(x.defense.rank)<=8&&finite(x.offense.value)&&finite(x.defense.value));
 if(matchups.length){const m=matchups.sort((a,b)=>Number(a.offense.rank)+Number(a.defense.rank)-Number(b.offense.rank)-Number(b.defense.rank))[0];paragraphs.push('Keep an eye on the red zone: the '+m.off+' have scored touchdowns on '+num(m.offense.value)+'% of their red-zone drives, while the '+m.def+' have allowed touchdowns on '+num(m.defense.value)+'% of opponents’ trips.');}
 const a=p.analysis?.away?.recent_form,h=p.analysis?.home?.recent_form;
 if(finite(a?.games)&&finite(a?.wins)&&finite(h?.games)&&finite(h?.wins)&&Number(a.games)>0&&Number(h.games)>0){
  paragraphs.push('Lately, the '+away+' have won '+Number(a.wins)+' of their last '+Number(a.games)+' games; the '+home+' have won '+Number(h.wins)+' of their last '+Number(h.games)+'.');
 }
 return paragraphs;
}
function render(id,data,now=Date.now()){
 const p=(data.live?.games||[]).find(g=>g.game_id===id);
 if(!p)return '<div class="card"><h1>Preview unavailable</h1><p>This matchup is not in the current forecast feed.</p><a href="index.html">Back to games</a></div>';
 const kick=Date.parse(p.kickoff_utc),fresh=Number.isFinite(kick)&&now<kick;
 if(!fresh)return '<div class="card"><h1>Pregame preview unavailable</h1><p>This game has started. Open its matchup on the site for the latest game information.</p><a href="index.html">Back to games</a></div>';
 const home=esc(p.home),away=esc(p.away),ha=p.analysis?.home||{},aa=p.analysis?.away||{};
 const editor=data.editorial?.games?.[id];
 const edtime=Date.parse(editor?.generated_at_utc),edkick=Date.parse(editor?.kickoff_utc);
 const safeEditor=editor&&Number.isFinite(edtime)&&edtime<kick&&Number.isFinite(edkick)&&Math.abs(edkick-kick)<3600000;
 let html='<div class="eyebrow">FOURTHDOWN · PREGAME PREVIEW</div><h1>'+away+' <span class="muted">at</span> '+home+'</h1><p class="muted">'+esc(time(p.kickoff_utc))+' · Forecast updated '+esc(time(data.live?.generated_at_utc))+'</p>';
 const summary=overview(p);if(summary.length)html+='<section class="card"><h2>The matchup</h2>'+summary.map(s=>'<p>'+esc(s)+'</p>').join('')+'</section>';
 html+='<section class="card"><h2>Model projection</h2><div class="scores"><div class="score">'+away+'<strong>'+num(p.projected_away_score)+'</strong></div><div class="score">'+home+'<strong>'+num(p.projected_home_score)+'</strong></div></div><p>Projected total: <b>'+num(p.projected_total)+'</b> · Projected margin: <b>'+home+' '+signed(p.projected_margin_home)+'</b></p><p class="muted">Research forecast; scores are estimates, not guaranteed outcomes.</p></section>';
 const ml=p.game_ml_shadow?.markets||{}, mm=ml.game_margin_home?.candidate, mt=ml.game_total?.candidate;
 if(finite(mm)&&finite(mt)&&Number(mt)>=Math.abs(Number(mm))){html+='<section class="card"><h2>ML research estimate</h2><div class="scores"><div class="score">'+away+'<strong>'+num((Number(mt)-Number(mm))/2)+'</strong></div><div class="score">'+home+'<strong>'+num((Number(mt)+Number(mm))/2)+'</strong></div></div><p>Projected total: <b>'+num(mt)+'</b></p><p class="muted">This research estimate may differ from the ML model selected for the game card.</p></section>';}
 const external=editor?.external_context, extKick=Date.parse(external?.kickoff_utc||'');
 if(Number.isFinite(extKick)&&Math.abs(extKick-kick)<=900000){
  const ep=external.predictor,at=Date.parse(ep?.retrieved_at_utc||'');
  const safeUrl=url=>{try{const u=new URL(url);return u.protocol==='https:'&&u.hostname==='www.espn.com'}catch(e){return false}};
  if(ep?.source==='ESPN Matchup Predictor'&&finite(ep.home_pct)&&finite(ep.away_pct)&&Number(ep.home_pct)>=0&&Number(ep.home_pct)<=100&&Number(ep.away_pct)>=0&&Number(ep.away_pct)<=100&&Math.abs(Number(ep.home_pct)+Number(ep.away_pct)-100)<=2&&Number.isFinite(at)&&at<=now&&at<kick&&safeUrl(ep.url)){
   html+='<section class="card"><h2>ESPN’s matchup predictor</h2><div class="scores"><div class="score">'+away+'<strong>'+num(ep.away_pct)+'%</strong></div><div class="score">'+home+'<strong>'+num(ep.home_pct)+'%</strong></div></div><p class="muted">ESPN’s estimate of each team’s chance to win · retrieved '+esc(time(ep.retrieved_at_utc))+' · <a href="'+esc(ep.url)+'" target="_blank" rel="noopener noreferrer">View source</a></p></section>';
  }
  const article=external.article, published=Date.parse(article?.published_at_utc||''),modified=Date.parse(article?.updated_at_utc||'');
  if(article&&typeof article.excerpt==='string'&&article.excerpt.trim().split(/\s+/).length<=20&&Number.isFinite(published)&&Number.isFinite(modified)&&published<=now&&modified<=now&&modified<kick&&safeUrl(article.url)){
   html+='<section class="card"><h2>From the game preview</h2><p>“'+esc(article.excerpt)+'”</p><p class="muted">'+esc(article.source||'ESPN')+' · updated '+esc(time(article.updated_at_utc))+' · <a href="'+esc(article.url)+'" target="_blank" rel="noopener noreferrer">Read the preview</a></p></section>';
  }
 }
 const odds=(data.odds?.games||[]).find(o=>canon(o.home)===canon(p.home)&&canon(o.away)===canon(p.away)&&Math.abs(Date.parse(o.commence_time)-kick)<=15*60000&&Date.parse(o.observed_at_utc)<kick&&Date.parse(o.observed_at_utc)<=now);
 if(odds){html+='<section class="card"><h2>DraftKings lines</h2><div class="cols"><div>Spread<br><strong>'+home+' '+(finite(odds.home_spread)?(Number(odds.home_spread)===0?'PK':signed(odds.home_spread)):'Unavailable')+'</strong></div><div>Total<br><strong>'+(finite(odds.total)?num(odds.total):'Unavailable')+'</strong></div></div><p class="muted">Observed '+esc(time(odds.observed_at_utc))+' · Lines can change; verify before use.</p></section>';}
 const rank=v=>finite(v)?'#'+esc(v):'—';
 html+='<section class="card"><h2>Team comparison</h2><p class="muted">Model efficiency ranks and the last five completed games</p><table class="stats"><thead><tr><th>Metric</th><th>'+away+'</th><th>'+home+'</th></tr></thead><tbody><tr><td>Offensive rank</td><td>'+rank(aa.offense_rank)+'</td><td>'+rank(ha.offense_rank)+'</td></tr><tr><td>Defensive rank</td><td>'+rank(aa.defense_rank)+'</td><td>'+rank(ha.defense_rank)+'</td></tr><tr><td>Recent points scored / game</td><td>'+num(aa.recent_form?.avg_points_for)+'</td><td>'+num(ha.recent_form?.avg_points_for)+'</td></tr><tr><td>Recent points allowed / game</td><td>'+num(aa.recent_form?.avg_points_against)+'</td><td>'+num(ha.recent_form?.avg_points_against)+'</td></tr></tbody></table></section>';
 const metrics=p.analysis?.matchup_metrics||[];
 if(metrics.length)html+='<section class="card"><h2>Matchups to watch</h2><p class="muted">Offense versus opposing defense; ranks and values reflect prior completed games.</p>'+metrics.filter(m=>['Points / game','EPA / pass','EPA / rush','3rd down conversion'].includes(m.label)).map(m=>'<div class="story"><h3>'+esc(m.label)+'</h3><p>'+away+' offense '+esc(m.away_offense?.value??'—')+' vs '+home+' defense '+esc(m.home_defense?.value??'—')+' · '+home+' offense '+esc(m.home_offense?.value??'—')+' vs '+away+' defense '+esc(m.away_defense?.value??'—')+' <span class="muted">'+esc(m.unit||'')+'</span></p></div>').join('')+'</section>';
 let inj=data.injuries;html+='<section class="card"><h2>Injury report</h2><p class="muted">ESPN team reports · updated '+esc(time(inj?.generated_at_utc))+' · Check official inactives near kickoff.</p><div class="cols">'+[p.away,p.home].map(team=>{let info=inj?.teams?.[team];let players=(info?.players||[]).filter(x=>/^(out|doubtful|questionable)$/i.test(x.status||''));return '<div><h3>'+esc(team)+'</h3>'+(info?.status!=='retrieved'?'<p>Report unavailable.</p>':players.length?'<ul>'+players.map(x=>'<li>'+esc(x.player)+' · '+esc(x.position||'')+' · '+esc(x.status)+'</li>').join('')+'</ul>':'<p>No out, doubtful, or questionable players listed in this feed.</p>')+'</div>'}).join('')+'</div></section>';
 if(safeEditor){let stories=/free evidence-based model commentary/i.test(editor.source||'')?[]:(editor.stories||[]).filter(s=>s&&typeof s.body==='string'&&Array.isArray(s.evidence_keys)&&s.evidence_keys.length);let news=(editor.news||[]).filter(n=>{try{const u=new URL(n.url);const published=Date.parse(n.published_at_utc);return u.protocol==='https:'&&['www.espn.com','news.google.com'].includes(u.hostname)&&Number.isFinite(published)&&published<=now&&now-published<=7*86400000}catch(e){return false}});if(stories.length||news.length){html+='<section class="card"><h2>More on this game</h2>'+(stories.length?'<p class="muted">'+esc(editor.source||'FOURTHDOWN preview')+' · written '+esc(time(editor.generated_at_utc))+'; numbers may have changed since then.</p>':'')+stories.map(s=>'<article class="story"><h3>'+esc(s.title)+'</h3><p>'+esc(s.body)+'</p></article>').join('')+(news.length?'<h3>Matchup headlines</h3><ul>'+news.slice(0,4).map(n=>'<li><a href="'+esc(n.url)+'" target="_blank" rel="noopener noreferrer">'+esc(n.title)+'</a> <small class="muted"> · '+esc(n.publisher||'News')+' · '+esc(time(n.published_at_utc))+'</small></li>').join('')+'</ul>':'')+'</section>';}}
 return html+'<footer>Preview uses available FOURTHDOWN feeds. Injuries and lines can change; missing information is left out. <a href="index.html">Back to games</a></footer>';
}
async function start(){const id=new URLSearchParams(location.search).get('game')||'';const paths=['live-v2','ai-game-previews','dk-game-odds','injuries'];const values=await Promise.all(paths.map(p=>fetch('data/'+p+'.json?ts='+Date.now(),{cache:'no-store'}).then(r=>r.ok?r.json():null).catch(()=>null)));document.getElementById('preview').innerHTML=render(id,{live:values[0],editorial:values[1],odds:values[2],injuries:values[3]});}
return {render,start,overview};
});

