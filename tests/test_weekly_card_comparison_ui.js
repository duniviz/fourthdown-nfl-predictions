const assert=require('assert');
const root={innerHTML:'',querySelector(){return {addEventListener(){}};}};
global.document={getElementById(){return root;}};
global.fetch=async()=>({ok:true,json:async()=>({weeks:[{season:2026,week:11,markets:[{market:'game_total',label:'Game total',winner:'regular',samples:1,regular_mae:14.43,ml_mae:18.43,regular_wins:1,ml_wins:0,ties:0,regular_hits:{hit_pct:100,hits:1,misses:0,pushes:0,unavailable:0},ml_hits:{hit_pct:0,hits:0,misses:1,pushes:0,unavailable:0},details:[{label:'IND @ HOU',actual:29,dk_line:44.5,regular:43.43,ml:47.43,regular_pick_result:'hit',ml_pick_result:'miss',evidence_source:'recovered_pregame_observation',winner:'regular'}]}]}]})});
require('../assets/fd-weekly-h2h.js');
setTimeout(()=>{assert(root.innerHTML.includes('Regular was closer'));assert(root.innerHTML.includes('IND @ HOU'));assert(root.innerHTML.includes('29.0'));assert(root.innerHTML.includes('Week 11'));assert(root.innerHTML.includes('100.0%'));assert(root.innerHTML.includes('0.0%'));assert(root.innerHTML.includes('44.5'));assert(root.innerHTML.includes('Recovered pregame'));assert(root.innerHTML.includes('43.4 · Hit'));assert(root.innerHTML.includes('47.4 · Miss'));assert(root.innerHTML.includes('Projection ran 14.4 points too high on average'));assert(root.innerHTML.includes('Under</b><span>100.0% hit rate · 1 hits, 0 misses'));assert(root.innerHTML.includes('Over</b><span>0.0% hit rate · 0 hits, 1 misses'));assert(root.innerHTML.includes('Under 2</b><span>100.0% hit rate · 1 hits, 0 misses'));assert(root.innerHTML.includes('2 to under 5</b><span>0.0% hit rate · 0 hits, 1 misses'));console.log('Weekly card comparison UI passed');},0);



