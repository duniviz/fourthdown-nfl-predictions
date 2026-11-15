/* Display-only views built from published snapshots and observed weekly grades. */
(()=>{
 const esc=x=>String(x??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
 const get=p=>fetch('data/'+p+'?t='+Date.now(),{cache:'no-store'}).then(r=>r.ok?r.json():null).catch(()=>null);
 const ct=x=>{const d=new Date(x);return Number.isFinite(d.getTime())?d.toLocaleString('en-US',{timeZone:'America/Chicago',month:'short',day:'numeric',hour:'numeric',minute:'2-digit',timeZoneName:'short'}):'Time unavailable';};
 const n=x=>x!==null&&x!==undefined&&x!==''&&Number.isFinite(Number(x));
 const moved=(a,b,min)=>n(a)&&n(b)&&Math.abs(Number(a)-Number(b))>=min;
 async function weekly(){
  const root=document.getElementById('fd-weekly-report-card');if(!root)return;const data=await get('weekly-model-performance.json');
  const weeks=(data?.weekly_reports||[]).filter(x=>x.status==='graded_observed_only').sort((a,b)=>Number(b.season)-Number(a.season)||Number(b.week)-Number(a.week));
  if(!weeks.length){root.innerHTML='<h2>Weekly model report card</h2><p class="fd-insight-note">Waiting for graded, timestamped pregame forecasts and verified results.</p>';return;}
  const latest=weeks[0],prev=weeks[1];
  const card=(label,v,old,unit)=>{if(!v||!n(v.mae)||!n(v.samples)||Number(v.samples)<=0)return '<article class="fd-insight-item"><strong>'+esc(label)+'</strong><p>Not enough graded results yet</p></article>';let cmp='';if(old&&n(old.mae)&&n(old.samples)&&Number(old.samples)>0){const d=Number(v.mae)-Number(old.mae);cmp='Prior week: '+Number(old.mae).toFixed(1)+' '+unit+' · '+(Math.abs(d)<.05?'about the same':Math.abs(d).toFixed(1)+' '+unit+' '+(d<0?'lower':'higher'))+' error';}return '<article class="fd-insight-item"><strong>'+esc(label)+'</strong><p>Average error: '+Number(v.mae).toFixed(1)+' '+esc(unit)+'</p><small>'+esc(v.samples)+' graded forecasts'+(cmp?' · '+esc(cmp):'')+'</small></article>';};
  root.innerHTML='<span class="fd-insight-tag">Observed pregame forecasts</span><h2>Weekly model report card</h2><p class="fd-insight-note">'+esc(latest.season)+' Week '+esc(latest.week)+' · '+esc(latest.completed_games??0)+' completed games graded. Lower average error is better; samples may be incomplete. Winner-pick accuracy is not published in this weekly report.</p><div class="fd-insight-grid">'+card('Game margin',latest.game_metrics?.home_margin,prev?.game_metrics?.home_margin,'points')+card('Game total',latest.game_metrics?.total,prev?.game_metrics?.total,'points')+card('Passing yards',latest.player_metrics?.passing_yards,prev?.player_metrics?.passing_yards,'yards')+card('Rushing yards',latest.player_metrics?.rushing_yards,prev?.player_metrics?.rushing_yards,'yards')+card('Receiving yards',latest.player_metrics?.receiving_yards,prev?.player_metrics?.receiving_yards,'yards')+'</div><p class="fd-insight-note">Each week uses its own graded sample, so changes can reflect different games and coverage. Updated '+esc(ct(data.generated_at_utc))+'.</p>';
 }
 weekly();
})();
