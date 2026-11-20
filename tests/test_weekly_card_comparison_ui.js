const assert=require('assert');
const root={innerHTML:'',querySelector(){return {addEventListener(){}};}};
global.document={getElementById(){return root;}};
global.fetch=async()=>({ok:true,json:async()=>({weeks:[{season:2026,week:11,markets:[{label:'Game total',winner:'regular',samples:1,regular_mae:14.43,ml_mae:18.43,regular_wins:1,ml_wins:0,ties:0,details:[{label:'IND @ HOU',actual:29,regular:43.43,ml:47.43,winner:'regular'}]}]}]})});
require('../assets/fd-weekly-h2h.js');
setTimeout(()=>{assert(root.innerHTML.includes('Regular was closer'));assert(root.innerHTML.includes('IND @ HOU'));assert(root.innerHTML.includes('29.0'));assert(root.innerHTML.includes('Week 11'));console.log('Weekly card comparison UI passed');},0);
