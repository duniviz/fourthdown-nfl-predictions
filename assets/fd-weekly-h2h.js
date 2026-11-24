(function(){
 'use strict';
 const root=document.getElementById('fd-weekly-h2h');if(!root)return;
 const esc=x=>String(x??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
 const num=x=>Number(x).toFixed(1);
 const grade=x=>({hit:'Hit',miss:'Miss',push:'Push',no_pick:'No pick',unavailable:'No saved line'}[x]||'No saved line');
 const hitCell=(label,x)=>{if(!x)return '<div><span>'+label+'</span><b>—</b><small>Awaiting grading</small></div>';const pct=x.hit_pct==null?'—':num(x.hit_pct)+'%';return '<div><span>'+label+'</span><b>'+pct+'</b><small>'+esc(x.hits)+'–'+esc(x.misses)+' · '+esc(x.pushes)+' push'+(x.no_picks?' · '+esc(x.no_picks)+' no pick':'')+'</small></div>';};
 function render(weeks,index,shadowWeeks){
  const week=weeks[index];
  const options=weeks.map((w,i)=>'<option value="'+i+'"'+(i===index?' selected':'')+'>'+esc(w.season)+' · Week '+esc(w.week)+'</option>').join('');
  const cards=(week.markets||[]).map(m=>{
   const winner=m.winner==='ml'?'ML was closer':m.winner==='regular'?'Regular was closer':'About even';
   const details=(m.details||[]).map(d=>'<tr><td>'+esc(d.label)+'</td><td>'+num(d.actual)+'</td><td>'+((d.dk_line==null)?'—':num(d.dk_line))+'</td><td>'+num(d.regular)+' · '+grade(d.regular_pick_result)+'</td><td>'+num(d.ml)+' · '+grade(d.ml_pick_result)+'</td></tr>').join('');
   return '<article class="fd-h2h-card"><div class="fd-h2h-heading"><h3>'+esc(m.market==='game_margin_home'?'Against the spread':m.label)+'</h3><strong>'+winner+'</strong></div><p>Hit rate against saved DraftKings line</p><div class="fd-h2h-values">'+hitCell('Regular',m.regular_hits)+hitCell('ML',m.ml_hits)+'</div><p>'+esc(m.regular_hits?.unavailable??m.samples)+' matched projections missing a usable saved line</p><div class="fd-h2h-values"><div><span>Regular avg. miss</span><b>'+num(m.regular_mae)+'</b></div><div><span>ML avg. miss</span><b>'+num(m.ml_mae)+'</b></div></div><p>'+esc(m.samples)+' matched result'+(m.samples===1?'':'s')+' · Regular closer '+esc(m.regular_wins)+' · ML closer '+esc(m.ml_wins)+' · Ties '+esc(m.ties)+'</p><details><summary>See individual results</summary><div class="fd-h2h-scroll"><table><thead><tr><th>Game or player</th><th>Actual</th><th>DK line</th><th>Regular · result</th><th>ML · result</th></tr></thead><tbody>'+details+'</tbody></table></div></details></article>';
  }).join('');
  const shadowWeek=(shadowWeeks||[]).find(w=>w.season===week.season&&w.week===week.week);
  const shadows=(shadowWeek?.markets||[]).map(m=>'<article class="fd-h2h-card"><div class="fd-h2h-heading"><h3>'+esc(m.market==='game_margin_home'?'Game margin':'Game total')+' · Saved ML shadow</h3></div><div class="fd-h2h-values"><div><span>Regular avg. miss</span><b>'+num(m.regular_mae)+'</b></div><div><span>ML shadow avg. miss</span><b>'+num(m.shadow_mae)+'</b></div></div><p>'+esc(m.samples)+' saved game locks · Includes early locks</p><details><summary>See individual results</summary><div class="fd-h2h-scroll"><table><thead><tr><th>Game</th><th>Actual</th><th>Regular</th><th>ML shadow</th></tr></thead><tbody>'+(m.details||[]).map(d=>'<tr><td>'+esc(d.game_id)+'</td><td>'+num(d.actual)+'</td><td>'+num(d.regular)+'</td><td>'+num(d.shadow)+'</td></tr>').join('')+'</tbody></table></div></details></article>').join('');
  root.innerHTML='<div class="fd-h2h-top"><div><span class="fd-h2h-kicker">SAVED PREGAME FORECASTS</span><h2>Regular vs ML results</h2></div><label>Week <select id="fd-h2h-week">'+options+'</select></label></div><p class="fd-h2h-intro">Hit rate is hits ÷ (hits + misses) against the saved pregame line. Pushes and projections exactly on the line do not count. Every eligible line is graded, including small edges; odds and profit are not included. Spread lines are shown from the home team’s perspective.</p><p class="fd-h2h-intro">Average miss measures how close the projection was to the final result. Lower is better. Game margin is home score minus away score.</p><div class="fd-h2h-grid">'+(cards||'<p>Waiting for matched, finalized results.</p>')+'</div>'+(shadows?'<h3>Saved game-lock ML shadows</h3><p class="fd-h2h-intro">These estimates were saved with the game forecast. They may differ from the selected ML card model.</p><div class="fd-h2h-grid">'+shadows+'</div>':'')+'<p class="fd-h2h-intro">Only verified saved pairs are included. Player results appear after final stats are graded; early weeks may be incomplete.</p>';
  root.querySelector('#fd-h2h-week').addEventListener('change',e=>render(weeks,Number(e.target.value),shadowWeeks));
 }
 fetch('data/weekly-card-comparison.json?t='+Date.now(),{cache:'no-store'}).then(r=>r.ok?r.json():null).then(d=>{
  if(!d||!Array.isArray(d.weeks)||!d.weeks.length){root.innerHTML='<h2>Regular vs ML: who was closer?</h2><p>Waiting for matching saved forecasts and final results.</p>';return;}
  render(d.weeks,0,d.game_shadow_comparisons);
 }).catch(()=>{root.innerHTML='<h2>Regular vs ML: who was closer?</h2><p>Results are temporarily unavailable.</p>';});
})();

