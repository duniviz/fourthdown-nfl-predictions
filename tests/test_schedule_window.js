const assert = require('assert');
const slate = require('../schedule-window.js');
function at(iso) { return slate.get(new Date(iso)); }
assert.strictEqual(at('2026-11-10T05:59:59Z').query, '20261105-20261110'); // Monday 11:59 PM CT
assert.deepStrictEqual(at('2026-11-10T06:00:00Z'), {start: '20261105', end: '20261109', requestEnd: '20261110', query: '20261105-20261110'}); // Tuesday midnight CT stays on prior slate
assert.strictEqual(at('2026-11-10T13:00:00Z').query, '20261112-20261117');
assert.strictEqual(at('2026-11-11T18:00:00Z').query, '20261112-20261117');
assert.strictEqual(at('2026-11-16T18:00:00Z').query, '20261112-20261117');
assert.strictEqual(slate.contains(at('2026-11-10T12:00:00Z'), '2026-11-13T01:15:00Z'), true);
assert.strictEqual(slate.contains(at('2026-11-10T12:00:00Z'), '2026-11-17T02:15:00Z'), true); // Monday night CT
assert.strictEqual(slate.contains(at('2026-11-10T12:00:00Z'), '2026-11-10T02:15:00Z'), false);
assert.strictEqual(at('2026-09-08T04:59:59Z').start, '20260903'); // daylight time boundary
assert.strictEqual(at('2026-09-08T05:00:00Z').start, '20260903'); // Tuesday midnight CDT stays on prior slate
assert.strictEqual(at('2026-09-08T10:59:59Z').start, '20260903'); // Tuesday 5:59 a.m. CDT
assert.strictEqual(at('2026-09-08T11:00:00Z').start, '20260910'); // Tuesday 6:00 a.m. CDT
assert.deepStrictEqual(slate.scoreboardDates(at('2026-11-10T12:00:00Z')), ['20261112', '20261113', '20261114', '20261115', '20261116']);
assert.ok(slate.scoreboardDates(at('2026-11-10T06:00:00Z')).every(day => /^\d{8}$/.test(day)));
const splitNow = Date.parse('2026-11-17T13:17:00Z'); // Tuesday morning CT
const groups = slate.splitGames([
  {id:'last-night',state:'pre',date:'2026-11-17T01:15:00Z'},
  {id:'next-game',state:'pre',date:'2026-11-20T01:15:00Z'},
  {id:'in-progress',state:'in',date:'2026-11-17T12:00:00Z'},
  {id:'final',state:'post',date:'2026-11-16T18:00:00Z'}
], splitNow);
assert.deepStrictEqual(groups.live.map(g=>g.id), ['in-progress']);
assert.deepStrictEqual(groups.upcoming.map(g=>g.id), ['next-game']);
assert.deepStrictEqual(groups.finals.map(g=>g.id), ['final']);
console.log('schedule-window tests passed');
