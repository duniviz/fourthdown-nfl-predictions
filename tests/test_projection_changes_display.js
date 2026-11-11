const fs=require('fs'),vm=require('vm'),assert=require('assert/strict');
const data={schema_version:1,players:{
 'G|1|passing_yards':[{at:'2026-11-09T20:00:00Z',value:200},{at:'2026-11-10T20:00:00Z',value:220}],
 'G|2|receiving_yards':[{at:'2026-11-09T20:00:00Z',value:200},{at:'2026-11-10T20:00:00Z',value:200.1}],
 'G|3|receptions':[{at:'2026-11-09T20:00:00Z',value:2.2},{at:'2026-11-10T20:00:00Z',value:3}],
 'G|4|receptions':[{at:'2026-11-09T20:00:00Z',value:2},{at:'2026-11-10T20:00:00Z',value:3}],
 'G|5|carries':[{at:'2026-11-10T20:00:00Z',value:8}]
},games:{
 G:[{at:'2026-11-09T20:00:00Z',home:20,away:17},{at:'2026-11-10T20:00:00Z',home:21,away:18}],
 H:[{at:'2026-11-09T20:00:00Z',home:20,away:17},{at:'2026-11-10T20:00:00Z',home:20.5,away:17.5}]
}};
const context={window:{},fetch:async()=>({ok:true,json:async()=>data}),Date,Number,String,Math};
vm.runInNewContext(fs.readFileSync('assets/projection-changes.js','utf8'),context);
(async()=>{await context.window.FDProjectionChanges.ready;const d=context.window.FDProjectionChanges;
 assert.match(d.player({game_id:'G',player_id:'1',stat_key:'passing_yards',projection:220}),/200.0 → 220.0/);
 assert.equal(d.player({game_id:'G',player_id:'1',stat_key:'passing_yards',projection:221}),'');
 assert.equal(d.player({game_id:'G',player_id:'2',stat_key:'receiving_yards',projection:200.1}),'','A 0.1-yard movement should be hidden');
 assert.equal(d.player({game_id:'G',player_id:'3',stat_key:'receptions',projection:3}),'','A sub-reception movement should be hidden');
 assert.match(d.player({game_id:'G',player_id:'4',stat_key:'receptions',projection:3}),/2.0 → 3.0/);
 assert.equal(d.player({game_id:'G',player_id:'5',stat_key:'carries',projection:8}),'','A first snapshot is not a change');
 assert.match(d.game({game_id:'G',home:'BUF',away:'MIN',projected_home_score:21,projected_away_score:18}),/MIN 17.0 · BUF 20.0 → MIN 18.0 · BUF 21.0/);
 assert.equal(d.game({game_id:'H',home:'BUF',away:'MIN',projected_home_score:20.5,projected_away_score:17.5}),'','Sub-point score movements should be hidden');
 console.log('Projection change display passed');
})().catch(e=>{console.error(e);process.exit(1)});
