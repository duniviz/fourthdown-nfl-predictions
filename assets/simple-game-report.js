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
 const status=r.lock_status==="official"?"Official T-15 lock":"Earlier saved pregame forecast ("+esc(r.lock_status||"unknown")+")";
 return '<details class="fd-grade-game"><summary><span><b>'+esc(r.away)+' at '+esc(r.home)+'</b><small>Week '+esc(r.week)+' · Actual '+score+'</small></span><span class="fd-grade-tags"><b class="'+gradeClass(r.winner_result)+'">Winner '+grade(r.winner_result)+'</b><b class="'+gradeClass(r.ats_result)+'">ATS '+grade(r.ats_result)+'</b><b class="'+gradeClass(r.ou_result)+'">O/U '+grade(r.ou_result)+'</b></span></summary>'+
 '<div class="fd-grade-detail"><p class="fd-grade-source">'+status+' · Forecast saved before kickoff. This is not a postgame prediction.</p>'+
 '<div class="fd-grade-columns"><div><small>Before the game</small><strong>Projected '+fmt(predictedAway)+' – '+fmt(predictedHome)+'</strong><span>Pick to win: '+esc(winner)+'</span><span>Spread side: '+spread+'</span><span>O/U: '+ou+(num(line)?' '+fmt(line):'')+'</span></div>'+
 '<div><small>After the game</small><strong>'+score+'</strong><span>Winner: '+esc(actualWinner)+'</span><span>Actual total: '+fmt(r.home_score+r.away_score)+'</span><span>Actual margin (home): '+fmt(r.home_score-r.away_score)+'</span></div></div>'+
 '<div class="fd-grade-lesson"><b>What this game tells us</b><p>'+notes.map(esc).join(" ")+'</p><small>Observed errors—not proof of a cause or automatic model learning.</small></div></div></details>';
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
Promise.allSettled([read("data/game-official-results.json"),read("data/game-learning-status.json"),read("data/weekly-learning-evidence.json")]).then(results=>{
 if(results[0].status!=="fulfilled")throw Error("Verified game grades unavailable");
 const grades=results[0].value,rows=Array.isArray(grades.rows)?grades.rows:[];
 const weeks=[...new Set(rows.map(r=>String(r.season)+" Week "+String(r.week)))].sort((a,b)=>b.localeCompare(a,undefined,{numeric:true}));
 week.innerHTML='<option value="all">All graded games</option>'+weeks.map(w=>'<option value="'+esc(w)+'">'+esc(w)+'</option>').join("");
 const render=()=>{
 const chosen=week.value,selected=rows.filter(r=>chosen==="all"||String(r.season)+" Week "+String(r.week)===chosen).sort((a,b)=>String(b.kickoff_utc).localeCompare(String(a.kickoff_utc)));
 overview.textContent=selected.length+' verified graded games · Winner '+selected.filter(r=>r.winner_result==="hit").length+' right · Spread '+selected.filter(r=>r.ats_result==="hit").length+' right · O/U '+selected.filter(r=>r.ou_result==="hit").length+' right. Missing grades do not count as wins.';
 list.innerHTML=selected.length?selected.map(drawGame).join(""):'No verified games in this selection.';
 };
 week.addEventListener("change",render);render();
 learning.innerHTML=learn(results[1].status==="fulfilled"?results[1].value:null,results[2].status==="fulfilled"?results[2].value:null);
 if(results[1].status!=="fulfilled"||results[2].status!=="fulfilled")learning.innerHTML+='<p>Some ML evidence files could not be retrieved. No learning conclusions are assumed.</p>';
}).catch(e=>{overview.textContent="Game report cards unavailable; existing History results are unchanged.";learning.textContent="No ML learning status available.";list.textContent=String(e.message)});
})();
