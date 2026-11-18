(function (root) {
  'use strict';
  const teams = new Set('ari atl bal buf car chi cin cle dal den det gb hou ind jax kc lv lac lar mia min ne no nyg nyj phi pit sf sea tb ten wsh'.split(' '));
  const aliases = {jac: 'jax', la: 'lar', was: 'wsh'};

  function starterSourceUrl(source, team) {
    const url = String(source || '');
    // Keep the original source in saved records, but show people ESPN's web page.
    if (/^https:\/\/site\.api\.espn\.com\/apis\/site\/v2\/sports\/football\/nfl\/teams\/\d+\/depthcharts(?:[/?#]|$)/i.test(url)) {
      const code = String(team || '').trim().toLowerCase();
      const espnCode = aliases[code] || code;
      return teams.has(espnCode) ? 'https://www.espn.com/nfl/team/depth/_/name/' + espnCode : '';
    }
    return url;
  }
  if (typeof module !== 'undefined' && module.exports) module.exports = starterSourceUrl;
  if (root) root.fdStarterSourceUrl = starterSourceUrl;
})(typeof window !== 'undefined' ? window : null);
