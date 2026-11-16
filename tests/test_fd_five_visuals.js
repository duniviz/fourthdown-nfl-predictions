"use strict";
const assert=require("node:assert/strict");
const visuals=require("../assets/fd-five-visuals.js");

const game={away:{abbr:"PIT"},home:{abbr:"CIN"},date:"2026-11-16T01:20:00Z"};
const live={games:[{game_id:"2026_10_PIT_CIN",away:"PIT",home:"CIN",kickoff_utc:"2026-11-16T01:20:00+00:00",projected_away_score:23.4,projected_home_score:25.9}]};
const sim={games:[{game_id:"2026_10_PIT_CIN",simulations:10000,away_win_pct:42.8,home_win_pct:57.2}]};
assert.equal(visuals.gameSimulation(game,live,sim).homePct,57.2);
assert.equal(visuals.gameSimulation(game,live,{games:[]}),null,"No made-up confidence if no matching simulation");
assert.equal(visuals.gameSimulation(game,{games:[]},sim),null,"No made-up forecast if game is missing");
assert.equal(visuals.gameSimulation(game,live,{games:[{...sim.games[0],home_win_pct:999}]}),null,"Reject invalid probability");
assert.equal(visuals.gameSimulation({...game,date:"2026-11-23T01:20:00Z"},live,sim),null,"Do not use past slate's model");

const rows=[
 {captured_at_utc:"2026-11-15T21:00:00Z",spread:-3.5,total:44.5},
 {captured_at_utc:"2026-11-15T19:00:00Z",spread:-2.5,total:45.5},
 {captured_at_utc:"invalid",spread:10,total:100}
];
const p=visuals.linePoints(rows,"spread");
assert.deepEqual(p.map(x=>x.v),[-2.5,-3.5]);
assert.equal(visuals.sparkline([]),"","No graph if no saved movements");
assert.match(visuals.sparkline(p),/<svg/);
assert.match(visuals.historyChart(p.map(x=>({captured_at_utc:new Date(x.t).toISOString(),spread:x.v})),"spread","Spread",v=>String(v)),/First saved/);
assert.match(visuals.historyChart([],"spread","Spread",v=>String(v)),/No verified pregame quotes/);
console.log("Five visual upgrades: matching simulation, no fabricated percentages, saved line trends validated");
