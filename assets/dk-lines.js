/* Shared by Game Center and Prop Desk. Quotes retain their provider timestamps. */
window.FDDraftKings = (() => {
  const name = value => String(value || '').normalize('NFKD').replace(/[\u0300-\u036f]/g, '')
    .toLowerCase().trim().replace(/(?:[\s.,-]+)(?:jr|junior|sr|senior|ii|iii|iv|v)\.?$/, '').replace(/[^a-z0-9]/g, '');
  const time = value => typeof value === 'number' ? value : Date.parse(value);
  const aliases = entries => new Map(Object.entries(entries).flatMap(([key, values]) =>
    [key, ...values].map(value => [value.toLowerCase(), key])));
  function create(contract, quotes, now = Date.now(), roster = []) {
    const teams = aliases(contract.teams), markets = aliases(contract.markets);
    const team = value => teams.get(String(value || '').toLowerCase());
    const market = value => markets.get(String(value || '').toLowerCase()) || value;
    const identity = (p, m, a, b, k) => {
      const pair = [team(a), team(b)];
      if (!name(p) || !m || !pair.every(Boolean) || pair[0] === pair[1] || !Number.isFinite(k)) return null;
      return [name(p), market(m), ...pair.sort(), k].join('|');
    };
    const rosterIds = new Map();
    for (const player of roster) {
      if (!player.player_id) continue;
      const key = identity(player.player, player.market_key || player.stat_key || player.market,
        player.team, player.opponent, time(player.kickoff_utc));
      if (!key) continue;
      if (!rosterIds.has(key)) rosterIds.set(key, new Set());
      rosterIds.get(key).add(String(player.player_id));
    }
    const rows = new Map();
    for (const q of quotes) {
      const kick = time(q.commence_time), stamp = time(q.last_update);
      const key = identity(q.player, q.market_key, q.away_team, q.home_team, kick);
      if (!key || (q.bookmaker && q.bookmaker !== 'draftkings') || !Number.isFinite(stamp) ||
          stamp >= kick || stamp > now || typeof q.line === 'boolean' || !(Number(q.line) > 0) || !Number.isFinite(Number(q.line))) continue;
      const old = rows.get(key);
      if (!old || old.last_update < stamp) rows.set(key, {...q, line:Number(q.line), last_update:stamp});
      else if (old.last_update === stamp && old.line !== Number(q.line)) old.ambiguous = true;
    }
    const find = (p, kickoff) => {
      const key = identity(p.player, p.market_key || p.stat_key || p.market, p.team, p.opponent, time(kickoff));
      if ((rosterIds.get(key)?.size || 0) > 1) return null;
      const q = rows.get(key);
      return q && !q.ambiguous ? q : null;
    };
    return {find, market, team, rows:[...rows.values()].filter(q => !q.ambiguous)};
  }
  const ready = fetch('assets/dk-markets.json').then(r => {
    if (!r.ok) throw Error('DraftKings market definitions unavailable');
    return r.json();
  });
  return {name, create, ready};
})();
