const assert = require('assert');
const fs = require('fs');
global.window = global;
global.fetch = async () => ({ok:true,json:async()=>JSON.parse(fs.readFileSync('assets/dk-markets.json'))});
require('../assets/dk-lines.js');
(async()=>{
 const contract=await FDDraftKings.ready;
 const now=Date.parse('2026-11-08T16:00:00Z');
 const kickoff='2026-11-08T18:00:00Z';
 const player={player:'Alex Smith',player_id:'one',team:'GB',opponent:'CHI',market_key:'player_rec_yds',kickoff_utc:kickoff};
 const quote={player:'Alex Smith Sr.',home_team:'Green Bay Packers',away_team:'Chicago Bears',market_key:'player_receiving_yards',commence_time:kickoff,last_update:'2026-11-08T15:00:00Z',line:43.5};
 assert.strictEqual(FDDraftKings.create(contract,[quote],now,[player]).find(player,kickoff).line,43.5);
 const rival={...player,player:'Alex Smith Jr.',player_id:'two',team:'CHI',opponent:'GB'};
 assert.strictEqual(FDDraftKings.create(contract,[quote],now,[player,rival]).find(player,kickoff),null);
 console.log('Verified suffix match and ambiguous same-name rejection');
})().catch(error=>{console.error(error);process.exitCode=1});
