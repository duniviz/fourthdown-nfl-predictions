/* Compact weekly sports desk: moves existing live sections without cloning or recalculating data. */
(() => {
  'use strict';
  function details(id, title, note) {
    const el = document.createElement('details');
    el.id=id; el.className='fd-desk-fold';
    const summary=document.createElement('summary');
    summary.innerHTML='<span><strong>'+title+'</strong><small>'+note+'</small></span><span class="fd-desk-chevron" aria-hidden="true"></span>';
    el.append(summary);
    return el;
  }
  function appendIf(target, node) { if (node) target.append(node); }
  function init(){
    const home=document.getElementById('fd-betting-board');
    if(!home||document.getElementById('fd-desk-games'))return;
    document.body.classList.add('fd-compact-desk');
    const results=document.getElementById('fd-bb-results');
    const tabs=home.querySelector('.fd-bb-tabs');
    const savedCount=document.getElementById('fd-desk-slip-count');
    if(savedCount){try{
      const list=JSON.parse(localStorage.getItem('fd-my-slip-v1')||'[]');
      if(Array.isArray(list))savedCount.textContent=list.length+' saved';
    }catch(e){savedCount.textContent='Slip unavailable'}}

    if(results&&tabs)home.insertBefore(results,tabs);
    const layout=document.createElement('div');
    layout.id='fd-weekly-desk';
    layout.className='fd-weekly-desk';
    home.after(layout);
    const games=details('fd-desk-games','Games & live scores','Live scoreboard · upcoming games · final results');
    const live=document.getElementById('fd-slate-pulse');
    const slate=document.getElementById('fd-bb-slate');
    const scoreboard=document.getElementById('scoreboard');
    // Keep original node IDs, score refresh handlers, popups and live observers intact.
    if(live)games.append(live);
    if(slate){const label=document.createElement('h3');label.textContent='This week’s slate';games.append(label,slate)}
    if(scoreboard)games.append(scoreboard);
    layout.append(games);
    const more=details('fd-desk-more','More this week','Top picks · featured matchups · player differences');
    for(const selector of ['#fd-top-picks','#fd-opportunities','.hybrid-spot','#fd-watch','#confidence-pool','.fd-command']){
      const node=document.querySelector(selector);
      if(node&&!more.contains(node))more.append(node);
    }
    // A prior presentation pass may have already nested these inside Top Picks.
    layout.append(more);
    const research=details('fd-desk-research','Research & archived examples','Past forecasts · historic comparisons · how our picks work');
    for(const selector of ['#tracking','#reading-guide','#model-v2','#picks','#markets','#props','#parlays']){
      appendIf(research,document.querySelector(selector));
    }
    const links=document.createElement('p');links.className='fd-desk-research-links';
    links.innerHTML='<a href="history.html">History & grading</a><a href="model-lab.html">Model Lab & backtests</a><a href="pipeline-health.html">Pipeline Health</a>';
    research.append(links);
    layout.append(research);
    const old=document.getElementById('fd-more');
    if(old){old.hidden=true;old.setAttribute('aria-hidden','true');old.tabIndex=-1}
    research.addEventListener('toggle',()=>{if(research.open){
      document.body.classList.add('fd-expanded');
      if(old)old.setAttribute('aria-expanded','true');
    }});
    function revealHash(){
      const hash=decodeURIComponent(location.hash.slice(1));
      const node=hash&&document.getElementById(hash);
      if(!node)return;
      for(const fold of [games,more,research])if(fold.contains(node))fold.open=true;
    }
    window.addEventListener('hashchange',revealHash);revealHash();
  }
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',init,{once:true});
  else init();
})();
