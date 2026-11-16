/* Fan-facing visuals. Reads published feeds only.
 * Does not change projections, grades, or market math.
 *
 * Confidence tags (documented thresholds):
 * Primary field, when a published simulation percentage exists for the side
 * we already picked (home/away win %, cover %, or over/under cover %):
 *   Strong — 62% or higher
 *   Lean   — 55% up to 62%
 *   Pass   — under 55%
 * Fallback, only when that percentage is missing (ATS and totals):
 * the absolute model-vs-DraftKings edge in points:
 *   Strong — 3.0 points or more
 *   Lean   — 1.5 points up to 3.0
 *   Pass   — under 1.5 points
 * Winner tags are not invented from the margin. They need a win percentage.
 *
 * Number-line highlight: a gap of 2.5 points or more is marked as large.
 * Spread numbers use the home team's spread. Negative means that team is favored.
 */
(function (root, factory) {
  const api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  if (root && root.document) {
    const start = () => api.mount(root);
    if (root.document.readyState === "loading") root.document.addEventListener("DOMContentLoaded", start);
    else start();
  }
})(typeof globalThis !== "undefined" ? globalThis : this, function () {
  "use strict";

  const STRONG_PCT = 62;
  const LEAN_PCT = 55;
  const STRONG_EDGE = 3;
  const LEAN_EDGE = 1.5;
  const LARGE_GAP = 2.5;

  const colorsApi = (typeof require === "function" && typeof module === "object")
    ? require("./fd-team-colors.js")
    : (typeof globalThis !== "undefined" ? globalThis.FDTeamColors : null);
  const teamsApi = (typeof require === "function" && typeof module === "object")
    ? require("./fd-teams.js")
    : null;

  function teamLabels() {
    return teamsApi || (typeof globalThis !== "undefined" ? globalThis.fdTeams : null);
  }
  function colorOf(code) {
    return colorsApi ? colorsApi.color(code) : "#6d8ea6";
  }
  // Display codes come from the shared fd-teams map (WAS, JAC, LAR).
  function canon(code) {
    const api = teamLabels();
    return api && api.label ? api.label(code) : String(code || "").trim().toUpperCase();
  }
  function homeSpread(home, value) {
    const api = teamLabels();
    if (api && api.homeSpread) return api.homeSpread(home, value);
    const n = num(value);
    if (n === null) return "";
    return canon(home) + " " + (n > 0 ? "+" : "") + n.toFixed(1);
  }

  const esc = (value) => String(value ?? "").replace(/[&<>"']/g, (ch) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
  }[ch]));

  function num(value) {
    if (value === null || value === undefined || value === "") return null;
    const n = Number(value);
    return Number.isFinite(n) ? n : null;
  }

  function fixed(value, digits) {
    const n = num(value);
    return n === null ? "" : n.toFixed(digits === undefined ? 1 : digits);
  }

  function normName(value) {
    return String(value || "").normalize("NFKD").replace(/[\u0300-\u036f]/g, "")
      .toLowerCase().trim().replace(/(?:[\s.,-]+)(?:jr|junior|sr|senior|ii|iii|iv|v)\.?$/, "")
      .replace(/[^a-z0-9]/g, "");
  }

  const MARKET_BY_LABEL = [
    ["passing yards", "player_pass_yds"],
    ["rushing yards", "player_rush_yds"],
    ["receiving yards", "player_rec_yds"],
    ["qb pass completions", "player_pass_completions"],
    ["pass completions", "player_pass_completions"],
    ["completions", "player_pass_completions"],
    ["rushing attempts", "player_rush_attempts"],
    ["rush attempts", "player_rush_attempts"],
    ["receptions", "player_receptions"]
  ];

  function marketKeyFromText(text) {
    const hay = String(text || "").toLowerCase();
    for (const [label, key] of MARKET_BY_LABEL) {
      if (hay.includes(label)) return key;
    }
    return "";
  }

  function confidenceTag(input) {
    const pct = num(input && input.pct);
    if (pct !== null && pct >= 0 && pct <= 100) {
      const tag = pct >= STRONG_PCT ? "Strong" : pct >= LEAN_PCT ? "Lean" : "Pass";
      return { tag, source: "simulation", pct };
    }
    if (input && input.allowEdge) {
      const edge = num(input.edge);
      if (edge !== null) {
        const size = Math.abs(edge);
        const tag = size >= STRONG_EDGE ? "Strong" : size >= LEAN_EDGE ? "Lean" : "Pass";
        return { tag, source: "edge", edge: size };
      }
    }
    return null;
  }

  function badge(kind, tag) {
    if (!tag) return "";
    const detail = tag.source === "simulation"
      ? tag.pct.toFixed(1) + "% sim"
      : tag.edge.toFixed(1) + " pt gap";
    const title = tag.source === "simulation"
      ? "From the published simulation. Strong is 62% or more, Lean is 55% or more."
      : "No simulation percentage was published, so this uses the model-versus-DraftKings gap. Strong is 3 points or more, Lean is 1.5 or more.";
    return '<span class="fd-appeal-badge is-' + tag.tag.toLowerCase() + '" title="' + esc(title) + '">' +
      esc(kind) + " · " + esc(tag.tag) + "<small>" + esc(detail) + "</small></span>";
  }

  function gradeWord(result) {
    const value = String(result || "").toLowerCase();
    if (value !== "hit" && value !== "miss" && value !== "push") return "";
    return value === "hit" ? "Hit" : value === "miss" ? "Miss" : "Push";
  }

  // Same sign rules as live/game_official_results.py: positive is home (or Over).
  function pickSide(value) {
    const n = num(value);
    if (n === null || n === 0) return "push";
    return n > 0 ? "home" : "away";
  }

  function signedLine(value) {
    const n = num(value);
    if (n === null) return "";
    const body = Math.abs(n).toFixed(1);
    if (n > 0) return "+" + body;
    if (n < 0) return "\u2212" + body;
    return body;
  }

  function wholeish(value) {
    const n = num(value);
    if (n === null) return "";
    const rounded = Math.round(n * 10) / 10;
    if (Math.abs(rounded - Math.round(rounded)) < 1e-9) return String(Math.round(rounded));
    return rounded.toFixed(1);
  }

  function winnerStory(input) {
    const result = gradeWord(input && input.winnerResult);
    if (!result) return null;
    const margin = num(input.gradeMargin);
    const homeScore = num(input.actualHome);
    const awayScore = num(input.actualAway);
    const away = input.away || "Away";
    const home = input.home || "Home";
    if (margin === null || homeScore === null || awayScore === null) return { label: "Winner", result, detail: "" };
    const picked = pickSide(margin);
    const actual = pickSide(homeScore - awayScore);
    const outcome = actual === "push"
      ? "Tied " + wholeish(awayScore) + "\u2013" + wholeish(homeScore)
      : actual === "home"
        ? home + " won " + wholeish(homeScore) + "\u2013" + wholeish(awayScore)
        : away + " won " + wholeish(awayScore) + "\u2013" + wholeish(homeScore);
    const pick = picked === "push"
      ? "No winner side"
      : "Picked " + (picked === "home" ? home : away) + " by " + Math.abs(margin).toFixed(1);
    return { label: "Winner", result, detail: pick + " \u00b7 " + outcome };
  }

  function spreadStory(input) {
    const result = gradeWord(input && input.spreadResult);
    if (!result) return null;
    const margin = num(input.gradeMargin);
    const spread = num(input.gradeSpread);
    const homeScore = num(input.actualHome);
    const awayScore = num(input.actualAway);
    if (margin === null || spread === null || homeScore === null || awayScore === null) return { label: "Spread", result, detail: "" };
    // model_ats = side(projected_margin_home + dk_home_spread). Away's number is the opposite spread.
    const picked = pickSide(margin + spread);
    if (picked === "push") return { label: "Spread", result, detail: "" };
    const away = input.away || "Away";
    const home = input.home || "Home";
    const team = picked === "home" ? home : away;
    const teamSpread = picked === "home" ? spread : -spread;
    const actual = pickSide((homeScore - awayScore) + spread);
    const teamScore = picked === "home" ? homeScore : awayScore;
    const oppScore = picked === "home" ? awayScore : homeScore;
    const outcome = actual === "push"
      ? "push"
      : actual === picked
        ? team + " covered"
        : teamScore < oppScore
          ? team + " lost"
          : teamScore > oppScore
            ? team + " didn't cover"
            : team + " tied";
    return {
      label: "Spread",
      result,
      detail: "Picked " + team + " " + signedLine(teamSpread) + " (model margin " + Math.abs(margin).toFixed(1) + ") \u00b7 " + outcome
    };
  }

  function totalStory(input) {
    const result = gradeWord(input && input.totalResult);
    if (!result) return null;
    const modelTotal = num(input.gradeTotal);
    const line = num(input.gradeLine);
    const homeScore = num(input.actualHome);
    const awayScore = num(input.actualAway);
    if (modelTotal === null || line === null || homeScore === null || awayScore === null) return { label: "O/U", result, detail: "" };
    // model_ou = side(projected_total - dk_total). Positive is Over.
    const edge = modelTotal - line;
    if (pickSide(edge) === "push") return { label: "O/U", result, detail: "" };
    return {
      label: "O/U",
      result,
      detail: "Picked " + (edge > 0 ? "Over" : "Under") + " " + line.toFixed(1) + " (model " + modelTotal.toFixed(1) + ") \u00b7 " + wholeish(homeScore + awayScore) + " total"
    };
  }

  function gradeStories(input) {
    return [winnerStory(input), spreadStory(input), totalStory(input)].filter(Boolean);
  }

  function stamp(result, label, detail) {
    const value = String(result || "").toLowerCase();
    const word = gradeWord(value);
    if (!word) return "";
    const text = label ? label + ": " + word : word;
    const title = detail ? ' title="' + esc(detail) + '"' : "";
    return '<span class="bet-final is-' + value + '"' + title + ">" + esc(text) + "</span>";
  }

  function winBar(game) {
    const awayPct = num(game.awayPct);
    const homePct = num(game.homePct);
    if (awayPct === null || homePct === null || awayPct < 0 || homePct < 0 || awayPct > 100 || homePct > 100) return "";
    const tiePct = num(game.tiePct);
    const tie = tiePct !== null && tiePct > 0 && tiePct <= 100 ? tiePct : 0;
    if (awayPct + homePct + tie > 103 || awayPct + homePct < 50) return "";
    const away = game.away || "Away";
    const home = game.home || "Home";
    const parts = [
      { pct: awayPct, color: colorOf(away) },
      ...(tie ? [{ pct: tie, color: "#9aabba", tie: true }] : []),
      { pct: homePct, color: colorOf(home) }
    ];
    const total = parts.reduce((sum, part) => sum + part.pct, 0) || 1;
    const chunks = parts.map((part) => '<i' + (part.tie ? ' class="is-tie"' : "") +
      ' style="width:' + (part.pct / total * 100).toFixed(2) + "%;background:" + part.color + '"></i>').join("");
    const tieNote = tie ? ", ties " + tie.toFixed(1) + " percent" : "";
    return '<div class="fd-appeal fd-appeal-win"><div class="fd-appeal-win-labels">' +
      '<span><b style="background:' + colorOf(away) + '"></b>' + esc(away) + " " + awayPct.toFixed(1) + "%</span>" +
      '<span>' + esc(home) + " " + homePct.toFixed(1) + '% <b style="background:' + colorOf(home) + '"></b></span>' +
      '</div><div class="fd-appeal-win-track" role="img" aria-label="Simulated win chance: ' +
      esc(away) + " " + awayPct.toFixed(1) + " percent, " + esc(home) + " " + homePct.toFixed(1) + " percent" + tieNote +
      '">' + chunks + "</div>" +
      (tie ? "<small>Ties " + tie.toFixed(1) + "% · simulated, not a guarantee</small>" : "<small>Simulated win chance · not a guarantee</small>") +
      "</div>";
  }

  function numberLine(spec) {
    const model = num(spec.model);
    const market = num(spec.market);
    if (model === null || market === null) return "";
    const gap = model - market;
    const large = Math.abs(gap) >= LARGE_GAP;
    const lo = Math.min(model, market);
    const hi = Math.max(model, market);
    const pad = Math.max(0.6, (hi - lo) * 0.45) || 1;
    const min = lo - pad;
    const max = hi + pad;
    const at = (value) => ((value - min) / (max - min) * 100);
    const left = Math.min(at(model), at(market));
    const width = Math.max(1.5, Math.abs(at(model) - at(market)));
    const teamNote = spec.team
      ? "Negative means " + spec.team + " is favored."
      : "";
    const same = Math.abs(gap) < 0.05;
    const aria = spec.label + ": our number " + spec.modelText + ", DraftKings " + spec.marketText +
      (same ? ", same number" : ", gap " + Math.abs(gap).toFixed(1) + " points") +
      (large ? ", large gap" : "");
    return '<div class="fd-appeal-line' + (large ? " is-large" : "") + '" role="group" aria-label="' + esc(aria) + '">' +
      '<div class="fd-appeal-line-head"><span>' + esc(spec.label) + "</span>" +
      (same ? "<strong>Same number</strong>" : '<strong' + (large ? ' class="is-large"' : "") + ">Gap " + Math.abs(gap).toFixed(1) + "</strong>") +
      "</div>" +
      '<div class="fd-appeal-line-key"><span><i class="is-us"></i>Us ' + esc(spec.modelText) + "</span>" +
      "<span><i class=\"is-dk\"></i>DK " + esc(spec.marketText) + "</span></div>" +
      '<div class="fd-appeal-axis" aria-hidden="true"><span class="fd-appeal-span" style="left:' + left.toFixed(2) +
      "%;width:" + width.toFixed(2) + '%"></span><i class="is-us" style="left:' + at(model).toFixed(2) +
      '%"></i><i class="is-dk" style="left:' + at(market).toFixed(2) + '%"></i></div>' +
      (teamNote ? "<p>" + esc(teamNote) + (large ? " Big gap versus the DK number." : "") + "</p>" : (large ? "<p>Big gap versus the DK number.</p>" : "")) +
      "</div>";
  }

  function linesBlock(input) {
    const home = input.home;
    const awayScore = num(input.awayScore);
    const homeScore = num(input.homeScore);
    const modelTotal = num(input.modelTotal) !== null ? num(input.modelTotal) : (awayScore !== null && homeScore !== null ? awayScore + homeScore : null);
    const homeMargin = awayScore !== null && homeScore !== null ? homeScore - awayScore : num(input.homeMargin);
    const modelSpread = homeMargin === null ? null : -homeMargin;
    const dkSpread = num(input.dkSpread);
    const dkTotal = num(input.dkTotal);
    const spread = numberLine({
      label: "Home spread on " + (home || "home"),
      team: home || "",
      model: modelSpread,
      market: dkSpread,
      modelText: homeSpread(home, modelSpread),
      marketText: homeSpread(home, dkSpread)
    });
    const total = numberLine({
      label: "Game total",
      model: modelTotal,
      market: dkTotal,
      modelText: modelTotal === null ? "" : modelTotal.toFixed(1),
      marketText: dkTotal === null ? "" : dkTotal.toFixed(1)
    });
    if (!spread && !total) return "";
    return '<div class="fd-appeal fd-appeal-lines">' + spread + total + "</div>";
  }

  function pickRow(input) {
    const winnerPct = input.winnerSide === "home" ? num(input.homeWin) : input.winnerSide === "away" ? num(input.awayWin) : null;
    const spreadEdge = num(input.spreadEdge);
    const spreadPct = spreadEdge === null ? null : (spreadEdge > 0.05 ? num(input.homeCover) : spreadEdge < -0.05 ? num(input.awayCover) : null);
    const totalEdge = num(input.totalEdge);
    const totalPct = totalEdge === null ? null : (totalEdge > 0.05 ? num(input.overCover) : totalEdge < -0.05 ? num(input.underCover) : null);
    const stories = gradeStories(input);
    const storyFor = (label) => stories.find((story) => story.label === label) || null;
    const chips = [
      badge("Winner", confidenceTag({ pct: winnerPct })),
      stamp(input.winnerResult, "Winner", storyFor("Winner") && storyFor("Winner").detail),
      badge("Spread", confidenceTag({ pct: spreadPct, edge: spreadEdge, allowEdge: spreadPct === null && spreadEdge !== null })),
      stamp(input.spreadResult, "Spread", storyFor("Spread") && storyFor("Spread").detail),
      badge("Total", confidenceTag({ pct: totalPct, edge: totalEdge, allowEdge: totalPct === null && totalEdge !== null })),
      stamp(input.totalResult, "O/U", storyFor("O/U") && storyFor("O/U").detail)
    ].filter(Boolean);
    const notes = stories.map((story) => story.detail).filter(Boolean);
    if (!chips.length && !notes.length) return "";
    const noteHtml = notes.length
      ? '<ul class="fd-appeal-grade-notes">' + notes.map((line) => "<li>" + esc(line) + "</li>").join("") + "</ul>"
      : "";
    return '<div class="fd-appeal fd-appeal-grades"><div class="fd-appeal fd-appeal-picks">' + chips.join("") + "</div>" + noteHtml + "</div>";
  }

  function gamePanel(input) {
    const bar = input.awayPct != null ? winBar(input) : "";
    const picks = pickRow(input);
    const lines = linesBlock(input);
    if (!bar && !picks && !lines) return "";
    return '<div class="fd-appeal fd-appeal-panel">' + bar + picks + lines + "</div>";
  }

  function sparkline(values, line) {
    const nums = (values || []).map(num).filter((value) => value !== null).slice(-5);
    if (nums.length < 2) return "";
    const lineN = num(line);
    const hasLine = lineN !== null;
    const dataMin = Math.min.apply(null, nums);
    const dataMax = Math.max.apply(null, nums);
    const span = Math.max(0.5, dataMax - dataMin);
    // A line far from the recent games would squash the shape. Keep the games readable and say where the line sits.
    const onScale = hasLine && lineN <= dataMax + span * 1.25 && lineN >= dataMin - span * 1.25;
    const sample = onScale ? nums.concat(lineN) : nums.slice();
    let min = Math.min.apply(null, sample);
    let max = Math.max.apply(null, sample);
    if (min === max) { min -= 1; max += 1; }
    const pad = (max - min) * 0.14;
    min -= pad;
    max += pad;
    const width = 148;
    const height = 42;
    const step = (width - 10) / (nums.length - 1);
    const yOf = (value) => 5 + (height - 10) * (1 - (value - min) / (max - min));
    const points = nums.map((value, index) => [5 + index * step, yOf(value)]);
    const poly = points.map((point) => point[0].toFixed(1) + "," + point[1].toFixed(1)).join(" ");
    const dots = points.map((point, index) => {
      const cls = !hasLine ? "" : nums[index] >= lineN ? " is-over" : " is-under";
      return '<circle cx="' + point[0].toFixed(1) + '" cy="' + point[1].toFixed(1) + '" r="2.6" class="' + cls.trim() + '"></circle>';
    }).join("");
    const ref = onScale
      ? '<line x1="4" x2="' + (width - 4) + '" y1="' + yOf(lineN).toFixed(1) + '" y2="' + yOf(lineN).toFixed(1) + '" class="fd-appeal-spark-line"></line>'
      : "";
    const placed = hasLine
      ? (onScale ? ", versus a line of " + lineN.toFixed(1) : ", DK line " + lineN.toFixed(1) + " is " + (lineN > dataMax ? "above" : "below") + " the chart")
      : "";
    const label = "Last " + nums.length + " games: " + nums.map((value) => value.toFixed(1)).join(", ") + placed;
    return '<svg class="fd-appeal-spark" viewBox="0 0 ' + width + " " + height + '" role="img" aria-label="' + esc(label) + '">' +
      ref + '<polyline points="' + poly + '"></polyline>' + dots + "</svg>";
  }

  function sparkBlock(values, line) {
    const graphic = sparkline(values, line);
    if (!graphic) return "";
    const lineN = num(line);
    const finite = (values || []).map(num).filter((value) => value !== null).slice(-5);
    const offChart = lineN !== null && finite.length >= 2 && (lineN > Math.max.apply(null, finite) + Math.max(0.5, Math.max.apply(null, finite) - Math.min.apply(null, finite)) * 1.25 || lineN < Math.min.apply(null, finite) - Math.max(0.5, Math.max.apply(null, finite) - Math.min.apply(null, finite)) * 1.25);
    const caption = lineN === null
      ? "Last games · no DK line on this card"
      : offChart
        ? "Last games · DK line " + lineN.toFixed(1) + " is " + (lineN > Math.max.apply(null, finite) ? "above" : "below") + " these games"
        : "Last games vs tonight's line (" + lineN.toFixed(1) + ")";
    return '<div class="fd-appeal fd-appeal-sparkline"><div class="fd-appeal-spark-caption">' + esc(caption) + "</div>" + graphic +
      '<small>Dots on the line are the last games. The dashed mark is the DK line.</small></div>';
  }

  function headshot(name, athleteId) {
    if (!/^\d+$/.test(String(athleteId || ""))) return "";
    const safeName = name || "Player";
    return '<img class="fd-appeal-headshot" alt="' + esc(safeName) + ' headshot" width="44" height="44" loading="lazy" src="https://a.espncdn.com/i/headshots/nfl/players/full/' +
      encodeURIComponent(String(athleteId)) + '.png" onerror="this.remove()">';
  }

  function recentValues(bundle, playerId, player, marketKey) {
    if (!bundle || !marketKey) return [];
    const byId = bundle.players || {};
    const byName = bundle.by_name || {};
    const rec = (playerId && byId[String(playerId) + "|" + marketKey]) || byName[normName(player) + "|" + marketKey];
    const games = rec && Array.isArray(rec.games) ? rec.games : [];
    return games.map((game) => num(game && (game.actual != null ? game.actual : game.value))).filter((value) => value !== null).slice(-5);
  }

  function athleteIdFor(bundle, player, marketKey) {
    const byName = (bundle && bundle.by_name) || {};
    const name = normName(player);
    if (!name) return "";
    if (marketKey && byName[name + "|" + marketKey] && /^\d+$/.test(String(byName[name + "|" + marketKey].athlete_id || ""))) {
      return String(byName[name + "|" + marketKey].athlete_id);
    }
    const hit = Object.keys(byName).find((key) => key.startsWith(name + "|") && /^\d+$/.test(String((byName[key] || {}).athlete_id || "")));
    return hit ? String(byName[hit].athlete_id) : "";
  }

  function labWeeks(rows) {
    const groups = new Map();
    (rows || []).forEach((row) => {
      const season = num(row.season);
      const week = num(row.week);
      if (season === null || week === null) return;
      const key = season + "-" + week;
      if (!groups.has(key)) groups.set(key, { season, week, winner: emptyCount(), ats: emptyCount(), ou: emptyCount() });
      const bucket = groups.get(key);
      addGrade(bucket.winner, row.winner_result);
      addGrade(bucket.ats, row.ats_result);
      addGrade(bucket.ou, row.ou_result);
    });
    return Array.from(groups.values()).sort((a, b) => a.season - b.season || a.week - b.week);
  }

  function emptyCount() {
    return { hits: 0, misses: 0, pushes: 0 };
  }

  function addGrade(bucket, result) {
    const value = String(result || "").toLowerCase();
    if (value === "hit") bucket.hits += 1;
    else if (value === "miss") bucket.misses += 1;
    else if (value === "push") bucket.pushes += 1;
  }

  function rateOf(bucket) {
    const sample = bucket.hits + bucket.misses;
    if (!sample) return null;
    return { sample, hits: bucket.hits, rate: 100 * bucket.hits / sample };
  }

  function tileFromBlock(label, block) {
    const hits = num(block && block.hits) || 0;
    const misses = num(block && block.misses) || 0;
    const pushes = num(block && block.pushes) || 0;
    const sample = hits + misses;
    const published = num(block && block.hit_pct);
    const rate = published !== null ? published : (sample ? 100 * hits / sample : null);
    return { label, hits, misses, pushes, sample, rate };
  }

  function labView(official) {
    const summary = (official && official.summary) || {};
    const tiles = [
      tileFromBlock("Winner", summary.winner),
      tileFromBlock("Against the spread", summary.ats),
      tileFromBlock("Over / Under", summary.ou)
    ];
    return { tiles, weeks: labWeeks(official && official.rows) };
  }

  function labMarkup(official) {
    const view = labView(official || {});
    const any = view.tiles.some((tile) => tile.sample > 0);
    if (!any && !view.weeks.length) {
      return '<section id="fd-appeal-lab" class="fd-appeal-lab" aria-labelledby="fd-appeal-lab-title"><p class="fd-appeal-kicker">Published grades</p><h2 id="fd-appeal-lab-title">How the picks have done</h2><p>No graded winner, spread, or total results are published yet.</p></section>';
    }
    const tiles = view.tiles.map((tile) => '<article class="fd-appeal-tile"><small>' + esc(tile.label) + "</small><strong>" +
      (tile.rate === null ? "—" : tile.rate.toFixed(1) + "%") + "</strong><span>" + tile.hits + " hits · " + tile.sample + " graded" +
      (tile.pushes ? " · " + tile.pushes + " pushes" : "") + "</span></article>").join("");
    const chart = trendChart(view.weeks);
    const list = view.weeks.map((week) => {
      const bits = ["winner", "ats", "ou"].map((key) => {
        const rated = rateOf(week[key]);
        const name = key === "ats" ? "ATS" : key === "ou" ? "O/U" : "Winner";
        return name + " " + (rated ? rated.rate.toFixed(0) + "% of " + rated.sample : "n/a");
      }).join(", ");
      return "<li>Week " + week.week + ": " + esc(bits) + "</li>";
    }).join("");
    return '<section id="fd-appeal-lab" class="fd-appeal-lab" aria-labelledby="fd-appeal-lab-title">' +
      '<p class="fd-appeal-kicker">Published grades</p><h2 id="fd-appeal-lab-title">How the picks have done</h2>' +
      "<p>Winner, against the spread, and over/under from the saved grade ledger. The rate is hits divided by hits plus misses. Pushes stay out of the rate.</p>" +
      '<div class="fd-appeal-tiles">' + tiles + "</div>" +
      "<h3>Week by week</h3>" + chart +
      (list ? '<ul class="fd-appeal-week-list">' + list + "</ul>" : "") +
      "<p class=\"fd-appeal-lab-note\">The long comparison tables are tucked below. Open them when you want every model and market.</p></section>";
  }

  function trendChart(weeks) {
    if (!weeks.length) return "";
    const width = 640;
    const height = 220;
    const left = 36;
    const right = 16;
    const top = 16;
    const bottom = 36;
    const innerW = width - left - right;
    const innerH = height - top - bottom;
    const yOf = (rate) => top + innerH * (1 - rate / 100);
    const xOf = (index) => weeks.length === 1 ? left + innerW / 2 : left + innerW * index / (weeks.length - 1);
    const series = [
      { key: "winner", name: "Winner", color: "#d6ff63" },
      { key: "ats", name: "ATS", color: "#8ecbff" },
      { key: "ou", name: "O/U", color: "#ffc56d" }
    ];
    const guides = [0, 50, 100].map((tick) => '<line x1="' + left + '" x2="' + (width - right) + '" y1="' + yOf(tick) + '" y2="' + yOf(tick) + '" class="fd-appeal-grid"></line>' +
      '<text x="' + (left - 6) + '" y="' + (yOf(tick) + 4) + '" text-anchor="end">' + tick + "</text>").join("");
    const labels = weeks.map((week, index) => '<text x="' + xOf(index) + '" y="' + (height - 12) + '" text-anchor="middle">W' + week.week + "</text>").join("");
    const paths = series.map((item) => {
      const pts = [];
      weeks.forEach((week, index) => {
        const rated = rateOf(week[item.key]);
        if (rated) pts.push([xOf(index), yOf(rated.rate), rated]);
      });
      if (!pts.length) return "";
      const poly = pts.length > 1 ? '<polyline points="' + pts.map((pt) => pt[0].toFixed(1) + "," + pt[1].toFixed(1)).join(" ") + '" stroke="' + item.color + '"></polyline>' : "";
      const dots = pts.map((pt) => '<circle cx="' + pt[0].toFixed(1) + '" cy="' + pt[1].toFixed(1) + '" r="4.5" fill="' + item.color + '"><title>' +
        item.name + " week " + " " + pt[2].rate.toFixed(1) + "% of " + pt[2].sample + "</title></circle>").join("");
      return poly + dots;
    }).join("");
    const summary = series.map((item) => {
      const bits = weeks.map((week) => {
        const rated = rateOf(week[item.key]);
        return "week " + week.week + " " + (rated ? rated.rate.toFixed(0) + "% of " + rated.sample : "no graded picks");
      }).join(", ");
      return item.name + ": " + bits;
    }).join(". ");
    const legend = series.map((item) => '<span><i style="background:' + item.color + '"></i>' + item.name + "</span>").join("");
    return '<figure class="fd-appeal-trend"><svg viewBox="0 0 ' + width + " " + height + '" role="img" aria-label="Week by week hit rates. ' + esc(summary) + '">' +
      guides + paths + labels + '</svg><figcaption class="fd-appeal-legend">' + legend + "</figcaption></figure>";
  }

  function near(a, b, hours) {
    const left = Date.parse(a || "");
    const right = Date.parse(b || "");
    if (!Number.isFinite(left) || !Number.isFinite(right)) return false;
    return Math.abs(left - right) < (hours || 20) * 3600000;
  }

  function matchByTeams(rows, away, home, kickoff) {
    const found = (rows || []).filter((row) => canon(row.away) === canon(away) && canon(row.home) === canon(home));
    if (!found.length) return null;
    if (kickoff) {
      const timed = found.filter((row) => near(row.kickoff_utc || row.commence_time, kickoff, 20));
      if (timed.length === 1) return timed[0];
      if (timed.length > 1) return timed.slice().sort((a, b) => Math.abs(Date.parse(a.kickoff_utc || a.commence_time) - Date.parse(kickoff)) - Math.abs(Date.parse(b.kickoff_utc || b.commence_time) - Date.parse(kickoff)))[0];
    }
    return found.length === 1 ? found[0] : null;
  }

  function buildGameInput(away, home, forecast, sim, odds, grade, showStamps) {
    const awayScore = num(forecast && forecast.projected_away_score);
    const homeScore = num(forecast && forecast.projected_home_score);
    const homeMargin = awayScore !== null && homeScore !== null ? homeScore - awayScore : num(forecast && forecast.projected_margin_home);
    const modelTotal = num(forecast && forecast.projected_total);
    const dkSpread = num(sim && sim.dk_home_spread);
    const dkTotal = num(sim && sim.dk_total);
    const oddsSpread = num(odds && odds.home_spread);
    const oddsTotal = num(odds && odds.total);
    const spread = dkSpread !== null ? dkSpread : oddsSpread;
    const total = dkTotal !== null ? dkTotal : oddsTotal;
    const winner = canon(forecast && forecast.predicted_winner);
    const winnerSide = winner && winner === canon(home) ? "home" : winner && winner === canon(away) ? "away" : (homeMargin !== null ? (homeMargin >= 0 ? "home" : "away") : "");
    return {
      away, home,
      awayPct: num(sim && sim.away_win_pct),
      homePct: num(sim && sim.home_win_pct),
      tiePct: num(sim && sim.tie_pct),
      awayScore, homeScore, homeMargin, modelTotal,
      dkSpread: spread, dkTotal: total,
      winnerSide,
      homeWin: num(sim && sim.home_win_pct),
      awayWin: num(sim && sim.away_win_pct),
      homeCover: num(sim && sim.home_cover_pct),
      awayCover: num(sim && sim.away_cover_pct),
      overCover: num(sim && sim.over_cover_pct),
      underCover: num(sim && sim.under_cover_pct),
      spreadEdge: homeMargin !== null && spread !== null ? homeMargin + spread : null,
      totalEdge: (modelTotal !== null ? modelTotal : (awayScore !== null && homeScore !== null ? awayScore + homeScore : null)) !== null && total !== null
        ? (modelTotal !== null ? modelTotal : awayScore + homeScore) - total
        : null,
      winnerResult: showStamps && grade ? grade.winner_result : "",
      spreadResult: showStamps && grade ? grade.ats_result : "",
      totalResult: showStamps && grade ? grade.ou_result : "",
      // Explain the published grade with the same locked numbers the grader used.
      gradeMargin: num(grade && grade.projected_margin_home),
      gradeSpread: num(grade && grade.dk_home_spread),
      gradeTotal: num(grade && grade.projected_total),
      gradeLine: num(grade && grade.dk_total),
      actualHome: num(grade && grade.home_score),
      actualAway: num(grade && grade.away_score)
    };
  }

  function tint(node, away, home) {
    if (!node || !away || !home) return;
    node.classList.add("fd-appeal-tinted");
    node.style.setProperty("--away-color", colorOf(away));
    node.style.setProperty("--home-color", colorOf(home));
  }

  function teamsFromScorecard(card) {
    const names = Array.from(card.querySelectorAll(".score-team .name")).map((node) => node.textContent.trim()).filter(Boolean);
    if (names.length >= 2) return { away: names[0], home: names[1] };
    const hybrid = (card.querySelector(".hybrid-teamlogos") || {}).textContent || "";
    const match = hybrid.match(/([A-Z]{2,3})\s+vs\s+([A-Z]{2,3})/);
    return match ? { away: match[1], home: match[2] } : null;
  }

  function decorateScorecards(doc, state) {
    doc.querySelectorAll("#scoreboard-cards .scorecard, #fd-live-board-cards .fd-live-board-card").forEach((card) => {
      const teams = card.classList.contains("fd-live-board-card")
        ? (() => {
          const names = Array.from(card.querySelectorAll(".fd-live-team strong")).map((node) => node.textContent.trim());
          return names.length >= 2 ? { away: names[0], home: names[1] } : null;
        })()
        : teamsFromScorecard(card);
      if (!teams) return;
      tint(card, teams.away, teams.home);
      if (card.classList.contains("fd-live-board-card")) return;
      const forecast = matchByTeams(state.live, teams.away, teams.home, null);
      const kickoff = forecast && forecast.kickoff_utc;
      const sim = forecast ? (state.sims || []).find((row) => String(row.game_id) === String(forecast.game_id)) : matchByTeams(state.sims, teams.away, teams.home, kickoff);
      const odds = matchByTeams(state.odds, teams.away, teams.home, kickoff);
      const grade = matchByTeams(state.grades, teams.away, teams.home, kickoff);
      const final = card.querySelector(".is-final, .score-state") && /FINAL/.test(card.textContent.slice(0, 80));
      const html = gamePanel(buildGameInput(teams.away, teams.home, forecast, sim, odds, grade, final));
      const previous = card.querySelector(":scope > .fd-appeal-panel");
      if (previous) previous.remove();
      if (!html) return;
      const anchor = card.querySelector(".projection-panel") || card.querySelector(".score-teams");
      if (!anchor) return;
      anchor.insertAdjacentHTML("afterend", html);
      const box = card.querySelector(".fd-v5-score-box");
      if (box && card.querySelector(".fd-appeal-win")) box.classList.add("fd-appeal-hide-dup");
    });
  }

  function decorateHistory(doc, state) {
    doc.querySelectorAll("#games > .card").forEach((card) => {
      const heading = (card.querySelector("strong") || {}).textContent || "";
      const match = heading.match(/Week\s+(\d+)\s+·\s+([A-Z]{2,3})\s+@\s+([A-Z]{2,3})/);
      if (!match) return;
      const week = match[1];
      const away = match[2];
      const home = match[3];
      tint(card, away, home);
      const grade = (state.grades || []).find((row) => String(row.week) === String(week) && canon(row.away) === canon(away) && canon(row.home) === canon(home));
      if (!grade) return;
      const forecast = {
        projected_margin_home: grade.projected_margin_home,
        projected_total: grade.projected_total,
        projected_home_score: null,
        projected_away_score: null,
        predicted_winner: num(grade.projected_margin_home) !== null && num(grade.projected_margin_home) >= 0 ? home : away
      };
      const homeMargin = num(grade.projected_margin_home);
      const modelTotal = num(grade.projected_total);
      if (homeMargin !== null && modelTotal !== null) {
        forecast.projected_home_score = (modelTotal + homeMargin) / 2;
        forecast.projected_away_score = (modelTotal - homeMargin) / 2;
      }
      const html = gamePanel(buildGameInput(away, home, forecast, null, {
        home_spread: grade.dk_home_spread,
        total: grade.dk_total
      }, grade, true));
      const previous = card.querySelector(":scope > .fd-appeal-panel");
      if (previous) previous.remove();
      if (html) card.insertAdjacentHTML("beforeend", html);
    });
  }

  function readPlayer(card) {
    return card.getAttribute("data-fd-player") ||
      ((card.querySelector("h3, .bet-name strong, .fd-unified-prop-head strong") || {}).textContent || "").trim();
  }

  function readMarket(card) {
    const attr = card.getAttribute("data-fd-market");
    if (attr && /player_/.test(attr)) return marketKeyFromText(attr) || attr;
    const bits = Array.from(card.querySelectorAll("small, .bet-sub, .fd-matchup-tag")).map((node) => node.textContent).join(" ");
    return marketKeyFromText(attr ? attr + " " + bits : bits);
  }

  function readLine(card) {
    const attr = num(card.getAttribute("data-fd-dk-line"));
    if (attr !== null) return attr;
    const smalls = Array.from(card.querySelectorAll("small"));
    for (const small of smalls) {
      if (/^DK\b/i.test(small.textContent.trim())) {
        const strong = small.parentElement && small.parentElement.querySelector("strong");
        const raw = String(strong ? strong.textContent : "").replace(/[^0-9.+-]/g, "");
        const value = num(raw);
        if (value !== null) return value;
      }
    }
    const gap = card.textContent.match(/DK\s+([0-9]+(?:\.[0-9]+)?)/);
    return gap ? num(gap[1]) : null;
  }

  function readTeam(card) {
    const attr = card.getAttribute("data-fd-team");
    if (attr) return attr;
    const small = card.querySelector(".bet-name small, .fd-unified-prop-head small, .fd-matchup-tag");
    const match = String(small ? small.textContent : "").match(/\b([A-Z]{2,3})\b/);
    return match ? match[1] : "";
  }

  function decoratePlayers(doc, state) {
    const bundle = state.recent || {};
    const cards = doc.querySelectorAll("#bet-cards .bet-card, #fd-extra-list .bet-card, .fd-unified-prop, #fd-opportunity-list article");
    cards.forEach((card) => {
      const player = readPlayer(card);
      if (!player) return;
      const market = readMarket(card);
      const team = readTeam(card);
      if (team) {
        card.classList.add("fd-appeal-player");
        card.style.setProperty("--fd-team", colorOf(team));
      }
      card.querySelectorAll("img").forEach((img) => {
        if (img.alt && img.alt.trim()) return;
        if (/headshots\/nfl\/players/.test(img.getAttribute("src") || "") || img.classList.contains("fd-opp-avatar") || img.classList.contains("fd-appeal-headshot")) {
          img.alt = player + " headshot";
        }
      });
      const existingShot = card.querySelector("img.fd-appeal-headshot, .bet-name img, .fd-opp-avatar, .fd-player-headshot");
      if (!existingShot) {
        const shot = headshot(player, athleteIdFor(bundle, player, market));
        if (shot) {
          const slot = card.querySelector(".fd-unified-prop-head > div") || card.querySelector(".bet-name, .fd-opp-identity") || card.querySelector("h3");
          if (slot) {
            if (slot.tagName === "H3") slot.insertAdjacentHTML("beforebegin", shot);
            else slot.insertAdjacentHTML("afterbegin", shot);
          }
        }
      }
      const values = recentValues(bundle, card.getAttribute("data-fd-player-id"), player, market);
      const block = sparkBlock(values, readLine(card));
      const previous = card.querySelector(":scope > .fd-appeal-sparkline, .fd-appeal-sparkline");
      if (previous) previous.remove();
      if (!block) return;
      const note = Array.from(card.querySelectorAll(".bet-note")).find((node) => /recent game totals unavailable/i.test(node.textContent));
      if (note) note.hidden = true;
      const host = card.querySelector(".fd-lastfive") || card;
      host.insertAdjacentHTML(host === card ? "beforeend" : "beforeend", block);
    });
  }

  function decorateLab(doc, official) {
    const main = doc.querySelector("main");
    if (!main) return;
    let host = doc.getElementById("fd-appeal-lab");
    const html = labMarkup(official);
    if (host) host.outerHTML = html;
    else main.insertAdjacentHTML("afterbegin", html);
    const deep = doc.getElementById("fd-deep-diagnostics");
    if (deep && !deep.closest("details.fd-appeal-fold")) {
      const details = doc.createElement("details");
      details.className = "fd-appeal-fold";
      const summary = doc.createElement("summary");
      summary.textContent = "Detailed accuracy and ML tables";
      deep.before(details);
      details.append(summary, deep);
    }
  }

  function mount(win) {
    const doc = win.document;
    const state = { live: [], sims: [], odds: [], grades: [], recent: { players: {}, by_name: {} } };
    const pages = {
      games: !!doc.getElementById("scoreboard-cards"),
      players: !!doc.getElementById("bet-cards") || !!doc.querySelector(".fd-unified-prop") || !!doc.getElementById("fd-opportunity-list"),
      history: !!doc.getElementById("games"),
      lab: !!doc.getElementById("fd-deep-diagnostics")
    };
    const draw = () => {
      try {
        if (pages.games) decorateScorecards(doc, state);
        if (pages.history) decorateHistory(doc, state);
        if (pages.players || pages.games) decoratePlayers(doc, state);
        if (pages.lab) decorateLab(doc, { summary: state.summary, rows: state.grades });
      } catch (error) {
        win.console && win.console.warn && win.console.warn("FOURTHDOWN visuals skipped", error);
      }
    };
    const watch = (id) => {
      const node = doc.getElementById(id);
      if (!node) return;
      new MutationObserver(() => draw()).observe(node, { childList: true });
    };
    ["scoreboard-cards", "fd-live-board-cards", "bet-cards", "fd-extra-list", "fd-opportunity-list", "games"].forEach(watch);
    const loads = [];
    const pull = (file, apply) => {
      loads.push(win.fetch(file, { cache: "no-store" }).then((response) => response.ok ? response.json() : null).then(apply).catch(() => null));
    };
    if (pages.games) {
      pull("data/live-v2.json", (data) => { state.live = (data && data.games) || []; });
      pull("data/simulations.json", (data) => { state.sims = (data && data.games) || []; });
      pull("data/dk-game-odds.json", (data) => { state.odds = (data && data.games) || []; });
    }
    if (pages.games || pages.history || pages.lab) {
      pull("data/game-official-results.json", (data) => {
        state.grades = (data && data.rows) || [];
        state.summary = data && data.summary;
      });
    }
    if (pages.players || pages.games) {
      pull("data/player-recent-games.json", (data) => {
        state.recent = data || { players: {}, by_name: {} };
      });
    }
    Promise.all(loads).then(draw).catch(() => draw());
    draw();
  }

  return {
    STRONG_PCT, LEAN_PCT, STRONG_EDGE, LEAN_EDGE, LARGE_GAP,
    canon, colorOf, confidenceTag, winBar, numberLine, linesBlock, pickRow, gamePanel, gradeStories,
    sparkline, sparkBlock, headshot, recentValues, labView, labMarkup, buildGameInput, mount
  };
});
