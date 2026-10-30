/* FOURTHDOWN ESPN live box scores: unofficial ESPN endpoints; read-only.
   Stats are actual box-score totals, NOT projections or betting recommendations. */
(function(){
'use strict';
// No standalone bottom panel: only update existing matchup player cards.
const esc=x=>String(x??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const url='https://site.api.espn.com/apis/site/v2/sports/football/nfl/';
const categories={passing:'passing_yards',rushing:'rushing_yards',receiving:'receiving_yards'};
const labels={passing_yards:'Passing',rushing_yards:'Rushing',receiving_yards:'Receiving'};
const state={game:'all',market:'all',rows:[],games:[],updated:null,feedError:false};
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
    output.push({game_id:String(event.id),matchup,team,player:athlete.displayName||athlete.fullName||athlete.shortName,player_id:String(athlete.id||''),market,actual:value,game_status:event.status?.type?.shortDetail||event.status?.type?.description||event.status?.displayClock||'',period:Number(event.status?.period||0),clock:event.status?.displayClock||''});
   }
  }
 }
 return output.filter(p=>p.player);
}

// Update only the matching player's market in the existing matchup card.
// No guesswork: player name, team abbreviation and stat market must all agree.
const playerKey=x=>String(x||'').toLowerCase().replace(/[^a-z0-9]/g,'');
// Experimental in-game estimate: blend observed per-minute pace with pregame
// rate for remaining regulation time. Avoid extreme extrapolation in Q1.
function elapsedMinutes(r){
 const clock=String(r.clock||'').match(/(\\d+):(\\d+)/);
 if(!clock||r.period<1||r.period>4)return null;
 const left=Number(clock[1])+Number(clock[2])/60;
 if(left<0||left>15)return null;
 return Math.max(0,Math.min(60,(r.period-1)*15+15-left));
}
function updateLiveBar(card,r){
 const bars=card.querySelector('.hybrid-bars');
 if(!bars)return;
 const model=Number(card.querySelector('.fd-mobile-prop-numbers>div:first-child b')?.textContent);
 const elapsed=elapsedMinutes(r);
 let estimate=null;
 if(Number.isFinite(model)&&model>0&&elapsed!==null&&elapsed>=3){
  const remaining=60-elapsed, baselineRate=model/60;
  const observedRate=r.actual/elapsed;
  const boundedRate=Math.max(baselineRate*0.5,Math.min(baselineRate*1.6,observedRate));
  const trust=Math.min(0.65,elapsed/60*0.85);
  estimate=Math.max(r.actual,r.actual+remaining*(baselineRate*(1-trust)+boundedRate*trust));
 }
 let line=bars.querySelector('.fd-live-final-bar');
 if(!line){line=document.createElement('div');line.className='fd-live-final-bar';bars.appendChild(line);}
 const max=Math.max(1,model||0,r.actual,estimate||0)*1.08;
 const width=Math.max(0,Math.min(100,(estimate??r.actual)/max*100));
 line.innerHTML='<div class="hybrid-label"><span>Live final estimate <small style="opacity:.8">(experimental)</small></span><b>'+(estimate===null?'—':estimate.toFixed(1))+'</b></div><div class="hybrid-track fd-live-estimate-track"><span style="width:'+width.toFixed(1)+'%"></span></div><small class="fd-live-estimate-note">'+(estimate===null?'Estimate available after 3 minutes of regulation play':'Actual '+r.actual+' yards · Blends live pace and pregame projection · Regulation only')+'</small>';
}
let painting=false;
function paintCards(){
 if(painting)return;painting=true;
 try{
  document.querySelectorAll('.fd-mobile-prop-card[data-fd-player]').forEach(card=>{
   const p=playerKey(card.dataset.fdPlayer),team=playerKey(card.dataset.fdTeam),market=card.dataset.fdMarket;
   const matches=state.rows.filter(r=>playerKey(r.player)===p&&playerKey(r.team)===team&&r.market===market);
   let slot=card.querySelector('.fd-live-inline');
   if(matches.length!==1){card.querySelector('.fd-live-final-bar')?.remove();if(!slot){slot=document.createElement('div');slot.className='fd-live-inline';const target=card.querySelector('.fd-mobile-prop-numbers');if(target)target.after(slot);else card.appendChild(slot);}slot.textContent=state.feedError?'ESPN stats temporarily unavailable':state.games.length?'ESPN stats pending for this player':'ESPN live stats · Waiting for kickoff';return;}
   const r=matches[0];
   if(!slot){slot=document.createElement('div');slot.className='fd-live-inline';const target=card.querySelector('.fd-mobile-prop-numbers');if(target)target.after(slot);else card.appendChild(slot);}
   slot.textContent='ESPN LIVE · '+r.actual+' '+(labels[r.market]||'')+' yards';
   updateLiveBar(card,r);const sub=document.createElement('small');sub.textContent=(r.game_status||'In progress')+' · Checked '+(state.updated?state.updated.toLocaleTimeString():'—');slot.appendChild(sub);
  });
 }finally{painting=false;}
}
const observer=new MutationObserver(mutations=>{if(mutations.some(m=>[...m.addedNodes].some(n=>n.nodeType===1&&(n.matches?.('.fd-mobile-prop-card')||n.querySelector?.('.fd-mobile-prop-card')))))paintCards();});
observer.observe(document.body,{subtree:true,childList:true});

async function refresh(){
 try{
  const board=await get('scoreboard?limit=30');
  const live=(board.events||[]).filter(e=>e.status?.type?.state==='in');
  state.games=live.map(e=>({id:String(e.id),name:e.shortName||e.name||String(e.id)}));
  const settled=await Promise.allSettled(live.map(async e=>readPlayers(await get('summary?event='+encodeURIComponent(e.id)),e)));
  state.rows=settled.flatMap(x=>x.status==='fulfilled'?x.value:[]);
  state.updated=new Date();state.feedError=false;
  if(!live.length){paintCards();return;}
  if(settled.every(x=>x.status==='rejected'))throw Error('box scores unavailable');
  paintCards();
 }catch(e){state.feedError=true;paintCards();}
}
paintCards();refresh();setInterval(refresh,60000);setInterval(paintCards,2500);
})();