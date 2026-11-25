const assert=require('assert'),vm=require('vm'),fs=require('fs');
const events={};
const js=fs.readFileSync('assets/fd-weekly-h2h.js','utf8');
const calc=vm.runInNewContext('('+js.match(/function breakEven\(price\)\{[\s\S]*?\n \}/)[0]+')');
assert(Math.abs(calc(-110)-52.380952)<.001);assert.equal(calc(200),100/3);assert.equal(calc(-99),null);
function element(tag){return {tag,textContent:'',innerHTML:'',value:'',appendChild(child){this.child=child},after(){},addEventListener(type,fn){if(tag==='select')events[this.value]=fn;}}}
const root={innerHTML:'',querySelector(s){if(s==='.fd-h2h-intro')return element('p');return {addEventListener(){}};}};
const market=(rows)=>({market:'rushing_yards',label:'Rushing yards',winner:'regular',samples:rows.length,regular_mae:1,ml_mae:1,regular_wins:0,ml_wins:0,ties:0,details:rows});
const row=(position,actual,line,regular,ml,result)=>({position,actual,dk_line:line,regular,ml,regular_pick_result:result,ml_pick_result:result,label:position,winner:'tie'});
const weeks=[{season:2026,week:11,markets:[market([row('RB',40,40.5,42,38,'miss'),row('WR',10,null,20,20,'unavailable')])]},{season:2026,week:10,markets:[market([row('RB',50,45.5,44,44,'miss')])]}];
const document={getElementById:()=>root,createElement:element};
vm.runInNewContext(fs.readFileSync('assets/fd-weekly-h2h.js','utf8'),{document,fetch:async()=>({ok:true,json:async()=>({weeks})}),console,setTimeout,Date,Number,String,Math});
setTimeout(()=>{
 assert(root.innerHTML.includes('Too high 6.0 yards'));
 events['1']({target:{value:'4'}});
 assert(root.innerHTML.includes('Too high 2.0 yards'));
 events['all']({target:{value:'RB'}});
 assert(root.innerHTML.includes('Too low 2.0 yards'));
 assert(root.innerHTML.includes('2 matched projections'));
 console.log('Trend window, position and no-line bias tests passed');
},0);
