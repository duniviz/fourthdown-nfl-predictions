(function(){
"use strict";
const root=document.getElementById("fd-deep-diagnostics");
if(!root)return;
const el=id=>document.getElementById(id);
const esc=v=>String(v??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const numeric=v=>typeof v==="number"&&Number.isFinite(v);
const fmt=(v,d=1)=>numeric(v)?v.toFixed(d):"—";
const pct=(n,d)=>d?(100*n/d).toFixed(1)+"%":"—";
const label=s=>String(s).replaceAll("_"," ").replace(/\b\w/g,c=>c.toUpperCase());
const fetchJSON=async name=>{const r=await fetch("data/"+name+".json",{cache:"no-store"});if(!r.ok)throw Error(name+" HTTP "+r.status);return r.json()};
function gradeMarket(rows,field){const a=rows.filter(r=>["hit","miss","push"].includes(r[field]));const hits=a.filter(r=>r[field]==="hit").length;const misses=a.filter(r=>r[field]==="miss").length;return {hits,misses,pushes:a.length-hits-misses,pct:pct(hits,hits+misses)}}
function gameStats(rows){
 const by={};for(const row of rows){const key=String(row.season)+" Week "+String(row.week);(by[key]??=[]).push(row)}
 const ordered=Object.entries(by).sort((a,b)=>b[0].localeCompare(a[0],undefined,{numeric:true}));
 const items=ordered.map(([week,r])=>{const winner=gradeMarket(r,"winner_result"),ats=gradeMarket(r,"ats_result"),ou=gradeMarket(r,"ou_result");const errors=r.filter(x=>numeric(x.projected_total)&&numeric(x.home_score)&&numeric(x.away_score));const totalMae=errors.length?errors.reduce((a,x)=>a+Math.abs(x.projected_total-(x.home_score+x.away_score)),0)/errors.length:null;const marginMae=errors.length?errors.reduce((a,x)=>a+Math.abs(x.projected_margin_home-(x.home_score-x.away_score)),0)/errors.length:null;const early=r.filter(x=>x.lock_status!=="official").length;return '<tr><td>'+esc(week)+'</td><td>'+r.length+'</td><td>'+winner.pct+' ('+winner.hits+'/'+(winner.hits+winner.misses)+')</td><td>'+ats.pct+'</td><td>'+ou.pct+'</td><td>'+fmt(marginMae)+'</td><td>'+fmt(totalMae)+'</td><td>'+early+'/'+r.length+'</td></tr>'}).join("");
 return '<h3>Scoring accuracy by completed week</h3><p class="fd-deep-note">Only previously archived pregame predictions with verified finals. ATS and O/U use saved DK quotes; games with earlier-than-T-15 locks remain marked as such. Average miss is how far the forecast usually lands from the result.</p><div class="fd-deep-overflow"><table><thead><tr><th>Week</th><th>Games n</th><th>Winner</th><th>Spread</th><th>O/U</th><th>Margin average miss</th><th>Total average miss</th><th>Not official T-15</th></tr></thead><tbody>'+items+'</tbody></table></div>';
}
function playerStats(rows){
 const chosen=el("fd-deep-market").value;
 const eligible=rows.filter(r=>numeric(r.actual)&&numeric(r.projection)&&["passing_yards","rushing_yards","receiving_yards","completions","attempts","carries","receptions"].includes(r.stat_key)&&(chosen==="all"||r.stat_key===chosen));
 const by={};for(const r of eligible){const match=String(r.game_id||"").match(/^(\d{4})_(\d{1,2})_/);const week=match?match[1]+" Week "+match[2]:"Unknown week";const key=r.stat_key+"|"+week;(by[key]??=[]).push(r)}
 const output=Object.entries(by).sort((a,b)=>a[0].localeCompare(b[0],undefined,{numeric:true})).map(([key,a])=>{
 const [market,week]=key.split("|"),n=a.length;
 const mae=a.reduce((acc,r)=>acc+Math.abs(r.actual-r.projection),0)/n;
 const bias=a.reduce((acc,r)=>acc+r.actual-r.projection,0)/n;
 const lean=Math.abs(bias)<0.05?'Even':(bias>0?'Leans low':'Leans high');
 const priced=a.filter(r=>numeric(r.dk_line)).length;
 const picks=a.filter(r=>r.recommendation_result==="hit"||r.recommendation_result==="miss");
 const hits=picks.filter(r=>r.recommendation_result==="hit").length;
 const ml=a.filter(r=>r.ml_comparison&&numeric(r.ml_comparison.baseline_absolute_error)&&numeric(r.ml_comparison.ml_absolute_error));
 const better=ml.filter(r=>r.ml_comparison.ml_absolute_error<r.ml_comparison.baseline_absolute_error).length;
 return '<tr><td>'+esc(label(market))+'</td><td>'+esc(week)+'</td><td>'+n+'</td><td>'+fmt(mae)+'</td><td>'+esc(lean)+' · '+fmt(Math.abs(bias))+'</td><td>'+priced+'</td><td>'+picks.length+' ('+pct(hits,picks.length)+')</td><td>'+ml.length+' ('+pct(better,ml.length)+' closer)</td></tr>'}).join("");
 const outliers=eligible.filter(r=>numeric(r.actual)&&numeric(r.projection)).sort((a,b)=>Math.abs(b.actual-b.projection)-Math.abs(a.actual-a.projection)).slice(0,8);
 const worst=outliers.map(r=>'<tr><td>'+esc(r.player)+'</td><td>'+esc(label(r.stat_key))+'</td><td>'+esc(r.game_id)+'</td><td>'+fmt(r.projection)+'</td><td>'+fmt(r.actual)+'</td><td>'+fmt(r.actual-r.projection)+'</td><td>'+fmt(r.dk_line)+'</td></tr>').join("");
 el("fd-deep-player").innerHTML='<h3>Player prediction error by market and week</h3><p class="fd-deep-note">Average miss is the typical distance between the forecast and the result. Leans high means the forecast was above the result; leans low means it was short. The number of DK quotes is not the number of graded picks.</p><div class="fd-deep-overflow"><table><thead><tr><th>Market</th><th>Week</th><th>n</th><th>Average miss</th><th>Leans high/low</th><th>DK quotes</th><th>Graded picks / hit%</th><th>Paired ML / closer%</th></tr></thead><tbody>'+output+'</tbody></table></div><details class="fd-deep-expand"><summary>Largest individual player misses (diagnostic examples)</summary><p class="fd-deep-note">These are observed outliers, not verified explanations for why they happened. Small samples can exaggerate trends.</p><div class="fd-deep-overflow"><table><thead><tr><th>Player</th><th>Market</th><th>Game</th><th>Projected</th><th>Actual</th><th>Error ±</th><th>DK line</th></tr></thead><tbody>'+worst+'</tbody></table></div></details>';
}
function challengers(evidence,player,game){
 const entries=Array.isArray(evidence?.paired_challenger_comparisons)?evidence.paired_challenger_comparisons:[];
 const grouped={};for(const x of entries){if(!numeric(x.production_mae)||!numeric(x.challenger_mae)||!Number.isInteger(x.matched_observations)||x.matched_observations<1)continue;(grouped[x.market]??=[]).push(x)}
 const tr=Object.entries(grouped).sort(([a],[b])=>a.localeCompare(b)).map(([market,a])=>{
 const best=[...a].sort((x,y)=>x.challenger_mae-y.challenger_mae)[0],gain=(best.production_mae-best.challenger_mae)/best.production_mae*100;
 const decision=game?.decisions?.[market]||player?.decisions?.[market]||{};
 const weeks=Number.isInteger(decision.weeks)?decision.weeks:1;
 const status=decision.active===true?"Live candidate enabled":decision.active===false?"Research only — not deployed":"Deployment not verified";
 return '<tr><td>'+esc(label(market))+'</td><td>'+a.length+'</td><td>'+esc(best.challenger)+'</td><td>'+best.matched_observations+'</td><td>'+fmt(best.production_mae,2)+'</td><td>'+fmt(best.challenger_mae,2)+'</td><td>'+(gain>=0?"+":"")+fmt(gain,2)+'%</td><td>'+weeks+'</td><td>'+esc(status)+'</td></tr>'}).join("");
 const desc='Latest evidence: '+esc(evidence?.week_tested||"not available")+'. '+esc(evidence?.completed_games_tested??"Unknown")+' completed games documented. Challenger rows are aggregate research summaries; equal sample sizes do not prove identical underlying game/player IDs. Do not approve deployment from this table.';
 return '<h3>Challenger comparisons, with sample sizes</h3><p class="fd-deep-note">'+desc+' Average miss is the typical distance from the result; lower is better.</p><div class="fd-deep-overflow"><table><thead><tr><th>Market</th><th>Models tested</th><th>Lowest average-miss candidate</th><th>n in candidate</th><th>Live average miss</th><th>Candidate average miss</th><th>Research gain</th><th>Weeks documented</th><th>Current status</th></tr></thead><tbody>'+tr+'</tbody></table></div><p class="fd-deep-note">A candidate appearing better here is a research signal, not a validated improvement. Promotion requires identical frozen observations, independent weeks, rollback evidence and thresholds in the real deployment policy.</p>';
}
function decisions(player,game){
 const cards=[["Game model",game],["Player model",player]].map(([name,runtime])=>{
 const decisions=runtime&&typeof runtime.decisions==="object"?Object.entries(runtime.decisions):[];
 return '<section class="fd-deep-decision"><h3>'+name+' deployment decisions</h3>'+(decisions.length?decisions.map(([market,d])=>{
 const active=d?.active===true;
 const n=d?.paired??d?.matched_observations??"—",weeks=d?.weeks??"—";
 const reason=d?.reason?label(d.reason):"No reason recorded";
 return '<p><b>'+esc(label(market))+'</b> · <strong class="'+(active?"fd-deep-positive":"fd-deep-muted")+'">'+(active?"ACTIVE":"NOT ACTIVE")+'</strong><span> Paired n '+esc(n)+' · weeks '+esc(weeks)+' · '+esc(reason)+'</span></p>';
 }).join(""):'<p>Live decision records unavailable.</p>')+'</section>'}).join("");
 return '<h3>What actually changed in production?</h3><p class="fd-deep-note">A model can finish training without being promoted. These are the current saved runtime decisions, not speculation from research rankings.</p><div class="fd-deep-decision-grid">'+cards+'</div>';
}
Promise.allSettled([fetchJSON("game-official-results"),fetchJSON("player-results"),fetchJSON("weekly-learning-evidence"),fetchJSON("player-ml-runtime"),fetchJSON("game-ml-runtime")]).then(results=>{
 const [games,players,evidence,player,game]=results.map(r=>r.status==="fulfilled"?r.value:null);
 if(!games&&!players){el("fd-deep-content").textContent="Grading archives unavailable. No conclusions shown.";return}
 let html='';
 if(games?.rows)html+=gameStats(games.rows);else html+='<p>Game grading unavailable.</p>';
 el("fd-deep-content").innerHTML=html;
 const draw=()=>{if(players?.rows)playerStats(players.rows);else el("fd-deep-player").textContent="Player archive unavailable."};
 el("fd-deep-market").addEventListener("change",draw);draw();
 el("fd-deep-challengers").innerHTML=challengers(evidence,player,game);
 el("fd-deep-decisions").innerHTML=decisions(player,game);
 const files=["game grades","player grades","paired research","player deployment","game deployment"];
 const missing=results.map((r,i)=>r.status!=="fulfilled"?files[i]:null).filter(Boolean);
 el("fd-deep-status").textContent=missing.length?"Some evidence is unavailable: "+missing.join(", ")+". Missing sources are not treated as success.":"Using published, timestamped FourthDown result and model evidence. No recalculation or changes to production.";
}).catch(e=>{el("fd-deep-status").textContent="Cannot load the detailed report: "+e.message});
})();
