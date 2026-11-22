(function(root, factory) {
  if (typeof module === 'object' && module.exports) module.exports = factory();
  else root.FDFinalGame = factory();
})(typeof globalThis !== 'undefined' ? globalThis : this, function() {
  'use strict';
  const finite = v => v !== null && v !== undefined && v !== '' && Number.isFinite(Number(v));
  const canon = v => ({JAX:'JAC', LAR:'LA', WSH:'WAS'}[String(v || '').toUpperCase()] || String(v || '').toUpperCase());
  const escape = v => String(v == null ? '' : v).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const value = v => finite(v) ? Number(v).toFixed(1) : '—';

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
    const row = (name, tag, a, h) => '<div class="fd-final-forecast-row"><div><strong>' + name + '</strong><small>' + tag + '</small></div><b>' + away + ' ' + value(a) + ' · ' + home + ' ' + value(h) + '</b><span>Total ' + value(Number(a) + Number(h)) + '</span></div>';
    let predictions = '<p class="fd-modal-muted">No verified pregame forecast was saved for this matchup.</p>';
    if (lock) {
      predictions = '<div class="fd-final-forecasts"><h4>Saved pregame projections</h4>' + row('Current model', 'PREGAME', lock.projected_away_score, lock.projected_home_score);
      const markets = lock.game_ml_shadow?.markets || {};
      const margin = markets.game_margin_home?.candidate, total = markets.game_total?.candidate;
      if (finite(margin) && finite(total) && Number(total) >= Math.abs(Number(margin))) {
        predictions += row('Machine learning', 'SAVED RESEARCH ESTIMATE', (Number(total)-Number(margin))/2, (Number(total)+Number(margin))/2);
        predictions += '<p class="fd-modal-muted">ML estimate saved with the forecast; an independently selected card model may have differed.</p>';
      } else {
        predictions += '<p class="fd-modal-muted">No complete pregame ML estimate was saved for this game.</p>';
      }
      predictions += '</div>';
    }
    return '<div class="fd-modal-pick fd-final-result"><h3>Final score</h3><div class="fd-modal-scores"><div><small>' + away + '</small>' + finalAway + '</div><small>FINAL</small><div><small>' + home + '</small>' + finalHome + '</div></div>' + predictions + '</div>';
  }
  return {savedLock, render};
});
