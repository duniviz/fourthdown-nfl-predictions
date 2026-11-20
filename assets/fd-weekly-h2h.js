(function(){
 'use strict';
 const root=document.getElementById('fd-weekly-h2h');if(!root)return;
 const esc=x=>String(x??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
 const num=x=>Number(x).toFixed(1);
 function render(weeks,index){
  const week=weeks[index];
  const options=weeks.map((w,i)=>'<option value="'+i+'"'+(i===index?' selected':'')+'>'+esc(w.season)+' · Week '+esc(w.week)+'</option>').join('');
  const cards=(week.markets||[]).map(m=>{
   const winner=m.winner==='ml'?'ML was closer':m.winner==='regular'?'Regular was closer':'About even';
   const details=(m.details||[]).map(d=>'<tr><td>'+esc(d.label)+'</td><td>'+num(d.actual)+'</td><td>'+num(d.regular)+'</td><td>'+num(d.ml)+'</td><td>'+esc(d.winner==='ml'?'ML':d.winner==='regular'?'Regular':'Tie')+'</td></tr>').join('');
   return '<article class="fd-h2h-card"><div class="fd-h2h-heading"><h3>'+esc(m.label)+'</h3><strong>'+winner+'</strong></div><div class="fd-h2h-values"><div><span>Regular avg. miss</span><b>'+num(m.regular_mae)+'</b></div><div><span>ML avg. miss</span><b>'+num(m.ml_mae)+'</b></div></div><p>'+esc(m.samples)+' matched result'+(m.samples===1?'':'s')+' · Regular closer '+esc(m.regular_wins)+' · ML closer '+esc(m.ml_wins)+' · Ties '+esc(m.ties)+'</p><details><summary>See individual results</summary><div class="fd-h2h-scroll"><table><thead><tr><th>Game or player</th><th>Actual</th><th>Regular</th><th>ML</th><th>Closer</th></tr></thead><tbody>'+details+'</tbody></table></div></details></article>';
  }).join('');
  root.innerHTML='<div class="fd-h2h-top"><div><span class="fd-h2h-kicker">SAVED PREGAME FORECASTS</span><h2>Regular vs ML: who was closer?</h2></div><label>Week <select id="fd-h2h-week">'+options+'</select></label></div><p class="fd-h2h-intro">Lower average miss is better. Both estimates are graded against the same final results. Game margin is the home score minus the away score.</p><div class="fd-h2h-grid">'+(cards||'<p>Waiting for matched, finalized results.</p>')+'</div><p class="fd-h2h-intro">Only verified saved pairs are included. Player results appear after final stats are graded; early weeks may be incomplete.</p>';
  root.querySelector('#fd-h2h-week').addEventListener('change',e=>render(weeks,Number(e.target.value)));
 }
 fetch('data/weekly-card-comparison.json?t='+Date.now(),{cache:'no-store'}).then(r=>r.ok?r.json():null).then(d=>{
  if(!d||!Array.isArray(d.weeks)||!d.weeks.length){root.innerHTML='<h2>Regular vs ML: who was closer?</h2><p>Waiting for matching saved forecasts and final results.</p>';return;}
  render(d.weeks,0);
 }).catch(()=>{root.innerHTML='<h2>Regular vs ML: who was closer?</h2><p>Results are temporarily unavailable.</p>';});
})();
