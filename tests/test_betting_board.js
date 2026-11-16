const assert = require('assert');
const {confidenceWords, gameEdgeRows, propEdgeRows, gradeRate, latestWeek, propSimulationRate, findPropSimulation} = require('../assets/fd-betting-board.js');

assert.strictEqual(confidenceWords(70), 'Strong lean');
assert.strictEqual(confidenceWords(58), 'Lean');
assert.strictEqual(confidenceWords(52.4), 'Slight lean');
assert.strictEqual(confidenceWords(40), 'Below break-even');
assert.strictEqual(confidenceWords(null), 'No simulation');

const rows = gameEdgeRows({
  home: 'BAL', away: 'LAC',
  projected_home_score: 18.5, projected_away_score: 15.6,
  game_ml_shadow: {markets: {game_margin_home: {candidate: 0.82}, game_total: {candidate: 38.1}}}
}, {home_spread: -4.5, total: 38.5}, {home_win_pct: 56.7, away_win_pct: 40.1, over_cover_pct: 38.6, under_cover_pct: 61.4, home_cover_pct: 45.3, away_cover_pct: 54.7});
const total = rows.find(row => row.kind === 'Total');
assert.strictEqual(total.model, '34.1');
assert.strictEqual(total.ml, '38.1');
assert.strictEqual(total.dk, '38.5');
assert.ok(Math.abs(total.edge - 4.4) < 0.05);
assert.strictEqual(total.pick, 'Under 38.5');
assert.strictEqual(total.tone, 'pos');
assert.strictEqual(total.direction, 'under');
const spread = rows.find(row => row.kind === 'Spread');
assert.strictEqual(spread.ml, 'BAL by 0.8');
assert.match(spread.pick, /LAC \+4\.5/);

const props = propEdgeRows([
  {player: 'Derrick Henry', team: 'BAL', market: 'Rushing yards', projection: 69.1, player_ml_shadow: {candidate: 65.3, active: false}}
], [
  {player: 'Derrick Henry', market_key: 'player_rushing_yards', line: 80.5, home_team: 'Baltimore Ravens', away_team: 'Los Angeles Chargers'}
]);
assert.strictEqual(props.length, 1);
assert.strictEqual(props[0].model, '69.1');
assert.strictEqual(props[0].ml, '65.3');
assert.strictEqual(props[0].dk, '80.5');
assert.ok(props[0].edge > 11);
assert.strictEqual(props[0].tone, 'pos');
assert.strictEqual(props[0].direction, 'under');
assert.strictEqual(props[0].pct, null);
const simRows=[{game_id:'2026_10_LAC_BAL',player:'Derrick Henry',stat_key:'rushing_yards',sorted_draws:Array.from({length:100},(_,i)=>i)}];
const matched = findPropSimulation({game_id:'2026_10_LAC_BAL',player:'Derrick Henry'},'player_rushing_yards',simRows);
assert.strictEqual(propSimulationRate(matched,80.5,'under'),81);
assert.strictEqual(propSimulationRate(matched,80.5,'over'),19);
assert.strictEqual(findPropSimulation({game_id:'2026_11_LAC_BAL',player:'Derrick Henry'},'player_rushing_yards',simRows),null);

assert.deepStrictEqual(gradeRate([{winner_result: 'hit'}, {winner_result: 'miss'}, {winner_result: 'push'}], 'winner_result'), {hits: 1, n: 2, pct: 50});
assert.deepStrictEqual(latestWeek([{season: 2026, week: 9}, {season: 2026, week: 10}]), {season: 2026, week: 10});

const fs = require('fs');
const home = fs.readFileSync('index.html', 'utf8');
assert.match(home, /id="fd-betting-board"/);
assert.match(home, /function fdMlGlance/);
assert.match(home, /Official pick · current model/);
assert.match(home, /ML projection, research/);
const bets = fs.readFileSync('bets.html', 'utf8');
assert.match(bets, /ML projection, research/);
assert.doesNotMatch(bets, /<span>ML projection<\/span>/);
const css = fs.readFileSync('assets/fd-betting-board.css', 'utf8');
assert.match(css, /#05070d|#ff5a1f|#3dffb0|#ff5b78|#ffc857/);
assert.match(css, /Barlow Condensed/);
assert.match(css, /Source Sans 3/);
assert.match(css, /max-width:640px/);
assert.match(css, /prefers-reduced-motion:reduce/);
assert.match(css, /font-display:swap/);
assert.match(css, /FD Barlow Fallback/);
assert.match(css, /barlow-800\\.woff2/);
assert.match(css, /source-400\\.woff2/);
assert.match(home, /preload[^>]+barlow-800\\.woff2/);
assert.match(bets, /preload[^>]+source-400\\.woff2/);
const polish = fs.readFileSync('assets/fd-betting-board-polish.css', 'utf8');
assert.match(polish, /fd-bb-result-chip/);
assert.match(polish, /fd-prop-edge-stat/);
assert.match(polish, /fd-more-menu/);
assert.match(bets, /fd-props-board/);
assert.match(bets, /fd-betting-board-polish.css/);
assert.match(bets, /<details class="fd-about-data"><summary>About this data<\/summary><div class="bet-stats"/);
const shell=fs.readFileSync('assets/fd2-shell.js','utf8');
assert.doesNotMatch(shell, /moreCurrent\(\) \? ' open' : ''/);
console.log('betting board unit tests passed');
