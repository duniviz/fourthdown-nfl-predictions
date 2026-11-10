/* Read-only display of saved pre-lock projection histories. */
window.FDProjectionChanges=(()=>{
 let data={games:{},players:{}};
 const ready=fetch('data/projection-changes.json?t='+Date.now(),{cache:'no-store'}).then(r=>r.ok?r.json():null).then(x=>{if(x&&x.schema_version===1)data=x;}).catch(()=>{});
 const esc=x=>String(x??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
 const aliases={player_pass_yds:'passing_yards',player_passing_yards:'passing_yards',player_rush_yds:'rushing_yards',player_rushing_yards:'rushing_yards',player_rec_yds:'receiving_yards',player_reception_yds:'receiving_yards',player_receiving_yards:'receiving_yards',player_pass_completions:'completions',player_rush_attempts:'carries',rush_attempts:'carries',player_receptions:'receptions'};
 const market=x=>aliases[String(x||'').toLowerCase()]||String(x||'').toLowerCase();
 const date=x=>{const d=new Date(x);return Number.isFinite(d.getTime())?d.toLocaleString('en-US',{timeZone:'America/Chicago',month:'short',day:'numeric',hour:'numeric',minute:'2-digit',timeZoneName:'short'}):'time unavailable';};
 const fmt=x=>Number(x).toFixed(1);
 const isNum=x=>x!==null&&x!==undefined&&x!==''&&Number.isFinite(Number(x));
 const same=(a,b)=>isNum(a)&&isNum(b)&&Math.abs(Number(a)-Number(b))<0.051;
 const block=(summary,rows)=>'<details class="fd-changes"><summary>'+summary+'</summary><div class="fd-changes-body">'+rows+'<p>Earlier saved forecast snapshots · Central Time. The reason for a change was not recorded.</p></div></details>';
 function player(p){
  if(!p||!p.game_id||!p.player_id)return '';
  const key=[p.game_id,p.player_id,market(p.stat_key||p.market_key)].join('|'),v=data.players?.[key]||[];
  if(!v.length)return '';
  const last=v[v.length-1];if(!same(last.value,p.projection))return '';
  const prior=v[v.length-2],summary=prior?'Projection: '+fmt(prior.value)+' → '+fmt(last.value)+' · '+date(last.at):'First saved projection · '+date(last.at);
  const diff=prior?Number((Number(last.value)-Number(prior.value)).toFixed(1)):null;
  const badge=diff===null?'':diff===0?'<span class="fd-move-badge is-flat">No change</span>':diff>0?'<span class="fd-move-badge">↑ +'+fmt(diff)+'</span>':'<span class="fd-move-badge is-down">↓ −'+fmt(Math.abs(diff))+'</span>';
  return block(esc(summary)+badge,v.slice().reverse().map(x=>'<div>'+esc(date(x.at))+' · <strong>'+esc(fmt(x.value))+'</strong></div>').join(''));
 }
 function game(p){
  if(!p?.game_id)return '';const v=data.games?.[p.game_id]||[];if(!v.length)return '';
  const last=v[v.length-1];if(!same(last.home,p.projected_home_score)||!same(last.away,p.projected_away_score))return '';
  const prior=v[v.length-2],format=x=>esc(p.away)+' '+fmt(x.away)+' · '+esc(p.home)+' '+fmt(x.home);
  const summary=prior?'Score: '+format(prior)+' → '+format(last)+' · '+esc(date(last.at)):'First saved score · '+esc(date(last.at));
  return block(summary,v.slice().reverse().map(x=>'<div>'+esc(date(x.at))+' · <strong>'+format(x)+'</strong></div>').join(''));
 }
 return {ready,player,game};
})();
