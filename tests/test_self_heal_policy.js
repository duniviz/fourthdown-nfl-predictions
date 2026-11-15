'use strict';
const assert = require('node:assert/strict');
const { decide, missing, NAME } = require('../scripts/self_heal_policy');
const now = Date.parse('2026-11-15T20:00:00Z');
const run = { name: NAME, head_branch: 'main', event: 'schedule',
  created_at: '2026-11-15T19:00:00Z', status: 'completed',
  conclusion: 'failure', run_attempt: 1 };
assert.equal(decide(run, now), 'retry');
assert.equal(decide({...run, run_attempt: 2}, now), 'escalate');
assert.equal(decide({...run, status: 'in_progress'}, now), 'ignore');
assert.equal(decide({...run, conclusion: 'success'}, now), 'ignore');
assert.equal(decide({...run, head_branch: 'feature'}, now), 'ignore');
assert.equal(decide({...run, event: 'pull_request'}, now), 'ignore');
assert.equal(decide({...run, name: 'Publish weekly v2 forecasts'}, now), 'ignore');
assert.equal(decide({...run, created_at: '2026-11-14T18:00:00Z'}, now), 'ignore');
assert.equal(missing([], now), true);
assert.equal(missing([run], now), false);
assert.equal(missing([{...run, created_at: '2026-11-15T14:00:00Z'}], now), true);
console.log('Safe retry and escalation policy tests passed');
