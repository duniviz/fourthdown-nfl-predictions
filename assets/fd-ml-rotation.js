/* Research-card display only; never modifies official forecasts or picks. */
(function(root){
 'use strict';
 const base=['ridge','random_forest','gradient_boosting','xgboost'];
 const algorithms=new Set(base.flatMap(name=>[name,name+'_recent',name+'_form',name+'_form_recent']));
 function create(rotation,live,players,counts,now=Date.now()){
  const valid=rotation&&rotation.research_only===true&&Number(rotation.season)===Number(live?.season)&&Number(rotation.week)===Number(live?.week)&&rotation.forecast_generated_at_utc===live?.generated_at_utc;
  const stamp=Date.parse(rotation?.generated_at_utc||'');
  if(!valid||!Number.isFinite(stamp)||stamp>now||now-stamp>120*3600000)return ()=>null;
  const byKey=new Map();
  for(const row of rotation.candidates||[]){
   const key=[row.game_id,row.player_id,row.market].join('|');
   if(byKey.has(key))byKey.set(key,null);else byKey.set(key,row);
  }
  return (game,player,market)=>{
   const row=byKey.get([game,player,market].join('|'));
   if(!row||Date.parse(row.kickoff_utc)<=now)return null;
   const d=row.selected;
   if(!d||!algorithms.has(d.model)||!Number.isInteger(d.samples)||d.samples<(player==='GAME'?4:10))return null;
   if(player!=='GAME'){
    const count=String(market).startsWith('player_');
    if(count ? rotation.count_generated_at_utc!==counts?.generated_at_utc : rotation.player_generated_at_utc!==players?.generated_at_utc)return null;
   }
   const v=row.predictions?.[d.model];
   if(typeof v!=='number'||!Number.isFinite(v))return null;
   return {candidate:v,active:false,research_only:true,variant:d.model,comparison_week:d.week,comparison_season:d.season,samples:d.samples};
  };
 }
 root.FDMlRotation={create};
 if(typeof module!=='undefined')module.exports={create};
})(typeof window==='undefined'?globalThis:window);
