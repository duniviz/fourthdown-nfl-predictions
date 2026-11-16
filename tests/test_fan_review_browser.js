const {chromium} = require('playwright');
const assert = require('node:assert/strict');
const fs = require('fs');

function chromePath() {
  if (process.env.CHROME_PATH) return process.env.CHROME_PATH;
  const candidates = ['/usr/bin/google-chrome', '/usr/local/bin/google-chrome', '/usr/bin/chromium', '/usr/bin/chromium-browser'];
  return candidates.find(path => fs.existsSync(path)) || '/usr/bin/google-chrome';
}

(async () => {
  const browser = await chromium.launch({
    headless: true,
    executablePath: chromePath(),
    args: ['--no-sandbox', '--disable-dev-shm-usage']
  });
  for (const width of [400, 1440]) {
    const page = await browser.newPage({viewport: {width, height: 900}});
    const errors = [];
    page.on('pageerror', error => errors.push(error.message));

    await page.goto('http://127.0.0.1:8123/model-lab.html', {waitUntil: 'domcontentloaded'});
    await page.waitForFunction(() => /verified score ledger/.test(document.querySelector('#fd-weekly-report-card')?.innerText || ''));
    const lab = await page.locator('#fd-weekly-report-card').innerText();
    assert.match(lab, /12 completed games on the verified score ledger/);
    assert.match(lab, /only included 2 final games/);
    assert.equal(await page.locator('#fd-weekly-report-card').getAttribute('data-fd-report-source'), 'official');
    assert.doesNotMatch(lab, /2 completed games graded/);

    await page.goto('http://127.0.0.1:8123/bets.html', {waitUntil: 'domcontentloaded'});
    assert.equal(await page.locator('.fd-about-data').evaluate(node => node.open), false);
    await page.locator('.fd-about-data > summary').click();
    await page.waitForFunction(() => /907/.test(document.querySelector('#bet-record')?.innerText || '') && /History only counts/.test(document.querySelector('#bet-pick-scope')?.innerText || ''));
    const props = await page.locator('#bet-record').innerText();
    assert.match(props, /907/);
    assert.match(await page.locator('#bet-pick-scope').innerText(), /838/);
    assert.match(await page.locator('#bet-pick-scope').innerText(), /JAX at BAL/);
    if (width === 400) {
      const market = await page.locator('#bet-market').boundingBox();
      const search = await page.locator('#bet-player-search').boundingBox();
      assert.ok(market.width >= 280, 'market filter is wide enough to read at 400px');
      assert.ok(search.width >= 280, 'search field is wide enough at 400px');
      assert.ok(search.y >= market.y + market.height - 2, 'search sits on its own row');
      const selected = await page.locator('#bet-market option:checked').innerText();
      assert.match(selected, /All yard markets/);
    }

    await page.goto('http://127.0.0.1:8123/history.html', {waitUntil: 'domcontentloaded'});
    await page.waitForFunction(() => /Verified picks/.test(document.querySelector('#fd-player-dataset')?.innerText || ''));
    await page.waitForFunction(() => /game-score row/.test(document.querySelector('#fd-pick-scope')?.innerText || ''));
    assert.match(await page.locator('#fd-player-dataset').innerText(), /838/);
    assert.match(await page.locator('#fd-pick-scope').innerText(), /907|69/);
    assert.match(await page.locator('#fd-pick-scope').innerText(), /Props also includes/);

    await page.goto('http://127.0.0.1:8123/index.html', {waitUntil: 'domcontentloaded'});
    await page.locator('#fd-desk-games > summary').click();
    await page.waitForFunction(() => /games/.test(document.querySelector('#score-status')?.innerText || ''));
    await page.waitForFunction(() => {
      const text = document.querySelector('#fd-live-board-status')?.innerText || '';
      return text && !/Loading live games/.test(text);
    });
    const board = await page.locator('#fd-live-board-status').innerText();
    const scoreStatus = await page.locator('#score-status').innerText();
    assert.doesNotMatch(board, /unavailable/, 'fresh scoreboard must not be described as unavailable');
    if (/in progress/.test(scoreStatus)) assert.match(board, /in progress/);
    else assert.match(board, /No games in progress/);
    await page.waitForSelector('#scoreboard-cards .scorecard');
    const finalTexts = await page.locator('#scoreboard-cards .scorecard').filter({hasText: 'FINAL'}).allInnerTexts();
    assert.ok(finalTexts.length > 0, 'expected at least one final game card');
    assert.ok(finalTexts.every(text => !/Matching game simulation unavailable/.test(text)));
    assert.ok(finalTexts.some(text => /No win simulation was saved for this finished game/.test(text) && /archived forecast and grade/.test(text)));
    await page.locator('#fd-desk-more > summary').click();
    await page.waitForFunction(() => document.querySelectorAll('#fd-top-picks-list .fd-top-pick').length > 0);
    const pickCount = await page.locator('#fd-top-picks-list .fd-top-pick').count();
    const title = await page.locator('#fd-top-picks-title').innerText();
    if (pickCount < 5) {
      assert.equal(title, 'Top Picks');
      assert.match(await page.locator('#fd-top-picks-status').innerText(), new RegExp(pickCount + ' qualifying pick'));
    } else {
      assert.equal(title, 'Top 5 Picks');
    }
    assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth + 1), true, 'no horizontal overflow at ' + width);
    assert.deepEqual(errors, [], 'page errors at ' + width);
    await page.close();
    console.log('fan review browser ' + width + 'px passed');
  }

  const failed = await browser.newPage({viewport: {width: 1200, height: 800}});
  await failed.route('https://site.api.espn.com/**', route => route.abort());
  await failed.route('**/espn-scoreboard-backup.json*', route => route.fulfill({status: 500, body: 'nope'}));
  await failed.goto('http://127.0.0.1:8123/index.html', {waitUntil: 'domcontentloaded'});
  await failed.waitForFunction(() => /Live scores are unavailable/.test(document.querySelector('#fd-live-board-status')?.innerText || ''), null, {timeout: 20000});
  assert.match(await failed.locator('#score-status').innerText(), /unavailable/);
  await failed.close();

  const finalsOnly = await browser.newPage({viewport: {width: 1200, height: 800}});
  await finalsOnly.goto('http://127.0.0.1:8123/index.html', {waitUntil: 'domcontentloaded'});
  await finalsOnly.waitForFunction(() => Array.isArray(window.fdAllGames) && window.fdAllGames.length > 0);
  await finalsOnly.evaluate(() => {
    window.fdAllGames = window.fdAllGames.filter(game => game.state === 'post');
    window.fdScoreboardFeed = 'ok';
    window.dispatchEvent(new CustomEvent('fd-scoreboard-updated'));
  });
  await finalsOnly.waitForFunction(() => /No games in progress/.test(document.querySelector('#fd-live-board-status')?.innerText || ''));
  assert.doesNotMatch(await finalsOnly.locator('#fd-live-board-status').innerText(), /unavailable/);
  assert.match(await finalsOnly.locator('#fd-live-board-status').innerText(), /Latest finals shown/);
  await finalsOnly.close();
  await browser.close();
  console.log('fan review browser tests passed');
})().catch(error => {
  console.error(error);
  process.exit(1);
});
