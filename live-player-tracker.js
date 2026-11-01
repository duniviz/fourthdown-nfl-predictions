/* FOURTHDOWN ESPN live box scores: unofficial ESPN endpoints; read-only.
   Stats are actual box-score totals, NOT projections or betting recommendations. */
(function(){
'use strict';
// No standalone bottom panel: only update existing matchup player cards.
const esc=x=>String(x??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const url='https://site.api.espn.com/apis/site/v2/sports/football/nfl/';
const categories={passing:'passing_yards',rushing:'rushing_yards',receiving:'receiving_yards'};
const countMarkets={passing:'player_pass_completions',rushing:'player_rush_attempts',receiving:'player_receptions'};
const labels={passing_yards:'Passing',rushing_yards:'Rushing',receiving_yards:'Receiving'};
const state={game:'all',market:'all',rows:[],games:[],updated:null,feedError:false};
const get=async path=>{const c=new AbortController();const timer=setTimeout(()=>c.abort(),9000);try{const r=await fetch(url+path,{cache:'no-store',signal:c.signal});if(!r.ok)throw Error('ESPN '+r.status);return await r.json();}finally{clearTimeout(timer);}};
function readPlayers(summary,event){
 const output=[],groups=summary?.boxscore?.players||[];
 const teams=event.competitions?.[0]?.competitors||[];
 const matchup=event.shortName||event.name||event.id;
 const scores=Object.fromEntries(teams.map(c=>[c.team?.abbreviation,Number(c.score)]));
 for(const group of groups){
  const team=group.team?.abbreviation||teams.find(t=>String(t.team?.id)===String(group.team?.id))?.team?.abbreviation||'';
  for(const section of group.statistics||[]){
   const market=categories[String(section.name||section.type||'').toLowerCase()];
   if(!market)continue;
   const idx=(section.labels||[]).findIndex(x=>String(x).toUpperCase()==='YDS');
   if(idx<0)continue;
   const countIdx=(section.labels||[]).findIndex(x=>String(x).toUpperCase()===(market==='passing_yards'?'C/ATT':market==='rushing_yards'?'CAR':'REC'));
   for(const row of section.athletes||[]){
    const athlete=row.athlete||{},values=row.stats||[];
    const value=Number(values[idx]);
    if(!Number.isFinite(value))continue;
    output.push({game_id:String(event.id),matchup,team,player:athlete.displayName||athlete.fullName||athlete.shortName,player_id:String(athlete.id||''),market,actual:value,game_status:event.status?.type?.shortDetail||event.status?.type?.description||event.status?.displayClock||'',period:Number(event.status?.period||0),clock:event.status?.displayClock||'',score_diff:(()=>{const opponent=teams.find(c=>c.team?.abbreviation!==team);const own=scores[team],other=scores[opponent?.team?.abbreviation];return Number.isFinite(own)&&Number.isFinite(other)?own-other:null;})()});
    if(countIdx>=0){
     const raw=String(values[countIdx]??'');
     const count=market==='passing_yards'?Number(raw.split('/')[0]):Number(raw);
     if(raw!==''&&Number.isFinite(count)&&count>=0)output.push({game_id:String(event.id),matchup,team,player:athlete.displayName||athlete.fullName||athlete.shortName,player_id:String(athlete.id||''),market:countMarkets[String(section.name||section.type||'').toLowerCase()],actual:count,game_status:event.status?.type?.shortDetail||event.status?.type?.description||'',period:Number(event.status?.period||0),clock:event.status?.displayClock||''});
    }
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
 const clock=String(r.clock||r.game_status||'').match(/(\d{1,2}):(\d{2})/);
 const period=r.period||Number(String(r.game_status||'').match(/(?:^|\s|-)([1-4])(?:st|nd|rd|th)\b/i)?.[1]||0);
 if(!clock||period<1||period>4)return null;
 const left=Number(clock[1])+Number(clock[2])/60;
 if(left<0||left>15)return null;
 return Math.max(0,Math.min(60,(period-1)*15+15-left));
}

// Observed 2023-2025 NFL pass shares, by score at snap and quarter.
// 0 = no observation; those buckets retain the prior heuristic.
const scriptPassRates={
 within_6:[.575,.642,.573,.620],
 lead_7_13:[.553,.641,.560,.421],lead_14_20:[.579,.635,.540,.358],
 lead_21_27:[0,.662,.497,.290],lead_28_plus:[0,.508,.468,.267],
 trail_7_13:[.590,.664,.605,.798],trail_14_20:[.598,.698,.637,.851],
 trail_21_27:[0,.725,.691,.813],trail_28_plus:[0,.796,.694,.652]
};
function historicalScriptFactor(diff,period,market){
 if(!Number.isFinite(diff)||!Number.isInteger(period)||period<1||period>4)return null;
 const a=Math.abs(diff),side=diff>0?'lead':'trail';
 const bucket=a<7?'within_6':side+'_'+(a<14?'7_13':a<21?'14_20':a<28?'21_27':'28_plus');
 const rate=scriptPassRates[bucket]?.[period-1],neutral=scriptPassRates.within_6[period-1];
 if(!rate||!neutral)return null;
 const passing=market!=='rushing_yards';
 const ratio=passing?rate/neutral:(1-rate)/(1-neutral);
 // Moderate observed play-call changes; player usage and efficiency can differ.
 return Math.max(.75,Math.min(1.25,1+.55*(ratio-1)));
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
  const baseRemaining=remaining*(baselineRate*(1-trust)+boundedRate*trust);
  const diff=r.score_diff;
  const late=.35+.65*(elapsed/60);
  const margin=Number.isFinite(diff)?Math.min(Math.abs(diff),28)/14:0;
  const direction=r.market==='rushing_yards'?(diff>0?1:-1):(diff>0?-1:1);
  const magnitude=r.market==='passing_yards'?.12:.10;
  const cap=r.market==='passing_yards'?.30:r.market==='rushing_yards'?.22:.25;
  const heuristic=Number.isFinite(diff)&&diff!==0?1+direction*Math.min(cap,magnitude*margin)*late:1;
  const historical=historicalScriptFactor(diff,r.period,r.market);
  const factor=historical===null?heuristic:historical;
  estimate=Math.max(r.actual,r.actual+baseRemaining*factor);
 }
 let line=bars.querySelector('.fd-live-final-bar');
 if(!line){line=document.createElement('div');line.className='fd-live-final-bar';bars.appendChild(line);}
 const max=Math.max(1,model||0,r.actual,estimate||0)*1.08;
 const actualWidth=Math.max(0,Math.min(100,r.actual/max*100));
 const projectedWidth=estimate===null?0:Math.max(0,Math.min(100,(estimate-r.actual)/max*100));
 line.innerHTML='<div class="hybrid-label"><span>Live final estimate <small style="opacity:.8">(experimental)</small></span><b>'+(estimate===null?'—':estimate.toFixed(1))+'</b></div><div class="hybrid-track fd-live-estimate-track" role="img" aria-label="Actual '+r.actual+' yards; projected additional '+(estimate===null?'unavailable':(estimate-r.actual).toFixed(1))+' yards"><span class="fd-live-actual-segment" style="width:'+actualWidth.toFixed(1)+'%"></span><span class="fd-live-projected-segment" style="width:'+projectedWidth.toFixed(1)+'%"></span></div><small class="fd-live-estimate-note">'+(estimate===null?'Actual '+r.actual+' yards · Final estimate available after 3 minutes':'<span class="fd-live-key-actual">●</span> Actual '+r.actual+' · <span class="fd-live-key-projected">●</span> Remaining '+(estimate-r.actual).toFixed(1)+' projected yards · Historical game script · Regulation only')+'</small>';
}
function paintModalTotals(){
 const panel=document.querySelector('.fd-live-player-stats[data-fd-live-game-id]');
 if(!panel)return;
 const body=panel.querySelector('.fd-live-player-body');if(!body)return;
 const gameId=String(panel.dataset.fdLiveGameId||'');
 const home=playerKey(panel.dataset.fdLiveHome),away=playerKey(panel.dataset.fdLiveAway);
 const rows=state.rows.filter(x=>String(x.game_id)===gameId&&[home,away].includes(playerKey(x.team)));
 if(!rows.length){body.innerHTML='<p class="fd-modal-muted">'+(state.feedError?'ESPN live stats are temporarily unavailable.':state.games.some(x=>x.id===gameId)?'Waiting for player box-score stats.':'No live player totals for this game right now. Stats appear when ESPN reports the game in progress.')+'</p>';return;}
 const quotes=[...document.querySelectorAll('.fd-result-row[data-fd-player][data-fd-team][data-fd-market]')].filter(el=>el.closest('.scorecard')||el.closest('.fd-modal'));
 const markets={passing_yards:'Passing yards',rushing_yards:'Rushing yards',receiving_yards:'Receiving yards',player_pass_completions:'Completions',player_rush_attempts:'Rush attempts',player_receptions:'Receptions'};
 const lookup=x=>quotes.find(el=>playerKey(el.dataset.fdPlayer)===playerKey(x.player)&&playerKey(el.dataset.fdTeam)===playerKey(x.team)&&el.dataset.fdMarket===x.market);
 const sorted=rows.filter(x=>markets[x.market]).sort((a,b)=>a.team.localeCompare(b.team)||a.player.localeCompare(b.player)||a.market.localeCompare(b.market));
 const nextHtml='<div class="fd-result-list">'+sorted.map(x=>{
  const q=lookup(x);
  const dataset=window.fdLiveMatchupData?.gameId===gameId?window.fdLiveMatchupData:null;
  const stored=(dataset?.projections||[]).find(p=>playerKey(p.player)===playerKey(x.player)&&playerKey(p.team)===playerKey(x.team)&&p.market===x.market);
  const quote=(dataset?.quotes||[]).find(p=>playerKey(p.player)===playerKey(x.player)&&playerKey(p.team)===playerKey(x.team)&&p.market===x.market);
  const raw=q?.dataset.fdDkLine||stored?.dk_line||quote?.line||'',line=raw!==''?Number(raw):NaN,valid=Number.isFinite(line)&&line>0;
  const rawProjection=q?.dataset.fdProjection||stored?.projection||'',projection=rawProjection!==''?Number(rawProjection):NaN;
  const validProjection=Number.isFinite(projection)&&projection>=0;
  return '<div class="fd-result-row"><div class="fd-result-name"><strong>'+esc(x.player)+'</strong><small>'+esc(x.team)+' · '+esc(markets[x.market])+'</small></div><div class="fd-result-values"><div><small>PROJ</small><strong>'+(validProjection?projection.toFixed(1):'—')+'</strong></div><div><small>DK LINE</small><strong>'+(valid?line:'—')+'</strong></div><div><small>ACTUAL</small><strong>'+x.actual+'</strong></div></div></div>';
 }).join('')+'</div><small>ESPN live box-score actuals · '+(state.updated?'Checked '+state.updated.toLocaleTimeString():'')+'</small>';
 if(body.innerHTML!==nextHtml)body.innerHTML=nextHtml;
}
function paintPropRows(){
 document.querySelectorAll('.fd-result-row[data-fd-player][data-fd-team][data-fd-market]').forEach(card=>{
  const player=playerKey(card.dataset.fdPlayer),team=playerKey(card.dataset.fdTeam),market=card.dataset.fdMarket;
  const found=state.rows.filter(r=>playerKey(r.player)===player&&playerKey(r.team)===team&&r.market===market);
  let slot=card.querySelector('.fd-prop-live-actual');
  if(!slot){slot=document.createElement('div');slot.className='fd-prop-live-actual';slot.style.cssText='margin-top:8px;padding:8px;border-radius:8px;background:#10333d;color:#b8f5e6;font-size:12px';card.appendChild(slot);}
  if(found.length!==1){slot.textContent=state.feedError?'Live ESPN stats unavailable':state.games.length?'Live actual pending':'Live actual starts at kickoff';return;}
  const x=found[0],line=Number(card.dataset.fdDkLine),hasLine=card.dataset.fdDkLine!==''&&Number.isFinite(line);
  const remaining=hasLine?Math.max(0,Math.floor(line-x.actual)+1):null;
  const unit=market.includes('yards')?'yards':market==='player_pass_completions'?'completions':market==='player_rush_attempts'?'attempts':'receptions';
  slot.textContent='LIVE ACTUAL: '+x.actual+' '+unit+(hasLine?' / DK '+line+' · '+(remaining===0?'Over line reached':remaining+' more to go over'):'')+' · '+(x.game_status||'In progress');
 });
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
  paintPropRows();paintModalTotals();
 }finally{painting=false;}
}
// Avoid a document-wide MutationObserver: rebuilding hundreds of player rows
// during modal rendering can lock up mobile browsers.
document.addEventListener('fd-matchup-opened',()=>{requestAnimationFrame(paintCards);});
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
refresh();setInterval(refresh,60000);
})();