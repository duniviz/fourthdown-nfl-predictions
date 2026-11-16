const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");

const source = fs.readFileSync("assets/fd-app-shell.js", "utf8");
for (const [path, expected] of [["/", "Edges"], ["/index.html", "Edges"], ["/fourthdown-nfl-predictions/", "Edges"], ["/fourthdown-nfl-predictions/index.html", "Edges"], ["/bets.html", "Props"], ["/fourthdown-nfl-predictions/bets.html", "Props"], ["/history.html", "Results"], ["/fourthdown-nfl-predictions/history.html", "Results"], ["/model-lab.html", "More"], ["/fourthdown-nfl-predictions/model-lab.html", "More"]]) {
  const nav = { setAttribute(name, value) { this[name] = value; } };
  const context = { location: { pathname: path }, document: { createElement: () => nav, body: { append: element => { context.appended = element; } } } };
  vm.runInNewContext(source, context);
  assert.equal(context.appended, nav, `navigation should be appended for ${path}`);
  assert.equal(nav.className, "fd-app-nav");
  assert.match(nav["aria-label"], /mobile navigation/i);
  assert.equal((nav.innerHTML.match(/aria-current="page"/g) || []).length, 1, `exactly one active destination for ${path}`);
  assert.match(nav.innerHTML, new RegExp(`<span>${expected}</span>`));
  assert.equal((nav.innerHTML.match(/<a /g) || []).length, 5);
}
const css = fs.readFileSync("assets/fd-premium-app.css", "utf8");
assert.match(css, /@media\(max-width:760px\)/);
assert.match(css, /@media\(max-width:390px\)/);
assert.match(css, /prefers-reduced-motion:reduce/);
assert.match(css, /Signature FOURTHDOWN treatment/);
assert.match(css, /#scoreboard-cards \.fd-market-picks>div:last-child/);
assert.match(css, /\.fd-mobile-prop-card:before/);
for (const page of ["index.html", "bets.html", "history.html", "model-lab.html"]) {
  const html = fs.readFileSync(page, "utf8");
  assert.match(html, /fd-premium-app\.css/);
  assert.match(html, /fd-app-shell\.js/);
}
console.log("Premium shell navigation and responsive hooks passed.");

require("./test_frozen_player_fallback.js");
