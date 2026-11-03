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
  // Tuesday's 8 AM CT rollover previews the next Thursday-through-Monday slate.
  function get(now) {
    now = now || new Date(); const p = parts(now), weekday = DAY[p.weekday], hour = Number(p.hour), minute = Number(p.minute);
    const afterTuesdayRollover = weekday === DAY.Tue && (hour > 8 || (hour === 8 && minute >= 0));
    const startOffset = weekday === DAY.Tue ? (afterTuesdayRollover ? 2 : -5) : weekday === DAY.Wed ? 1 : -((weekday - DAY.Thu + 7) % 7);
    const start = addDays(Number(p.year), Number(p.month), Number(p.day), startOffset);
    const end = addDays(start.date.getUTCFullYear(), start.date.getUTCMonth() + 1, start.date.getUTCDate(), 4);
    const requestEnd = addDays(end.date.getUTCFullYear(), end.date.getUTCMonth() + 1, end.date.getUTCDate(), 1);
    return {start: start.key, end: end.key, requestEnd: requestEnd.key, query: start.key + '-' + requestEnd.key};
  }
  function centralDateKey(value) { const time = Date.parse(value); if (!Number.isFinite(time)) return ''; const p = parts(new Date(time)); return p.year + String(p.month).padStart(2, '0') + String(p.day).padStart(2, '0'); }
  function contains(window, value) { const key = centralDateKey(value); return !!key && key >= window.start && key <= window.end; }
  return {ZONE, get, contains, centralDateKey};
});
