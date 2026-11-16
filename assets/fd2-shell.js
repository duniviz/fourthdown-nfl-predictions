/* FOURTHDOWN shared shell. Presentation only. */
(() => {
  'use strict';
  const file = () => location.pathname.split('/').pop() || 'index.html';
  const onHome = () => { const name = file(); return name === '' || name === 'index.html'; };
  const items = [
    ['index.html', 'Edges'],
    ['index.html#scoreboard', 'Games'],
    ['bets.html', 'Props'],
    ['history.html', 'Results']
  ];
  const more = [
    ['model-lab.html', 'Model Lab'],
    ['pipeline-health.html', 'Pipeline Health'],
    ['index.html#reading-guide', 'How to read']
  ];
  function current(href) {
    const name = file();
    const home = name === '' || name === 'index.html';
    if (href.indexOf('#scoreboard') !== -1) return home && location.hash === '#scoreboard';
    if (href === 'index.html') return home && location.hash !== '#scoreboard';
    return href.split('#')[0] === name;
  }
  function moreCurrent() {
    const name = file();
    return name === 'model-lab.html' || name === 'pipeline-health.html';
  }
  function link(href, label) {
    return '<a href="' + href + '"' + (current(href) ? ' aria-current="page"' : '') + '>' + label + '</a>';
  }
  function menu(className) {
    const links = more.map(([href, label]) => '<a href="' + href + '"' + (current(href) ? ' aria-current="page"' : '') + '>' + label + '</a>').join('');
    return '<details class="fd-more' + (moreCurrent() ? ' fd-more-here' : '') + '"' + (moreCurrent() ? ' open' : '') + '><summary' + (moreCurrent() ? ' aria-current="page"' : '') + '>More</summary><div class="' + className + '">' + links + '</div></details>';
  }
  function render() {
    if (document.querySelector('.fd2-header')) return;
    const header = document.createElement('header');
    header.className = 'fd2-header';
    header.innerHTML = '<div class="fd2-shell"><a class="fd2-brand" href="index.html">FOURTH<b>DOWN</b><small>NFL PREDICTIONS</small></a><nav class="fd2-links" aria-label="Primary navigation">' + items.map(([href, label]) => link(href, label)).join('') + menu('fd-more-menu') + '</nav></div>';
    document.body.insertBefore(header, document.body.firstChild);
    const badge = document.getElementById('fd-freshness-badge');
    const shell = header.querySelector('.fd2-shell');
    if (badge && shell) shell.append(badge);
    const bottom = document.createElement('nav');
    bottom.className = 'fd2-bottom';
    bottom.setAttribute('aria-label', 'Mobile navigation');
    bottom.innerHTML = items.map(([href, label]) => link(href, label)).join('') + menu('fd-more-menu');
    document.body.appendChild(bottom);
    const hero = document.querySelector('.hero,.page-intro');
    if (hero) hero.classList.add('fd2-hero');
    if (onHome()) {
      const duplicate = document.querySelector('.hybrid-spot');
      const primary = document.querySelector('#fd-opportunities');
      if (duplicate && primary && !document.querySelector('#fd2-secondary-research')) {
        const detail = document.createElement('details');
        detail.id = 'fd2-secondary-research';
        detail.className = 'fd2-details';
        const summary = document.createElement('summary');
        summary.textContent = 'More player projection research';
        detail.append(summary, duplicate);
        primary.append(detail);
      }
      const guide = document.querySelector('#reading-guide');
      if (guide && !guide.closest('details')) {
        const details = document.createElement('details');
        details.id = 'fd-how-to-read';
        details.className = 'fd2-details fd2-guide';
        if (location.hash === '#reading-guide') details.open = true;
        const summary = document.createElement('summary');
        summary.textContent = 'How to read predictions';
        guide.parentNode.insertBefore(details, guide);
        details.append(summary, guide);
      }
    }
    document.body.classList.add('fd2-ready');
  }
  function scrollScoreboard() {
    const board = document.getElementById('scoreboard');
    if (!board) return false;
    board.scrollIntoView({behavior: window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth', block: 'start'});
    return true;
  }
  document.addEventListener('click', event => {
    const anchor = event.target.closest && event.target.closest('a[href]');
    if (!anchor || !onHome()) return;
    const href = anchor.getAttribute('href') || '';
    if (href.indexOf('#scoreboard') === -1) return;
    if (scrollScoreboard()) {
      event.preventDefault();
      if (location.hash !== '#scoreboard') history.pushState(null, '', '#scoreboard');
    }
  });
  window.addEventListener('hashchange', () => { if (location.hash === '#scoreboard') scrollScoreboard(); });
  window.addEventListener('load', () => { if (location.hash === '#scoreboard') setTimeout(scrollScoreboard, 80); });
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', render, {once: true});
  else render();
})();
