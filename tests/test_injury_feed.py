"""Injury feed parsing for the current ESPN league payload and team-code aliases."""
import json
import os
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from live.generate import forecast
from live import injuries

FIXTURE=Path(__file__).resolve().parents[1]/"tests"/"fixtures"/"espn_nfl_injuries_league.json"

class JSONResponse:
    def __init__(self, payload):
        self._raw=json.dumps(payload).encode()
    def read(self):
        return self._raw
    def __enter__(self):
        return self
    def __exit__(self, *exc):
        return False

def league_fixture():
    return json.loads(FIXTURE.read_text(encoding="utf-8"))

class InjuryFeedTests(unittest.TestCase):
    def test_fixture_matches_current_espn_shape(self):
        league=league_fixture()
        self.assertEqual(league["status"], "success")
        self.assertIn("season", league)
        block=next(b for b in league["injuries"] if b["displayName"]=="Baltimore Ravens")
        self.assertEqual(set(block), {"id","displayName","injuries"})
        self.assertNotIn("team", block)
        row=next(r for r in block["injuries"] if r["athlete"]["displayName"]=="Lamar Jackson")
        self.assertEqual(row["status"], "Injured Reserve")
        self.assertEqual(row["athlete"]["position"]["abbreviation"], "QB")
        self.assertIn("details", row)

    def test_team_from_current_league_block(self):
        self.assertEqual(injuries.team_from_block({"id":"33","displayName":"Baltimore Ravens"}),"BAL")
        self.assertEqual(injuries.team_from_block({"id":"30","displayName":"Jacksonville Jaguars"}),"JAX")
        self.assertEqual(injuries.team_from_block({"id":"14","displayName":"Los Angeles Rams"}),"LAR")
        self.assertEqual(injuries.team_from_block({"id":"24","displayName":"Los Angeles Chargers"}),"LAC")
        self.assertEqual(injuries.team_from_block({"id":"28","displayName":"Washington Commanders"}),"WAS")
        self.assertEqual(injuries.team_from_block({"id":"28"}),"WAS")
        self.assertEqual(injuries.team_from_block({}),"")

    def test_legacy_nested_team_abbreviation_still_works(self):
        self.assertEqual(injuries.team_from_block({"team":{"abbreviation":"JAC"}}),"JAC")
        self.assertEqual(injuries.team_from_block({"team":{"abbreviation":"WSH"}}),"WSH")
        self.assertEqual(injuries.team_from_block({"team":{"abbreviation":"bal"}}),"BAL")
        self.assertEqual(injuries.team_from_block({"team":{"displayName":"Los Angeles Rams"}}),"LAR")

    def test_apply_league_feed_fills_alias_keys(self):
        data={"teams":{}}
        filled=injuries.apply_league_feed(data, league_fixture())
        self.assertEqual(filled, 5)
        bal={p["player"]:p for p in data["teams"]["BAL"]["players"]}
        self.assertEqual(data["teams"]["BAL"]["status"], "retrieved")
        self.assertEqual(bal["Lamar Jackson"]["status"], "Injured Reserve")
        self.assertEqual(bal["Lamar Jackson"]["position"], "QB")
        self.assertEqual(bal["Lamar Jackson"]["detail"], "Surgery")
        self.assertIn("Jaylinn Hawkins", bal)
        self.assertTrue(any(p["player"]=="Ladd McConkey" and p["status"]=="Out" for p in data["teams"]["LAC"]["players"]))
        self.assertTrue(any(p["status"]=="Active" for p in data["teams"]["BAL"]["players"]))
        jags=data["teams"]["JAX"]["players"]
        self.assertEqual(jags, data["teams"]["JAC"]["players"])
        self.assertTrue(jags)
        self.assertEqual(data["teams"]["LA"]["players"], data["teams"]["LAR"]["players"])
        self.assertTrue(data["teams"]["LA"]["players"])
        self.assertEqual(data["teams"]["WAS"]["players"], data["teams"]["WSH"]["players"])
        self.assertTrue(data["teams"]["WAS"]["players"])

    def test_legacy_payload_still_parses(self):
        data={"teams":{}}
        filled=injuries.apply_league_feed(data, {"injuries":[
            {"team":{"abbreviation":"BAL","displayName":"Baltimore Ravens"},"injuries":[
                {"status":"Out","athlete":{"displayName":"Test Player","position":{"abbreviation":"RB"}}},
            ]},
            {"team":{"abbreviation":"JAC"},"injuries":[
                {"status":"Out","athlete":{"displayName":"Jessie Bates III","position":{"abbreviation":"S"}}},
            ]},
        ]})
        self.assertEqual(filled, 2)
        self.assertEqual(data["teams"]["BAL"]["players"][0]["player"], "Test Player")
        self.assertEqual(data["teams"]["BAL"]["status"], "retrieved")
        self.assertEqual(data["teams"]["JAX"]["players"][0]["player"], "Jessie Bates III")
        self.assertEqual(data["teams"]["JAC"]["players"][0]["player"], "Jessie Bates III")

    def test_empty_block_is_not_retrieved(self):
        data={"teams":{}}
        filled=injuries.apply_league_feed(data, {"injuries":[{"id":"33","displayName":"Baltimore Ravens","injuries":[]}]})
        self.assertEqual(filled, 0)
        self.assertEqual(data["teams"]["BAL"]["status"], "empty")
        self.assertEqual(data["teams"]["BAL"]["players"], [])

    def test_empty_team_payload_is_not_retrieved(self):
        self.assertEqual(injuries.report_from_payload({}), {"status":"empty","players":[]})
        data={"teams":{}}
        calls=[]
        def load_team(code):
            calls.append(code)
            if code=="JAC":
                raise OSError("HTTP 400")
            return {}
        self.assertEqual(injuries.fallback_team(data, "JAX", load_team), "empty")
        self.assertEqual(data["teams"]["JAX"]["status"], "empty")
        self.assertEqual(data["teams"]["JAC"]["status"], "empty")
        self.assertEqual(data["teams"]["JAX"]["players"], [])
        self.assertIn("JAX", calls)
        def fail(code):
            raise OSError("down")
        failed={"teams":{}}
        self.assertEqual(injuries.fallback_team(failed, "BAL", fail), "unavailable")
        self.assertEqual(failed["teams"]["BAL"], {"status":"unavailable","players":[]})

    def test_missing_team_identity_is_skipped(self):
        data={"teams":{}}
        payload={"injuries":[{"id":"unknown","displayName":"Not A Team","injuries":[{"status":"Out","athlete":{"displayName":"X","position":{"abbreviation":"QB"}}}]}]}
        self.assertEqual(injuries.apply_league_feed(data, payload), 0)
        self.assertEqual(data["teams"], {})
        with self.assertRaises(injuries.InjuryPublishError):
            injuries.assert_publishable(payload, data)

    def test_publish_refuses_when_league_players_do_not_land(self):
        league=league_fixture()
        stale={"teams":{team:{"status":"retrieved","players":[]} for team in injuries.TEAMS}}
        with self.assertRaises(injuries.InjuryPublishError):
            injuries.assert_publishable(league, stale)
        with self.assertRaises(injuries.InjuryPublishError):
            injuries.assert_publishable(league, {"teams":{}})
        parsed={"teams":{}}
        injuries.apply_league_feed(parsed, league)
        injuries.assert_publishable(league, parsed)

    def test_lookup_report_accepts_either_code(self):
        jac={"status":"retrieved","players":[{"player":"Trevor Lawrence","position":"QB","status":"Out"}]}
        empty={"status":"empty","players":[]}
        self.assertEqual(injuries.lookup_report({"JAC":jac}, "JAX"), jac)
        self.assertEqual(injuries.lookup_report({"JAX":jac}, "JAC"), jac)
        self.assertEqual(injuries.lookup_report({"JAX":empty,"JAC":jac}, "JAX"), jac)
        lar={"status":"retrieved","players":[{"player":"Puka Nacua","position":"WR","status":"Out"}]}
        self.assertEqual(injuries.lookup_report({"LAR":lar}, "LA"), lar)
        self.assertEqual(injuries.lookup_report({"LA":lar}, "LAR"), lar)
        wsh={"status":"retrieved","players":[{"player":"Jayden Daniels","position":"QB","status":"Questionable"}]}
        self.assertEqual(injuries.lookup_report({"WSH":wsh}, "WAS"), wsh)
        self.assertEqual(injuries.lookup_report({"WAS":wsh}, "WSH"), wsh)
        self.assertEqual(injuries.lookup_report({}, "BAL"), {})

    def test_forecast_reads_espn_codes_for_nflverse_teams(self):
        games=[]; epa=[]
        for week in range(1,6):
            played=week<5
            games.append(dict(season=2026,week=week,game_type="REG",game_id=f"g{week}",home_team="JAX",away_team="LA",home_score=24 if played else None,away_score=17 if played else None,gameday=f"2026-09-{week+1:02d}" if played else "2026-11-16",gametime="13:00"))
            if played:
                epa.extend([
                    dict(season=2026,week=week,team="JAX",offense_epa=.1,defense_epa=-.05),
                    dict(season=2026,week=week,team="LA",offense_epa=-.05,defense_epa=.1),
                ])
        reports={
            "JAC":{"status":"retrieved","players":[{"player":"Trevor Lawrence","position":"QB","status":"Out"}]},
            "LAR":{"status":"retrieved","players":[{"player":"Puka Nacua","position":"WR","status":"Out"}]},
            "WSH":{"status":"retrieved","players":[{"player":"Jayden Daniels","position":"QB","status":"Out"}]},
        }
        result=forecast(games, epa, datetime(2026,11,16,tzinfo=timezone.utc), reports)
        adj=result["games"][0]["injury_adjustments"]
        self.assertNotEqual(adj["JAX"]["status"], "injury_feed_unavailable")
        self.assertNotEqual(adj["LA"]["status"], "injury_feed_unavailable")
        self.assertGreaterEqual(adj["JAX"]["reported_out"], 1)
        self.assertGreaterEqual(adj["LA"]["reported_out"], 1)
        was_games=[]; was_epa=[]
        for week in range(1,6):
            played=week<5
            was_games.append(dict(season=2026,week=week,game_type="REG",game_id=f"w{week}",home_team="WAS",away_team="BAL",home_score=20 if played else None,away_score=17 if played else None,gameday=f"2026-09-{week+1:02d}" if played else "2026-11-16",gametime="13:00"))
            if played:
                was_epa.extend([
                    dict(season=2026,week=week,team="WAS",offense_epa=.05,defense_epa=.0),
                    dict(season=2026,week=week,team="BAL",offense_epa=.08,defense_epa=-.02),
                ])
        was=forecast(was_games, was_epa, datetime(2026,11,16,tzinfo=timezone.utc), reports)
        self.assertGreaterEqual(was["games"][0]["injury_adjustments"]["WAS"]["reported_out"], 1)

    def test_main_publishes_fixture_and_does_not_mark_empty_endpoints_retrieved(self):
        league=league_fixture()
        def fake_urlopen(req, timeout=None):
            if "/teams/" in req.full_url:
                return JSONResponse({})
            return JSONResponse(league)
        previous=os.getcwd()
        with tempfile.TemporaryDirectory() as tmp:
            os.chdir(tmp)
            try:
                with patch("live.injuries.urllib.request.urlopen", side_effect=fake_urlopen):
                    injuries.main()
                published=json.loads(Path("data/injuries.json").read_text(encoding="utf-8"))
            finally:
                os.chdir(previous)
        names={p["player"] for p in published["teams"]["BAL"]["players"]}
        self.assertIn("Lamar Jackson", names)
        self.assertTrue(any(p["player"]=="Ladd McConkey" for p in published["teams"]["LAC"]["players"]))
        self.assertEqual(published["teams"]["BUF"]["status"], "empty")
        self.assertEqual(published["teams"]["BUF"]["players"], [])
        self.assertNotEqual(published["teams"]["BUF"]["status"], "retrieved")

    def test_main_refuses_to_publish_unparsed_league_players(self):
        league={"timestamp":"2026-11-16T03:56:57Z","status":"success","injuries":[
            {"id":"nope","displayName":"Not A Team","injuries":[
                {"status":"Injured Reserve","athlete":{"displayName":"Lamar Jackson","position":{"abbreviation":"QB"}},"details":{"detail":"Surgery"}},
            ]},
        ]}
        def fake_urlopen(req, timeout=None):
            if "/teams/" in req.full_url:
                return JSONResponse({})
            return JSONResponse(league)
        previous=os.getcwd()
        with tempfile.TemporaryDirectory() as tmp:
            os.chdir(tmp)
            try:
                with patch("live.injuries.urllib.request.urlopen", side_effect=fake_urlopen):
                    with self.assertRaises(SystemExit) as caught:
                        injuries.main()
                self.assertIn("REFUSING TO PUBLISH", str(caught.exception))
                self.assertFalse((Path(tmp)/"data"/"injuries.json").exists())
            finally:
                os.chdir(previous)

if __name__=="__main__":
    unittest.main()
