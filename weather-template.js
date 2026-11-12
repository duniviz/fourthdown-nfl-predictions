/* FOURTHDOWN weather research candidate v3.
   Historical weather and position splits from P3 Adaptive's NFL Weather Effects
   report (nflverse + Open-Meteo, 1999-present). Position splits are 50% shrunk
   toward no effect; the observed category averages are not causal estimates.
   Forecast classifications are proxies and never alter saved/live forecasts. */
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
 const condition=String(weather.conditions||'').toLowerCase();
 // P3 historical data uses measurable precipitation during the game.
 // Forecast chance is only a proxy, so scale its effect by the forecast probability.
 const rain=precip>0&&/rain|shower|storm/.test(condition);
 const snow=precip>0&&/snow|sleet/.test(condition);
 const rainWeight=rain?precip/100:0,snowWeight=snow?precip/100:0;
 const windy=wind>=15,breezy=wind>=8&&wind<15,freezing=temp<32,hot=temp>=80;
 let points=0,passing=0,passAttempts=0,receptions=0,rushAttempts=0;
 const reasons=[];
 if(rain){points-=0.8*rainWeight;passing-=0.025*rainWeight;passAttempts-=0.01*rainWeight;receptions-=0.02*rainWeight;rushAttempts+=0.01*rainWeight;reasons.push('rain chance '+Math.round(precip)+'%');}
 if(windy){points-=wind>=22?1.0:0.6;passing-=0.02;passAttempts-=0.01;receptions-=0.01;rushAttempts+=0.01;reasons.push(wind>=22?'very windy':'windy (15+ mph)');}
 else if(breezy){points-=0.3;passing-=0.01;reasons.push('breezy (8–14 mph)');}
 if(snow){passing-=0.01*snowWeight;reasons.push('snow chance '+Math.round(precip)+'%');}
 if(freezing){passing-=0.01;reasons.push('freezing (<32°F)');}
 if(hot)reasons.push('hot (80°F+ estimate)');
 return {points,passing,passAttempts,receptions,rushAttempts,rushEfficiency:0,
  reasons,wind,temp,precip,rain,snow,rainWeight,snowWeight,windy,breezy,freezing,hot,
  hotThresholdEstimated:true,version:'weather-context-v3',
  evidence:{source:'P3 Adaptive NFL Weather Effects',fairGames:4397,windyGames:279,rainGames:295,freezingGames:324,
   observed:{fairPoints:43.9,rainPoints:39.3,windyPoints:40.5,rainPassRatePct:57.9,fairPassRatePct:59.5,
    rainPassEpa:-0.030,fairPassEpa:0.045,rainCompletionPct:54.6,fairCompletionPct:57.3,
    rainYardsPerAttempt:6.10,fairYardsPerAttempt:6.50,freezingPoints:43.5}}};
}
function adjust(market,baseline,s){
 const n=finite(baseline);if(n===null||n<0||!s)return null;
 const factors={passing_yards:s.passing,receiving_yards:s.passing,pass_attempts:s.passAttempts,
  pass_completions:s.passAttempts,receptions:s.receptions,rush_attempts:s.rushAttempts,rushing_yards:s.rushAttempts,
  player_pass_yds:s.passing,player_rec_yds:s.passing,player_pass_attempts:s.passAttempts,
  player_pass_completions:s.passAttempts,player_receptions:s.receptions,player_rush_attempts:s.rushAttempts,
  player_rush_yds:s.rushAttempts};
 const key=String(market||'').toLowerCase();
 if(key==='game_total')return Math.max(0,n+s.points);
 if(key==='home_score'||key==='away_score')return Math.max(0,n+s.points/2);
 const factor=factors[key]||0;
 return Math.max(0,n*(1+Math.max(-.05,Math.min(.05,factor))));
}
function adjustFantasy(market,baseline,s,position){
 const n=finite(baseline);if(n===null||n<0||!s)return null;
 const pos=String(position||'').toUpperCase(),key=String(market||'').toLowerCase();
 const categoryWeights=[];
 if(s.rain)categoryWeights.push(['rain',s.rainWeight]);
 if(s.snow)categoryWeights.push(['snow',s.snowWeight]);
 if(s.windy)categoryWeights.push(['windy',1]);
 if(s.freezing)categoryWeights.push(['freezing',1]);
 if(s.hot)categoryWeights.push(['hot',1]);
 const rates={
  QB:{passing_yards:{rain:-.091,snow:-.120,windy:-.079,freezing:-.050,hot:-.030}},
  WR:{receiving_yards:{rain:-.101,snow:-.118,windy:-.075,freezing:-.050,hot:-.010},
      receptions:{rain:-.050,snow:-.090,windy:-.090,freezing:-.010,hot:0}},
  TE:{receiving_yards:{rain:-.083,snow:-.137,windy:-.122,freezing:-.070,hot:-.108}},
  RB:{receptions:{rain:-.030,snow:-.050,windy:-.120,freezing:.020,hot:0}}
 };
 const alias={player_pass_yds:'passing_yards',passing_yards:'passing_yards',
  player_rec_yds:'receiving_yards',receiving_yards:'receiving_yards',
  player_receptions:'receptions',receptions:'receptions'};
 const metric=alias[key],byCategory=rates[pos]?.[metric];
 if(!byCategory)return null;
 const applicable=categoryWeights.map(([name,weight])=>({name,weight,rate:byCategory[name]}))
  .filter(x=>x.rate!==undefined&&x.weight>0)
  .sort((a,b)=>Math.abs(b.rate*b.weight)-Math.abs(a.rate*a.weight));
 if(!applicable.length)return null;
 // Overlapping weather types use the strongest relevant split once, not as additive penalties.
 const chosen=applicable[0],shrinkage=0.5;
 return {projection:Math.max(0,n*(1+chosen.rate*chosen.weight*shrinkage)),
  category:chosen.name,observedRate:chosen.rate,forecastWeight:chosen.weight,shrinkage,
  label:'P3 position split · 50% shrunk · '+chosen.name};
}
root.FDWeatherTemplate={scenario,adjust,adjustFantasy};
})(typeof window!=='undefined'?window:globalThis);
