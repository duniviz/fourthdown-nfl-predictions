/* One shared NFL team-color map for fan-facing visuals.
 * Hexes are display tints chosen to stay visible on the dark cards.
 * Aliases cover the codes the feeds actually publish (JAC/JAX, LAR/LA, WAS/WSH).
 */
(function (root, factory) {
  const api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  if (root) root.FDTeamColors = api;
})(typeof globalThis !== "undefined" ? globalThis : this, function () {
  "use strict";

  // Keys are the display codes from assets/fd-teams.js (WAS, JAC, LAR).
  const TEAM_COLORS = {
    ARI: "#97233f",
    ATL: "#c8102e",
    BAL: "#7a45d6",
    BUF: "#3b82f6",
    CAR: "#00a3e0",
    CHI: "#e25b1a",
    CIN: "#fb4f14",
    CLE: "#ff5a1f",
    DAL: "#4c8fe0",
    DEN: "#fb6b2d",
    DET: "#1c96d4",
    GB: "#3e9a62",
    HOU: "#d4273a",
    IND: "#5b94e0",
    JAC: "#00b3a4",
    KC: "#e31837",
    LAC: "#0090d0",
    LAR: "#3d78e0",
    LV: "#b7bec4",
    MIA: "#00a8b0",
    MIN: "#8a5ad4",
    NE: "#d0122d",
    NO: "#d7c48a",
    NYG: "#4d86d6",
    NYJ: "#2faf68",
    PHI: "#1aa39a",
    PIT: "#f0c14a",
    SEA: "#6fce32",
    SF: "#e10600",
    TB: "#e02323",
    TEN: "#5aa4e8",
    WAS: "#e15b68"
  };

  const FALLBACK = "#6d8ea6";

  function teams() {
    if (typeof module === "object" && typeof require === "function") {
      try { return require("./fd-teams.js"); } catch (error) { return null; }
    }
    return typeof globalThis !== "undefined" ? globalThis.fdTeams : null;
  }

  function label(code) {
    const api = teams();
    return api && api.label ? api.label(code) : String(code || "").trim().toUpperCase();
  }

  function color(code) {
    return TEAM_COLORS[label(code)] || FALLBACK;
  }

  function pairStyle(away, home) {
    return "--away-color:" + color(away) + ";--home-color:" + color(home);
  }

  return { TEAM_COLORS, FALLBACK, label, color, pairStyle };
});
