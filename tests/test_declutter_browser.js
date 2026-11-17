const {chromium} = require('playwright');
const assert = require('node:assert/strict');
(async () => {
  const browser = await chromium.launch({headless: true, executablePath: process.env.CHROME_PATH || '/usr/bin/google-chrome', args: ['--no-sandbox']});
  const page = await browser.newPage({viewport: {width: 1280, height: 900}});
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  await page.route('https://site.api.espn.com/**', route => route.fulfill({json: {events: []}}));
  await page.route('https://api.github.com/**', route => route.fulfill({json: {workflow_runs: []}}));
  await page.goto('http://127.0.0.1:8123/index.html', {waitUntil: 'domcontentloaded'});
  await page.waitForSelector('#fd-freshness-badge');
  await page.waitForFunction(() => /Updated .+ ago · DK lines .+ old/.test(document.getElementById('fd-freshness-badge').textContent));
  assert.equal(await page.locator('.fd2-status').count(), 0);
  assert.equal(await page.getByText('PREGAME INTELLIGENCE').count(), 0);
  assert.equal(await page.locator('a[href="#parlays"], a[href="#tracking"], a[href="#picks"], a[href="#confidence-pool"]').count(), 0);
  assert.equal(await page.getByText('Pipeline Health / Refresh Status').count(), 0);
  assert.match(await page.locator('footer').innerText(), /Pipeline Health/);
  await page.waitForFunction(() => /52\.4%/.test(document.querySelector('#fd-bb-results')?.textContent || ''));
  assert.equal(await page.locator('#fd-desk-games').evaluate(node => node.open), true, 'Games should lead the home page expanded');
  assert.equal(await page.locator('#fd-desk-edges').evaluate(node => node.open), false, 'Best edges should be collapsed by default');
  const gamesBox = await page.locator('#fd-slate-pulse').boundingBox();
  const edgesSummaryBox = await page.locator('#fd-desk-edges > summary').boundingBox();
  assert.ok(gamesBox && edgesSummaryBox && gamesBox.y < edgesSummaryBox.y, 'games appear before Best edges');
  await page.locator('#fd-desk-edges > summary').click();
  const strip = await page.locator('#fd-bb-results').boundingBox();
  assert.ok(strip, 'Best edges results are available when expanded');
  assert.match(await page.locator('#fd-bb-results').innerText(), /52\.4%/);
  assert.equal(await page.locator('#fd-mini-coverage').count(), 0);
  await page.locator('#fd-desk-games').evaluate(node => { node.open = true; });
  await page.evaluate(() => {
    window.__openedMatchup = null;
    window.addEventListener('fd-open-matchup', event => { window.__openedMatchup = event.detail; }, {once:true});
    window.fdAllGames = Array.from({length:6}, (_, index) => ({
      id: 'browser-fixture-' + index, date: new Date(Date.now() + (index + 1) * 86400000).toISOString(),
      state: 'pre', status: 'Scheduled', away: {abbr:'NE', name:'New England Patriots', score:null},
      home: {abbr:'BUF', name:'Buffalo Bills', score:null}
    }));
    window.fdScoreboardFeed = 'ok';
    window.dispatchEvent(new CustomEvent('fd-scoreboard-updated'));
  });
  await page.locator('#fd-slate-pulse .fd-live-board-head>a').click();
  assert.equal(await page.locator('#fd-slate-pulse .fd-live-board-head>a').getAttribute('aria-expanded'), 'true');
  assert.equal(await page.locator('#scoreboard').isHidden(), true, 'All games expands compact cards without restoring the duplicate lower list');
  assert.ok(await page.locator('#fd-live-board-cards [data-game-id]').count() > 4, 'All games shows the full slate in the top scoreboard');
  await page.locator('#fd-live-board-cards [data-game-id]').first().click();
  await page.waitForFunction(() => !!window.__openedMatchup?.id, null, {timeout:10000});
  assert.ok(await page.evaluate(() => window.__openedMatchup.id), 'A scoreboard card opens its complete matchup');
  await page.locator('#fd-desk-more > summary').click();
  await page.waitForFunction(() => {
    const list = document.querySelector('#fd-top-picks-list');
    const status = document.querySelector('#fd-top-picks-status')?.textContent || '';
    return !!list?.querySelector('.fd-pick-reason') || (!!status && !/Loading/.test(status));
  });
  const pickReasons = page.locator('#fd-top-picks-list .fd-pick-reason');
  if (await pickReasons.count()) {
    await pickReasons.first().waitFor({state:'visible'});
  } else {
    assert.doesNotMatch(await page.locator('#fd-top-picks-status').innerText(), /Loading/);
  }
  assert.equal(await page.locator('#fd-folded-signals').evaluate(node => node.open), false);
  assert.equal(await page.locator('#fd-watch').count(), 1);
  assert.equal(await page.locator('#confidence-pool').count(), 1);
  const games = page.locator('a', {hasText: /^Games$/});
  assert.match(await games.first().getAttribute('href'), /#fd-slate-pulse/);
  await page.locator('#fd-desk-games').evaluate(node => { node.open = false; });
  await games.first().click();
  await page.waitForFunction(() => {
    const box = document.getElementById('scoreboard')?.getBoundingClientRect();
    const board = document.getElementById('fd-slate-pulse')?.getBoundingClientRect();
    return location.hash === '#fd-slate-pulse' && board && board.top < 320 && board.top > -40;
  });

  await page.goto('http://127.0.0.1:8123/bets.html', {waitUntil: 'domcontentloaded'});
  await page.waitForSelector('#bet-game');
  await page.waitForFunction(() => document.getElementById('bet-game')?.value === 'upcoming');
  assert.equal(await page.locator('#bet-game').inputValue(), 'upcoming');
  await page.waitForFunction(() => document.getElementById('research-dk-board')?.hidden === true);
  assert.equal(await page.getByText('Start here:').count(), 0);
  assert.equal(await page.locator('#fd-prop-help-tip').count(), 1);
  assert.equal(await page.locator('#fd-compare-panel').isHidden(), true);
  assert.equal(await page.locator('.fd-about-data').evaluate(node => node.open), false);
  assert.match(await page.locator('#bet-order').innerText(), /Largest edge/);

  await page.goto('http://127.0.0.1:8123/history.html', {waitUntil: 'domcontentloaded'});
  assert.equal(await page.locator('#fd-coverage-note').evaluate(node => node.open), false);
  assert.equal(await page.locator('#fd-mini-coverage').count(), 1);

  await page.goto('http://127.0.0.1:8123/model-lab.html', {waitUntil: 'domcontentloaded'});
  await page.waitForSelector('#fd-appeal-lab svg rect');
  assert.equal(await page.locator('#fd-appeal-lab polyline').count(), 0);
  await page.locator('.fd2-links .fd-more > summary').click();
  assert.match(await page.locator('.fd2-links').innerText(), /Model Lab/);
  await page.locator('.fd2-links .fd-more > summary').click();
  assert.equal(await page.locator('.clear-advanced').evaluate(node => node.open), false);

  await page.goto('http://127.0.0.1:8123/pipeline-health.html', {waitUntil: 'domcontentloaded'});
  assert.equal(await page.locator('.fd-workflow-log').evaluate(node => node.open), false);
  assert.equal(await page.locator('#runs').count(), 1);

  assert.deepEqual(errors, []);
  await browser.close();
  console.log('declutter browser checks passed');
})().catch(error => {
  console.error(error);
  process.exit(1);
});
