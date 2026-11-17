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
    {name:'games', target:'index.html#fd-slate-pulse', selector:'#fd-slate-pulse'}
  ];
  for (const [version, port] of [['before', 8123], ['after', 8124]]) {
    for (const width of [1440, 400]) {
      for (const entry of cases) {
        const page = await browser.newPage({viewport:{width,height:900}, deviceScaleFactor:1});
        await page.route('https://site.api.espn.com/**', r => r.fulfill({json:{events:[]}}));
        await page.route('https://api.github.com/**', r => r.fulfill({json:{workflow_runs:[]}}));
        await page.goto('http://127.0.0.1:' + port + '/' + entry.target, {waitUntil:'domcontentloaded'});
        await page.waitForTimeout(1200);
        if(version==='after'&&entry.name==='games'){
          await page.evaluate(() => {
            window.fdAllGames = Array.from({length:6}, (_, index) => ({
              id:'screenshot-game-'+index, date:new Date(Date.now()+(index+1)*86400000).toISOString(), state:'pre', status:'Scheduled',
              away:{abbr:'NE',name:'New England Patriots',score:null}, home:{abbr:'BUF',name:'Buffalo Bills',score:null}
            }));
            window.fdScoreboardFeed='ok';
            window.dispatchEvent(new CustomEvent('fd-scoreboard-updated'));
          });
        }
        if(version==='after'&&entry.name==='games'&&!(await page.locator('#fd-desk-games').evaluate(el=>el.open))) await page.locator('#fd-desk-games > summary').click();
        if (entry.selector) {
          const loc = page.locator(entry.selector).first();
          await loc.waitFor({state:'visible',timeout:15000});
          await loc.scrollIntoViewIfNeeded();
        }
        const file = path.join(out, version+'-'+entry.name+'-'+width+'.png');
        await page.screenshot({path:file, fullPage:false, animations:'disabled'});
        console.log('Screenshot:',path.basename(file));
        if(version==='after'&&entry.name==='games'){
          await page.locator('#fd-slate-pulse .fd-live-board-head>a').click();
          await page.locator('#fd-live-board-cards [data-game-id]').first().waitFor({state:'visible',timeout:15000});
          const allFile=path.join(out,'after-all-games-'+width+'.png');
          await page.screenshot({path:allFile,fullPage:false,animations:'disabled'});
          console.log('Screenshot:',path.basename(allFile));
          await page.locator('#fd-live-board-cards [data-game-id]').first().click();
          await page.locator('#fd-modal').waitFor({state:'visible',timeout:15000});
          const modalFile=path.join(out,'after-full-matchup-'+width+'.png');
          await page.screenshot({path:modalFile,fullPage:false,animations:'disabled'});
          console.log('Screenshot:',path.basename(modalFile));
        }
        await page.close();
      }
    }
  }
  await browser.close();
})().catch(error => {console.error(error);process.exit(1)});
