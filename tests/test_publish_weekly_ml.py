import os,subprocess,tempfile,unittest
from pathlib import Path

SCRIPT=Path(__file__).resolve().parents[1]/'scripts'/'publish_weekly_ml.sh'

class WeeklyPublishTests(unittest.TestCase):
 def git(self,where,*args):
  return subprocess.run(['git',*args],cwd=where,check=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
  self.remote=self.root/'remote.git';self.a=self.root/'weekly';self.b=self.root/'other'
  self.git(self.root,'init','--bare','--initial-branch=main',str(self.remote))
  self.git(self.root,'clone',str(self.remote),str(self.a))
  self.git(self.a,'config','user.name','Test');self.git(self.a,'config','user.email','test@example.com')
  (self.a/'data').mkdir()
  for p in ('game-official-results.json','player-calibration.json','player-results.json'):(self.a/'data'/p).write_text('original\n')
  (self.a/'sensitive.txt').write_text('original\n')
  self.git(self.a,'add','.');self.git(self.a,'commit','-m','initial');self.git(self.a,'push','-u','origin','main')
  self.git(self.root,'clone',str(self.remote),str(self.b))
  self.git(self.b,'config','user.name','Test');self.git(self.b,'config','user.email','test@example.com')
 def tearDown(self):self.temp.cleanup()
 def call(self):
  return subprocess.run(['bash',str(SCRIPT)],cwd=self.a,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,env={**os.environ,'GIT_TERMINAL_PROMPT':'0'})
 def test_latest_production_ledgers_win_while_ml_archive_is_published(self):
  for p in ('game-official-results.json','player-calibration.json','player-results.json'):(self.a/'data'/p).write_text('weekly\n')
  (self.a/'data'/'ml-card-training.csv.gz').write_text('new training\n')
  self.git(self.a,'add','.');self.git(self.a,'commit','-m','weekly learning')
  for p in ('game-official-results.json','player-calibration.json','player-results.json'):(self.b/'data'/p).write_text('newer forecast\n')
  self.git(self.b,'add','.');self.git(self.b,'commit','-m','newer forecast');self.git(self.b,'push')
  result=self.call();self.assertEqual(result.returncode,0,result.stderr)
  self.git(self.b,'pull','--ff-only')
  for p in ('game-official-results.json','player-calibration.json','player-results.json'):self.assertEqual((self.b/'data'/p).read_text(),'newer forecast\n')
  self.assertEqual((self.b/'data'/'ml-card-training.csv.gz').read_text(),'new training\n')
 def test_unrecognized_conflict_aborts_without_overwriting(self):
  (self.a/'sensitive.txt').write_text('weekly\n');self.git(self.a,'add','.');self.git(self.a,'commit','-m','weekly')
  (self.b/'sensitive.txt').write_text('other\n');self.git(self.b,'add','.');self.git(self.b,'commit','-m','other');self.git(self.b,'push')
  result=self.call();self.assertNotEqual(result.returncode,0)
  self.assertIn('Unexpected conflict',result.stderr)
  self.assertEqual((self.b/'sensitive.txt').read_text(),'other\n')
  self.assertEqual((self.a/'sensitive.txt').read_text(),'weekly\n')
if __name__=='__main__':unittest.main()
