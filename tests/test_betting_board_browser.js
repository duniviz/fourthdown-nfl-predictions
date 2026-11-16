const {chromium} = require('playwright');
const assert = require('node:assert/strict');
(async () => {
  const browser = await chromium.launch({headless: true, executablePath: process.env.CHROME_PATH || '/usr/bin/google-chrome', args: ['--no-sandbox']});
  for (const width of [400, 1440]) {
    const page = await browser.newPage({viewport: {width, height: 1000}});
    const errors = [];
    page.on('pageerror', error => errors.push(error.message));
    await page.route('https://site.api.espn.com/**', route => route.fulfill({json: {events: []}}));
    await page.goto('http://127.0.0.1:8123/index.html', {waitUntil: 'domcontentloaded'});
    await page.waitForFunction(() => /Under|Over|to win/.test(document.querySelector('#fd-bb-table')?.innerText || ''));
    const table = await page.locator('#fd-bb-table').innerText();
    assert.match(table, /Official pick · current model/);
    assert.match(table, /ML projection, research/);
    assert.match(await page.locator('#fd-bb-results').innerText(), /52\.4%/);
    await page.locator('[data-fd-bb-tab="props"]').click();
    await page.waitForFunction(() => /ML projection, research/.test(document.querySelector('#fd-bb-table')?.innerText || ''));
    const nav = page.locator('.fd2-links');
    assert.match(await nav.innerText(), /Edges/);
    assert.match(await nav.innerText(), /Games/);
    assert.match(await nav.innerText(), /Props/);
    assert.match(await nav.innerText(), /Results/);
    assert.match(await nav.evaluate(node => node.textContent), /Model Lab/);
    assert.match(await nav.evaluate(node => node.textContent), /How to read/);
    if (width === 400) assert.equal(await page.locator('.fd2-bottom').evaluate(node => getComputedStyle(node).display), 'grid');
    if (width === 1440) assert.equal(await page.locator('.fd2-bottom').evaluate(node => getComputedStyle(node).display), 'none');
    await page.goto('http://127.0.0.1:8123/bets.html', {waitUntil: 'domcontentloaded'});
    await page.waitForSelector('#bet-cards .fd-bet-ml-projection');
    assert.match(await page.locator('#bet-cards .fd-bet-ml-projection').first().innerText(), /ML projection, research/);
    assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth + 1), true, 'overflow ' + width);
    assert.deepEqual(errors, []);
    await page.close();
    console.log('Betting board browser', width, 'passed');
  }
  await browser.close();
})().catch(error => { console.error(error); process.exit(1); });
