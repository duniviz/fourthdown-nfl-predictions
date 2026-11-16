/* Display-only weekly report card. Prefers the newer verified score ledger over a partial grade. */
(function (root, factory) {
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  if (root && root.document) api.mount();
})(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  const num = x => x !== null && x !== undefined && x !== '' && Number.isFinite(Number(x)) ? Number(x) : null;
  const esc = x => String(x ?? '').replace(/[&<>"']/g, c => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}[c]));
  const ct = x => {
    const d = new Date(x);
    return Number.isFinite(d.getTime()) ? d.toLocaleString('en-US', {timeZone: 'America/Chicago', month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit', timeZoneName: 'short'}) : 'Time unavailable';
  };
  function meanAbs(errors) {
    const xs = (errors || []).filter(e => Number.isFinite(e));
    if (!xs.length) return null;
    return {mae: xs.reduce((sum, value) => sum + Math.abs(value), 0) / xs.length, samples: xs.length};
  }
  function scored(rows) {
    return (rows || []).filter(row => num(row.home_score) !== null && num(row.away_score) !== null);
  }
  function gameMetrics(rows) {
    const margin = [], total = [];
    for (const row of scored(rows)) {
      const home = num(row.home_score), away = num(row.away_score);
      const projectedMargin = num(row.projected_margin_home), projectedTotal = num(row.projected_total);
      if (projectedMargin !== null) margin.push(projectedMargin - (home - away));
      if (projectedTotal !== null) total.push(projectedTotal - (home + away));
    }
    return {home_margin: meanAbs(margin), total: meanAbs(total)};
  }
  function playerMetrics(rows, gameIds) {
    const buckets = {passing_yards: [], rushing_yards: [], receiving_yards: []};
    for (const row of rows || []) {
      if (gameIds && !gameIds.has(row.game_id)) continue;
      if (!buckets[row.stat_key]) continue;
      const projection = num(row.projection), actual = num(row.actual);
      if (projection === null || actual === null) continue;
      buckets[row.stat_key].push(projection - actual);
    }
    return {
      passing_yards: meanAbs(buckets.passing_yards),
      rushing_yards: meanAbs(buckets.rushing_yards),
      receiving_yards: meanAbs(buckets.receiving_yards)
    };
  }
  function weeksOf(rows) {
    const grouped = new Map();
    for (const row of rows || []) {
      const season = num(row.season), week = num(row.week);
      if (season === null || week === null) continue;
      const key = season * 100 + week;
      if (!grouped.has(key)) grouped.set(key, []);
      grouped.get(key).push(row);
    }
    return [...grouped.keys()].sort((a, b) => b - a).map(key => ({
      season: Math.floor(key / 100),
      week: key % 100,
      rows: grouped.get(key)
    }));
  }
  function snapshotWeeks(performance) {
    return (performance && performance.weekly_reports || [])
      .filter(week => week && week.status === 'graded_observed_only')
      .sort((a, b) => Number(b.season) - Number(a.season) || Number(b.week) - Number(a.week));
  }
  function reportCardModel(performance, official, playerResults) {
    const snapshots = snapshotWeeks(performance);
    const snapshot = snapshots[0] || null;
    const previousSnapshot = snapshots[1] || null;
    const officialWeeks = weeksOf(official && official.rows);
    const reportAt = Date.parse(performance && performance.generated_at_utc || '');
    const officialAt = Date.parse(official && official.generated_at_utc || '');
    const playerAt = Date.parse(playerResults && playerResults.generated_at_utc || '');
    const latestOfficial = officialWeeks[0] || null;
    const officialNewer = !!(latestOfficial && Number.isFinite(officialAt) && (!snapshot || !Number.isFinite(reportAt) || officialAt > reportAt) && (!snapshot || latestOfficial.season > Number(snapshot.season) || (latestOfficial.season === Number(snapshot.season) && latestOfficial.week >= Number(snapshot.week))));
    if (!officialNewer) {
      if (!snapshot) return null;
      return {
        source: 'snapshot',
        latest: snapshot,
        previous: previousSnapshot,
        generatedAt: performance && performance.generated_at_utc,
        headline: null,
        footnote: null
      };
    }
    const currentRows = scored(latestOfficial.rows);
    const previousOfficial = officialWeeks[1] || null;
    const previousRows = previousOfficial ? scored(previousOfficial.rows) : [];
    const ids = new Set(currentRows.map(row => row.game_id));
    const previousIds = new Set(previousRows.map(row => row.game_id));
    const playersFresh = Number.isFinite(playerAt) && (!Number.isFinite(reportAt) || playerAt >= reportAt);
    const players = playersFresh ? (playerResults.rows || []) : [];
    const partial = snapshot && Number(snapshot.season) === latestOfficial.season && Number(snapshot.week) === latestOfficial.week && Number(snapshot.completed_games) < currentRows.length ? snapshot : null;
    const latest = {
      season: latestOfficial.season,
      week: latestOfficial.week,
      completed_games: currentRows.length,
      game_metrics: gameMetrics(currentRows),
      player_metrics: playersFresh ? playerMetrics(players, ids) : (partial && partial.player_metrics) || {}
    };
    const previous = previousRows.length ? {
      season: previousOfficial.season,
      week: previousOfficial.week,
      completed_games: previousRows.length,
      game_metrics: gameMetrics(previousRows),
      player_metrics: playersFresh ? playerMetrics(players, previousIds) : {}
    } : null;
    let footnote = 'Game margin, total, and player yards use saved pregame forecasts for every completed game on the verified score ledger.';
    if (!playersFresh && partial) footnote = 'Game margin and total use every completed game on the verified score ledger. Player yards still use the earlier partial grade.';
    if (partial) footnote += ' An earlier grade on ' + ct(performance && performance.generated_at_utc) + ' only included ' + partial.completed_games + ' final game' + (Number(partial.completed_games) === 1 ? '' : 's') + ', so that partial sample is not shown.';
    footnote += ' Updated ' + ct(official.generated_at_utc) + '.';
    return {
      source: 'official',
      latest,
      previous,
      generatedAt: official.generated_at_utc,
      headline: latest.season + ' Week ' + latest.week + ' · ' + latest.completed_games + ' completed games on the verified score ledger. Lower average error is better.',
      footnote
    };
  }
  function card(label, value, old, unit) {
    const ready = value && num(value.mae) !== null && num(value.samples) !== null && Number(value.samples) > 0;
    if (!ready) return '<article class="fd-insight-item"><strong>' + esc(label) + '</strong><p>Not enough graded results yet</p></article>';
    let compare = '';
    if (old && num(old.mae) !== null && num(old.samples) !== null && Number(old.samples) > 0) {
      const delta = Number(value.mae) - Number(old.mae);
      compare = 'Prior week: ' + Number(old.mae).toFixed(1) + ' ' + unit + ' · ' + (Math.abs(delta) < .05 ? 'about the same' : Math.abs(delta).toFixed(1) + ' ' + unit + ' ' + (delta < 0 ? 'lower' : 'higher') + ' error');
    }
    return '<article class="fd-insight-item"><strong>' + esc(label) + '</strong><p>Average error: ' + Number(value.mae).toFixed(1) + ' ' + esc(unit) + '</p><small>' + esc(value.samples) + ' graded forecasts' + (compare ? ' · ' + esc(compare) : '') + '</small></article>';
  }
  function markup(model) {
    const latest = model.latest, previous = model.previous;
    const headline = model.headline || (latest.season + ' Week ' + latest.week + ' · ' + (latest.completed_games ?? 0) + ' completed games graded. Lower average error is better; samples may be incomplete. Winner-pick accuracy is not published in this weekly report.');
    const footnote = model.footnote || ('Each week uses its own graded sample, so changes can reflect different games and coverage. Updated ' + ct(model.generatedAt) + '.');
    return '<span class="fd-insight-tag">Observed pregame forecasts</span><h2>Weekly model report card</h2><p class="fd-insight-note">' + esc(headline) + '</p><div class="fd-insight-grid">' +
      card('Game margin', latest.game_metrics && latest.game_metrics.home_margin, previous && previous.game_metrics && previous.game_metrics.home_margin, 'points') +
      card('Game total', latest.game_metrics && latest.game_metrics.total, previous && previous.game_metrics && previous.game_metrics.total, 'points') +
      card('Passing yards', latest.player_metrics && latest.player_metrics.passing_yards, previous && previous.player_metrics && previous.player_metrics.passing_yards, 'yards') +
      card('Rushing yards', latest.player_metrics && latest.player_metrics.rushing_yards, previous && previous.player_metrics && previous.player_metrics.rushing_yards, 'yards') +
      card('Receiving yards', latest.player_metrics && latest.player_metrics.receiving_yards, previous && previous.player_metrics && previous.player_metrics.receiving_yards, 'yards') +
      '</div><p class="fd-insight-note">' + esc(footnote) + '</p>';
  }
  async function mount() {
    const rootNode = document.getElementById('fd-weekly-report-card');
    if (!rootNode) return;
    const get = path => fetch('data/' + path + '?t=' + Date.now(), {cache: 'no-store'}).then(response => response.ok ? response.json() : null).catch(() => null);
    const [performance, official, players] = await Promise.all([
      get('weekly-model-performance.json'),
      get('game-official-results.json'),
      get('player-results.json')
    ]);
    const model = reportCardModel(performance, official, players);
    if (!model) {
      rootNode.innerHTML = '<h2>Weekly model report card</h2><p class="fd-insight-note">Waiting for graded, timestamped pregame forecasts and verified results.</p>';
      return;
    }
    rootNode.dataset.fdReportSource = model.source;
    rootNode.innerHTML = markup(model);
  }
  return {reportCardModel, markup, mount};
});
