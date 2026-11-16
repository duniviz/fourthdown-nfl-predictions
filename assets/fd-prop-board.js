/* Prop Desk category, slate label, and recorded-hit display helpers. */
(function (root, factory) {
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  root.fdPropBoard = api;
})(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  const YARDS = ['Passing yards', 'Rushing yards', 'Receiving yards'];
  const TD = ['Anytime TD'];
  const COUNTS = {
    completions: {markets: ['Pass completions', 'Completions'], key: 'player_pass_completions'},
    rushes: {markets: ['Rush attempts'], key: 'player_rush_attempts'},
    receptions: {markets: ['Receptions'], key: 'player_receptions'}
  };
  function tabOf(player) {
    const market = String(player && player.market || '');
    if (YARDS.includes(market)) return 'yards';
    if (TD.includes(market)) return 'td';
    if (COUNTS.completions.markets.includes(market)) return 'completions';
    if (COUNTS.rushes.markets.includes(market)) return 'rushes';
    if (COUNTS.receptions.markets.includes(market)) return 'receptions';
    return '';
  }
  function matchesTab(player, tab) {
    return tabOf(player) === tab;
  }
  function countKey(tab) {
    return COUNTS[tab] ? COUNTS[tab].key : '';
  }
  function marketOptions(tab) {
    if (tab === 'yards') return [{value: 'all', label: 'All yard markets'}].concat(YARDS.map(name => ({value: name, label: name})));
    return [];
  }
  function gameTag(gameId, kickoff, now) {
    const parts = String(gameId || '').split('_');
    const week = parts.length >= 2 && /^\d+$/.test(parts[1]) ? 'Week ' + Number(parts[1]) : '';
    const time = Date.parse(kickoff || '');
    const when = Number.isFinite(time)
      ? new Intl.DateTimeFormat('en-US', {timeZone: 'America/Chicago', weekday: 'short', month: 'short', day: 'numeric'}).format(new Date(time))
      : '';
    const clock = Number.isFinite(now) ? now : Date.now();
    return {text: [week, when].filter(Boolean).join(' · '), final: Number.isFinite(time) && time <= clock};
  }
  function recordedHits(rows) {
    const graded = (rows || []).filter(row => ['hit', 'miss', 'push'].includes(row.recommendation_result));
    const hits = graded.filter(row => row.recommendation_result === 'hit').length;
    const weeks = graded.map(row => {
      const match = String(row.game_id || '').match(/^(\d{4})_(\d{1,2})_/);
      return match ? {season: Number(match[1]), week: Number(match[2])} : null;
    }).filter(Boolean).sort((a, b) => a.season - b.season || a.week - b.week);
    let window = '';
    if (weeks.length) {
      const first = weeks[0], last = weeks[weeks.length - 1];
      window = first.season === last.season
        ? (first.week === last.week ? first.season + ' Week ' + first.week : first.season + ' Weeks ' + first.week + '–' + last.week)
        : first.season + ' Week ' + first.week + ' – ' + last.season + ' Week ' + last.week;
    }
    return {hits, graded: graded.length, window};
  }
  function gameLabel(gameId) {
    const parts = String(gameId || '').split('_');
    return parts.length >= 4 ? parts[2] + ' at ' + parts[3] : String(gameId || 'a game');
  }
  function joinGames(labels) {
    if (labels.length <= 1) return labels[0] || '';
    if (labels.length === 2) return labels[0] + ' and ' + labels[1];
    return labels.slice(0, -1).join(', ') + ', and ' + labels[labels.length - 1];
  }
  // Props counts every saved over/under grade. History counts that same grade only when
  // the game also has a row on the verified score ledger.
  function ledgerGap(rows, officialRows) {
    const ids = new Set((officialRows || []).map(row => row && row.game_id).filter(Boolean));
    const graded = (rows || []).filter(row => ['hit', 'miss', 'push'].includes(row.recommendation_result));
    const onLedger = ids.size ? graded.filter(row => ids.has(row.game_id)) : graded;
    const outside = ids.size ? graded.filter(row => !ids.has(row.game_id)) : [];
    const games = [...new Set(outside.map(row => row.game_id))].map(gameLabel);
    const summary = recordedHits(graded);
    const empty = {
      propsGraded: graded.length,
      historyGraded: onLedger.length,
      outside: outside.length,
      games,
      propsNote: '',
      historyNote: ''
    };
    if (!outside.length) return empty;
    const list = joinGames(games);
    const windowLabel = summary.window ? 'This ' + summary.window + ' total' : 'This total';
    return {
      propsGraded: graded.length,
      historyGraded: onLedger.length,
      outside: outside.length,
      games,
      propsNote: windowLabel + ' counts every saved over/under grade, including ' + outside.length + ' from ' + list + '. History only counts games with a verified final score, so it shows ' + onLedger.length + '.',
      historyNote: 'Verified picks count saved over/under grades for games with a final score on this ledger (' + onLedger.length + ' when all weeks are selected). Props also includes ' + outside.length + ' graded picks from ' + list + ', which do not have a game-score row here.'
    };
  }
  return {YARDS, tabOf, matchesTab, countKey, marketOptions, gameTag, recordedHits, ledgerGap};
});
