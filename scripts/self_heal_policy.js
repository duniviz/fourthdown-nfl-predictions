'use strict';

// Keep all automatic recovery limited to the read-only watchdog.
const NAME = 'FOURTHDOWN independent operations watchdog';
const MAX_AGE_MS = 4 * 60 * 60 * 1000;
const MISSING_MS = 4 * 60 * 60 * 1000;

function asTime(value) {
  const result = Date.parse(value || '');
  return Number.isFinite(result) ? result : 0;
}
function inScope(run, nowMs) {
  return !!run && run.name === NAME && run.head_branch === 'main' &&
    ['schedule', 'workflow_dispatch'].includes(run.event) &&
    asTime(run.created_at) > 0 &&
    nowMs - asTime(run.created_at) >= 0 &&
    nowMs - asTime(run.created_at) <= MAX_AGE_MS;
}
function decide(run, nowMs) {
  if (!inScope(run, nowMs) || run.status !== 'completed') return 'ignore';
  if (!['failure', 'timed_out'].includes(run.conclusion)) return 'ignore';
  if (!Number.isInteger(run.run_attempt) || run.run_attempt < 1) return 'ignore';
  return run.run_attempt === 1 ? 'retry' : 'escalate';
}
function missing(runs, nowMs) {
  // A dispatch or scheduled run in the last four hours is enough, even if still queued.
  return !(runs || []).some(run => inScope(run, nowMs));
}
module.exports = { NAME, MAX_AGE_MS, MISSING_MS, inScope, decide, missing };
