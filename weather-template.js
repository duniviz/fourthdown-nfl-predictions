/* FOURTHDOWN initial live weather template v1.
   Forecast-only, before kickoff, never alters saved/archived predictions.
   Fixed heuristic coefficients; not yet backtest validated. */
(function(root){
'use strict';
function finite(v){return v!==null&&v!==undefined&&v!==''&&Number.isFinite(Number(v))?Number(v):null;}
function scenario(weather,generatedAt,kickoff){
 if(!weather||weather.status!=='forecast')return null;
 const now=Date.now(),kick=Date.parse(kickoff),captured=Date.parse(generatedAt);
 if(!Number.isFinite(kick)||!Number.isFinite(captured)||captured>=kick||now>=kick)return null;
 const wind=finite(String(weather.wind_speed||'').match(/\d+(?:\.\d+)?/)?.[0]);
 const temp=finite(weather.temperature_f),precip=finite(weather.precipitation_probability);
 if(wind===null||temp===null||precip===null||wind<0||wind>150||temp< -100||temp>140||precip<0||precip>100)return null;
 let pts=0,pass=0,passAttempts=0,receptions=0,rush=0,eff=0;
 const reasons=[];
 if(wind>=25){pts-=5;pass-=.12;passAttempts-=.04;receptions-=.08;rush+=.06;eff-=.02;reasons.push('strong wind');}
 else if(wind>=18){pts-=3;pass-=.07;passAttempts-=.02;receptions-=.05;rush+=.03;eff-=.01;reasons.push('wind');}
 else if(wind>=12){pts-=1;pass-=.03;receptions-=.02;rush+=.01;reasons.push('breezy');}
 if(temp<=20){pts-=1;pass-=.02;rush+=.01;reasons.push('extreme cold');}
 const condition=String(weather.conditions||'').toLowerCase();
 const heavy=precip>=60&&/rain|snow|sleet|storm|shower/.test(condition);
 if(heavy){pts-=2;pass-=.05;receptions-=.03;rush+=.03;eff-=.03;reasons.push('precipitation');}
 return {points:Math.max(-3,pts),passing:Math.max(-.05,pass),passAttempts:Math.max(-.05,passAttempts),
  receptions:Math.max(-.05,receptions),rushAttempts:Math.min(.05,rush),rushEfficiency:Math.max(-.05,eff),
  reasons,wind,temp,precip,version:'weather-template-v1'};
}
function adjust(market,baseline,s){
 const n=finite(baseline);if(n===null||n<0||!s)return null;
 const factors={passing_yards:s.passing,receiving_yards:s.passing,pass_attempts:s.passAttempts,pass_completions:(1+s.passAttempts)*(1+s.receptions)-1,
  receptions:s.receptions,rush_attempts:s.rushAttempts,
  rushing_yards:(1+s.rushAttempts)*(1+s.rushEfficiency)-1};
 const factor=Math.max(-.05,Math.min(.05,factors[market]||0));
 if(market==='game_total')return Math.max(0,n+s.points);
 if(market==='home_score'||market==='away_score')return Math.max(0,n+s.points/2);
 return Math.max(0,n*(1+factor));
}
root.FDWeatherTemplate={scenario,adjust};
})(typeof window!=='undefined'?window:globalThis);
