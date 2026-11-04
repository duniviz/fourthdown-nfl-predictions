#!/usr/bin/env python3
"""Offline archive integration test; no live files or network are modified."""
import datetime as dt
import importlib.util
import json
import pathlib
import tempfile
import unittest

spec=importlib.util.spec_from_file_location("archive",pathlib.Path(__file__).with_name("archive_pregame_player_lines.py"))
archive=importlib.util.module_from_spec(spec)
spec.loader.exec_module(archive)

class ArchiveTest(unittest.TestCase):
    def test_all_markets_and_postkickoff_lock(self):
        original=archive.ROOT
        now=dt.datetime.now(dt.timezone.utc)
        kickoff=(now+dt.timedelta(minutes=15)).isoformat()
        quote=(now-dt.timedelta(minutes=4)).isoformat()
        forecast=(now-dt.timedelta(minutes=9)).isoformat()
        markets=[("player_passing_yards",265.0,250.5),("player_rushing_yards",82.0,90.5),
                 ("player_receiving_yards",74.0,70.5),("player_receptions",5.0,4.5)]
        with tempfile.TemporaryDirectory() as temp:
            archive.ROOT=pathlib.Path(temp)
            def write(name,obj):
                (archive.ROOT/name).write_text(json.dumps(obj))
            def projections(selected):
                return {"generated_at_utc":forecast,"players":[
                    {"game_id":"2026_08_KC_DEN","player":"Test Player","player_id":"00-TEST-1","team":"KC",
                     "market_key":market,"projection":proj} for market,proj,line in selected]}
            write("count-projections.json",projections(markets[3:]))
            write("player-research.json",projections(markets[:3]))
            write("dk-odds.json",{"bookmaker":"draftkings","rows":[
                {"game_id":"2026_08_KC_DEN","player":"Test Player","market_key":market,
                 "line":line,"commence_time":kickoff,"last_update":quote,
                 "away_team":"Kansas City Chiefs","home_team":"Denver Broncos"}
                for market,proj,line in markets]})
            try:
                # Real DK feeds often use shorthand names for the same markets.
                odds=json.loads((archive.ROOT/"dk-odds.json").read_text())
                shorthand={"player_passing_yards":"player_pass_yds",
                           "player_rushing_yards":"player_rush_yds",
                           "player_receiving_yards":"player_rec_yds"}
                for row in odds["rows"]:
                    row["market_key"]=shorthand.get(row["market_key"],row["market_key"])
                write("dk-odds.json",odds)
                archive.main()
                first=json.loads((archive.ROOT/"player-history.json").read_text())["players"]
                self.assertEqual(len(first),4)
                self.assertEqual({x["stat_key"] for x in first},{"passing_yards","rushing_yards","receiving_yards","receptions"})
                self.assertTrue(all(x["player_id"]=="00-TEST-1" for x in first))
                self.assertEqual({x["stat_key"]:x["recommended_side"] for x in first},
                                 {"passing_yards":"OVER","rushing_yards":"UNDER",
                                  "receiving_yards":"OVER","receptions":"OVER"})
                archive.main()
                self.assertEqual(len(json.loads((archive.ROOT/"player-history.json").read_text())["players"]),4)
                # Odds changed after kickoff must not replace the original snapshots.
                odds=json.loads((archive.ROOT/"dk-odds.json").read_text())
                odds["rows"][0]["last_update"]=(now+dt.timedelta(hours=4)).isoformat()
                odds["rows"][0]["line"]=300.5
                write("dk-odds.json",odds)
                archive.main()
                final=json.loads((archive.ROOT/"player-history.json").read_text())["players"]
                self.assertEqual(len(final),4)
                self.assertEqual(next(x["dk_line"] for x in final if x["stat_key"]=="passing_yards"),250.5)
            finally:
                archive.ROOT=original

if __name__=="__main__":
    unittest.main()
