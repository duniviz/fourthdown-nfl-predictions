(function(){
"use strict";
const host=document.getElementById("fd-simple-grades");
if(!host)return;
const week=document.getElementById("fd-simple-week"),list=document.getElementById("fd-simple-game-list"),learning=document.getElementById("fd-simple-learning"),overview=document.getElementById("fd-simple-overview");
const esc=v=>String(v==null?"":v).replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const num=n=>typeof n==="number"&&Number.isFinite(n),fmt=n=>num(n)?(Math.round(n*10)/10).toString():"—";
const grade=v=>v==="hit"?"RIGHT":v==="miss"?"MISSED":v==="push"?"PUSH":"NOT GRADED";
const gradeClass=v=>v==="hit"?"fd-good":v==="miss"?"fd-bad":"fd-neutral";
const known=(a,b)=>num(a)&&num(b);
function read(url){return fetch(url,{cache:"no-store"}).then(r=>{if(!r.ok)throw Error(url+" unavailable");return r.json()})}
function reason(row){
 const pm=row.projected_margin_home,am=row.home_score-row.away_score;
 const total=row.home_score+row.away_score,pt=row.projected_total;
 const e1=known(pm,am)?Math.abs(pm-am):null,e2=known(total,pt)?Math.abs(total-pt):null;
 let observations=[];
 if(num(e1))observations.push("Projected margin missed by "+fmt(e1)+" points.");
 if(num(e2))observations.push("Projected total missed by "+fmt(e2)+" points"+(pt>total?" (forecast too high).":pt<total?" (forecast too low).":"."));
 if(row.winner_result==="miss")observations.unshift("The winning team prediction was wrong.");
 if(row.ats_result==="miss")observations.push("The spread pick missed.");
 if(row.ou_result==="miss")observations.push("The over/under pick missed.");
 if(!observations.length)observations.push("No verified game-level error details were available.");
 return observations;
}
function sideLabel(a,b,low,high){
 if(!known(a,b)||a===b)return "No clear pick";
 return a>b?high:low;
}
let playerRows=[];
function drawGame(r){
 const score=esc(r.away)+" "+fmt(r.away_score)+" – "+esc(r.home)+" "+fmt(r.home_score);
 const predictedHome=num(r.projected_margin_home)&&num(r.projected_total)?(r.projected_total+r.projected_margin_home)/2:null;
 const predictedAway=num(r.projected_margin_home)&&num(r.projected_total)?(r.projected_total-r.projected_margin_home)/2:null;
 const winner=num(r.projected_margin_home)?(r.projected_margin_home>0?r.home:r.projected_margin_home<0?r.away:"Tie"):"Unavailable";
 const actualWinner=num(r.home_score)&&num(r.away_score)?(r.home_score>r.away_score?r.home:r.home_score<r.away_score?r.away:"Tie"):"Unavailable";
 const ats=known(r.projected_margin_home,r.dk_home_spread)?r.projected_margin_home+r.dk_home_spread:null;
 const line=r.dk_total;
 const ou=known(r.projected_total,line)?sideLabel(r.projected_total,line,"Under","Over"):"Not available";
 const spread=ats==null?"Not available":ats>0?esc(r.home)+" + "+fmt(r.dk_home_spread):ats<0?esc(r.away)+" (vs spread)":"No pick";
 const notes=reason(r);
 const props=playerRows.filter(p=>p.game_id===r.game_id&&num(p.projection)&&num(p.actual));
 const status=r.lock_status==="official"?"Official T-15 lock":"Earlier saved pregame forecast ("+esc(r.lock_status||"unknown")+")";
 return '<details class="fd-grade-game"><summary><span><b>'+esc(r.away)+' at '+esc(r.home)+'</b><small>Week '+esc(r.week)+' · Actual '+score+'</small></span><span class="fd-grade-tags"><b class="'+gradeClass(r.winner_result)+'">Winner '+grade(r.winner_result)+'</b><b class="'+gradeClass(r.ats_result)+'">ATS '+grade(r.ats_result)+'</b><b class="'+gradeClass(r.ou_result)+'">O/U '+grade(r.ou_result)+'</b></span></summary>'+
 '<div class="fd-grade-detail"><p class="fd-grade-source">'+status+' · Forecast saved before kickoff. This is not a postgame prediction.</p>'+
 '<div class="fd-grade-columns"><div><small>Before the game</small><strong>Projected '+fmt(predictedAway)+' – '+fmt(predictedHome)+'</strong><span>Pick to win: '+esc(winner)+'</span><span>Spread side: '+spread+'</span><span>O/U: '+ou+(num(line)?' '+fmt(line):'')+'</span></div>'+
 '<div><small>After the game</small><strong>'+score+'</strong><span>Winner: '+esc(actualWinner)+'</span><span>Actual total: '+fmt(r.home_score+r.away_score)+'</span><span>Actual margin (home): '+fmt(r.home_score-r.away_score)+'</span></div></div>'+
 '<div class="fd-grade-lesson"><b>What this game tells us</b><p>'+notes.map(esc).join(" ")+'</p><small>Observed errors—not proof of a cause or automatic model learning.</small></div>'+drawPlayers(props)+'</div></details>';
}
function drawPlayers(props){
 const markets=["passing_yards","rushing_yards","receiving_yards","completions","attempts","carries","receptions"];
 const eligible=props.filter(p=>markets.includes(p.stat_key)&&num(p.projection)&&num(p.actual));
 if(!eligible.length)return '<p class="fd-grade-source">No completed archived yardage or count-prop forecasts for this matchup.</p>';
 const graded=eligible.filter(p=>p.recommendation_result==="hit"||p.recommendation_result==="miss"||p.recommendation_result==="push");
 const yardage=eligible.filter(p=>p.stat_key.endsWith("_yards"));
 const yardageMae=yardage.length?yardage.reduce((sum,p)=>sum+Math.abs(p.actual-p.projection),0)/yardage.length:null;
 const summary='<p class="fd-grade-source">'+eligible.length+' archived player forecasts · Average yardage miss '+fmt(yardageMae)+' yards · '+graded.length+' verified DK pick results. A saved DK line alone does not prove a pick was recommended.</p>';
 const sections=markets.map(market=>{
  const rows=eligible.filter(p=>p.stat_key===market).sort((a,b)=>Math.abs(b.actual-b.projection)-Math.abs(a.actual-a.projection));
  if(!rows.length)return '';
  const title=market.endsWith("_yards")?market.replace("_yards","").replace(/^./,c=>c.toUpperCase())+" yards":market.replace(/^./,c=>c.toUpperCase());
  const units=market.endsWith("_yards")?"yards":"counts";
  const avg=rows.reduce((sum,p)=>sum+p.actual-p.projection,0)/rows.length;
  const direction=avg>0?"underestimated actual production":avg<0?"overestimated actual production":"was unbiased in this sample";
  return '<details class="fd-player-market"><summary><b>'+title+'</b><small>'+rows.length+' players · Average error '+fmt(Math.abs(avg))+' '+units+' ('+direction+')</small></summary><div class="fd-player-items">'+rows.map(p=>{
    const diff=p.actual-p.projection;
    const verdict=p.recommendation_result||"not_available";
    const recommendation=p.recommended_side==="over"?"OVER":p.recommended_side==="under"?"UNDER":null;
    const recLabel=recommendation?('Saved pick '+recommendation+' · '+grade(verdict)):'No archived pick to grade';
    const model= p.ml_comparison && num(p.ml_comparison.baseline_absolute_error) && num(p.ml_comparison.ml_absolute_error)
      ? 'ML shadow: '+(p.ml_comparison.ml_absolute_error<p.ml_comparison.baseline_absolute_error?'closer than live by ':p.ml_comparison.ml_absolute_error>p.ml_comparison.baseline_absolute_error?'farther from actual by ':'tied live; difference ')+fmt(Math.abs(p.ml_comparison.ml_absolute_error-p.ml_comparison.baseline_absolute_error))+' '+units+' (research only).'
      : 'No verified paired ML comparison for this player.';
    const explanation=Math.abs(diff)<0.05?'Forecast matched the final '+units+'.':diff>0?'Player gained '+fmt(diff)+' more yards than projected.':'Player gained '+fmt(Math.abs(diff))+' fewer yards than projected.';
    return '<article class="fd-player-item"><div class="fd-player-item-head"><b>'+esc(p.player||"Unknown player")+'</b><span class="'+gradeClass(verdict)+'">'+esc(recLabel)+'</span></div><small>'+esc(p.team||"")+' · '+title+'</small><div class="fd-player-figures"><span>Projected <b>'+fmt(p.projection)+'</b></span><span>Actual <b>'+fmt(p.actual)+'</b></span><span>DK line <b>'+fmt(p.dk_line)+'</b></span></div><p>'+esc(explanation)+'</p><small>'+esc(model)+'</small></article>';
  }).join("")+'</div></details>';
 }).join("");
 return '<div class="fd-player-reports"><h3>Player yards &amp; props report cards</h3>'+summary+sections+'</div>';
}
function learn(status,evidence){
 const v=status&&status.validation||{},margin=v.margin||{},total=v.total||{};
 const comparisons=Array.isArray(evidence?.paired_challenger_comparisons)?evidence.paired_challenger_comparisons:[];
 const games=evidence?.completed_games_tested;
 const research=comparisons.filter(x=>num(x.production_mae)&&num(x.challenger_mae)&&num(x.matched_observations)&&x.matched_observations>0);
 const improved=research.filter(x=>x.challenger_mae<x.production_mae);
 const active=Boolean(margin.enabled||total.enabled);
 let html='<h3>What has machine learning actually learned?</h3>';
 html+='<p><b>Live model adjustment: '+(active?'At least one learned adjustment is enabled.':'None enabled in the current learning-status file.')+'</b></p>';
 html+='<p>Margin adjustment: '+fmt(margin.adjustment||0)+' points; total adjustment: '+fmt(total.adjustment||0)+' points. These are reported settings, not inferred gains.</p>';
 html+='<p><b>Research challengers:</b> '+research.length+' comparable market/model summary rows; '+improved.length+' show lower error than production in their reported sample. This does <b>not</b> prove a better model across multiple weeks.</p>';
 if(num(games))html+='<p>Research evidence currently references '+games+' completed games. Small samples are not reliable enough for automatic promotion.</p>';
 html+='<p><b>Simple takeaway:</b> We can identify where projected scores and picks were off. A model change counts as learned and deployed only when the saved validation says it was approved; otherwise it is still being tested.</p>';
 return html;
}
function drawPlayerAnalytics(rows,selectedGameIds,market){
 const container=document.getElementById("fd-player-market-analytics"),summary=document.getElementById("fd-player-dataset");
 if(!container||!summary)return;
 // Only rows from verified graded games, to match the week selector.
 const eligible=rows.filter(r=>selectedGameIds.has(r.game_id)&&num(r.projection)&&num(r.actual)&&["passing_yards","rushing_yards","receiving_yards","completions","attempts","carries","receptions"].includes(r.stat_key));
 const filtered=eligible.filter(r=>market==="all"||r.stat_key===market);
 const picked=filtered.filter(r=>r.recommended_side==="over"||r.recommended_side==="under");
 const graded=picked.filter(r=>r.recommendation_result==="hit"||r.recommendation_result==="miss");
 const hits=graded.filter(r=>r.recommendation_result==="hit").length;
 const mae=filtered.length?filtered.reduce((sum,r)=>sum+Math.abs(r.actual-r.projection),0)/filtered.length:null;
 const bias=filtered.length?filtered.reduce((sum,r)=>sum+r.actual-r.projection,0)/filtered.length:null;
 const withQuote=filtered.filter(r=>num(r.dk_line)).length;
 const paired=filtered.filter(r=>r.ml_comparison&&num(r.ml_comparison.baseline_absolute_error)&&num(r.ml_comparison.ml_absolute_error));
 const improved=paired.filter(r=>r.ml_comparison.ml_absolute_error<r.ml_comparison.baseline_absolute_error).length;
 const stats=[["Forecasts",filtered.length],["Avg absolute error",fmt(mae)+(market==="all"?" mixed units":market.endsWith("_yards")?" yards":" counts")],["Average actual − predicted",fmt(bias)+(market==="all"?" mixed units":market.endsWith("_yards")?" yards":" counts")],["With DK line",withQuote],["Verified picks",graded.length],["Pick hit rate",graded.length?fmt(100*hits/graded.length)+"%":"Not available"],["Paired ML player tests",paired.length],["ML closer",paired.length?improved+"/"+paired.length:"Not available"]];
 // Never represent cross-unit MAE / bias as a valid aggregate.
 if(market==="all"){
  stats[1][1]="See market breakdown";
  stats[2][1]="See market breakdown";
 }
 summary.innerHTML=stats.map(([k,v])=>'<span>'+esc(k)+'<b>'+esc(v)+'</b></span>').join("");
 const group={};for(const r of filtered)(group[r.stat_key]??=[]).push(r);
 const table=Object.entries(group).sort(([a],[b])=>a.localeCompare(b)).map(([key,entries])=>{
  const avg=entries.reduce((sum,r)=>sum+Math.abs(r.actual-r.projection),0)/entries.length;
  const dir=entries.reduce((sum,r)=>sum+r.actual-r.projection,0)/entries.length;
  const quote=entries.filter(r=>num(r.dk_line)).length;
  const picks=entries.filter(r=>r.recommendation_result==="hit"||r.recommendation_result==="miss");
  const success=picks.filter(r=>r.recommendation_result==="hit").length;
  const ml=entries.filter(r=>r.ml_comparison&&num(r.ml_comparison.baseline_absolute_error)&&num(r.ml_comparison.ml_absolute_error));
  const mlWins=ml.filter(r=>r.ml_comparison.ml_absolute_error<r.ml_comparison.baseline_absolute_error).length;
  return '<tr><td>'+esc(key.replace(/_/g," "))+'</td><td>'+entries.length+'</td><td>'+fmt(avg)+'</td><td>'+fmt(dir)+'</td><td>'+quote+'</td><td>'+(picks.length?success+"/"+picks.length+" ("+fmt(100*success/picks.length)+"%)":"Not graded")+'</td><td>'+(ml.length?mlWins+"/"+ml.length:"Not paired")+'</td></tr>';
 }).join("");
 container.innerHTML=table?'<div class="fd-player-table-wrap"><table><thead><tr><th>Market</th><th>n</th><th>MAE</th><th>Bias (actual − model)</th><th>DK lines</th><th>Pick hits</th><th>ML closer</th></tr></thead><tbody>'+table+'</tbody></table></div><small>MAE = mean absolute prediction error. Positive bias means the model underestimated actual production. Hit rate is based only on saved pregame recommendations, not a retrospective pick inferred from the DK line. ML closer measures saved paired challenger results, not deployment eligibility. Different market units are not combined.</small>':'<p class="muted">No verified archived player stats in the chosen games and market.</p>';
}
function playerLearning(calibration,rows){
 const markets=(calibration&&Array.isArray(calibration.markets)?calibration.markets:[]).filter(m=>["passing_yards","rushing_yards","receiving_yards","completions","attempts","carries","receptions"].includes(m.stat_key));
 const paired=rows.filter(p=>p.ml_comparison&&num(p.ml_comparison.baseline_absolute_error)&&num(p.ml_comparison.ml_absolute_error));
 const better=paired.filter(p=>p.ml_comparison.ml_absolute_error<p.ml_comparison.baseline_absolute_error).length;
 let html='<div class="fd-player-learning"><h3>What player-prop ML has learned so far</h3>';
 html+='<p><b>Archived head-to-head player comparisons:</b> '+paired.length+' valid pairs; challenger closer on '+better+'. A closer result for one player does not establish a better deployed model.</p>';
 if(markets.length){
 html+='<p><b>Measured player forecast errors:</b></p><div class="fd-player-learning-grid">'+markets.map(m=>{
   const direction=num(m.mean_error)?m.mean_error>0?'Actual production averaged higher than projected':m.mean_error<0?'Actual production averaged lower than projected':'No average directional bias':'Unknown direction';
   return '<div><b>'+esc(m.stat_key.replace(/_/g," "))+'</b><small>'+fmt(m.sample_size)+' archived forecasts · average absolute miss '+fmt(m.mae)+' '+(m.stat_key.endsWith("_yards")?'yards':'counts')+'</small><small>'+direction+'. '+(m.active?'Bias tracking has enough records for the configured threshold.':'Below the configured bias-tracking sample threshold.')+'</small></div>';
 }).join("")+'</div>';
 }else html+='<p>Player error calibration records unavailable.</p>';
 html+='<small>These are archived error measurements, not calibrated betting probabilities or proof that a correction has been promoted to the live model.</small></div>';
 return html;
}
Promise.allSettled([read("data/game-official-results.json"),read("data/game-learning-status.json"),read("data/weekly-learning-evidence.json"),read("data/player-results.json"),read("data/player-calibration.json")]).then(results=>{
 if(results[0].status!=="fulfilled")throw Error("Verified game grades unavailable");
 const grades=results[0].value,rows=Array.isArray(grades.rows)?grades.rows:[];
 playerRows=results[3].status==="fulfilled"&&Array.isArray(results[3].value.rows)?results[3].value.rows:[];
 const weeks=[...new Set(rows.map(r=>String(r.season)+" Week "+String(r.week)))].sort((a,b)=>b.localeCompare(a,undefined,{numeric:true}));
 week.innerHTML='<option value="all">All graded games</option>'+weeks.map(w=>'<option value="'+esc(w)+'">'+esc(w)+'</option>').join("");
 const render=()=>{
 const chosen=week.value,selected=rows.filter(r=>chosen==="all"||String(r.season)+" Week "+String(r.week)===chosen).sort((a,b)=>String(b.kickoff_utc).localeCompare(String(a.kickoff_utc)));
 overview.textContent=selected.length+' verified graded games · Winner '+selected.filter(r=>r.winner_result==="hit").length+' right · Spread '+selected.filter(r=>r.ats_result==="hit").length+' right · O/U '+selected.filter(r=>r.ou_result==="hit").length+' right. Missing grades do not count as wins.';
 list.innerHTML=selected.length?selected.map(drawGame).join(""):'No verified games in this selection.';
 drawPlayerAnalytics(playerRows,new Set(selected.map(g=>g.game_id)),document.getElementById("fd-player-market-filter")?.value||"all");
 };
 week.addEventListener("change",render);document.getElementById("fd-player-market-filter")?.addEventListener("change",render);render();
 learning.innerHTML=learn(results[1].status==="fulfilled"?results[1].value:null,results[2].status==="fulfilled"?results[2].value:null)+playerLearning(results[4].status==="fulfilled"?results[4].value:null,playerRows);
 if(results[1].status!=="fulfilled"||results[2].status!=="fulfilled")learning.innerHTML+='<p>Some ML evidence files could not be retrieved. No learning conclusions are assumed.</p>';
}).catch(e=>{overview.textContent="Game report cards unavailable; existing History results are unchanged.";learning.textContent="No ML learning status available.";list.textContent=String(e.message)});
})();
