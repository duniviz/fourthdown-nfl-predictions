"""Fetch stadium-specific NWS hourly forecasts near NFL kickoff.

Weather is published as context, NOT silently turned into arbitrary point penalties.
"""
import json
import urllib.request
from datetime import datetime,timezone,timedelta
from pathlib import Path
STADIUMS={
"ARI":(33.5276,-112.2626,True),"ATL":(33.7554,-84.4008,True),"BAL":(39.278,-76.6227,False),"BUF":(42.7738,-78.7868,False),"CAR":(35.2258,-80.8528,False),"CHI":(41.8623,-87.6167,False),"CIN":(39.0954,-84.516,False),"CLE":(41.5061,-81.6995,False),"DAL":(32.748,-97.0928,True),"DEN":(39.7439,-105.0208,False),"DET":(42.34,-83.0456,True),"GB":(44.5013,-88.0622,False),"HOU":(29.6847,-95.4107,True),"IND":(39.7601,-86.1639,True),"JAC":(30.3239,-81.6373,False),"KC":(39.0489,-94.4839,False),"LV":(36.0909,-115.1833,True),"LAC":(33.9535,-118.3392,True),"LAR":(33.9535,-118.3392,True),"MIA":(25.958,-80.2389,False),"MIN":(44.9737,-93.2575,True),"NE":(42.0909,-71.2643,False),"NO":(29.9511,-90.0812,True),"NYG":(40.8135,-74.0745,False),"NYJ":(40.8135,-74.0745,False),"PHI":(39.9008,-75.1675,False),"PIT":(40.4468,-80.0158,False),"SF":(37.403,-121.97,False),"SEA":(47.5952,-122.3316,False),"TB":(27.9759,-82.5033,False),"TEN":(36.1665,-86.7713,False),"WAS":(38.9076,-76.8645,False)}
def get(url):
    req=urllib.request.Request(url,headers={"User-Agent":"FOURTHDOWN predictions (public research; contact via GitHub)","Accept":"application/geo+json, application/json"})
    with urllib.request.urlopen(req,timeout=12) as r:return json.load(r)
def main():
    games=json.loads(Path("data/live-v2.json").read_text())["games"]
    result={"generated_at_utc":datetime.now(timezone.utc).isoformat(),"source":"US National Weather Service hourly forecast","model_adjusted":False,"games":{}}
    for g in games:
        home=g["home"]; gid=g["game_id"]
        if home not in STADIUMS:
            result["games"][gid]={"status":"stadium_unknown"};continue
        lat,lon,roof=STADIUMS[home]
        if roof:
            result["games"][gid]={"status":"roofed_stadium","roof":"covered_or_retractable","note":"Roof position not verified; outdoor forecast may not apply"};continue
        try:
            kickoff=datetime.fromisoformat(g["kickoff_utc"].replace("Z","+00:00"))
            points=get(f"https://api.weather.gov/points/{lat},{lon}")
            hourly=get(points["properties"]["forecastHourly"])
            periods=hourly["properties"]["periods"]
            valid=[p for p in periods if datetime.fromisoformat(p["startTime"]).astimezone(timezone.utc)<=kickoff<datetime.fromisoformat(p["endTime"]).astimezone(timezone.utc)]
            if not valid:
                result["games"][gid]={"status":"outside_forecast_horizon"};continue
            p=valid[0]
            result["games"][gid]={"status":"forecast","temperature_f":p.get("temperature"),"wind_speed":p.get("windSpeed"),"wind_direction":p.get("windDirection"),"precipitation_probability":(p.get("probabilityOfPrecipitation") or {}).get("value"),"conditions":p.get("shortForecast"),"forecast_period_start":p.get("startTime")}
        except Exception:
            result["games"][gid]={"status":"unavailable"}
    Path("data/weather.json").write_text(json.dumps(result,indent=2)+"\n")
    print("Wrote weather status for",len(result["games"]),"games")
if __name__=="__main__":main()
