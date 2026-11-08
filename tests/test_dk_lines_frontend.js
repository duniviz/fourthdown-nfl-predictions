const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

const contract = JSON.parse(fs.readFileSync('assets/dk-markets.json', 'utf8'));
const context = {
  window: {},
  fetch: async () => ({ ok: true, json: async () => contract }),
};
vm.runInNewContext(fs.readFileSync('assets/dk-lines.js', 'utf8'), context);

async function main() {
  await context.window.FDDraftKings.ready;
  const now = Date.parse('2026-11-07T19:00:00Z');
  const kickoff = '2026-11-08T14:30:00Z';
  const quote = (player, market, line) => ({
    player, market_key: market, home_team: 'Atlanta Falcons',
    away_team: 'Cincinnati Bengals', commence_time: kickoff,
    last_update: '2026-11-07T16:00:00Z',
    observed_at_utc: '2026-11-07T19:00:00Z', line,
    bookmaker: 'draftkings',
  });
  const index = context.window.FDDraftKings.create(contract, [
    quote('Kyle Pitts Sr.', 'player_rec_yds', 43.5),
    quote('Michael Penix Jr.', 'player_pass_yds', 224.5),
    {...quote('Kyle Pitts', 'player_rec_yds', 45.5),
      commence_time: '2026-11-08T14:00:00Z'},
  ], now);
  const find = (player, market) => index.find({
    player, market_key: market, team: 'ATL', opponent: 'CIN',
  }, kickoff);
  assert.equal(find('Kyle Pitts', 'player_rec_yds')?.line, 43.5);
  assert.equal(find('Michael Penix', 'passing_yards')?.line, 224.5);
  assert.equal(find('Kyle Pitts', 'player_rec_yds')?.last_update, now);
  assert.equal(index.find({player:'Michael Penix',market_key:'passing_yards',team:'ATL',opponent:'CIN'},
    '2026-11-08T14:00:00Z'), null);
  console.log('Frontend player identity, market alias, and verified-observation checks passed');
}

main().catch(error => { console.error(error); process.exitCode = 1; });
