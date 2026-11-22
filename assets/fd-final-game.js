(function(root, factory) {
  if (typeof module === 'object' && module.exports) module.exports = factory();
  else root.FDFinalGame = factory();
})(typeof globalThis !== 'undefined' ? globalThis : this, function() {
  'use strict';
  const finite = v => v !== null && v !== undefined && v !== '' && Number.isFinite(Number(v));
  const canon = v => ({JAX:'JAC', LAR:'LA', WSH:'WAS'}[String(v || '').toUpperCase()] || String(v || '').toUpperCase());
  const escape = v => String(v == null ? '' : v).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const value = v => finite(v) ? Number(v).toFixed(1) : '—';
  const signed = v => Number(v) > 0 ? '+' + value(v) : value(v);

  function ats(game, lock, margin) {
    const spread = lock?.dk_home_spread;
    const kickoff = Date.parse(lock?.kickoff_utc || ''), captured = Date.parse(lock?.captured_at_utc || '');
    const quote = Date.parse(lock?.dk_at_utc || ''), observed = Date.parse(lock?.dk_home_spread_observed_at_utc || lock?.dk_at_utc || '');
    if (!finite(spread) || !finite(margin) || !Number.isFinite(kickoff) ||
        !Number.isFinite(captured) || !Number.isFinite(quote) || !Number.isFinite(observed) ||
        quote > captured || observed > captured || quote >= kickoff || observed >= kickoff) return null;
    const edge = Number(margin) + Number(spread);
    if (Math.abs(edge) < 0.05) return {pick:'No ATS lean', result:null};
    const homePick = edge > 0;
    const team = canon(homePick ? game.home?.abbr : game.away?.abbr);
    const line = homePick ? Number(spread) : -Number(spread);
    let result = null;
    if (finite(game.home?.score) && finite(game.away?.score)) {
      const actualEdge = Number(game.home.score) - Number(game.away.score) + Number(spread);
      result = Math.abs(actualEdge) < 1e-9 ? 'PUSH' : ((actualEdge > 0) === homePick ? 'HIT' : 'MISS');
    }
    return {pick: team + ' ' + (line === 0 ? 'PK' : signed(line)), result};
  }

  function savedLock(game, records) {
    const kick = Date.parse(game?.date || '');
    if (!Number.isFinite(kick)) return null;
    const found = (Array.isArray(records) ? records : []).filter(r => {
      if (!r || !['official', 'last_available', 'forecast_only'].includes(r.lock_status)) return false;
      const rk = Date.parse(r.kickoff_utc || ''), fc = Date.parse(r.forecast_at_utc || ''), captured = Date.parse(r.captured_at_utc || '');
      return canon(r.home) === canon(game.home?.abbr) && canon(r.away) === canon(game.away?.abbr) &&
        Number.isFinite(rk) && Math.abs(rk - kick) <= 15 * 60000 &&
        Number.isFinite(fc) && Number.isFinite(captured) && fc <= captured && captured < rk &&
        finite(r.projected_away_score) && finite(r.projected_home_score) &&
        Number(r.projected_away_score) >= 0 && Number(r.projected_home_score) >= 0;
    });
    return found.length === 1 ? found[0] : null;
  }

  function render(game, records) {
    const away = escape(canon(game.away?.abbr)), home = escape(canon(game.home?.abbr));
    const finalAway = finite(game.away?.score) ? escape(game.away.score) : '—';
    const finalHome = finite(game.home?.score) ? escape(game.home.score) : '—';
    const lock = savedLock(game, records);
    const row = (name, tag, a, h, margin) => {
      const selection = ats(game, lock, margin);
      const atsText = selection ? escape(selection.pick) + (selection.result ? ' · ' + selection.result : '') : 'Unavailable';
      return '<div class="fd-final-forecast-row"><div><strong>' + name + '</strong><small>' + tag + '</small></div><b>' + away + ' ' + value(a) + ' · ' + home + ' ' + value(h) + '</b><span>Total ' + value(Number(a) + Number(h)) + '</span><span class="fd-final-ats">ATS: <strong>' + atsText + '</strong></span></div>';
    };
    let predictions = '<p class="fd-modal-muted">No verified pregame forecast was saved for this matchup.</p>';
    if (lock) {
      const spread = ats(game, lock, 0);
      const lineText = spread ? home + ' ' + (Number(lock.dk_home_spread) === 0 ? 'PK' : signed(lock.dk_home_spread)) : 'Unavailable';
      const regularMargin = finite(lock.projected_margin_home) ? Number(lock.projected_margin_home) : Number(lock.projected_home_score)-Number(lock.projected_away_score);
      predictions = '<div class="fd-final-forecasts"><h4>Saved pregame projections</h4><p class="fd-modal-muted fd-final-line">Saved DK spread: ' + lineText + '</p>' + row('Current model', 'PREGAME', lock.projected_away_score, lock.projected_home_score, regularMargin);
      const markets = lock.game_ml_shadow?.markets || {};
      const margin = markets.game_margin_home?.candidate, total = markets.game_total?.candidate;
      if (finite(margin) && finite(total) && Number(total) >= Math.abs(Number(margin))) {
        predictions += row('Machine learning', 'SAVED RESEARCH ESTIMATE', (Number(total)-Number(margin))/2, (Number(total)+Number(margin))/2, Number(margin));
        predictions += '<p class="fd-modal-muted">ML estimate saved with the forecast; an independently selected card model may have differed.</p>';
      } else {
        predictions += '<p class="fd-modal-muted">No complete pregame ML estimate was saved for this game.</p>';
      }
      predictions += '</div>';
    }
    return '<div class="fd-modal-pick fd-final-result"><h3>Final score</h3><div class="fd-modal-scores"><div><small>' + away + '</small>' + finalAway + '</div><small>FINAL</small><div><small>' + home + '</small>' + finalHome + '</div></div>' + predictions + '</div>';
  }
  return {savedLock, ats, render};
});
