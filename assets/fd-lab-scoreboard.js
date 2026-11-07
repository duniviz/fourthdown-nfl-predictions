/* Presentation-only view of published, same-slate live/challenger rows. */
(function(){
'use strict';
const tbody=document.getElementById('slate-table'),target=document.getElementById('fd-lab-scoreboard');
if(!tbody||!target)return;
const make=(tag,cls,value)=>{const el=document.createElement(tag);if(cls)el.className=cls;if(value!==undefined)el.textContent=value;return el;};
function render(){
 const rows=[...tbody.querySelectorAll('tr')].map(tr=>[...tr.cells].map(c=>c.textContent.trim())).filter(c=>c.length>=8&&!/awaiting|loading|unavailable|no (verified|matched|published)/i.test(c.join(' ')));
 target.replaceChildren();
 const title=make('div','fd-lab-board-title');title.append(make('span','fd-lab-board-kicker','LIVE VS CHALLENGER'),make('h2','','Verified model comparisons'));target.append(title);
 if(!rows.length){target.append(make('p','fd-lab-board-empty','No verified matched-game comparisons published yet. The leaderboard below will populate after results are available.'));return;}
 const info=make('p','fd-lab-board-note','Published weekly rows only · lower MAE / RMSE is better · DK hits are not guaranteed outcomes');target.append(info);
 const grid=make('div','fd-lab-board-grid');
 for(const row of rows.slice(0,12)){
  const [market,model,samples,mae,rmse,hits,delta,dkDelta]=row;
  const card=make('article','fd-lab-board-card');const header=make('div','fd-lab-board-card-head');header.append(make('small','',market),make('strong','',model));card.append(header);
  const metrics=make('div','fd-lab-board-metrics');
  for(const [label,value] of [['Samples',samples],['MAE',mae],['RMSE',rmse],['DK hits',hits]]){const m=make('div');m.append(make('small','',label),make('strong','',value||'—'));metrics.append(m);}
  card.append(metrics);
  const foot=make('div','fd-lab-board-foot');foot.append(make('span','','MAE vs live: '+(delta||'—')),make('span','','DK vs live: '+(dkDelta||'—')));card.append(foot);grid.append(card);
 }
 target.append(grid);
 if(rows.length>12)target.append(make('p','fd-lab-board-note','Showing 12 of '+rows.length+' published rows. Full leaderboard below.'));
}
let queued=false;const schedule=()=>{if(queued)return;queued=true;requestAnimationFrame(()=>{queued=false;render();});};
new MutationObserver(schedule).observe(tbody,{childList:true,subtree:true,characterData:true});
render();
})();