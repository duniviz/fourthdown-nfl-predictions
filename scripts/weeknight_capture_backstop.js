'use strict';

// Read-only decision for an independent UTC-scheduled pregame watchdog.
// The existing capture workflow remains the only odds and snapshot writer.
function decide(now, games, state, locks, runs) {
  if (!Array.isArray(games) || !games.length) throw new Error('Missing published game schedule');
  const weekday = new Intl.DateTimeFormat('en-US', {timeZone: 'America/Chicago', weekday: 'short'});
  const active = (runs || []).some(r => r.status !== 'completed' &&
    Number.isFinite(Date.parse(r.created_at)) && now - Date.parse(r.created_at) < 60 * 60 * 1000);
  if (active) return {action: 'wait', reason: 'capture workflow already running or queued'};
  const entries = Object.entries((state || {}).refreshes || {});
  for (const g of games) {
    const kickoff = Date.parse(g.kickoff_utc || '');
    const lead = kickoff - now;
    if (!g.game_id || !Number.isFinite(kickoff) || !['Mon', 'Thu'].includes(weekday.format(kickoff)) ||
        lead > 45 * 60000 || lead < 5 * 60000) continue;
    const entry = entries.find(([key]) => Date.parse(key) === kickoff);
    const progress = entry ? entry[1] : {};
    const refreshed = ['game_odds', 'player_props'].every(k => progress?.[k]?.status === 'request_completed');
    const lock = (locks || []).find(r => r.game_id === g.game_id && Date.parse(r.kickoff_utc || '') === kickoff);
    const locked = lock && ['official', 'last_available', 'forecast_only'].includes(lock.lock_status);
    if (!refreshed || !locked) return {action: 'dispatch', game_id: g.game_id,
      reason: !refreshed ? 'game odds or player props not yet refreshed' : 'pregame lock not yet saved'};
  }
  return {action: 'none', reason: 'no incomplete Monday or Thursday game in the safe window'};
}
module.exports = {decide};
