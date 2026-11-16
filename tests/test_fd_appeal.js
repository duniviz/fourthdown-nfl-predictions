"use strict";
const assert = require("node:assert/strict");
const appeal = require("../assets/fd-appeal.js");
const colors = require("../assets/fd-team-colors.js");

assert.equal(colors.color("LAR"), colors.color("LA"));
assert.equal(colors.color("JAC"), colors.color("JAX"));
assert.equal(colors.color("WAS"), colors.color("WSH"));
assert.equal(colors.color("bal"), colors.color("BAL"));
assert.notEqual(colors.color("NOPE"), "");
assert.match(colors.pairStyle("LAC", "BAL"), /--away-color:#0090d0;--home-color:#7a45d6/);

assert.equal(appeal.confidenceTag({ pct: 62 }).tag, "Strong");
assert.equal(appeal.confidenceTag({ pct: 61.9 }).tag, "Lean");
assert.equal(appeal.confidenceTag({ pct: 55 }).tag, "Lean");
assert.equal(appeal.confidenceTag({ pct: 54.9 }).tag, "Pass");
assert.equal(appeal.confidenceTag({ pct: 70 }).source, "simulation");
assert.equal(appeal.confidenceTag({ edge: 3, allowEdge: true }).tag, "Strong");
assert.equal(appeal.confidenceTag({ edge: -1.5, allowEdge: true }).tag, "Lean");
assert.equal(appeal.confidenceTag({ edge: 1.4, allowEdge: true }).tag, "Pass");
assert.equal(appeal.confidenceTag({ edge: 9, allowEdge: true, pct: 40 }).tag, "Pass", "A published percentage wins over the point gap");
assert.equal(appeal.confidenceTag({ edge: 4 }), null, "Do not use the point gap unless the caller allows that fallback");
assert.equal(appeal.confidenceTag({}), null);

const panel = appeal.gamePanel({
  away: "LAC",
  home: "BAL",
  awayPct: 40.1,
  homePct: 56.7,
  tiePct: 3.2,
  awayScore: 15.6,
  homeScore: 18.5,
  modelTotal: 34.1,
  dkSpread: -4.5,
  dkTotal: 38.5,
  winnerSide: "home",
  homeWin: 56.7,
  awayWin: 40.1,
  homeCover: 45.3,
  awayCover: 54.7,
  overCover: 38.6,
  underCover: 61.4,
  spreadEdge: 18.5 - 15.6 + -4.5,
  totalEdge: 34.1 - 38.5
});
assert.match(panel, /LAC 40\.1%/);
assert.match(panel, /BAL 56\.7%/);
assert.match(panel, /Home spread on BAL/);
assert.match(panel, /BAL -2\.9/);
assert.match(panel, /BAL -4\.5/);
assert.match(panel, /Negative means BAL is favored/);
assert.match(panel, /Winner · Lean/);
assert.match(panel, /Total · Lean/);
assert.match(panel, /Spread · Pass/);
assert.match(panel, /is-large/, "A 4.4-point total gap is highlighted");
assert.match(panel, /Game total/);

const graded = appeal.gamePanel({
  away: "CLE",
  home: "NO",
  awayScore: 20,
  homeScore: 23,
  dkSpread: -3,
  dkTotal: 42.5,
  spreadEdge: 0,
  totalEdge: 0.2,
  winnerResult: "hit",
  spreadResult: "miss",
  totalResult: "push"
});
assert.match(graded, /class="bet-final is-hit"/);
assert.match(graded, /class="bet-final is-miss"/);
assert.match(graded, /class="bet-final is-push"/);
assert.doesNotMatch(graded, /Winner · /, "No winner tag without a published win percentage");

assert.equal(appeal.sparkline([12], 10), "");
assert.equal(appeal.sparkline([], 10), "");
const spark = appeal.sparkline([10, 22, 18, 30, 14], 19.5);
assert.match(spark, /<svg/);
assert.match(spark, /versus a line of 19.5/);
const far = appeal.sparkline([10, 12, 11, 13, 9], 73.5);
assert.match(far, /above the chart/);
assert.doesNotMatch(far, /fd-appeal-spark-line/);
assert.match(spark, /is-over/);
assert.match(spark, /is-under/);
assert.match(appeal.headshot("Derrick Henry", "3043078"), /alt="Derrick Henry headshot"/);
assert.equal(appeal.headshot("Nope", "abc"), "");

const recent = appeal.recentValues({
  players: { "00-1|player_pass_yds": { games: [{ actual: 1 }, { actual: 2 }, { actual: 3 }, { actual: 4 }, { actual: 5 }, { actual: 6 }] } },
  by_name: { "ajbrown|player_rec_yds": { games: [{ actual: 40 }, { actual: 80 }], athlete_id: "99" } }
}, "00-1", "Someone", "player_pass_yds");
assert.deepEqual(recent, [2, 3, 4, 5, 6]);
assert.deepEqual(appeal.recentValues({ by_name: { "ajbrown|player_rec_yds": { games: [{ actual: 40 }, { actual: 80 }] } } }, "", "A.J. Brown", "player_rec_yds"), [40, 80]);

const view = appeal.labView({
  summary: {
    winner: { hits: 19, misses: 6, pushes: 0, hit_pct: 76 },
    ats: { hits: 10, misses: 15, pushes: 1, hit_pct: 40 },
    ou: { hits: 13, misses: 12, pushes: 0, hit_pct: 52 }
  },
  rows: [
    { season: 2026, week: 9, winner_result: "hit", ats_result: "miss", ou_result: "hit" },
    { season: 2026, week: 9, winner_result: "miss", ats_result: "hit", ou_result: "push" },
    { season: 2026, week: 10, winner_result: "hit", ats_result: "hit", ou_result: "miss" }
  ]
});
assert.equal(view.tiles[0].rate, 76);
assert.equal(view.tiles[0].sample, 25);
assert.equal(view.tiles[1].sample, 25);
assert.equal(view.weeks[0].week, 9);
assert.equal(view.weeks[0].ou.pushes, 1);
assert.equal(view.weeks[1].winner.hits, 1);
const markup = appeal.labMarkup({
  summary: view.tiles.reduce((acc, tile, index) => {
    const key = ["winner", "ats", "ou"][index];
    acc[key] = { hits: tile.hits, misses: tile.misses, pushes: tile.pushes, hit_pct: tile.rate };
    return acc;
  }, {}),
  rows: [
    { season: 2026, week: 9, winner_result: "hit", ats_result: "miss", ou_result: "hit" },
    { season: 2026, week: 10, winner_result: "hit", ats_result: "hit", ou_result: "miss" }
  ]
});
assert.match(markup, /76\.0%/);
assert.match(markup, /25 graded/);
assert.match(markup, /<svg/);
assert.match(markup, /Week 9/);
assert.match(markup, /Detailed accuracy and ML tables|long comparison tables/);

console.log("Appeal visuals: team colors, confidence thresholds, spread label, sparkline, and lab tiles passed");
