/* Shared by Game Center and Prop Desk. Use fetch time for freshness while keeping the book's price-update time. */
window.FDDraftKings = (() => {
  const name = value => String(value || '').normalize('NFKD').replace(/[\u0300-\u036f]/g, '')
    .toLowerCase().trim().replace(/(?:[\s.,-]+)(?:jr|junior|sr|senior|ii|iii|iv|v)\.?$/, '').replace(/[^a-z0-9]/g, '');
  const suffix = value => {
    const raw = String(value || '').normalize('NFKD').replace(/[\u0300-\u036f]/g, '').toLowerCase().trim();
    const match = raw.match(/(?:[\s.,-]+)(jr|junior|sr|senior|ii|iii|iv|v)\.?$/);
    if (!match) return '';
    return ({junior:'jr',senior:'sr'})[match[1]] || match[1];
  };
  const time = value => typeof value === 'number' ? value : Date.parse(value);
  const aliases = entries => new Map(Object.entries(entries).flatMap(([key, values]) =>
    [key, ...values].map(value => [value.toLowerCase(), key])));
  function create(contract, quotes, now = Date.now(), players = []) {
    const teams = aliases(contract.teams), markets = aliases(contract.markets);
    const team = value => teams.get(String(value || '').toLowerCase());
    const market = value => markets.get(String(value || '').toLowerCase()) || value;
    const identity = (p, m, a, b, k) => {
      const pair = [team(a), team(b)];
      if (!name(p) || !m || !pair.every(Boolean) || pair[0] === pair[1] || !Number.isFinite(k)) return null;
      return [name(p), market(m), ...pair.sort(), k].join('|');
    };
    const rows = new Map();
    for (const q of quotes) {
      const kick = time(q.commence_time), providerStamp = time(q.last_update);
      const stamp = time(q.observed_at_utc || q.last_update);
      const key = identity(q.player, q.market_key, q.away_team, q.home_team, kick);
      if (!key || (q.bookmaker && q.bookmaker !== 'draftkings') || !Number.isFinite(stamp) ||
          stamp >= kick || stamp > now || !Number.isFinite(providerStamp) || providerStamp >= kick || providerStamp > now ||
          typeof q.line === 'boolean' || !(Number(q.line) > 0) || !Number.isFinite(Number(q.line))) continue;
      const rowKey = key + '|' + suffix(q.player);
      const old = rows.get(rowKey);
      if (!old || old.last_update < stamp) rows.set(rowKey, {...q, line:Number(q.line), last_update:stamp, provider_last_update:providerStamp});
      else if (old.last_update === stamp && old.line !== Number(q.line)) old.ambiguous = true;
    }
    const find = (p, kickoff) => {
      const base = identity(p.player, p.market_key || p.stat_key || p.market, p.team, p.opponent, time(kickoff));
      if (!base) return null;
      const requestedSuffix = suffix(p.player);
      let candidates = [...rows.entries()].filter(([key]) => key.startsWith(base + '|')).map(([,q]) => q)
        .filter(q => !q.ambiguous && (!requestedSuffix || !suffix(q.player) || suffix(q.player) === requestedSuffix));
      if (p.player_id != null) {
        const withIds = candidates.filter(q => q.player_id != null);
        if (withIds.length) candidates = withIds.filter(q => String(q.player_id) === String(p.player_id));
      }
      if (candidates.length !== 1) return null;
      const quote = candidates[0];
      if (requestedSuffix && suffix(quote.player) && requestedSuffix !== suffix(quote.player)) return null;
      if (p.player_id != null && quote.player_id != null && String(p.player_id) !== String(quote.player_id)) return null;
      const allRoster = (Array.isArray(players) ? players : []).filter(r =>
        identity(r.player || r.player_name, r.market_key || r.stat_key || r.market,
          r.team, r.opponent, time(kickoff)) === base &&
        name(r.player || r.player_name) === name(p.player));
      const uniqueRoster = new Map();
      for (const r of allRoster) {
        const rosterName = r.player || r.player_name;
        const key = [name(rosterName), suffix(rosterName), team(r.team), team(r.opponent),
          market(r.market_key || r.stat_key || r.market), String(r.player_id || '')].join('|');
        if (!uniqueRoster.has(key)) uniqueRoster.set(key, r);
      }
      let roster = [...uniqueRoster.values()];
      if (p.player_id != null && quote.player_id != null) {
        const exactId = roster.filter(r => r.player_id != null && String(r.player_id) === String(p.player_id));
        if (exactId.length) roster = exactId;
      }
      if (roster.length > 1) {
        const quoteSuffix = suffix(quote.player);
        const exact = roster.filter(r =>
          quoteSuffix && suffix(r.player || r.player_name) === quoteSuffix &&
          (!requestedSuffix || requestedSuffix === quoteSuffix));
        if (exact.length !== 1) return null;
        roster = exact;
      }
      if (roster.length === 1) {
        const rosterPlayer = roster[0];
        const rosterSuffix = suffix(rosterPlayer.player || rosterPlayer.player_name);
        if (rosterSuffix && suffix(quote.player) && rosterSuffix !== suffix(quote.player)) return null;
        if (quote.player_id != null && rosterPlayer.player_id != null &&
            String(quote.player_id) !== String(rosterPlayer.player_id)) return null;
      }
      return quote;
    };
    return {find, market, team, rows:[...rows.values()].filter(q => !q.ambiguous)};
  }
  const ready = fetch('assets/dk-markets.json').then(r => {
    if (!r.ok) throw Error('DraftKings market definitions unavailable');
    return r.json();
  });
  return {name, create, ready};
})();
