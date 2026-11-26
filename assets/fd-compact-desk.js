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
    // Keep the most useful picks visible, with the full slate one tap away.
    const edges=details('fd-desk-edges','Best picks & edges','Top 5 picks · DraftKings comparisons');
    edges.classList.add('fd-desk-edges-fold');
    edges.open=false;
    home.before(edges);
    edges.append(home);
    const layout=document.createElement('div');
    layout.id='fd-weekly-desk';
    layout.className='fd-weekly-desk';
    edges.before(layout);
    const games=details('fd-desk-games','Games & live scores','This week’s slate · live scoreboard · final results');
    games.classList.add('fd-desk-games-primary');
    games.open=true;
    const live=document.getElementById('fd-slate-pulse');
    const slate=document.getElementById('fd-bb-slate');
    const scoreboard=document.getElementById('scoreboard');
    // Keep original node IDs, score refresh handlers, popups and live observers intact.
    if(live)games.append(live);
    // Keep the legacy matchup rows inside Best edges for direct links and archived comparison.
    if(scoreboard)games.append(scoreboard);
    layout.append(games);
    layout.append(edges);
    const more=details('fd-desk-more','More this week','Top picks · featured matchups · player differences');
    for(const selector of ['#fd-top-picks','#fd-opportunities','.hybrid-spot','#fd-watch','#confidence-pool','.fd-command']){
      const node=document.querySelector(selector);
      if(node&&!more.contains(node))more.append(node);
    }
    // A prior presentation pass may have already nested these inside Top Picks.
    layout.append(more);
    const research=details('fd-desk-research','How it works','Past results · model testing · site details');
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
      for(const fold of [games,edges,more,research])if(fold.contains(node))fold.open=true;
    }
    function attachSlateCards(){
      const visible=Array.isArray(window.fdVisibleGames)?window.fdVisibleGames:[];
      const teamCode=value=>({JAX:'JAC',WSH:'WAS',LA:'LAR'}[String(value||'').toUpperCase()]||String(value||'').toUpperCase());
      const rows=document.querySelectorAll('#fd-bb-slate .fd-bb-row[data-home-team][data-away-team]:not(.fd-bb-final)');
      for(const row of rows){
        let slot=row.querySelector(':scope > .fd-bb-inline-matchup');
        if(!slot){slot=document.createElement('div');slot.className='fd-bb-inline-matchup';slot.setAttribute('aria-label','Complete live matchup card');row.insertBefore(slot,row.querySelector(':scope > .fd-bb-detail'));}
        const match=visible.find(g=>teamCode(g.home?.abbr)===teamCode(row.dataset.homeTeam)&&teamCode(g.away?.abbr)===teamCode(row.dataset.awayTeam));
        if(!match){slot.replaceChildren();continue;}
        const button=[...document.querySelectorAll('#scoreboard-cards [data-matchup-id]')].find(el=>el.dataset.matchupId===String(match.id));
        const card=button&&button.closest('.scorecard');
        if(card)slot.replaceChildren(card);
      }
    }
    const scoreboardCards=document.getElementById('scoreboard-cards');
    if(scoreboardCards)new MutationObserver(attachSlateCards).observe(scoreboardCards,{childList:true,subtree:true});
    const slateHost=document.getElementById('fd-bb-slate');
    if(slateHost)new MutationObserver(attachSlateCards).observe(slateHost,{childList:true,subtree:true});
    window.addEventListener('fd-scoreboard-updated',attachSlateCards);
    attachSlateCards();
    window.addEventListener('hashchange',revealHash);revealHash();
  }
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',init,{once:true});
  else init();
})();
