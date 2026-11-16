/* PR-only visual evidence: screenshots of main vs proposed Betting Board polish. */
const {chromium} = require('playwright');
const fs = require('node:fs');
const path = require('node:path');

(async () => {
  const root = path.resolve(__dirname, '../..');
  const out = path.join(root, 'betting-board-screenshots');
  fs.mkdirSync(out, {recursive:true});
  const browser = await chromium.launch({
    headless:true,
    executablePath: process.env.CHROME_PATH || '/usr/bin/google-chrome',
    args:['--no-sandbox']
  });
  const cases = [
    {name:'home', target:'index.html'},
    {name:'props', target:'bets.html', selector:'#bet-cards'},
    {name:'games', target:'index.html#scoreboard', selector:'#scoreboard'}
  ];
  for (const [version, port] of [['before', 8123], ['after', 8124]]) {
    for (const width of [1440, 400]) {
      for (const entry of cases) {
        const page = await browser.newPage({viewport:{width,height:900}, deviceScaleFactor:1});
        await page.route('https://site.api.espn.com/**', r => r.fulfill({json:{events:[]}}));
        await page.route('https://api.github.com/**', r => r.fulfill({json:{workflow_runs:[]}}));
        await page.goto('http://127.0.0.1:' + port + '/' + entry.target, {waitUntil:'domcontentloaded'});
        await page.waitForTimeout(1200);
        if (entry.selector) {
          const loc = page.locator(entry.selector).first();
          await loc.waitFor({state:'visible',timeout:15000});
          await loc.scrollIntoViewIfNeeded();
        }
        const file = path.join(out, version+'-'+entry.name+'-'+width+'.png');
        await page.screenshot({path:file, fullPage:false, animations:'disabled'});
        console.log('Screenshot:',path.basename(file));
        await page.close();
      }
    }
  }
  await browser.close();
})().catch(error => {console.error(error);process.exit(1)});
