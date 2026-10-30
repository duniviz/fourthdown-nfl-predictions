/* FOURTHDOWN live stats display. Requires a verified, timestamped data/live-player-stats.json feed.
   This viewer never edits pregame predictions or archived DraftKings quotes. */
(function(){
'use strict';
const root=document.getElementById('fd-live-prop-tracker');if(!root)return;
const esc=x=>String(x??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;','"':'&quot;',"'":'&#39;'}[c]));
const norm=x=>String(x||'').toLowerCase().replace(/[^a-z0-9]/g,'');
let last=null;
root.innerHTML='<div class="fd-live-head"><strong>Live player stats</strong><small id="fd-live-stamp">Waiting for verified stats</small></div><div id="fd-live-rows">Live player box scores are not connected yet.</div>';
async function refresh(){
 try{
  const r=await fetch('data/live-player-stats.json?t='+Date.now(),{cache:'no-store'});
  if(!r.ok)throw Error('not published');
  const d=await r.json(),updated=Date.parse(d.updated_at_utc||''),age=(Date.now()-updated)/60000;
  if(!Number.isFinite(updated)||age< -5||age>10||!Array.isArray(d.players))throw Error('stale or invalid feed');
  last=d;
  const game=document.querySelector('#fd-live-game-filter')?.value||'all';
  const market=document.querySelector('#fd-live-market-filter')?.value||'all';
  const rows=d.players.filter(p=>p&&p.player&&p.game_id&&['passing_yards','rushing_yards','receiving_yards'].includes(p.market)&&Number.isFinite(Number(p.actual))&&(game==='all'||String(p.game_id)===game)&&(market==='all'||p.market===market));
  const names={passing_yards:'Passing',rushing_yards:'Rushing',receiving_yards:'Receiving'};
  document.getElementById('fd-live-stamp').textContent='Updated '+new Date(updated).toLocaleTimeString()+' · '+(d.source||'Verified feed');
  const games=[...new Map(d.players.filter(p=>p.game_id).map(p=>[String(p.game_id),String(p.matchup||p.game_id)])).entries()];
  const filters='<label>Game <select id="fd-live-game-filter"><option value="all">All games</option>'+games.map(([id,name])=>'<option value="'+esc(id)+'" '+(game===id?'selected':'')+'>'+esc(name)+'</option>').join('')+'</select></label> <label>Stat <select id="fd-live-market-filter">'+[['all','All'],['passing_yards','Passing'],['rushing_yards','Rushing'],['receiving_yards','Receiving']].map(([id,name])=>'<option value="'+id+'" '+(market===id?'selected':'')+'>'+name+'</option>').join('')+'</select></label>';
  document.getElementById('fd-live-rows').innerHTML='<div class="fd-live-filters">'+filters+'</div>'+(rows.length?rows.slice(0,100).map(p=>{
   const actual=Number(p.actual),projection=Number(p.pregame_projection),line=Number(p.dk_pregame_line);
   const hasProjection=p.pregame_projection!==null&&p.pregame_projection!==undefined&&Number.isFinite(projection);
   const hasLine=p.dk_pregame_line!==null&&p.dk_pregame_line!==undefined&&Number.isFinite(line);
   return '<div class="fd-live-row"><div><strong>'+esc(p.player)+'</strong><small>'+esc(p.team)+' · '+esc(p.matchup||'')+' · '+names[p.market]+' · '+esc(p.game_status||'')+'</small></div><div><b>'+actual.toFixed(0)+'</b><small>Actual</small></div><div><b>'+(hasProjection?projection.toFixed(1):'—')+'</b><small>Pregame model</small></div><div><b>'+(hasLine?line.toFixed(1):'—')+'</b><small>Pregame DK</small></div></div>';
  }).join(''):'<p>No verified player statistics for this selection yet.</p>');
  root.querySelectorAll('select').forEach(s=>s.addEventListener('change',refreshDisplay));
 }catch(e){
  document.getElementById('fd-live-stamp').textContent='Feed unavailable';
  document.getElementById('fd-live-rows').textContent='Live stats are unavailable or delayed. Pregame projections remain unchanged.';
 }
}
function refreshDisplay(){if(last){const game=root.querySelector('#fd-live-game-filter')?.value||'all',market=root.querySelector('#fd-live-market-filter')?.value||'all';root.dataset.game=game;root.dataset.market=market;}refresh();}
refresh();setInterval(refresh,60000);
})();