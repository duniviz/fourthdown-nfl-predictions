(function(){
 'use strict';
 const root=document.getElementById('fd-weekly-h2h');if(!root)return;
 const esc=x=>String(x??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
 const num=x=>Number(x).toFixed(1);
 const grade=x=>({hit:'Hit',miss:'Miss',push:'Push',no_pick:'No pick',unavailable:'No saved line'}[x]||'No saved line');
 function breakEven(price){
  const n=Number(price);if(!Number.isInteger(n)||Math.abs(n)<100)return null;
  return n<0?100*(-n)/(-n+100):100*100/(n+100);
 }
 const hitCell=(label,x)=>{if(!x)return '<div><span>'+label+'</span><b>—</b><small>Awaiting grading</small></div>';const pct=x.hit_pct==null?'—':num(x.hit_pct)+'%';return '<div><span>'+label+'</span><b>'+pct+'</b><small>'+esc(x.hits)+'–'+esc(x.misses)+' · '+esc(x.pushes)+' push'+(x.no_picks?' · '+esc(x.no_picks)+' no pick':'')+'</small></div>';};
 function trends(items,market,field){
  market=market||'';
  const valid=items.filter(d=>typeof d.actual==='number'&&Number.isFinite(d.actual)&&typeof d[field]==='number'&&Number.isFinite(d[field]));
  if(!valid.length)return '<p>No matched projections yet.</p>';
  const bias=valid.reduce((sum,d)=>sum+d.actual-d[field],0)/valid.length;
  const high=valid.filter(d=>d[field]>d.actual).length,low=valid.filter(d=>d[field]<d.actual).length;
  const unit=market.startsWith('game_')?'points':market.includes('yards')?'yards':'units';
  const direction=Math.abs(bias)<.05?'Near even':market==='game_margin_home'?(bias<0?'Favored home too much':'Favored away too much'):(bias<0?'Too high':'Too low');
  const cells={};
  for(const d of valid){
   const line=d.dk_line, result=d[field+'_pick_result'];
   if(typeof line!=='number'||!Number.isFinite(line)||!['hit','miss','push'].includes(result))continue;
   const edge=market==='game_margin_home'?d[field]+line:d[field]-line;
   if(Math.abs(edge)<1e-9)continue;
   const side=market==='game_margin_home'?(edge>0?'Home':'Away'):(edge>0?'Over':'Under');
   const size=Math.abs(edge),band=size<2?'Under 2':size<5?'2 to under 5':'5 or more';
   for(const k of [side,band]){if(!cells[k])cells[k]={hit:0,miss:0,push:0};cells[k][result]++;}
  }
  const fmt=k=>{const c=cells[k];if(!c)return esc(k)+': —';const n=c.hit+c.miss;return esc(k)+': '+(n?num(100*c.hit/n)+'%':'—')+' ('+c.hit+'–'+c.miss+(c.push?', '+c.push+' push':'')+')';};
  const sides=market==='game_margin_home'?['Home','Away']:['Over','Under'];
  return '<p><strong>'+esc(direction)+' '+num(Math.abs(bias))+' '+unit+'</strong> on average · '+valid.length+' matched projections · '+high+' high, '+low+' low, '+(valid.length-high-low)+' exact</p><p>'+sides.map(fmt).join(' · ')+'</p><p>Edge size ('+unit+'): '+['Under 2','2 to under 5','5 or more'].map(fmt).join(' · ')+'</p>';
 }
 function render(weeks,index,shadowWeeks,span=1,position='all'){
  const week=weeks[index];
  const options=weeks.map((w,i)=>'<option value="'+i+'"'+(i===index?' selected':'')+'>'+esc(w.season)+' · Week '+esc(w.week)+'</option>').join('');
  const cards=(week.markets||[]).map(m=>{
   const period=weeks.slice(index,index+span).filter(w=>w.season===week.season);
   const allRows=period.flatMap(w=>(w.markets||[]).filter(x=>x.market===m.market).flatMap(x=>x.details||[]));
   const rows=position==='all'||String(m.market||'').startsWith('game_')?allRows:allRows.filter(d=>d.position===position);
   const recovered=(m.details||[]).filter(d=>d.evidence_source==='recovered_pregame_observation').length;
   const winner=m.winner==='ml'?'ML was closer':m.winner==='regular'?'Regular was closer':'About even';
   const details=(m.details||[]).map(d=>'<tr><td>'+esc(d.label)+(d.evidence_source==='recovered_pregame_observation'?' · Recovered pregame':'')+'</td><td>'+num(d.actual)+'</td><td>'+((d.dk_line==null)?'—':num(d.dk_line))+'</td><td>'+num(d.regular)+' · '+grade(d.regular_pick_result)+'</td><td>'+num(d.ml)+' · '+grade(d.ml_pick_result)+'</td></tr>').join('');
   return '<article class="fd-h2h-card"><div class="fd-h2h-heading"><h3>'+esc(m.market==='game_margin_home'?'Against the spread':m.label)+'</h3><strong>'+winner+'</strong></div><p>Hit rate against saved DraftKings line</p><div class="fd-h2h-values">'+hitCell('Regular',m.regular_hits)+hitCell('ML',m.ml_hits)+'</div><p>'+esc(m.regular_hits?.unavailable??m.samples)+' matched projections missing a usable saved line</p><div class="fd-h2h-values"><div><span>Regular avg. miss</span><b>'+num(m.regular_mae)+'</b></div><div><span>ML avg. miss</span><b>'+num(m.ml_mae)+'</b></div></div><p>'+esc(m.samples)+' matched result'+(m.samples===1?'':'s')+(recovered?' · '+recovered+' recovered pregame':'')+' · Regular closer '+esc(m.regular_wins)+' · ML closer '+esc(m.ml_wins)+' · Ties '+esc(m.ties)+'</p><details><summary>High/low trends and pick breakdown</summary><p>Regular projection</p>'+trends(rows,m.market,'regular')+'<p>ML projection</p>'+trends(rows,m.market,'ml')+'</details><details><summary>See individual results</summary><div class="fd-h2h-scroll"><table><thead><tr><th>Game or player</th><th>Actual</th><th>DK line</th><th>Regular · result</th><th>ML · result</th></tr></thead><tbody>'+details+'</tbody></table></div></details></article>';
  }).join('');
  const shadowWeek=(shadowWeeks||[]).find(w=>w.season===week.season&&w.week===week.week);
  const shadows=(shadowWeek?.markets||[]).map(m=>'<article class="fd-h2h-card"><div class="fd-h2h-heading"><h3>'+esc(m.market==='game_margin_home'?'Game margin':'Game total')+' · Saved ML shadow</h3></div><div class="fd-h2h-values"><div><span>Regular avg. miss</span><b>'+num(m.regular_mae)+'</b></div><div><span>ML shadow avg. miss</span><b>'+num(m.shadow_mae)+'</b></div></div><p>'+esc(m.samples)+' saved game locks · Includes early locks</p><details><summary>See individual results</summary><div class="fd-h2h-scroll"><table><thead><tr><th>Game</th><th>Actual</th><th>Regular</th><th>ML shadow</th></tr></thead><tbody>'+(m.details||[]).map(d=>'<tr><td>'+esc(d.game_id)+'</td><td>'+num(d.actual)+'</td><td>'+num(d.regular)+'</td><td>'+num(d.shadow)+'</td></tr>').join('')+'</tbody></table></div></details></article>').join('');
  root.innerHTML='<div class="fd-h2h-top"><div><span class="fd-h2h-kicker">SAVED PREGAME FORECASTS</span><h2>Regular vs ML results</h2></div><label>Week <select id="fd-h2h-week">'+options+'</select></label></div><p class="fd-h2h-intro">Hit rate is hits ÷ (hits + misses) against the saved pregame line. Pushes and projections exactly on the line do not count. Every eligible line is graded, including small edges; odds and profit are not included. Spread lines are shown from the home team’s perspective.</p><p class="fd-h2h-intro">Average miss measures how close the projection was to the final result. Lower is better. Game margin is home score minus away score.</p><div class="fd-h2h-grid">'+(cards||'<p>Waiting for matched, finalized results.</p>')+'</div>'+(shadows?'<h3>Saved game-lock ML shadows</h3><p class="fd-h2h-intro">These estimates were saved with the game forecast. They may differ from the selected ML card model.</p><div class="fd-h2h-grid">'+shadows+'</div>':'')+'<p class="fd-h2h-intro">Only verified saved pairs are included. Player results appear after final stats are graded; early weeks may be incomplete.</p>';
  const intro=root.querySelector('.fd-h2h-intro');
  if(intro&&typeof document.createElement==='function'){
   const note=document.createElement('p');note.textContent='Trend filters apply to the expanded breakdowns. Hit-rate cards above remain the selected week. Position filters exclude players without a verified saved position; game totals remain unfiltered. Historical prices and profit are not included.';
   const selector=document.createElement('label');selector.textContent='Trend window ';const select=document.createElement('select');select.innerHTML='<option value="1">Selected week</option><option value="4">Selected week + up to 3 earlier graded weeks</option>';select.value=String(span);selector.appendChild(select);
   const positionLabel=document.createElement('label');positionLabel.textContent=' Player position ';const positionSelect=document.createElement('select');positionSelect.innerHTML='<option value="all">All positions</option><option value="QB">QB</option><option value="RB">RB</option><option value="WR">WR</option><option value="TE">TE</option>';positionSelect.value=position;positionLabel.appendChild(positionSelect);
   intro.after(note);note.after(selector);selector.after(positionLabel);
   const oddsLabel=document.createElement('label');oddsLabel.textContent=' Compare with American odds ';const odds=document.createElement('input');odds.type='number';odds.placeholder='e.g. -110';odds.inputMode='numeric';oddsLabel.appendChild(odds);const rate=document.createElement('span');rate.textContent=' Enter odds to see the break-even hit rate; this does not use saved prices.';oddsLabel.appendChild(rate);positionLabel.after(oddsLabel);odds.addEventListener('input',()=>{const value=breakEven(odds.value);rate.textContent=value===null?' Enter valid American odds (−100 or lower, or +100 or higher).':' Break-even: '+num(value)+'% at your entered odds; not historical profit.';});
   select.addEventListener('change',e=>render(weeks,index,shadowWeeks,Number(e.target.value),position));
   positionSelect.addEventListener('change',e=>render(weeks,index,shadowWeeks,span,e.target.value));
  }
  root.querySelector('#fd-h2h-week').addEventListener('change',e=>render(weeks,Number(e.target.value),shadowWeeks,span,position));
 }
 fetch('data/weekly-card-comparison.json?t='+Date.now(),{cache:'no-store'}).then(r=>r.ok?r.json():null).then(d=>{
  if(!d||!Array.isArray(d.weeks)||!d.weeks.length){root.innerHTML='<h2>Regular vs ML: who was closer?</h2><p>Waiting for matching saved forecasts and final results.</p>';return;}
  render(d.weeks,0,d.game_shadow_comparisons);
 }).catch(()=>{root.innerHTML='<h2>Regular vs ML: who was closer?</h2><p>Results are temporarily unavailable.</p>';});
})();



