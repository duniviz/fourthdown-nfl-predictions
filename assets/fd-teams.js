/* One fan-facing abbreviation for clubs whose feeds disagree. */
(function (root, factory) {
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  root.fdTeams = api;
})(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  // Logos, CSS, and existing match keys already use WAS, JAC, and LAR.
  const DISPLAY = {WSH: 'WAS', JAX: 'JAC', LA: 'LAR'};
  function label(value) {
    const key = String(value || '').trim().toUpperCase();
    return DISPLAY[key] || key;
  }
  // dk home spread is stored from the home team's perspective. Keep the number; name the team.
  function homeSpread(home, value) {
    if (value === null || value === undefined || value === '') return '';
    const n = Number(value);
    if (!Number.isFinite(n)) return '';
    return label(home) + ' ' + (n > 0 ? '+' : '') + n.toFixed(1);
  }
  return {DISPLAY, label, homeSpread};
});
