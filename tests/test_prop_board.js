const assert = require('assert');
const board = require('../assets/fd-prop-board.js');
const yards = {market: 'Receiving yards', stat_key: 'receiving_yards'};
const catches = {market: 'Receptions', stat_key: 'receptions'};
const rushes = {market: 'Rush attempts', stat_key: 'carries'};
const completions = {market: 'Pass completions', stat_key: 'completions'};
const td = {market: 'Anytime TD', stat_key: 'anytime_td'};
assert.strictEqual(board.matchesTab(yards, 'yards'), true);
assert.strictEqual(board.matchesTab(catches, 'yards'), false);
assert.strictEqual(board.matchesTab(rushes, 'yards'), false);
assert.strictEqual(board.matchesTab(completions, 'yards'), false);
assert.strictEqual(board.matchesTab(td, 'yards'), false);
assert.strictEqual(board.matchesTab(catches, 'receptions'), true);
assert.strictEqual(board.matchesTab(rushes, 'rushes'), true);
assert.strictEqual(board.matchesTab(completions, 'completions'), true);
assert.strictEqual(board.matchesTab({market: 'Completions'}, 'completions'), true);
assert.deepStrictEqual(board.marketOptions('yards').map(option => option.value), ['all', 'Passing yards', 'Rushing yards', 'Receiving yards']);
assert.strictEqual(board.countKey('receptions'), 'player_receptions');
assert.strictEqual(board.countKey('yards'), '');
const upcoming = board.gameTag('2026_10_LAC_BAL', '2026-11-17T01:15:00Z', Date.parse('2026-11-16T18:00:00Z'));
assert.strictEqual(upcoming.text, 'Week 10 · Mon, Nov 16');
assert.strictEqual(upcoming.final, false);
const done = board.gameTag('2026_10_WAS_NYG', '2026-11-13T01:15:00Z', Date.parse('2026-11-16T18:00:00Z'));
assert.strictEqual(done.text, 'Week 10 · Thu, Nov 12');
assert.strictEqual(done.final, true);
const hits = board.recordedHits([
  {game_id: '2026_09_A_B', recommendation_result: 'hit'},
  {game_id: '2026_10_C_D', recommendation_result: 'miss'},
  {game_id: '2026_10_E_F', recommendation_result: 'push'},
  {game_id: '2026_08_G_H', recommendation_result: 'not_available'}
]);
assert.deepStrictEqual(hits, {hits: 1, graded: 3, window: '2026 Weeks 9–10'});
console.log('prop board tests passed');
