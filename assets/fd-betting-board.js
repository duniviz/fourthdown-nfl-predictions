/* Betting Board presentation. Displays published forecasts, DK lines, and ML candidates. Does not change model math. */
(function (root, factory) {
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  if (root && root.document) api.mount(root.document);
})(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  const NAMES = {ARI:'cardinals',ATL:'falcons',BAL:'ravens',BUF:'bills',CAR:'panthers',CHI:'bears',CIN:'bengals',CLE:'browns',DAL:'cowboys',DEN:'broncos',DET:'lions',GB:'packers',HOU:'texans',IND:'colts',JAC:'jaguars',JAX:'jaguars',KC:'chiefs',LV:'raiders',LAC:'chargers',LAR:'rams',LA:'rams',MIA:'dolphins',MIN:'vikings',NE:'patriots',NO:'saints',NYG:'giants',NYJ:'jets',PHI:'eagles',PIT:'steelers',SF:'49ers',SEA:'seahawks',TB:'buccaneers',TEN:'titans',WAS:'commanders',WSH:'commanders'};
  const LOGO = {JAC:'jax',JAX:'jax',WAS:'wsh',WSH:'wsh',LAR:'lar',LA:'lar'};
  const MARKET_KEY = {passing_yards:'player_passing_yards',rushing_yards:'player_rushing_yards',receiving_yards:'player_receiving_yards','Passing yards':'player_passing_yards','Rushing yards':'player_rushing_yards','Receiving yards':'player_receiving_yards'};
  const MARKET_LABEL = {passing_yards:'Passing yards',rushing_yards:'Rushing yards',receiving_yards:'Receiving yards',player_passing_yards:'Passing yards',player_rushing_yards:'Rushing yards',player_receiving_yards:'Receiving yards'};

  function num(value) {
    return value !== null && value !== undefined && value !== '' && Number.isFinite(Number(value)) ? Number(value) : null;
  }
  function esc(value) {
    return String(value ?? '').replace(/[&<>"']/g, ch => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]));
  }
  function norm(value) {
    return String(value || '').toLowerCase().replace(/[^a-z0-9]/g, '');
  }
  function confidenceWords(pct) {
    if (pct === null || pct === undefined || !Number.isFinite(Number(pct))) return 'No simulation';
    const value = Number(pct);
    if (value >= 62) return 'Strong lean';
    if (value >= 56) return 'Lean';
    if (value >= 52.4) return 'Slight lean';
    return 'Below break-even';
  }
  function mlCandidate(market) {
    const value = num(market && market.candidate);
    return value;
  }
  function logo(team) {
    return 'https://a.espncdn.com/i/teamlogos/nfl/500/' + (LOGO[team] || String(team || 'nfl')).toLowerCase() + '.png';
  }
  function gradeRate(rows, field) {
    const graded = (rows || []).filter(row => row && (row[field] === 'hit' || row[field] === 'miss'));
    const hits = graded.filter(row => row[field] === 'hit').length;
    return {hits, n: graded.length, pct: graded.length ? 100 * hits / graded.length : null};
  }
  function latestWeek(rows) {
    return (rows || []).reduce((best, row) => {
      const season = num(row && row.season), week = num(row && row.week);
      if (season === null || week === null) return best;
      if (!best || season > best.season || (season === best.season && week > best.week)) return {season, week};
      return best;
    }, null);
  }
  function gameEdgeRows(forecast, quote, sim) {
    const away = num(forecast && forecast.projected_away_score);
    const home = num(forecast && forecast.projected_home_score);
    if (!forecast || away === null || home === null) return [];
    const margin = home - away;
    const total = away + home;
    const markets = (forecast.game_ml_shadow && forecast.game_ml_shadow.markets) || {};
    const mlMargin = mlCandidate(markets.game_margin_home);
    const mlTotal = mlCandidate(markets.game_total);
    const spread = num(quote && quote.home_spread);
    const dkTotal = num(quote && quote.total);
    const rows = [];
    if (dkTotal !== null && total !== dkTotal) {
      const edge = total - dkTotal;
      const over = edge > 0;
      rows.push({
        kind: 'Total',
        pick: (over ? 'Over ' : 'Under ') + dkTotal.toFixed(1),
        model: total.toFixed(1),
        ml: mlTotal === null ? null : mlTotal.toFixed(1),
        dk: dkTotal.toFixed(1),
        edge: Math.abs(edge),
        unit: 'pts',
        pct: num(sim && (over ? sim.over_cover_pct : sim.under_cover_pct)),
        tone: 'pos', direction: over ? 'over' : 'under'
      });
    }
    if (spread !== null && Math.abs(margin + spread) >= 0.05) {
      const homePick = margin + spread > 0;
      const team = homePick ? forecast.home : forecast.away;
      const line = homePick ? spread : -spread;
      rows.push({
        kind: 'Spread',
        pick: team + ' ' + (line > 0 ? '+' : '') + line.toFixed(1),
        model: (margin >= 0 ? forecast.home : forecast.away) + ' by ' + Math.abs(margin).toFixed(1),
        ml: mlMargin === null ? null : (mlMargin >= 0 ? forecast.home : forecast.away) + ' by ' + Math.abs(mlMargin).toFixed(1),
        dk: (spread < 0 ? forecast.home : forecast.away) + ' ' + Math.abs(spread).toFixed(1),
        edge: Math.abs(margin + spread),
        unit: 'pts',
        pct: num(sim && (homePick ? sim.home_cover_pct : sim.away_cover_pct)),
        tone: 'pos'
      });
    }
    if (home !== away) {
      const winner = home > away ? forecast.home : forecast.away;
      rows.push({
        kind: 'Winner',
        pick: winner + ' to win',
        model: away.toFixed(1) + '–' + home.toFixed(1),
        ml: mlMargin === null ? null : (mlMargin >= 0 ? forecast.home : forecast.away) + ' side',
        dk: 'Moneyline',
        edge: null,
        unit: '',
        pct: num(sim && (winner === forecast.home ? sim.home_win_pct : sim.away_win_pct)),
        tone: 'pos'
      });
    }
    return rows.sort((a, b) => (b.edge || 0) - (a.edge || 0));
  }
  // Use only same-game, same-player, same-market pregame simulation draws.
  // The sampled distribution is exploratory, not a calibrated win probability.
  function propSimulationRate(row, line, direction) {
    if (!row || !Array.isArray(row.sorted_draws) || row.sorted_draws.length < 50 ||
        !Number.isFinite(Number(line))) return null;
    const nums = row.sorted_draws.map(Number);
    if (nums.some(x => !Number.isFinite(x))) return null;
    let hits = 0, valid = 0;
    for (const value of nums) {
      valid += 1;
      if (direction === 'over' ? value > Number(line) : value < Number(line)) hits += 1;
    }
    return valid ? 100 * hits / valid : null;
  }
  function findPropSimulation(player, key, simulationRows) {
    const id = String(player.game_id || '');
    const name = norm(player.player_name || player.player);
    const market = key.replace(/^player_/, '');
    if (!id || !name) return null; // Do not mix players from different games.
    return (simulationRows || []).find(row =>
      row.game_id === id && norm(row.player) === name && row.stat_key === market) || null;
  }
  function propEdgeRows(players, lines, simulationRows) {
    const rows = [];
    for (const player of players || []) {
      const key = MARKET_KEY[player.market] || MARKET_KEY[player.stat_key] || MARKET_KEY[player.market_key];
      const projection = num(player.projection !== undefined ? player.projection : player.projected_yards);
      const team = String(player.team || '').toUpperCase();
      const nick = NAMES[team];
      if (!key || projection === null || !nick) continue;
      const quote = (lines || []).find(line => line.market_key === key && norm(line.player) === norm(player.player_name || player.player) && String(line.home_team + ' ' + line.away_team).toLowerCase().includes(nick));
      const dk = num(quote && quote.line);
      if (dk === null) continue;
      const gap = projection - dk;
      const ml = mlCandidate(player.player_ml_shadow);
      rows.push({
        player: player.player_name || player.player,
        team,
        market: MARKET_LABEL[player.market] || MARKET_LABEL[player.stat_key] || player.market || 'Prop',
        pick: (gap >= 0 ? 'Over ' : 'Under ') + dk.toFixed(1) + ' · ' + (player.player_name || player.player),
        model: projection.toFixed(1),
        ml: ml === null ? null : ml.toFixed(1),
        dk: dk.toFixed(1),
        edge: Math.abs(gap),
        unit: 'yds',
        pct: propSimulationRate(findPropSimulation(player, key, simulationRows), dk, gap >= 0 ? 'over' : 'under'),
        tone: 'pos', direction: gap >= 0 ? 'over' : 'under'
      });
    }
    const seen = new Set();
    return rows.filter(row => {
      const id = row.player + '|' + row.market;
      if (seen.has(id)) return false;
      seen.add(id);
      return true;
    }).sort((a, b) => b.edge - a.edge);
  }
  function meter(edge, max, mlEdge) {
    const width = Math.max(8, Math.min(100, (Number(edge) || 0) / max * 100));
    const mark = mlEdge === null || mlEdge === undefined ? '' : '<b class="fd-bb-ml-mark" style="left:' + Math.max(4, Math.min(96, Number(mlEdge) / max * 100)).toFixed(1) + '%" title="ML projection, research"></b>';
    return '<div class="fd-bb-meter" role="img" aria-label="Official edge ' + esc(edge) + '.' + (mark ? ' ML projection, research, also marked.' : '') + '"><i style="width:' + width.toFixed(1) + '%"></i>' + mark + '</div>';
  }
  function table(rows, max) {
    if (!rows.length) return '<p class="fd-bb-empty">No matched current-model edges for this tab yet.</p>';
    const body = rows.map(row => {
      const mlEdge = row.ml === null || row.dk === 'Moneyline' ? null : Math.abs(Number(row.ml) - Number(row.dk));
      return '<tr><td><span class="fd-bb-kind">' + esc(row.kind || row.market) + '</span><div class="fd-bb-pick">' + esc(row.pick) + '</div><span class="fd-official">Official pick · current model</span></td>' +
        '<td class="fd-bb-num"><span class="fd-bb-cell">Model</span>' + esc(row.model) + '</td>' +
        '<td class="fd-bb-num fd-bb-ml"><span class="fd-bb-cell">ML</span>' + (row.ml === null ? '—' : esc(row.ml)) + '<small>ML projection, research</small></td>' +
        '<td class="fd-bb-num"><span class="fd-bb-cell">DK</span>' + esc(row.dk) + '</td>' +
        '<td><span class="fd-bb-cell">Edge</span><div class="fd-bb-edge ' + row.tone + '">' + (row.edge === null ? '—' : row.edge.toFixed(1) + ' ' + row.unit) + '</div>' + (row.edge === null ? '' : meter(row.edge, max, Number.isFinite(mlEdge) ? mlEdge : null)) + '</td>' +
        '<td class="fd-bb-conf"><span class="fd-bb-cell">Confidence</span>' + (row.pct === null ? 'Simulation unavailable' : Number(row.pct).toFixed(1) + '% sim · exploratory') + '</td></tr>';
    }).join('');
    return '<table class="fd-bb-table"><thead><tr><th>Pick</th><th>Model</th><th>ML</th><th>DK</th><th>Edge</th><th>Confidence</th></tr></thead><tbody>' + body + '</tbody></table>';
  }
  function resultMarkup(block) {
    const cell = (label, item) => '<article><small>' + esc(label) + '</small><strong>' + (item.pct === null ? '—' : item.pct.toFixed(1) + '%') + '</strong><span>' + item.hits + '/' + item.n + '</span></article>';
    return '<section class="fd-bb-strip" aria-label="Latest graded week"><p class="fd-bb-kicker">Week ' + esc(block.week) + ' results</p><div class="fd-bb-strip-row">' +
      cell('Winners', block.winner) + cell('ATS', block.ats) + cell('O/U', block.ou) + cell('Props', block.props) +
      '<article class="fd-bb-even"><small>Break-even at -110</small><strong>52.4%</strong><span>Juice line</span></article></div></section>';
  }
  function mount(doc) {
    if (!doc || !doc.body || doc.body.classList.contains('fd-bb-plain')) return;
    doc.body.classList.add('fd-bb');
    const host = doc.getElementById('fd-betting-board');
    if (!host) return;
    const tableNode = doc.getElementById('fd-bb-table');
    const resultsNode = doc.getElementById('fd-bb-results');
    const slateNode = doc.getElementById('fd-bb-slate');
    let tab = 'games';
    let games = [];
    let props = [];
    const draw = () => {
      if (tableNode) tableNode.innerHTML = table(tab === 'props' ? props : games, tab === 'props' ? 15 : 8);
      doc.querySelectorAll('[data-fd-bb-tab]').forEach(button => button.setAttribute('aria-selected', String(button.dataset.fdBbTab === tab)));
    };
    doc.querySelectorAll('[data-fd-bb-tab]').forEach(button => button.addEventListener('click', () => { tab = button.dataset.fdBbTab; draw(); }));
    const get = path => fetch(path + '?t=' + Date.now(), {cache: 'no-store'}).then(response => response.ok ? response.json() : {}).catch(() => ({}));
    Promise.all([
      get('data/live-v2.json'),
      get('data/dk-game-odds.json'),
      get('data/simulations.json'),
      get('data/player-research.json'),
      get('data/dk-odds.json'),
      get('data/game-official-results.json'),
      get('data/player-results.json')
    ]).then(([forecast, odds, sims, research, dk, official, playerResults]) => {
      const now = Date.now();
      const upcoming = (forecast.games || []).filter(game => Date.parse(game.kickoff_utc) > now);
      const quotes = odds.games || [];
      const simGames = sims.games || [];
      games = upcoming.flatMap(game => {
        const quote = quotes.find(row => row.home === game.home && row.away === game.away) || {};
        const sim = simGames.find(row => row.game_id === game.game_id) || {};
        return gameEdgeRows(game, quote, sim).map(row => Object.assign({game: game.away + ' @ ' + game.home}, row, {pick: row.pick + ' · ' + game.away + ' @ ' + game.home}));
      }).sort((a, b) => (b.edge || 0) - (a.edge || 0));
      const slateIds = new Set(upcoming.map(game => String(game.kickoff_utc).slice(0, 16)));
      const lines = (dk.rows || []).filter(row => slateIds.has(String(row.commence_time).slice(0, 16)));
      props = propEdgeRows(research.players || research.rows || [], lines, sims.players || []);
      const week = latestWeek(official.rows || []);
      const weekRows = week ? (official.rows || []).filter(row => Number(row.season) === week.season && Number(row.week) === week.week) : [];
      const propRows = week ? (playerResults.rows || []).filter(row => String(row.game_id || '').startsWith(week.season + '_' + String(week.week).padStart(2, '0') + '_') && (row.recommendation_result === 'hit' || row.recommendation_result === 'miss')) : [];
      if (resultsNode && week) {
        resultsNode.innerHTML = resultMarkup({
          week: week.week,
          winner: gradeRate(weekRows, 'winner_result'),
          ats: gradeRate(weekRows, 'ats_result'),
          ou: gradeRate(weekRows, 'ou_result'),
          props: {hits: propRows.filter(row => row.recommendation_result === 'hit').length, n: propRows.length, pct: propRows.length ? 100 * propRows.filter(row => row.recommendation_result === 'hit').length / propRows.length : null}
        });
      }
      if (slateNode) {
        const finals = weekRows.slice().sort((a, b) => Date.parse(b.kickoff_utc) - Date.parse(a.kickoff_utc));
        const upcomingHtml = upcoming.map(game => {
          const edges = gameEdgeRows(game, quotes.find(row => row.home === game.home && row.away === game.away) || {}, simGames.find(row => row.game_id === game.game_id) || {});
          const lead = edges.find(row => row.edge !== null);
          const ml = ((game.game_ml_shadow || {}).markets || {});
          return '<details class="fd-bb-row"><summary><span class="fd-bb-teams"><img alt="" src="' + esc(logo(game.away)) + '">' + esc(game.away) + ' @ <img alt="" src="' + esc(logo(game.home)) + '">' + esc(game.home) + '</span><span>Upcoming</span><b class="fd-bb-edge pos">' + (lead ? '+' + lead.edge.toFixed(1) : '—') + '</b></summary><div class="fd-bb-detail"><div><small>Official model</small><b>' + num(game.projected_away_score).toFixed(1) + ' – ' + num(game.projected_home_score).toFixed(1) + '</b></div><div><small>ML projection, research</small><b>' + (mlCandidate(ml.game_total) === null ? '—' : mlCandidate(ml.game_total).toFixed(1) + ' total') + '</b></div><div><small>Top official edge</small><b>' + esc(lead ? lead.pick : '—') + '</b></div></div></details>';
        }).join('');
        const chip = result => '<b class="fd-bb-' + (result || 'none') + '">' + (result === 'hit' ? 'Hit' : result === 'miss' ? 'Miss' : result === 'push' ? 'Push' : '—') + '</b>';
        const finalHtml = finals.map(row => '<details class="fd-bb-row"><summary><span class="fd-bb-teams"><img alt="" src="' + esc(logo(row.away)) + '">' + esc(row.away) + ' @ <img alt="" src="' + esc(logo(row.home)) + '">' + esc(row.home) + '</span><span>Final ' + row.away_score + '–' + row.home_score + '</span>' + chip(row.winner_result) + '</summary><div class="fd-bb-detail"><div><small>Winner</small>' + chip(row.winner_result) + '</div><div><small>ATS</small>' + chip(row.ats_result) + '</div><div><small>O/U</small>' + chip(row.ou_result) + '</div></div></details>').join('');
        slateNode.innerHTML = upcomingHtml + finalHtml;
      }
      draw();
    }).catch(() => { if (tableNode) tableNode.textContent = 'Best edges are waiting for the published forecast.'; });
    draw();
  }
  return {confidenceWords, mlCandidate, gameEdgeRows, propEdgeRows, propSimulationRate, findPropSimulation, gradeRate, latestWeek, meter, table, mount};
});
