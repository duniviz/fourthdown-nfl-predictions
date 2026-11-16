const assert = require('assert');
const fs = require('fs');
const {freshnessModel, FD_STALE_LINE_HOURS} = require('../assets/feed-freshness.js');
const {topPicksTabsCollapsed} = require('../top-picks.js');

const now = Date.parse('2026-11-16T14:00:00Z');
const fresh = freshnessModel('2026-11-16T04:00:00Z', '2026-11-16T08:00:00Z', now);
assert.strictEqual(fresh.text, 'Updated 10h ago · DK lines 6h old');
assert.strictEqual(fresh.stale, false);
const minutes = freshnessModel('2026-11-16T13:40:00Z', '2026-11-16T13:20:00Z', now);
assert.strictEqual(minutes.text, 'Updated 20m ago · DK lines 40m old');
const stale = freshnessModel('2026-11-15T04:00:00Z', '2026-11-14T04:00:00Z', now);
assert.strictEqual(stale.stale, true);
assert.match(stale.text, /DK lines 58h old/);
assert.ok(FD_STALE_LINE_HOURS >= 12);

const same = {kind: 'Winner', pick: 'BAL to win'};
assert.strictEqual(topPicksTabsCollapsed({
  players: [same],
  scoring: [same],
  blended: [same]
}), true);
assert.strictEqual(topPicksTabsCollapsed({
  players: [],
  scoring: [same],
  blended: [same]
}), true);
assert.strictEqual(topPicksTabsCollapsed({
  players: [{kind: 'Passing yards', pick: 'A'}],
  scoring: [same],
  blended: [same]
}), false);
assert.strictEqual(topPicksTabsCollapsed({players: [], scoring: [], blended: []}), false);

const home = fs.readFileSync('index.html', 'utf8');
assert.doesNotMatch(home, /<a href="#(?:parlays|picks|tracking|confidence-pool)"/);
assert.doesNotMatch(home, /Pipeline Health \/ Refresh Status/);
assert.doesNotMatch(home, /With v2 picks/);
assert.doesNotMatch(home, /id="fd-mini-coverage"/);
assert.match(home, /id="fd-freshness-badge"/);
assert.match(home, /52\.4%/);
assert.match(home, /pipeline-health\.html/);
assert.match(home, /With model picks/);
assert.match(home, /fd-card-detail/);
assert.match(home, /Research only, not the pick/);

const shell = fs.readFileSync('assets/fd2-shell.js', 'utf8');
assert.doesNotMatch(shell, /PREGAME INTELLIGENCE/);
assert.match(shell, /Model Lab/);
assert.match(shell, /#scoreboard/);

const bets = fs.readFileSync('bets.html', 'utf8');
assert.doesNotMatch(bets, /Start here:/);
assert.match(bets, /id="fd-prop-help-tip"/);
assert.match(bets, /About this data/);
assert.match(bets, /id="fd-compare-panel" hidden/);
assert.match(bets, /Upcoming games/);
assert.match(bets, /Largest edge/);
assert.match(bets, /fdGameVisible/);

const history = fs.readFileSync('history.html', 'utf8');
assert.match(history, /id="fd-mini-coverage"/);
assert.match(history, /Advanced · coverage notes/);
assert.match(history, /index\.html#scoreboard/);

const lab = fs.readFileSync('model-lab.html', 'utf8');
assert.match(lab, /Average miss/);
assert.match(lab, /Leans high\/low/);
assert.match(lab, /index\.html#scoreboard/);
assert.match(lab, /research only, not the pick/);

const health = fs.readFileSync('pipeline-health.html', 'utf8');
assert.match(health, /<details class="fd-workflow-log">/);
assert.match(health, /id="runs"/);

const appeal = fs.readFileSync('assets/fd-appeal.js', 'utf8');
assert.match(appeal, /<rect /);
assert.doesNotMatch(appeal.slice(appeal.indexOf('function trendChart'), appeal.indexOf('function near')), /polyline/);

console.log('declutter unit tests passed');
