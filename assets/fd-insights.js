/* Display-only views built from published snapshots and observed weekly grades. */
(()=>{
 const esc=x=>String(x??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
 const get=p=>fetch('data/'+p+'?t='+Date.now(),{cache:'no-store'}).then(r=>r.ok?r.json():null).catch(()=>null);
 const ct=x=>{const d=new Date(x);return Number.isFinite(d.getTime())?d.toLocaleString('en-US',{timeZone:'America/Chicago',month:'short',day:'numeric',hour:'numeric',minute:'2-digit',timeZoneName:'short'}):'Time unavailable';};
 const n=x=>x!==null&&x!==undefined&&x!==''&&Number.isFinite(Number(x));
 async function changes(){
  const root=document.getElementById('fd-whats-changed');if(!root)return;
  const [history,feed,players]=await Promise.all([get('projection-changes.json'),get('live-v2.json'),get('player-research.json')]);
  const games=new Map((feed?.games||[]).filter(g=>window.fdScheduleWindow?.contains(window.fdScheduleWindow.get(),g.kickoff_utc)).map(g=>[String(g.game_id),g]));
  const names=new Map((players?.players||[]).map(p=>[String(p.game_id)+'|'+String(p.player_id),p.player]));
  const rows=[];
  for(const [id,v] of Object.entries(history?.games||{})){const g=games.get(id);if(!g||!Array.isArray(v)||v.length<2)continue;const [a,b]=v.slice(-2);if(!n(a.home)||!n(a.away)||!n(b.home)||!n(b.away)||!n(Date.parse(b.at)))continue;if(Number(a.home)===Number(b.home)&&Number(a.away)===Number(b.away))continue;rows.push({at:b.at,title:g.away+' @ '+g.home,detail:'Projected score: '+g.away+' '+Number(a.away).toFixed(1)+' → '+Number(b.away).toFixed(1)+' · '+g.home+' '+Number(a.home).toFixed(1)+' → '+Number(b.home).toFixed(1)});}
  for(const [key,v] of Object.entries(history?.players||{})){const [id,pid,market]=key.split('|');if(!games.has(id)||!Array.isArray(v)||v.length<2)continue;const [a,b]=v.slice(-2);if(!n(a.value)||!n(b.value)||!n(Date.parse(b.at))||Number(a.value)===Number(b.value))continue;const name=names.get(id+'|'+pid);if(!name)continue;rows.push({at:b.at,title:name+' · '+market.replaceAll('_',' '),detail:'Projection: '+Number(a.value).toFixed(1)+' → '+Number(b.value).toFixed(1)});}
  rows.sort((a,b)=>Date.parse(b.at)-Date.parse(a.at));
  root.innerHTML='<span class="fd-insight-tag">Latest saved snapshots</span><h2>What changed?</h2><p class="fd-insight-note">Changes between the two latest saved forecasts for this slate. Reasons and injury changes are not recorded here.</p><div class="fd-insight-grid">'+(rows.length?rows.slice(0,6).map(x=>'<article class="fd-insight-item"><strong>'+esc(x.title)+'</strong><p>'+esc(x.detail)+'</p><small>'+esc(ct(x.at))+'</small></article>').join(''):'<p class="fd-insight-note">No changes found between the latest saved forecast snapshots for this slate.</p>')+'</div>';
 }
 async function weekly(){
  const root=document.getElementById('fd-weekly-report-card');if(!root)return;const data=await get('weekly-model-performance.json');
  const weeks=(data?.weekly_reports||[]).filter(x=>x.status==='graded_observed_only').sort((a,b)=>Number(b.season)-Number(a.season)||Number(b.week)-Number(a.week));
  if(!weeks.length){root.innerHTML='<h2>Weekly model report card</h2><p class="fd-insight-note">Waiting for graded, timestamped pregame forecasts and verified results.</p>';return;}
  const latest=weeks[0],prev=weeks[1];
  const card=(label,v,old,unit)=>{if(!v||!n(v.mae)||!n(v.samples)||Number(v.samples)<=0)return '<article class="fd-insight-item"><strong>'+esc(label)+'</strong><p>Not enough graded results yet</p></article>';let cmp='';if(old&&n(old.mae)&&n(old.samples)&&Number(old.samples)>0){const d=Number(v.mae)-Number(old.mae);cmp='Prior week: '+Number(old.mae).toFixed(1)+' '+unit+' · '+(Math.abs(d)<.05?'about the same':Math.abs(d).toFixed(1)+' '+unit+' '+(d<0?'lower':'higher'))+' error';}return '<article class="fd-insight-item"><strong>'+esc(label)+'</strong><p>Average error: '+Number(v.mae).toFixed(1)+' '+esc(unit)+'</p><small>'+esc(v.samples)+' graded forecasts'+(cmp?' · '+esc(cmp):'')+'</small></article>';};
  root.innerHTML='<span class="fd-insight-tag">Observed pregame forecasts</span><h2>Weekly model report card</h2><p class="fd-insight-note">'+esc(latest.season)+' Week '+esc(latest.week)+' · '+esc(latest.completed_games??0)+' completed games graded. Lower average error is better; samples may be incomplete. Winner-pick accuracy is not published in this weekly report.</p><div class="fd-insight-grid">'+card('Game margin',latest.game_metrics?.home_margin,prev?.game_metrics?.home_margin,'points')+card('Game total',latest.game_metrics?.total,prev?.game_metrics?.total,'points')+card('Passing yards',latest.player_metrics?.passing_yards,prev?.player_metrics?.passing_yards,'yards')+card('Rushing yards',latest.player_metrics?.rushing_yards,prev?.player_metrics?.rushing_yards,'yards')+card('Receiving yards',latest.player_metrics?.receiving_yards,prev?.player_metrics?.receiving_yards,'yards')+'</div><p class="fd-insight-note">Each week uses its own graded sample, so changes can reflect different games and coverage. Updated '+esc(ct(data.generated_at_utc))+'.</p>';
 }
 changes();weekly();
})();
