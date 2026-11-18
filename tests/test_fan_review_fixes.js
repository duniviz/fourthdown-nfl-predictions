const assert = require('assert');
const {reportCardModel} = require('../assets/fd-insights.js');
const {ledgerGap, recordedHits} = require('../assets/fd-prop-board.js');
const {scoreboardStatus} = require('../slate-pulse.js');
const {topPicksHeading} = require('../top-picks.js');
const {missingSimulationMessage} = require('../assets/fd-five-visuals.js');

// Fixed examples keep this test independent of the changing live score ledger.
const performance = {generated_at_utc:'2026-11-10T00:00:00Z', weekly_reports:[
  {season:2026, week:10, status:'graded_observed_only', completed_games:1}
]};
const official = {generated_at_utc:'2026-11-11T00:00:00Z', rows:[
  {game_id:'2026_10_A_B',season:2026,week:10,home_score:24,away_score:20,projected_margin_home:3,projected_total:45},
  {game_id:'2026_10_C_D',season:2026,week:10,home_score:20,away_score:17,projected_margin_home:1,projected_total:35},
  {game_id:'2026_10_E_F',season:2026,week:10,home_score:28,away_score:14,projected_margin_home:17,projected_total:39}
]};
const players = {generated_at_utc:'2026-11-11T00:00:00Z',rows:[]};
const card = reportCardModel(performance, official, players);
assert.strictEqual(card.source, 'official');
assert.strictEqual(card.latest.completed_games, 3);
assert.match(card.headline, /3 completed games on the verified score ledger/);
assert.match(card.footnote, /only included 1 final game/);
assert.strictEqual(card.latest.game_metrics.home_margin.samples, 3);
assert.strictEqual(card.latest.game_metrics.home_margin.mae, 2);
assert.strictEqual(card.latest.game_metrics.total.mae, 2);

const olderOfficial = {...official, generated_at_utc: '2026-11-01T00:00:00Z'};
const kept = reportCardModel(performance, olderOfficial, players);
assert.strictEqual(kept.source, 'snapshot');
assert.strictEqual(kept.latest.completed_games, 1);

const gap = ledgerGap([
  {game_id:'2026_10_A_B', recommendation_result:'hit'},
  {game_id:'2026_10_A_B', recommendation_result:'miss'},
  {game_id:'2026_10_X_Y', recommendation_result:'hit'},
  {game_id:'2026_10_X_Y', recommendation_result:'push'}
], official.rows);
assert.strictEqual(gap.propsGraded, 4);
assert.strictEqual(gap.historyGraded, 2);
assert.strictEqual(gap.outside, 2);
assert.match(gap.propsNote, /X at Y/);
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
