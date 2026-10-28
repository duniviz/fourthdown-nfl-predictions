import unittest
from tools.fetch_official_inactive_sources import source_url
class SourceTests(unittest.TestCase):
 def test_official_https(self):
  self.assertEqual(source_url("https://www.nfl.com/news/example"),"https://www.nfl.com/news/example")
 def test_reject_lookalike(self):
  for url in ("https://nfl.com.evil.example/news","http://nfl.com/news","https://evil.example/nfl.com","https://nfl.com@evil.example/news"):
   with self.subTest(url=url),self.assertRaises(ValueError):source_url(url)
if __name__=="__main__":unittest.main()
