'use strict';
const assert = require('node:assert/strict');
const view = require('../assets/fd-final-game');
const game = {date:'2026-11-22T18:00:00Z', away:{abbr:'ARI',score:7}, home:{abbr:'KC',score:34}};
const lock = {game_id:'2026_11_ARI_KC', away:'ARI', home:'KC', kickoff_utc:'2026-11-22T18:00:00Z',
  forecast_at_utc:'2026-11-22T17:28:22Z', captured_at_utc:'2026-11-22T17:30:02Z', lock_status:'official',
  projected_away_score:16, projected_home_score:28.8,
  game_ml_shadow:{markets:{game_total:{candidate:43.91},game_margin_home:{candidate:10.23}}}};
const html = view.render(game, [lock]);
assert.match(html, /ARI 16\.0 · KC 28\.8/);
assert.match(html, /ARI 16\.8 · KC 27\.1/);
assert.match(html, /SAVED RESEARCH ESTIMATE/);
assert.match(html, /<small>KC<\/small>34/);
assert.match(view.render(game, []), /No verified pregame forecast/);
assert.match(view.render(game, [{...lock,captured_at_utc:'2026-11-22T18:00:00Z'}]), /No verified pregame forecast/);
assert.match(view.render(game, [{...lock,forecast_at_utc:'2026-11-22T17:31:00Z'}]), /No verified pregame forecast/);
assert.match(view.render(game, [lock,lock]), /No verified pregame forecast/);
assert.match(view.render(game, [{...lock,game_ml_shadow:{markets:{game_total:{candidate:null},game_margin_home:{candidate:10}}}}]), /No complete pregame ML estimate/);
assert.equal(view.savedLock({...game,away:{abbr:'NYJ'}},[lock]), null);
const atsGame = {date:'2026-11-22T18:00:00Z',away:{abbr:'TB',score:21},home:{abbr:'DET',score:31}};
const atsLock = {...lock,away:'TB',home:'DET',projected_away_score:18.9,projected_home_score:21.8,
  projected_margin_home:2.86,dk_home_spread:-3.5,dk_total:48.5,dk_at_utc:'2026-11-22T17:29:36Z',
  game_ml_shadow:{markets:{game_total:{candidate:44.71},game_margin_home:{candidate:5.15}}}};
const atsHtml = view.render(atsGame,[atsLock]);
assert.match(atsHtml,/Saved DK spread: DET -3\.5/);
assert.match(atsHtml,/ATS: <strong>TB \+3\.5 · MISS<\/strong>/);
assert.match(atsHtml,/ATS: <strong>DET -3\.5 · HIT<\/strong>/);
assert.match(atsHtml,/Total: 48\.5/);
assert.equal((atsHtml.match(/O\/U: <strong>UNDER 48\.5 · MISS<\/strong>/g)||[]).length,2);
assert.deepEqual(view.ats(atsGame,atsLock,3.5),{pick:'No ATS lean',result:null});
assert.equal(view.ats({...atsGame,home:{abbr:'DET',score:24},away:{abbr:'TB',score:21}}, {...atsLock,dk_home_spread:-3}, 4).result,'PUSH');
assert.equal(view.ats(atsGame,{...atsLock,dk_at_utc:'2026-11-22T18:01:00Z'},5),null);
assert.equal(view.ats(atsGame,{...atsLock,dk_home_spread:null},5),null);
assert.equal(view.ats({...atsGame,home:{abbr:'DET',score:null}},atsLock,5).result,null);
assert.equal(view.totalPick(atsGame,{...atsLock,dk_total:52},55).result,'PUSH');
assert.deepEqual(view.totalPick(atsGame,atsLock,48.5),{pick:'No total lean',result:null});
assert.equal(view.totalPick(atsGame,{...atsLock,dk_total_observed_at_utc:'2026-11-22T18:01:00Z'},55),null);
assert.equal(view.totalPick(atsGame,{...atsLock,dk_total:null},55),null);
assert.match(view.render(atsGame,[{...atsLock,dk_home_spread:null}]),/Saved DK spread: Unavailable/);
console.log('Final game saved-projection checks passed');
