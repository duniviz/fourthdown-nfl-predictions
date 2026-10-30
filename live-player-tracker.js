/* FOURTHDOWN ESPN live box scores: unofficial ESPN endpoints; read-only.
   Stats are actual box-score totals, NOT projections or betting recommendations. */
(function(){
'use strict';
const root=document.getElementById('fd-live-prop-tracker');if(!root)return;
const esc=x=>String(x??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const url='https://site.api.espn.com/apis/site/v2/sports/football/nfl/';
const categories={passing:'passing_yards',rushing:'rushing_yards',receiving:'receiving_yards'};
const labels={passing_yards:'Passing',rushing_yards:'Rushing',receiving_yards:'Receiving'};
const state={game:'all',market:'all',rows:[],games:[],updated:null};
root.innerHTML='<div class="fd-live-head"><strong>ESPN player box scores</strong><small id="fd-live-stamp">Checking ESPN…</small></div><div id="fd-live-rows">Loading live game statistics…</div>';
const get=async path=>{const c=new AbortController();const timer=setTimeout(()=>c.abort(),9000);try{const r=await fetch(url+path,{cache:'no-store',signal:c.signal});if(!r.ok)throw Error('ESPN '+r.status);return await r.json();}finally{clearTimeout(timer);}};
function readPlayers(summary,event){
 const output=[],groups=summary?.boxscore?.players||[];
 const teams=event.competitions?.[0]?.competitors||[];
 const matchup=event.shortName||event.name||event.id;
 for(const group of groups){
  const team=group.team?.abbreviation||teams.find(t=>String(t.team?.id)===String(group.team?.id))?.team?.abbreviation||'';
  for(const section of group.statistics||[]){
   const market=categories[String(section.name||section.type||'').toLowerCase()];
   if(!market)continue;
   const idx=(section.labels||[]).findIndex(x=>String(x).toUpperCase()==='YDS');
   if(idx<0)continue;
   for(const row of section.athletes||[]){
    const athlete=row.athlete||{},values=row.stats||[];
    const value=Number(values[idx]);
    if(!Number.isFinite(value))continue;
    output.push({game_id:String(event.id),matchup,team,player:athlete.displayName||athlete.fullName||athlete.shortName,player_id:String(athlete.id||''),market,actual:value,game_status:event.status?.type?.shortDetail||event.status?.type?.description||event.status?.displayClock||''});
   }
  }
 }
 return output.filter(p=>p.player);
}

// Update only the matching player's market in the existing matchup card.
// No guesswork: player name, team abbreviation and stat market must all agree.
const playerKey=x=>String(x||'').toLowerCase().replace(/[^a-z0-9]/g,'');
let painting=false;
function paintCards(){
 if(painting)return;painting=true;
 try{
  document.querySelectorAll('.fd-mobile-prop-card[data-fd-player]').forEach(card=>{
   const p=playerKey(card.dataset.fdPlayer),team=playerKey(card.dataset.fdTeam),market=card.dataset.fdMarket;
   const matches=state.rows.filter(r=>playerKey(r.player)===p&&playerKey(r.team)===team&&r.market===market);
   let slot=card.querySelector('.fd-live-inline');
   if(matches.length!==1){if(slot)slot.remove();return;}
   const r=matches[0];
   if(!slot){slot=document.createElement('div');slot.className='fd-live-inline';const target=card.querySelector('.fd-mobile-prop-numbers');if(target)target.after(slot);else card.appendChild(slot);}
   slot.textContent='ESPN LIVE · '+r.actual+' '+(labels[r.market]||'')+' yards';
   const sub=document.createElement('small');sub.textContent=(r.game_status||'In progress')+' · Checked '+(state.updated?state.updated.toLocaleTimeString():'—');slot.appendChild(sub);
  });
 }finally{painting=false;}
}
const observer=new MutationObserver(mutations=>{if(mutations.some(m=>[...m.addedNodes].some(n=>n.nodeType===1&&(n.matches?.('.fd-mobile-prop-card')||n.querySelector?.('.fd-mobile-prop-card')))))paintCards();});
observer.observe(document.body,{subtree:true,childList:true});

function display(){
 const games=state.games,rows=state.rows.filter(p=>(state.game==='all'||p.game_id===state.game)&&(state.market==='all'||p.market===state.market));
 const filters='<div class="fd-live-filters"><label>Game <select id="fd-live-game-filter"><option value="all">All live games</option>'+games.map(g=>'<option value="'+esc(g.id)+'" '+(state.game===g.id?'selected':'')+'>'+esc(g.name)+'</option>').join('')+'</select></label><label>Stat <select id="fd-live-market-filter">'+[['all','All'],['passing_yards','Passing'],['rushing_yards','Rushing'],['receiving_yards','Receiving']].map(([id,name])=>'<option value="'+id+'" '+(state.market===id?'selected':'')+'>'+name+'</option>').join('')+'</select></label></div>';
 document.getElementById('fd-live-rows').innerHTML=filters+(rows.length?rows.slice(0,120).map(p=>'<div class="fd-live-row"><div><strong>'+esc(p.player)+'</strong><small>'+esc(p.team)+' · '+esc(p.matchup)+' · '+labels[p.market]+' · '+esc(p.game_status)+'</small></div><div><b>'+p.actual+'</b><small>ESPN actual</small></div><div><b>—</b><small>Pregame model*</small></div><div><b>—</b><small>Pregame DK*</small></div></div>').join(''):'<p>No player box-score totals available for the selected live games yet.</p>')+'<small>*Pregame forecasts and DraftKings prices are not linked to ESPN player IDs yet. They are deliberately withheld rather than guessed.</small>';
 root.querySelector('#fd-live-game-filter').addEventListener('change',e=>{state.game=e.target.value;display();});
 root.querySelector('#fd-live-market-filter').addEventListener('change',e=>{state.market=e.target.value;display();});
}
async function refresh(){
 try{
  const board=await get('scoreboard?limit=30');
  const live=(board.events||[]).filter(e=>e.status?.type?.state==='in');
  state.games=live.map(e=>({id:String(e.id),name:e.shortName||e.name||String(e.id)}));
  const settled=await Promise.allSettled(live.map(async e=>readPlayers(await get('summary?event='+encodeURIComponent(e.id)),e)));
  state.rows=settled.flatMap(x=>x.status==='fulfilled'?x.value:[]);
  state.updated=new Date();
  document.getElementById('fd-live-stamp').textContent=live.length?'ESPN checked '+state.updated.toLocaleTimeString()+' · '+live.length+' live game(s)':'ESPN checked '+state.updated.toLocaleTimeString()+' · No live games';
  if(!live.length){document.getElementById('fd-live-rows').textContent='No NFL games are currently in progress. Live box scores will appear during games.';paintCards();return;}
  if(settled.every(x=>x.status==='rejected'))throw Error('box scores unavailable');
  display();paintCards();
 }catch(e){document.getElementById('fd-live-stamp').textContent='ESPN feed unavailable';document.getElementById('fd-live-rows').textContent='Unable to retrieve ESPN live box scores. No statistics are inferred or substituted.';}
}
refresh();setInterval(refresh,60000);
})();