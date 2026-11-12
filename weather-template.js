/* FOURTHDOWN weather context candidate v2.
   Anchored to P3 Adaptive NFL Weather Effects aggregates supplied 2026-11-12:
   Fair (n=4,397), windy (n=279), rain (n=295), freezing (n=324).
   This is a small, shrinkage-weighted research scenario, not a trained causal model.
   It never changes the saved/live forecast. */
(function(root){
'use strict';
function finite(v){return v!==null&&v!==undefined&&v!==''&&Number.isFinite(Number(v))?Number(v):null;}
function scenario(weather,generatedAt,kickoff){
 if(!weather||weather.status!=='forecast')return null;
 const now=Date.now(),kick=Date.parse(kickoff),captured=Date.parse(generatedAt);
 if(!Number.isFinite(kick)||!Number.isFinite(captured)||captured>=kick||now>=kick)return null;
 const wind=finite(String(weather.wind_speed||'').match(/\\d+(?:\\.\\d+)?/)?.[0]);
 const temp=finite(weather.temperature_f),precip=finite(weather.precipitation_probability);
 if(wind===null||temp===null||precip===null||wind<0||wind>150||temp< -100||temp>140||precip<0||precip>100)return null;
 const condition=String(weather.conditions||'').toLowerCase();
 const rain=precip>=60&&/rain|shower|storm/.test(condition);
 const snow=precip>=50&&/snow|sleet/.test(condition);
 const windy=wind>=15;
 let points=0,passing=0,passAttempts=0,receptions=0,rushAttempts=0;
 const reasons=[];
 // Historical differences are shrunk because these are observational group averages.
 if(rain){points-=0.8;passing-=0.025;passAttempts-=0.01;receptions-=0.02;rushAttempts+=0.01;reasons.push('rain');}
 if(windy){points-=0.6;passing-=0.02;passAttempts-=0.01;receptions-=0.01;rushAttempts+=0.01;reasons.push('wind');}
 if(snow){passing-=0.01;reasons.push('snow');}
 if(temp<=32){passing-=0.01;reasons.push('freezing temperature');}
 return {points,passing,passAttempts,receptions,rushAttempts,rushEfficiency:0,
  reasons,wind,temp,precip,version:'weather-context-v2',
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
root.FDWeatherTemplate={scenario,adjust};
})(typeof window!=='undefined'?window:globalThis);
