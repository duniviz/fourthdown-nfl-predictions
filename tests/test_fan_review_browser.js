const {chromium} = require('playwright');
const assert = require('node:assert/strict');
const fs = require('fs');
const {reportCardModel} = require('../assets/fd-insights.js');
const {ledgerGap} = require('../assets/fd-prop-board.js');
const performance = JSON.parse(fs.readFileSync('data/weekly-model-performance.json', 'utf8'));
const official = JSON.parse(fs.readFileSync('data/game-official-results.json', 'utf8'));
const players = JSON.parse(fs.readFileSync('data/player-results.json', 'utf8'));
const expectedCard = reportCardModel(performance, official, players);
const expectedGap = ledgerGap(players.rows, official.rows);

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
    await page.waitForFunction(() => document.querySelector('#fd-weekly-report-card')?.hasAttribute('data-fd-report-source'));
    const lab = await page.locator('#fd-weekly-report-card').innerText();
    assert.ok(expectedCard, 'expected a published weekly report');
    assert.equal(await page.locator('#fd-weekly-report-card').getAttribute('data-fd-report-source'), expectedCard.source);
    assert.ok(lab.includes(String(expectedCard.latest.completed_games) + ' completed games'));
    if (expectedCard.source === 'official') assert.match(lab, /verified score ledger/);

    await page.goto('http://127.0.0.1:8123/bets.html', {waitUntil: 'domcontentloaded'});
    assert.equal(await page.locator('.fd-about-data').evaluate(node => node.open), false);
    await page.locator('.fd-about-data > summary').click();
    await page.waitForFunction(n => (document.querySelector('#bet-record')?.innerText || '').includes(n), String(expectedGap.propsGraded));
    const props = await page.locator('#bet-record').innerText();
    assert.ok(props.includes(String(expectedGap.propsGraded)), 'props shows the current graded total');
    if (expectedGap.outside) {
      await page.waitForFunction(() => /History only counts/.test(document.querySelector('#bet-pick-scope')?.innerText || ''));
      const note=await page.locator('#bet-pick-scope').innerText();
      assert.ok(note.includes(String(expectedGap.historyGraded)));
      assert.match(note, /History only counts/);
    }
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
    await page.waitForFunction(n => (document.querySelector('#fd-player-dataset')?.innerText || '').includes(n), String(expectedGap.historyGraded));
    if (expectedGap.outside) {
      await page.waitForFunction(() => /game-score row/.test(document.querySelector('#fd-pick-scope')?.innerText || ''));
      const note=await page.locator('#fd-pick-scope').innerText();
      assert.ok(note.includes(String(expectedGap.outside)));
      assert.match(note, /Props also includes/);
    }

    await page.goto('http://127.0.0.1:8123/index.html', {waitUntil: 'domcontentloaded'});
    await page.waitForFunction(() => /games|unavailable/i.test(document.querySelector('#score-status')?.innerText || ''));
    await page.waitForFunction(() => {
      const text = document.querySelector('#fd-live-board-status')?.innerText || '';
      return text && !/Loading live games/.test(text);
    });
    const board = await page.locator('#fd-live-board-status').innerText();
    const scoreStatus = await page.locator('#score-status').innerText();
    if (/unavailable/i.test(board)) {
      assert.match(scoreStatus, /unavailable/i);
    } else {
      if (/in progress/.test(scoreStatus)) assert.match(board, /in progress/);
      else assert.match(board, /No games in progress/);
      // The current slate can have no legacy scorecards (the compact board is
      // the primary view), so check final-card wording when cards exist.
      const finalTexts = await page.locator('#scoreboard-cards .scorecard').filter({hasText: 'FINAL'}).allInnerTexts();
      assert.ok(finalTexts.every(text => !/Matching game simulation unavailable/.test(text)));
      if (finalTexts.length) assert.ok(finalTexts.some(text => /No win simulation was saved for this finished game/.test(text) && /archived forecast and grade/.test(text)));
      await page.locator('#fd-desk-more > summary').click();
      await page.waitForFunction(() => {
        const count = document.querySelectorAll('#fd-top-picks-list .fd-top-pick').length;
        const status = document.querySelector('#fd-top-picks-status')?.textContent || '';
        return count > 0 || (!!status && !/Loading/.test(status));
      });
      const pickCount = await page.locator('#fd-top-picks-list .fd-top-pick').count();
      const title = await page.locator('#fd-top-picks-title').innerText();
      if (pickCount < 5) assert.equal(title, 'Top Picks');
      else assert.equal(title, 'Top 5 Picks');
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
  await finalsOnly.waitForFunction(() => Array.isArray(window.fdAllGames) || /unavailable/i.test(document.querySelector('#fd-live-board-status')?.innerText || ''));
  if (Array.isArray(await finalsOnly.evaluate(() => window.fdAllGames)) && (await finalsOnly.evaluate(() => window.fdAllGames.length)) > 0) {
    await finalsOnly.evaluate(() => {
      window.fdAllGames = window.fdAllGames.filter(game => game.state === 'post');
      window.fdScoreboardFeed = 'ok';
      window.dispatchEvent(new CustomEvent('fd-scoreboard-updated'));
    });
    await finalsOnly.waitForFunction(() => /No games in progress/.test(document.querySelector('#fd-live-board-status')?.innerText || ''));
    assert.doesNotMatch(await finalsOnly.locator('#fd-live-board-status').innerText(), /unavailable/);
    assert.match(await finalsOnly.locator('#fd-live-board-status').innerText(), /Latest finals shown/);
  }
  await finalsOnly.close();
  await browser.close();
  console.log('fan review browser tests passed');
})().catch(error => {
  console.error(error);
  process.exit(1);
});
