/* Shared, read-only player season stats panel. ESPN verified completed games only. */
(()=>{'use strict';
const norm=s=>String(s||'').toLowerCase().replace(/[^a-z0-9]/g,'');
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const labels={player_pass_yds:'Passing yards',player_rush_yds:'Rushing yards',player_rec_yds:'Receiving yards',player_pass_completions:'Completions',player_pass_attempts:'Pass attempts',player_rush_attempts:'Rushing attempts',player_receptions:'Receptions'};
let dataPromise,oddsPromise,projectionPromise;
const loadOdds=()=>oddsPromise||(oddsPromise=fetch('data/dk-odds.json',{cache:'no-store'}).then(r=>r.ok?r.json():{}).catch(()=>({})));
const loadProjections=()=>projectionPromise||(projectionPromise=Promise.all([
 fetch('data/count-projections.json',{cache:'no-store'}).then(r=>r.ok?r.json():{}).catch(()=>({})),
 fetch('data/research-prop-desk.json',{cache:'no-store'}).then(r=>r.ok?r.json():{}).catch(()=>({}))
]).then(([count,research])=>({count,research})));
const playerProjection=(source,name,market,kickoff)=>{
 const research=Array.isArray(source?.comparisons);
 const rows=research?source.comparisons:(Array.isArray(source?.players)?source.players:[]);
 const captured=Date.parse(source?.generated_at_utc);
 const start=Date.parse(kickoff);
 if(Number.isFinite(captured)&&Number.isFinite(start)&&captured>=start)return null;
 const researchMarkets={player_pass_yds:'passing_yards',player_rush_yds:'rushing_yards',player_rec_yds:'receiving_yards'};
 const expectedMarket=research?(researchMarkets[market]||market):market;
 const matches=rows.filter(x=>norm(research?x.player_name:x.player)===norm(name)&&(research?x.market:(x.market_key||x.stat_key))===expectedMarket&&
   (research?(x.projected_yards!==null&&x.projected_yards!==undefined&&Number.isFinite(Number(x.projected_yards))):(x.projection!==null&&x.projection!==undefined&&x.projection!==''&&Number.isFinite(Number(x.projection)))));
 if(matches.length!==1)return null;
 return {value:Number(research?matches[0].projected_yards:matches[0].projection),kind:research?'Research estimate':'Model projection'};
};
const findPlayerProjection=(sources,name,market,kickoff)=>{
 const model=playerProjection(sources.count,name,market,kickoff);
 return model||playerProjection(sources.research,name,market,kickoff);
};
const currentQuote=(rows,name,market)=>{const now=Date.now();return (rows||[]).filter(q=>norm(q.player)===norm(name)&&q.market_key===market&&q.line!==null&&q.line!==''&&Number.isFinite(Number(q.line))&&Date.parse(q.commence_time)>now&&Date.parse(q.last_update)<=now).sort((a,b)=>Date.parse(b.last_update)-Date.parse(a.last_update))[0]};
const load=()=>dataPromise||(dataPromise=fetch('data/player-recent-games.json',{cache:'no-store'}).then(r=>{if(!r.ok)throw Error('No player history');return r.json()}));
const style=document.createElement('style');style.textContent=`
.fd-stat-name{cursor:pointer;text-decoration:underline;text-decoration-style:dotted;text-underline-offset:4px;color:#e8fff8}
.fd-stat-overlay{position:fixed;inset:0;background:rgba(2,9,18,.78);backdrop-filter:blur(7px);-webkit-backdrop-filter:blur(7px);z-index:99999;display:flex;align-items:center;justify-content:center;padding:clamp(12px,3vw,28px)}
.fd-stat-dialog{width:min(760px,100%);max-height:min(90dvh,860px);overflow:auto;padding:0;color:#f3f7fc;border:1px solid #45667b;border-radius:20px;background:linear-gradient(155deg,#14283b,#0b1727 76%);box-shadow:0 28px 90px #000b,0 0 0 1px #baff2512;scrollbar-color:#3b5c70 #101e30}
.fd-stat-dialog header{position:sticky;top:0;z-index:2;display:flex;align-items:center;justify-content:space-between;gap:14px;padding:16px 20px;border-bottom:1px solid #304a60;background:linear-gradient(110deg,#172e43,#122237f5)}
.fd-stat-identity{display:flex;align-items:center;gap:14px;min-width:0}
.fd-stat-title{min-width:0}
.fd-stat-kicker{display:block;margin-bottom:3px;color:#baff35;font-size:9px;font-weight:900;letter-spacing:.14em;text-transform:uppercase}
.fd-stat-dialog h2{margin:0;color:#f6fbff;font-size:clamp(19px,3vw,25px);line-height:1.15;letter-spacing:-.02em}
.fd-stat-dialog header p{margin:5px 0 0;color:#a9bdce;font-size:11px}
.fd-stat-headshot{width:62px;height:62px;flex:0 0 62px;object-fit:contain;border-radius:50%;background:linear-gradient(145deg,#27485a,#152a3c);border:2px solid #7ce1c8;box-shadow:0 0 0 4px #7ce1c81a}
.fd-stat-dialog button{flex:0 0 auto;border:1px solid #47647b;background:#20394f;color:#eff9ff;border-radius:10px;padding:9px 13px;font-size:12px;font-weight:800;cursor:pointer;transition:background .18s,border-color .18s}
.fd-stat-dialog button:hover{background:#2b4c65;border-color:#79dbcc}
.fd-stat-dialog button:focus-visible{outline:2px solid #baff35;outline-offset:2px}
.fd-stat-content{padding:16px 20px 20px}
.fd-stat-content>p:first-child{color:#bfd0dc;line-height:1.55}
.fd-stat-table-wrap{overflow:auto;border:1px solid #304c63;border-radius:13px;background:#0c1724;box-shadow:inset 0 1px #ffffff08}
.fd-stat-compact{width:100%;min-width:490px;table-layout:fixed;border-collapse:separate;border-spacing:0;font-size:12px;font-variant-numeric:tabular-nums}
.fd-stat-compact th,.fd-stat-compact td{padding:9px 7px;text-align:center;border-bottom:1px solid #293f52;white-space:nowrap}
.fd-stat-compact thead th{position:sticky;top:0;z-index:1;background:#1b3449;color:#a9c8dc;font-size:10px;font-weight:900;letter-spacing:.08em;text-transform:uppercase}
.fd-stat-compact th:first-child{position:sticky;left:0;z-index:2;width:48px;text-align:left;background:#183047;color:#a8bed0}
.fd-stat-compact thead th:first-child{z-index:3;background:#1b3449}
.fd-stat-compact td{color:#f0f6fa;font-weight:700}
.fd-stat-compact tbody tr:nth-child(even):not(.fd-stat-summary){background:#ffffff04}
.fd-stat-compact tbody tr:not(.fd-stat-summary):hover{background:#1a3548}
.fd-stat-compact .fd-stat-summary th,.fd-stat-compact .fd-stat-summary td{background:#1b3449;border-bottom-color:#36546c}
.fd-stat-compact .fd-stat-total th,.fd-stat-compact .fd-stat-total td{background:#23435a;color:#f5fffc}
.fd-stat-compact .fd-stat-avg th,.fd-stat-compact .fd-stat-avg td{background:#1b394d}
.fd-stat-compact .fd-stat-last-5 th,.fd-stat-compact .fd-stat-last-5 td{background:#183d3c;color:#cefff0;border-bottom:0}
.fd-stat-quotes{position:relative;margin-top:14px;padding:14px 16px 13px 18px;border:1px solid #36576c;border-radius:13px;background:linear-gradient(120deg,#1b354b,#142a3d)}
.fd-stat-quotes:before{content:"";position:absolute;left:0;top:12px;bottom:12px;width:3px;border-radius:3px;background:#baff35}
.fd-stat-quotes strong{display:block;color:#eaf7ff;font-size:12px}
.fd-stat-quotes p{margin:8px 0 5px;color:#c9f8e8;font-size:13px;font-weight:800;line-height:1.5}
.fd-stat-quotes small,.fd-stat-source{color:#9eb4c5;font-size:10px;line-height:1.5}
.fd-stat-source{margin:12px 2px 0}
.fd-stat-quotes-head{display:flex;align-items:baseline;justify-content:space-between;gap:10px;margin-bottom:10px}
.fd-stat-quotes-head small{color:#9eb4c5;font-size:10px}
.fd-stat-market-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,205px),1fr));gap:10px}
.fd-stat-market-card{min-width:0;padding:12px;border:1px solid #3a596f;border-radius:11px;background:linear-gradient(145deg,#10263a,#0d1c2c)}
.fd-stat-market-card h3{margin:0 0 9px;color:#dff8f0;font-size:12px;line-height:1.35}
.fd-stat-market-values{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:6px}
.fd-stat-market-values>div{min-width:0;padding:7px 6px;border-radius:8px;background:#1a354a;text-align:center}
.fd-stat-market-values small{display:block;color:#9eb9c9;font-size:9px;font-weight:800;letter-spacing:.04em;text-transform:uppercase}
.fd-stat-market-values b{display:block;margin-top:3px;color:#f4fbff;font-size:14px;font-variant-numeric:tabular-nums;white-space:nowrap}
.fd-stat-market-values .fd-stat-projection b{color:#baff35}
.fd-stat-market-source{display:block;margin-top:8px;color:#9eb4c5;font-size:9px;line-height:1.4}
.fd-stat-market-empty{color:#aab9c5!important}
@media(max-width:540px){.fd-stat-overlay{align-items:flex-end;padding:0}.fd-stat-dialog{width:100%;max-height:92dvh;border-radius:20px 20px 0 0;border-bottom:0}.fd-stat-dialog header{padding:13px 14px;gap:9px}.fd-stat-identity{gap:10px}.fd-stat-headshot{width:50px;height:50px;flex-basis:50px}.fd-stat-dialog button{padding:8px 10px;font-size:11px}.fd-stat-content{padding:12px 12px 18px}.fd-stat-compact{min-width:470px;font-size:11px}.fd-stat-compact th,.fd-stat-compact td{padding:8px 5px}.fd-stat-compact th:first-child{width:39px}}
`;document.head.appendChild(style);
function findName(el){const explicit=el.closest('[data-fd-player]');if(explicit)return explicit.dataset.fdPlayer;const t=el.textContent.trim();return t.replace(/\\s+/g,' ')}
async function openPlayer(name){
 const previous=document.querySelector('.fd-stat-overlay');if(previous)previous.remove();
 const overlay=document.createElement('div');overlay.className='fd-stat-overlay';overlay.innerHTML='<section class="fd-stat-dialog" role="dialog" aria-modal="true" aria-label="Player season statistics"><header><div class="fd-stat-identity"><div class="fd-stat-title"><span class="fd-stat-kicker">Player snapshot</span><h2>'+esc(name)+'</h2><p>Verified ESPN game logs · 2026 season</p></div></div><button type="button" aria-label="Close player stats">Close ✕</button></header><div class="fd-stat-content"><p>Loading verified game log…</p></div></section>';
 document.body.appendChild(overlay);const close=()=>{overlay.remove();document.removeEventListener('keydown',onKey)};const onKey=e=>{if(e.key==='Escape')close()};document.addEventListener('keydown',onKey);overlay.querySelector('button').focus();overlay.querySelector('button').onclick=close;overlay.addEventListener('click',e=>{if(e.target===overlay)close()});
 const body=overlay.querySelector('.fd-stat-content');
 try{const [data,odds,projections]=await Promise.all([load(),loadOdds(),loadProjections()]);if(!overlay.isConnected)return;const key=norm(name),matches=Object.entries(data.by_name||{}).filter(([k])=>k.startsWith(key+'|'));if(!matches.length){body.innerHTML='<p>No verified completed-game statistics are available for this player in the published feed.</p>';return}
 const athleteId=matches.map(([,v])=>v.athlete_id).find(id=>/^[0-9]+$/.test(String(id||'')));
 if(athleteId){const h=overlay.querySelector('.fd-stat-identity');const img=document.createElement('img');img.className='fd-stat-headshot';img.alt=name+' headshot';img.loading='lazy';img.referrerPolicy='no-referrer';img.src='https://a.espncdn.com/i/headshots/nfl/players/full/'+athleteId+'.png';img.onerror=()=>{img.style.display='none'};h.prepend(img)}
 const order=['player_pass_yds','player_pass_completions','player_pass_attempts','player_rush_yds','player_rush_attempts','player_rec_yds','player_receptions'];
 const cols=matches.map(([k,v])=>({market:k.slice(key.length+1),games:(v.games||[]).filter(g=>g.actual!==null&&Number.isFinite(Number(g.actual)))})).filter(x=>x.games.length).sort((a,b)=>order.indexOf(a.market)-order.indexOf(b.market));
 const weeks=[...new Set(cols.flatMap(x=>x.games.map(g=>Number(g.week))))].sort((a,b)=>a-b);
 const short={player_pass_yds:'Pass',player_pass_completions:'Cmp',player_pass_attempts:'Att',player_rush_yds:'Rush',player_rush_attempts:'Car',player_rec_yds:'RecY',player_receptions:'Rec'};
 const row=(label,fn)=>'<tr'+(['Total','Avg','Last 5'].includes(label)?' class="fd-stat-summary fd-stat-'+(label==='Last 5'?'last-5':label.toLowerCase())+'"':'')+'><th>'+esc(label)+'</th>'+cols.map(x=>'<td>'+esc(fn(x))+'</td>').join('')+'</tr>';
 const average=gs=>gs.length?(gs.reduce((a,g)=>a+Number(g.actual),0)/gs.length).toFixed(1):'—';
 const quotes=cols.map(x=>({market:x.market,q:currentQuote(odds.rows,name,x.market)})).filter(x=>x.q);
 body.innerHTML='<div class="fd-stat-table-wrap"><table class="fd-stat-compact"><thead><tr><th>Week</th>'+cols.map(x=>'<th title="'+esc(labels[x.market]||x.market)+'">'+esc(short[x.market]||x.market)+'</th>').join('')+'</tr></thead><tbody>'+weeks.map(w=>row(''+w,x=>{const g=x.games.find(g=>Number(g.week)===w);return g?Number(g.actual).toFixed(0):'—'})).join('')+row('Total',x=>x.games.reduce((a,g)=>a+Number(g.actual),0).toFixed(0))+row('Avg',x=>average(x.games))+row('Last 5',x=>average(x.games.slice(-5)))+'</tbody></table></div>'+(quotes.length?'<div class="fd-stat-quotes"><div class="fd-stat-quotes-head"><strong>Upcoming DraftKings lines</strong><small>Line compared with published projection</small></div><div class="fd-stat-market-grid">'+quotes.map(x=>{const projection=findPlayerProjection(projections,name,x.market,x.q.commence_time),dk=Number(x.q.line),difference=projection?projection.value-dk:null;return '<article class="fd-stat-market-card"><h3>'+esc(labels[x.market]||short[x.market]||x.market)+'</h3><div class="fd-stat-market-values"><div><small>DK line</small><b>'+dk.toFixed(1)+'</b></div><div class="fd-stat-projection"><small>Projection</small><b class="'+(projection?'':'fd-stat-market-empty')+'">'+(projection?projection.value.toFixed(1):'—')+'</b></div><div><small>Proj. − line</small><b class="'+(difference===null?'fd-stat-market-empty':'')+'">'+(difference===null?'—':(difference>0?'+':'')+difference.toFixed(1))+'</b></div></div><small class="fd-stat-market-source">'+(projection?(projection.kind==='Research estimate'?'Research estimate · experimental':'FOURTHDOWN model projection · not a betting recommendation'):'No published projection for this player and metric.')+'</small></article>'}).join('')+'</div><small>Upcoming quotes only. Projections are estimates, not betting recommendations.</small></div>':'')+'<p class="fd-stat-source">Source: ESPN verified completed games. A dash means no available stat.</p>';

 }catch(e){body.innerHTML='<p>Player game statistics could not be loaded right now.</p>'}
}
const selectors=['.fd-mobile-prop-name strong','.fd-spotlight-top strong','.bet-card h3','.prop-mobile-card > strong','.fd-live-prop-player strong','.fd-matchup-card h3'];
document.addEventListener('click',e=>{const el=e.target.closest(selectors.join(','));if(!el||el.closest('.fd-stat-dialog'))return;const name=findName(el);if(!name)return;e.preventDefault();openPlayer(name)});
document.addEventListener('keydown',e=>{if(e.key!=='Enter'&&e.key!==' ')return;const el=e.target.closest(selectors.join(','));if(!el)return;e.preventDefault();openPlayer(findName(el))});
function mark(){document.querySelectorAll(selectors.join(',')).forEach(el=>{if(!el.classList.contains('fd-stat-name')){el.classList.add('fd-stat-name');el.setAttribute('role','button');el.setAttribute('tabindex','0');el.setAttribute('title','View verified player game stats')}})}
new MutationObserver(()=>mark()).observe(document.body,{childList:true,subtree:true});mark();
})();