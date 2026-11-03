/* FOURTHDOWN defensive matchup intelligence: presentation only. Never writes projections, odds or picks. */
(()=>{'use strict';
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const allowed=new Set(['QB','RB','WR','TE']);
const metric={QB:'passing_yards',RB:'rushing_yards',WR:'receiving_yards',TE:'receiving_yards'};
const rankLabel=r=>r<=8?'Favorable':r>=25?'Unfavorable':'Neutral';
function card(record){
 if(!record||!allowed.has(record.position)||record.status!=='verified'||!Number.isInteger(record.games)||record.games<3)return '<p class="fd-dmi-unavailable">Defensive matchup data unavailable or insufficient.</p>';
 const m=record.metrics?.[metric[record.position]];
 if(!m||![m.per_game,m.league_average,m.rank_most_allowed].every(Number.isFinite)||m.league_average<=0||m.rank_most_allowed<1||m.rank_most_allowed>32)return '<p class="fd-dmi-unavailable">Defensive matchup data unavailable or insufficient.</p>';
 const pct=(m.per_game/m.league_average-1)*100,label=rankLabel(m.rank_most_allowed);
 return '<section class="fd-dmi-card"><div class="fd-dmi-head"><strong>'+esc(record.opponent)+' defense vs '+esc(record.position)+'</strong><span>'+label+'</span></div><div class="fd-dmi-numbers"><div><b>'+m.per_game.toFixed(1)+'</b><small>Yards allowed/game</small></div><div><b>#'+m.rank_most_allowed+'</b><small>Most allowed</small></div><div><b>'+(pct>=0?'+':'')+pct.toFixed(0)+'%</b><small>Vs NFL average</small></div></div><p>'+esc(record.opponent)+' allows '+m.per_game.toFixed(1)+' '+(record.position==='RB'?'rushing':'receiving')+' yards per game to '+esc(record.position)+'s, '+Math.abs(pct).toFixed(0)+'% '+(pct>=0?'above':'below')+' the league average. This is contextual matchup information, not a model adjustment or a betting recommendation.</p><small>Through '+esc(record.through_week)+' · '+record.games+' games · Source: '+esc(record.source)+' · No projection adjustment</small></section>';
}
window.FourthdownMatchupIntelligence=Object.freeze({card,rankLabel});
})();
