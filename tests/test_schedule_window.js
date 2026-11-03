const assert = require('assert');
const slate = require('../schedule-window.js');
function at(iso) { return slate.get(new Date(iso)); }
assert.deepStrictEqual(at('2026-11-03T13:59:00Z'), {start: '20261029', end: '20261102', requestEnd: '20261103', query: '20261029-20261103'});
assert.deepStrictEqual(at('2026-11-03T14:00:00Z'), {start: '20261105', end: '20261109', requestEnd: '20261110', query: '20261105-20261110'});
assert.strictEqual(slate.contains(at('2026-11-03T14:00:00Z'), '2026-11-06T01:15:00Z'), true);
assert.strictEqual(slate.contains(at('2026-11-03T14:00:00Z'), '2026-11-10T02:15:00Z'), true);
assert.strictEqual(slate.contains(at('2026-11-03T14:00:00Z'), '2026-11-03T01:15:00Z'), false);
assert.strictEqual(at('2026-11-04T18:00:00Z').query, '20261105-20261110');
assert.strictEqual(at('2026-11-09T18:00:00Z').query, '20261105-20261110');
assert.strictEqual(at('2026-11-10T13:59:00Z').query, '20261105-20261110');
console.log('schedule-window tests passed');
