const assert = require('assert');
const fs = require('fs');
const {reportCardModel} = require('../assets/fd-insights.js');
const {ledgerGap, recordedHits} = require('../assets/fd-prop-board.js');
const {scoreboardStatus} = require('../slate-pulse.js');
const {topPicksHeading} = require('../top-picks.js');
const {missingSimulationMessage} = require('../assets/fd-five-visuals.js');

const performance = JSON.parse(fs.readFileSync('data/weekly-model-performance.json', 'utf8'));
const official = JSON.parse(fs.readFileSync('data/game-official-results.json', 'utf8'));
const players = JSON.parse(fs.readFileSync('data/player-results.json', 'utf8'));

const card = reportCardModel(performance, official, players);
assert.strictEqual(card.source, 'official');
assert.strictEqual(card.latest.completed_games, 12);
assert.match(card.headline, /12 completed games on the verified score ledger/);
assert.match(card.footnote, /only included 2 final games/);
assert.strictEqual(card.latest.game_metrics.home_margin.samples, 12);
assert.ok(Math.abs(card.latest.game_metrics.home_margin.mae - 10.96) < 0.02);
assert.ok(Math.abs(card.latest.game_metrics.total.mae - 8.79) < 0.02);

const olderOfficial = {...official, generated_at_utc: '2026-11-01T00:00:00Z'};
const kept = reportCardModel(performance, olderOfficial, players);
assert.strictEqual(kept.source, 'snapshot');
assert.strictEqual(kept.latest.completed_games, 2);

const gap = ledgerGap(players.rows, official.rows);
assert.strictEqual(gap.propsGraded, 907);
assert.strictEqual(gap.historyGraded, 838);
assert.strictEqual(gap.outside, 69);
assert.match(gap.propsNote, /JAX at BAL/);
assert.match(gap.propsNote, /CIN at ATL/);
assert.match(gap.propsNote, /History only counts games with a verified final score/);
assert.match(gap.historyNote, /do not have a game-score row/);
assert.deepStrictEqual(recordedHits([
  {game_id: '2026_09_A_B', recommendation_result: 'hit'},
  {game_id: '2026_10_C_D', recommendation_result: 'miss'},
  {game_id: '2026_10_E_F', recommendation_result: 'push'},
  {game_id: '2026_08_G_H', recommendation_result: 'not_available'}
]), {hits: 1, graded: 3, window: '2026 Weeks 9–10'});
const aligned = ledgerGap(
  [{game_id: 'g', recommendation_result: 'hit'}],
  [{game_id: 'g'}]
);
assert.strictEqual(aligned.outside, 0);
assert.strictEqual(aligned.propsNote, '');

assert.match(scoreboardStatus({live: 0, upcoming: 2, finals: 12, feed: 'ok'}), /No games in progress · Showing the next kickoffs/);
assert.match(scoreboardStatus({live: 0, upcoming: 0, finals: 12, feed: 'ok'}), /No games in progress · Latest finals shown/);
assert.match(scoreboardStatus({live: 1, upcoming: 0, finals: 12, feed: 'ok'}), /1 game in progress/);
assert.match(scoreboardStatus({live: 0, upcoming: 0, finals: 0, feed: 'failed', forecastFallback: true}), /Live scores are unavailable/);
assert.match(scoreboardStatus({live: 0, upcoming: 0, finals: 0, feed: 'loading'}), /Loading live games/);
assert.doesNotMatch(scoreboardStatus({live: 0, upcoming: 0, finals: 4, feed: 'stale'}), /unavailable/);

assert.deepStrictEqual(topPicksHeading(3), {
  title: 'Top Picks',
  note: '3 qualifying picks this week. A pick needs a matching simulation above 50%, so fewer than five can qualify.'
});
assert.strictEqual(topPicksHeading(5).title, 'Top 5 Picks');
assert.strictEqual(topPicksHeading(0).note, '');

assert.match(missingSimulationMessage({state: 'post', status: 'Final'}), /No win simulation was saved for this finished game/);
assert.match(missingSimulationMessage({state: 'post', status: 'Final'}), /archived forecast and grade/);
assert.doesNotMatch(missingSimulationMessage({state: 'pre', status: 'Scheduled'}), /finished game/);

console.log('fan review unit tests passed');
