/* FOURTHDOWN weather research candidate v3.
   Historical weather and position splits from P3 Adaptive's NFL Weather Effects
   report (nflverse + Open-Meteo, 1999-present). Position splits are 50% shrunk
   toward no effect; the observed category averages are not causal estimates.
   Forecast classifications are proxies and never alter saved/live forecasts. */
(function(root){
'use strict';
function finite(v){return v!==null&&v!==undefined&&v!==''&&Number.isFinite(Number(v))?Number(v):null;}
function scenario(weather,generatedAt,kickoff,isIndoor=false){
 const now=Date.now(),kick=Date.parse(kickoff),captured=Date.parse(generatedAt);
 if(isIndoor){
  if(!Number.isFinite(kick)||now>=kick)return null;
  return {points:1.5,passing:0,passAttempts:0,receptions:0,rushAttempts:0,rushEfficiency:0,
   reasons:['indoors'],wind:null,temp:null,precip:null,rain:false,snow:false,rainWeight:0,snowWeight:0,
   windy:false,breezy:false,freezing:false,hot:false,indoor:true,
   version:'weather-context-v4',evidence:{source:'P3 Adaptive NFL Weather Effects',category:'Indoors',observedPointsPerGame:46.9,fairPointsPerGame:43.9,shrinkage:0.5}};
 }
 if(!weather||weather.status!=='forecast')return null;
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
 const windy=wind>=15,breezy=wind>=8&&wind<15,freezing=temp<32,hot=temp>=85;
 let passing=0,passAttempts=0,receptions=0,rushAttempts=0;
 const reasons=[],pointCandidates=[];
 // P3 per-game scoring differences, shrunk 50% toward no adjustment.
 if(rain){pointCandidates.push(-2.3*rainWeight);passing-=0.025*rainWeight;passAttempts-=0.01*rainWeight;receptions-=0.02*rainWeight;rushAttempts+=0.01*rainWeight;reasons.push('rain chance '+Math.round(precip)+'%');}
 if(windy){pointCandidates.push(wind>=22?-5.5:-1.9);passing-=0.02;passAttempts-=0.01;receptions-=0.01;rushAttempts+=0.01;reasons.push(wind>=22?'very windy (22+ mph)':'windy (15–21 mph)');}
 else if(breezy){pointCandidates.push(-1.1);passing-=0.01;reasons.push('breezy (8–14 mph)');}
 if(snow){pointCandidates.push(-0.25*snowWeight);passing-=0.01*snowWeight;reasons.push('snow chance '+Math.round(precip)+'%');}
 if(freezing){pointCandidates.push(-0.2);passing-=0.01;reasons.push('freezing (<32°F)');}
 if(hot){pointCandidates.push(-0.25);reasons.push('hot (85°F+)');}
 const points=pointCandidates.sort((a,b)=>Math.abs(b)-Math.abs(a))[0]||0;
 return {points,passing,passAttempts,receptions,rushAttempts,rushEfficiency:0,
  reasons,wind,temp,precip,rain,snow,rainWeight,snowWeight,windy,breezy,freezing,hot,
  hotThresholdEstimated:false,version:'weather-context-v4',
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
 if(s.indoor)categoryWeights.push(['indoor',1]);
 if(s.rain)categoryWeights.push(['rain',s.rainWeight]);
 if(s.snow)categoryWeights.push(['snow',s.snowWeight]);
 if(s.windy)categoryWeights.push(['windy',1]);
 if(s.freezing)categoryWeights.push(['freezing',1]);
 if(s.hot)categoryWeights.push(['hot',1]);
 const rates={
  QB:{passing_yards:{indoor:.06,hot:-.03,freezing:-.05,rain:-.09,snow:-.12,windy:-.08}},
  WR:{receiving_yards:{indoor:.10,hot:-.01,freezing:-.05,rain:-.10,snow:-.12,windy:-.07},
      receptions:{indoor:.08,hot:-.01,freezing:-.05,rain:-.09,snow:-.09,windy:-.05}},
  TE:{receiving_yards:{indoor:0,hot:-.11,freezing:-.07,rain:-.08,snow:-.14,windy:-.12}},
  RB:{rushing_yards:{indoor:.02,hot:-.02,freezing:.03,rain:.03,snow:.10,windy:0},
      receptions:{indoor:.05,hot:.02,freezing:-.03,rain:-.05,snow:-.12,windy:-.04}}
 };
 const alias={player_pass_yds:'passing_yards',passing_yards:'passing_yards',
  player_rec_yds:'receiving_yards',receiving_yards:'receiving_yards',
  player_rush_yds:'rushing_yards',rushing_yards:'rushing_yards',
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
  label:(pos==='RB'&&metric==='rushing_yards'?'P3 RB team yards split · 50% shrunk (rushing proxy) · ':'P3 position split · 50% shrunk · ')+chosen.name};
}
root.FDWeatherTemplate={scenario,adjust,adjustFantasy};
})(typeof window!=='undefined'?window:globalThis);
