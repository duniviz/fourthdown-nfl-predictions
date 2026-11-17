"use strict";
const fs = require("node:fs");
const path = require("node:path");
const { chromium } = require("playwright");
const assert = require("node:assert/strict");

(async () => {
  const browser = await chromium.launch({
    headless: true,
    executablePath: process.env.CHROME_PATH || "/usr/bin/google-chrome",
    args: ["--no-sandbox"]
  });
  const page = await browser.newPage({ viewport: { width: 400, height: 900 }, deviceScaleFactor: 2 });
  const errors = [];
  page.on("pageerror", (error) => errors.push(error.message));
  await page.clock.install({ time: new Date("2026-11-16T18:00:00Z") });
  const kickoff = "2026-11-13T01:15:00Z";
  await page.route("https://site.api.espn.com/**", (route) => route.fulfill({
    json: {
      events: [{
        id: "401772936",
        date: kickoff,
        competitions: [{
          competitors: [
            { homeAway: "home", team: { abbreviation: "NYG", displayName: "New York Giants", logo: "https://a.espncdn.com/i/teamlogos/nfl/500/nyg.png" }, score: "21" },
            { homeAway: "away", team: { abbreviation: "WAS", displayName: "Washington Commanders", logo: "https://a.espncdn.com/i/teamlogos/nfl/500/wsh.png" }, score: "24" }
          ],
          status: { type: { state: "post", completed: true, shortDetail: "Final", detail: "Final" } },
          broadcasts: [{ names: ["ESPN"] }]
        }]
      }]
    }
  }));

  await page.goto("http://127.0.0.1:8123/index.html", { waitUntil: "domcontentloaded" });
  await page.locator("#fd-desk-games").evaluate((node) => { node.open = true; });
  await page.locator("#fd-slate-pulse .fd-live-board-head>a").click();
  await page.locator("#scoreboard").waitFor({ state: "visible" });
  const card = page.locator("#scoreboard-cards .scorecard").filter({ hasText: "WAS" }).filter({ hasText: "NYG" });
  await card.waitFor();
  await page.waitForFunction(() => {
    const node = [...document.querySelectorAll("#scoreboard-cards .scorecard")].find((el) => /WAS/.test(el.textContent) && /NYG/.test(el.textContent));
    return node && /Winner: Miss/.test(node.textContent);
  });
  const text = await card.innerText();
  assert.match(text, /Winner: Miss/);
  assert.match(text, /Spread: Miss/);
  assert.match(text, /O\/U: Hit/);
  assert.match(text, /Picked NYG by 3\.7 · WAS won 24–21/);
  assert.match(text, /Picked NYG −2\.5 \(model margin 3\.7\) · NYG lost/);
  assert.match(text, /Picked Over 40\.5 \(model 41\.3\) · 45 total/);
  assert.equal(await card.locator(".fd-status-pill.is-final").count(), 0, "Completed cards keep a single Final indicator");
  assert.equal(await card.locator(".score-state", { hasText: "FINAL" }).count(), 1);
  const finals = await card.locator(".score-state, .fd-status-pill, .score-head .caption").allInnerTexts();
  assert.deepEqual(finals.map((item) => item.trim()).filter((item) => /^final$/i.test(item)), ["FINAL"]);
  assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth + 1), true, "Grade lines fit a 400px screen");
  const shotDir = "/opt/cursor/artifacts";
  if (fs.existsSync(shotDir)) await card.screenshot({ path: path.join(shotDir, "grade-pills-mobile-after.png") });

  await page.goto("http://127.0.0.1:8123/history.html", { waitUntil: "domcontentloaded" });
  await page.waitForFunction(() => /Winner: Miss/.test(document.querySelector("#games")?.innerText || ""), null, { timeout: 20000 });
  const history = await page.locator("#games .card").filter({ hasText: "WAS" }).filter({ hasText: "NYG" }).first().innerText();
  assert.match(history, /Winner: Miss/);
  assert.match(history, /Spread: Miss/);
  assert.match(history, /O\/U: Hit/);
  assert.match(history, /Picked NYG by 3\.7 · WAS won 24–21/);
  assert.match(history, /Picked NYG −2\.5 \(model margin 3\.7\) · NYG lost/);
  assert.match(history, /Picked Over 40\.5 \(model 41\.3\) · 45 total/);
  assert.deepEqual(errors, []);
  await browser.close();
  console.log("Grade labels: homepage and history pills name winner, spread, and O/U");
})().catch((error) => {
  console.error(error);
  process.exit(1);
});
