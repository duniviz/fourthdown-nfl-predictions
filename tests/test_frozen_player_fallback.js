const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");

const html = fs.readFileSync("index.html", "utf8");
const start = html.indexOf(" function frozenPlayers(g){");
const end = html.indexOf("\n function completedPlayerPanel(g){", start);
assert.ok(start >= 0 && end > start, "matchup player freezer must exist");
const implementation = html.slice(start, end);

const kickoff = "2026-11-08T14:30:00.000Z";
const feedStamp = "2026-11-08T14:14:00.000Z";
const player = {
  game_id: "2026_09_CIN_ATL", player_id: "00-0039917", player: "Michael Penix Jr.",
  team: "ATL", opponent: "CIN", stat_key: "passing_yards", market_key: "player_pass_yds",
  projection: 215.8
};
function run(feedTimestamp, history = []) {
  const context = {
    Date,
    playerHistory: history,
    playerFeed: { generated_at_utc: feedTimestamp },
    playerResearch: [player],
    canon: value => String(value || "").toUpperCase(),
    getProjection: () => ({ game_id: "2026_09_CIN_ATL" }),
    FDDraftKings: { name: value => String(value).toLowerCase() },
    dkIndex: { market: value => value },
    withSavedLine: row => ({ ...row, dk_line: 224.5, dk_quote_time: "2026-11-08T14:07:38.254Z" })
  };
  vm.runInNewContext(implementation, context);
  return context.frozenPlayers({
    id: "2026_09_CIN_ATL", date: kickoff,
    home: { abbr: "ATL" }, away: { abbr: "CIN" }
  });
}

const fallback = run(feedStamp);
assert.equal(fallback.length, 1, "a published pregame forecast should fill a missed player archive");
assert.equal(fallback[0].player, "Michael Penix Jr.");
assert.equal(fallback[0].projection, 215.8);
assert.equal(fallback[0].dk_line, 224.5);
assert.equal(fallback[0].pregame_feed_fallback, true);

const postKick = run("2026-11-08T14:31:00.000Z");
assert.equal(postKick.length, 0, "post-kickoff player feeds must never be reconstructed as pregame forecasts");

const locked = { ...player, kickoff_utc: kickoff, forecast_captured_at_utc: "2026-11-08T14:20:00.000Z", projection: 219.1 };
const preferred = run(feedStamp, [locked]);
assert.equal(preferred.length, 1);
assert.equal(preferred[0].projection, 219.1, "the archived lock must take precedence over the fallback feed");
console.log("Pregame player fallback preserves only timestamped pre-kick forecasts.");
