/* Read-only bettor-first board. No changes to prediction or grading logic. */
(async function(){
 const root=document.getElementById('fd-opportunity-list'),stamp=document.getElementById('fd-opportunity-freshness'),category=document.getElementById('fd-opportunity-category');
 if(!root)return;
 const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
 const norm=s=>String(s||'').toLowerCase().replace(/[^a-z0-9]/g,'');
 const names={'player_pass_completions':'Completions','player_pass_attempts':'Pass attempts','player_rush_attempts':'Rush attempts','player_receptions':'Receptions','player_pass_yds':'Passing yards','player_rush_yds':'Rushing yards','player_rec_yds':'Receiving yards'};
 const categoryOf=m=>m==='player_receptions'||m==='player_rec_yds'?'receiving':m.includes('rush')?'rushing':m.includes('pass')?'passing':'count';
 const isCount=m=>!['player_pass_yds','player_rush_yds','player_rec_yds'].includes(m);
 const aliases={'player_passing_completions':'player_pass_completions','player_passing_attempts':'player_pass_attempts','player_rushing_attempts':'player_rush_attempts','player_passing_yards':'player_pass_yds','player_rushing_yards':'player_rush_yds','player_receiving_yards':'player_rec_yds'};
 const teams={ARI:'cardinals',ATL:'falcons',BAL:'ravens',BUF:'bills',CAR:'panthers',CHI:'bears',CIN:'bengals',CLE:'browns',DAL:'cowboys',DEN:'broncos',DET:'lions',GB:'packers',HOU:'texans',IND:'colts',JAX:'jaguars',KC:'chiefs',LV:'raiders',LAC:'chargers',LA:'rams',MIA:'dolphins',MIN:'vikings',NE:'patriots',NO:'saints',NYG:'giants',NYJ:'jets',PHI:'eagles',PIT:'steelers',SF:'49ers',SEA:'seahawks',TB:'buccaneers',TEN:'titans',WAS:'commanders'};
 const matchesGame=(q,gameId,team)=>{const parts=String(gameId||'').split('_');if(parts.length!==4||!teams[parts[2]]||!teams[parts[3]]||!teams[team])return false;const away=String(q.away_team||'').toLowerCase(),home=String(q.home_team||'').toLowerCase();return away.includes(teams[parts[2]])&&home.includes(teams[parts[3]])&&(team===parts[2]||team===parts[3]);};
 const validTime=s=>{const t=Date.parse(s||'');return Number.isFinite(t)?t:null};
 try{
  const [pr,od,yr]=await Promise.all(['data/count-projections.json','data/dk-odds.json','data/research-prop-desk.json'].map(u=>fetch(u+'?t='+Date.now(),{cache:'no-store'})));
  if(!pr.ok||!od.ok)throw Error('Data feed unavailable');
  const p=await pr.json(),d=await od.json(),y=yr.ok?await yr.json():{},now=Date.now();
  const generated=validTime(p.generated_at_utc),quoted=validTime(d.generated_at_utc);
  if(!generated||now-generated>36*3600000||!quoted||now-quoted>36*3600000)throw Error('Current projections or DK lines are stale');
  const quotes=new Map();
  for(const q of d.rows||[]){
   const kickoff=validTime(q.commence_time),updated=validTime(q.last_update);
   if(!kickoff||kickoff<=now||!updated||updated>now||updated>=kickoff)continue;
   if(!Number.isFinite(Number(q.line))||q.line===null||q.line==='')continue;
   const k=norm(q.player)+'|'+String(q.market_key)+'|'+norm(q.away_team)+'|'+norm(q.home_team);
   if(!quotes.has(k)||updated>quotes.get(k).updated)quotes.set(k,{q,updated});
  }
  const rows=[];
  for(const x of p.players||[]){
   const market=aliases[x.market_key]||x.market_key;
   if(!names[market]||!Number.isFinite(Number(x.projection)))continue;
   const found=[...quotes.values()].filter(v=>norm(v.q.player)===norm(x.player)&&v.q.market_key===market&&matchesGame(v.q,x.game_id,x.team)).sort((a,b)=>b.updated-a.updated)[0];if(!found)continue;
   const q=found.q,line=Number(q.line),projection=Number(x.projection);
   const gap=projection-line;if(Math.abs(gap)<0.01)continue;
   
   const row={x,q,line,projection,gap,market,updated:found.updated};
   rows.push(row);
  }
  // Yardage forecasts come from the published research feed; quotes always
  // come from the same timestamped DK feed used by count props.
  const yardMarket={'passing_yards':'player_pass_yds','rushing_yards':'player_rush_yds','receiving_yards':'player_rec_yds'};
  const yardStamp=validTime(y.generated_at_utc);
  if(yardStamp&&yardStamp<=now&&now-yardStamp<=36*3600000){
   for(const x of y.comparisons||[]){
    const market=yardMarket[x.market];if(!market||!Number.isFinite(Number(x.projected_yards))||x.projected_yards===null)continue;
    const found=[...quotes.values()].filter(v=>norm(v.q.player)===norm(x.player_name)&&v.q.market_key===market&&((v.q.away_team||'').toLowerCase().includes(teams[x.team]||'__invalid__')||(v.q.home_team||'').toLowerCase().includes(teams[x.team]||'__invalid__'))).sort((a,b)=>b.updated-a.updated)[0];if(!found)continue;
    const q=found.q;
    const line=Number(q.line),projection=Number(x.projected_yards),gap=projection-line;
    if(Math.abs(gap)<0.01)continue;
    rows.push({x:{player:x.player_name,team:x.team,recent_5_avg:null},q,line,projection,gap,market,updated:found.updated,provisional:x.ranking_status!=='eligible'});
   }
  }
  // Deduplicate player/market; rank relative gaps within the market, not as probabilities.
  const seen=new Set(),best=rows.sort((a,b)=>Math.abs(b.gap)/Math.max(1,b.line)-Math.abs(a.gap)/Math.max(1,a.line)).filter(r=>{const k=norm(r.x.player)+'|'+r.market;if(seen.has(k))return false;seen.add(k);return true});
  const render=()=>{const selected=category?.value||'all';const filtered=best.filter(r=>selected==='all'||(selected==='count'?isCount(r.market):categoryOf(r.market)===selected)).slice(0,5);
  if(!filtered.length){root.innerHTML='<p class="caption">No matching upcoming DK player lines are available right now. Check the Prop Desk for the full slate.</p>';return;}
  root.innerHTML=filtered.map(r=>'<article class="fd-matchup-card" style="padding:15px"><div class="fd-matchup-top"><div><div class="fd-matchup-tag">'+esc(r.x.team)+' · '+esc(names[r.market])+'</div><h3>'+esc(r.x.player)+'</h3></div><span class="fd-matchup-tag">'+(r.gap>0?'OVER':'UNDER')+' '+esc(r.line.toFixed(1))+'</span></div><p style="margin:8px 0">Model <strong>'+esc(r.projection.toFixed(1))+'</strong> · DK <strong>'+esc(r.line.toFixed(1))+'</strong> · Gap <strong>'+esc((r.gap>0?'+':'')+r.gap.toFixed(1))+'</strong></p><small class="caption">Recent five-game avg: '+(r.x.recent_5_avg!==null&&r.x.recent_5_avg!==undefined&&Number.isFinite(Number(r.x.recent_5_avg))?esc(Number(r.x.recent_5_avg).toFixed(1)):'unavailable')+' · '+(r.provisional?'Research projection; availability not verified · ':'')+'DK quote '+esc(new Date(r.updated).toLocaleString('en-US',{timeZone:'America/Chicago',month:'short',day:'numeric',hour:'numeric',minute:'2-digit'}))+' CT</small></article>').join('');
  };
  category?.addEventListener('change',render);render();
  stamp.textContent='DK feed updated '+new Date(quoted).toLocaleString('en-US',{timeZone:'America/Chicago',month:'short',day:'numeric',hour:'numeric',minute:'2-digit'})+' CT · Research only; confirm lines before betting.';
 }catch(e){root.innerHTML='<p class="caption">Current player prop comparisons are unavailable. <a href="bets.html">Open the Prop Desk</a>.</p>';stamp.textContent='No unverified or stale lines are presented as current.';}
})();