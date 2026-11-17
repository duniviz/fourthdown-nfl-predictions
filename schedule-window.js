(function (root, factory) {
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  root.fdScheduleWindow = api;
})(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  const ZONE = 'America/Chicago';
  const DAY = {Sun: 0, Mon: 1, Tue: 2, Wed: 3, Thu: 4, Fri: 5, Sat: 6};
  function parts(now) {
    const values = new Intl.DateTimeFormat('en-US', {timeZone: ZONE, weekday: 'short', year: 'numeric', month: 'numeric', day: 'numeric', hour: '2-digit', minute: '2-digit', hourCycle: 'h23'}).formatToParts(now);
    return Object.fromEntries(values.filter(x => x.type !== 'literal').map(x => [x.type, x.value]));
  }
  function dateKey(date) { return date.getUTCFullYear() + String(date.getUTCMonth() + 1).padStart(2, '0') + String(date.getUTCDate()).padStart(2, '0'); }
  function addDays(year, month, day, days) { const date = new Date(Date.UTC(year, month - 1, day + days)); return {date, key: dateKey(date)}; }
  // A new slate begins at 6 a.m. Tuesday in Central time, after Monday's games.
  function get(now) {
    now = now || new Date(); const p = parts(now), weekday = DAY[p.weekday];
    const startOffset = weekday === DAY.Tue ? (Number(p.hour) >= 6 ? 2 : -5) : weekday === DAY.Wed ? 1 : -((weekday - DAY.Thu + 7) % 7);
    const start = addDays(Number(p.year), Number(p.month), Number(p.day), startOffset);
    const end = addDays(start.date.getUTCFullYear(), start.date.getUTCMonth() + 1, start.date.getUTCDate(), 4);
    const requestEnd = addDays(end.date.getUTCFullYear(), end.date.getUTCMonth() + 1, end.date.getUTCDate(), 1);
    return {start: start.key, end: end.key, requestEnd: requestEnd.key, query: start.key + '-' + requestEnd.key};
  }
  // ESPN's site scoreboard returns HTTP 400 for dates=YYYYMMDD-YYYYMMDD.
  // Each request has to be one calendar day. Thursday and Monday night games
  // are filed under that US slate day, so start through end is the full window.
  function scoreboardDates(window) {
    const keys = [];
    let year = Number(window.start.slice(0, 4)), month = Number(window.start.slice(4, 6)), day = Number(window.start.slice(6, 8));
    for (let i = 0; i < 8; i++) {
      const key = year + String(month).padStart(2, '0') + String(day).padStart(2, '0');
      keys.push(key);
      if (key === window.end) break;
      const next = addDays(year, month, day, 1);
      year = next.date.getUTCFullYear();
      month = next.date.getUTCMonth() + 1;
      day = next.date.getUTCDate();
    }
    return keys;
  }
  function centralDateKey(value) { const time = Date.parse(value); if (!Number.isFinite(time)) return ''; const p = parts(new Date(time)); return p.year + String(p.month).padStart(2, '0') + String(p.day).padStart(2, '0'); }
  function contains(window, value) { const key = centralDateKey(value); return !!key && key >= window.start && key <= window.end; }
  function splitGames(games, now) {
    now = Number.isFinite(Number(now)) ? Number(now) : Date.now();
    const rows = Array.isArray(games) ? games : [];
    return {
      live: rows.filter(g => g && g.state === 'in'),
      upcoming: rows.filter(g => g && g.state === 'pre' && Number.isFinite(Date.parse(g.date)) && Date.parse(g.date) > now),
      finals: rows.filter(g => g && g.state === 'post')
    };
  }
  return {ZONE, get, contains, centralDateKey, scoreboardDates, splitGames};
});
