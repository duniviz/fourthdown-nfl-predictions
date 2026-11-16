'use strict';
const assert = require('node:assert/strict');
const {decide,localParts} = require('../scripts/sunday_preset_backstop_policy');
const at = stamp => Date.parse(stamp);
const game = {kickoff_utc:'2026-11-15T18:00:00Z'}; // Noon Central in November
const late = at('2026-11-15T17:07:00Z'); // 11:07 Central
assert.deepEqual([localParts(late).day,localParts(late).minuteOfDay],['Sun',667]);
assert.equal(decide(late,[],[game]).action,'dispatch');
assert.equal(decide(late,[{head_branch:'main',event:'schedule',created_at:'2026-11-15T17:01:00Z'}],[game]).action,'ignore');
assert.equal(decide(late,[{head_branch:'main',event:'workflow_dispatch',created_at:'2026-11-15T16:59:00Z'}],[game]).action,'ignore');
assert.equal(decide(late,[{head_branch:'feature',event:'schedule',created_at:'2026-11-15T17:01:00Z'}],[game]).action,'dispatch');
assert.equal(decide(late,[],[]).action,'ignore');
assert.equal(decide(at('2026-11-15T17:20:00Z'),[],[{kickoff_utc:'2026-11-15T17:30:00Z'}]).action,'alert'); // Less than 25m to kickoff
assert.equal(decide(at('2026-11-15T17:37:00Z'),[],[game]).action,'ignore'); // Outside recovery window
assert.equal(decide(at('2026-11-15T18:05:00Z'),[],[game]).action,'ignore'); // Already kicked
assert.equal(decide(at('2026-11-16T17:07:00Z'),[],[game]).action,'ignore');
assert.equal(decide(at('2026-07-12T16:07:00Z'),[],[{kickoff_utc:'2026-07-12T17:00:00Z'}]).action,'dispatch'); // CDT
assert.equal(decide(at('2026-11-15T14:07:00Z'),[],[{kickoff_utc:'2026-11-15T14:30:00Z'}]).action,'alert'); // Early game cutoff
// A failed primary isn't enough: automatically recover once, only kickoff-safe.
const failed={head_branch:'main',event:'schedule',status:'completed',
  conclusion:'failure',created_at:'2026-11-15T17:01:00Z'};
const good={...failed,conclusion:'success'};
const active={...failed,status:'in_progress',conclusion:null};
const recovery={...failed,event:'workflow_dispatch',created_at:'2026-11-15T17:06:00Z'};
assert.equal(decide(late,[failed],[game]).action,'dispatch');
assert.equal(decide(late,[good],[game]).action,'ignore');
assert.equal(decide(late,[active],[game]).action,'ignore');
assert.equal(decide(late,[failed,{...recovery,conclusion:'success'}],[game]).action,'ignore');
assert.equal(decide(late,[failed,{...recovery,conclusion:'failure'}],[game]).action,'alert');
assert.equal(decide(late,[failed,{...recovery,status:'queued',conclusion:null}],[game]).action,'ignore');
assert.equal(decide(at('2026-11-15T17:20:00Z'),[failed],
  [{kickoff_utc:'2026-11-15T17:30:00Z'}]).action,'alert');
console.log('Sunday preset missed-run fallback tests passed');
