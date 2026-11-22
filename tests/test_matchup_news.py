import importlib.util
from datetime import datetime, timezone
from pathlib import Path
import unittest

spec=importlib.util.spec_from_file_location('free_previews',Path(__file__).resolve().parents[1]/'tools/generate_free_game_previews.py')
mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

class MatchupNewsTest(unittest.TestCase):
    def test_filters_unrelated_stale_and_untrusted_links(self):
        rss=b'''<rss><channel>
        <item><title>Vikings vs 49ers preview</title><link>https://news.google.com/rss/articles/1</link><pubDate>Sun, 22 Nov 2026 16:00:00 GMT</pubDate><source>Sports News</source></item>
        <item><title>Vikings roster news</title><link>https://news.google.com/rss/articles/2</link><pubDate>Sun, 22 Nov 2026 16:00:00 GMT</pubDate><source>News</source></item>
        <item><title>Vikings vs 49ers old</title><link>https://news.google.com/rss/articles/3</link><pubDate>Sun, 01 Nov 2026 16:00:00 GMT</pubDate><source>News</source></item>
        <item><title>Vikings vs 49ers unsafe</title><link>https://news.google.com.evil.test/a</link><pubDate>Sun, 22 Nov 2026 16:00:00 GMT</pubDate><source>News</source></item>
        </channel></rss>'''
        news=mod.matchup_news({'away':'MIN','home':'SF'},datetime(2026,11,22,20,tzinfo=timezone.utc),fetch=lambda _:rss)
        self.assertEqual(len(news),1)
        self.assertEqual(news[0]['publisher'],'Sports News')
        self.assertEqual(news[0]['title'],'Vikings vs 49ers preview')
    def test_feed_failure_is_optional(self):
        def fail(_): raise OSError('no network')
        self.assertEqual(mod.matchup_news({'away':'MIN','home':'SF'},datetime.now(timezone.utc),fetch=fail),[])
    def test_missing_team_skips_feed(self):
        self.assertEqual(mod.matchup_news({'away':'MIN','home':'UNKNOWN'},datetime.now(timezone.utc)),[])

if __name__=='__main__': unittest.main()
