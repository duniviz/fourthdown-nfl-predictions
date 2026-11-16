/* Moves duplicate home blocks and tucks extra game-card visuals. Does not change picks. */
(function () {
  function foldSignals() {
    const picks = document.getElementById('fd-top-picks');
    if (!picks || document.getElementById('fd-folded-signals')) return;
    const watch = document.getElementById('fd-watch');
    const pool = document.getElementById('confidence-pool');
    if (!watch && !pool) return;
    const details = document.createElement('details');
    details.id = 'fd-folded-signals';
    details.className = 'fd-folded-signals';
    const summary = document.createElement('summary');
    summary.textContent = 'More slate signals';
    details.append(summary);
    if (watch) details.append(watch);
    if (pool) details.append(pool);
    picks.append(details);
  }
  function compactCard(card) {
    const detail = card.querySelector(':scope > details.fd-card-detail');
    if (!detail) return;
    const selectors = [
      ':scope .projection-panel > .fd-weather-game-candidate',
      ':scope .projection-panel > .fd-score-share',
      ':scope .projection-panel > .fd-score-share-note',
      ':scope .projection-panel > details.fd-changes'
    ];
    selectors.forEach(selector => {
      card.querySelectorAll(selector).forEach(node => {
        if (!detail.contains(node)) detail.append(node);
      });
    });
  }
  function compactCards() {
    document.querySelectorAll('#scoreboard-cards > article.scorecard').forEach(compactCard);
  }
  function wireHelp() {
    document.querySelectorAll('.fd-help-tip').forEach(button => {
      if (button.dataset.fdHelp) return;
      button.dataset.fdHelp = '1';
      button.setAttribute('aria-expanded', 'false');
      button.addEventListener('click', () => {
        const open = button.getAttribute('aria-expanded') !== 'true';
        button.setAttribute('aria-expanded', String(open));
      });
    });
  }
  function start() {
    foldSignals();
    compactCards();
    wireHelp();
    const board = document.getElementById('scoreboard-cards');
    if (board) new MutationObserver(compactCards).observe(board, {childList: true, subtree: true});
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', start, {once: true});
  else start();
})();
