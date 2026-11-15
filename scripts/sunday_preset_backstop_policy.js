'use strict';
/** Read-only decision policy for recovering a missing Sunday preset run.
 * This NEVER directly updates odds, forecasts, model weights or frozen locks.
 */
const SLOT_MINUTES = [8 * 60, 11 * 60, 14 * 60 + 30, 18 * 60 + 45];
const MIN_DELAY_MINUTES = 5;
const MAX_DELAY_MINUTES = 24;
const MIN_KICKOFF_LEAD_MINUTES = 25;

function localParts(value) {
  const parts = new Intl.DateTimeFormat('en-US', {
    timeZone: 'America/Chicago', weekday: 'short', year: 'numeric', month: '2-digit',
    day: '2-digit', hour: '2-digit', minute: '2-digit', hourCycle: 'h23'
  }).formatToParts(new Date(value));
  const field = name => parts.find(p => p.type === name)?.value;
  return {date: field('year') + '-' + field('month') + '-' + field('day'),
    day: field('weekday'), minuteOfDay: Number(field('hour')) * 60 + Number(field('minute'))};
}

function decide(nowMs, runs, games) {
  const current = localParts(nowMs);
  if (current.day !== 'Sun') return {action:'ignore',reason:'not Sunday Central'};
  const slot = SLOT_MINUTES.find(s =>
    current.minuteOfDay - s >= MIN_DELAY_MINUTES &&
    current.minuteOfDay - s <= MAX_DELAY_MINUTES);
  if (slot === undefined) return {action:'ignore',reason:'not a Sunday recovery window'};
  const name = current.date + '/' + String(Math.floor(slot / 60)).padStart(2,'0') +
    ':' + String(slot % 60).padStart(2,'0');
  const existing = (runs || []).some(r => {
    if (!r || r.head_branch !== 'main' || !['schedule','workflow_dispatch'].includes(r.event)) return false;
    const started = Date.parse(r.created_at || '');
    if (!Number.isFinite(started) || started > nowMs) return false;
    const startedLocal = localParts(started);
    return startedLocal.date === current.date &&
      startedLocal.minuteOfDay >= slot - 20 &&
      startedLocal.minuteOfDay <= current.minuteOfDay;
  });
  if (existing) return {action:'ignore',reason:'preset already started',slot:name};
  const kickoffs = (games || []).map(g => Date.parse(g?.kickoff_utc || ''))
    .filter(t => Number.isFinite(t) && t > nowMs)
    .filter(t => localParts(t).date === current.date);
  if (!kickoffs.length) return {action:'ignore',reason:'no future Sunday games',slot:name};
  const soonest = Math.min(...kickoffs);
  if ((soonest - nowMs) / 60000 < MIN_KICKOFF_LEAD_MINUTES) {
    return {action:'alert',reason:'too close to kickoff for full refresh',slot:name};
  }
  return {action:'dispatch',reason:'scheduled Sunday preset missing',slot:name};
}

module.exports = {decide,localParts};
