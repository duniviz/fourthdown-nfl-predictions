'use strict';
const assert = require('node:assert/strict');
const {policy} = require('../scripts/verified_data_recovery_policy');
const now = Date.parse('2026-11-15T20:00:00Z');
const id = 'publish-espn-scoreboard.yml';
const run = {id:23,name:'Publish ESPN scoreboard backup',head_branch:'main',event:'schedule',
  created_at:'2026-11-15T19:45:00Z',status:'completed',conclusion:'failure',run_attempt:1};
assert.equal(policy(id,[run],now).action,'retry');
assert.equal(policy('publish-v2.yml',[run],now).action,'ignore');
assert.equal(policy('daily-dk-player-props.yml',[run],now).action,'ignore');
assert.equal(policy(id,[{...run,run_attempt:2}],now).action,'escalate');
assert.equal(policy(id,[{...run,conclusion:'success'}],now).action,'ignore');
assert.equal(policy(id,[{...run,event:'workflow_dispatch'}],now).action,'ignore');
assert.equal(policy(id,[{...run,head_branch:'feature'}],now).action,'ignore');
assert.equal(policy(id,[{...run,created_at:'2026-11-15T19:58:00Z'}],now).action,'ignore');
assert.equal(policy(id,[{...run,created_at:'2026-11-15T16:00:00Z'}],now).action,'ignore');
assert.equal(policy(id,[run,{...run,id:24,status:'in_progress',created_at:'2026-11-15T19:48:00Z'}],now).action,'ignore');
assert.equal(policy('refresh-game-context.yml',[{...run,name:'Refresh verified game context'}],now).action,'retry');
assert.equal(policy(id,[],now).action,'ignore'); // Missed schedule: alert separately; never blindly dispatch writer.
console.log('Verified-data recovery allowlist, bounded retries, and exclusions passed');
