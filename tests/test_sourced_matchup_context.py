import sys
import unittest
from pathlib import Path
from datetime import datetime, timezone
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import sourced_matchup_context as m

class SourceTests(unittest.TestCase):
    def setUp(self):
        self.now=datetime(2026,11,22,20,tzinfo=timezone.utc)
        self.game={'game_id':'2026_11_MIN_SF','away':'MIN','home':'SF','kickoff_utc':'2026-11-23T01:20:00Z'}
        self.event={'id':'123','date':'2026-11-23T01:20:00Z','competitions':[{'competitors':[{'id':'16','homeAway':'away','team':{'abbreviation':'MIN'}},{'id':'25','homeAway':'home','team':{'abbreviation':'SF'}}]}]}
        self.summary={'predictor':{'homeTeam':{'id':'25','gameProjection':'63'},'awayTeam':{'id':'16','gameProjection':'37'}},'article':{'type':'Preview','gameId':'123','published':'2026-11-20T19:00:00Z','lastModified':'2026-11-21T19:00:00Z','source':'AP','headline':'Game preview','story':'<p>Minnesota uses a blitz to pressure opposing passers.</p>','links':{'web':{'href':'http://www.espn.com/nfl/preview?gameId=123'}}}}
    def test_matchup_predictor_and_quoted_source(self):
        result=m.extract(self.game,self.event,self.summary,self.now)
        self.assertEqual(result['predictor']['home_pct'],63)
        self.assertEqual(result['article']['source'],'AP')
        self.assertEqual(result['article']['excerpt'],'Minnesota uses a blitz to pressure opposing passers.')
        self.assertTrue(result['article']['url'].startswith('https://www.espn.com/'))
    def test_future_or_wrong_game_is_not_attributed(self):
        self.summary['article']['lastModified']='2026-11-23T02:00:00Z'
        self.summary['predictor']['homeTeam']['id']='16'
        self.assertIsNone(m.extract(self.game,self.event,self.summary,self.now))
        self.assertIsNone(m.extract(self.game,{**self.event,'date':'2026-11-24T01:20:00Z'},self.summary,self.now))
    def test_no_future_predictions_and_conflicting_events(self):
        self.assertIsNone(m.extract(self.game,self.event,self.summary,datetime(2026,11,23,2,tzinfo=timezone.utc)))
        self.assertIsNone(m.collect([self.game],{'events':[self.event,self.event]},self.now,fetch=lambda _:self.summary)[self.game['game_id']])
    def test_untrusted_urls_and_invalid_probabilities(self):
        self.summary['article']['links']['web']['href']='https://www.espn.com.evil.test/x'
        self.summary['predictor']['awayTeam']['gameProjection']='80'
        self.assertIsNone(m.extract(self.game,self.event,self.summary,self.now))
    def test_safe_story_extraction(self):
        self.assertIsNone(m.quote_from_story('<script>the blitz and pressure are clearly very dangerous here today</script>'))
        self.assertIsNone(m.quote_from_story(' '.join(['pressure']*25)+'.'))
    def test_network_failure_does_not_fail(self):
        def fail(_): raise OSError('offline')
        self.assertIsNone(m.collect([self.game],{'events':[self.event]},self.now,fetch=fail)[self.game['game_id']])
if __name__=='__main__': unittest.main()
