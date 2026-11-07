/* Visualize verified grading counts from the existing fail-closed ledger. */
(function(){
'use strict';
const labels={winner:'Winner picks',ats:'Against spread',ou:'Over / Under',props:'Player props'};
function draw(){
 const host=document.getElementById('fd-accuracy-dashboard'),data=window.FOURTHDOWN_GRADES;
 if(!host||!data)return;
 const counts=data.counts||{};
 const totals=Object.values(counts).reduce((a,x)=>({graded:a.graded+(x.graded||0),hit:a.hit+(x.hit||0),pending:a.pending+(x.pending||0),missing:a.missing+(x.missing||0)}),{graded:0,hit:0,pending:0,missing:0});
 const el=(tag,cls,text)=>{const n=document.createElement(tag);if(cls)n.className=cls;if(text!==undefined)n.textContent=text;return n;};
 host.replaceChildren();
 const head=el('div','fd-accuracy-head');
 const title=el('div');title.append(el('span','fd-accuracy-eyebrow','VERIFIED PERFORMANCE'),el('h2','','Accuracy at a glance'));
 head.append(title,el('span','fd-accuracy-coverage',totals.graded+' graded picks'));host.append(head);
 const grid=el('div','fd-accuracy-grid');
 for(const [key,label] of Object.entries(labels)){
  const c=counts[key]||{},graded=Number(c.graded)||0,hit=Number(c.hit)||0,rate=graded?100*hit/graded:null;
  const card=el('article','fd-accuracy-tile');card.append(el('small','',label),el('strong','',rate===null?'—':rate.toFixed(1)+'%'));
  const track=el('div','fd-accuracy-track');track.setAttribute('role','progressbar');track.setAttribute('aria-label',label+' hit rate');track.setAttribute('aria-valuemin','0');track.setAttribute('aria-valuemax','100');if(rate!==null)track.setAttribute('aria-valuenow',rate.toFixed(1));else track.setAttribute('aria-valuetext','No graded picks');const fill=el('span');fill.style.width=(rate===null?0:rate)+'%';track.append(fill);card.append(track);
  card.append(el('p','',hit+' hits / '+graded+' graded'),el('small','fd-accuracy-secondary',(c.pending||0)+' pending · '+(c.missing||0)+' ungraded'+(c.push?' · '+c.push+' pushes':'')));grid.append(card);
 }
 host.append(grid);
 host.append(el('p','fd-accuracy-disclaimer','Only eligible verified pregame records are counted. Ungraded and missing records are not losses or wins.'));
}
document.addEventListener('fourthdown:grades-ready',draw);
if(window.FOURTHDOWN_GRADES)draw();
})();