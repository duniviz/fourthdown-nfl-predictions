/* FOURTHDOWN shared shell. Presentation only. */
(() => {
  'use strict';
  const file = () => location.pathname.split('/').pop() || 'index.html';
  const onHome = () => { const name = file(); return name === '' || name === 'index.html'; };
  const items = [
    ['index.html#fd-slate-pulse', 'Games'],
    ['bets.html', 'Props'],
    ['history.html', 'Results']
  ];
  const tools = [
    ['model-lab.html', 'Model Lab'],
    ['pipeline-health.html', 'Pipeline Health'],
    ['index.html#reading-guide', 'How to read']
  ];
  function current(href) {
    const name = file();
    const home = name === '' || name === 'index.html';
    if (href.indexOf('#fd-slate-pulse') !== -1) return home && location.hash === '#fd-slate-pulse';
    if (href.indexOf('#scoreboard') !== -1) return home && location.hash === '#scoreboard';
    if (href.indexOf('#reading-guide') !== -1) return home && location.hash === '#reading-guide';
    if (href === 'index.html') return home && location.hash !== '#scoreboard';
    return href.split('#')[0] === name;
  }
  function link(href, label) {
    return '<a href="' + href + '"' + (current(href) ? ' aria-current="page"' : '') + '>' + label + '</a>';
  }
  function render() {
    if (document.querySelector('.fd2-header')) return;
    const header = document.createElement('header');
    header.className = 'fd2-header';
    header.innerHTML = '<div class="fd2-shell"><a class="fd2-brand" href="index.html">FOURTH<b>DOWN</b><small>NFL PREDICTIONS</small></a><nav class="fd2-links" aria-label="Primary navigation">' + items.map(([href, label]) => link(href, label)).join('') + '</nav></div>';
    if (!document.getElementById('fd2-tools-style')) {
      const style = document.createElement('style');
      style.id = 'fd2-tools-style';
      style.textContent = '.fd2-tools{display:flex;align-items:center;gap:8px;flex-wrap:wrap;width:min(1380px,calc(100% - 48px));margin:8px auto 12px}.fd2-tools>a{display:inline-flex;align-items:center;justify-content:center;min-height:38px;padding:8px 13px;border:1px solid #35536c;border-radius:10px;background:#101d2b;color:#dcebf4;text-decoration:none;font-size:12px;font-weight:800}.fd2-tools>a:hover,.fd2-tools>a:focus-visible{border-color:#ff9b69;color:#fff}.fd2-tools>a[aria-current="page"]{border-color:#b6d95e;background:#202d19;color:#d8ff81}@media(max-width:850px){.fd2-tools{width:auto;margin:8px 14px 12px;gap:7px}.fd2-tools>a{flex:1 1 auto;padding:8px 10px;min-height:40px}}';
      document.head.append(style);
    }
    const toolsNav = document.createElement('nav');
    toolsNav.className = 'fd2-tools';
    toolsNav.setAttribute('aria-label', 'Labs and tools');
    toolsNav.innerHTML = tools.map(([href, label]) => link(href, label)).join('');

    document.body.insertBefore(header, document.body.firstChild);
    const badge = document.getElementById('fd-freshness-badge');
    const shell = header.querySelector('.fd2-shell');
    const viewPicker = document.querySelector('.fd-view-picker');
    if (viewPicker && shell) shell.append(viewPicker);
    if (badge && shell) shell.append(badge);
    const bottom = document.createElement('nav');
    bottom.className = 'fd2-bottom';
    bottom.setAttribute('aria-label', 'Mobile navigation');
    bottom.innerHTML = items.map(([href, label]) => link(href, label)).join('');
    document.body.append(bottom);
    header.insertAdjacentElement('afterend', toolsNav);
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
    // The compact home page keeps the scoreboard inside a collapsed Games disclosure.
    // Open every disclosure ancestor before scrolling so the Games link works even
    // when the page is already on #scoreboard and no hashchange event will fire.
    let parent = board.parentElement;
    while (parent) {
      if (parent.tagName === 'DETAILS') parent.open = true;
      parent = parent.parentElement;
    }
    const behavior = window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth';
    const scroll = () => board.scrollIntoView({behavior, block: 'start'});
    if (typeof window.requestAnimationFrame === 'function') {
      window.requestAnimationFrame(() => window.requestAnimationFrame(scroll));
    } else {
      setTimeout(scroll, 0);
    }
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
