const assert = require('assert');
const slate = require('../schedule-window.js');
function at(iso) { return slate.get(new Date(iso)); }
assert.strictEqual(at('2026-11-10T05:59:59Z').query, '20261105-20261110'); // Monday 11:59 PM CT
assert.deepStrictEqual(at('2026-11-10T06:00:00Z'), {start: '20261112', end: '20261116', requestEnd: '20261117', query: '20261112-20261117'});
assert.strictEqual(at('2026-11-10T13:00:00Z').query, '20261112-20261117');
assert.strictEqual(at('2026-11-11T18:00:00Z').query, '20261112-20261117');
assert.strictEqual(at('2026-11-16T18:00:00Z').query, '20261112-20261117');
assert.strictEqual(slate.contains(at('2026-11-10T06:00:00Z'), '2026-11-13T01:15:00Z'), true);
assert.strictEqual(slate.contains(at('2026-11-10T06:00:00Z'), '2026-11-17T02:15:00Z'), true); // Monday night CT
assert.strictEqual(slate.contains(at('2026-11-10T06:00:00Z'), '2026-11-10T02:15:00Z'), false);
assert.strictEqual(at('2026-09-08T04:59:59Z').start, '20260903'); // daylight time boundary
assert.strictEqual(at('2026-09-08T05:00:00Z').start, '20260910');
console.log('schedule-window tests passed');
