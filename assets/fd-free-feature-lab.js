(function(root){
  'use strict';
  const markets=[['passing_yards','Passing yards'],['rushing_yards','Rushing yards'],['receiving_yards','Receiving yards']];
  const labels={pfr_fixed:'PFR',ftn_player:'FTN player',ftn_opponent:'FTN opponent',pfr_ftn:'PFR + FTN',pfr_plus:'Existing advanced + PFR',ftn_plus:'Existing advanced + FTN',ftn_opponent_plus:'Existing advanced + FTN opponent',pfr_ftn_plus:'Existing advanced + PFR + FTN',all_new:'All new sources'};
  const number=x=>x===null||x===undefined||!Number.isFinite(Number(x))?'—':Number(x).toFixed(2);
  function summarize(report,selection){
    return markets.map(([key,label])=>{
      const r=report?.markets?.[key]||{},s=selection?.player?.[key]||{};
      const trials=Object.entries(r.pfr_ftn_comparisons||{}).map(([name,comparison])=>({name:labels[name]||name,reference:comparison.reference,selection:comparison.selection,confirmation:comparison.confirmation}));
      return {label,selected:s.research_winner||'Not available',coverage:r.source_coverage||{},trials};
    });
  }
  if(typeof module!=='undefined'&&module.exports)module.exports={summarize};
  if(!root.document)return;
  async function start(){
    const el=root.document.getElementById('fd-free-feature-lab');if(!el)return;
    async function read(path){try{const r=await fetch(path+'?t='+Date.now(),{cache:'no-store'});return r.ok?await r.json():null;}catch{return null;}}
    const [report,selection]=await Promise.all([read('data/research-free-nfl-features.json'),read('data/market-ml-research-selection.json')]);
    if(!report||!selection){el.textContent='Research results are not available yet.';return;}
    el.textContent='';
    for(const market of summarize(report,selection)){
      const group=root.document.createElement('details');group.className='fd-research-details';
      const title=root.document.createElement('summary');title.textContent=market.label+' · ML candidate: '+market.selected.replaceAll('_',' ');group.append(title);
      const coverage=root.document.createElement('p');coverage.className='muted';coverage.textContent='Eligible historical rows: PFR '+(market.coverage.pfr_new||0)+', FTN player '+(market.coverage.ftn||0)+', FTN opponent '+(market.coverage.ftn_defense||0)+'.';group.append(coverage);
      if(!market.trials.length){const p=root.document.createElement('p');p.textContent='No matched PFR or FTN comparisons have been published yet.';group.append(p);}
      for(const trial of market.trials){
        const p=root.document.createElement('p');p.className='fd-lab-sub';
        const a=trial.selection||{},b=trial.confirmation||{};
        p.textContent=trial.name+' vs '+String(trial.reference||'unavailable').replaceAll('_',' ')+': selection '+number(a.candidate_mae)+' vs '+number(a.reference_mae)+' yards MAE ('+(a.samples||0)+' player games); later confirmation '+number(b.candidate_mae)+' vs '+number(b.reference_mae)+' MAE and '+number(b.candidate_rmse)+' vs '+number(b.reference_rmse)+' RMSE ('+(b.samples||0)+' player games). Lower is better.';
        group.append(p);
      }
      el.append(group);
    }
  }
  start();
})(typeof window!=='undefined'?window:globalThis);
