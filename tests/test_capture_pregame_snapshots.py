import datetime, importlib.util, pathlib, unittest
spec=importlib.util.spec_from_file_location("capture",pathlib.Path(__file__).resolve().parents[1]/"scripts"/"capture_pregame_snapshots.py")
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
UTC=datetime.timezone.utc
def date(h):return datetime.datetime(2026,11,1,h,tzinfo=UTC)
class CaptureTests(unittest.TestCase):
 def setUp(self):
  self.p={"game_id":"game","player_id":"123","player":"Example","team":"GB","opponent":"CHI","market_key":"player_rushing_yards","projection":82,"generated_at_utc":date(16).isoformat()}
  self.q={"game_id":"game","player_id":"123","market_key":"player_rushing_yards","line":75.5,"captured_at":date(16).isoformat()}
  self.games={("GB","CHI"):date(18),("CHI","GB"):date(18)}
 def test_latest_pregame(self):
  rows=m.capture([], [self.p], [self.q],self.games,date(17))
  self.assertEqual((rows[0]["projection"],rows[0]["dk_line"]),(82,75.5))
 def test_no_post_kickoff_capture(self):
  self.assertEqual(m.capture([], [self.p],[self.q],self.games,date(19)),[])
 def test_no_post_kickoff_source(self):
  p=dict(self.p,generated_at_utc=date(19).isoformat())
  self.assertEqual(m.capture([], [p],[self.q],self.games,date(17)),[])
 def test_missing_line_is_not_fabricated(self):
  self.assertIsNone(m.capture([],[self.p],[],self.games,date(17))[0]["dk_line"])
 def test_existing_snapshot_preserved_after_kickoff(self):
  old=m.capture([],[self.p],[self.q],self.games,date(17))
  self.assertEqual(m.capture(old,[self.p],[],self.games,date(19)),old)
 def test_newer_quote_updates_without_new_projection(self):
  old=m.capture([],[self.p],[self.q],self.games,date(17))
  later=dict(self.q,line=79.5,captured_at=date(17).isoformat())
  updated=m.capture(old,[self.p],[later],self.games,date(17))
  self.assertEqual(updated[0]["projection"],82)
  self.assertEqual(updated[0]["dk_line"],79.5)
 def test_same_name_on_opposite_teams_is_ambiguous(self):
  first={**self.p,"player":"Alex Smith","player_id":"one"}
  second={**self.p,"player":"Alex Smith Jr.","player_id":"two","team":"CHI","opponent":"GB"}
  quote={"player":"Alex Smith","market_key":"player_rushing_yards","line":75.5,
         "home_team":"Green Bay Packers","away_team":"Chicago Bears",
         "commence_time":date(18).isoformat(),"last_update":date(16).isoformat()}
  rows=m.capture([], [first,second],[quote],self.games,date(17))
  self.assertTrue(all(row["dk_line"] is None for row in rows))
 def test_rescheduled_game_does_not_reuse_old_kickoff_line(self):
  quote={**self.q,"commence_time":date(18).isoformat()}
  old=m.capture([], [self.p],[quote],self.games,date(17))
  revised={("GB","CHI"):date(20)}
  new=m.capture(old,[self.p],[quote],revised,date(17))
  self.assertIsNone(new[0]["dk_line"])
  self.assertEqual(new[0]["kickoff"],date(20).isoformat())
  self.assertEqual(m.capture(old,[self.p],[quote],revised,date(19)),old)
 def test_stale_quote_does_not_replace_newer(self):
  newer=dict(self.q,line=79.5,captured_at=date(17).isoformat())
  old=m.capture([],[self.p],[newer],self.games,date(17))
  updated=m.capture(old,[self.p],[self.q],self.games,date(17))
  self.assertEqual(updated[0]["dk_line"],79.5)
if __name__=="__main__":unittest.main()
