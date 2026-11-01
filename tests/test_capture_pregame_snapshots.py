import datetime, importlib.util, pathlib, unittest
spec=importlib.util.spec_from_file_location("capture",pathlib.Path(__file__).resolve().parents[1]/"scripts"/"capture_pregame_snapshots.py")
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
UTC=datetime.timezone.utc
def date(h):return datetime.datetime(2026,11,1,h,tzinfo=UTC)
class CaptureTests(unittest.TestCase):
 def setUp(self):
  self.p={"game_id":"game","player_id":"123","player":"Example","team":"GB","opponent":"CHI","market_key":"player_rushing_yards","projection":82,"generated_at_utc":date(16).isoformat()}
  self.q={"game_id":"game","player_id":"123","market_key":"player_rushing_yards","line":75.5,"captured_at":date(16).isoformat()}
  self.games={("GB","CHI"):date(18)}
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
if __name__=="__main__":unittest.main()
