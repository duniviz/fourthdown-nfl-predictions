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
    // Index once: each lookup previously scanned every quote and every roster row.
    const quotesByBase = new Map();
    for (const [key, quote] of rows) {
      const base = key.slice(0, key.lastIndexOf('|'));
      if (!quotesByBase.has(base)) quotesByBase.set(base, []);
      quotesByBase.get(base).push(quote);
    }
    const rosterByIdentity = new Map();
    for (const r of Array.isArray(players) ? players : []) {
      const id = identity(r.player || r.player_name, r.market_key || r.stat_key || r.market, r.team, r.opponent, 0);
      if (!id) continue;
      if (!rosterByIdentity.has(id)) rosterByIdentity.set(id, []);
      rosterByIdentity.get(id).push(r);
    }
    const find = (p, kickoff) => {
      const base = identity(p.player, p.market_key || p.stat_key || p.market, p.team, p.opponent, time(kickoff));
      if (!base) return null;
      const requestedSuffix = suffix(p.player);
      let candidates = (quotesByBase.get(base) || []).filter(q => !q.ambiguous && (!requestedSuffix || !suffix(q.player) || suffix(q.player) === requestedSuffix));
      if (p.player_id != null) {
        const exactIds = candidates.filter(q => q.player_id != null && String(q.player_id) === String(p.player_id));
        // Provider IDs may use a different namespace than the projection feed.
        // Prefer an exact ID match, but retain the strict name/team/market/game
        // match when no provider ID agrees.
        if (exactIds.length) candidates = exactIds;
      }
      if (candidates.length !== 1) return null;
      const quote = candidates[0];
      if (requestedSuffix && suffix(quote.player) && requestedSuffix !== suffix(quote.player)) return null;
      const rosterId = identity(p.player, p.market_key || p.stat_key || p.market, p.team, p.opponent, 0);
      const allRoster = rosterByIdentity.get(rosterId) || [];
      const uniqueRoster = new Map();
      for (const r of allRoster) {
        const rosterName = r.player || r.player_name;
        const key = [name(rosterName), suffix(rosterName), team(r.team), team(r.opponent),
          market(r.market_key || r.stat_key || r.market), String(r.player_id || '')].join('|');
        if (!uniqueRoster.has(key)) uniqueRoster.set(key, r);
      }
      let roster = [...uniqueRoster.values()];
      const quoteSuffix = suffix(quote.player);
      if (requestedSuffix && quoteSuffix && requestedSuffix !== quoteSuffix) return null;
      // Resolve a shared name by suffix before considering projection-feed IDs.
      // Provider IDs can be from a different namespace and must not hide a
      // second roster entry with the same normalized name.
      if (roster.length > 1) {
        const exact = roster.filter(r =>
          quoteSuffix && suffix(r.player || r.player_name) === quoteSuffix);
        if (exact.length !== 1) return null;
        roster = exact;
      }
      if (roster.length === 1) {
        const rosterSuffix = suffix(roster[0].player || roster[0].player_name);
        if (quoteSuffix && rosterSuffix && quoteSuffix !== rosterSuffix) return null;
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
