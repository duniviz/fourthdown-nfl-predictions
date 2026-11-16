/* FOURTHDOWN published-feed freshness. Never claims an update unless timestamps advance. */
const FD_STALE_LINE_HOURS = 26;
function freshnessModel(forecastIso, oddsIso, now) {
  const forecastAt = Date.parse(forecastIso || '');
  const oddsAt = Date.parse(oddsIso || '');
  const clock = Number.isFinite(now) ? now : Date.now();
  if (!Number.isFinite(forecastAt) || !Number.isFinite(oddsAt)) {
    return {text: 'Could not verify update times', stale: true};
  }
  const hours = stamp => Math.max(0, (clock - stamp) / 3600000);
  const amount = value => {
    if (value < 1) return Math.max(1, Math.round(value * 60)) + 'm';
    const rounded = value < 10 ? Math.round(value * 10) / 10 : Math.round(value);
    return String(rounded).replace(/\.0$/, '') + 'h';
  };
  const lineHours = hours(oddsAt);
  return {
    text: 'Updated ' + amount(hours(forecastAt)) + ' ago · DK lines ' + amount(lineHours) + ' old',
    stale: lineHours > FD_STALE_LINE_HOURS
  };
}
function mountFreshness() {
  if (typeof document === 'undefined') return;
  const badge = document.getElementById('fd-freshness-badge');
  const banner = badge || document.createElement('p');
  if (!badge) {
    banner.id = 'fd-freshness-badge';
    banner.className = 'fd-freshness-badge';
    const top = document.querySelector('header') || document.body.firstElementChild;
    if (top && top.parentNode) top.insertAdjacentElement('afterend', banner);
    else document.body.prepend(banner);
  }
  banner.setAttribute('role', 'status');
  banner.setAttribute('aria-live', 'polite');
  banner.textContent = 'Checking update times…';
  let previous = null;
  async function check() {
    try {
      const [forecastResponse, oddsResponse] = await Promise.all([
        fetch('data/live-v2.json?freshness=' + Date.now(), {cache: 'no-store'}),
        fetch('data/dk-game-odds.json?freshness=' + Date.now(), {cache: 'no-store'})
      ]);
      if (!forecastResponse.ok || !oddsResponse.ok) throw Error('published feed unavailable');
      const [forecast, odds] = await Promise.all([forecastResponse.json(), oddsResponse.json()]);
      const model = freshnessModel(forecast.generated_at_utc, odds.snapshot_date_utc, Date.now());
      banner.textContent = (model.stale ? 'Warning · ' : '') + model.text;
      banner.classList.toggle('is-stale', model.stale);
      const current = forecast.generated_at_utc + '|' + odds.snapshot_date_utc;
      if (previous && current !== previous && document.visibilityState === 'visible') {
        banner.textContent += ' · New data available — reloading';
        window.location.reload();
      }
      previous = current;
    } catch (_) {
      banner.textContent = 'Could not verify update times';
      banner.classList.add('is-stale');
    }
  }
  check();
  setInterval(check, 120000);
}
if (typeof document !== 'undefined') mountFreshness();
if (typeof module === 'object' && module.exports) module.exports = {freshnessModel, FD_STALE_LINE_HOURS};
