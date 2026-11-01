/* Shared FOURTHDOWN pregame snapshot reader.
 * Historical values must originate from a published, timestamped pre-kickoff record.
 * Never reconstruct historical projections from current model output. */
(function(root){
 'use strict';
 const finite=v=>v!==null&&v!==undefined&&v!==''&&Number.isFinite(Number(v))?Number(v):null;
 const key=v=>String(v??'').trim().toLowerCase().replace(/[^a-z0-9]/g,'');
 function valid(record,kickoff){
  if(!record||!record.captured_at||!kickoff)return false;
  const captured=Date.parse(record.captured_at),start=Date.parse(kickoff);
  return Number.isFinite(captured)&&Number.isFinite(start)&&captured<start;
 }
 function select(records,match,kickoff){
  if(!Array.isArray(records))return null;
  return records.filter(r=>valid(r,kickoff)&&
   ['game_id','player_id','team','market'].every(k=>match[k]==null||key(r[k])===key(match[k])))
   .sort((a,b)=>Date.parse(b.captured_at)-Date.parse(a.captured_at))[0]||null;
 }
 function display(record,actual){
  return {projection:finite(record?.projection),dk_line:finite(record?.dk_line),
   actual:finite(actual),captured_at:record?.captured_at||null,
   source:record?'pregame_snapshot':'unavailable'};
 }
 async function load(path='data/pregame-snapshots.json'){
  const response=await fetch(path,{cache:'no-store'});
  if(!response.ok)throw Error('Snapshot feed unavailable');
  const data=await response.json();
  if(!Array.isArray(data.records))throw Error('Invalid snapshot feed');
  return data.records;
 }
 root.FourthdownPregame=Object.freeze({valid,select,display,load});
})(window);
