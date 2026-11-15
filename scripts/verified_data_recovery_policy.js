'use strict';
/** Strict allowlist: ONLY independently sourced backup data writers.
 * No game locks, forecasts, DK quotes, model training, or publishing.
 */
const ALLOWED = Object.freeze({
  'publish-espn-scoreboard.yml': 'Publish ESPN scoreboard backup',
  'refresh-game-context.yml': 'Refresh verified game context'
});
const MIN_AGE_MS = 5 * 60 * 1000;
const MAX_AGE_MS = 2 * 60 * 60 * 1000;
function policy(workflow, runs, now) {
  if (!Object.prototype.hasOwnProperty.call(ALLOWED, workflow)) return {action:'ignore', reason:'not allowed'};
  const relevant = (runs || []).filter(r => r && r.name === ALLOWED[workflow] &&
      r.head_branch === 'main' && r.event === 'schedule' && Number.isFinite(Date.parse(r.created_at)));
  relevant.sort((a,b) => Date.parse(b.created_at)-Date.parse(a.created_at));
  if (!relevant.length) return {action:'ignore', reason:'no scheduled run'};
  const latest = relevant[0];
  const age = now - Date.parse(latest.created_at);
  if (age < MIN_AGE_MS || age > MAX_AGE_MS) return {action:'ignore', reason:'outside retry window'};
  if (latest.status !== 'completed') return {action:'ignore', reason:'ongoing run'};
  if (!['failure','timed_out'].includes(latest.conclusion)) return {action:'ignore', reason:'not failed'};
  if (latest.run_attempt !== 1) return {action:'escalate', reason:'retry exhausted', run:latest};
  // Do not rerun if ANY newer run of this workflow is in flight, including manual runs.
  if ((runs || []).some(r => r && r.id !== latest.id &&
      r.name === ALLOWED[workflow] && r.head_branch === 'main' &&
      r.status !== 'completed' && Date.parse(r.created_at) >= Date.parse(latest.created_at))) {
    return {action:'ignore', reason:'newer run already active'};
  }
  return {action:'retry', run:latest};
}
module.exports = {ALLOWED, policy};
