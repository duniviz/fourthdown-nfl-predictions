/* FOURTHDOWN published-feed freshness indicator. Never claims an update unless data timestamps advance. */
(() => {
  const banner = document.createElement('div');
  banner.id = 'fd-feed-freshness';
  banner.setAttribute('role', 'status');
  banner.setAttribute('aria-live', 'polite');
  banner.style.cssText = 'padding:8px 14px;text-align:center;font:600 12px system-ui,sans-serif;background:#10283b;color:#c4e5ee;border-bottom:1px solid #35546b';
  banner.textContent = 'Checking published forecast and DraftKings timestamps…';
  const top = document.querySelector('header') || document.querySelector('.top') || document.body.firstElementChild;
  if (top && top.parentNode) top.insertAdjacentElement('afterend', banner);
  else document.body.prepend(banner);
  const fmt = (date) => new Intl.DateTimeFormat('en-US', {timeZone:'America/Chicago',month:'short',day:'numeric',hour:'numeric',minute:'2-digit',timeZoneName:'short'}).format(date);
  let previous = null;
  async function check() {
    try {
      const [forecastResponse, oddsResponse] = await Promise.all([
        fetch('data/live-v2.json?freshness=' + Date.now(), {cache:'no-store'}),
        fetch('data/dk-game-odds.json?freshness=' + Date.now(), {cache:'no-store'})
      ]);
      if (!forecastResponse.ok || !oddsResponse.ok) throw Error('published feed unavailable');
      const [forecast, odds] = await Promise.all([forecastResponse.json(),oddsResponse.json()]);
      const f = new Date(forecast.generated_at_utc);
      const d = new Date(odds.snapshot_date_utc);
      if (!Number.isFinite(f.getTime()) || !Number.isFinite(d.getTime())) throw Error('invalid timestamps');
      const stale = Date.now()-f.getTime()>26*3600000 || Date.now()-d.getTime()>26*3600000;
      banner.textContent = (stale ? '⚠ Published data may be stale · ' : 'Published data · ') +
        'Forecast: ' + fmt(f) + ' · DK lines: ' + fmt(d);
      banner.style.color = stale ? '#ffd18b' : '#b9f7dc';
      banner.style.background = stale ? '#3b2918' : '#10283b';
      const current = forecast.generated_at_utc + '|' + odds.snapshot_date_utc;
      if (previous && current !== previous && document.visibilityState === 'visible') {
        banner.textContent += ' · New data available — reloading';
        window.location.reload();
      }
      previous = current;
    } catch (_) {
      banner.textContent = '⚠ Could not verify published forecast and DraftKings freshness';
      banner.style.color = '#ffd18b';
      banner.style.background = '#3b2918';
    }
  }
  check();
  setInterval(check, 120000);
})();
