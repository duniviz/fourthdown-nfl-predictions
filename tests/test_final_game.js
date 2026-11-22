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
console.log('Final game saved-projection checks passed');
