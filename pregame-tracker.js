/* Shared read-only pregame vs actual comparison, identical on both FOURTHDOWN pages.
   Missing pregame values are deliberately not reconstructed. */
(function(){
'use strict';
const esc=x=>String(x??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const fmt=x=>x===null||x===undefined||x===''||!Number.isFinite(Number(x))?'—':Number(x).toFixed(1);
const id=x=>String(x??'').trim().toLowerCase().replace(/[^a-z0-9]/g,'');
async function get(path){try{const r=await fetch('data/'+path+'?t='+Date.now(),{cache:'no-store'});return r.ok?await r.json():{};}catch{return {};}}
async function draw(){
 const host=document.createElement('section');
 host.id='fd-pregame-tracker';
 host.style.cssText='max-width:1160px;margin:24px auto;padding:18px;border:1px solid #425b40;border-radius:16px;background:#112126;color:#f2fbff';
 host.innerHTML='<h2 style="margin:0 0 6px">Pregame projection · DK line · Actual</h2><p style="color:#b9cbd9;margin:0 0 14px">Only timestamped predictions captured before kickoff are shown. Missing values are not estimated.</p><div id="fd-pregame-tracker-content">Loading verified snapshots…</div>';
 const main=document.querySelector('main')||document.body;
 main.appendChild(host);
 const [snap,results]=await Promise.all([get('pregame-snapshots.json'),get('player-results.json')]);
 const rows=Array.isArray(snap.records)?snap.records:[];
 const actuals=new Map((Array.isArray(results.rows)?results.rows:[]).map(r=>[[id(r.game_id),id(r.player_id),id(r.stat_key||r.market)].join(':'),r.actual]));
 const content=host.querySelector('#fd-pregame-tracker-content');
 if(!rows.length){content.textContent='No verified pregame snapshots saved yet.';return;}
 const valid=rows.filter(r=>r.captured_at&&r.kickoff&&Date.parse(r.captured_at)<Date.parse(r.kickoff));
 if(!valid.length){content.textContent='No valid pre-kickoff snapshots available.';return;}
 const display=valid.slice().sort((a,b)=>String(a.game_id).localeCompare(String(b.game_id))).slice(0,200);
 const aliases={player_pass_yds:'passing_yards',player_rush_yds:'rushing_yards',player_rec_yds:'receiving_yards',player_pass_completions:'pass_completions',player_receptions:'receptions',player_rush_attempts:'rushing_attempts'};
 content.innerHTML='<div style="overflow-x:auto"><table style="width:100%;border-collapse:collapse;text-align:left;min-width:570px"><thead><tr><th>Player / Market</th><th>Pregame projection</th><th>Pregame DK line</th><th>Actual</th></tr></thead><tbody>'+display.map(r=>{
 const market=aliases[r.market]||r.market;
 const actual=actuals.get([id(r.game_id),id(r.player_id),id(market)].join(':'));
 return '<tr style="border-top:1px solid #425b40"><td style="padding:10px 5px">'+esc(r.player||r.player_id)+'<small style="display:block;color:#b9cbd9">'+esc(r.game_id)+' · '+esc(r.market)+'</small></td><td>'+fmt(r.projection)+'</td><td>'+fmt(r.dk_line)+'</td><td>'+fmt(actual)+'</td></tr>';
 }).join('')+'</tbody></table></div>';
}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',draw);else draw();
})();
